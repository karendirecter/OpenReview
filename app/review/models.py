from typing import Literal

from pydantic import BaseModel, Field


class ChangedFile(BaseModel):
    """
    Represents a changed file in a PR.

    文档缺陷标注：SPEC.md 6.2 定义了此模型，但 PLAN.md Task 2 没有包含此模型定义
    """
    file_path: str
    language: str | None = None
    status: str
    diff_hunks: list[str] = Field(default_factory=list)
    surrounding_context: list[str] = Field(default_factory=list)
    full_file_content: str | None = None
    position_mapping: dict[int, int] = Field(default_factory=dict)


class ReviewTask(BaseModel):
    """
    Represents a complete review task.

    文档缺陷标注：SPEC.md 6.1 定义了此模型的完整字段，PLAN.md Task 2 只给出了简化定义
    """
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
    """
    Represents a candidate issue from rule analysis layer.

    文档缺陷标注：SPEC.md 6.3 定义了此模型，PLAN.md Task 2 的定义基本正确但缺少文档说明
    """
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
    """
    Represents a final issue after LLM verification.

    文档缺陷标注：
    1. SPEC.md 6.4 定义了此模型，但 PLAN.md Task 2 完全没有包含此模型定义
    2. PLAN.md Task 5 才定义此模型，但应该在 Task 2 中与所有核心模型一起定义
    """
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
    """
    Represents aggregated review result after completion.

    文档缺陷标注：SPEC.md 6.5 定义了此模型，但 PLAN.md 完全没有包含此模型定义
    """
    review_commit_sha: str
    summary: str
    overall_risk: str
    findings: list[ReviewFinding]
    stats: dict[str, int] = Field(default_factory=dict)
    render_mode: str


class RenderedComment(BaseModel):
    """
    Represents a final comment ready to submit to GitHub.

    文档缺陷标注：SPEC.md 6.6 定义了此模型，但 PLAN.md 完全没有包含此模型定义
    """
    comment_type: str
    body: str
    file_path: str | None = None
    line_number: int | None = None
    end_line_number: int | None = None
    side: str | None = None
    commit_sha: str