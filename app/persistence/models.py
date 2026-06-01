from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewRunCreate(BaseModel):
    review_run_id: str
    repo_owner: str
    repo_name: str
    pr_number: int
    review_commit_sha: str
    trigger_type: str
    selected_model: str
    base_url: str
    status: str = "pending"
    task_payload: dict[str, Any] = Field(default_factory=dict)
    diff_snapshot: str = ""
    summary_snapshot: str = ""
    result_payload: dict[str, Any] = Field(default_factory=dict)
    rendered_comments: list[dict[str, Any]] = Field(default_factory=list)
    github_status: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class ReviewRunUpdate(BaseModel):
    status: str | None = None
    task_payload: dict[str, Any] | None = None
    summary_snapshot: str | None = None
    result_payload: dict[str, Any] | None = None
    rendered_comments: list[dict[str, Any]] | None = None
    github_status: dict[str, Any] | None = None
    completed_at: datetime | None = None


class ReviewRunRecord(ReviewRunCreate):
    pass


class AgentTraceCreate(BaseModel):
    review_run_id: str
    agent_role: str
    model_name: str
    prompt_version: str
    input_payload: dict[str, Any]
    raw_response: dict[str, Any] | str
    parsed_output: dict[str, Any]
    latency_ms: int | None = None
    token_usage: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class AgentTraceRecord(AgentTraceCreate):
    id: int


class ReviewRunDetail(BaseModel):
    run: ReviewRunRecord
    agent_traces: list[AgentTraceRecord] = Field(default_factory=list)
