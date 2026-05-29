import pytest

from app.review.models import ChangedFile, ReviewTask
from app.review.orchestrator import ensure_not_stale, review_pull_request


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


class FakeLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return {
            "summary": "Found a correctness issue",
            "findings": [
                {
                    "file_path": "app/service.py",
                    "line_number": 2,
                    "end_line_number": 2,
                    "risk_level": "high",
                    "verdict": "confirm",
                    "issue_title": "LLM detected issue",
                    "issue_detail": "This change breaks behavior.",
                    "why_it_matters": "It causes a runtime error.",
                    "suggestion_rationale": "Add the missing guard.",
                    "suggested_code": "return value or 0",
                    "original_code_snippet": "return value",
                    "confidence": 0.93,
                }
            ],
        }


def test_review_pull_request_uses_llm_fallback_for_command_trigger_without_stage1_hits():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value"],
                full_file_content="def run(value):\n    return value\n",
            )
        ],
    )
    llm_client = FakeLLMClient()

    result = review_pull_request(task, llm_client=llm_client)

    assert len(llm_client.prompts) == 1
    assert result.stats["stage1_candidates"] == 0
    assert len(result.findings) == 1
    assert result.findings[0].issue_title == "LLM detected issue"


class EmptyLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return {"summary": "No output", "findings": []}


def test_review_pull_request_does_not_report_pass_when_llm_fallback_returns_no_findings():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value"],
                full_file_content="def run(value):\n    return value\n",
            )
        ],
    )
    llm_client = EmptyLLMClient()

    result = review_pull_request(task, llm_client=llm_client)

    assert len(llm_client.prompts) == 1
    assert result.findings == []
    assert result.overall_risk == "medium"
    assert "LLM 复核没有产出有效结果" in result.summary


class StringFindingsLLMClient:
    def review_findings(self, prompt: str) -> dict:
        return {
            "summary": "Found a correctness issue",
            "findings": [
                "value is dereferenced without checking whether it is None.",
            ],
        }


def test_review_pull_request_salvages_string_findings_from_llm_payload():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value"],
                full_file_content="def run(value):\n    return value\n",
            )
        ],
    )

    result = review_pull_request(task, llm_client=StringFindingsLLMClient())

    assert len(result.findings) == 1
    assert result.findings[0].file_path == "app/service.py"
    assert "None" in result.findings[0].issue_detail
