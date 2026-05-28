from app.review.models import IssueHit, ReviewTask


def test_review_task_binds_review_commit_sha():
    """
    Test that ReviewTask correctly binds review_commit_sha.

    文档缺陷标注：
    1. PLAN.md Task 2 测试文件名为 test_orchestrator.py，但测试内容是模型基本属性，应该叫 test_models.py
    2. PLAN.md Task 2 只定义了 ReviewTask 和 IssueHit，但缺少 SPEC.md 中定义的其他核心模型：
       ChangedFile, ReviewFinding, ReviewResult, RenderedComment
    """
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

    assert task.review_commit_sha == hit.commit_sha