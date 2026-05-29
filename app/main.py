from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.config import Settings
from app.github.service import GitHubReviewService, decode_json_body
from app.github.webhook import should_trigger_review, verify_webhook_signature

app = FastAPI(title="GitHub PR Auto Review")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/github", status_code=202)
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    body = await request.body()
    settings = getattr(app.state, "settings", None) or Settings()
    app.state.settings = settings

    signature_256 = request.headers.get("X-Hub-Signature-256")
    if not verify_webhook_signature(settings.github_webhook_secret, body, signature_256):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    payload = decode_json_body(body)
    event_name = request.headers.get("X-GitHub-Event", "")
    if not should_trigger_review(event_name, payload):
        return {"status": "ignored"}

    review_service = getattr(app.state, "review_service", None) or GitHubReviewService(settings)
    app.state.review_service = review_service
    background_tasks.add_task(review_service.process_issue_comment, payload)
    return {"status": "accepted"}
