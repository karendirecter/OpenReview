from app.llm.base import LLMClient
from app.prompts.review_prompt import build_review_prompt
from app.review.context_loader import select_review_context
from app.review.models import ChangedFile, IssueHit, ReviewFinding, ReviewResult, ReviewTask
from app.review.schema import validate_llm_payload
from app.rules.diff_general import GeneralDiffAnalyzer
from app.rules.python_ast import PythonAstAnalyzer
from app.rules.registry import run_analyzers


def ensure_not_stale(task: ReviewTask) -> None:
    if task.head_sha != task.review_commit_sha:
        raise RuntimeError("stale review commit")


def review_pull_request(task: ReviewTask, llm_client: LLMClient | None = None) -> ReviewResult:
    ensure_not_stale(task)
    candidate_hits = run_stage_one(task)
    llm_candidates = candidate_hits or build_llm_fallback_hits(task)
    findings = run_stage_two(task, llm_candidates, llm_client) if llm_candidates else []
    used_llm_fallback = not candidate_hits and bool(llm_candidates)

    if not findings:
        findings = [issue_hit_to_finding(task, hit) for hit in candidate_hits]

    summary, risk = summarize_findings(findings, used_llm_fallback=used_llm_fallback)
    return ReviewResult(
        review_commit_sha=task.review_commit_sha,
        summary=summary,
        overall_risk=risk,
        findings=findings,
        stats={
            "stage1_candidates": len(candidate_hits),
            "llm_candidates": len(llm_candidates),
            "stage2_findings": len(findings),
        },
        render_mode="summary_only" if not findings else "summary_inline",
    )


def run_stage_one(task: ReviewTask) -> list[IssueHit]:
    hits: list[IssueHit] = []

    for changed_file in task.changed_files:
        diff_text = "\n".join(changed_file.diff_hunks)
        hits.extend(run_analyzers([GeneralDiffAnalyzer(task.review_commit_sha)], changed_file.file_path, diff_text))

        if changed_file.language == "python" and changed_file.full_file_content:
            try:
                hits.extend(
                    PythonAstAnalyzer(task.review_commit_sha).analyze(
                        file_path=changed_file.file_path,
                        diff=changed_file.full_file_content,
                    )
                )
            except SyntaxError:
                continue

    return hits


def run_stage_two(task: ReviewTask, candidate_hits: list[IssueHit], llm_client: LLMClient | None) -> list[ReviewFinding]:
    if llm_client is None:
        return []

    findings: list[ReviewFinding] = []
    file_lookup = {changed.file_path: changed for changed in task.changed_files}

    for hit in candidate_hits[:5]:
        changed_file = file_lookup.get(hit.file_path)
        if changed_file is None:
            continue

        diff_context = select_review_context(
            diff_hunks=changed_file.diff_hunks,
            file_content=changed_file.full_file_content or "",
            use_full_file=bool(changed_file.full_file_content),
        )
        prompt = build_review_prompt(
            review_commit_sha=task.review_commit_sha,
            file_path=hit.file_path,
            diff_context=diff_context,
            candidate_summary=hit.message,
        )

        try:
            payload = llm_client.review_findings(prompt)
        except Exception:  # noqa: BLE001
            continue

        validated = validate_llm_payload(payload, {hit.file_path}, task.review_commit_sha)
        if validated:
            findings.extend(validated)
            continue
        findings.extend(
            salvage_string_findings(
                payload=payload,
                hit=hit,
                changed_file=changed_file,
                review_commit_sha=task.review_commit_sha,
            )
        )

    return findings


def build_llm_fallback_hits(task: ReviewTask) -> list[IssueHit]:
    if task.trigger_type != "command":
        return []

    fallback_hits: list[IssueHit] = []
    for changed_file in task.changed_files:
        if not changed_file.diff_hunks:
            continue
        line_number = first_changed_line(changed_file)
        fallback_hits.append(
            IssueHit(
                file_path=changed_file.file_path,
                line_number=line_number,
                end_line_number=line_number,
                commit_sha=task.review_commit_sha,
                rule_id="llm.full-review-fallback",
                severity="medium",
                message="Perform full-file correctness review for this changed file.",
                evidence="No static rule hit; escalate to LLM review because /review was requested.",
            )
        )
    return fallback_hits


def issue_hit_to_finding(task: ReviewTask, hit: IssueHit) -> ReviewFinding:
    changed_file = next((item for item in task.changed_files if item.file_path == hit.file_path), None)
    snippet = extract_code_snippet(changed_file, hit.line_number)
    return ReviewFinding(
        file_path=hit.file_path,
        line_number=hit.line_number,
        end_line_number=hit.end_line_number or hit.line_number,
        commit_sha=task.review_commit_sha,
        risk_level=hit.severity,
        confidence=0.9,
        issue_title=hit.message,
        issue_detail=hit.evidence,
        why_it_matters=hit.message,
        fix_strategy="Review the flagged code path and apply the safer alternative.",
        suggested_code="",
        original_code_snippet=snippet,
    )


def salvage_string_findings(
    payload: dict,
    hit: IssueHit,
    changed_file: ChangedFile,
    review_commit_sha: str,
) -> list[ReviewFinding]:
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        return []

    snippet = extract_code_snippet(changed_file, hit.line_number)
    findings: list[ReviewFinding] = []
    for item in raw_findings:
        if not isinstance(item, str):
            continue
        detail = item.strip()
        if not detail:
            continue
        findings.append(
            ReviewFinding(
                file_path=hit.file_path,
                line_number=hit.line_number,
                end_line_number=hit.end_line_number or hit.line_number,
                commit_sha=review_commit_sha,
                risk_level=hit.severity,
                confidence=0.6,
                issue_title=derive_string_finding_title(detail),
                issue_detail=detail,
                why_it_matters=detail,
                fix_strategy="Review the LLM finding and apply the necessary guard or correction.",
                suggested_code="",
                original_code_snippet=snippet,
            )
        )
    return findings


def derive_string_finding_title(detail: str) -> str:
    sentence = detail.split(".")[0].strip()
    if len(sentence) <= 90:
        return sentence
    return f"{sentence[:87].rstrip()}..."


def summarize_findings(findings: list[ReviewFinding], *, used_llm_fallback: bool = False) -> tuple[str, str]:
    if not findings:
        if used_llm_fallback:
            return "静态规则未命中，但 LLM 复核没有产出有效结果；本次自动审查已降级，请人工复查或稍后重试。", "medium"
        return "未发现高置信度正确性缺陷，检查通过。", "low"

    overall_risk = "high" if any(finding.risk_level == "high" for finding in findings) else "medium"
    return f"发现 {len(findings)} 个需要关注的正确性问题。", overall_risk


def extract_code_snippet(changed_file: ChangedFile | None, line_number: int) -> str:
    if changed_file is None or not changed_file.full_file_content:
        return ""

    lines = changed_file.full_file_content.splitlines()
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]
    return ""


def first_changed_line(changed_file: ChangedFile) -> int:
    for hunk in changed_file.diff_hunks:
        for line in hunk.splitlines():
            if line.startswith("@@"):
                parts = line.split()
                if len(parts) >= 3 and parts[2].startswith("+"):
                    return int(parts[2].split(",")[0][1:])
    return 1
