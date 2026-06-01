from pathlib import Path

from pydantic import Field, field_validator
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
    allowed_llm_models: list[str] = Field(
        default_factory=lambda: [
            "deepseek-v4-flash-260425",
            "doubao-seed-2-0-code-preview-260215",
            "doubao-seed-1-8-251228",
        ]
    )
    review_db_path: Path = Field(default=Path(".data") / "review_runs.db")

    @field_validator("github_private_key")
    @classmethod
    def normalize_github_private_key(cls, value: str) -> str:
        return value.replace("\\n", "\n").strip()

    @field_validator("allowed_llm_models", mode="before")
    @classmethod
    def normalize_allowed_llm_models(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("llm_model")
    @classmethod
    def ensure_llm_model_is_allowed(cls, value: str, info) -> str:
        allowed = info.data.get("allowed_llm_models") or []
        if allowed and value not in allowed:
            raise ValueError("llm_model must be included in allowed_llm_models")
        return value
