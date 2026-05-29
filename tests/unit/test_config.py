from app.config import Settings


def test_settings_load_required_review_defaults():
    settings = Settings(
        github_webhook_secret="secret",
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        github_trigger_mode="comment",
        llm_base_url="https://ark.cn-beijing.volces.com/api/v3/",
        llm_api_key="token",
        llm_model="deepseek-v4-flash-260425",
    )

    assert settings.github_trigger_mode == "comment"
    assert settings.enable_pull_request_auto_review is False
    assert settings.llm_model == "deepseek-v4-flash-260425"
