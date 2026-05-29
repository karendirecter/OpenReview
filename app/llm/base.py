from typing import Protocol


class LLMClient(Protocol):
    def review_findings(self, prompt: str) -> dict:
        ...
