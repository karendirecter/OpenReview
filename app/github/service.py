import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from json import JSONDecodeError, loads
from pathlib import PurePosixPath
from re import match
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


class GitHubReviewService:
    def __init__(
        self,
        settings: Settings,
        github_client_factory: Callable[[], Github] | None = None,
        llm_client: LLMClient | None = None,
        review_run_repository: ReviewRunRepository | None = None,
    ) -> None:
        self.settings = settings
        self._github_client_factory = github_client_factory or self._build_installation_client
        self._llm_client = llm_client or OpenAICompatibleClient.from_settings(settings)
        self._review_run_repository = review_run_repository
        if self._review_run_repository is None and hasattr(settings, "review_db_path"):
            self._review_run_repository = ReviewRunRepository.for_sqlite(settings.review_db_path)

    def process_issue_comment(self, payload_dict: dict[str, Any]) -> None:
        payload = IssueCommentPayload.model_validate(payload_dict)
        task: ReviewTask | None = None

        try:
            context = self._load_pull_request_context(payload)
            task = self._build_review_task(payload, context.pull_request)
            self._create_review_run(task)
            result = review_pull_request(task, llm_client=self._llm_client)
            comments = render_review_comments(result)
            github_status = self._publish_review(context.pull_request, comments)
            self._complete_review_run(task, result, comments, github_status)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("GitHub review processing failed")
            self._fail_review_run(task, str(exc))
            self._post_failure_comment(payload, str(exc))
            raise

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

    def _publish_review(self, pull_request: PullRequest, comments: list[RenderedComment]) -> dict[str, Any]:
        published = {"summary_posted": 0, "inline_posted": 0}

        for comment in comments:
            if comment.comment_type == "summary":
                pull_request.create_issue_comment(comment.body)
                published["summary_posted"] += 1
                continue

            if comment.file_path is None or comment.line_number is None:
                continue

            kwargs: dict[str, Any] = {
                "body": comment.body,
                "commit": comment.commit_sha,
                "path": comment.file_path,
                "line": comment.end_line_number or comment.line_number,
                "side": comment.side or "RIGHT",
            }
            if comment.end_line_number and comment.end_line_number > comment.line_number:
                kwargs["start_line"] = comment.line_number
                kwargs["start_side"] = comment.side or "RIGHT"

            pull_request.create_review_comment(**kwargs)
            published["inline_posted"] += 1

        return published

    def _post_failure_comment(self, payload: IssueCommentPayload, error_message: str) -> None:
        try:
            github = self._github_client_factory()
            repo = github.get_repo(payload.repository.full_name)
            pull_request = repo.get_pull(payload.issue.number)
            pull_request.create_issue_comment(
                "自动审查执行失败。\n\n"
                f"- PR: #{payload.issue.number}\n"
                f"- 原因: `{error_message[:300]}`"
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to post review failure comment")

    def _create_review_run(self, task: ReviewTask) -> None:
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
                status="running",
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


def decode_json_body(body: bytes) -> dict[str, Any]:
    try:
        return loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise ValueError("invalid webhook body") from exc
