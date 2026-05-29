from typing import Protocol

from app.review.models import IssueHit


class Analyzer(Protocol):
    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        ...
