from app.rules.python_ast import PythonAstAnalyzer


SOURCE = """
async def endpoint(user, fetch_remote):
    time.sleep(1)
    profile = user.profile
    return fetch_remote()
"""


def test_python_ast_analyzer_flags_blocking_sleep_in_async_function():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/api.py", diff=SOURCE)

    assert any(hit.rule_id == "python.async-blocking-io" for hit in hits)
