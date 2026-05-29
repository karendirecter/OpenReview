from app.review.models import IssueHit, RenderedComment, ReviewFinding, ReviewResult, ReviewTask


def test_review_task_binds_review_commit_sha():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=7,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        trigger_type="command",
        trigger_comment_id=99,
        changed_files=[],
    )

    hit = IssueHit(
        file_path="app/service.py",
        line_number=10,
        end_line_number=12,
        commit_sha="head123",
        rule_id="python.none-access",
        severity="high",
        message="Possible None dereference",
        evidence="user.profile.name",
    )

    finding = ReviewFinding(
        file_path="app/service.py",
        line_number=10,
        end_line_number=12,
        commit_sha="head123",
        risk_level="high",
        confidence=0.91,
        issue_title="Possible None dereference",
        issue_detail="user.profile may be None.",
        why_it_matters="This can crash at runtime.",
        fix_strategy="Guard the access.",
        suggested_code="if user.profile is not None:\n    name = user.profile.name",
        original_code_snippet="name = user.profile.name",
    )

    result = ReviewResult(
        review_commit_sha="head123",
        summary="1 high-risk finding",
        overall_risk="high",
        findings=[finding],
        stats={"high": 1},
        render_mode="command",
    )

    comment = RenderedComment(
        comment_type="inline",
        body="body",
        file_path="app/service.py",
        line_number=10,
        end_line_number=12,
        side="RIGHT",
        commit_sha="head123",
    )

    assert task.review_commit_sha == hit.commit_sha == result.review_commit_sha == comment.commit_sha
