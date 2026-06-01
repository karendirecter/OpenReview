import json
import sqlite3
from pathlib import Path

from app.persistence.models import (
    AgentTraceCreate,
    AgentTraceRecord,
    ReviewRunCreate,
    ReviewRunDetail,
    ReviewRunRecord,
    ReviewRunUpdate,
)


class ReviewRunRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def for_sqlite(cls, db_path: Path) -> "ReviewRunRepository":
        return cls(db_path)

    def create_run(self, payload: ReviewRunCreate) -> ReviewRunRecord:
        with self._connect() as connection:
            connection.execute(
                """
                insert into review_runs (
                    review_run_id,
                    repo_owner,
                    repo_name,
                    pr_number,
                    review_commit_sha,
                    trigger_type,
                    selected_model,
                    base_url,
                    status,
                    task_payload,
                    diff_snapshot,
                    summary_snapshot,
                    result_payload,
                    rendered_comments,
                    github_status,
                    created_at,
                    completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.review_run_id,
                    payload.repo_owner,
                    payload.repo_name,
                    payload.pr_number,
                    payload.review_commit_sha,
                    payload.trigger_type,
                    payload.selected_model,
                    payload.base_url,
                    payload.status,
                    json.dumps(payload.task_payload),
                    payload.diff_snapshot,
                    payload.summary_snapshot,
                    json.dumps(payload.result_payload),
                    json.dumps(payload.rendered_comments),
                    json.dumps(payload.github_status),
                    payload.created_at.isoformat(),
                    payload.completed_at.isoformat() if payload.completed_at else None,
                ),
            )
        return self.get_run(payload.review_run_id)

    def update_run(self, review_run_id: str, payload: ReviewRunUpdate) -> ReviewRunRecord:
        existing = self.get_run(review_run_id)
        merged = existing.model_copy(
            update={
                "status": payload.status if payload.status is not None else existing.status,
                "task_payload": payload.task_payload if payload.task_payload is not None else existing.task_payload,
                "summary_snapshot": payload.summary_snapshot
                if payload.summary_snapshot is not None
                else existing.summary_snapshot,
                "result_payload": payload.result_payload
                if payload.result_payload is not None
                else existing.result_payload,
                "rendered_comments": payload.rendered_comments
                if payload.rendered_comments is not None
                else existing.rendered_comments,
                "github_status": payload.github_status
                if payload.github_status is not None
                else existing.github_status,
                "completed_at": payload.completed_at if payload.completed_at is not None else existing.completed_at,
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                update review_runs
                set status = ?,
                    task_payload = ?,
                    summary_snapshot = ?,
                    result_payload = ?,
                    rendered_comments = ?,
                    github_status = ?,
                    completed_at = ?
                where review_run_id = ?
                """,
                (
                    merged.status,
                    json.dumps(merged.task_payload),
                    merged.summary_snapshot,
                    json.dumps(merged.result_payload),
                    json.dumps(merged.rendered_comments),
                    json.dumps(merged.github_status),
                    merged.completed_at.isoformat() if merged.completed_at else None,
                    review_run_id,
                ),
            )
        return self.get_run(review_run_id)

    def save_agent_trace(self, payload: AgentTraceCreate) -> AgentTraceRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                insert into agent_traces (
                    review_run_id,
                    agent_role,
                    model_name,
                    prompt_version,
                    input_payload,
                    raw_response,
                    parsed_output,
                    latency_ms,
                    token_usage,
                    created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.review_run_id,
                    payload.agent_role,
                    payload.model_name,
                    payload.prompt_version,
                    json.dumps(payload.input_payload),
                    json.dumps(payload.raw_response),
                    json.dumps(payload.parsed_output),
                    payload.latency_ms,
                    json.dumps(payload.token_usage),
                    payload.created_at.isoformat(),
                ),
            )
            trace_id = int(cursor.lastrowid)
        return AgentTraceRecord(id=trace_id, **payload.model_dump())

    def list_runs(self, limit: int = 20) -> list[ReviewRunRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from review_runs
                order by created_at desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_run(self, review_run_id: str) -> ReviewRunRecord:
        with self._connect() as connection:
            row = connection.execute(
                "select * from review_runs where review_run_id = ?",
                (review_run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(review_run_id)
        return self._row_to_run(row)

    def list_agent_traces(self, review_run_id: str) -> list[AgentTraceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from agent_traces
                where review_run_id = ?
                order by id asc
                """,
                (review_run_id,),
            ).fetchall()
        return [self._row_to_trace(row) for row in rows]

    def get_run_detail(self, review_run_id: str) -> ReviewRunDetail:
        return ReviewRunDetail(run=self.get_run(review_run_id), agent_traces=self.list_agent_traces(review_run_id))

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists review_runs (
                    review_run_id text primary key,
                    repo_owner text not null,
                    repo_name text not null,
                    pr_number integer not null,
                    review_commit_sha text not null,
                    trigger_type text not null,
                    selected_model text not null,
                    base_url text not null,
                    status text not null,
                    task_payload text not null,
                    diff_snapshot text not null,
                    summary_snapshot text not null,
                    result_payload text not null,
                    rendered_comments text not null,
                    github_status text not null,
                    created_at text not null,
                    completed_at text
                )
                """
            )
            connection.execute(
                """
                create table if not exists agent_traces (
                    id integer primary key autoincrement,
                    review_run_id text not null,
                    agent_role text not null,
                    model_name text not null,
                    prompt_version text not null,
                    input_payload text not null,
                    raw_response text not null,
                    parsed_output text not null,
                    latency_ms integer,
                    token_usage text not null,
                    created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_run(self, row: sqlite3.Row) -> ReviewRunRecord:
        return ReviewRunRecord(
            review_run_id=row["review_run_id"],
            repo_owner=row["repo_owner"],
            repo_name=row["repo_name"],
            pr_number=row["pr_number"],
            review_commit_sha=row["review_commit_sha"],
            trigger_type=row["trigger_type"],
            selected_model=row["selected_model"],
            base_url=row["base_url"],
            status=row["status"],
            task_payload=json.loads(row["task_payload"]),
            diff_snapshot=row["diff_snapshot"],
            summary_snapshot=row["summary_snapshot"],
            result_payload=json.loads(row["result_payload"]),
            rendered_comments=json.loads(row["rendered_comments"]),
            github_status=json.loads(row["github_status"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    def _row_to_trace(self, row: sqlite3.Row) -> AgentTraceRecord:
        return AgentTraceRecord(
            id=row["id"],
            review_run_id=row["review_run_id"],
            agent_role=row["agent_role"],
            model_name=row["model_name"],
            prompt_version=row["prompt_version"],
            input_payload=json.loads(row["input_payload"]),
            raw_response=json.loads(row["raw_response"]),
            parsed_output=json.loads(row["parsed_output"]),
            latency_ms=row["latency_ms"],
            token_usage=json.loads(row["token_usage"]),
            created_at=row["created_at"],
        )
