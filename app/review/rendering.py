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
