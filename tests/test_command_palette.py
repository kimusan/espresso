"""Unit tests for CommandPalette bean."""

from __future__ import annotations

import unittest

from espresso.beans.command_palette import CommandPalette, PaletteItem
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestCommandPalette(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            PaletteItem(id="git_status", title="Git: View Status", category="Git", shortcut="Ctrl+G"),
            PaletteItem(id="file_open", title="File: Open File", category="File", shortcut="Ctrl+O"),
            PaletteItem(id="term_toggle", title="Terminal: Toggle", category="View", shortcut="Ctrl+`"),
            PaletteItem(id="settings", title="Preferences: Open Settings", category="Preferences"),
        ]
        self.palette = CommandPalette(items=self.items, is_open=True)

    def test_initial_state(self) -> None:
        self.assertTrue(self.palette.is_open)
        self.assertEqual(self.palette.cursor, 0)
        self.assertEqual(len(self.palette.get_filtered_items()), 4)

    def test_fuzzy_filtering(self) -> None:
        self.palette.query = "git"
        filtered = self.palette.get_filtered_items()
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "git_status")

        self.palette.query = "term"
        filtered2 = self.palette.get_filtered_items()
        self.assertEqual(len(filtered2), 1)
        self.assertEqual(filtered2[0].id, "term_toggle")

    def test_keyboard_input_and_backspace(self) -> None:
        # Type "f"
        self.palette.update(KeyMsg("f"))
        self.assertEqual(self.palette.query, "f")
        self.assertEqual(self.palette.cursor, 0)

        # Type "i"
        self.palette.update(KeyMsg("i"))
        self.assertEqual(self.palette.query, "fi")

        # Backspace
        self.palette.update(KeyMsg("backspace"))
        self.assertEqual(self.palette.query, "f")

    def test_cursor_navigation(self) -> None:
        self.palette.update(KeyMsg("down"))
        self.assertEqual(self.palette.cursor, 1)

        self.palette.update(KeyMsg("down"))
        self.assertEqual(self.palette.cursor, 2)

        self.palette.update(KeyMsg("up"))
        self.assertEqual(self.palette.cursor, 1)

    def test_selection_and_recents(self) -> None:
        # Move cursor to item 1 (File: Open File)
        self.palette.update(KeyMsg("down"))
        self.assertEqual(self.palette.cursor, 1)

        # Press enter
        self.palette.update(KeyMsg("enter"))
        self.assertFalse(self.palette.is_open)
        self.assertIn("file_open", self.palette.recent_ids)
        self.assertEqual(self.palette.recent_ids[0], "file_open")

        # Reopen: recent item should appear at the top
        self.palette.open()
        items = self.palette.get_filtered_items()
        self.assertEqual(items[0].id, "file_open")

    def test_toggle_and_esc(self) -> None:
        self.palette.update(KeyMsg("esc"))
        self.assertFalse(self.palette.is_open)

        # Toggle key default ctrl+p
        self.palette.update(KeyMsg("ctrl+p"))
        self.assertTrue(self.palette.is_open)

    def test_mouse_interactions(self) -> None:
        self.palette.set_offset(0, 0)
        # Click on row at y=4 (first item is at y=3, second item at y=4)
        click_msg = MouseMsg(x=10, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS)
        self.palette.update(click_msg)
        self.assertEqual(self.palette.cursor, 1)

        # Double click to select
        dbl_msg = MouseMsg(x=10, y=4, button=MouseButton.LEFT, action=MouseAction.DOUBLE_CLICK)
        self.palette.update(dbl_msg)
        self.assertFalse(self.palette.is_open)
        self.assertIn(self.items[1].id, self.palette.recent_ids)

    def test_overlay(self) -> None:
        base = "Base Screen Line 1\nBase Screen Line 2\nBase Screen Line 3\nBase Screen Line 4\nBase Screen Line 5"
        self.palette.close()
        res_closed = self.palette.overlay(base)
        self.assertEqual(res_closed, base)

        self.palette.open()
        res_open = self.palette.overlay(base)
        self.assertNotEqual(res_open, base)
        self.assertIn("Command Palette", res_open)
