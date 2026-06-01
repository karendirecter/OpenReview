from typing import Any, Literal

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
    review_run_id: str = ""
    repo_owner: str
    repo_name: str
    pr_number: int
    base_sha: str
    head_sha: str
    review_commit_sha: str
    selected_model: str | None = None
    trigger_type: Literal["command", "auto"]
    trigger_comment_id: int | None = None
    changed_files: list[ChangedFile] = Field(default_factory=list)


class IssueHit(BaseModel):
    file_path: str
    line_number: int
    end_line_number: int | None = None
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
    fix_intent: str = ""
    suggested_code: str
    original_code_snippet: str


class AgentTrace(BaseModel):
    agent_role: Literal["inspector", "fixer"]
    model_name: str
    prompt_version: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any] | str = Field(default_factory=dict)
    parsed_output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    token_usage: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    review_run_id: str = ""
    review_commit_sha: str
    summary: str
    overall_risk: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    render_mode: str
    agent_traces: list[AgentTrace] = Field(default_factory=list)


class RenderedComment(BaseModel):
    comment_type: str
    body: str
    file_path: str | None = None
    line_number: int | None = None
    end_line_number: int | None = None
    side: str | None = None
    commit_sha: str
