from types import SimpleNamespace

from github.GithubException import GithubException

from app.github.models import IssueCommentPayload
from app.persistence.models import ReviewRunCreate
from app.persistence.repository import ReviewRunRepository
from app.github.service import GitHubReviewService
from app.review.models import ChangedFile, RenderedComment


class FakeContentFile:
    def __init__(self, text: str) -> None:
        self.decoded_content = text.encode("utf-8")


class FakePullFile:
    def __init__(self, filename: str, patch: str, status: str = "modified") -> None:
        self.filename = filename
        self.patch = patch
        self.status = status


class FakeRepo:
    def __init__(self, pull_request, file_contents: dict[str, str]) -> None:
        self._pull_request = pull_request
        self._file_contents = file_contents

    def get_pull(self, number: int):
        assert number == self._pull_request.number
        return self._pull_request

    def get_contents(self, file_path: str, ref: str):
        assert ref == self._pull_request.head.sha
        return FakeContentFile(self._file_contents[file_path])


class FakePullRequest:
    def __init__(self, number: int, files: list[FakePullFile], file_contents: dict[str, str]) -> None:
        self.number = number
        self.base = SimpleNamespace(sha="base123")
        self.head = SimpleNamespace(sha="head123", repo=FakeRepo(self, file_contents))
        self._files = files
        self.issue_comments: list[str] = []
        self.inline_comments: list[dict] = []

    def get_files(self):
        return list(self._files)

    def create_issue_comment(self, body: str) -> None:
        self.issue_comments.append(body)

    def create_review_comment(self, **kwargs) -> None:
        self.inline_comments.append(kwargs)


class FailingInlinePullRequest(FakePullRequest):
    def create_review_comment(self, **kwargs) -> None:
        if kwargs["line"] == 4:
            raise GithubException(
                status=422,
                data={
                    "message": "Validation Failed",
                    "errors": [
                        {
                            "resource": "PullRequestReviewComment",
                            "code": "custom",
                            "field": "pull_request_review_thread.line",
                            "message": "could not be resolved",
                        }
                    ],
                },
            )
        super().create_review_comment(**kwargs)


class FakeGithub:
    def __init__(self, repo) -> None:
        self._repo = repo

    def get_repo(self, full_name: str):
        assert full_name == "octo/demo"
        return self._repo


class FakeQueueManager:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, object]] = []
        self.cancelled: list[object] = []

    def enqueue(self, review_run_id: str, pr_key) -> None:
        self.enqueued.append((review_run_id, pr_key))

    def cancel_pending_for_pr(self, pr_key) -> list[str]:
        self.cancelled.append(pr_key)
        return [
            review_run_id
            for review_run_id, queued_key in self.enqueued
            if queued_key == pr_key
        ]


class FakeLLMClient:
    def __init__(self, payload: dict | None = None) -> None:
        self.payload = payload or {}
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        if self.payload:
            return self.payload
        if "Inspector Agent" in prompt:
            return {
                "summary": "Found a correctness issue",
                "findings": [
                    {
                        "file_path": "app/api.py",
                        "line_number": 4,
                        "end_line_number": 4,
                        "risk_level": "high",
                        "verdict": "confirm",
                        "issue_title": "Blocking I/O in async route",
                        "issue_detail": "time.sleep blocks the event loop.",
                        "why_it_matters": "Requests will stall under load.",
                        "fix_intent": "Replace blocking call with an awaitable sleep.",
                        "suggestion_rationale": "Use an async-friendly API.",
                        "suggested_code": "",
                        "original_code_snippet": "    time.sleep(1)",
                        "confidence": 0.95,
                    }
                ],
            }
        return {
            "summary": "Generated a fix",
            "findings": [
                {
                    "file_path": "app/api.py",
                    "line_number": 4,
                    "end_line_number": 4,
                    "risk_level": "high",
                    "verdict": "confirm",
                    "issue_title": "Blocking I/O in async route",
                    "issue_detail": "time.sleep blocks the event loop.",
                    "why_it_matters": "Requests will stall under load.",
                    "fix_intent": "Replace blocking call with an awaitable sleep.",
                    "suggestion_rationale": "Use an async-friendly API.",
                    "suggested_code": "    await asyncio.sleep(1)",
                    "original_code_snippet": "    time.sleep(1)",
                    "confidence": 0.95,
                }
            ],
        }


class PartialStructuredLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        if "Inspector Agent" in prompt:
            return {
                "summary": "Found a correctness issue",
                "findings": [
                    {
                        "issue_title": "Blocking I/O in async route",
                        "issue_detail": "time.sleep blocks the event loop.",
                        "why_it_matters": "Requests will stall under load.",
                        "fix_intent": "Replace blocking call with an awaitable sleep.",
                        "suggestion_rationale": "Use an async-friendly API.",
                        "confidence": 0.95,
                    }
                ],
            }

        return {
            "summary": "Generated a fix",
            "findings": [
                {
                    "issue_title": "Blocking I/O in async route",
                    "issue_detail": "time.sleep blocks the event loop.",
                    "why_it_matters": "Requests will stall under load.",
                    "fix_intent": "Replace blocking call with an awaitable sleep.",
                    "suggestion_rationale": "Use an async-friendly API.",
                    "suggested_code": "    await asyncio.sleep(1)",
                    "confidence": 0.95,
                }
            ],
        }


class FallbackRejectingLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        if "Inspector Agent" in prompt:
            return {
                "summary": "Found one critical bug.",
                "findings": [
                    {
                        "file_path": "app/service.py",
                        "line_number": 2,
                        "end_line_number": 2,
                        "risk_level": "high",
                        "verdict": "reject",
                        "issue_title": "Missing None check for get_page_by_id return value",
                        "issue_detail": "The code dereferences a possible None return value.",
                        "why_it_matters": "This raises AttributeError at runtime.",
                        "fix_intent": "Add a guard for the missing page case.",
                        "suggestion_rationale": "Prevent the crash and return a graceful error.",
                        "suggested_code": "",
                        "original_code_snippet": "return value.id",
                        "confidence": "high",
                    }
                ],
            }

        return {
            "summary": "Generated a fix",
            "findings": [
                {
                    "issue_title": "Missing None check for get_page_by_id return value",
                    "issue_detail": "The code dereferences a possible None return value.",
                    "why_it_matters": "This raises AttributeError at runtime.",
                    "fix_intent": "Add a guard for the missing page case.",
                    "suggestion_rationale": "Prevent the crash and return a graceful error.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "confidence": 0.95,
                }
            ],
        }


def test_process_issue_comment_posts_summary_and_inline_comments():
    source = "import asyncio\nimport time\n\nasync def endpoint():\n    time.sleep(1)\n"
    patch = "@@ -2,3 +2,4 @@\n import time\n \n async def endpoint():\n+    time.sleep(1)\n"
    pr = FakePullRequest(
        number=7,
        files=[FakePullFile(filename="app/api.py", patch=patch)],
        file_contents={"app/api.py": source},
    )
    repo = FakeRepo(pr, {"app/api.py": source})
    github = FakeGithub(repo)
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=FakeLLMClient())

    service.process_issue_comment(
        {
            "action": "created",
            "comment": {"id": 9, "body": "/review"},
            "issue": {"number": 7, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/7"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    assert len(pr.issue_comments) == 1
    assert "Automated Code Review Results" in pr.issue_comments[0]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["path"] == "app/api.py"
    assert pr.inline_comments[0]["line"] == 4


def test_process_issue_comment_uses_llm_when_stage1_has_no_hits():
    source = "def run(value):\n    return value.id\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value.id\n"
    pr = FakePullRequest(
        number=8,
        files=[FakePullFile(filename="app/service.py", patch=patch)],
        file_contents={"app/service.py": source},
    )
    repo = FakeRepo(pr, {"app/service.py": source})
    github = FakeGithub(repo)
    llm_client = FakeLLMClient(
        payload={
            "summary": "Found a correctness issue",
            "findings": [
                {
                    "file_path": "app/service.py",
                    "line_number": 2,
                    "end_line_number": 2,
                    "risk_level": "high",
                    "verdict": "confirm",
                    "issue_title": "Missing fallback",
                    "issue_detail": "Returning raw value can fail.",
                    "why_it_matters": "The code raises when value is None.",
                    "fix_intent": "Guard before dereference.",
                    "suggestion_rationale": "Guard the return.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "original_code_snippet": "return value.id",
                    "confidence": 0.95,
                }
            ],
        }
    )
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=llm_client)

    service.process_issue_comment(
        {
            "action": "created",
            "comment": {"id": 10, "body": "/review"},
            "issue": {"number": 8, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/8"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    assert len(llm_client.prompts) == 2
    assert len(pr.issue_comments) == 1
    assert "Missing fallback" in pr.issue_comments[0]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["path"] == "app/service.py"


def test_process_issue_comment_reports_degraded_review_when_llm_fallback_returns_no_findings():
    source = "def run(value):\n    return value\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value\n"
    pr = FakePullRequest(
        number=9,
        files=[FakePullFile(filename="app/service.py", patch=patch)],
        file_contents={"app/service.py": source},
    )
    repo = FakeRepo(pr, {"app/service.py": source})
    github = FakeGithub(repo)
    llm_client = FakeLLMClient(payload={"summary": "No output", "findings": []})
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=llm_client)

    service.process_issue_comment(
        {
            "action": "created",
            "comment": {"id": 11, "body": "/review"},
            "issue": {"number": 9, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/9"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    assert len(llm_client.prompts) == 1
    assert len(pr.issue_comments) == 1
    assert "LLM fallback did not return any actionable findings" in pr.issue_comments[0]
    assert pr.inline_comments == []


def test_publish_review_skips_inline_comments_outside_diff_context():
    patch = "@@ -2,3 +2,4 @@\n import time\n \n async def endpoint():\n+    time.sleep(1)\n"
    changed_file = ChangedFile(
        file_path="app/api.py",
        language="python",
        status="modified",
        diff_hunks=[patch],
        full_file_content="import asyncio\nimport time\n\nasync def endpoint():\n    time.sleep(1)\n",
    )
    pr = FakePullRequest(
        number=13,
        files=[FakePullFile(filename="app/api.py", patch=patch)],
        file_contents={"app/api.py": changed_file.full_file_content or ""},
    )
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: None, llm_client=FakeLLMClient())
    comments = [
        RenderedComment(comment_type="summary", body="summary", commit_sha="head123"),
        RenderedComment(
            comment_type="inline",
            body="valid inline",
            file_path="app/api.py",
            line_number=4,
            end_line_number=4,
            side="RIGHT",
            commit_sha="head123",
        ),
        RenderedComment(
            comment_type="inline",
            body="invalid inline",
            file_path="app/api.py",
            line_number=20,
            end_line_number=20,
            side="RIGHT",
            commit_sha="head123",
        ),
    ]

    published = service._publish_review(pr, comments, [changed_file])

    assert published == {"summary_posted": 1, "inline_posted": 1, "inline_skipped": 1, "inline_failed": 0}
    assert pr.issue_comments == ["summary"]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["line"] == 4


def test_publish_review_continues_when_github_rejects_one_inline_comment():
    patch = "@@ -2,3 +2,4 @@\n import time\n \n async def endpoint():\n+    time.sleep(1)\n"
    changed_file = ChangedFile(
        file_path="app/api.py",
        language="python",
        status="modified",
        diff_hunks=[patch],
        full_file_content="import asyncio\nimport time\n\nasync def endpoint():\n    time.sleep(1)\n",
    )
    pr = FailingInlinePullRequest(
        number=14,
        files=[FakePullFile(filename="app/api.py", patch=patch)],
        file_contents={"app/api.py": changed_file.full_file_content or ""},
    )
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: None, llm_client=FakeLLMClient())
    comments = [
        RenderedComment(comment_type="summary", body="summary", commit_sha="head123"),
        RenderedComment(
            comment_type="inline",
            body="first inline",
            file_path="app/api.py",
            line_number=4,
            end_line_number=4,
            side="RIGHT",
            commit_sha="head123",
        ),
        RenderedComment(
            comment_type="inline",
            body="second inline",
            file_path="app/api.py",
            line_number=5,
            end_line_number=5,
            side="RIGHT",
            commit_sha="head123",
        ),
    ]

    published = service._publish_review(pr, comments, [changed_file])

    assert published == {"summary_posted": 1, "inline_posted": 1, "inline_skipped": 0, "inline_failed": 1}
    assert pr.issue_comments == ["summary"]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["body"] == "second inline"


def test_post_failure_comment_uses_readable_text():
    pr = FakePullRequest(number=15, files=[], file_contents={})
    repo = FakeRepo(pr, {})
    github = FakeGithub(repo)
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=FakeLLMClient())
    payload = IssueCommentPayload.model_validate(
        {
            "action": "created",
            "comment": {"id": 15, "body": "/review"},
            "issue": {"number": 15, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/15"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    service._post_failure_comment(payload, "Validation Failed")

    assert pr.issue_comments == ["Automated review failed.\n\n- PR: #15\n- Reason: `Validation Failed`"]


def test_process_issue_comment_salvages_string_findings_from_llm_payload():
    source = "def run(value):\n    return value\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value\n"
    pr = FakePullRequest(
        number=10,
        files=[FakePullFile(filename="app/service.py", patch=patch)],
        file_contents={"app/service.py": source},
    )
    repo = FakeRepo(pr, {"app/service.py": source})
    github = FakeGithub(repo)
    llm_client = FakeLLMClient(
        payload={
            "summary": "Found a correctness issue",
            "findings": ["value is dereferenced without checking whether it is None."],
        }
    )
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=llm_client)

    service.process_issue_comment(
        {
            "action": "created",
            "comment": {"id": 12, "body": "/review"},
            "issue": {"number": 10, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/10"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    assert len(pr.issue_comments) == 1
    assert "value is dereferenced" in pr.issue_comments[0]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["path"] == "app/service.py"


def test_process_issue_comment_salvages_partial_structured_findings():
    source = "import asyncio\nimport time\n\nasync def endpoint():\n    time.sleep(1)\n"
    patch = "@@ -2,3 +2,4 @@\n import time\n \n async def endpoint():\n+    time.sleep(1)\n"
    pr = FakePullRequest(
        number=11,
        files=[FakePullFile(filename="app/api.py", patch=patch)],
        file_contents={"app/api.py": source},
    )
    repo = FakeRepo(pr, {"app/api.py": source})
    github = FakeGithub(repo)
    llm_client = PartialStructuredLLMClient()
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=llm_client)

    service.process_issue_comment(
        {
            "action": "created",
            "comment": {"id": 13, "body": "/review"},
            "issue": {"number": 11, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/11"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    assert len(llm_client.prompts) == 2
    assert len(pr.issue_comments) == 1
    assert "Blocking I/O in async route" in pr.issue_comments[0]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["path"] == "app/api.py"


def test_process_issue_comment_salvages_rejected_fallback_findings():
    source = "def run(value):\n    return value.id\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value.id\n"
    pr = FakePullRequest(
        number=12,
        files=[FakePullFile(filename="app/service.py", patch=patch)],
        file_contents={"app/service.py": source},
    )
    repo = FakeRepo(pr, {"app/service.py": source})
    github = FakeGithub(repo)
    llm_client = FallbackRejectingLLMClient()
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
    )
    service = GitHubReviewService(settings=settings, github_client_factory=lambda: github, llm_client=llm_client)

    service.process_issue_comment(
        {
            "action": "created",
            "comment": {"id": 14, "body": "/review"},
            "issue": {"number": 12, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/12"}},
            "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
        }
    )

    assert len(llm_client.prompts) == 2
    assert len(pr.issue_comments) == 1
    assert "Missing None check for get_page_by_id return value" in pr.issue_comments[0]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["path"] == "app/service.py"


def test_enqueue_issue_comment_cancels_older_queued_runs_for_same_pr(tmp_path):
    source = "def run(value):\n    return value.id\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value.id\n"
    pr = FakePullRequest(
        number=20,
        files=[FakePullFile(filename="app/service.py", patch=patch)],
        file_contents={"app/service.py": source},
    )
    repo = FakeRepo(pr, {"app/service.py": source})
    github = FakeGithub(repo)
    queue_manager = FakeQueueManager()
    repository = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
        review_worker_threads=2,
    )
    service = GitHubReviewService(
        settings=settings,
        github_client_factory=lambda: github,
        llm_client=FakeLLMClient(),
        review_run_repository=repository,
        review_queue=queue_manager,
    )

    first_payload = {
        "action": "created",
        "comment": {"id": 21, "body": "/review"},
        "issue": {"number": 20, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/20"}},
        "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
    }
    second_payload = {
        "action": "created",
        "comment": {"id": 22, "body": "/review"},
        "issue": {"number": 20, "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/20"}},
        "repository": {"name": "demo", "full_name": "octo/demo", "owner": {"login": "octo"}},
    }

    service.enqueue_issue_comment(first_payload)
    service.enqueue_issue_comment(second_payload)

    runs = repository.list_runs(limit=10)

    assert len(queue_manager.enqueued) == 2
    assert runs[0].status == "queued"
    assert runs[1].status == "cancelled"


def test_process_review_run_marks_stale_when_pr_head_has_advanced(tmp_path):
    source = "def run(value):\n    return value.id\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value.id\n"
    pr = FakePullRequest(
        number=21,
        files=[FakePullFile(filename="app/service.py", patch=patch)],
        file_contents={"app/service.py": source},
    )
    pr.head.sha = "newhead456"
    repo = FakeRepo(pr, {"app/service.py": source})
    github = FakeGithub(repo)
    repository = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
        review_worker_threads=2,
    )
    service = GitHubReviewService(
        settings=settings,
        github_client_factory=lambda: github,
        llm_client=FakeLLMClient(),
        review_run_repository=repository,
    )
    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-stale",
            repo_owner="octo",
            repo_name="demo",
            pr_number=21,
            review_commit_sha="oldhead123",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="queued",
            task_payload={
                "review_run_id": "run-stale",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 21,
                "base_sha": "base123",
                "head_sha": "oldhead123",
                "review_commit_sha": "oldhead123",
                "selected_model": "model",
                "trigger_type": "command",
                "trigger_comment_id": 99,
                "changed_files": [
                    {
                        "file_path": "app/service.py",
                        "language": "python",
                        "status": "modified",
                        "diff_hunks": [patch],
                        "full_file_content": source,
                        "position_mapping": {"2": 2},
                    }
                ],
            },
        )
    )

    service.process_review_run("run-stale")
    updated = repository.get_run("run-stale")

    assert updated.status == "stale"
    assert pr.issue_comments == []
    assert pr.inline_comments == []


def test_recover_pending_runs_requeues_latest_run_per_pr_and_resets_running(tmp_path):
    queue_manager = FakeQueueManager()
    repository = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    settings = SimpleNamespace(
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        llm_base_url="https://example.com",
        llm_api_key="token",
        llm_model="model",
        review_worker_threads=2,
    )
    service = GitHubReviewService(
        settings=settings,
        github_client_factory=lambda: None,
        llm_client=FakeLLMClient(),
        review_run_repository=repository,
        review_queue=queue_manager,
    )

    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-older",
            repo_owner="octo",
            repo_name="demo",
            pr_number=30,
            review_commit_sha="head-old",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="queued",
            task_payload={
                "review_run_id": "run-older",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 30,
                "base_sha": "base",
                "head_sha": "head-old",
                "review_commit_sha": "head-old",
                "selected_model": "model",
                "trigger_type": "command",
                "changed_files": [],
            },
        )
    )
    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-newer",
            repo_owner="octo",
            repo_name="demo",
            pr_number=30,
            review_commit_sha="head-new",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="queued",
            task_payload={
                "review_run_id": "run-newer",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 30,
                "base_sha": "base",
                "head_sha": "head-new",
                "review_commit_sha": "head-new",
                "selected_model": "model",
                "trigger_type": "command",
                "changed_files": [],
            },
        )
    )
    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-running",
            repo_owner="octo",
            repo_name="demo",
            pr_number=31,
            review_commit_sha="head-running",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="running",
            task_payload={
                "review_run_id": "run-running",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 31,
                "base_sha": "base",
                "head_sha": "head-running",
                "review_commit_sha": "head-running",
                "selected_model": "model",
                "trigger_type": "command",
                "changed_files": [],
            },
        )
    )

    service.recover_pending_runs()

    assert [item[0] for item in queue_manager.enqueued] == ["run-running", "run-newer"]
    assert repository.get_run("run-running").status == "queued"
    assert repository.get_run("run-older").status == "cancelled"
