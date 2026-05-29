from app.llm.openai_compatible import build_review_request


def test_build_review_request_targets_configured_model():
    request = build_review_request(
        model="deepseek-v4-flash-260425",
        prompt="review this",
    )

    assert request["model"] == "deepseek-v4-flash-260425"
    assert request["response_format"]["type"] == "json_object"
