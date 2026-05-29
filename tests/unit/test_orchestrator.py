import pytest

from app.review.models import ReviewTask
from app.review.orchestrator import ensure_not_stale


def test_ensure_not_stale_raises_when_head_sha_changes():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="newhead",
        review_commit_sha="oldhead",
        trigger_type="command",
        changed_files=[],
    )

    with pytest.raises(RuntimeError, match="stale review commit"):
        ensure_not_stale(task)
