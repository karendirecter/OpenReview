from app.review.schema import validate_llm_payload


def test_validate_llm_payload_rejects_unknown_file_path():
    payload = {
        "summary": "Found an issue",
        "findings": [
            {
                "file_path": "../../etc/passwd",
                "line_number": 2,
                "end_line_number": 2,
                "risk_level": "high",
                "verdict": "confirm",
                "issue_title": "Bad path",
                "issue_detail": "Bad path",
                "why_it_matters": "Bad path",
                "suggestion_rationale": "Fix path",
                "suggested_code": "safe = True",
                "original_code_snippet": "unsafe = True",
                "confidence": 0.91,
            }
        ],
    }

    findings = validate_llm_payload(payload, allowed_files={"app/service.py"}, review_commit_sha="abc123")

    assert findings == []
