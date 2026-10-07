"""Unit tests for ScrollView bean component."""

from __future__ import annotations

import unittest

from espresso.beans.scroll_view import ScrollChangeMsg, ScrollView
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema.style import Style
from espresso.crema.width import strip_ansi


class TestScrollView(unittest.TestCase):
    def setUp(self) -> None:
        self.text_content = "\n".join([f"Line {i:02d}: Some sample test content" for i in range(50)])

    def test_initial_state_with_text(self) -> None:
        sv = ScrollView(child=self.text_content, width=40, height=10)
        self.assertEqual(sv.y_offset, 0)
        self.assertEqual(sv.total_lines, 50)
        self.assertEqual(sv.max_offset, 40)
        self.assertEqual(sv.scroll_percent, 0.0)

        view_lines = sv.view().splitlines()
        self.assertEqual(len(view_lines), 10)
        self.assertIn("Line 00", strip_ansi(view_lines[0]))
        self.assertIn("Line 09", strip_ansi(view_lines[9]))

    def test_keyboard_scrolling_text(self) -> None:
        sv = ScrollView(child=self.text_content, width=40, height=10)

        # Scroll down 3 lines
        for _ in range(3):
            sv, cmd = sv.update(KeyMsg(key="j"))
            self.assertIsNotNone(cmd)
            msg = cmd()
            self.assertIsInstance(msg, ScrollChangeMsg)
        self.assertEqual(sv.y_offset, 3)

        # Scroll up 1 line
        sv, cmd = sv.update(KeyMsg(key="k"))
        self.assertEqual(sv.y_offset, 2)

        # Page down (default jumps by height=10)
        sv, _ = sv.update(KeyMsg(key="pagedown"))
        self.assertEqual(sv.y_offset, 12)

        # Page up
        sv, _ = sv.update(KeyMsg(key="pageup"))
        self.assertEqual(sv.y_offset, 2)

        # Jump to bottom
        sv, _ = sv.update(KeyMsg(key="end"))
        self.assertEqual(sv.y_offset, 40)
        self.assertEqual(sv.scroll_percent, 1.0)

        # Jump to top
        sv, _ = sv.update(KeyMsg(key="home"))
        self.assertEqual(sv.y_offset, 0)

    def test_clamping_and_bounds(self) -> None:
        sv = ScrollView(child="Short content", width=40, height=10)
        self.assertEqual(sv.total_lines, 1)
        self.assertEqual(sv.max_offset, 0)
        self.assertEqual(sv.scroll_percent, 1.0)

        # Scrolling down should do nothing
        sv, _ = sv.update(KeyMsg(key="down"))
        self.assertEqual(sv.y_offset, 0)

        # Scroll to arbitrary invalid offset
        sv.scroll_to(100)
        self.assertEqual(sv.y_offset, 0)

        sv.scroll_to(-50)
        self.assertEqual(sv.y_offset, 0)

    def test_mouse_wheel_scrolling(self) -> None:
        sv = ScrollView(child=self.text_content, width=40, height=10, scroll_step=2)

        # Mouse wheel down
        sv, cmd = sv.update(
            MouseMsg(x=10, y=5, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS)
        )
        self.assertEqual(sv.y_offset, 2)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), ScrollChangeMsg)

        # Mouse wheel up
        sv, _ = sv.update(
            MouseMsg(x=10, y=5, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS)
        )
        self.assertEqual(sv.y_offset, 0)

    def test_mouse_scrollbar_click_jump(self) -> None:
        sv = ScrollView(child=self.text_content, width=40, height=10)
        scrollbar_x = 39  # content_w = 40 - 1 = 39

        # Click at bottom of scrollbar (y = 9)
        sv, cmd = sv.update(
            MouseMsg(x=scrollbar_x, y=9, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, ScrollChangeMsg)
        self.assertEqual(sv.y_offset, 40)

        # Click near middle of scrollbar (y = 5)
        sv, _ = sv.update(
            MouseMsg(x=scrollbar_x, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertGreater(sv.y_offset, 15)
        self.assertLess(sv.y_offset, 25)

    def test_wrapping_child_model_bean(self) -> None:
        ti = TextInput(placeholder="Type here...")
        sv = ScrollView(child=ti, width=40, height=5)

        # Delegate init
        self.assertIsNone(sv.init())

        # Typing keys forwards to child TextInput
        sv, _ = sv.update(KeyMsg(key="h"))
        sv, _ = sv.update(KeyMsg(key="e"))
        sv, _ = sv.update(KeyMsg(key="y"))

        self.assertEqual(ti.value, "hey")
        view_str = sv.view()
        self.assertIn("hey", view_str)

    def test_mouse_coordinate_translation_for_child(self) -> None:
        class ClickTracker:
            def __init__(self) -> None:
                self.last_clicked_x = -1
                self.last_clicked_y = -1

            def init(self):
                return None

            def update(self, msg):
                if isinstance(msg, MouseMsg) and msg.action == MouseAction.PRESS:
                    self.last_clicked_x = msg.x
                    self.last_clicked_y = msg.y
                return self, None

            def view(self) -> str:
                return "Row 0\nRow 1\nRow 2\nRow 3\nRow 4\nRow 5\nRow 6\nRow 7\nRow 8\nRow 9"

        tracker = ClickTracker()
        sv = ScrollView(child=tracker, width=30, height=5, offset_x=10, offset_y=5)
        sv.scroll_to(3)  # y_offset is 3

        # Click at screen coords (15, 7)
        # local_x = 15 - 10 + 0 = 5
        # local_y = 7 - 5 + 3 = 5
        sv.update(MouseMsg(x=15, y=7, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(tracker.last_clicked_x, 5)
        self.assertEqual(tracker.last_clicked_y, 5)

    def test_dynamic_child_content_expansion(self) -> None:
        class DynamicContent:
            def __init__(self) -> None:
                self.lines_count = 3

            def update(self, msg):
                return self, None

            def view(self) -> str:
                return "\n".join([f"Item {i}" for i in range(self.lines_count)])

        dyn = DynamicContent()
        sv = ScrollView(child=dyn, width=30, height=5)
        self.assertEqual(sv.total_lines, 3)
        self.assertEqual(sv.max_offset, 0)

        # Child expands to 20 lines
        dyn.lines_count = 20
        self.assertEqual(sv.total_lines, 20)
        self.assertEqual(sv.max_offset, 15)

        sv.scroll_to_bottom()
        self.assertEqual(sv.y_offset, 15)

    def test_set_dimensions_and_set_content(self) -> None:
        sv = ScrollView(width=20, height=5)
        sv.set_content("A\nB\nC\nD\nE\nF\nG\nH")
        self.assertEqual(sv.total_lines, 8)
        self.assertEqual(sv.max_offset, 3)

        sv.scroll_to(3)
        self.assertEqual(sv.y_offset, 3)

        # Resizing to height 10 clamps offset to 0
        sv.set_dimensions(width=20, height=10)
        self.assertEqual(sv.max_offset, 0)
        self.assertEqual(sv.y_offset, 0)


if __name__ == "__main__":
    unittest.main()
