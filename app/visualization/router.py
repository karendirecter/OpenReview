from fastapi import APIRouter, Request

from app.runtime import ensure_runtime_state
from app.visualization.service import get_models, get_review_run_detail, list_review_runs, replay_review_run

router = APIRouter()


@router.get("/api/review-runs")
def review_runs(request: Request, limit: int = 20) -> dict:
    _, repository, _ = ensure_runtime_state(request.app)
    return list_review_runs(repository, limit=limit)


@router.get("/api/review-runs/{review_run_id}")
def review_run_detail(review_run_id: str, request: Request) -> dict:
    _, repository, _ = ensure_runtime_state(request.app)
    return get_review_run_detail(repository, review_run_id)


@router.post("/api/review-runs/{review_run_id}/replay")
async def replay(review_run_id: str, request: Request) -> dict:
    settings, repository, _ = ensure_runtime_state(request.app)
    payload = await request.json()
    return replay_review_run(
        repository=repository,
        settings=settings,
        review_run_id=review_run_id,
        model_name=payload["model_name"],
        publish_to_github=payload.get("publish_to_github", False),
    )


@router.get("/api/models")
def models(request: Request) -> dict:
    settings, _, _ = ensure_runtime_state(request.app)
    return get_models(settings)
