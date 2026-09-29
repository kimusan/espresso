"""Unit tests for Beans standard components."""

from __future__ import annotations

import unittest

from espresso import KeyMsg, Model
from espresso.beans import (
    Column,
    EchoMode,
    Progress,
    Spinner,
    SpinnerTickMsg,
    Table,
    TextInput,
    Viewport,
)


class TestBeansComponents(unittest.TestCase):
    def test_spinner_tick(self) -> None:
        sp = Spinner(frames=["A", "B", "C"], tag="test_sp")
        self.assertIn("A", sp.view())

        # Tick message advances frame
        sp2, cmd = sp.update(SpinnerTickMsg(tag="test_sp", frame=1))
        self.assertIsNotNone(cmd)
        self.assertIn("B", sp2.view())

    def test_textinput_typing_and_backspace(self) -> None:
        ti = TextInput(placeholder="Type here...")
        self.assertEqual(ti.value, "")

        # Type 'h', 'i'
        ti.update(KeyMsg("h"))
        ti.update(KeyMsg("i"))
        self.assertEqual(ti.value, "hi")

        # Backspace
        ti.update(KeyMsg("backspace"))
        self.assertEqual(ti.value, "h")

    def test_textinput_password_masking(self) -> None:
        ti = TextInput(echo_mode=EchoMode.PASSWORD)
        ti.set_value("secret")
        v = ti.view()
        self.assertNotIn("secret", v)
        self.assertIn("••••••", v)

    def test_progress_bar(self) -> None:
        pb = Progress(width=20, percent=0.5, show_percentage=True)
        v = pb.view()
        self.assertIn("50%", v)
        self.assertIn("█", v)
        self.assertIn("░", v)

    def test_viewport_scrolling(self) -> None:
        vp = Viewport(width=20, height=3)
        vp.set_content("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        self.assertEqual(vp.y_offset, 0)
        self.assertIn("Line 1", vp.view())

        # Scroll down
        vp.update(KeyMsg("down"))
        self.assertEqual(vp.y_offset, 1)
        self.assertIn("Line 2", vp.view())
        self.assertNotIn("Line 1", vp.view())

    def test_table_navigation(self) -> None:
        cols = [Column("ID", 5), Column("Name", 10)]
        rows = [["1", "Alice"], ["2", "Bob"], ["3", "Charlie"]]
        tb = Table(cols, rows)
        self.assertEqual(tb.cursor, 0)
        self.assertEqual(tb.selected_row, ["1", "Alice"])

        tb.update(KeyMsg("down"))
        self.assertEqual(tb.cursor, 1)
        self.assertEqual(tb.selected_row, ["2", "Bob"])


if __name__ == "__main__":
    unittest.main()
