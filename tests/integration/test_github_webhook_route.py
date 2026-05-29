import hashlib
import hmac
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class FakeReviewService:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def process_issue_comment(self, payload: dict) -> None:
        self.payloads.append(payload)


def sign(secret: str, payload: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_github_webhook_ignores_non_review_comment():
    app.state.settings = SimpleNamespace(github_webhook_secret="secret")
    app.state.review_service = FakeReviewService()
    body = "{\"comment\":{\"body\":\"hello\"},\"issue\":{\"number\":1,\"pull_request\":{\"url\":\"x\"}},\"repository\":{\"name\":\"demo\",\"full_name\":\"octo/demo\",\"owner\":{\"login\":\"octo\"}}}"
    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "issue_comment", "X-Hub-Signature-256": sign("secret", body)},
        content=body,
    )

    assert response.status_code == 202
    assert response.json() == {"status": "ignored"}


def test_github_webhook_accepts_review_comment():
    fake_service = FakeReviewService()
    app.state.settings = SimpleNamespace(github_webhook_secret="secret")
    app.state.review_service = fake_service
    body = "{\"comment\":{\"id\":9,\"body\":\" /review \"},\"issue\":{\"number\":1,\"pull_request\":{\"url\":\"x\"}},\"repository\":{\"name\":\"demo\",\"full_name\":\"octo/demo\",\"owner\":{\"login\":\"octo\"}}}"
    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "issue_comment", "X-Hub-Signature-256": sign("secret", body)},
        content=body,
    )

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert fake_service.payloads[0]["comment"]["body"] == " /review "


def test_github_webhook_rejects_invalid_signature():
    app.state.settings = SimpleNamespace(github_webhook_secret="secret")
    app.state.review_service = FakeReviewService()
    body = "{\"comment\":{\"body\":\"/review\"},\"issue\":{\"number\":1,\"pull_request\":{\"url\":\"x\"}},\"repository\":{\"name\":\"demo\",\"full_name\":\"octo/demo\",\"owner\":{\"login\":\"octo\"}}}"
    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "issue_comment", "X-Hub-Signature-256": "sha256=bad"},
        content=body,
    )

    assert response.status_code == 401
