from app.review.schema import validate_llm_payload


def test_validate_llm_payload_drops_negative_line_number():
    payload = {
        "summary": "bad",
        "findings": [
            {
                "file_path": "app/a.py",
                "line_number": -3,
                "end_line_number": -1,
                "risk_level": "high",
                "verdict": "confirm",
                "issue_title": "Bad line",
                "issue_detail": "Bad line",
                "why_it_matters": "Bad line",
                "suggestion_rationale": "Fix",
                "suggested_code": "x = 1",
                "original_code_snippet": "x = y",
                "confidence": 0.8,
            }
        ],
    }

    assert validate_llm_payload(payload, {"app/a.py"}, "head123") == []


def test_validate_llm_payload_drops_reversed_line_range():
    payload = {
        "summary": "bad",
        "findings": [
            {
                "file_path": "app/a.py",
                "line_number": 8,
                "end_line_number": 3,
                "risk_level": "high",
                "verdict": "confirm",
                "issue_title": "Bad range",
                "issue_detail": "Bad range",
                "why_it_matters": "Bad range",
                "suggestion_rationale": "Fix",
                "suggested_code": "x = 1",
                "original_code_snippet": "x = y",
                "confidence": 0.8,
            }
        ],
    }

    assert validate_llm_payload(payload, {"app/a.py"}, "head123") == []
