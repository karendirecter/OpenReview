PROMPT_VERSION = "task19-v1"


def build_inspector_prompt(
    review_commit_sha: str,
    file_path: str,
    diff_context: str,
    candidate_summary: str,
    evidence: str,
    original_code_snippet: str,
) -> str:
    return f"""
You are the Inspector Agent for code correctness review.
Your job is to confirm, reject, or refine one candidate issue.
Review commit SHA: {review_commit_sha}
File: {file_path}
Candidate issue: {candidate_summary}
Rule evidence: {evidence}
Original code snippet:
{original_code_snippet}

Diff and context:
{diff_context}

Return strict JSON with keys: "summary", "findings".
Each finding must include:
- file_path
- line_number
- end_line_number
- risk_level
- verdict
- issue_title
- issue_detail
- why_it_matters
- fix_intent
- suggestion_rationale
- suggested_code
- original_code_snippet
- confidence

If the issue is real, keep suggested_code empty and describe the intended fix in fix_intent.
Do not return extra text.
""".strip()


def build_fixer_prompt(
    review_commit_sha: str,
    file_path: str,
    diff_context: str,
    inspector_summary: str,
    issue_title: str,
    issue_detail: str,
    fix_intent: str,
    original_code_snippet: str,
) -> str:
    return f"""
You are the Fixer Agent for code correctness review.
You only write a minimal code suggestion for a confirmed issue.
Review commit SHA: {review_commit_sha}
File: {file_path}
Inspector summary: {inspector_summary}
Confirmed issue: {issue_title}
Issue detail: {issue_detail}
Fix intent: {fix_intent}
Original code snippet:
{original_code_snippet}

Diff and context:
{diff_context}

Return strict JSON with keys: "summary", "findings".
Each finding must include the same schema fields as the inspector output.
Use the same file_path and line range.
Only provide a suggestion if it directly fixes the confirmed issue.
Do not add unrelated imports, logging, refactors, or style-only edits.
If no reliable suggestion can be produced, return suggested_code as an empty string.
Do not return extra text.
""".strip()


def build_review_prompt(review_commit_sha: str, file_path: str, diff_context: str, candidate_summary: str) -> str:
    return build_inspector_prompt(
        review_commit_sha=review_commit_sha,
        file_path=file_path,
        diff_context=diff_context,
        candidate_summary=candidate_summary,
        evidence=candidate_summary,
        original_code_snippet="",
    )
