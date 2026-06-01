from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Callable


@dataclass(frozen=True)
class PullRequestKey:
    repo_owner: str
    repo_name: str
    pr_number: int


@dataclass(frozen=True)
class QueuedReview:
    review_run_id: str
    pr_key: PullRequestKey


class ReviewQueueManager:
    def __init__(self, worker: Callable[[str], None], max_workers: int = 2) -> None:
        self._worker = worker
        self._max_workers = max(1, max_workers)
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="review-worker")
        self._lock = Lock()
        self._pending: list[QueuedReview] = []
        self._active_prs: set[PullRequestKey] = set()
        self._known_review_run_ids: set[str] = set()
        self._shutdown = False

    def enqueue(self, review_run_id: str, pr_key: PullRequestKey) -> None:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("review queue is shut down")
            if review_run_id in self._known_review_run_ids:
                return
            self._pending.append(QueuedReview(review_run_id=review_run_id, pr_key=pr_key))
            self._known_review_run_ids.add(review_run_id)
            self._dispatch_locked()

    def cancel_pending_for_pr(self, pr_key: PullRequestKey) -> list[str]:
        with self._lock:
            cancelled = [item.review_run_id for item in self._pending if item.pr_key == pr_key]
            self._pending = [item for item in self._pending if item.pr_key != pr_key]
            for review_run_id in cancelled:
                self._known_review_run_ids.discard(review_run_id)
            return cancelled

    def shutdown(self, *, wait: bool = True) -> None:
        with self._lock:
            self._shutdown = True
        self._executor.shutdown(wait=wait)

    def _dispatch_locked(self) -> None:
        while len(self._active_prs) < self._max_workers:
            next_index = self._next_runnable_index()
            if next_index is None:
                return
            item = self._pending.pop(next_index)
            self._active_prs.add(item.pr_key)
            self._executor.submit(self._run_item, item)

    def _next_runnable_index(self) -> int | None:
        for index, item in enumerate(self._pending):
            if item.pr_key not in self._active_prs:
                return index
        return None

    def _run_item(self, item: QueuedReview) -> None:
        try:
            self._worker(item.review_run_id)
        finally:
            with self._lock:
                self._active_prs.discard(item.pr_key)
                self._known_review_run_ids.discard(item.review_run_id)
                self._dispatch_locked()
