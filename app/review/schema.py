from pydantic import BaseModel

from app.review.models import ReviewFinding


class RawFinding(BaseModel):
    file_path: str
    line_number: int
    end_line_number: int | None = None
    risk_level: str
    verdict: str
    issue_title: str
    issue_detail: str
    why_it_matters: str
    suggestion_rationale: str
    suggested_code: str
    original_code_snippet: str
    confidence: float


def validate_llm_payload(payload: dict, allowed_files: set[str], review_commit_sha: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    for item in payload.get("findings", []):
        raw = RawFinding.model_validate(item)
        if raw.file_path not in allowed_files:
            continue
        if raw.line_number <= 0:
            continue
        if raw.end_line_number is not None and raw.end_line_number < raw.line_number:
            continue
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
                suggested_code=raw.suggested_code,
                original_code_snippet=raw.original_code_snippet,
            )
        )

    return findings
