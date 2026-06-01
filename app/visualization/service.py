from fastapi import HTTPException

from app.config import Settings
from app.llm.openai_compatible import OpenAICompatibleClient
from app.persistence.models import AgentTraceCreate, ReviewRunCreate, ReviewRunUpdate
from app.persistence.repository import ReviewRunRepository
from app.review.models import ReviewTask
from app.review.orchestrator import review_pull_request
from app.review.rendering import render_review_comments


def list_review_runs(repository: ReviewRunRepository, *, limit: int = 20) -> dict:
    runs = repository.list_runs(limit=limit)
    return {"items": [run.model_dump(mode="json") for run in runs]}


def get_review_run_detail(repository: ReviewRunRepository, review_run_id: str) -> dict:
    try:
        detail = repository.get_run_detail(review_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="review run not found") from exc
    return detail.model_dump(mode="json")


def replay_review_run(
    repository: ReviewRunRepository,
    settings: Settings,
    review_run_id: str,
    model_name: str,
    publish_to_github: bool = False,
) -> dict:
    if publish_to_github:
        raise HTTPException(status_code=400, detail="local replay does not publish to GitHub")
    if model_name not in settings.allowed_llm_models:
        raise HTTPException(status_code=400, detail="model is not allowed")

    try:
        detail = repository.get_run_detail(review_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="review run not found") from exc

    task = ReviewTask.model_validate(detail.run.task_payload)
    replay_task = task.model_copy(
        update={
            "review_run_id": f"{task.review_run_id}-replay-{model_name}",
            "selected_model": model_name,
        }
    )
    repository.create_run(
        ReviewRunCreate(
            review_run_id=replay_task.review_run_id,
            repo_owner=replay_task.repo_owner,
            repo_name=replay_task.repo_name,
            pr_number=replay_task.pr_number,
            review_commit_sha=replay_task.review_commit_sha,
            trigger_type=replay_task.trigger_type,
            selected_model=model_name,
            base_url=settings.llm_base_url,
            status="running",
            task_payload=replay_task.model_dump(mode="json"),
            diff_snapshot=detail.run.diff_snapshot,
        )
    )

    llm_client = OpenAICompatibleClient.from_settings(settings, model_name=model_name)
    result = review_pull_request(replay_task, llm_client=llm_client)
    comments = render_review_comments(result)
    for trace in result.agent_traces:
        repository.save_agent_trace(
            AgentTraceCreate(
                review_run_id=replay_task.review_run_id,
                agent_role=trace.agent_role,
                model_name=trace.model_name,
                prompt_version=trace.prompt_version,
                input_payload=trace.input_payload,
                raw_response=trace.raw_response,
                parsed_output=trace.parsed_output,
                latency_ms=trace.latency_ms,
                token_usage=trace.token_usage,
            )
        )
    updated = repository.update_run(
        replay_task.review_run_id,
        ReviewRunUpdate(
            status="completed",
            summary_snapshot=result.summary,
            result_payload=result.model_dump(mode="json"),
            rendered_comments=[comment.model_dump(mode="json") for comment in comments],
            github_status={"published": False},
        ),
    )
    return {
        "review_run_id": updated.review_run_id,
        "selected_model": updated.selected_model,
        "base_url": updated.base_url,
        "summary": result.summary,
        "findings": result.model_dump(mode="json")["findings"],
        "comments": [comment.model_dump(mode="json") for comment in comments],
    }


def get_models(settings: Settings) -> dict:
    return {
        "default_model": settings.llm_model,
        "items": settings.allowed_llm_models,
    }
