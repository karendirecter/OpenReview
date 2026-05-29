def build_review_request(model: str, prompt: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
