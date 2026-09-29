"""Unit tests for Crema styling, box model, and layout engine."""

from __future__ import annotations

import os
import unittest

from espresso.crema import (
    Align,
    ANSIColor,
    ROUNDED_BORDER,
    Style,
    TrueColor,
    char_width,
    join_horizontal,
    join_vertical,
    parse_color,
    place,
    string_width,
    strip_ansi,
    truncate_ansi,
)


class TestCremaColorsAndWidth(unittest.TestCase):
    def test_parse_color_hex(self) -> None:
        c = parse_color("#FF5500")
        self.assertIsInstance(c, TrueColor)
        self.assertEqual(c.r, 255)
        self.assertEqual(c.g, 85)
        self.assertEqual(c.b, 0)
        self.assertEqual(c.render_fg(), "\x1b[38;2;255;85;0m")

    def test_parse_color_ansi(self) -> None:
        c = parse_color(205)
        self.assertIsInstance(c, ANSIColor)
        self.assertEqual(c.code, 205)
        self.assertEqual(c.render_fg(), "\x1b[38;5;205m")

    def test_unicode_cell_width(self) -> None:
        self.assertEqual(char_width("a"), 1)
        self.assertEqual(char_width("中"), 2)  # Chinese
        self.assertEqual(char_width("☕"), 2)  # Coffee emoji
        self.assertEqual(char_width("🚀"), 2)  # Rocket emoji
        self.assertEqual(char_width("✕"), 1)  # Multiplication X symbol
        self.assertEqual(char_width("✓"), 1)  # Check mark
        self.assertEqual(char_width("✗"), 1)  # Ballot X
        self.assertEqual(char_width("★"), 1)  # Star symbol

    def test_string_width_and_ansi_stripping(self) -> None:
        styled = "\x1b[1;31mHello\x1b[0m World"
        self.assertEqual(strip_ansi(styled), "Hello World")
        self.assertEqual(string_width(styled), 11)

        cjk_styled = "\x1b[34m你好\x1b[0m"
        self.assertEqual(string_width(cjk_styled), 4)

    def test_truncate_ansi(self) -> None:
        text = "\x1b[1;32mHelloWorld\x1b[0m"
        # Truncate to 6 cells with "…"
        trunc = truncate_ansi(text, 6, tail="…")
        self.assertEqual(string_width(trunc), 6)
        self.assertTrue(trunc.endswith("\x1b[0m"))


class TestCremaStyleAndBox(unittest.TestCase):
    def test_style_rendering_simple(self) -> None:
        s = Style().bold(True).foreground("#FFFFFF")
        res = s.render("Test")
        self.assertIn("Test", res)
        self.assertIn("\x1b[1m", res)
        self.assertIn("\x1b[38;2;255;255;255m", res)

    def test_style_with_padding_and_border(self) -> None:
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .padding(1, 2)
            .width(10)
            .align(Align.CENTER)
        )
        res = s.render("Hi")
        lines = res.splitlines()

        # Should have top border, 1 top padding row, 1 content row, 1 bottom padding row, bottom border = 5 rows
        self.assertEqual(len(lines), 5)
        self.assertTrue(lines[0].startswith("╭"))
        self.assertTrue(lines[0].endswith("╮"))
        self.assertTrue(lines[-1].startswith("╰"))
        self.assertTrue(lines[-1].endswith("╯"))

        # Visual width of each row should match
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)

    def test_layout_join_horizontal(self) -> None:
        b1 = "Box 1\nLine 2"
        b2 = "Box 2"
        joined = join_horizontal(Align.TOP, b1, b2)
        lines = joined.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("Box 1", lines[0])
        self.assertIn("Box 2", lines[0])
        self.assertIn("Line 2", lines[1])

    def test_layout_join_vertical(self) -> None:
        b1 = "A"
        b2 = "BB"
        joined = join_vertical(Align.CENTER, b1, b2)
        lines = joined.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(string_width(lines[0]), string_width(lines[1]))

    def test_place_utility(self) -> None:
        placed = place(10, 3, Align.CENTER, Align.CENTER, "OK")
        lines = placed.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(string_width(lines[1]), 10)
        self.assertIn("OK", lines[1])


if __name__ == "__main__":
    unittest.main()
