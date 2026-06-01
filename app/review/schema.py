from re import findall

from pydantic import BaseModel, ValidationError

from app.review.models import ReviewFinding


class RawFinding(BaseModel):
    file_path: str
    line_number: int
    end_line_number: int | None = None
    risk_level: str = "medium"
    verdict: str = "confirm"
    issue_title: str = ""
    issue_detail: str = ""
    why_it_matters: str = ""
    fix_intent: str = ""
    suggestion_rationale: str = ""
    suggested_code: str = ""
    original_code_snippet: str = ""
    confidence: float = 0.7


def validate_llm_payload(payload: dict, allowed_files: set[str], review_commit_sha: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        return findings

    for item in raw_findings:
        try:
            raw = RawFinding.model_validate(item)
        except ValidationError:
            continue
        if raw.file_path not in allowed_files:
            continue
        if raw.verdict == "reject":
            continue
        if raw.line_number <= 0:
            continue
        if raw.end_line_number is not None and raw.end_line_number < raw.line_number:
            continue
        suggested_code = raw.suggested_code if suggestion_matches_confirmed_issue(raw) else ""
        findings.append(
            ReviewFinding(
                file_path=raw.file_path,
                line_number=raw.line_number,
                end_line_number=raw.end_line_number or raw.line_number,
                commit_sha=review_commit_sha,
                risk_level=raw.risk_level,
                confidence=raw.confidence,
                issue_title=raw.issue_title,
                issue_detail=raw.issue_detail,
                why_it_matters=raw.why_it_matters,
                fix_strategy=raw.suggestion_rationale,
                fix_intent=raw.fix_intent,
                suggested_code=suggested_code,
                original_code_snippet=raw.original_code_snippet,
            )
        )

    return findings


def suggestion_matches_confirmed_issue(finding: RawFinding | ReviewFinding) -> bool:
    suggested_code = finding.suggested_code.strip()
    if not suggested_code:
        return False

    normalized = suggested_code.lower()
    if normalized in {"import logging", "logging"} or normalized.startswith("import logging\n"):
        return False

    original_tokens = meaningful_tokens(finding.original_code_snippet)
    suggestion_tokens = meaningful_tokens(suggested_code)
    if original_tokens and original_tokens.intersection(suggestion_tokens):
        return True

    intent_tokens = meaningful_tokens(getattr(finding, "fix_intent", "")) | meaningful_tokens(finding.issue_title)
    return bool(intent_tokens.intersection(suggestion_tokens))


def meaningful_tokens(text: str) -> set[str]:
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "code",
        "line",
        "fix",
    }
    return {
        token.lower()
        for token in findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
        if len(token) > 2 and token.lower() not in stop_words
    }
