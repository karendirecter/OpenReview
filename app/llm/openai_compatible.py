from json import loads

from openai import OpenAI

from app.config import Settings


def build_review_request(model: str, prompt: str, *, use_response_format: bool = True) -> dict:
    request = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if use_response_format:
        request["response_format"] = {"type": "json_object"}
    return request


class OpenAICompatibleClient:
    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenAICompatibleClient":
        return cls(base_url=settings.llm_base_url, api_key=settings.llm_api_key, model=settings.llm_model)

    def review_findings(self, prompt: str) -> dict:
        try:
            response = self._client.chat.completions.create(
                **build_review_request(model=self._model, prompt=prompt, use_response_format=True)
            )
        except Exception as exc:  # noqa: BLE001
            if not should_retry_without_response_format(exc):
                raise
            response = self._client.chat.completions.create(
                **build_review_request(model=self._model, prompt=prompt, use_response_format=False)
            )
        content = response.choices[0].message.content or "{}"
        return loads(content)


def should_retry_without_response_format(exc: Exception) -> bool:
    message = str(exc)
    return "response_format.type" in message and "not supported" in message
