from app.review.models import IssueHit
from app.rules.registry import run_analyzers


class FakeAnalyzer:
    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        return [
            IssueHit(
                file_path=file_path,
                line_number=4,
                end_line_number=4,
                commit_sha="head123",
                rule_id="fake.rule",
                severity="medium",
                message="flagged",
                evidence="evidence",
            )
        ]


def test_run_analyzers_collects_hits_from_all_plugins():
    hits = run_analyzers([FakeAnalyzer(), FakeAnalyzer()], file_path="app/a.py", diff="+x")

    assert len(hits) == 2
