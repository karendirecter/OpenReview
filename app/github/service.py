import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from json import JSONDecodeError, loads
from pathlib import PurePosixPath
from re import match
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from github import Auth, Github, GithubIntegration
from github.GithubException import GithubException
from github.PullRequest import PullRequest

from app.config import Settings
from app.github.models import IssueCommentPayload
from app.llm.base import LLMClient
from app.llm.openai_compatible import OpenAICompatibleClient
from app.persistence.models import AgentTraceCreate, ReviewRunCreate, ReviewRunUpdate
from app.persistence.repository import ReviewRunRepository
from app.review.models import ChangedFile, RenderedComment, ReviewTask
from app.review.orchestrator import review_pull_request
from app.review.queue import PullRequestKey, ReviewQueueManager
from app.review.rendering import render_review_comments

LOGGER = logging.getLogger(__name__)


@dataclass
class PullRequestContext:
    github: Github
    pull_request: PullRequest


def detect_language(file_path: str) -> str | None:
    suffix = PurePosixPath(file_path).suffix.lower()
    if suffix == ".py":
        return "python"
    return None


def split_diff_hunks(patch: str) -> list[str]:
    hunks: list[str] = []
    current: list[str] = []

    for line in patch.splitlines():
        if line.startswith("@@"):
            if current:
                hunks.append("\n".join(current))
                current = []
        current.append(line)

    if current:
        hunks.append("\n".join(current))

    return hunks


def build_patch_position_mapping(patch: str) -> dict[int, int]:
    mapping: dict[int, int] = {}

    for hunk in split_diff_hunks(patch):
        header = hunk.splitlines()[0]
        header_match = match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", header)
        if header_match is None:
            continue

        current_line = int(header_match.group(1))
        position = 0
        for raw_line in hunk.splitlines()[1:]:
            position += 1
            if raw_line.startswith("+") and not raw_line.startswith("+++"):
                mapping[current_line] = position
                current_line += 1
                continue
            if raw_line.startswith("-") and not raw_line.startswith("---"):
                continue
            current_line += 1

    return mapping


def build_commentable_line_ranges(diff_hunks: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []

    for hunk in diff_hunks:
        lines = hunk.splitlines()
        if not lines:
            continue

        header_match = match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", lines[0])
        if header_match is None:
            continue

        start = int(header_match.group(1))
        length = int(header_match.group(2) or "1")
        if length <= 0:
            continue

        ranges.append((start, start + length - 1))

    return ranges


def resolve_comment_line_range(
    changed_file: ChangedFile,
    line_number: int,
    end_line_number: int | None,
) -> tuple[int, int] | None:
    target_end = end_line_number or line_number

    for start, end in build_commentable_line_ranges(changed_file.diff_hunks):
        if not (start <= line_number <= end):
            continue
        if line_number <= target_end <= end:
            return line_number, target_end
        return line_number, line_number

    return None


class GitHubReviewService:
    def __init__(
        self,
        settings: Settings,
        github_client_factory: Callable[[], Github] | None = None,
        llm_client: LLMClient | None = None,
        review_run_repository: ReviewRunRepository | None = None,
        review_queue: ReviewQueueManager | None = None,
    ) -> None:
        self.settings = settings
        self._github_client_factory = github_client_factory or self._build_installation_client
        self._llm_client = llm_client or OpenAICompatibleClient.from_settings(settings)
        self._review_run_repository = review_run_repository
        if self._review_run_repository is None and hasattr(settings, "review_db_path"):
            self._review_run_repository = ReviewRunRepository.for_sqlite(settings.review_db_path)
        self._review_queue = review_queue or ReviewQueueManager(
            worker=self.process_review_run,
            max_workers=max(1, getattr(settings, "review_worker_threads", 2)),
        )
        self._superseded_run_ids: set[str] = set()
        self._superseded_lock = Lock()

    def process_issue_comment(self, payload_dict: dict[str, Any]) -> None:
        payload = IssueCommentPayload.model_validate(payload_dict)
        task: ReviewTask | None = None

        try:
            context = self._load_pull_request_context(payload)
            task = self._build_review_task(payload, context.pull_request)
            self._create_review_run(task, status="running")
            self._execute_review_task(task, context)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("GitHub review processing failed")
            self._fail_review_run(task, str(exc))
            self._post_failure_comment(payload, str(exc))
            raise
        finally:
            if task is not None:
                self._clear_superseded(task.review_run_id)

    def enqueue_issue_comment(self, payload_dict: dict[str, Any]) -> str:
        payload = IssueCommentPayload.model_validate(payload_dict)
        context = self._load_pull_request_context(payload)
        task = self._build_review_task(payload, context.pull_request)
        self._cancel_queued_runs_for_pr(task)
        self._mark_running_runs_superseded(task)
        self._create_review_run(task, status="queued")
        self._review_queue.enqueue(task.review_run_id, self._pull_request_key(task))
        return task.review_run_id

    def process_review_run(self, review_run_id: str) -> None:
        if self._review_run_repository is None:
            raise RuntimeError("review run repository is not configured")

        record = self._review_run_repository.get_run(review_run_id)
        task = ReviewTask.model_validate(record.task_payload)
        try:
            if record.status == "cancelled":
                return

            context = self._load_pull_request_context_for_task(task)
            if self._is_pull_request_stale(context.pull_request, task.review_commit_sha):
                self._mark_run_stale(task, "PR head changed before this queued review started.")
                return

            self._review_run_repository.update_run(task.review_run_id, ReviewRunUpdate(status="running"))
            if self._should_cancel_run(task.review_run_id):
                self._cancel_run(task.review_run_id, "Superseded by a newer /review request for this PR.")
                return

            self._execute_review_task(task, context)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Queued GitHub review processing failed")
            self._fail_review_run(task, str(exc))
            self._post_failure_comment_for_task(task, str(exc))
        finally:
            self._clear_superseded(task.review_run_id)

    def recover_pending_runs(self) -> None:
        if self._review_run_repository is None:
            return

        pending_runs = self._review_run_repository.list_runs_by_status(("queued", "running"), limit=500)
        latest_by_pr: dict[PullRequestKey, tuple[Any, ReviewTask]] = {}

        for record in pending_runs:
            task = ReviewTask.model_validate(record.task_payload)
            pr_key = self._pull_request_key(task)
            if pr_key in latest_by_pr:
                self._cancel_run(record.review_run_id, "Superseded during queue recovery after process restart.")
                continue
            latest_by_pr[pr_key] = (record, task)

        for record, task in latest_by_pr.values():
            if record.status == "running":
                self._review_run_repository.update_run(
                    task.review_run_id,
                    ReviewRunUpdate(status="queued"),
                )
            self._review_queue.enqueue(task.review_run_id, self._pull_request_key(task))

    def _build_installation_client(self) -> Github:
        auth = Auth.AppAuth(self.settings.github_app_id, self.settings.github_private_key)
        integration = GithubIntegration(auth=auth)
        return integration.get_github_for_installation(int(self.settings.github_installation_id))

    def _load_pull_request_context(self, payload: IssueCommentPayload) -> PullRequestContext:
        github = self._github_client_factory()
        repo = github.get_repo(payload.repository.full_name)
        pull_request = repo.get_pull(payload.issue.number)
        return PullRequestContext(github=github, pull_request=pull_request)

    def _build_review_task(self, payload: IssueCommentPayload, pull_request: PullRequest) -> ReviewTask:
        changed_files: list[ChangedFile] = []

        for changed in pull_request.get_files():
            patch = changed.patch or ""
            if not patch:
                continue

            changed_files.append(
                ChangedFile(
                    file_path=changed.filename,
                    language=detect_language(changed.filename),
                    status=changed.status,
                    diff_hunks=split_diff_hunks(patch),
                    full_file_content=self._load_file_content(pull_request, changed.filename, changed.status),
                    position_mapping=build_patch_position_mapping(patch),
                )
            )

        return ReviewTask(
            review_run_id=f"run-{uuid4().hex}",
            repo_owner=payload.repository.owner.login,
            repo_name=payload.repository.name,
            pr_number=payload.issue.number,
            base_sha=pull_request.base.sha,
            head_sha=pull_request.head.sha,
            review_commit_sha=pull_request.head.sha,
            selected_model=self.settings.llm_model,
            trigger_type="command",
            trigger_comment_id=payload.comment.id,
            changed_files=changed_files,
        )

    def _load_file_content(self, pull_request: PullRequest, file_path: str, status: str) -> str | None:
        if status == "removed":
            return None

        try:
            content = pull_request.head.repo.get_contents(file_path, ref=pull_request.head.sha)
        except GithubException:
            return None

        if isinstance(content, list):
            return None
        if not hasattr(content, "decoded_content"):
            return None

        try:
            return content.decoded_content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _publish_review(
        self,
        pull_request: PullRequest,
        comments: list[RenderedComment],
        changed_files: list[ChangedFile],
    ) -> dict[str, Any]:
        published = {"summary_posted": 0, "inline_posted": 0, "inline_skipped": 0, "inline_failed": 0}
        changed_file_lookup = {item.file_path: item for item in changed_files}

        for comment in comments:
            if comment.comment_type == "summary":
                pull_request.create_issue_comment(comment.body)
                published["summary_posted"] += 1
                continue

            if comment.file_path is None or comment.line_number is None:
                continue

            changed_file = changed_file_lookup.get(comment.file_path)
            if changed_file is None:
                LOGGER.warning("Skipping inline review comment for unknown file path: %s", comment.file_path)
                published["inline_skipped"] += 1
                continue

            resolved_range = resolve_comment_line_range(changed_file, comment.line_number, comment.end_line_number)
            if resolved_range is None:
                LOGGER.warning(
                    "Skipping inline review comment outside diff context for %s:%s-%s",
                    comment.file_path,
                    comment.line_number,
                    comment.end_line_number or comment.line_number,
                )
                published["inline_skipped"] += 1
                continue

            start_line, end_line = resolved_range

            kwargs: dict[str, Any] = {
                "body": comment.body,
                "commit": comment.commit_sha,
                "path": comment.file_path,
                "line": end_line,
                "side": comment.side or "RIGHT",
            }
            if end_line > start_line:
                kwargs["start_line"] = start_line
                kwargs["start_side"] = comment.side or "RIGHT"

            try:
                pull_request.create_review_comment(**kwargs)
            except GithubException as exc:
                LOGGER.warning(
                    "Failed to publish inline review comment for %s:%s-%s: %s",
                    comment.file_path,
                    start_line,
                    end_line,
                    exc.data if hasattr(exc, "data") else str(exc),
                )
                published["inline_failed"] += 1
                continue
            published["inline_posted"] += 1

        return published

    def _post_failure_comment(self, payload: IssueCommentPayload, error_message: str) -> None:
        try:
            github = self._github_client_factory()
            repo = github.get_repo(payload.repository.full_name)
            pull_request = repo.get_pull(payload.issue.number)
            pull_request.create_issue_comment(
                "Automated review failed.\n\n"
                f"- PR: #{payload.issue.number}\n"
                f"- Reason: `{error_message[:300]}`"
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to post review failure comment")

    def _create_review_run(self, task: ReviewTask, *, status: str = "running") -> None:
        if self._review_run_repository is None:
            return

        self._review_run_repository.create_run(
            ReviewRunCreate(
                review_run_id=task.review_run_id,
                repo_owner=task.repo_owner,
                repo_name=task.repo_name,
                pr_number=task.pr_number,
                review_commit_sha=task.review_commit_sha,
                trigger_type=task.trigger_type,
                selected_model=task.selected_model or self.settings.llm_model,
                base_url=self.settings.llm_base_url,
                status=status,
                task_payload=task.model_dump(mode="json"),
                diff_snapshot=self._build_diff_snapshot(task),
            )
        )

    def _complete_review_run(
        self,
        task: ReviewTask,
        result,
        comments: list[RenderedComment],
        github_status: dict[str, Any],
    ) -> None:
        if self._review_run_repository is None:
            return

        for trace in result.agent_traces:
            self._review_run_repository.save_agent_trace(
                AgentTraceCreate(
                    review_run_id=task.review_run_id,
                    agent_role=trace.agent_role,
                    model_name=trace.model_name,
                    prompt_version=trace.prompt_version,
                    input_payload=trace.input_payload,
                    raw_response=trace.raw_response,
                    parsed_output=trace.parsed_output,
                    latency_ms=trace.latency_ms,
                    token_usage=trace.token_usage,
                )
            )
        self._review_run_repository.update_run(
            task.review_run_id,
            ReviewRunUpdate(
                status="completed",
                summary_snapshot=result.summary,
                result_payload=result.model_dump(mode="json"),
                rendered_comments=[comment.model_dump(mode="json") for comment in comments],
                github_status=github_status,
                completed_at=datetime.now(timezone.utc),
            ),
        )

    def _fail_review_run(self, task: ReviewTask | None, error_message: str) -> None:
        if task is None or self._review_run_repository is None:
            return

        try:
            self._review_run_repository.update_run(
                task.review_run_id,
                ReviewRunUpdate(
                    status="failed",
                    summary_snapshot=error_message[:300],
                    github_status={"error": error_message[:300]},
                    completed_at=datetime.now(timezone.utc),
                ),
            )
        except KeyError:
            return

    def _build_diff_snapshot(self, task: ReviewTask) -> str:
        parts: list[str] = []
        for changed_file in task.changed_files:
            parts.append(f"### {changed_file.file_path}")
            parts.extend(changed_file.diff_hunks)
        return "\n".join(parts)

    def _load_pull_request_context_for_task(self, task: ReviewTask) -> PullRequestContext:
        github = self._github_client_factory()
        repo = github.get_repo(f"{task.repo_owner}/{task.repo_name}")
        pull_request = repo.get_pull(task.pr_number)
        return PullRequestContext(github=github, pull_request=pull_request)

    def _execute_review_task(self, task: ReviewTask, context: PullRequestContext) -> None:
        result = review_pull_request(task, llm_client=self._llm_client)
        if self._should_cancel_run(task.review_run_id):
            self._cancel_run(task.review_run_id, "Superseded by a newer /review request for this PR.")
            return

        fresh_context = self._load_pull_request_context_for_task(task)
        if self._is_pull_request_stale(fresh_context.pull_request, task.review_commit_sha):
            self._mark_run_stale(task, "PR head changed before review comments were published.")
            return

        comments = render_review_comments(result)
        github_status = self._publish_review(fresh_context.pull_request, comments, task.changed_files)
        self._complete_review_run(task, result, comments, github_status)

    def _pull_request_key(self, task: ReviewTask) -> PullRequestKey:
        return PullRequestKey(
            repo_owner=task.repo_owner,
            repo_name=task.repo_name,
            pr_number=task.pr_number,
        )

    def _cancel_queued_runs_for_pr(self, task: ReviewTask) -> None:
        if self._review_run_repository is None:
            return

        pr_key = self._pull_request_key(task)
        cancelled_run_ids = set(self._review_queue.cancel_pending_for_pr(pr_key))
        queued_runs = self._review_run_repository.list_runs_for_pr(
            task.repo_owner,
            task.repo_name,
            task.pr_number,
            statuses=("queued",),
            limit=50,
        )
        cancelled_run_ids.update(run.review_run_id for run in queued_runs)
        for review_run_id in cancelled_run_ids:
            self._cancel_run(review_run_id, "Superseded by a newer /review request for this PR.")

    def _mark_running_runs_superseded(self, task: ReviewTask) -> None:
        if self._review_run_repository is None:
            return

        running_runs = self._review_run_repository.list_runs_for_pr(
            task.repo_owner,
            task.repo_name,
            task.pr_number,
            statuses=("running",),
            limit=50,
        )
        if not running_runs:
            return

        with self._superseded_lock:
            self._superseded_run_ids.update(run.review_run_id for run in running_runs)

    def _should_cancel_run(self, review_run_id: str) -> bool:
        with self._superseded_lock:
            return review_run_id in self._superseded_run_ids

    def _clear_superseded(self, review_run_id: str) -> None:
        with self._superseded_lock:
            self._superseded_run_ids.discard(review_run_id)

    def _cancel_run(self, review_run_id: str, reason: str) -> None:
        if self._review_run_repository is None:
            return

        self._review_run_repository.update_run(
            review_run_id,
            ReviewRunUpdate(
                status="cancelled",
                summary_snapshot=reason,
                github_status={"cancelled": reason},
                completed_at=datetime.now(timezone.utc),
            ),
        )

    def _mark_run_stale(self, task: ReviewTask, reason: str) -> None:
        if self._review_run_repository is None:
            return

        self._review_run_repository.update_run(
            task.review_run_id,
            ReviewRunUpdate(
                status="stale",
                summary_snapshot=reason,
                github_status={"stale": reason},
                completed_at=datetime.now(timezone.utc),
            ),
        )

    def _is_pull_request_stale(self, pull_request: PullRequest, review_commit_sha: str) -> bool:
        return pull_request.head.sha != review_commit_sha

    def _post_failure_comment_for_task(self, task: ReviewTask, error_message: str) -> None:
        try:
            context = self._load_pull_request_context_for_task(task)
            context.pull_request.create_issue_comment(
                "Queued automated review failed.\n\n"
                f"- PR: #{task.pr_number}\n"
                f"- Reason: `{error_message[:300]}`"
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to post queued review failure comment")


def decode_json_body(body: bytes) -> dict[str, Any]:
    try:
        return loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise ValueError("invalid webhook body") from exc
