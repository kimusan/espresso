"""Unit tests for CardList bean component."""

from __future__ import annotations

import unittest

from espresso.beans.card_list import (
    CardActivateMsg,
    CardItem,
    CardList,
    CardSelectMsg,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi


class TestCardList(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            CardItem(
                id="c1",
                title="Linus Torvalds",
                subtitle="Merge branch 'tip/x86/urgent'",
                badge_text="10:42 AM",
                glyphs="★",
                is_unread=True,
            ),
            CardItem(
                id="c2",
                title="Greg Kroah-Hartman",
                subtitle="Linux 6.12-rc4 release notes",
                badge_text="Yesterday",
                depth=1,
            ),
            CardItem(
                id="c3",
                title="Sub-Reply",
                subtitle="Acked-by patch reviewed",
                badge_text="Oct 20",
                depth=2,
            ),
            CardItem(
                id="c4",
                title="Mailing List Digest",
                subtitle="Weekly compilation of RFC patches",
                badge_text="Oct 18",
            ),
            CardItem(
                id="c5",
                title="Security Advisory",
                subtitle="CVE-2026-9999 mitigation applied",
                badge_text="Oct 15",
                glyphs="🔒",
            ),
        ]
        self.card_list = CardList(
            items=self.items,
            selected_index=0,
            width=50,
            height=6,  # 3 items visible at 2 lines each
        )

    def test_initial_state(self) -> None:
        self.assertEqual(self.card_list.selected_index, 0)
        self.assertEqual(self.card_list.items_per_page, 3)
        self.assertEqual(self.card_list.get_selected_item().id, "c1")  # type: ignore

    def test_rendering_2_lines_and_tree(self) -> None:
        v = self.card_list.view()
        lines = [strip_ansi(l) for l in v.split("\n")]
        self.assertEqual(len(lines), 6)

        # Item 1 (lines 0, 1)
        self.assertIn("Linus Torvalds", lines[0])
        self.assertIn("10:42 AM", lines[0])
        self.assertIn("●", lines[0])  # unread glyph
        self.assertIn("Merge branch", lines[1])

        # Item 2 with depth 1 has tree branch glyph ╰─ (lines 2, 3)
        self.assertIn("╰─", lines[2])
        self.assertIn("Greg Kroah-Hartman", lines[2])
        self.assertIn("Yesterday", lines[2])

        # Item 3 with depth 2 has indentation before branch (lines 4, 5)
        self.assertIn("  ╰─", lines[4])
        self.assertIn("Sub-Reply", lines[4])

    def test_keyboard_navigation(self) -> None:
        # Down key advances selection
        self.card_list, cmd = self.card_list.update(KeyMsg("down"))
        self.assertEqual(self.card_list.selected_index, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, CardSelectMsg)
        self.assertEqual(msg.item.id, "c2")
        self.assertEqual(msg.index, 1)

        # Up key moves back
        self.card_list, cmd2 = self.card_list.update(KeyMsg("up"))
        self.assertEqual(self.card_list.selected_index, 0)
        self.assertEqual(cmd2().item.id, "c1")  # type: ignore

        # End key moves to last item (index 4)
        self.card_list, _ = self.card_list.update(KeyMsg("end"))
        self.assertEqual(self.card_list.selected_index, 4)

        # Home key moves to first item
        self.card_list, _ = self.card_list.update(KeyMsg("home"))
        self.assertEqual(self.card_list.selected_index, 0)

        # Enter triggers activate
        self.card_list, cmd_act = self.card_list.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd_act)
        act_msg = cmd_act()
        self.assertIsInstance(act_msg, CardActivateMsg)
        self.assertEqual(act_msg.item.id, "c1")

    def test_viewport_scrolling(self) -> None:
        # Initially scroll_offset is 0
        self.assertEqual(self.card_list.scroll_offset, 0)

        # Select item index 3 (4th item, outside initial page of 3 items)
        self.card_list.select_index(3)
        self.assertEqual(self.card_list.scroll_offset, 1)  # Scrolled down by 1

        v = [strip_ansi(l) for l in self.card_list.view().split("\n")]
        # Item 1 is now scrolled off, item 4 ("Mailing List Digest") is visible
        self.assertNotIn("Linus Torvalds", v[0])
        self.assertIn("Mailing List Digest", v[4])

    def test_mouse_interactions(self) -> None:
        # Mouse click on item 1 (row 2 or 3 in view)
        self.card_list, cmd = self.card_list.update(
            MouseMsg(x=10, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertEqual(self.card_list.selected_index, 1)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), CardSelectMsg)

        # Clicking already selected item activates it
        self.card_list, cmd_act = self.card_list.update(
            MouseMsg(x=10, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertIsNotNone(cmd_act)
        self.assertIsInstance(cmd_act(), CardActivateMsg)

        # Mouse wheel down moves selection
        self.card_list, cmd_wheel = self.card_list.update(
            MouseMsg(x=10, y=2, button=MouseButton.WHEEL_DOWN, action=MouseAction.MOTION)
        )
        self.assertEqual(self.card_list.selected_index, 2)

    def test_mouse_double_click_activates(self) -> None:
        # Double-click item 2 (row 4)
        self.card_list, cmd = self.card_list.update(
            MouseMsg(x=10, y=4, button=MouseButton.LEFT, action=MouseAction.DOUBLE_CLICK)
        )
        self.assertEqual(self.card_list.selected_index, 2)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), CardActivateMsg)

    def test_mouse_right_click_selects_without_activating(self) -> None:
        # Right-click item 1 (row 2)
        self.card_list, cmd = self.card_list.update(
            MouseMsg(x=10, y=2, button=MouseButton.RIGHT, action=MouseAction.PRESS)
        )
        self.assertEqual(self.card_list.selected_index, 1)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), CardSelectMsg)

    def test_mouse_drag_selection(self) -> None:
        # Press on item 0 (row 0)
        self.card_list, _ = self.card_list.update(
            MouseMsg(x=10, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertEqual(self.card_list.selected_index, 0)

        # Drag motion down to row 2 (item 1)
        self.card_list, cmd = self.card_list.update(
            MouseMsg(x=10, y=2, button=MouseButton.LEFT, action=MouseAction.MOTION)
        )
        self.assertEqual(self.card_list.selected_index, 1)
        self.assertIsNotNone(cmd)

        # Release mouse ends drag
        self.card_list, _ = self.card_list.update(
            MouseMsg(x=10, y=2, button=MouseButton.LEFT, action=MouseAction.RELEASE)
        )
        self.assertFalse(self.card_list._is_mouse_down)

    def test_empty_list(self) -> None:
        empty_list = CardList(items=[], empty_text="Inbox Zero")
        v = strip_ansi(empty_list.view())
        self.assertIn("Inbox Zero", v)
        self.assertIsNone(empty_list.get_selected_item())
        empty_list, cmd = empty_list.update(KeyMsg("down"))
        self.assertIsNone(cmd)


if __name__ == "__main__":
    unittest.main()
