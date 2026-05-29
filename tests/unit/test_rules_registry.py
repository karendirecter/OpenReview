from app.review.models import IssueHit
from app.rules.diff_general import GeneralDiffAnalyzer
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


def test_general_diff_analyzer_flags_broad_exception_pass():
    analyzer = GeneralDiffAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(
        file_path="app/service.py",
        diff="+except Exception:\n+    pass",
    )

    assert hits[0].rule_id == "diff.exception-swallow"


def test_general_diff_analyzer_flags_bare_except_pass():
    analyzer = GeneralDiffAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(
        file_path="app/service.py",
        diff="@@ -8,0 +9,2 @@\n+except:\n+    pass",
    )

    assert hits[0].rule_id == "diff.exception-swallow"
