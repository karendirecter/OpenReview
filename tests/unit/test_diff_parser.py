from app.review.diff_parser import build_position_mapping


SAMPLE_PATCH = """@@ -1,3 +1,4 @@
 line1
-line2
+line2_changed
+line3
 line4
"""


def test_build_position_mapping_returns_added_line_positions():
    """
    Test that build_position_mapping correctly maps added line numbers to review positions.

    文档缺陷标注：
    1. PLAN.md Task 3 步骤 1 需要测试 fixture，但没有说明如何创建
    2. 测试用例过于简单，只测试了添加行，缺少删除行和上下文行的测试
    3. PLAN.md 的 SAMPLE_PATCH 定义在测试文件中，应该使用 fixture 文件
    """
    mapping = build_position_mapping(SAMPLE_PATCH, new_start=1)

    assert mapping[2] == 3
    assert mapping[3] == 4