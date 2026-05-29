from app.rules.python_ast import PythonAstAnalyzer


SOURCE = """
async def endpoint(user, fetch_remote):
    time.sleep(1)
    profile = user.profile
    return fetch_remote()
"""

NONE_SOURCE = """
def load_profile(data):
    profile = data.get("profile")
    return profile.name
"""

MISSING_AWAIT_SOURCE = """
async def endpoint(fetch_remote):
    return fetch_remote()
"""

REQUESTS_SOURCE = """
import requests

async def endpoint(url):
    return requests.get(url)
"""

ASYNCIO_SLEEP_SOURCE = """
import asyncio

async def endpoint():
    asyncio.sleep(1)
"""

SUBPROCESS_SOURCE = """
import subprocess

async def endpoint():
    subprocess.run(["git", "status"])
"""

RESOURCE_LEAK_SOURCE = """
def load_text(path):
    handle = open(path)
    return handle.read()
"""

OPTIONAL_ARG_SOURCE = """
def load_profile(profile=None):
    return profile.name
"""

NONE_SUBSCRIPT_SOURCE = """
def load_profile(data):
    profile = data.get("profile")
    return profile["name"]
"""


def test_python_ast_analyzer_flags_blocking_sleep_in_async_function():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/api.py", diff=SOURCE)

    assert any(hit.rule_id == "python.async-blocking-io" for hit in hits)


def test_python_ast_analyzer_flags_possible_none_dereference_from_dict_get():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/service.py", diff=NONE_SOURCE)

    assert any(hit.rule_id == "python.none-dereference" for hit in hits)


def test_python_ast_analyzer_flags_missing_await_in_async_function():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/async_service.py", diff=MISSING_AWAIT_SOURCE)

    assert any(hit.rule_id == "python.missing-await" for hit in hits)


def test_python_ast_analyzer_flags_sync_requests_in_async_function():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/http_service.py", diff=REQUESTS_SOURCE)

    assert any(hit.rule_id == "python.async-blocking-http" for hit in hits)


def test_python_ast_analyzer_flags_asyncio_sleep_without_await():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/async_service.py", diff=ASYNCIO_SLEEP_SOURCE)

    assert any(hit.rule_id == "python.missing-await" for hit in hits)


def test_python_ast_analyzer_flags_blocking_subprocess_in_async_function():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/process_service.py", diff=SUBPROCESS_SOURCE)

    assert any(hit.rule_id == "python.async-blocking-io" for hit in hits)


def test_python_ast_analyzer_flags_open_without_close():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/file_service.py", diff=RESOURCE_LEAK_SOURCE)

    assert any(hit.rule_id == "python.resource-leak" for hit in hits)


def test_python_ast_analyzer_flags_possible_none_dereference_from_optional_arg():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/service.py", diff=OPTIONAL_ARG_SOURCE)

    assert any(hit.rule_id == "python.none-dereference" for hit in hits)


def test_python_ast_analyzer_flags_possible_none_subscript_access():
    analyzer = PythonAstAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(file_path="app/service.py", diff=NONE_SUBSCRIPT_SOURCE)

    assert any(hit.rule_id == "python.none-dereference" for hit in hits)
