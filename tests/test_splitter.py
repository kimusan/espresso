"""Unit tests for Splitter bean component."""

from __future__ import annotations

import unittest

from espresso.beans.splitter import Splitter, SplitterOrientation, SplitterResizeMsg
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi


class TestSplitter(unittest.TestCase):
    def test_horizontal_initial_sizing(self) -> None:
        sp = Splitter("Left Pane", "Right Pane", orientation=SplitterOrientation.HORIZONTAL, width=81, height=10, ratio=0.5)
        # width = 81 -> total available = 80 (excluding 1-cell divider)
        # 50% of 80 = 40
        self.assertEqual(sp.pane1_size, 40)
        self.assertEqual(sp.pane2_size, 40)
        self.assertEqual(sp.divider_position, 40)

        v = sp.view()
        lines = v.split("\n")
        self.assertEqual(len(lines), 10)
        self.assertIn("Left Pane", lines[0])
        self.assertIn("Right Pane", lines[0])

    def test_vertical_initial_sizing(self) -> None:
        sp = Splitter("Top Pane", "Bottom Pane", orientation=SplitterOrientation.VERTICAL, width=40, height=21, ratio=0.5)
        # height = 21 -> total available = 20
        # 50% of 20 = 10
        self.assertEqual(sp.pane1_size, 10)
        self.assertEqual(sp.pane2_size, 10)
        self.assertEqual(sp.divider_position, 10)

        lines = sp.view().split("\n")
        self.assertEqual(len(lines), 21)
        self.assertIn("Top Pane", lines[0])
        self.assertIn("Bottom Pane", lines[11])

    def test_min_pane_constraints(self) -> None:
        sp = Splitter("P1", "P2", width=31, height=10, min_pane1=8, min_pane2=10)
        # total avail = 30
        sp.set_ratio(0.01)  # Try to make pane1 smaller than min
        self.assertGreaterEqual(sp.pane1_size, 8)

        sp.set_ratio(0.99)  # Try to make pane2 smaller than min
        self.assertGreaterEqual(sp.pane2_size, 10)

    def test_keyboard_navigation(self) -> None:
        sp = Splitter("P1", "P2", orientation=SplitterOrientation.HORIZONTAL, width=81, height=10, ratio=0.5)
        orig_p1 = sp.pane1_size

        # Move right
        sp, cmd = sp.update(KeyMsg("right"))
        self.assertEqual(sp.pane1_size, orig_p1 + 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SplitterResizeMsg)
        self.assertEqual(msg.pane1_size, orig_p1 + 1)

        # Move left
        sp, _ = sp.update(KeyMsg("left"))
        self.assertEqual(sp.pane1_size, orig_p1)

        # Coarse step (ctrl+right)
        sp, _ = sp.update(KeyMsg("right", ctrl=True))
        self.assertEqual(sp.pane1_size, orig_p1 + 5)

        # Reset ratio with =
        sp, _ = sp.update(KeyMsg("="))
        self.assertEqual(sp.pane1_size, orig_p1)

    def test_mouse_drag_resizing(self) -> None:
        sp = Splitter("P1", "P2", orientation=SplitterOrientation.HORIZONTAL, width=81, height=10, ratio=0.5)
        div_x = sp.divider_position
        self.assertEqual(div_x, 40)
        self.assertFalse(sp.is_dragging)

        # 1. Click on divider
        sp, _ = sp.update(MouseMsg(x=div_x, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertTrue(sp.is_dragging)

        # 2. Drag to x = 50
        sp, cmd = sp.update(MouseMsg(x=50, y=5, button=MouseButton.LEFT, action=MouseAction.MOTION))
        self.assertEqual(sp.pane1_size, 50)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SplitterResizeMsg)
        self.assertEqual(msg.pane1_size, 50)

        # 3. Release mouse
        sp, _ = sp.update(MouseMsg(x=50, y=5, button=MouseButton.LEFT, action=MouseAction.RELEASE))
        self.assertFalse(sp.is_dragging)

        # Further motion when not dragging does not change position
        sp, _ = sp.update(MouseMsg(x=20, y=5, button=MouseButton.NONE, action=MouseAction.MOTION))
        self.assertEqual(sp.pane1_size, 50)


if __name__ == "__main__":
    unittest.main()
