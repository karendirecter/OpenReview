from app.rules.semgrep_runner import parse_semgrep_output


def test_parse_semgrep_output_returns_issue_hits():
    payload = {
        "results": [
            {
                "path": "app/repo.py",
                "start": {"line": 8},
                "end": {"line": 9},
                "check_id": "python.resource-leak",
                "extra": {
                    "severity": "WARNING",
                    "message": "Connection is not closed",
                    "lines": "conn = connect()",
                },
            }
        ]
    }

    hits = parse_semgrep_output(payload, commit_sha="head123")

    assert hits[0].rule_id == "python.resource-leak"
