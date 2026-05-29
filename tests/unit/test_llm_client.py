from app.llm.openai_compatible import build_review_request
from app.prompts.review_prompt import build_review_prompt


def test_build_review_request_targets_configured_model():
    request = build_review_request(
        model="deepseek-v4-flash-260425",
        prompt="review this",
    )

    assert request["model"] == "deepseek-v4-flash-260425"
    assert request["response_format"]["type"] == "json_object"


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
