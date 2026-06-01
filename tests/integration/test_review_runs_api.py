from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.persistence.models import AgentTraceCreate, ReviewRunCreate
from app.persistence.repository import ReviewRunRepository


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
    app.state.review_service = None
    app.state.review_recovery_completed = False
    return TestClient(app), repository


def seed_review_run(repository: ReviewRunRepository) -> str:
    repository.create_run(
        ReviewRunCreate(
            review_run_id="run-1",
            repo_owner="octo",
            repo_name="demo",
            pr_number=12,
            review_commit_sha="head123",
            trigger_type="command",
            selected_model="deepseek-v4-flash-260425",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
            task_payload={
                "review_run_id": "run-1",
                "repo_owner": "octo",
                "repo_name": "demo",
                "pr_number": 12,
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
            result_payload={
                "review_run_id": "run-1",
                "review_commit_sha": "head123",
                "summary": "found issue",
                "overall_risk": "high",
                "findings": [],
                "stats": {},
                "render_mode": "summary_inline",
                "agent_traces": [],
            },
            rendered_comments=[{"body": "summary"}],
            github_status={"published": True},
        )
    )
    repository.save_agent_trace(
        AgentTraceCreate(
            review_run_id="run-1",
            agent_role="inspector",
            model_name="deepseek-v4-flash-260425",
            prompt_version="task19-v1",
            input_payload={"file_path": "app/service.py"},
            raw_response={"summary": "found issue", "findings": []},
            parsed_output={"summary": "found issue", "findings": []},
        )
    )
    return "run-1"


def test_get_review_runs_returns_persisted_history(tmp_path):
    client, repository = build_client(tmp_path)
    review_run_id = seed_review_run(repository)

    response = client.get("/api/review-runs")

    assert response.status_code == 200
    assert response.json()["items"][0]["review_run_id"] == review_run_id


def test_get_review_run_detail_returns_agent_traces(tmp_path):
    client, repository = build_client(tmp_path)
    review_run_id = seed_review_run(repository)

    response = client.get(f"/api/review-runs/{review_run_id}")

    assert response.status_code == 200
    assert response.json()["agent_traces"][0]["agent_role"] == "inspector"


def test_get_models_returns_allowed_models(tmp_path):
    client, repository = build_client(tmp_path)
    seed_review_run(repository)

    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json()["default_model"] == "deepseek-v4-flash-260425"
    assert "doubao-seed-2-0-code-preview-260215" in response.json()["items"]
