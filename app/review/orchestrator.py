from app.llm.base import LLMClient
from app.prompts.review_prompt import PROMPT_VERSION, build_fixer_prompt, build_inspector_prompt
from app.review.context_loader import select_review_context
from app.review.models import AgentTrace, ChangedFile, IssueHit, ReviewFinding, ReviewResult, ReviewTask
from app.review.schema import suggestion_matches_confirmed_issue, validate_llm_payload
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
    findings, agent_traces = run_stage_two(task, llm_candidates, llm_client) if llm_candidates else ([], [])
    used_llm_fallback = not candidate_hits and bool(llm_candidates)

    if not findings:
        findings = [issue_hit_to_finding(task, hit) for hit in candidate_hits]

    summary, risk = summarize_findings(findings, used_llm_fallback=used_llm_fallback)
    return ReviewResult(
        review_run_id=task.review_run_id,
        review_commit_sha=task.review_commit_sha,
        summary=summary,
        overall_risk=risk,
        findings=findings,
        stats={
            "stage1_candidates": len(candidate_hits),
            "llm_candidates": len(llm_candidates),
            "stage2_findings": len(findings),
            "agent_traces": len(agent_traces),
            "fixer_suggestions": sum(1 for finding in findings if finding.suggested_code),
        },
        render_mode="summary_only" if not findings else "summary_inline",
        agent_traces=agent_traces,
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


def run_stage_two(
    task: ReviewTask,
    candidate_hits: list[IssueHit],
    llm_client: LLMClient | None,
) -> tuple[list[ReviewFinding], list[AgentTrace]]:
    if llm_client is None:
        return [], []

    findings: list[ReviewFinding] = []
    agent_traces: list[AgentTrace] = []
    file_lookup = {changed.file_path: changed for changed in task.changed_files}

    for hit in candidate_hits[:5]:
        changed_file = file_lookup.get(hit.file_path)
        if changed_file is None:
            continue

        hit_findings, hit_traces = run_stage2_agents(task, hit, changed_file, llm_client)
        findings.extend(hit_findings)
        agent_traces.extend(hit_traces)

    return findings, agent_traces


def run_stage2_agents(
    task: ReviewTask,
    hit: IssueHit,
    changed_file: ChangedFile,
    llm_client: LLMClient,
) -> tuple[list[ReviewFinding], list[AgentTrace]]:
    diff_context = select_review_context(
        diff_hunks=changed_file.diff_hunks,
        file_content=changed_file.full_file_content or "",
        use_full_file=bool(changed_file.full_file_content),
    )
    original_code_snippet = hit.original_code_snippet or extract_code_snippet(changed_file, hit.line_number)
    inspector_prompt = build_inspector_prompt(
        review_commit_sha=task.review_commit_sha,
        file_path=hit.file_path,
        diff_context=diff_context,
        candidate_summary=hit.message,
        evidence=hit.evidence,
        original_code_snippet=original_code_snippet,
    )

    try:
        inspector_payload = llm_client.review_findings(inspector_prompt)
    except Exception:  # noqa: BLE001
        return [], []

    traces = [
        AgentTrace(
            agent_role="inspector",
            model_name=task.selected_model or "unknown",
            prompt_version=PROMPT_VERSION,
            input_payload={
                "file_path": hit.file_path,
                "candidate_summary": hit.message,
                "evidence": hit.evidence,
            },
            raw_response=inspector_payload,
            parsed_output=inspector_payload,
        )
    ]
    inspector_findings = validate_llm_payload(inspector_payload, {hit.file_path}, task.review_commit_sha)
    if not inspector_findings:
        inspector_findings = salvage_fallback_findings(
            payload=inspector_payload,
            hit=hit,
            changed_file=changed_file,
            review_commit_sha=task.review_commit_sha,
        )
        if not inspector_findings:
            return [], traces

    merged_findings: list[ReviewFinding] = []
    for inspector_finding in inspector_findings:
        fixer_prompt = build_fixer_prompt(
            review_commit_sha=task.review_commit_sha,
            file_path=inspector_finding.file_path,
            diff_context=diff_context,
            inspector_summary=inspector_payload.get("summary", ""),
            issue_title=inspector_finding.issue_title,
            issue_detail=inspector_finding.issue_detail,
            fix_intent=inspector_finding.fix_intent or inspector_finding.fix_strategy,
            original_code_snippet=inspector_finding.original_code_snippet,
        )
        try:
            fixer_payload = llm_client.review_findings(fixer_prompt)
        except Exception:  # noqa: BLE001
            merged_findings.append(inspector_finding.model_copy(update={"suggested_code": ""}))
            continue

        traces.append(
            AgentTrace(
                agent_role="fixer",
                model_name=task.selected_model or "unknown",
                prompt_version=PROMPT_VERSION,
                input_payload={
                    "file_path": inspector_finding.file_path,
                    "issue_title": inspector_finding.issue_title,
                    "fix_intent": inspector_finding.fix_intent or inspector_finding.fix_strategy,
                },
                raw_response=fixer_payload,
                parsed_output=fixer_payload,
            )
        )
        fixer_findings = validate_llm_payload(fixer_payload, {hit.file_path}, task.review_commit_sha)
        if fixer_findings:
            best_fix = fixer_findings[0]
            merged_findings.append(
                inspector_finding.model_copy(
                    update={
                        "fix_strategy": best_fix.fix_strategy or inspector_finding.fix_strategy,
                        "fix_intent": inspector_finding.fix_intent or inspector_finding.fix_strategy,
                        "suggested_code": best_fix.suggested_code,
                    }
                )
            )
            continue

        salvaged_fixes = salvage_partial_structured_findings(
            payload=fixer_payload,
            hit=hit,
            changed_file=changed_file,
            review_commit_sha=task.review_commit_sha,
            fallback_finding=inspector_finding,
        )
        if salvaged_fixes:
            best_fix = salvaged_fixes[0]
            merged_findings.append(
                inspector_finding.model_copy(
                    update={
                        "fix_strategy": best_fix.fix_strategy or inspector_finding.fix_strategy,
                        "fix_intent": best_fix.fix_intent or inspector_finding.fix_intent or inspector_finding.fix_strategy,
                        "suggested_code": best_fix.suggested_code,
                    }
                )
            )
            continue

        merged_findings.append(inspector_finding.model_copy(update={"suggested_code": ""}))

    return merged_findings, traces


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
                original_code_snippet=extract_code_snippet(changed_file, line_number),
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
        fix_intent="Add the minimal guard or correction required to address this issue.",
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
                fix_intent="Apply a focused correction that directly addresses the described defect.",
                suggested_code="",
                original_code_snippet=snippet,
            )
        )
    return findings


def salvage_fallback_findings(
    payload: dict,
    hit: IssueHit,
    changed_file: ChangedFile,
    review_commit_sha: str,
) -> list[ReviewFinding]:
    findings = salvage_partial_structured_findings(
        payload=payload,
        hit=hit,
        changed_file=changed_file,
        review_commit_sha=review_commit_sha,
    )
    if findings:
        return findings
    return salvage_string_findings(
        payload=payload,
        hit=hit,
        changed_file=changed_file,
        review_commit_sha=review_commit_sha,
    )


def salvage_partial_structured_findings(
    payload: dict,
    hit: IssueHit,
    changed_file: ChangedFile,
    review_commit_sha: str,
    fallback_finding: ReviewFinding | None = None,
) -> list[ReviewFinding]:
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        return []

    default_file_path = fallback_finding.file_path if fallback_finding else hit.file_path
    default_line_number = fallback_finding.line_number if fallback_finding else hit.line_number
    default_end_line_number = fallback_finding.end_line_number if fallback_finding else (hit.end_line_number or hit.line_number)
    default_risk_level = fallback_finding.risk_level if fallback_finding else hit.severity
    default_confidence = fallback_finding.confidence if fallback_finding else 0.6
    default_issue_title = fallback_finding.issue_title if fallback_finding else hit.message
    default_issue_detail = fallback_finding.issue_detail if fallback_finding else hit.evidence
    default_why_it_matters = fallback_finding.why_it_matters if fallback_finding else hit.evidence
    default_fix_strategy = (
        fallback_finding.fix_strategy
        if fallback_finding
        else "Review the LLM finding and apply the necessary guard or correction."
    )
    default_fix_intent = (
        fallback_finding.fix_intent
        if fallback_finding
        else "Apply a focused correction that directly addresses the described defect."
    )
    default_original_snippet = (
        fallback_finding.original_code_snippet
        if fallback_finding
        else extract_code_snippet(changed_file, default_line_number)
    )

    findings: list[ReviewFinding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict", "confirm")).strip().lower()
        if verdict == "reject" and not should_salvage_rejected_finding(hit, item):
            continue

        file_path = item.get("file_path") or default_file_path
        if file_path != default_file_path:
            continue

        issue_detail = text_or_default(item.get("issue_detail"), payload.get("summary", ""), default_issue_detail)
        issue_title = text_or_default(item.get("issue_title"), derive_string_finding_title(issue_detail), default_issue_title)
        why_it_matters = text_or_default(item.get("why_it_matters"), issue_detail, default_why_it_matters)
        fix_strategy = text_or_default(item.get("suggestion_rationale"), item.get("fix_strategy"), default_fix_strategy)
        fix_intent = text_or_default(item.get("fix_intent"), fix_strategy, default_fix_intent)
        original_code_snippet = text_or_default(item.get("original_code_snippet"), "", default_original_snippet)
        suggested_code = text_or_default(item.get("suggested_code"), "", "")
        if not any(
            value.strip()
            for value in (
                issue_title,
                issue_detail,
                why_it_matters,
                fix_strategy,
                fix_intent,
                suggested_code,
            )
        ):
            continue

        line_number = infer_line_number(
            changed_file=changed_file,
            raw_line_number=item.get("line_number"),
            original_code_snippet=original_code_snippet,
            default_line_number=default_line_number,
        )
        end_line_number = coerce_positive_int(item.get("end_line_number")) or default_end_line_number
        if end_line_number < line_number:
            end_line_number = line_number

        finding = ReviewFinding(
            file_path=file_path,
            line_number=line_number,
            end_line_number=end_line_number,
            commit_sha=review_commit_sha,
            risk_level=text_or_default(item.get("risk_level"), "", default_risk_level),
            confidence=coerce_confidence(item.get("confidence"), default_confidence),
            issue_title=issue_title,
            issue_detail=issue_detail,
            why_it_matters=why_it_matters,
            fix_strategy=fix_strategy,
            fix_intent=fix_intent,
            suggested_code=suggested_code,
            original_code_snippet=original_code_snippet,
        )
        if finding.suggested_code and not suggestion_matches_confirmed_issue(finding):
            finding = finding.model_copy(update={"suggested_code": ""})
        findings.append(finding)

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
        return "未发现高置信正确性缺陷，检查通过。", "low"

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
        lines = hunk.splitlines()
        if not lines or not lines[0].startswith("@@"):
            continue

        parts = lines[0].split()
        if len(parts) < 3 or not parts[2].startswith("+"):
            continue

        current_line = int(parts[2].split(",")[0][1:])
        for line in lines[1:]:
            if line.startswith("+") and not line.startswith("+++"):
                return current_line
            if line.startswith("-") and not line.startswith("---"):
                continue
            current_line += 1
    return 1


def text_or_default(*values: object) -> str:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return ""


def coerce_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        if parsed > 0:
            return parsed
    return None


def coerce_confidence(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def infer_line_number(
    changed_file: ChangedFile,
    raw_line_number: object,
    original_code_snippet: str,
    default_line_number: int,
) -> int:
    line_number = coerce_positive_int(raw_line_number)
    if line_number is not None:
        return line_number

    snippet = original_code_snippet.strip()
    if snippet and changed_file.full_file_content:
        for index, line in enumerate(changed_file.full_file_content.splitlines(), start=1):
            if line.strip() == snippet:
                return index

    return default_line_number


def should_salvage_rejected_finding(hit: IssueHit, item: dict) -> bool:
    if hit.rule_id != "llm.full-review-fallback":
        return False

    return any(
        isinstance(value, str) and value.strip()
        for value in (
            item.get("issue_title"),
            item.get("issue_detail"),
            item.get("why_it_matters"),
            item.get("fix_intent"),
            item.get("suggestion_rationale"),
            item.get("suggested_code"),
        )
    )
