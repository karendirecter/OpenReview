from app.review.models import ReviewTask


def build_local_task(repo_owner: str, repo_name: str, pr_number: int, review_commit_sha: str) -> ReviewTask:
    return ReviewTask(
        repo_owner=repo_owner,
        repo_name=repo_name,
        pr_number=pr_number,
        base_sha=review_commit_sha,
        head_sha=review_commit_sha,
        review_commit_sha=review_commit_sha,
        trigger_type="command",
        changed_files=[],
    )
