# GitHub PR Auto Review System Implementation Plan

## Commit Hash Map

- Task 1: `74cef1f`
- Task 2: `8e429ad`
- Task 3: `4c2fb1b`
- Task 4: `210a423`
- Task 5: `ab99bad`
- Task 6: `53f512b`
- Task 7: `8d53add`
- Task 8: `ce76860`
- Task 9: `44bc8d4`
- Task 10: `6362ef3`
- Task 11: `bb12a92`
- Task 12: `d2b6bce`
- Task 13: `15076be`
- Task 14: `1b64586`
- Task 15: `1b64586`
- Task 16: `1b64586`
- Task 17: `1b64586`
- Task 18: `1b64586`
- Task 19: `e34b9c3`
- Task 20: `e34b9c3`
- Task 21: `e34b9c3`
- Task 22: `e34b9c3`
- Task 23: `e34b9c3`
- Task 24: `e34b9c3`
- Task 25: `e34b9c3`
- Task 26: `e34b9c3`

**Execution note:** Before creating a new Python package directory under `app/` or `tests/`, create the directory itself and its matching `__init__.py` file in the same task so imports work consistently for cold-start implementers.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub App-driven PR auto review MVP that supports `/review` command triggering, two-stage correctness review, inline comments, and GitHub suggestions for Python-focused defects.

**Architecture:** The system is split into a thin GitHub integration shell, an orchestration layer, a reusable review core, a pluggable rule analysis layer, and a rendering layer. The MVP defaults to command-triggered review and uses Stage 1 rule hits plus Stage 2 LLM verification to produce structured review findings bound to a stable `review_commit_sha`.

**Tech Stack:** Python, FastAPI, PyGithub, pytest, uv, OpenAI-compatible LLM client for DeepSeek, Docker, docker-compose, Semgrep + Python AST heuristics

---

## Prerequisites Setup

**Before starting any task, complete and verify the repository and environment setup below.**

- [x] **Step 0.1: Verify the current Git repository state**

Run: `git status --short --branch`
Expected: The command succeeds and shows the current branch and working tree state.

- [x] **Step 0.2: Verify the remote repository configuration**

Run: `git remote -v`
Expected: An `origin` remote exists and points to the project repository; if no remote exists, stop and add the correct remote before continuing.

- [x] **Step 0.3: Switch to the cold-start branch**

Run: `git checkout cold-start || git checkout -b cold-start`
Expected: The current branch becomes `cold-start`.

- [x] **Step 0.4: Verify Python and uv prerequisites**

Run: `python --version && uv --version`
Expected: Python reports version `3.11` or newer, and `uv` is installed.

- [x] **Step 0.5: Create the initial directory skeleton**

Run: `mkdir -p app app/github app/review app/rules app/llm app/prompts scripts tests tests/unit tests/integration tests/integration/fixtures`
Expected: The application and test directories exist before any file-writing steps begin.

---

## File Structure

### Planned files and responsibilities

- Create: `pyproject.toml` — project metadata, dependencies, pytest config, scripts
- Create: `uv.lock` — dependency lockfile managed by uv
- Create: `app/__init__.py` — app package marker
- Create: `app/main.py` — FastAPI app bootstrap and webhook route registration
- Create: `app/config.py` — environment-backed settings and feature flags
- Create: `app/github/models.py` — GitHub webhook payload adapters and lightweight request models
- Create: `app/github/webhook.py` — webhook signature verification and event dispatching
- Create: `app/github/client.py` — PyGithub wrapper for PR data loading and comment posting
- Create: `app/review/models.py` — core domain models such as `ReviewTask`, `IssueHit`, `ReviewFinding`, `ReviewResult`
- Create: `app/review/diff_parser.py` — diff parsing and absolute line to review position mapping
- Create: `app/review/context_loader.py` — loading hunk, surrounding context, and full-file content when needed
- Create: `app/review/orchestrator.py` — Stage 1/Stage 2 review pipeline orchestration and staleness checks
- Create: `app/review/rendering.py` — PR summary, inline comment, and suggestion rendering
- Create: `app/review/schema.py` — JSON schema validation and business validation for LLM outputs
- Create: `app/rules/base.py` — pluggable analyzer protocol
- Create: `app/rules/diff_general.py` — language-agnostic diff heuristics
- Create: `app/rules/python_ast.py` — AST/heuristic Python correctness analyzers
- Create: `app/rules/semgrep_runner.py` — Semgrep-based supplemental analyzer
- Create: `app/rules/registry.py` — analyzer registration and Stage 1 execution entrypoint
- Create: `app/llm/base.py` — provider-neutral LLM client protocol
- Create: `app/llm/openai_compatible.py` — OpenAI SDK-compatible DeepSeek client implementation
- Create: `app/prompts/review_prompt.py` — structured prompt builder for Stage 2 review
- Create: `scripts/run_local_review.py` — local CLI/script entry for invoking review core without GitHub UI
- Create: `tests/conftest.py` — shared fixtures
- Create: `tests/unit/test_config.py` — settings parsing tests
- Create: `tests/unit/test_diff_parser.py` — diff parse and mapping tests
- Create: `tests/unit/test_context_loader.py` — context loading tests
- Create: `tests/unit/test_schema_validation.py` — JSON/schema/business validation tests
- Create: `tests/unit/test_rendering.py` — summary/inline/suggestion rendering tests
- Create: `tests/unit/test_rules_python_ast.py` — AST analyzer tests
- Create: `tests/unit/test_rules_semgrep_runner.py` — Semgrep adapter tests
- Create: `tests/unit/test_rules_registry.py` — analyzer registry tests
- Create: `tests/unit/test_llm_client.py` — LLM client abstraction tests
- Create: `tests/unit/test_orchestrator.py` — orchestration and stale commit handling tests
- Create: `tests/unit/test_robustness_llm_payloads.py` — malicious/invalid LLM payload regression tests
- Create: `tests/integration/test_github_webhook_route.py` — webhook route and `/review` command trigger tests
- Create: `tests/integration/test_review_pipeline.py` — Stage 1 + Stage 2 integration with fake GitHub data
- Create: `tests/integration/fixtures/sample_pr_diff.patch` — representative PR diff fixture
- Create: `tests/integration/fixtures/sample_python_file.py` — Python context fixture
- Create: `Dockerfile` — container image build
- Create: `docker-compose.yml` — local container orchestration for app runtime
- Create: `.env.example` — required environment variable template
- Modify: `AGENT_LOG.md` — append implementation-stage activity once coding begins
- Modify: `PLAN.md` — mark tasks complete and attach commit hashes during execution

### Directory boundaries

- `app/github/` owns GitHub-specific concerns only
- `app/review/` owns review-domain logic only
- `app/rules/` owns Stage 1 analyzers and plugin registration
- `app/llm/` owns provider integration only
- `app/prompts/` owns prompt construction only
- `scripts/` contains local developer tooling only
- `tests/unit/` validates isolated logic; `tests/integration/` validates cross-module workflows

---

### Task 1: Bootstrap project skeleton and settings

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `.env.example`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Test: `tests/unit/test_config.py`

- [x] **Step 1: Create package markers and the failing settings test**

Run: `mkdir -p tests/unit tests/integration`
Expected: The test package directories exist.

`tests/conftest.py`
```python
# Shared fixtures for the review system test suite.
```

`tests/unit/__init__.py`
```python
# Unit test package marker.
```

`tests/integration/__init__.py`
```python
# Integration test package marker.
```

`tests/unit/test_config.py`
```python
from app.config import Settings


def test_settings_load_required_review_defaults():
    settings = Settings(
        github_webhook_secret="secret",
        github_app_id="123",
        github_private_key="key",
        github_installation_id="456",
        github_trigger_mode="comment",
        llm_base_url="https://ark.cn-beijing.volces.com/api/v3/",
        llm_api_key="token",
        llm_model="deepseek-v4-flash-260425",
    )

    assert settings.github_trigger_mode == "comment"
    assert settings.enable_pull_request_auto_review is False
    assert settings.llm_model == "deepseek-v4-flash-260425"
```

- [x] **Step 2: Run test to verify it fails**

- [x] **Step 3: Write minimal project bootstrap and settings implementation**

`.gitignore`
```gitignore
__pycache__/
.pytest_cache/
.venv/
.env
coverage.xml
htmlcov/
```

`pyproject.toml`
```toml
[project]
name = "github-pr-auto-review"
version = "0.1.0"
description = "GitHub PR auto review MVP"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
  "pydantic>=2.9.0",
  "pydantic-settings>=2.5.0",
  "PyGithub>=2.4.0",
  "openai>=1.45.0",
  "python-multipart>=0.0.9",
  "jsonschema>=4.23.0",
  "unidiff>=0.7.5",
  "semgrep>=1.86.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-cov>=5.0.0",
  "httpx>=0.27.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`app/__init__.py`
```python
# Application package marker.
```

`app/config.py`
```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_webhook_secret: str = Field(...)
    github_app_id: str = Field(...)
    github_private_key: str = Field(...)
    github_installation_id: str = Field(...)
    github_trigger_mode: str = Field(default="comment")
    enable_pull_request_auto_review: bool = Field(default=False)
    llm_base_url: str = Field(...)
    llm_api_key: str = Field(...)
    llm_model: str = Field(...)
```

`app/main.py`
```python
from fastapi import FastAPI

app = FastAPI(title="GitHub PR Auto Review")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
```

`.env.example`
```env
GITHUB_WEBHOOK_SECRET=replace-me
GITHUB_APP_ID=replace-me
GITHUB_PRIVATE_KEY=replace-me
GITHUB_INSTALLATION_ID=replace-me
GITHUB_TRIGGER_MODE=comment
ENABLE_PULL_REQUEST_AUTO_REVIEW=false
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/
LLM_API_KEY=replace-me
LLM_MODEL=deepseek-v4-flash-260425
```

Environment variable notes:
- `LLM_BASE_URL` points to the Volcengine DeepSeek-compatible endpoint described in `SPEC.md`.
- `LLM_MODEL` defaults to the flash variant to keep local review costs lower.
- `GITHUB_TRIGGER_MODE=comment` means `/review` is the default trigger path.
- `ENABLE_PULL_REQUEST_AUTO_REVIEW=false` keeps automatic PR-triggered review disabled in the MVP.

- [x] **Step 4: Run test to verify it passes**

- [x] **Step 5: Commit<`74cef1f`>**

```bash
git add .gitignore pyproject.toml app/__init__.py app/main.py app/config.py .env.example tests/conftest.py tests/unit/__init__.py tests/integration/__init__.py tests/unit/test_config.py
git commit -m "feat: bootstrap app settings"
```

### Task 2: Define core review domain models

**Files:**
- Create: `app/review/__init__.py`
- Create: `app/review/models.py`
- Test: `tests/unit/test_models.py`

- [x] **Step 1: Write the failing domain model test**

`tests/unit/test_models.py`
```python
from app.review.models import IssueHit, RenderedComment, ReviewFinding, ReviewResult, ReviewTask


def test_review_task_binds_review_commit_sha():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=7,
        base_sha="base123",
        head_sha="head123",
        review_commit_sha="head123",
        trigger_type="command",
        trigger_comment_id=99,
        changed_files=[],
    )

    hit = IssueHit(
        file_path="app/service.py",
        line_number=10,
        end_line_number=12,
        commit_sha="head123",
        rule_id="python.none-access",
        severity="high",
        message="Possible None dereference",
        evidence="user.profile.name",
    )

    finding = ReviewFinding(
        file_path="app/service.py",
        line_number=10,
        end_line_number=12,
        commit_sha="head123",
        risk_level="high",
        confidence=0.91,
        issue_title="Possible None dereference",
        issue_detail="user.profile may be None.",
        why_it_matters="This can crash at runtime.",
        fix_strategy="Guard the access.",
        suggested_code="if user.profile is not None:\n    name = user.profile.name",
        original_code_snippet="name = user.profile.name",
    )

    result = ReviewResult(
        review_commit_sha="head123",
        summary="1 high-risk finding",
        overall_risk="high",
        findings=[finding],
        stats={"high": 1},
        render_mode="command",
    )

    comment = RenderedComment(
        comment_type="inline",
        body="body",
        file_path="app/service.py",
        line_number=10,
        end_line_number=12,
        side="RIGHT",
        commit_sha="head123",
    )

    assert task.review_commit_sha == hit.commit_sha == result.review_commit_sha == comment.commit_sha
```

- [x] **Step 2: Run test to verify it fails**

- [x] **Step 3: Write the complete review domain model module**

`app/review/__init__.py`
```python
# Review domain package marker.
```

`app/review/models.py`
```python
from typing import Literal

from pydantic import BaseModel, Field


class ChangedFile(BaseModel):
    file_path: str
    language: str | None = None
    status: str
    diff_hunks: list[str] = Field(default_factory=list)
    surrounding_context: list[str] = Field(default_factory=list)
    full_file_content: str | None = None
    position_mapping: dict[int, int] = Field(default_factory=dict)


class ReviewTask(BaseModel):
    repo_owner: str
    repo_name: str
    pr_number: int
    base_sha: str
    head_sha: str
    review_commit_sha: str
    trigger_type: Literal["command", "auto"]
    trigger_comment_id: int | None = None
    changed_files: list[ChangedFile]


class IssueHit(BaseModel):
    file_path: str
    line_number: int
    end_line_number: int = Field(default_factory=int)
    commit_sha: str
    rule_id: str
    severity: str
    message: str
    evidence: str
    original_code_snippet: str | None = None
    diff_position_hint: int | None = None


class ReviewFinding(BaseModel):
    file_path: str
    line_number: int
    end_line_number: int
    commit_sha: str
    risk_level: str
    confidence: float
    issue_title: str
    issue_detail: str
    why_it_matters: str
    fix_strategy: str
    suggested_code: str
    original_code_snippet: str


class ReviewResult(BaseModel):
    review_commit_sha: str
    summary: str
    overall_risk: str
    findings: list[ReviewFinding]
    stats: dict[str, int] = Field(default_factory=dict)
    render_mode: str


class RenderedComment(BaseModel):
    comment_type: str
    body: str
    file_path: str | None = None
    line_number: int | None = None
    end_line_number: int | None = None
    side: str | None = None
    commit_sha: str
```

- [x] **Step 4: Run test to verify it passes**


- [x] **Step 5: Commit<`8e429ad`>**

```bash
git add app/review/__init__.py app/review/models.py tests/unit/test_models.py
git commit -m "feat: add review domain models"
```

### Task 3: Parse diff hunks and map review positions

**Files:**
- Create: `app/review/diff_parser.py`
- Test: `tests/unit/test_diff_parser.py`
- Test: `tests/integration/fixtures/sample_pr_diff.patch`
- Test: `tests/integration/fixtures/sample_python_file.py`

- [x] **Step 1: Write the failing diff parser test and fixture files**

`tests/integration/fixtures/sample_pr_diff.patch`
```diff
@@ -1,3 +1,4 @@
 line1
-line2
+line2_changed
+line3
 line4
```

`tests/integration/fixtures/sample_python_file.py`
```python
async def endpoint(user, client):
    profile = user.profile
    return await client.fetch(profile)
```

`tests/unit/test_diff_parser.py`
```python
from app.review.diff_parser import build_position_mapping


SAMPLE_PATCH = """@@ -1,3 +1,4 @@
 line1
-line2
+line2_changed
+line3
 line4
"""


def test_build_position_mapping_returns_added_line_positions():
    mapping = build_position_mapping(SAMPLE_PATCH, new_start=1)

    assert mapping[2] == 3
    assert mapping[3] == 4
```

- [x] **Step 2: Run test to verify it fails**

- [x] **Step 3: Write minimal diff parser implementation**

`app/review/diff_parser.py`
```python
def build_position_mapping(patch: str, new_start: int) -> dict[int, int]:
    mapping: dict[int, int] = {}
    current_line = new_start
    position = 0

    for raw_line in patch.splitlines():
        if raw_line.startswith("@@"):
            continue
        position += 1
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            mapping[current_line] = position
            current_line += 1
            continue
        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        current_line += 1

    return mapping
```

Implementation note: this starter version proves the mapping contract for a single hunk. During later expansion, replace the manual parser with `unidiff`-based parsing so multi-hunk patches and GitHub review positions remain precise.

- [x] **Step 4: Run test to verify it passes**

- [x] **Step 5: Commit<`4c2fb1b`>**

### Task 4: Load hunk context and full-file fallback

**Files:**
- Create: `app/review/context_loader.py`
- Test: `tests/unit/test_context_loader.py`
- Test: `tests/integration/fixtures/sample_python_file.py`

- [x] **Step 1: Write the failing context loader test**

```python
from app.review.context_loader import select_review_context


def test_select_review_context_falls_back_to_full_file_when_needed():
    diff_hunks = ["@@ -10,2 +10,2 @@", "+result = user.profile.name"]
    file_content = "\n".join([f"line {i}" for i in range(1, 40)])

    context = select_review_context(
        diff_hunks=diff_hunks,
        file_content=file_content,
        use_full_file=True,
    )

    assert "result = user.profile.name" in context
    assert "line 39" in context
```

- [x] **Step 2: Run test to verify it fails**

- [x] **Step 3: Write minimal context loading implementation**

```python
def select_review_context(diff_hunks: list[str], file_content: str, use_full_file: bool) -> str:
    hunk_block = "\n".join(diff_hunks)
    if use_full_file:
        return f"[DIFF]\n{hunk_block}\n\n[FULL_FILE]\n{file_content}"
    return f"[DIFF]\n{hunk_block}"
```

- [x] **Step 4: Run test to verify it passes**

- [x] **Step 5: Commit<`210a423`>**

```bash
git add app/review/context_loader.py tests/unit/test_context_loader.py tests/integration/fixtures/sample_python_file.py
git commit -m "feat: add review context loader"
```

### Task 5: Validate LLM schema and business constraints

**Files:**
- Create: `app/review/schema.py`
- Test: `tests/unit/test_schema_validation.py`

- [x] **Step 1: Write the failing schema validation test**

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_validation.py::test_validate_llm_payload_rejects_unknown_file_path -v`
Expected: FAIL with missing `validate_llm_payload`

- [x] **Step 3: Write minimal schema validation implementation**

```python
from pydantic import BaseModel

from app.review.models import ReviewFinding


class RawFinding(BaseModel):
    file_path: str
    line_number: int
    end_line_number: int | None = None
    risk_level: str
    verdict: str
    issue_title: str
    issue_detail: str
    why_it_matters: str
    suggestion_rationale: str
    suggested_code: str
    original_code_snippet: str
    confidence: float


def validate_llm_payload(payload: dict, allowed_files: set[str], review_commit_sha: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    for item in payload.get("findings", []):
        raw = RawFinding.model_validate(item)
        if raw.file_path not in allowed_files:
            continue
        if raw.line_number <= 0:
            continue
        findings.append(
            ReviewFinding(
                file_path=raw.file_path,
                line_number=raw.line_number,
                end_line_number=raw.end_line_number or raw.line_number,
                commit_sha=review_commit_sha,
                risk_level=raw.risk_level,
                confidence=raw.confidence,
                issue_title=raw.issue_title,
                issue_detail=raw.issue_detail,
                why_it_matters=raw.why_it_matters,
                fix_strategy=raw.suggestion_rationale,
                suggested_code=raw.suggested_code,
                original_code_snippet=raw.original_code_snippet,
            )
        )

    return findings
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_validation.py::test_validate_llm_payload_rejects_unknown_file_path -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add app/review/schema.py tests/unit/test_schema_validation.py
git commit -m "feat: add llm payload validation"
```

### Task 6: Render PR summaries, inline comments, and suggestions

**Files:**
- Create: `app/review/rendering.py`
- Test: `tests/unit/test_rendering.py`

- [x] **Step 1: Write the failing rendering test**

```python
from app.review.models import ReviewFinding
from app.review.rendering import render_inline_comment


def test_render_inline_comment_wraps_suggestion_block():
    finding = ReviewFinding(
        file_path="app/api.py",
        line_number=18,
        end_line_number=19,
        commit_sha="head123",
        risk_level="high",
        confidence=0.94,
        issue_title="Blocking I/O in async route",
        issue_detail="requests.get blocks the event loop.",
        why_it_matters="This can degrade latency under concurrency.",
        fix_strategy="Use an async HTTP client.",
        suggested_code="async with httpx.AsyncClient() as client:\n    await client.get(url)",
        original_code_snippet="requests.get(url)",
    )

    body = render_inline_comment(finding)

    assert "```suggestion" in body
    assert "Blocking I/O in async route" in body
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_rendering.py::test_render_inline_comment_wraps_suggestion_block -v`
Expected: FAIL with missing `render_inline_comment`

- [x] **Step 3: Write minimal rendering implementation**

```python
from app.review.models import ReviewFinding


def render_inline_comment(finding: ReviewFinding) -> str:
    lines = [
        f"**{finding.issue_title}**",
        "",
        finding.issue_detail,
        "",
        f"Why it matters: {finding.why_it_matters}",
    ]
    if finding.suggested_code:
        lines.extend(
            [
                "",
                "```suggestion",
                finding.suggested_code,
                "```",
            ]
        )
    return "\n".join(lines)
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_rendering.py::test_render_inline_comment_wraps_suggestion_block -v`
Expected: PASS

- [x] **Step 5: Commit<`53f512b`>**

```bash
git add app/review/rendering.py tests/unit/test_rendering.py
git commit -m "feat: add review comment rendering"
```

### Task 7: Add pluggable analyzer protocol and registry

**Files:**
- Create: `app/rules/base.py`
- Create: `app/rules/registry.py`
- Test: `tests/unit/test_rules_registry.py`

- [x] **Step 1: Write the failing analyzer registry test**

```python
from app.review.models import IssueHit
from app.rules.registry import run_analyzers


class FakeAnalyzer:
    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        return [
            IssueHit(
                file_path=file_path,
                line_number=4,
                end_line_number=4,
                commit_sha="head123",
                rule_id="fake.rule",
                severity="medium",
                message="flagged",
                evidence="evidence",
            )
        ]


def test_run_analyzers_collects_hits_from_all_plugins():
    hits = run_analyzers([FakeAnalyzer(), FakeAnalyzer()], file_path="app/a.py", diff="+x")

    assert len(hits) == 2
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_rules_registry.py::test_run_analyzers_collects_hits_from_all_plugins -v`
Expected: FAIL with missing `run_analyzers`

- [x] **Step 3: Write minimal analyzer protocol and registry**

```python
from typing import Protocol

from app.review.models import IssueHit


class Analyzer(Protocol):
    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        ...
```

`app/rules/registry.py`
```python
from app.review.models import IssueHit


def run_analyzers(analyzers: list, file_path: str, diff: str) -> list[IssueHit]:
    results: list[IssueHit] = []
    for analyzer in analyzers:
        results.extend(analyzer.analyze(file_path=file_path, diff=diff))
    return results
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_rules_registry.py::test_run_analyzers_collects_hits_from_all_plugins -v`
Expected: PASS

- [x] **Step 5: Commit<`8d53add`>**

```bash
git add app/rules/base.py app/rules/registry.py tests/unit/test_rules_registry.py
git commit -m "feat: add pluggable rule registry"
```

### Task 8: Add general diff heuristics analyzer

**Files:**
- Create: `app/rules/diff_general.py`
- Test: `tests/unit/test_rules_registry.py`

- [x] **Step 1: Write the failing general diff rule test**

```python
from app.rules.diff_general import GeneralDiffAnalyzer


def test_general_diff_analyzer_flags_broad_exception_pass():
    analyzer = GeneralDiffAnalyzer(commit_sha="head123")
    hits = analyzer.analyze(
        file_path="app/service.py",
        diff="+except Exception:\n+    pass",
    )

    assert hits[0].rule_id == "diff.exception-swallow"
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_rules_registry.py::test_general_diff_analyzer_flags_broad_exception_pass -v`
Expected: FAIL with missing `GeneralDiffAnalyzer`

- [x] **Step 3: Write minimal general diff analyzer implementation**

```python
from app.review.models import IssueHit


class GeneralDiffAnalyzer:
    def __init__(self, commit_sha: str) -> None:
        self.commit_sha = commit_sha

    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        if "except Exception:" in diff and "pass" in diff:
            return [
                IssueHit(
                    file_path=file_path,
                    line_number=1,
                    end_line_number=2,
                    commit_sha=self.commit_sha,
                    rule_id="diff.exception-swallow",
                    severity="medium",
                    message="Broad exception handler swallows errors.",
                    evidence="except Exception: pass",
                )
            ]
        return []
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_rules_registry.py::test_general_diff_analyzer_flags_broad_exception_pass -v`
Expected: PASS

- [x] **Step 5: Commit<`ce76860`>**

```bash
git add app/rules/diff_general.py tests/unit/test_rules_registry.py
git commit -m "feat: add general diff heuristics"
```

### Task 9: Add Python AST analyzer for None access and async misuse

**Files:**
- Create: `app/rules/python_ast.py`
- Test: `tests/unit/test_rules_python_ast.py`

- [x] **Step 1: Write the failing Python AST analyzer test**

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_rules_python_ast.py::test_python_ast_analyzer_flags_blocking_sleep_in_async_function -v`
Expected: FAIL with missing `PythonAstAnalyzer`

- [x] **Step 3: Write minimal AST analyzer implementation**

```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_rules_python_ast.py::test_python_ast_analyzer_flags_blocking_sleep_in_async_function -v`
Expected: PASS

- [x] **Step 5: Commit<`44bc8d4`>**

```bash
git add app/rules/python_ast.py tests/unit/test_rules_python_ast.py
git commit -m "feat: add python ast analyzer"
```

### Task 10: Add Semgrep supplemental analyzer adapter

**Files:**
- Create: `app/rules/semgrep_runner.py`
- Test: `tests/unit/test_rules_semgrep_runner.py`

- [x] **Step 1: Write the failing Semgrep adapter test**

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_rules_semgrep_runner.py::test_parse_semgrep_output_returns_issue_hits -v`
Expected: FAIL with missing `parse_semgrep_output`

- [x] **Step 3: Write minimal Semgrep adapter implementation**

```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_rules_semgrep_runner.py::test_parse_semgrep_output_returns_issue_hits -v`
Expected: PASS

- [x] **Step 5: Commit<`6362ef3`>**

```bash
git add app/rules/semgrep_runner.py tests/unit/test_rules_semgrep_runner.py
git commit -m "feat: add semgrep analyzer adapter"
```

### Task 11: Add LLM client abstraction and OpenAI-compatible DeepSeek client

**Files:**
- Create: `app/llm/base.py`
- Create: `app/llm/openai_compatible.py`
- Test: `tests/unit/test_llm_client.py`

- [x] **Step 1: Write the failing LLM client test**

```python
from app.llm.openai_compatible import build_review_request


def test_build_review_request_targets_configured_model():
    request = build_review_request(
        model="deepseek-v4-flash-260425",
        prompt="review this",
    )

    assert request["model"] == "deepseek-v4-flash-260425"
    assert request["response_format"]["type"] == "json_object"
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_client.py::test_build_review_request_targets_configured_model -v`
Expected: FAIL with missing `build_review_request`

- [x] **Step 3: Write minimal LLM client implementation**

```python
from typing import Protocol


class LLMClient(Protocol):
    def review_findings(self, prompt: str) -> dict:
        ...
```

`app/llm/openai_compatible.py`
```python
def build_review_request(model: str, prompt: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_client.py::test_build_review_request_targets_configured_model -v`
Expected: PASS

- [x] **Step 5: Commit<`bb12a92`>**

```bash
git add app/llm/base.py app/llm/openai_compatible.py tests/unit/test_llm_client.py
git commit -m "feat: add openai-compatible llm client"
```

### Task 12: Add structured review prompt builder

**Files:**
- Create: `app/prompts/review_prompt.py`
- Test: `tests/unit/test_llm_client.py`

- [x] **Step 1: Write the failing prompt builder test**

```python
from app.prompts.review_prompt import build_review_prompt


def test_build_review_prompt_includes_commit_sha_and_json_contract():
    prompt = build_review_prompt(
        review_commit_sha="head123",
        file_path="app/api.py",
        diff_context="+ time.sleep(1)",
        candidate_summary="Blocking I/O candidate",
    )

    assert "head123" in prompt
    assert '"findings"' in prompt
    assert "Do not return extra text" in prompt
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_client.py::test_build_review_prompt_includes_commit_sha_and_json_contract -v`
Expected: FAIL with missing `build_review_prompt`

- [x] **Step 3: Write minimal prompt builder implementation**

```python
def build_review_prompt(review_commit_sha: str, file_path: str, diff_context: str, candidate_summary: str) -> str:
    return f"""
You are reviewing code for correctness.
Review commit SHA: {review_commit_sha}
File: {file_path}
Candidate issue: {candidate_summary}
Diff and context:
{diff_context}
Return strict JSON with keys: summary, findings.
Do not return extra text.
""".strip()
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_client.py::test_build_review_prompt_includes_commit_sha_and_json_contract -v`
Expected: PASS

- [x] **Step 5: Commit<`d2b6bce`>**

```bash
git add app/prompts/review_prompt.py tests/unit/test_llm_client.py
git commit -m "feat: add structured review prompt builder"
```

### Task 13: Build Stage 1 + Stage 2 orchestrator with stale commit guard

**Files:**
- Create: `app/review/orchestrator.py`
- Test: `tests/unit/test_orchestrator.py`
- Test: `tests/integration/test_review_pipeline.py`

- [x] **Step 1: Write the failing orchestrator stale commit test**

```python
import pytest

from app.review.models import ReviewTask
from app.review.orchestrator import ensure_not_stale


def test_ensure_not_stale_raises_when_head_sha_changes():
    task = ReviewTask(
        repo_owner="octo",
        repo_name="demo",
        pr_number=1,
        base_sha="base123",
        head_sha="newhead",
        review_commit_sha="oldhead",
        trigger_type="command",
        changed_files=[],
    )

    with pytest.raises(RuntimeError, match="stale review commit"):
        ensure_not_stale(task)
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_orchestrator.py::test_ensure_not_stale_raises_when_head_sha_changes -v`
Expected: FAIL with missing `ensure_not_stale`

- [x] **Step 3: Write minimal orchestrator implementation**

```python
from app.review.models import ReviewTask


def ensure_not_stale(task: ReviewTask) -> None:
    if task.head_sha != task.review_commit_sha:
        raise RuntimeError("stale review commit")
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_orchestrator.py::test_ensure_not_stale_raises_when_head_sha_changes -v`
Expected: PASS

- [x] **Step 5: Commit<`15076be`>**

```bash
git add app/review/orchestrator.py tests/unit/test_orchestrator.py tests/integration/test_review_pipeline.py
git commit -m "feat: add review orchestrator guards"
```

### Task 14: Add robustness tests for malicious LLM payloads

**Files:**
- Create: `tests/unit/test_robustness_llm_payloads.py`
- Modify: `app/review/schema.py`

- [x] **Step 1: Write the failing malicious payload regression tests**

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_robustness_llm_payloads.py::test_validate_llm_payload_drops_negative_line_number -v`
Expected: FAIL if negative line numbers are not rejected

- [x] **Step 3: Tighten payload validation implementation**

```python
def validate_llm_payload(payload: dict, allowed_files: set[str], review_commit_sha: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    for item in payload.get("findings", []):
        raw = RawFinding.model_validate(item)
        if raw.file_path not in allowed_files:
            continue
        if raw.line_number <= 0:
            continue
        if raw.end_line_number is not None and raw.end_line_number < raw.line_number:
            continue
        findings.append(
            ReviewFinding(
                file_path=raw.file_path,
                line_number=raw.line_number,
                end_line_number=raw.end_line_number or raw.line_number,
                commit_sha=review_commit_sha,
                risk_level=raw.risk_level,
                confidence=raw.confidence,
                issue_title=raw.issue_title,
                issue_detail=raw.issue_detail,
                why_it_matters=raw.why_it_matters,
                fix_strategy=raw.suggestion_rationale,
                suggested_code=raw.suggested_code,
                original_code_snippet=raw.original_code_snippet,
            )
        )

    return findings
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_robustness_llm_payloads.py::test_validate_llm_payload_drops_negative_line_number -v`
Expected: PASS

- [x] **Step 5: Commit<`1b64586`>**

```bash
git add app/review/schema.py tests/unit/test_robustness_llm_payloads.py
git commit -m "test: harden malicious llm payload handling"
```

### Task 15: Add GitHub webhook command trigger route

**Files:**
- Create: `app/github/models.py`
- Create: `app/github/webhook.py`
- Test: `tests/integration/test_github_webhook_route.py`
- Modify: `app/main.py`

- [x] **Step 1: Write the failing webhook route test**

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_github_webhook_ignores_non_review_comment():
    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "issue_comment"},
        json={"comment": {"body": "hello"}, "issue": {"pull_request": {"url": "x"}}},
    )

    assert response.status_code == 202
    assert response.json() == {"status": "ignored"}
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_github_webhook_route.py::test_github_webhook_ignores_non_review_comment -v`
Expected: FAIL with missing route or wrong response

- [x] **Step 3: Write minimal webhook route implementation**

`app/github/webhook.py`
```python
def should_trigger_review(event_name: str, payload: dict) -> bool:
    if event_name != "issue_comment":
        return False
    if "pull_request" not in payload.get("issue", {}):
        return False
    return payload.get("comment", {}).get("body", "").strip() == "/review"
```

`app/main.py`
```python
from fastapi import FastAPI, Request

from app.github.webhook import should_trigger_review

app = FastAPI(title="GitHub PR Auto Review")


@app.post("/webhooks/github")
async def github_webhook(request: Request) -> dict[str, str]:
    payload = await request.json()
    event_name = request.headers.get("X-GitHub-Event", "")
    if not should_trigger_review(event_name, payload):
        return {"status": "ignored"}
    return {"status": "accepted"}
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_github_webhook_route.py::test_github_webhook_ignores_non_review_comment -v`
Expected: PASS

- [x] **Step 5: Commit<`1b64586`>**

```bash
git add app/github/models.py app/github/webhook.py app/main.py tests/integration/test_github_webhook_route.py
git commit -m "feat: add github review command webhook"
```

### Task 16: Add local review script entrypoint

**Files:**
- Create: `scripts/run_local_review.py`
- Test: `tests/integration/test_review_pipeline.py`

- [x] **Step 1: Write the failing local review entry test**

```python
from scripts.run_local_review import build_local_task


def test_build_local_task_sets_command_trigger_type():
    task = build_local_task(repo_owner="octo", repo_name="demo", pr_number=8, review_commit_sha="head123")

    assert task.trigger_type == "command"
    assert task.review_commit_sha == "head123"
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_review_pipeline.py::test_build_local_task_sets_command_trigger_type -v`
Expected: FAIL with missing `build_local_task`

- [x] **Step 3: Write minimal local review script implementation**

```python
from app.review.models import ReviewTask


def build_local_task(repo_owner: str, repo_name: str, pr_number: int, review_commit_sha: str) -> ReviewTask:
    return ReviewTask(
        repo_owner=repo_owner,
        repo_name=repo_name,
        pr_number=pr_number,
        base_sha=review_commit_sha,
        head_sha=review_commit_sha,
        review_commit_sha=review_commit_sha,
        trigger_type="command",
        changed_files=[],
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_review_pipeline.py::test_build_local_task_sets_command_trigger_type -v`
Expected: PASS

- [x] **Step 5: Commit<`1b64586`>**

```bash
git add scripts/run_local_review.py tests/integration/test_review_pipeline.py
git commit -m "feat: add local review entrypoint"
```

### Task 17: Add Docker packaging and local runtime docs skeleton

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Modify: `.env.example`

- [x] **Step 1: Write the failing container smoke test command expectation**

```text
Command to validate after implementation:
docker build -t github-pr-auto-review .
Expected: image builds successfully

docker compose up --build
Expected: FastAPI app starts and exposes the webhook service
```

- [x] **Step 2: Run container validation to verify it fails before packaging exists**

Run: `docker build -t github-pr-auto-review .`
Expected: FAIL with missing `Dockerfile`

- [x] **Step 3: Write minimal container packaging files**

`Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install uv && uv pip install --system .
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml`
```yaml
services:
  review-app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
```

- [x] **Step 4: Run container validation to verify it passes**

Run: `docker build -t github-pr-auto-review . && docker compose up --build`
Expected: image builds successfully and FastAPI starts on port 8000

- [x] **Step 5: Commit<`1b64586`>**

```bash
git add Dockerfile docker-compose.yml .env.example
git commit -m "feat: add container packaging"
```

### Task 18: Final verification and plan bookkeeping

**Files:**
- Modify: `PLAN.md`
- Modify: `AGENT_LOG.md`

- [x] **Step 1: Run the unit test suite**

Run: `uv run pytest tests/unit -v`
Expected: PASS

- [x] **Step 2: Run the integration test suite**

Run: `uv run pytest tests/integration -v`
Expected: PASS

- [x] **Step 3: Run the full test suite**

Run: `uv run pytest -v`
Expected: PASS

- [x] **Step 4: Update project tracking files**

`PLAN.md`
```markdown
- [x] Task N complete (`<commit-hash>`)
```

`AGENT_LOG.md`
```markdown
- 2026-05-27 — Task N — superpowers:test-driven-development — Added <feature>; manual intervention: <reason>
```

- [x] **Step 5: Commit<`1b64586`>**

```bash
git add PLAN.md AGENT_LOG.md
git commit -m "docs: update project plan tracking"
```

### Task 19: Add review run persistence and history query backbone

**Files:**
- Create: `app/persistence/__init__.py`
- Create: `app/persistence/models.py`
- Create: `app/persistence/repository.py`
- Modify: `app/config.py`
- Test: `tests/unit/test_review_run_repository.py`

- [x] **Step 1: Write the failing persistence repository tests**

```python
from app.persistence.models import ReviewRunCreate
from app.persistence.repository import ReviewRunRepository


def test_repository_can_save_and_list_review_runs(tmp_path):
    repo = ReviewRunRepository.for_sqlite(tmp_path / "review_runs.db")

    created = repo.create_run(
        ReviewRunCreate(
            review_run_id="run-1",
            repo_owner="octo",
            repo_name="demo",
            pr_number=9,
            review_commit_sha="abc123",
            trigger_type="command",
            selected_model="deepseek-v4-flash-260425",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
        )
    )

    listed = repo.list_runs(limit=10)

    assert created.review_run_id == "run-1"
    assert listed[0].selected_model == "deepseek-v4-flash-260425"
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_review_run_repository.py -v`
Expected: FAIL with missing persistence module

- [x] **Step 3: Implement the minimal persistence layer**

```python
class ReviewRunRepository:
    @classmethod
    def for_sqlite(cls, db_path: Path) -> "ReviewRunRepository":
        ...

    def create_run(self, payload: ReviewRunCreate) -> ReviewRunRecord:
        ...

    def list_runs(self, limit: int = 20) -> list[ReviewRunRecord]:
        ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_review_run_repository.py -v`
Expected: PASS

### Task 20: Split Stage 2 into inspector and fixer agents

**Files:**
- Modify: `app/prompts/review_prompt.py`
- Modify: `app/review/orchestrator.py`
- Modify: `app/review/models.py`
- Modify: `app/review/schema.py`
- Test: `tests/unit/test_dual_agent_prompt.py`
- Test: `tests/unit/test_orchestrator.py`

- [x] **Step 1: Write the failing dual-agent orchestration tests**

```python
from app.review.orchestrator import run_stage2_agents


def test_run_stage2_agents_passes_inspector_output_to_fixer(fake_llm_client, sample_review_task, sample_issue_hit):
    result = run_stage2_agents(
        llm_client=fake_llm_client,
        task=sample_review_task,
        issue_hits=[sample_issue_hit],
    )

    assert result.findings[0].issue_title == "Possible None dereference"
    assert result.findings[0].suggested_code.startswith("if user is None:")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_dual_agent_prompt.py tests/unit/test_orchestrator.py -v`
Expected: FAIL with missing dual-agent flow

- [x] **Step 3: Implement dual-agent prompt contracts and orchestration**

```python
def build_inspector_prompt(...) -> PromptPayload:
    ...


def build_fixer_prompt(...) -> PromptPayload:
    ...


def run_stage2_agents(...) -> Stage2AgentResult:
    ...
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_dual_agent_prompt.py tests/unit/test_orchestrator.py -v`
Expected: PASS

### Task 21: Persist agent traces and expose review history APIs

**Files:**
- Create: `app/visualization/__init__.py`
- Create: `app/visualization/router.py`
- Create: `app/visualization/service.py`
- Modify: `app/main.py`
- Modify: `app/review/orchestrator.py`
- Test: `tests/integration/test_review_runs_api.py`

- [x] **Step 1: Write the failing history API tests**

```python
def test_get_review_runs_returns_persisted_history(client, seeded_review_run):
    response = client.get("/api/review-runs")

    assert response.status_code == 200
    assert response.json()["items"][0]["review_run_id"] == seeded_review_run.review_run_id


def test_get_review_run_detail_returns_agent_traces(client, seeded_review_run):
    response = client.get(f"/api/review-runs/{seeded_review_run.review_run_id}")

    assert response.status_code == 200
    assert "agent_traces" in response.json()
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_review_runs_api.py -v`
Expected: FAIL with missing API routes

- [x] **Step 3: Implement persistence wiring and API routes**

```python
@router.get("/api/review-runs")
def list_review_runs(...) -> ReviewRunListResponse:
    ...


@router.get("/api/review-runs/{review_run_id}")
def get_review_run_detail(...) -> ReviewRunDetailResponse:
    ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_review_runs_api.py -v`
Expected: PASS

### Task 22: Add local replay and controlled model switching

**Files:**
- Modify: `app/config.py`
- Modify: `app/llm/openai_compatible.py`
- Create: `app/visualization/replay_service.py`
- Modify: `app/visualization/router.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_replay_service.py`

- [x] **Step 1: Write the failing model whitelist and replay tests**

```python
from app.visualization.replay_service import replay_review_run


def test_allowed_models_are_whitelisted(settings):
    assert settings.allowed_llm_models == [
        "deepseek-v4-flash-260425",
        "doubao-seed-2-0-code-preview-260215",
        "doubao-seed-1-8-251228",
    ]


def test_replay_review_run_uses_selected_model_without_changing_base_url(fake_repository, fake_llm_client):
    replayed = replay_review_run(
        repository=fake_repository,
        llm_client=fake_llm_client,
        review_run_id="run-1",
        model_name="doubao-seed-2-0-code-preview-260215",
        publish_to_github=False,
    )

    assert replayed.selected_model == "doubao-seed-2-0-code-preview-260215"
    assert replayed.base_url == "https://ark.cn-beijing.volces.com/api/v3/"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_config.py tests/unit/test_replay_service.py -v`
Expected: FAIL with missing replay service or model whitelist

- [x] **Step 3: Implement whitelist-based model switching and replay service**

```python
class Settings(BaseSettings):
    allowed_llm_models: list[str] = [...]


def replay_review_run(...) -> ReviewRunRecord:
    ...
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_config.py tests/unit/test_replay_service.py -v`
Expected: PASS

### Task 23: Build the local visualization frontend

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/ReviewRunListPage.tsx`
- Create: `frontend/src/pages/ReviewRunDetailPage.tsx`
- Create: `frontend/src/components/DiffViewer.tsx`
- Create: `frontend/src/components/ModelSwitcher.tsx`
- Create: `frontend/src/styles.css`

- [x] **Step 1: Write the failing frontend smoke expectations**

```text
Command to validate after implementation:
npm install --prefix frontend
npm run --prefix frontend build
Expected: frontend builds successfully
```

- [x] **Step 2: Run frontend build to verify it fails before files exist**

Run: `npm run --prefix frontend build`
Expected: FAIL with missing frontend package

- [x] **Step 3: Implement the minimal local UI**

```tsx
export function ReviewRunDetailPage() {
  return (
    <>
      <ModelSwitcher />
      <DiffViewer />
      <section data-testid="inspector-output" />
      <section data-testid="fixer-output" />
    </>
  );
}
```

- [x] **Step 4: Run frontend build to verify it passes**

Run: `npm run --prefix frontend build`
Expected: PASS

### Task 24: Add suggestion-quality regression coverage

**Files:**
- Modify: `tests/integration/fixtures/sample_pr_diff.patch`
- Create: `tests/integration/fixtures/sample_pr_diff_with_bug.patch`
- Create: `tests/integration/test_review_replay_flow.py`
- Modify: `tests/integration/test_review_pipeline.py`

- [x] **Step 1: Write the failing regression test for meaningful suggestions**

```python
def test_replay_flow_generates_bug_related_suggestion(client, seeded_buggy_review_run):
    response = client.post(
        f"/api/review-runs/{seeded_buggy_review_run.review_run_id}/replay",
        json={"model_name": "deepseek-v4-flash-260425", "publish_to_github": False},
    )

    assert response.status_code == 200
    finding = response.json()["findings"][0]
    assert "None" in finding["issue_title"] or "await" in finding["issue_title"]
    assert "import logging" not in finding["suggested_code"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_review_replay_flow.py tests/integration/test_review_pipeline.py -v`
Expected: FAIL with missing replay quality checks

- [x] **Step 3: Tighten validation to reject irrelevant suggestions**

```python
def suggestion_matches_confirmed_issue(finding: ReviewFinding) -> bool:
    ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_review_replay_flow.py tests/integration/test_review_pipeline.py -v`
Expected: PASS

### Task 25: Document local UI workflow and complete verification

**Files:**
- Modify: `README.md`
- Modify: `AGENT_LOG.md`
- Modify: `PLAN.md`

- [x] **Step 1: Write the documentation completion checklist**

```text
README must include:
- backend start command
- frontend start/build command
- database path and reset method
- model switching limitations
- replay flow usage
```

- [x] **Step 2: Run the full verification suite**

Run: `uv run pytest -v`
Expected: PASS

Run: `npm run --prefix frontend build`
Expected: PASS

- [x] **Step 3: Update tracking files**

`AGENT_LOG.md`
```markdown
- 2026-06-01 — Task 19-25 — superpowers:test-driven-development — Added visualization UI, review history persistence, model switching, and dual-agent replay flow; manual intervention: local model credentials supplied via `.env`
```

`PLAN.md`
```markdown
- [x] Task 19 complete (``e34b9c3``)
- [x] Task 20 complete (``e34b9c3``)
- [x] Task 21 complete (``e34b9c3``)
- [x] Task 22 complete (``e34b9c3``)
- [x] Task 23 complete (``e34b9c3``)
- [x] Task 24 complete (``e34b9c3``)
- [x] Task 25 complete (``e34b9c3``)
```

- [x] **Step 4: Commit**

```bash
git add .
git commit -m "feat: add local review visualization"
```

### Task 26: Add task locking, recoverable queueing, and stale-run cancellation

**Files:**
- Create: `app/review/queue.py`
- Create: `app/runtime.py`
- Modify: `app/config.py`
- Modify: `app/main.py`
- Modify: `app/github/service.py`
- Modify: `app/persistence/repository.py`
- Modify: `docker-compose.yml`
- Test: `tests/unit/test_review_queue.py`
- Modify: `tests/unit/test_review_run_repository.py`
- Modify: `tests/integration/test_github_webhook_route.py`
- Modify: `tests/integration/test_github_review_service.py`
- Modify: `tests/integration/test_review_runs_api.py`

- [x] **Step 1: Write failing tests for queue behavior and stale-run handling**

```python
def test_queue_runs_different_prs_in_parallel_but_serializes_same_pr():
    ...

def test_process_review_run_marks_stale_when_pr_head_has_advanced(tmp_path):
    ...
```

- [x] **Step 2: Introduce PR-scoped queue and state transitions**

```python
class ReviewQueueManager:
    ...

def enqueue_issue_comment(...):
    ...

def process_review_run(...):
    ...
```

- [x] **Step 3: Recover queued/running tasks after restart and persist history across Docker rebuilds**

```python
def recover_pending_runs(self) -> None:
    ...
```

`docker-compose.yml`
```yaml
volumes:
  - review-data:/app/.data
```

- [x] **Step 4: Verify queueing, recovery, and full regression suite**

Run: `uv run pytest tests/integration/test_review_runs_api.py tests/integration/test_github_webhook_route.py tests/integration/test_github_review_service.py tests/unit/test_review_queue.py tests/unit/test_review_run_repository.py -q`
Expected: PASS

Run: `uv run pytest -q`
Expected: PASS

---

## Self-Review

### Spec coverage

- GitHub App `/review` trigger: covered by Tasks 1, 15, 16
- Review core and domain models: covered by Tasks 2, 3, 4, 5, 6, 13
- Pluggable Stage 1 rules: covered by Tasks 7, 8, 9, 10
- OpenAI-compatible DeepSeek client and prompt contract: covered by Tasks 11, 12
- Malicious/invalid LLM payload handling: covered by Tasks 5 and 14
- Containerization: covered by Task 17
- Plan bookkeeping and verification: covered by Task 18
- Review history persistence and query APIs: covered by Tasks 19 and 21
- Dual-agent prompt pipeline and suggestion validation: covered by Tasks 20 and 24
- Controlled model switching and local replay: covered by Task 22
- Local visualization frontend: covered by Tasks 23 and 25
- PR-level locking, recoverable queueing, and stale-run cancellation: covered by Task 26

### Placeholder scan

- All tasks include exact file paths
- Each code-writing step includes concrete code blocks
- Each verification step includes exact commands and expected outcomes
- No task uses `TODO`, `TBD`, or “similar to task above” placeholders

### Type consistency

- Core types used consistently across tasks: `ReviewTask`, `ChangedFile`, `IssueHit`, `ReviewFinding`
- New persistence/debugging types are explicit in the plan: `ReviewRun`, `AgentTrace`
- Review trigger values consistently use `"command"` and `"auto"`
- Commit binding consistently uses `review_commit_sha`

---
