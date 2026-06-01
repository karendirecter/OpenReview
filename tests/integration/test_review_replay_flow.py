from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.persistence.models import ReviewRunCreate
from app.persistence.repository import ReviewRunRepository


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
                        "issue_detail": "value may be None before attribute access.",
                        "why_it_matters": "This can crash at runtime.",
                        "fix_intent": "Add a guard before dereference.",
                        "suggestion_rationale": "Guard the access.",
                        "suggested_code": "",
                        "original_code_snippet": "return value.id",
                        "confidence": 0.95,
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
                    "issue_detail": "value may be None before attribute access.",
                    "why_it_matters": "This can crash at runtime.",
                    "fix_intent": "Add a guard before dereference.",
                    "suggestion_rationale": "Guard the access.",
                    "suggested_code": "if value is None:\n    return 0\nreturn value.id",
                    "original_code_snippet": "return value.id",
                    "confidence": 0.95,
                }
            ],
        }


def build_client(tmp_path: Path) -> tuple[TestClient, ReviewRunRepository]:
    repository = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    app.state.settings = SimpleNamespace(
        llm_model="deepseek-v4-flash-260425",
        allowed_llm_models=[
            "deepseek-v4-flash-260425",
            "doubao-seed-2-0-code-preview-260215",
            "doubao-seed-1-8-251228",
        ],
        llm_base_url="https://ark.cn-beijing.volces.com/api/v3/",
        llm_api_key="token",
        review_db_path=tmp_path / "review_runs.db",
    )
    app.state.review_run_repository = repository
    return TestClient(app), repository


def seed_buggy_review_run(repository: ReviewRunRepository) -> str:
    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-bug",
            repo_owner="octo",
            repo_name="demo",
            pr_number=99,
            review_commit_sha="head123",
            trigger_type="command",
            selected_model="deepseek-v4-flash-260425",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
            task_payload={
                "review_run_id": "run-bug",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 99,
                "base_sha": "base123",
                "head_sha": "head123",
                "review_commit_sha": "head123",
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
    return "run-bug"


def test_replay_flow_generates_bug_related_suggestion(tmp_path, monkeypatch):
    client, repository = build_client(tmp_path)
    review_run_id = seed_buggy_review_run(repository)
    monkeypatch.setattr(
        "app.visualization.service.OpenAICompatibleClient.from_settings",
        lambda settings, model_name=None: FakeReplayClient(),
    )

    response = client.post(
        f"/api/review-runs/{review_run_id}/replay",
        json={"model_name": "deepseek-v4-flash-260425", "publish_to_github": False},
    )

    assert response.status_code == 200
    finding = response.json()["findings"][0]
    assert "None" in finding["issue_title"] or "dereference" in finding["issue_title"]
    assert "import logging" not in finding["suggested_code"]
    assert "value.id" in finding["suggested_code"]
