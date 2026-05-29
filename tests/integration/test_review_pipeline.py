from scripts.run_local_review import build_local_task


def test_build_local_task_sets_command_trigger_type():
    task = build_local_task(repo_owner="octo", repo_name="demo", pr_number=8, review_commit_sha="head123")

    assert task.trigger_type == "command"
    assert task.review_commit_sha == "head123"
