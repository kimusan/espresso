"""Unit tests for MenuBar and DropdownMenu components."""

from __future__ import annotations

import unittest

from espresso.beans.menubar import (
    MenuBar,
    MenuCategory,
    MenuCloseMsg,
    MenuItem,
    MenuOpenMsg,
    MenuSelectMsg,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi


class TestMenuBar(unittest.TestCase):
    def setUp(self) -> None:
        self.action_called = False

        def _sample_action() -> None:
            self.action_called = True

        self.categories = [
            MenuCategory(
                id="file",
                label="File",
                mnemonic="f",
                items=[
                    MenuItem(id="new", label="New File", shortcut="Ctrl+N", action=_sample_action),
                    MenuItem(id="open", label="Open...", shortcut="Ctrl+O"),
                    MenuItem(id="sep1", label="", is_separator=True),
                    MenuItem(id="disabled_item", label="Disabled", enabled=False),
                    MenuItem(id="exit", label="Exit", shortcut="Ctrl+Q"),
                ],
            ),
            MenuCategory(
                id="edit",
                label="Edit",
                mnemonic="e",
                items=[
                    MenuItem(id="undo", label="Undo", shortcut="Ctrl+Z"),
                    MenuItem(id="redo", label="Redo", shortcut="Ctrl+Y"),
                ],
            ),
            MenuCategory(
                id="help",
                label="Help",
                mnemonic="h",
                items=[
                    MenuItem(id="about", label="About"),
                ],
            ),
        ]
        self.menubar = MenuBar(
            categories=self.categories,
            width=80,
            brand="EspressoApp",
            right_status="v1.0.0",
        )

    def test_initial_state(self) -> None:
        self.assertFalse(self.menubar.is_open)
        self.assertEqual(len(self.menubar.categories), 3)
        view_text = strip_ansi(self.menubar.view())
        self.assertIn("EspressoApp", view_text)
        self.assertIn("File ▾", view_text)
        self.assertIn("Edit ▾", view_text)
        self.assertIn("Help ▾", view_text)
        self.assertIn("v1.0.0", view_text)

    def test_f10_toggles_menu(self) -> None:
        # F10 opens first category
        self.menubar, cmd = self.menubar.update(KeyMsg("f10"))
        self.assertTrue(self.menubar.is_open)
        self.assertEqual(self.menubar.active_cat_idx, 0)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, MenuOpenMsg)
        self.assertEqual(msg.category_id, "file")

        # F10 again closes menu
        self.menubar, cmd2 = self.menubar.update(KeyMsg("f10"))
        self.assertFalse(self.menubar.is_open)
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertIsInstance(msg2, MenuCloseMsg)

    def test_alt_mnemonic_opens_category(self) -> None:
        self.menubar, cmd = self.menubar.update(KeyMsg("alt+e"))
        self.assertTrue(self.menubar.is_open)
        self.assertEqual(self.menubar.active_cat_idx, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertEqual(msg.category_id, "edit")

    def test_arrow_keys_navigation(self) -> None:
        # Open menu
        self.menubar.open_category(0)
        self.assertTrue(self.menubar.is_open)
        self.assertEqual(self.menubar.active_item_idx, 0)

        # Down arrow moves to next item (open)
        self.menubar, _ = self.menubar.update(KeyMsg("down"))
        self.assertEqual(self.menubar.active_item_idx, 1)

        # Down arrow again skips separator and disabled item, landing on exit (index 4)
        self.menubar, _ = self.menubar.update(KeyMsg("down"))
        self.assertEqual(self.menubar.active_item_idx, 4)

        # Down arrow wraps around to first item (new, index 0)
        self.menubar, _ = self.menubar.update(KeyMsg("down"))
        self.assertEqual(self.menubar.active_item_idx, 0)

        # Up arrow wraps back to last valid item (exit, index 4)
        self.menubar, _ = self.menubar.update(KeyMsg("up"))
        self.assertEqual(self.menubar.active_item_idx, 4)

        # Right arrow moves to next category (Edit)
        self.menubar, cmd = self.menubar.update(KeyMsg("right"))
        self.assertEqual(self.menubar.active_cat_idx, 1)
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd().category_id, "edit")

        # Left arrow wraps back to last category (Help)
        self.menubar, cmd = self.menubar.update(KeyMsg("left"))
        self.assertEqual(self.menubar.active_cat_idx, 0)

    def test_enter_activates_item_and_executes_callback(self) -> None:
        self.menubar.open_category(0)
        self.menubar.active_item_idx = 0  # "new" item
        self.assertFalse(self.action_called)

        self.menubar, cmd = self.menubar.update(KeyMsg("enter"))
        self.assertFalse(self.menubar.is_open)
        self.assertTrue(self.action_called)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, MenuSelectMsg)
        self.assertEqual(msg.category_id, "file")
        self.assertEqual(msg.item_id, "new")

    def test_esc_closes_dropdown(self) -> None:
        self.menubar.open_category(0)
        self.assertTrue(self.menubar.is_open)

        self.menubar, cmd = self.menubar.update(KeyMsg("esc"))
        self.assertFalse(self.menubar.is_open)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), MenuCloseMsg)

    def test_mouse_header_click_and_hover(self) -> None:
        # Category bounds: brand is "EspressoApp" (len 11 + 1 space = 12)
        # File header starts around x=12
        x0, x1 = self.menubar._cat_bounds[0]

        # Click on File header
        self.menubar, cmd = self.menubar.update(
            MouseMsg(x=x0 + 1, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertTrue(self.menubar.is_open)
        self.assertEqual(self.menubar.active_cat_idx, 0)

        # Hover to Edit category header
        e_x0, e_x1 = self.menubar._cat_bounds[1]
        self.menubar, cmd2 = self.menubar.update(
            MouseMsg(x=e_x0 + 1, y=0, button=MouseButton.NONE, action=MouseAction.MOTION)
        )
        self.assertTrue(self.menubar.is_open)
        self.assertEqual(self.menubar.active_cat_idx, 1)

    def test_mouse_dropdown_item_click(self) -> None:
        self.menubar.open_category(0)
        drop_x, drop_y, _, _ = self.menubar.dropdown_bounds()  # type: ignore

        # Click first item ("New File") at y = drop_y + 1
        self.menubar, cmd = self.menubar.update(
            MouseMsg(x=drop_x + 2, y=drop_y + 1, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertFalse(self.menubar.is_open)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, MenuSelectMsg)
        self.assertEqual(msg.category_id, "file")
        self.assertEqual(msg.item_id, "new")

    def test_mouse_click_outside_closes(self) -> None:
        self.menubar.open_category(0)
        self.assertTrue(self.menubar.is_open)

        # Click at coordinate far outside
        self.menubar, cmd = self.menubar.update(
            MouseMsg(x=70, y=10, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertFalse(self.menubar.is_open)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), MenuCloseMsg)

    def test_mouse_wheel_navigation(self) -> None:
        # Wheel on header when closed opens and cycles
        self.menubar, cmd = self.menubar.update(
            MouseMsg(x=15, y=0, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS)
        )
        self.assertTrue(self.menubar.is_open)
        self.assertEqual(self.menubar.active_cat_idx, 1)

        # Wheel in dropdown navigates items
        drop_x, drop_y, _, _ = self.menubar.dropdown_bounds()  # type: ignore
        self.menubar, _ = self.menubar.update(
            MouseMsg(x=drop_x + 2, y=drop_y + 1, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS)
        )
        self.assertEqual(self.menubar.active_item_idx, 1)

    def test_mouse_press_drag_release(self) -> None:
        self.menubar.open_category(0)
        drop_x, drop_y, _, _ = self.menubar.dropdown_bounds()  # type: ignore

        # Release mouse over "Open..." (row 1)
        self.menubar, cmd = self.menubar.update(
            MouseMsg(x=drop_x + 2, y=drop_y + 2, button=MouseButton.LEFT, action=MouseAction.RELEASE)
        )
        self.assertFalse(self.menubar.is_open)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, MenuSelectMsg)
        self.assertEqual(msg.item_id, "open")

    def test_mouse_double_click_item(self) -> None:
        self.menubar.open_category(0)
        drop_x, drop_y, _, _ = self.menubar.dropdown_bounds()  # type: ignore

        # Double click on "New File"
        self.menubar, cmd = self.menubar.update(
            MouseMsg(x=drop_x + 2, y=drop_y + 1, button=MouseButton.LEFT, action=MouseAction.DOUBLE_CLICK)
        )
        self.assertFalse(self.menubar.is_open)
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd().item_id, "new")  # type: ignore

    def test_render_overlay(self) -> None:
        base_view = "Line 0\nLine 1\nLine 2\nLine 3\nLine 4"
        # When closed, base_view unchanged
        self.assertEqual(self.menubar.render_overlay(base_view), base_view)

        # When open, overlay dropdown box
        self.menubar.open_category(0)
        overlaid = self.menubar.render_overlay(base_view)
        self.assertIn("New File", overlaid)
        self.assertIn("Ctrl+N", overlaid)


if __name__ == "__main__":
    unittest.main()
