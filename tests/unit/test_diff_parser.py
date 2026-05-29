from app.review.diff_parser import build_position_mapping


SAMPLE_PATCH = """@@ -1,3 +1,4 @@
 line1
-line2
+line2_changed
+line3
 line4
"""


def test_build_position_mapping_returns_added_line_positions():
    mapping = build_position_mapping(SAMPLE_PATCH, new_start=1)

    assert mapping[2] == 3
    assert mapping[3] == 4
