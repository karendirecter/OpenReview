import ast

from app.review.models import IssueHit


class PythonAstAnalyzer:
    def __init__(self, commit_sha: str) -> None:
        self.commit_sha = commit_sha

    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        tree = ast.parse(diff)
        hits: list[IssueHit] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        if getattr(child.func.value, "id", None) == "time" and child.func.attr == "sleep":
                            hits.append(
                                IssueHit(
                                    file_path=file_path,
                                    line_number=child.lineno,
                                    end_line_number=child.lineno,
                                    commit_sha=self.commit_sha,
                                    rule_id="python.async-blocking-io",
                                    severity="high",
                                    message="Blocking time.sleep used inside async function.",
                                    evidence="time.sleep(...)",
                                )
                            )
        return hits
