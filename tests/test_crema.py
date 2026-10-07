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
    gradient,
    join_horizontal,
    join_vertical,
    linear_gradient,
    multi_gradient,
    multi_gradient_colors,
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

    def test_emoji_zwj_and_ligature_widths(self) -> None:
        # Pirate flag: with explicit ZWJ (🏴 2 + ☠️ 2 = 4 cells in terminal)
        self.assertEqual(string_width("🏴‍☠️"), 4)
        self.assertEqual(string_width("🏴☠️"), 4)
        self.assertEqual(string_width("Captain Jack 🏴☠️"), 17)
        self.assertEqual(string_width("Captain Jack 🏴‍☠️"), 17)

        # Rainbow flag (🏳️ 2 + 🌈 2 = 4 cells in terminal)
        self.assertEqual(string_width("🏳️‍🌈"), 4)
        self.assertEqual(string_width("stephaniepixie 🏳️‍🌈 @stephaniepixie@fandom.garden"), 49)
        self.assertEqual(string_width("stephaniepixie   🌈 @stephaniepixie@fandom.garden"), 49)

        # Other ZWJ sequences: cursor advances per visible emoji component in terminals
        self.assertEqual(string_width("👨‍👩‍👧‍👦"), 8)
        self.assertEqual(string_width("🧑‍💻"), 4)
        self.assertEqual(string_width("❤️‍🔥"), 4)

        # Modifiers and composite symbols that combine into 2 cells
        self.assertEqual(string_width("👍🏽"), 2)
        self.assertEqual(string_width("👩🏾‍🦱"), 2)
        self.assertEqual(string_width("💁🏻‍♂️"), 2)
        self.assertEqual(string_width("🇩🇰"), 2)
        self.assertEqual(string_width("1️⃣"), 2)

        # Unicode 17.0 / unassigned fallback characters (e.g. 🫯 U+1FAEF Fight Cloud)
        self.assertEqual(char_width("🫯"), 1)
        self.assertEqual(string_width("Thomas Fuchs 🫯 @thomasfuchs@hachyderm.io"), 40)

        # Base symbols with vs without emoji presentation selector (VS16)
        self.assertEqual(char_width("❤"), 1)
        self.assertEqual(string_width("❤️"), 2)
        self.assertEqual(char_width("✔"), 1)
        self.assertEqual(char_width("✈"), 1)
        self.assertEqual(char_width("☕"), 2)
        self.assertEqual(char_width("✨"), 2)

    def test_truncate_ansi_with_graphemes(self) -> None:
        text = "Ahoy 🏴‍☠️ Matey"
        # Total width: 5 + 4 + 1 + 5 = 15
        self.assertEqual(string_width(text), 15)
        # Limit 7: "Ahoy " (5) + "…" (1) = 6 (emoji cluster of 4 cells cannot fit in remaining 2 cells)
        t7 = truncate_ansi(text, 7, tail="…")
        self.assertEqual(string_width(t7), 6)
        self.assertEqual(t7, "Ahoy …")

        # Limit 10: "Ahoy " (5) + "🏴‍☠️" (4) + "…" (1) = 10
        t10 = truncate_ansi(text, 10, tail="…")
        self.assertEqual(string_width(t10), 10)
        self.assertEqual(t10, "Ahoy 🏴‍☠️…")


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

    def test_style_background_padding_fill(self) -> None:
        s = Style().background("#333333").padding(1, 2)
        res = s.render("Test")
        lines = res.splitlines()
        self.assertEqual(len(lines), 3)  # 1 top pad + 1 content + 1 bot pad
        # Top pad and bot pad should contain the background ANSI code (\x1b[48;2;51;51;51m)
        self.assertIn("\x1b[48;2;51;51;51m", lines[0])
        self.assertIn("\x1b[48;2;51;51;51m", lines[1])
        self.assertIn("\x1b[48;2;51;51;51m", lines[2])
        # Visual width must be consistent
        self.assertEqual(string_width(lines[0]), string_width(lines[1]))
        self.assertEqual(string_width(lines[1]), string_width(lines[2]))

    def test_style_background_with_internal_ansi_resets(self) -> None:
        """Ensure internal \033[0m does not create uncolored gaps before alignment spaces."""
        s = Style().background("#1E1E2E").width(30)
        res = s.render("\033[1;32mGreen Text\033[0m")
        # Line must be width 30
        self.assertEqual(string_width(res), 30)
        # Background ANSI code \x1b[48;2;30;30;46m must appear both before and after Green Text
        bg_code = "\x1b[48;2;30;30;46m"
        self.assertIn(bg_code, res)
        # The trailing alignment spaces must also be styled with bg_code
        self.assertTrue(res.endswith(f"{bg_code}                    \x1b[0m"))

    def test_style_box_vertical_gradient(self) -> None:
        """Test vertical gradient background on a bordered card with text on top."""
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .background_gradient("#FF0000", "#0000FF", direction="vertical")
            .padding(1, 1)
            .width(20)
        )
        res = s.render("Line 1\nLine 2")
        lines = res.splitlines()
        # Border top + pad top (1) + 2 content + pad bot (1) + border bot = 6 rows
        self.assertEqual(len(lines), 6)
        # Verify visual width of each row is identical
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)
        # Top padding row has red bg
        self.assertIn("\x1b[48;2;255;0;0m", lines[1])
        # Bottom padding row has blue bg
        self.assertIn("\x1b[48;2;0;0;255m", lines[4])

    def test_style_box_horizontal_gradient(self) -> None:
        """Test horizontal gradient background across card columns with text on top."""
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .background_gradient("#FF0000", "#0000FF", direction="horizontal")
            .padding(0, 1)
            .width(20)
        )
        res = s.render("Gradient Card")
        lines = res.splitlines()
        self.assertEqual(len(lines), 3)  # Top border, content, bot border
        content_row = lines[1]
        self.assertEqual(string_width(content_row), string_width(lines[0]))
        # Starts with red bg and ends before border with blue bg
        self.assertIn("\x1b[48;2;255;0;0m", content_row)
        self.assertIn("\x1b[48;2;0;0;255m", content_row)

    def test_preserve_trailing_empty_lines(self) -> None:
        """Verify that trailing empty lines are preserved by Style and layout functions."""
        raw = "line 1\nline 2\n"
        rendered = Style().render(raw)
        lines = rendered.split("\n")
        self.assertEqual(len(lines), 3)

        bordered = Style().border(ROUNDED_BORDER).render(raw)
        b_lines = bordered.split("\n")
        # 3 content lines + 2 border lines (top + bottom) = 5 lines total
        self.assertEqual(len(b_lines), 5)

        jv = join_vertical(Align.LEFT, raw, "line 3")
        self.assertEqual(len(jv.split("\n")), 4)

        jh = join_horizontal(Align.TOP, raw, "foo\nbar\nbaz")
        self.assertEqual(len(jh.split("\n")), 3)

        pl = place(10, 5, Align.LEFT, Align.TOP, raw)
        self.assertEqual(len(pl.split("\n")), 5)


class TestCremaGradients(unittest.TestCase):
    def test_linear_gradient_foreground(self) -> None:
        res = linear_gradient("ABC", "#FF0000", "#0000FF")
        self.assertIn("\x1b[38;2;255;0;0m", res)  # Start red
        self.assertIn("\x1b[38;2;0;0;255m", res)  # End blue
        self.assertEqual(strip_ansi(res), "ABC")

    def test_linear_gradient_background(self) -> None:
        res = linear_gradient("ABC", "#FF0000", "#0000FF", background=True, fg_color="#FFFFFF")
        self.assertIn("\x1b[48;2;255;0;0m", res)  # Start bg red
        self.assertIn("\x1b[48;2;0;0;255m", res)  # End bg blue
        self.assertIn("\x1b[38;2;255;255;255m", res)  # Fg white
        self.assertEqual(strip_ansi(res), "ABC")

    def test_multi_gradient_colors_and_rendering(self) -> None:
        stops = ["#FF0000", "#00FF00", "#0000FF"]
        steps = multi_gradient_colors(stops, 5)
        self.assertEqual(len(steps), 5)
        self.assertEqual((steps[0].r, steps[0].g, steps[0].b), (255, 0, 0))
        self.assertEqual((steps[2].r, steps[2].g, steps[2].b), (0, 255, 0))
        self.assertEqual((steps[4].r, steps[4].g, steps[4].b), (0, 0, 255))

        res = multi_gradient("HELLO", stops)
        self.assertEqual(strip_ansi(res), "HELLO")
        self.assertIn("\x1b[38;2;255;0;0m", res)
        self.assertIn("\x1b[38;2;0;0;255m", res)

    def test_gradient_no_color(self) -> None:
        old_val = os.environ.get("NO_COLOR")
        try:
            os.environ["NO_COLOR"] = "1"
            res = linear_gradient("Testing", "#FF0000", "#00FF00")
            self.assertEqual(res, "Testing")
            self.assertNotIn("\x1b[", res)

            res_m = multi_gradient("Testing", ["#FF0000", "#00FF00", "#0000FF"])
            self.assertEqual(res_m, "Testing")
            self.assertNotIn("\x1b[", res_m)
        finally:
            if old_val is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = old_val


if __name__ == "__main__":
    unittest.main()
