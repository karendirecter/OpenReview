def build_review_prompt(review_commit_sha: str, file_path: str, diff_context: str, candidate_summary: str) -> str:
    return f"""
You are reviewing code for correctness.
Review commit SHA: {review_commit_sha}
File: {file_path}
Candidate issue: {candidate_summary}
Diff and context:
{diff_context}
Return strict JSON with keys: "summary", "findings".
Do not return extra text.
""".strip()
