"""Unit tests for QuickFix diagnostics drawer component."""

from __future__ import annotations

import unittest

from espresso.beans.quickfix import QuickFix, QuickFixItem, QuickFixSelectMsg
from espresso.core.keys import KeyMsg
from espresso.crema import strip_ansi


class TestQuickFix(unittest.TestCase):
    def test_quickfix_toggle_and_state(self) -> None:
        qf = QuickFix(items=[], is_open=False, toggle_key="ctrl+x")
        self.assertFalse(qf.is_open)

        # Toggle via key
        qf, _ = qf.update(KeyMsg("ctrl+x"))
        self.assertTrue(qf.is_open)

        # Esc closes
        qf, _ = qf.update(KeyMsg("esc"))
        self.assertFalse(qf.is_open)

    def test_navigation_and_selection(self) -> None:
        items = [
            QuickFixItem(file="main.py", line=12, message="undefined name 'x'", severity="error", code="F821"),
            QuickFixItem(file="utils.py", line=45, message="line too long", severity="warning", code="E501"),
        ]
        qf = QuickFix(items=items, is_open=True)
        self.assertEqual(qf.cursor, 0)
        self.assertEqual(qf.selected_item.message, "undefined name 'x'")

        # Move down
        qf, _ = qf.update(KeyMsg("down"))
        self.assertEqual(qf.cursor, 1)
        self.assertEqual(qf.selected_item.file, "utils.py")

        # Select
        qf, cmd = qf.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, QuickFixSelectMsg)
        self.assertEqual(msg.item.line, 45)
        self.assertEqual(msg.index, 1)

    def test_wrap_view_overlay(self) -> None:
        items = [QuickFixItem("app.py", 1, message="Syntax error", severity="error")]
        qf = QuickFix(items=items, is_open=False, height=6)

        bg = "Row 1\nRow 2\nRow 3\nRow 4\nRow 5\nRow 6\nRow 7\nRow 8"
        # Closed: returns bg unmodified
        v_closed = qf.wrap_view(bg, width=30, height=8)
        self.assertEqual(v_closed, bg)

        # Open: drawer overlay appears at bottom
        qf.is_open = True
        v_open = qf.wrap_view(bg, width=40, height=8)
        clean = strip_ansi(v_open)
        self.assertIn("Diagnostics", clean)
        self.assertIn("app.py:1", clean)
        self.assertIn("Syntax error", clean)


if __name__ == "__main__":
    unittest.main()
