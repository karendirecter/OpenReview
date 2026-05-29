from app.review.models import IssueHit


def run_analyzers(analyzers: list, file_path: str, diff: str) -> list[IssueHit]:
    results: list[IssueHit] = []
    for analyzer in analyzers:
        results.extend(analyzer.analyze(file_path=file_path, diff=diff))
    return results
