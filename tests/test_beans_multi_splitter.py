"""Unit tests for MultiSplitter bean component."""

from __future__ import annotations

import unittest

from espresso.beans.multi_splitter import MultiSplitter, MultiSplitterResizeMsg
from espresso.beans.splitter import SplitterOrientation
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Model, Msg


class DummyPaneModel(Model):
    def __init__(self, name: str) -> None:
        self.name = name
        self.width = 0
        self.height = 0
        self.last_msg: Msg | None = None

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def init(self):
        return None

    def update(self, msg: Msg):
        self.last_msg = msg
        return self, None

    def view(self) -> str:
        lines = [f"{self.name} (w={self.width}, h={self.height})"]
        while len(lines) < max(1, self.height):
            lines.append(f"{self.name} content")
        return "\n".join(lines)


class TestMultiSplitter(unittest.TestCase):
    def test_horizontal_initial_sizing(self) -> None:
        # 3 panes with 2 dividers (2 cells). Total available = 82 - 2 = 80 cells.
        # Ratios [0.25, 0.5, 0.25] -> sizes [20, 40, 20]
        sp = MultiSplitter(
            panes=["Pane 1", "Pane 2", "Pane 3"],
            ratios=[0.25, 0.5, 0.25],
            orientation=SplitterOrientation.HORIZONTAL,
            width=82,
            height=10,
        )
        self.assertEqual(sp.num_panes, 3)
        self.assertEqual(sp.num_dividers, 2)
        self.assertEqual(sp.total_available, 80)
        self.assertEqual(sp.pane_sizes, [20, 40, 20])
        self.assertEqual(sp.divider_position(0), 20)
        self.assertEqual(sp.divider_position(1), 61)  # 20 + 1 + 40 = 61

        v = sp.view()
        lines = v.split("\n")
        self.assertEqual(len(lines), 10)
        self.assertIn("Pane 1", lines[0])
        self.assertIn("Pane 2", lines[0])
        self.assertIn("Pane 3", lines[0])

    def test_vertical_initial_sizing(self) -> None:
        # Height 22 with 2 dividers -> total available = 20.
        # Ratios [0.25, 0.5, 0.25] -> sizes [5, 10, 5]
        sp = MultiSplitter(
            panes=["Top", "Middle", "Bottom"],
            ratios=[0.25, 0.5, 0.25],
            orientation=SplitterOrientation.VERTICAL,
            width=30,
            height=22,
        )
        self.assertEqual(sp.total_available, 20)
        self.assertEqual(sp.pane_sizes, [5, 10, 5])
        self.assertEqual(sp.divider_position(0), 5)
        self.assertEqual(sp.divider_position(1), 16)  # 5 + 1 + 10 = 16

        lines = sp.view().split("\n")
        self.assertEqual(len(lines), 22)

    def test_min_sizes_constraints(self) -> None:
        sp = MultiSplitter(
            panes=["P1", "P2", "P3"],
            ratios=[0.33, 0.33, 0.34],
            min_sizes=[10, 15, 20],
            width=50,
            height=10,
        )
        # Nudge divider 0 leftwards as far as possible
        sp.nudge_divider(0, -50)
        sizes = sp.pane_sizes
        self.assertGreaterEqual(sizes[0], 10)
        self.assertGreaterEqual(sizes[1], 15)
        self.assertGreaterEqual(sizes[2], 20)

    def test_keyboard_navigation(self) -> None:
        sp = MultiSplitter(
            panes=["P1", "P2", "P3"],
            ratios=[0.25, 0.5, 0.25],
            width=82,
            height=10,
        )
        # Active divider starts at 0
        self.assertEqual(sp.active_divider_idx, 0)
        old_size_0 = sp.pane_sizes[0]

        # Left key nudges divider 0 left
        sp, cmd = sp.update(KeyMsg("left"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, MultiSplitterResizeMsg)
        self.assertEqual(msg.divider_index, 0)
        self.assertEqual(sp.pane_sizes[0], old_size_0 - 1)

        # Tab switches active divider to 1
        sp, _ = sp.update(KeyMsg("tab"))
        self.assertEqual(sp.active_divider_idx, 1)

        # Right key nudges divider 1 right
        old_size_1 = sp.pane_sizes[1]
        sp, cmd2 = sp.update(KeyMsg("right"))
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertEqual(msg2.divider_index, 1)
        self.assertEqual(sp.pane_sizes[1], old_size_1 + 1)

        # Equalize key '='
        sp, cmd3 = sp.update(KeyMsg("="))
        self.assertIsNotNone(cmd3)
        self.assertAlmostEqual(sp.ratios[0], 1.0 / 3, places=2)
        self.assertAlmostEqual(sp.ratios[1], 1.0 / 3, places=2)
        self.assertAlmostEqual(sp.ratios[2], 1.0 / 3, places=2)

    def test_mouse_dragging(self) -> None:
        sp = MultiSplitter(
            panes=["P1", "P2", "P3"],
            ratios=[0.25, 0.5, 0.25],
            width=82,
            height=10,
        )
        div0_x = sp.divider_position(0)  # 20

        # Press on divider 0
        sp, _ = sp.update(MouseMsg(x=div0_x, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertTrue(sp.is_dragging)
        self.assertEqual(sp.active_divider_idx, 0)

        # Drag motion
        sp, cmd = sp.update(MouseMsg(x=div0_x + 5, y=5, button=MouseButton.LEFT, action=MouseAction.MOTION))
        self.assertIsNotNone(cmd)
        self.assertEqual(sp.pane_sizes[0], 25)

        # Release
        sp, cmd_rel = sp.update(MouseMsg(x=div0_x + 5, y=5, button=MouseButton.LEFT, action=MouseAction.RELEASE))
        self.assertFalse(sp.is_dragging)
        self.assertIsNotNone(cmd_rel)
        msg_rel = cmd_rel()
    def test_mouse_wheel_on_divider(self) -> None:
        sp = MultiSplitter(
            panes=["P1", "P2", "P3"],
            ratios=[0.25, 0.5, 0.25],
            width=82,
            height=10,
        )
        div0_x = sp.divider_position(0)  # 20
        orig_s0 = sp.pane_sizes[0]

        # Wheel down on divider moves divider right (delta = 1)
        sp, cmd = sp.update(MouseMsg(x=div0_x, y=5, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertIsNotNone(cmd)
        self.assertEqual(sp.pane_sizes[0], orig_s0 + 1)

    def test_mouse_double_click_divider_equalizes_adjacent(self) -> None:
        sp = MultiSplitter(
            panes=["P1", "P2", "P3"],
            ratios=[0.10, 0.65, 0.25],  # P1=8, P2=52
            width=82,
            height=10,
        )
        div0_x = sp.divider_position(0)
        # Combined space for P1 and P2 is 8 + 52 = 60. Equal split should be 30 and 30.
        sp, cmd = sp.update(MouseMsg(x=div0_x, y=5, button=MouseButton.LEFT, action=MouseAction.DOUBLE_CLICK))
        self.assertIsNotNone(cmd)
        self.assertEqual(sp.pane_sizes[0], 30)
        self.assertEqual(sp.pane_sizes[1], 30)

    def test_mouse_right_click_divider_equalizes_all(self) -> None:
        sp = MultiSplitter(
            panes=["P1", "P2", "P3"],
            ratios=[0.10, 0.70, 0.20],
            width=82,
            height=10,
        )
        div0_x = sp.divider_position(0)
        sp, cmd = sp.update(MouseMsg(x=div0_x, y=5, button=MouseButton.RIGHT, action=MouseAction.PRESS))
        self.assertIsNotNone(cmd)
        self.assertAlmostEqual(sp.ratios[0], 1.0 / 3, places=2)
        self.assertAlmostEqual(sp.ratios[1], 1.0 / 3, places=2)
        self.assertAlmostEqual(sp.ratios[2], 1.0 / 3, places=2)

    def test_child_model_delegation(self) -> None:
        p1 = DummyPaneModel("P1")
        p2 = DummyPaneModel("P2")
        p3 = DummyPaneModel("P3")

        sp = MultiSplitter(
            panes=[p1, p2, p3],
            ratios=[0.25, 0.5, 0.25],
            width=82,
            height=10,
        )

        # Verify child models received sizes
        self.assertEqual(p1.width, 20)
        self.assertEqual(p2.width, 40)
        self.assertEqual(p3.width, 20)
        self.assertEqual(p1.height, 10)

        # Click inside pane 2 (x=30, between divider 0 at 20 and divider 1 at 61)
        sp, _ = sp.update(MouseMsg(x=30, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertIsNotNone(p2.last_msg)
        self.assertIsInstance(p2.last_msg, MouseMsg)
        # Mouse coordinate translated relative to pane 2 start (x=21)
        self.assertEqual(p2.last_msg.x, 30 - 21)

    def test_resize_adaptation(self) -> None:
        p1 = DummyPaneModel("P1")
        p2 = DummyPaneModel("P2")
        p3 = DummyPaneModel("P3")
        sp = MultiSplitter(
            panes=[p1, p2, p3],
            ratios=[0.2, 0.4, 0.4],
            width=52,
            height=10,
        )
        # Expand width to 102
        sp.set_size(102, 20)
        self.assertEqual(sp.width, 102)
        self.assertEqual(sp.height, 20)
        self.assertEqual(sp.total_available, 100)
        self.assertEqual(sp.pane_sizes, [20, 40, 40])
        self.assertEqual(p1.width, 20)
        self.assertEqual(p2.width, 40)
        self.assertEqual(p3.width, 40)
        self.assertEqual(p1.height, 20)


if __name__ == "__main__":
    unittest.main()
