from app.review.models import ReviewTask


def ensure_not_stale(task: ReviewTask) -> None:
    if task.head_sha != task.review_commit_sha:
        raise RuntimeError("stale review commit")
