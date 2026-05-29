def select_review_context(diff_hunks: list[str], file_content: str, use_full_file: bool) -> str:
    hunk_block = "\n".join(diff_hunks)
    if use_full_file:
        return f"[DIFF]\n{hunk_block}\n\n[FULL_FILE]\n{file_content}"
    return f"[DIFF]\n{hunk_block}"
