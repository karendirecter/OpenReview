from fastapi import APIRouter, Request

from app.config import Settings
from app.persistence.repository import ReviewRunRepository
from app.visualization.service import get_models, get_review_run_detail, list_review_runs, replay_review_run

router = APIRouter()


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        settings = Settings()
        request.app.state.settings = settings
    return settings


def get_repository(request: Request, settings: Settings) -> ReviewRunRepository:
    repository = getattr(request.app.state, "review_run_repository", None)
    if repository is None:
        repository = ReviewRunRepository.for_sqlite(settings.review_db_path)
        request.app.state.review_run_repository = repository
    return repository


@router.get("/api/review-runs")
def review_runs(request: Request, limit: int = 20) -> dict:
    settings = get_settings(request)
    repository = get_repository(request, settings)
    return list_review_runs(repository, limit=limit)


@router.get("/api/review-runs/{review_run_id}")
def review_run_detail(review_run_id: str, request: Request) -> dict:
    settings = get_settings(request)
    repository = get_repository(request, settings)
    return get_review_run_detail(repository, review_run_id)


@router.post("/api/review-runs/{review_run_id}/replay")
async def replay(review_run_id: str, request: Request) -> dict:
    settings = get_settings(request)
    repository = get_repository(request, settings)
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
    settings = get_settings(request)
    return get_models(settings)
