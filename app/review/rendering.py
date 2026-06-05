from app.review.models import RenderedComment, ReviewFinding, ReviewResult


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


def render_summary_comment(result: ReviewResult) -> str:
    lines = [
        "## Automated Code Review Results",
        "",
        f"- Commit: `{result.review_commit_sha}`",
        f"- Overall risk: `{result.overall_risk}`",
        f"- Stage 1 candidates: {result.stats.get('stage1_candidates', 0)}",
        f"- Final findings: {result.stats.get('stage2_findings', len(result.findings))}",
        f"- Agent traces: {result.stats.get('agent_traces', len(result.agent_traces))}",
        "",
        result.summary,
    ]
    if result.findings:
        lines.extend(["", "### Findings"])
        for finding in result.findings:
            lines.append(f"- `{finding.file_path}:{finding.line_number}` {finding.issue_title}")
    return "\n".join(lines)


def render_review_comments(result: ReviewResult) -> list[RenderedComment]:
    comments = [
        RenderedComment(
            comment_type="summary",
            body=render_summary_comment(result),
            commit_sha=result.review_commit_sha,
        )
    ]

    for finding in result.findings:
        comments.append(
            RenderedComment(
                comment_type="inline",
                body=render_inline_comment(finding),
                file_path=finding.file_path,
                line_number=finding.line_number,
                end_line_number=finding.end_line_number,
                side="RIGHT",
                commit_sha=finding.commit_sha,
            )
        )

    return comments
