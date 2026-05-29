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
