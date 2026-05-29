from types import SimpleNamespace

from app.github.service import GitHubReviewService


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


class FakeGithub:
    def __init__(self, repo) -> None:
        self._repo = repo

    def get_repo(self, full_name: str):
        assert full_name == "octo/demo"
        return self._repo


class FakeLLMClient:
    def __init__(self, payload: dict | None = None) -> None:
        self.payload = payload or {}
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return self.payload


def test_process_issue_comment_posts_summary_and_inline_comments():
    source = "import time\n\nasync def endpoint():\n    time.sleep(1)\n"
    patch = "@@ -1,3 +1,4 @@\n import time\n \n async def endpoint():\n+    time.sleep(1)\n"
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
    assert "自动代码评审结果" in pr.issue_comments[0]
    assert len(pr.inline_comments) == 1
    assert pr.inline_comments[0]["path"] == "app/api.py"
    assert pr.inline_comments[0]["line"] == 4


def test_process_issue_comment_uses_llm_when_stage1_has_no_hits():
    source = "def run(value):\n    return value\n"
    patch = "@@ -1,1 +1,2 @@\n-return old\n+return value\n"
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
                    "suggestion_rationale": "Guard the return.",
                    "suggested_code": "return value or 0",
                    "original_code_snippet": "return value",
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

    assert len(llm_client.prompts) == 1
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
    assert "LLM 复核没有产出有效结果" in pr.issue_comments[0]
    assert pr.inline_comments == []


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
