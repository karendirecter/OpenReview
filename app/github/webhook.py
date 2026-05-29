import hashlib
import hmac

from app.github.models import IssueCommentPayload


def verify_webhook_signature(secret: str, body: bytes, signature_256: str | None) -> bool:
    if not signature_256 or not signature_256.startswith("sha256="):
        return False

    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_256, f"sha256={expected}")


def should_trigger_review(event_name: str, payload: dict) -> bool:
    if event_name != "issue_comment":
        return False

    comment_payload = IssueCommentPayload.model_validate(payload)
    if comment_payload.issue.pull_request is None:
        return False

    return comment_payload.comment.body.strip() == "/review"
