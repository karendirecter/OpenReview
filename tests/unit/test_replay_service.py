from types import SimpleNamespace

from app.persistence.models import ReviewRunCreate
from app.persistence.repository import ReviewRunRepository
from app.visualization.service import replay_review_run


class FakeReplayClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def review_findings(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        if "Inspector Agent" in prompt:
            return {
                "summary": "Issue confirmed",
                "findings": [
                    {
                        "file_path": "app/service.py",
                        "line_number": 2,
                        "end_line_number": 2,
                        "risk_level": "high",
                        "verdict": "confirm",
                        "issue_title": "Possible None dereference",
                        "issue_detail": "value may be None",
                        "why_it_matters": "This can crash",
                        "fix_intent": "Add a guard before dereference.",
                        "suggestion_rationale": "Guard the access.",
                        "suggested_code": "",
                        "original_code_snippet": "return value.id",
                        "confidence": 0.91,
                    }
                ],
            }
        return {
            "summary": "Fix generated",
            "findings": [
                {
                    "file_path": "app/service.py",
                    "line_number": 2,
                    "end_line_number": 2,
                    "risk_level": "high",
                    "verdict": "confirm",
                    "issue_title": "Possible None dereference",
                    "issue_detail": "value may be None",
                    "why_it_matters": "This can crash",
                    "fix_intent": "Add a guard before dereference.",
                    "suggestion_rationale": "Guard the access.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "original_code_snippet": "return value.id",
                    "confidence": 0.91,
                }
            ],
        }


def test_replay_review_run_uses_selected_model_without_changing_base_url(tmp_path, monkeypatch):
    repository = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-1",
            repo_owner="octo",
            repo_name="demo",
            pr_number=9,
            review_commit_sha="abc123",
            trigger_type="command",
            selected_model="deepseek-v4-flash-260425",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
            task_payload={
                "review_run_id": "run-1",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 9,
                "base_sha": "base123",
                "head_sha": "abc123",
                "review_commit_sha": "abc123",
                "selected_model": "deepseek-v4-flash-260425",
                "trigger_type": "command",
                "changed_files": [
                    {
                        "file_path": "app/service.py",
                        "language": "python",
                        "status": "modified",
                        "diff_hunks": ["@@ -1,1 +1,2 @@\n-return old\n+return value.id"],
                        "surrounding_context": [],
                        "full_file_content": "def run(value):\n    return value.id\n",
                        "position_mapping": {},
                    }
                ],
            },
            diff_snapshot="@@ -1,1 +1,2 @@\n-return old\n+return value.id",
        )
    )
    settings = SimpleNamespace(
        llm_base_url="https://ark.cn-beijing.volces.com/api/v3/",
        llm_api_key="token",
        llm_model="deepseek-v4-flash-260425",
        allowed_llm_models=[
            "deepseek-v4-flash-260425",
            "doubao-seed-2-0-code-preview-260215",
            "doubao-seed-1-8-251228",
        ],
    )

    monkeypatch.setattr(
        "app.visualization.service.OpenAICompatibleClient.from_settings",
        lambda current_settings, model_name=None: FakeReplayClient(),
    )

    replayed = replay_review_run(
        repository=repository,
        settings=settings,
        review_run_id="run-1",
        model_name="doubao-seed-2-0-code-preview-260215",
        publish_to_github=False,
    )

    assert replayed["selected_model"] == "doubao-seed-2-0-code-preview-260215"
    assert replayed["base_url"] == "https://ark.cn-beijing.volces.com/api/v3/"
    assert replayed["findings"][0]["suggested_code"].startswith("if value is None:")
