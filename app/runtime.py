from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI

from app.config import Settings
from app.github.service import GitHubReviewService
from app.persistence.repository import ReviewRunRepository


def get_settings(app: FastAPI) -> Settings | SimpleNamespace:
    settings = getattr(app.state, "settings", None)
    if settings is None:
        settings = Settings()
        app.state.settings = settings
    return settings


def get_repository(app: FastAPI, settings: Settings | SimpleNamespace) -> ReviewRunRepository | None:
    repository = getattr(app.state, "review_run_repository", None)
    review_db_path = getattr(settings, "review_db_path", None)
    if repository is None and review_db_path is not None:
        repository = ReviewRunRepository.for_sqlite(review_db_path)
        app.state.review_run_repository = repository
    return repository


def get_review_service(
    app: FastAPI,
    settings: Settings | SimpleNamespace,
    review_repository: ReviewRunRepository | None,
) -> Any:
    review_service = getattr(app.state, "review_service", None)
    if review_service is None:
        review_service = GitHubReviewService(settings, review_run_repository=review_repository)
        app.state.review_service = review_service
        app.state.review_recovery_completed = False
        return review_service

    bound_repository = getattr(review_service, "_review_run_repository", None)
    if bound_repository is not None and bound_repository is not review_repository:
        review_service = GitHubReviewService(settings, review_run_repository=review_repository)
        app.state.review_service = review_service
        app.state.review_recovery_completed = False
    return review_service


def ensure_runtime_state(app: FastAPI) -> tuple[Settings | SimpleNamespace, ReviewRunRepository | None, Any]:
    settings = get_settings(app)
    repository = get_repository(app, settings)
    review_service = get_review_service(app, settings, repository)

    if not getattr(app.state, "review_recovery_completed", False) and hasattr(review_service, "recover_pending_runs"):
        review_service.recover_pending_runs()
        app.state.review_recovery_completed = True

    return settings, repository, review_service
