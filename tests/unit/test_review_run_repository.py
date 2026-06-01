from app.persistence.models import AgentTraceCreate, ReviewRunCreate, ReviewRunUpdate
from app.persistence.repository import ReviewRunRepository


def test_repository_can_save_and_list_review_runs(tmp_path):
    repo = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")

    created = repo.create_run(
        ReviewRunCreate(
            review_run_id="run-1",
            repo_owner="octo",
            repo_name="demo",
            pr_number=9,
            review_commit_sha="abc123",
            trigger_type="command",
            selected_model="deepseek-v4-flash-260425",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
        )
    )

    listed = repo.list_runs(limit=10)

    assert created.review_run_id == "run-1"
    assert listed[0].selected_model == "deepseek-v4-flash-260425"


def test_repository_can_store_agent_traces_and_run_detail(tmp_path):
    repo = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    repo.create_run(
        ReviewRunCreate(
            review_run_id="run-2",
            repo_owner="octo",
            repo_name="demo",
            pr_number=10,
            review_commit_sha="def456",
            trigger_type="command",
            selected_model="doubao-seed-2-0-code-preview-260215",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
        )
    )
    repo.save_agent_trace(
        AgentTraceCreate(
            review_run_id="run-2",
            agent_role="inspector",
            model_name="doubao-seed-2-0-code-preview-260215",
            prompt_version="v2",
            input_payload={"file": "app/api.py"},
            raw_response={"summary": "found"},
            parsed_output={"findings": []},
        )
    )
    repo.update_run(
        "run-2",
        ReviewRunUpdate(
            status="completed",
            summary_snapshot="completed",
            result_payload={"summary": "done"},
            rendered_comments=[{"body": "summary"}],
            github_status={"summary_posted": True},
        ),
    )

    detail = repo.get_run_detail("run-2")

    assert detail.run.status == "completed"
    assert detail.run.result_payload["summary"] == "done"
    assert detail.agent_traces[0].agent_role == "inspector"


def test_repository_can_list_active_runs_for_same_pr(tmp_path):
    repo = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")
    repo.create_run(
        ReviewRunCreate(
            review_run_id="run-queued",
            repo_owner="octo",
            repo_name="demo",
            pr_number=11,
            review_commit_sha="abc123",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="queued",
        )
    )
    repo.create_run(
        ReviewRunCreate(
            review_run_id="run-running",
            repo_owner="octo",
            repo_name="demo",
            pr_number=11,
            review_commit_sha="def456",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="running",
        )
    )
    repo.create_run(
        ReviewRunCreate(
            review_run_id="run-completed",
            repo_owner="octo",
            repo_name="demo",
            pr_number=11,
            review_commit_sha="ghi789",
            trigger_type="command",
            selected_model="model",
            base_url="https://example.com",
            status="completed",
        )
    )

    active = repo.list_runs_for_pr("octo", "demo", 11, statuses=("queued", "running"))

    assert [run.review_run_id for run in active] == ["run-running", "run-queued"]
