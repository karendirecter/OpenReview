import re

from app.review.models import IssueHit


class GeneralDiffAnalyzer:
    def __init__(self, commit_sha: str) -> None:
        self.commit_sha = commit_sha

    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        lines = diff.splitlines()
        current_line = 1
        swallow_start: int | None = None

        for index, line in enumerate(lines):
            if line.startswith("@@"):
                header_match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if header_match:
                    current_line = int(header_match.group(1))
                continue

            if line.startswith("-") and not line.startswith("---"):
                continue

            added_or_context = not line.startswith("\\")
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                if "except Exception:" in content:
                    swallow_start = current_line
                elif swallow_start is not None and content.strip() == "pass":
                    return [
                        IssueHit(
                            file_path=file_path,
                            line_number=swallow_start,
                            end_line_number=current_line,
                            commit_sha=self.commit_sha,
                            rule_id="diff.exception-swallow",
                            severity="medium",
                            message="Broad exception handler swallows errors.",
                            evidence="except Exception: pass",
                        )
                    ]

            if added_or_context:
                current_line += 1

        return []
