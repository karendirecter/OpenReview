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


def test_validate_llm_payload_skips_invalid_entries_and_keeps_valid_findings():
    payload = {
        "summary": "Found an issue",
        "findings": [
            "this is not a finding object",
            {
                "file_path": "app/service.py",
                "line_number": 2,
                "end_line_number": 2,
                "risk_level": "high",
                "verdict": "confirm",
                "issue_title": "Missing null guard",
                "issue_detail": "value can be None",
                "why_it_matters": "This can crash at runtime",
                "suggestion_rationale": "Guard before access",
                "suggested_code": "return value or 0",
                "original_code_snippet": "return value.id",
                "confidence": 0.91,
            },
        ],
    }

    findings = validate_llm_payload(payload, allowed_files={"app/service.py"}, review_commit_sha="abc123")

    assert len(findings) == 1
    assert findings[0].file_path == "app/service.py"
    assert findings[0].issue_title == "Missing null guard"


def test_validate_llm_payload_drops_irrelevant_logging_suggestion():
    payload = {
        "summary": "Found an issue",
        "findings": [
            {
                "file_path": "app/service.py",
                "line_number": 2,
                "end_line_number": 2,
                "risk_level": "high",
                "verdict": "confirm",
                "issue_title": "Missing null guard",
                "issue_detail": "value can be None",
                "why_it_matters": "This can crash at runtime",
                "fix_intent": "Add a guard before attribute access",
                "suggestion_rationale": "Guard before access",
                "suggested_code": "import logging",
                "original_code_snippet": "return value.id",
                "confidence": 0.91,
            },
        ],
    }

    findings = validate_llm_payload(payload, allowed_files={"app/service.py"}, review_commit_sha="abc123")

    assert len(findings) == 1
    assert findings[0].suggested_code == ""


def test_validate_llm_payload_accepts_inspector_outputs_without_suggestion_fields():
    payload = {
        "summary": "Found an issue",
        "findings": [
            {
                "file_path": "app/service.py",
                "line_number": 2,
                "risk_level": "high",
                "verdict": "confirm",
                "issue_title": "Missing null guard",
                "issue_detail": "value can be None",
                "why_it_matters": "This can crash at runtime",
            }
        ],
    }

    findings = validate_llm_payload(payload, allowed_files={"app/service.py"}, review_commit_sha="abc123")

    assert len(findings) == 1
    assert findings[0].suggested_code == ""
