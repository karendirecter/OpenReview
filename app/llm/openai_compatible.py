from json import loads

from openai import OpenAI

from app.config import Settings


def build_review_request(model: str, prompt: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }


class OpenAICompatibleClient:
    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenAICompatibleClient":
        return cls(base_url=settings.llm_base_url, api_key=settings.llm_api_key, model=settings.llm_model)

    def review_findings(self, prompt: str) -> dict:
        response = self._client.chat.completions.create(**build_review_request(model=self._model, prompt=prompt))
        content = response.choices[0].message.content or "{}"
        return loads(content)
