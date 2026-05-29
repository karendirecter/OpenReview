from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_webhook_secret: str = Field(...)
    github_app_id: str = Field(...)
    github_private_key: str = Field(...)
    github_installation_id: str = Field(...)
    github_trigger_mode: str = Field(default="comment")
    enable_pull_request_auto_review: bool = Field(default=False)
    llm_base_url: str = Field(...)
    llm_api_key: str = Field(...)
    llm_model: str = Field(...)
