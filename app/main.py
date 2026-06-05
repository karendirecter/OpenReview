from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from app.github.service import decode_json_body
from app.github.webhook import should_trigger_review, verify_webhook_signature
from app.runtime import ensure_runtime_state, get_settings
from app.visualization.router import router as visualization_router

app = FastAPI(title="GitHub PR Auto Review")
app.include_router(visualization_router)
FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/github", status_code=202)
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    body = await request.body()
    settings = get_settings(request.app)

    signature_256 = request.headers.get("X-Hub-Signature-256")
    if not verify_webhook_signature(settings.github_webhook_secret, body, signature_256):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    payload = decode_json_body(body)
    event_name = request.headers.get("X-GitHub-Event", "")
    if not should_trigger_review(event_name, payload):
        return {"status": "ignored"}

    _, _, review_service = ensure_runtime_state(request.app)
    background_tasks.add_task(review_service.enqueue_issue_comment, payload)
    return {"status": "accepted"}


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    if not FRONTEND_DIST_DIR.exists():
        raise HTTPException(status_code=404, detail="frontend not built")

    requested_path = (FRONTEND_DIST_DIR / full_path).resolve()
    frontend_root = FRONTEND_DIST_DIR.resolve()

    # Only serve files that stay within the built frontend output directory.
    if requested_path != frontend_root and frontend_root not in requested_path.parents:
        raise HTTPException(status_code=404, detail="not found")

    if full_path and requested_path.is_file():
        return FileResponse(requested_path)

    if full_path and Path(full_path).suffix:
        raise HTTPException(status_code=404, detail="not found")

    return FileResponse(frontend_root / "index.html")
