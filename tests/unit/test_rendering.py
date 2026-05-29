from app.review.models import ReviewFinding
from app.review.rendering import render_inline_comment


def test_render_inline_comment_wraps_suggestion_block():
    finding = ReviewFinding(
        file_path="app/api.py",
        line_number=18,
        end_line_number=19,
        commit_sha="head123",
        risk_level="high",
        confidence=0.94,
        issue_title="Blocking I/O in async route",
        issue_detail="requests.get blocks the event loop.",
        why_it_matters="This can degrade latency under concurrency.",
        fix_strategy="Use an async HTTP client.",
        suggested_code="async with httpx.AsyncClient() as client:\n    await client.get(url)",
        original_code_snippet="requests.get(url)",
    )

    body = render_inline_comment(finding)

    assert "```suggestion" in body
    assert "Blocking I/O in async route" in body
