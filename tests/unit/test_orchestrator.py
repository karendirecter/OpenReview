import pytest

from app.review.models import ChangedFile, IssueHit, ReviewTask
from app.review.orchestrator import ensure_not_stale, review_pull_request, run_stage2_agents


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
        if "Inspector Agent" in prompt:
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
                        "fix_intent": "Guard the access when value can be None.",
                        "suggestion_rationale": "Add the missing guard.",
                        "suggested_code": "",
                        "original_code_snippet": "return value.id",
                        "confidence": 0.93,
                    }
                ],
            }

        return {
            "summary": "Generate a fix",
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
                    "fix_intent": "Guard the access when value can be None.",
                    "suggestion_rationale": "Add the missing guard.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "original_code_snippet": "return value.id",
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
        selected_model="deepseek-v4-flash-260425",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value.id"],
                full_file_content="def run(value):\n    return value.id\n",
            )
        ],
    )
    llm_client = FakeLLMClient()

    result = review_pull_request(task, llm_client=llm_client)

    assert len(llm_client.prompts) == 2
    assert result.stats["stage1_candidates"] == 0
    assert len(result.findings) == 1
    assert result.findings[0].issue_title == "LLM detected issue"
    assert result.findings[0].suggested_code.startswith("if value is None:")
    assert [trace.agent_role for trace in result.agent_traces] == ["inspector", "fixer"]


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
                        "issue_title": "LLM detected issue",
                        "issue_detail": "This change breaks behavior.",
                        "why_it_matters": "It causes a runtime error.",
                        "fix_intent": "Guard the access when value can be None.",
                        "suggestion_rationale": "Add the missing guard.",
                        "confidence": 0.93,
                    }
                ],
            }

        return {
            "summary": "Generate a fix",
            "findings": [
                {
                    "issue_title": "LLM detected issue",
                    "issue_detail": "This change breaks behavior.",
                    "why_it_matters": "It causes a runtime error.",
                    "fix_intent": "Guard the access when value can be None.",
                    "suggestion_rationale": "Add the missing guard.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "confidence": 0.93,
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
                        "issue_title": "Missing None check",
                        "issue_detail": "value may be None before attribute access.",
                        "why_it_matters": "It crashes at runtime.",
                        "fix_intent": "Add a guard before dereference.",
                        "suggestion_rationale": "Prevent AttributeError.",
                        "suggested_code": "",
                        "original_code_snippet": "return value.id",
                        "confidence": "high",
                    }
                ],
            }

        return {
            "summary": "Generate a fix",
            "findings": [
                {
                    "issue_title": "Missing None check",
                    "issue_detail": "value may be None before attribute access.",
                    "why_it_matters": "It crashes at runtime.",
                    "fix_intent": "Add a guard before dereference.",
                    "suggestion_rationale": "Prevent AttributeError.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "confidence": 0.93,
                }
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


def test_review_pull_request_salvages_partial_structured_findings_and_runs_fixer():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        selected_model="deepseek-v4-flash-260425",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value.id"],
                full_file_content="def run(value):\n    return value.id\n",
            )
        ],
    )
    llm_client = PartialStructuredLLMClient()

    result = review_pull_request(task, llm_client=llm_client)

    assert len(llm_client.prompts) == 2
    assert len(result.findings) == 1
    assert result.findings[0].file_path == "app/service.py"
    assert result.findings[0].line_number > 0
    assert result.findings[0].suggested_code.startswith("if value is None:")
    assert [trace.agent_role for trace in result.agent_traces] == ["inspector", "fixer"]


def test_review_pull_request_salvages_rejected_fallback_findings_with_real_issue_details():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        selected_model="deepseek-v4-flash-260425",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value.id"],
                full_file_content="def run(value):\n    return value.id\n",
            )
        ],
    )

    result = review_pull_request(task, llm_client=FallbackRejectingLLMClient())

    assert len(result.findings) == 1
    assert result.findings[0].issue_title == "Missing None check"
    assert result.findings[0].suggested_code.startswith("if value is None:")
    assert [trace.agent_role for trace in result.agent_traces] == ["inspector", "fixer"]


def test_run_stage2_agents_passes_inspector_output_to_fixer():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        selected_model="deepseek-v4-flash-260425",
        trigger_type="command",
        changed_files=[
            ChangedFile(
                file_path="app/service.py",
                language="python",
                status="modified",
                diff_hunks=["@@ -1,1 +1,2 @@\n-return old\n+return value.id"],
                full_file_content="def run(value):\n    return value.id\n",
            )
        ],
    )
    llm_client = FakeLLMClient()
    hit = IssueHit(
        file_path="app/service.py",
        line_number=2,
        end_line_number=2,
        commit_sha="head123",
        rule_id="python.none",
        severity="high",
        message="Possible None dereference",
        evidence="value may be None",
        original_code_snippet="return value.id",
    )

    findings, traces = run_stage2_agents(
        task=task,
        hit=hit,
        changed_file=task.changed_files[0],
        llm_client=llm_client,
    )

    assert findings[0].issue_title == "LLM detected issue"
    assert findings[0].suggested_code.startswith("if value is None:")
    assert [trace.agent_role for trace in traces] == ["inspector", "fixer"]
