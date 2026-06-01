from types import SimpleNamespace

from app.llm.openai_compatible import OpenAICompatibleClient, build_review_request
from app.prompts.review_prompt import build_fixer_prompt, build_inspector_prompt, build_review_prompt


def test_build_review_request_targets_configured_model():
    request = build_review_request(
        model="deepseek-v4-flash-260425",
        prompt="review this",
    )

    assert request["model"] == "deepseek-v4-flash-260425"
    assert request["response_format"]["type"] == "json_object"


def test_build_review_request_can_disable_response_format():
    request = build_review_request(
        model="deepseek-v4-flash-260425",
        prompt="review this",
        use_response_format=False,
    )

    assert request["model"] == "deepseek-v4-flash-260425"
    assert "response_format" not in request


def test_build_review_prompt_includes_commit_sha_and_json_contract():
    prompt = build_review_prompt(
        review_commit_sha="head123",
        file_path="app/api.py",
        diff_context="+ time.sleep(1)",
        candidate_summary="Blocking I/O candidate",
    )

    assert "head123" in prompt
    assert '"findings"' in prompt
    assert "Do not return extra text" in prompt
    assert "Inspector Agent" in prompt


def test_build_fixer_prompt_forbids_unrelated_changes():
    prompt = build_fixer_prompt(
        review_commit_sha="head123",
        file_path="app/api.py",
        diff_context="+ user.name",
        inspector_summary="Issue confirmed",
        issue_title="Possible None dereference",
        issue_detail="user may be None before attribute access.",
        fix_intent="Add a guard before user.name is accessed.",
        original_code_snippet="return user.name",
    )

    assert "Fixer Agent" in prompt
    assert "Do not add unrelated imports" in prompt


def test_build_inspector_prompt_includes_fix_intent_contract():
    prompt = build_inspector_prompt(
        review_commit_sha="head123",
        file_path="app/api.py",
        diff_context="+ user.name",
        candidate_summary="Possible None dereference",
        evidence="user may be None",
        original_code_snippet="return user.name",
    )

    assert "fix_intent" in prompt


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise Exception(
                "Error code: 400 - {'error': {'code': 'InvalidParameter', "
                "'message': 'The parameter `response_format.type` specified in the request are not valid: "
                "`json_object` is not supported by this model.'}}"
            )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok","findings":[]}'))]
        )


def test_review_findings_retries_without_response_format_when_model_rejects_json_object():
    client = OpenAICompatibleClient(base_url="https://example.com", api_key="token", model="model")
    fake_completions = FakeCompletions()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))

    payload = client.review_findings("review this")

    assert payload["findings"] == []
    assert len(fake_completions.calls) == 2
    assert fake_completions.calls[0]["response_format"]["type"] == "json_object"
    assert "response_format" not in fake_completions.calls[1]
