"""Comprehensive unit tests for bubblelister-inspired List features:
- PaginationMode (SCROLL vs PAGINATED)
- Absolute and Vim relative numbering
- Right-aligned badges and custom suffix_fn
- Multi-line tree continuation guides
- Custom prefix_fn and item_renderer
- Scrollbar rendering
- Native mouse navigation and selection
"""

from __future__ import annotations

import unittest

from espresso.beans.list import List, ListItem, ListSelectMsg, PaginationMode
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi
from espresso.crema.style import Style


class TestListBubblelister(unittest.TestCase):
    def test_scroll_mode_navigation(self) -> None:
        items = [f"Item {i}" for i in range(10)]
        lst = List(
            items=items,
            per_page=4,
            pagination_mode=PaginationMode.SCROLL,
            show_title=False,
            show_filter=False,
        )

        self.assertEqual(lst.cursor, 0)
        self.assertEqual(lst.scroll_offset, 0)
        start, end = lst.visible_slice
        self.assertEqual((start, end), (0, 4))

        # Move down within viewport
        lst.update(KeyMsg("down"))
        self.assertEqual(lst.cursor, 1)
        self.assertEqual(lst.scroll_offset, 0)

        lst.update(KeyMsg("j"))
        self.assertEqual(lst.cursor, 2)
        self.assertEqual(lst.scroll_offset, 0)

        lst.update(KeyMsg("down"))
        self.assertEqual(lst.cursor, 3)
        self.assertEqual(lst.scroll_offset, 0)

        # Move down past viewport -> scroll_offset increases
        lst.update(KeyMsg("down"))
        self.assertEqual(lst.cursor, 4)
        self.assertEqual(lst.scroll_offset, 1)
        self.assertEqual(lst.visible_slice, (1, 5))

        # Page down
        lst.update(KeyMsg("pgdown"))
        self.assertEqual(lst.cursor, 8)
        self.assertEqual(lst.scroll_offset, 5)

        # End key
        lst.update(KeyMsg("end"))
        self.assertEqual(lst.cursor, 9)
        self.assertEqual(lst.scroll_offset, 6)
        self.assertEqual(lst.visible_slice, (6, 10))

        # Up key
        lst.update(KeyMsg("up"))
        self.assertEqual(lst.cursor, 8)
        self.assertEqual(lst.scroll_offset, 6)  # Still in [6:10]

        # Home key
        lst.update(KeyMsg("home"))
        self.assertEqual(lst.cursor, 0)
        self.assertEqual(lst.scroll_offset, 0)

    def test_scroll_mode_footer_indicator(self) -> None:
        items = [f"Task {i}" for i in range(5)]
        lst = List(
            items=items,
            per_page=3,
            pagination_mode=PaginationMode.SCROLL,
            show_title=False,
            show_filter=False,
            show_pagination=True,
        )
        rendered = strip_ansi(lst.view())
        # First item: 1/5 (20%)
        self.assertIn("1/5 (20%)", rendered)

        # Move to last item
        lst.update(KeyMsg("end"))
        rendered_end = strip_ansi(lst.view())
        self.assertIn("5/5 (100%)", rendered_end)

    def test_absolute_numbering(self) -> None:
        items = ["Alpha", "Beta", "Gamma"]
        lst = List(
            items=items,
            show_numbers=True,
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = strip_ansi(lst.view())
        self.assertIn("1. ▶ Alpha", rendered)
        self.assertIn("2.   Beta", rendered)
        self.assertIn("3.   Gamma", rendered)

    def test_relative_numbering_vim_style(self) -> None:
        items = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
        lst = List(
            items=items,
            relative_numbers=True,
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        # Initially cursor at index 0 (Line 1)
        # Line 1: cursor row -> absolute index 1
        # Line 2: distance 1
        # Line 3: distance 2
        r0 = strip_ansi(lst.view())
        lines0 = [l.strip() for l in r0.splitlines() if l.strip()]
        self.assertIn("1 ▶ Line 1", lines0[0])
        self.assertIn("1   Line 2", lines0[1])
        self.assertIn("2   Line 3", lines0[2])

        # Move cursor to index 2 (Line 3)
        lst.update(KeyMsg("down"))
        lst.update(KeyMsg("down"))
        self.assertEqual(lst.cursor, 2)
        r2 = strip_ansi(lst.view())
        lines2 = [l.strip() for l in r2.splitlines() if l.strip()]
        self.assertIn("2   Line 1", lines2[0])
        self.assertIn("1   Line 2", lines2[1])
        self.assertIn("3 ▶ Line 3", lines2[2])
        self.assertIn("1   Line 4", lines2[3])
        self.assertIn("2   Line 5", lines2[4])

    def test_right_aligned_badges(self) -> None:
        items = [
            ListItem("Auth Service", badge="PROD", badge_style=Style().foreground("#00FF00")),
            ListItem("Billing Service", badge="STAGING"),
        ]
        lst = List(
            items=items,
            width=50,
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = strip_ansi(lst.view())
        self.assertIn("Auth Service", rendered)
        self.assertIn("PROD", rendered)
        self.assertIn("Billing Service", rendered)
        self.assertIn("STAGING", rendered)

        # Verify badge is pushed toward the right edge
        first_line = [l for l in rendered.splitlines() if "Auth Service" in l][0]
        self.assertTrue(first_line.endswith("PROD"))

    def test_custom_suffix_fn(self) -> None:
        items = ["build", "test", "deploy"]
        lst = List(
            items=items,
            width=40,
            suffix_fn=lambda it, idx, sel: f"[{idx * 10}ms]",
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = strip_ansi(lst.view())
        self.assertIn("[0ms]", rendered)
        self.assertIn("[10ms]", rendered)
        self.assertIn("[20ms]", rendered)

    def test_tree_continuation_guides(self) -> None:
        items = [
            ListItem("Root Task", "Initialize cluster resources"),
            ListItem("Mid Task", "Apply migrations"),
            ListItem("Leaf Task", "Verify health"),
        ]
        lst = List(
            items=items,
            show_tree_guides=True,
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = strip_ansi(lst.view())
        self.assertIn("╭ ▶ Root Task", rendered)
        self.assertIn("│   Initialize cluster resources", rendered)
        self.assertIn("├   Mid Task", rendered)
        self.assertIn("╰   Verify health", rendered)

    def test_custom_prefix_fn(self) -> None:
        items = ["Branch main", "Branch dev"]
        lst = List(
            items=items,
            prefix_fn=lambda it, idx, sel: "* " if sel else "  ",
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = strip_ansi(lst.view())
        self.assertIn("* Branch main", rendered)
        self.assertIn("  Branch dev", rendered)

    def test_custom_item_renderer(self) -> None:
        items = [ListItem("Card A", value=100), ListItem("Card B", value=200)]

        def render_card(it: ListItem, idx: int, sel: bool, width: int) -> str:
            prefix = ">> " if sel else "-- "
            return f"{prefix}[{it.title}] (Val: {it.value})"

        lst = List(
            items=items,
            item_renderer=render_card,
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = lst.view()
        self.assertIn(">> [Card A] (Val: 100)", rendered)
        self.assertIn("-- [Card B] (Val: 200)", rendered)

    def test_scrollbar_rendering(self) -> None:
        items = [f"Item {i}" for i in range(12)]
        lst = List(
            items=items,
            per_page=4,
            show_scrollbar=True,
            pagination_mode=PaginationMode.SCROLL,
            show_title=False,
            show_filter=False,
            show_help=False,
        )
        rendered = strip_ansi(lst.view())
        # Thumb character and track characters appear
        self.assertIn("█", rendered)

    def test_mouse_wheel_navigation(self) -> None:
        items = ["A", "B", "C", "D"]
        lst = List(items=items, show_title=False, show_filter=False)
        self.assertEqual(lst.cursor, 0)

        # Wheel down advances cursor
        lst, _ = lst.update(MouseMsg(x=0, y=0, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertEqual(lst.cursor, 1)

        lst, _ = lst.update(MouseMsg(x=0, y=0, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertEqual(lst.cursor, 2)

        # Wheel up moves cursor back
        lst, _ = lst.update(MouseMsg(x=0, y=0, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
        self.assertEqual(lst.cursor, 1)

    def test_mouse_click_selection(self) -> None:
        items = [
            ListItem("Item 0", "Description 0"),
            ListItem("Item 1", "Description 1"),
            ListItem("Item 2", "Description 2"),
        ]
        # Standalone List with title enabled:
        # row 0: Title
        # row 1: Blank separator
        # row 2: Item 0 title
        # row 3: Item 0 description
        # row 4: Item 1 title
        # row 5: Item 1 description
        # row 6: Item 2 title
        # row 7: Item 2 description
        lst = List(items=items, show_title=True, show_filter=False)
        self.assertEqual(lst.cursor, 0)

        # Click on row 4 (Item 1 title)
        lst, cmd = lst.update(MouseMsg(x=5, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(lst.cursor, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, ListSelectMsg)
        self.assertEqual(msg.item.title, "Item 1")
        self.assertEqual(msg.index, 1)

        # Click on row 3 (Item 0 description) -> selects Item 0
        lst, cmd0 = lst.update(MouseMsg(x=5, y=3, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(lst.cursor, 0)
        self.assertIsNotNone(cmd0)
        msg0 = cmd0()
        self.assertIsInstance(msg0, ListSelectMsg)
        self.assertEqual(msg0.item.title, "Item 0")
        self.assertEqual(msg0.index, 0)

        # Click on header (row 0) -> no selection
        lst, cmd_none = lst.update(MouseMsg(x=5, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertIsNone(cmd_none)


if __name__ == "__main__":
    unittest.main()
