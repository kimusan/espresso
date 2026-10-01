"""Unit tests for DiffViewer component."""

from __future__ import annotations

import unittest

from espresso.beans.diff_viewer import DiffHunk, DiffLine, DiffMode, DiffViewer
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi

SAMPLE_OLD = """def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""

SAMPLE_NEW = """def calculate_total(items, tax_rate=0.0):
    total = 0
    for item in items:
        total += item.price * (1.0 + tax_rate)
    return round(total, 2)
"""


class TestDiffViewer(unittest.TestCase):
    def test_compare_and_stats(self) -> None:
        dv = DiffViewer(old_text=SAMPLE_OLD, new_text=SAMPLE_NEW, width=80, height=15)
        self.assertGreater(len(dv.hunks), 0)
        self.assertGreater(dv.stats_additions, 0)
        self.assertGreater(dv.stats_deletions, 0)

        # Check hunk details
        hunk = dv.hunks[0]
        self.assertTrue(any(line.line_type == "+" for line in hunk.lines))
        self.assertTrue(any(line.line_type == "-" for line in hunk.lines))

    def test_intra_line_word_highlighting(self) -> None:
        dv = DiffViewer(old_text=SAMPLE_OLD, new_text=SAMPLE_NEW, highlight_words=True)
        # Check that line tokens were generated for modified lines
        hunk = dv.hunks[0]
        modified_lines = [l for l in hunk.lines if l.tokens is not None]
        self.assertGreater(len(modified_lines), 0)

        # Check token types
        first_mod = modified_lines[0]
        token_types = {tt for _, tt in first_mod.tokens}
        self.assertTrue("same" in token_types or "added" in token_types or "removed" in token_types)

    def test_unified_view(self) -> None:
        dv = DiffViewer(old_text=SAMPLE_OLD, new_text=SAMPLE_NEW, mode=DiffMode.UNIFIED, width=80, height=12)
        v = strip_ansi(dv.view())
        self.assertIn("DIFF [UNIFIED]", v)
        self.assertIn("+", v)
        self.assertIn("-", v)
        self.assertIn("calculate_total", v)
        lines = v.split("\n")
        self.assertEqual(len(lines), 12)

    def test_split_view(self) -> None:
        dv = DiffViewer(old_text=SAMPLE_OLD, new_text=SAMPLE_NEW, mode=DiffMode.SPLIT, width=80, height=12)
        v = strip_ansi(dv.view())
        self.assertIn("DIFF [SPLIT]", v)
        self.assertIn("│", v)
        lines = v.split("\n")
        self.assertEqual(len(lines), 12)

    def test_keyboard_toggle_and_scrolling(self) -> None:
        dv = DiffViewer(old_text=SAMPLE_OLD, new_text=SAMPLE_NEW, mode=DiffMode.UNIFIED, height=8)
        self.assertEqual(dv.mode, DiffMode.UNIFIED)

        # Tab toggles to SPLIT
        dv, _ = dv.update(KeyMsg("tab"))
        self.assertEqual(dv.mode, DiffMode.SPLIT)

        # 'm' toggles back to UNIFIED
        dv, _ = dv.update(KeyMsg("m"))
        self.assertEqual(dv.mode, DiffMode.UNIFIED)

        # Down arrow scrolls
        self.assertEqual(dv.scroll_y, 0)
        dv, _ = dv.update(KeyMsg("down"))
        self.assertEqual(dv.scroll_y, 1)

        # Home scrolls back to top
        dv, _ = dv.update(KeyMsg("home"))
        self.assertEqual(dv.scroll_y, 0)

    def test_mouse_wheel_scroll(self) -> None:
        dv = DiffViewer(old_text=SAMPLE_OLD, new_text=SAMPLE_NEW, width=50, height=8, offset_x=0, offset_y=0)
        dv, _ = dv.update(MouseMsg(x=10, y=3, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertEqual(dv.scroll_y, 2)

        dv, _ = dv.update(MouseMsg(x=10, y=3, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
        self.assertEqual(dv.scroll_y, 0)


if __name__ == "__main__":
    unittest.main()
