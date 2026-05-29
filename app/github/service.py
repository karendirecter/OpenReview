import logging
from dataclasses import dataclass
from json import JSONDecodeError, loads
from pathlib import PurePosixPath
from re import match
from typing import Any, Callable

from github import Auth, Github, GithubIntegration
from github.GithubException import GithubException
from github.PullRequest import PullRequest

from app.config import Settings
from app.github.models import IssueCommentPayload
from app.llm.base import LLMClient
from app.llm.openai_compatible import OpenAICompatibleClient
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
    ) -> None:
        self.settings = settings
        self._github_client_factory = github_client_factory or self._build_installation_client
        self._llm_client = llm_client or OpenAICompatibleClient.from_settings(settings)

    def process_issue_comment(self, payload_dict: dict[str, Any]) -> None:
        payload = IssueCommentPayload.model_validate(payload_dict)

        try:
            context = self._load_pull_request_context(payload)
            task = self._build_review_task(payload, context.pull_request)
            result = review_pull_request(task, llm_client=self._llm_client)
            self._publish_review(context.pull_request, render_review_comments(result))
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("GitHub review processing failed")
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
            repo_owner=payload.repository.owner.login,
            repo_name=payload.repository.name,
            pr_number=payload.issue.number,
            base_sha=pull_request.base.sha,
            head_sha=pull_request.head.sha,
            review_commit_sha=pull_request.head.sha,
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

    def _publish_review(self, pull_request: PullRequest, comments: list[RenderedComment]) -> None:
        for comment in comments:
            if comment.comment_type == "summary":
                pull_request.create_issue_comment(comment.body)
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

    def _post_failure_comment(self, payload: IssueCommentPayload, error_message: str) -> None:
        try:
            github = self._github_client_factory()
            repo = github.get_repo(payload.repository.full_name)
            pull_request = repo.get_pull(payload.issue.number)
            pull_request.create_issue_comment(
                "自动评审执行失败。\n\n"
                f"- PR: #{payload.issue.number}\n"
                f"- 原因: `{error_message[:300]}`"
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to post review failure comment")


def decode_json_body(body: bytes) -> dict[str, Any]:
    try:
        return loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise ValueError("invalid webhook body") from exc
