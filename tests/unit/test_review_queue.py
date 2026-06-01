from threading import Event

from app.review.queue import PullRequestKey, ReviewQueueManager


def test_queue_runs_different_prs_in_parallel_but_serializes_same_pr():
    started = {
        "run-1": Event(),
        "run-2": Event(),
        "run-3": Event(),
    }
    release = {
        "run-1": Event(),
        "run-2": Event(),
        "run-3": Event(),
    }

    def worker(review_run_id: str) -> None:
        started[review_run_id].set()
        assert release[review_run_id].wait(2)

    queue = ReviewQueueManager(worker=worker, max_workers=2)
    pr_one = PullRequestKey("octo", "demo", 1)
    pr_two = PullRequestKey("octo", "demo", 2)

    queue.enqueue("run-1", pr_one)
    queue.enqueue("run-2", pr_one)
    queue.enqueue("run-3", pr_two)

    assert started["run-1"].wait(1)
    assert started["run-3"].wait(1)
    assert not started["run-2"].wait(0.2)

    release["run-1"].set()

    assert started["run-2"].wait(1)

    release["run-2"].set()
    release["run-3"].set()
    queue.shutdown(wait=True)


def test_queue_can_cancel_pending_runs_for_pr():
    started = {"run-1": Event(), "run-2": Event()}
    release = {"run-1": Event(), "run-2": Event()}

    def worker(review_run_id: str) -> None:
        started[review_run_id].set()
        assert release[review_run_id].wait(2)

    queue = ReviewQueueManager(worker=worker, max_workers=1)
    pr_key = PullRequestKey("octo", "demo", 1)

    queue.enqueue("run-1", pr_key)
    queue.enqueue("run-2", pr_key)

    assert started["run-1"].wait(1)
    cancelled = queue.cancel_pending_for_pr(pr_key)

    assert cancelled == ["run-2"]

    release["run-1"].set()
    assert not started["run-2"].wait(0.2)
    queue.shutdown(wait=True)
