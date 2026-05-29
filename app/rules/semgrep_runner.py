from app.review.models import IssueHit


def parse_semgrep_output(payload: dict, commit_sha: str) -> list[IssueHit]:
    hits: list[IssueHit] = []
    for result in payload.get("results", []):
        hits.append(
            IssueHit(
                file_path=result["path"],
                line_number=result["start"]["line"],
                end_line_number=result["end"]["line"],
                commit_sha=commit_sha,
                rule_id=result["check_id"],
                severity=result["extra"]["severity"].lower(),
                message=result["extra"]["message"],
                evidence=result["extra"]["lines"],
            )
        )
    return hits
