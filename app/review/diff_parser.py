"""
Diff parser module for mapping review positions.

文档缺陷标注：PLAN.md Task 3 步骤 3 的实现过于简化，
缺少对 unidiff 库的使用说明和更复杂的 diff 解析逻辑
"""


def build_position_mapping(patch: str, new_start: int) -> dict[int, int]:
    """
    Build a mapping from absolute line numbers to review positions.

    Args:
        patch: The diff patch string
        new_start: The starting line number in the new file

    Returns:
        A dictionary mapping line numbers to positions

    文档缺陷标注：
    1. PLAN.md 的实现逻辑过于简化，缺少对 diff_position 的精确说明
    2. 缺少对 unidiff 库的使用，应该使用 unidiff 库来解析 diff
    3. 缺少对多 hunk 的处理逻辑
    """
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