from app.review.models import IssueHit


class GeneralDiffAnalyzer:
    def __init__(self, commit_sha: str) -> None:
        self.commit_sha = commit_sha

    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        if "except Exception:" in diff and "pass" in diff:
            return [
                IssueHit(
                    file_path=file_path,
                    line_number=1,
                    end_line_number=2,
                    commit_sha=self.commit_sha,
                    rule_id="diff.exception-swallow",
                    severity="medium",
                    message="Broad exception handler swallows errors.",
                    evidence="except Exception: pass",
                )
            ]
        return []
