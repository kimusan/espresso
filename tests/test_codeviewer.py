"""Unit tests for CodeViewer component."""

from __future__ import annotations

import unittest

from espresso.beans.codeviewer import (
    THEME_DRACULA,
    THEME_ESPRESSO,
    CodeViewer,
    highlight_code,
    highlight_python,
)
from espresso.core.keys import KeyMsg
from espresso.crema import strip_ansi


class TestCodeViewer(unittest.TestCase):
    def test_highlight_python_keywords_and_strings(self) -> None:
        code = "def hello():\n    return 'world'"
        lines = highlight_python(code, THEME_ESPRESSO)
        self.assertEqual(len(lines), 2)
        # Verify ANSI codes were injected
        self.assertIn("\x1b[", lines[0])
        self.assertEqual(strip_ansi(lines[0]), "def hello():")
        self.assertEqual(strip_ansi(lines[1]), "    return 'world'")

    def test_code_viewer_gutter_and_cursor(self) -> None:
        code = "x = 1\ny = 2\nz = 3"
        cv = CodeViewer(code=code, width=40, height=10, cursor_line=1)
        v = strip_ansi(cv.view())

        # Line numbers in gutter
        self.assertIn("1 │ ▶ x = 1", v)
        self.assertIn("2 │   y = 2", v)
        self.assertIn("3 │   z = 3", v)

        # Move cursor down
        cv, _ = cv.update(KeyMsg("down"))
        self.assertEqual(cv.cursor_line, 2)
        v2 = strip_ansi(cv.view())
        self.assertIn("1 │   x = 1", v2)
        self.assertIn("2 │ ▶ y = 2", v2)

    def test_navigation_keys(self) -> None:
        code = "\n".join([f"line_{i} = {i}" for i in range(20)])
        cv = CodeViewer(code=code, width=40, height=6)
        self.assertEqual(cv.cursor_line, 1)

        # Jump to end
        cv, _ = cv.update(KeyMsg("end"))
        self.assertEqual(cv.cursor_line, 20)

        # Up
        cv, _ = cv.update(KeyMsg("k"))
        self.assertEqual(cv.cursor_line, 19)

        # Home
        cv, _ = cv.update(KeyMsg("home"))
        self.assertEqual(cv.cursor_line, 1)

    def test_set_code_and_language(self) -> None:
        cv = CodeViewer(code="let a = 10;", language="javascript")
        v = strip_ansi(cv.view())
        self.assertIn("let a = 10;", v)
        self.assertIn("JAVASCRIPT", v)

        cv.set_code("fn main() {}", language="rust")
        v2 = strip_ansi(cv.view())
        self.assertIn("fn main() {}", v2)
        self.assertIn("RUST", v2)


if __name__ == "__main__":
    unittest.main()
