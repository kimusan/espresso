"""Unit tests for SortableList component."""

from __future__ import annotations

import unittest

from espresso.beans.sortable_list import ItemReorderedMsg, SortableItem, SortableList
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi


class TestSortableList(unittest.TestCase):
    def test_initial_items_and_view(self) -> None:
        items = ["Task A", "Task B", "Task C"]
        sl = SortableList(items=items, width=30, height=5)
        self.assertEqual(sl.cursor, 0)
        self.assertEqual(sl.selected_item, "Task A")

        v = strip_ansi(sl.view())
        lines = v.split("\n")
        self.assertEqual(len(lines), 5)
        self.assertIn("▶ ⠿ Task A", lines[0])
        self.assertIn("  ⠿ Task B", lines[1])

    def test_keyboard_navigation(self) -> None:
        sl = SortableList(items=["A", "B", "C"])
        sl, _ = sl.update(KeyMsg("down"))
        self.assertEqual(sl.cursor, 1)
        self.assertEqual(sl.selected_item, "B")

        sl, _ = sl.update(KeyMsg("up"))
        self.assertEqual(sl.cursor, 0)
        self.assertEqual(sl.selected_item, "A")

    def test_keyboard_grab_and_move(self) -> None:
        sl = SortableList(items=["Task 1", "Task 2", "Task 3"])

        # Pick up item 0 with Space
        sl, _ = sl.update(KeyMsg("space"))
        self.assertEqual(sl.picked_index, 0)

        # Move down to index 1
        sl, cmd = sl.update(KeyMsg("down"))
        self.assertEqual(sl.items, ["Task 2", "Task 1", "Task 3"])
        self.assertEqual(sl.picked_index, 1)
        self.assertEqual(sl.cursor, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, ItemReorderedMsg)
        self.assertEqual(msg.old_index, 0)
        self.assertEqual(msg.new_index, 1)
        self.assertEqual(msg.item, "Task 1")

        # Drop item with Space
        sl, _ = sl.update(KeyMsg("space"))
        self.assertIsNone(sl.picked_index)
        self.assertEqual(sl.items, ["Task 2", "Task 1", "Task 3"])

    def test_mouse_drag_and_drop(self) -> None:
        sl = SortableList(items=["Apple", "Banana", "Cherry", "Date"])

        # 1. Click on row 0 (Apple)
        sl, _ = sl.update(MouseMsg(x=5, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(sl.dragging_index, 0)

        # 2. Drag down to row 2 (Cherry)
        sl, _ = sl.update(MouseMsg(x=5, y=2, button=MouseButton.LEFT, action=MouseAction.MOTION))
        self.assertEqual(sl.drag_target_index, 2)

        # 3. Release mouse to commit drop
        sl, cmd = sl.update(MouseMsg(x=5, y=2, button=MouseButton.LEFT, action=MouseAction.RELEASE))
        self.assertIsNone(sl.dragging_index)
        self.assertEqual(sl.items, ["Banana", "Cherry", "Apple", "Date"])
        self.assertEqual(sl.cursor, 2)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, ItemReorderedMsg)
        self.assertEqual(msg.old_index, 0)
        self.assertEqual(msg.new_index, 2)
        self.assertEqual(msg.item, "Apple")

    def test_custom_sortable_item_objects(self) -> None:
        items = [
            SortableItem(id="1", title="First Item"),
            SortableItem(id="2", title="Second Item"),
        ]
        sl = SortableList(items=items)
        v = strip_ansi(sl.view())
        self.assertIn("First Item", v)
        self.assertIn("Second Item", v)


if __name__ == "__main__":
    unittest.main()
