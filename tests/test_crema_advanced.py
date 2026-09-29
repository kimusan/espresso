"""Comprehensive unit tests for Crema advanced features: wrap_ansi, gradients, and border titles."""

from __future__ import annotations

import os
import unittest

from espresso.crema import (
    ROUNDED_BORDER,
    Align,
    Style,
    TrueColor,
    gradient,
    hex_to_rgb,
    linear_gradient,
    string_width,
    strip_ansi,
    wrap_ansi,
)


class TestWrapAnsi(unittest.TestCase):
    def test_plain_text_wrapping(self) -> None:
        text = "The quick brown fox jumps over the lazy dog"
        wrapped = wrap_ansi(text, 15)
        lines = wrapped.splitlines()
        for line in lines:
            self.assertLessEqual(string_width(line), 15)
        self.assertEqual(strip_ansi(wrapped), "The quick brown\nfox jumps over\nthe lazy dog")

    def test_ansi_color_preservation_across_breaks(self) -> None:
        # Red styled sentence wrapping to 2 lines at width 16
        red_text = "\x1b[31mHello Wonderful World\x1b[0m"
        wrapped = wrap_ansi(red_text, 16)
        lines = wrapped.splitlines()

        self.assertEqual(len(lines), 2)
        # Line 1 should be "Hello Wonderful"
        self.assertIn("Hello Wonderful", lines[0])
        self.assertLessEqual(string_width(lines[0]), 16)
        # Line 1 must end with reset code to avoid color bleed
        self.assertTrue(lines[0].endswith("\x1b[0m"))

        # Line 2 should be "World", and MUST start with red sequence
        self.assertTrue(lines[1].startswith("\x1b[31m"))
        self.assertTrue(lines[1].endswith("\x1b[0m"))
        self.assertIn("World", lines[1])
        self.assertLessEqual(string_width(lines[1]), 16)

    def test_multiple_styles_preserved(self) -> None:
        # Bold + Underline + TrueColor FG
        styled = "\x1b[1m\x1b[4m\x1b[38;2;255;100;50mBold Underline Colored\x1b[0m"
        wrapped = wrap_ansi(styled, 15)
        lines = wrapped.splitlines()

        self.assertGreaterEqual(len(lines), 2)
        # Second line must reopen bold, underline, and color
        self.assertIn("\x1b[1m", lines[1])
        self.assertIn("\x1b[4m", lines[1])
        self.assertIn("\x1b[38;2;255;100;50m", lines[1])
        self.assertTrue(lines[0].endswith("\x1b[0m"))

    def test_mid_sentence_color_change(self) -> None:
        styled = "\x1b[31mRed words\x1b[0m and \x1b[32mgreen words\x1b[0m"
        wrapped = wrap_ansi(styled, 12)
        lines = wrapped.splitlines()

        self.assertGreaterEqual(len(lines), 2)
        # Verify first line contains red and reset
        self.assertIn("\x1b[31m", lines[0])
        # Verify clean visual widths
        for line in lines:
            self.assertLessEqual(string_width(line), 12)

    def test_long_word_splitting(self) -> None:
        # Word longer than width must be split character by character
        long_word = "\x1b[34mSupercalifragilisticexpialidocious\x1b[0m"
        wrapped = wrap_ansi(long_word, 10)
        lines = wrapped.splitlines()

        self.assertGreaterEqual(len(lines), 4)
        for line in lines:
            self.assertLessEqual(string_width(line), 10)
            self.assertTrue(line.startswith("\x1b[34m"))
            self.assertTrue(line.endswith("\x1b[0m"))

    def test_wide_unicode_cjk_and_emoji(self) -> None:
        # CJK characters occupy 2 cells each
        cjk = "你好世界美好生活"  # 8 chars = 16 visual cells
        wrapped = wrap_ansi(cjk, 6)
        lines = wrapped.splitlines()

        for line in lines:
            self.assertLessEqual(string_width(line), 6)
        # Total text preserved
        self.assertEqual("".join(lines), cjk)

        # Emoji wrapping
        emojis = "🚀 ☕ 🌟 💻 ⚡ 🎉"
        wrapped_emojis = wrap_ansi(emojis, 6)
        for line in wrapped_emojis.splitlines():
            self.assertLessEqual(string_width(line), 6)

    def test_existing_newlines_preserved(self) -> None:
        text = "Line 1 is short\nLine 2 is also short\n\nLine 4 after empty line"
        wrapped = wrap_ansi(text, 30)
        lines = wrapped.split("\n")
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[0], "Line 1 is short")

    def test_leading_indentation_preserved(self) -> None:
        text = "    Indented line with several words that will wrap"
        wrapped = wrap_ansi(text, 20)
        lines = wrapped.splitlines()
        self.assertTrue(lines[0].startswith("    Indented"))
        # Continuation line should NOT have leading space from word break
        self.assertFalse(lines[1].startswith(" "))

    def test_empty_and_zero_width_edge_cases(self) -> None:
        self.assertEqual(wrap_ansi("", 10), "")
        self.assertEqual(wrap_ansi("Hello", 0), "")
        self.assertEqual(wrap_ansi("Hello", -5), "")
        # Already fitting string returns unchanged
        self.assertEqual(wrap_ansi("Short", 20), "Short")


class TestLinearGradient(unittest.TestCase):
    def test_hex_to_rgb_parsing(self) -> None:
        self.assertEqual(hex_to_rgb("#FF5500"), (255, 85, 0))
        self.assertEqual(hex_to_rgb("00FF00"), (0, 255, 0))
        self.assertEqual(hex_to_rgb("#F0A"), (255, 0, 170))
        with self.assertRaises(ValueError):
            hex_to_rgb("invalid")

    def test_gradient_palette_generation(self) -> None:
        steps = gradient("#000000", "#FFFFFF", 3)
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], TrueColor(0, 0, 0))
        self.assertEqual(steps[1], TrueColor(128, 128, 128))
        self.assertEqual(steps[2], TrueColor(255, 255, 255))

        # Edge cases
        self.assertEqual(gradient("#000000", "#FFFFFF", 0), [])
        self.assertEqual(gradient("#FF0000", "#0000FF", 1), [TrueColor(255, 0, 0)])

    def test_linear_gradient_characters(self) -> None:
        text = "ABC"
        res = linear_gradient(text, "#000000", "#FFFFFF")
        self.assertEqual(strip_ansi(res), "ABC")
        self.assertEqual(string_width(res), 3)

        # First char is black, last char is white
        self.assertIn("\x1b[38;2;0;0;0mA", res)
        self.assertIn("\x1b[38;2;255;255;255mC", res)
        self.assertTrue(res.endswith("\x1b[0m"))

    def test_linear_gradient_multiline(self) -> None:
        text = "Hello\nWorld"
        res = linear_gradient(text, "#FF0000", "#0000FF")
        lines = res.split("\n")
        self.assertEqual(len(lines), 2)
        # Line 1 ends with reset before newline
        self.assertTrue(lines[0].endswith("\x1b[0m"))
        # Line 2 ends with reset
        self.assertTrue(lines[1].endswith("\x1b[0m"))
        self.assertEqual(strip_ansi(res), text)

    def test_linear_gradient_no_color_env(self) -> None:
        old_val = os.environ.get("NO_COLOR")
        try:
            os.environ["NO_COLOR"] = "1"
            res = linear_gradient("Espresso", "#FF0000", "#0000FF")
            self.assertEqual(res, "Espresso")
            self.assertNotIn("\x1b[", res)
        finally:
            if old_val is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = old_val

    def test_empty_gradient(self) -> None:
        self.assertEqual(linear_gradient("", "#FF0000", "#0000FF"), "")


class TestBorderTitle(unittest.TestCase):
    def test_border_title_left(self) -> None:
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .width(20)
            .border_title(" [ Title ] ", align=Align.LEFT)
        )
        rendered = s.render("Content")
        lines = rendered.splitlines()

        # Top line must start with ╭─ [ Title ]
        self.assertTrue(lines[0].startswith("╭─ [ Title ] "))
        self.assertTrue(lines[0].endswith("╮"))
        # All lines must have equal visual width
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)
        self.assertEqual(widths[0], 22)  # 20 inner + 2 borders

    def test_border_title_center(self) -> None:
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .width(24)
            .border_title(" [ Center ] ", align=Align.CENTER)
        )
        rendered = s.render("Box body")
        lines = rendered.splitlines()

        top_line = lines[0]
        self.assertIn(" [ Center ] ", top_line)
        # Visual width consistency
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)
        self.assertEqual(widths[0], 26)

    def test_border_title_right(self) -> None:
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .width(22)
            .border_title(" [ End ] ", align=Align.RIGHT)
        )
        rendered = s.render("Right-aligned title")
        lines = rendered.splitlines()

        top_line = lines[0]
        # Should end with [ End ] ─╮
        self.assertTrue(top_line.endswith(" [ End ] ─╮"))
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)

    def test_styled_title_and_border_colors(self) -> None:
        styled_title = "\x1b[1;33m [ Gold ] \x1b[0m"
        s = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E676")
            .width(20)
            .border_title(styled_title)
        )
        rendered = s.render("Test")
        lines = rendered.splitlines()

        # Top border must contain green border color and yellow title
        top_line = lines[0]
        self.assertIn("\x1b[38;2;0;230;118m", top_line)
        self.assertIn("\x1b[1;33m [ Gold ] \x1b[0m", top_line)
        # Width check
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)

    def test_auto_expansion_for_title(self) -> None:
        # If width is not explicitly specified, box expands to fit the title
        title = " [ Very Long Informative Title ] "
        s = Style().border(ROUNDED_BORDER).border_title(title)
        rendered = s.render("Hi")
        lines = rendered.splitlines()

        top_line = lines[0]
        self.assertIn(title, top_line)
        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)
        self.assertGreaterEqual(widths[0], string_width(title) + 2)

    def test_title_truncation_when_width_constrained(self) -> None:
        # When explicit width is smaller than title, title should be truncated without breaking the box
        long_title = " [ Super Long Title That Cannot Fit ] "
        s = Style().border(ROUNDED_BORDER).width(12).border_title(long_title)
        rendered = s.render("Data")
        lines = rendered.splitlines()

        widths = [string_width(l) for l in lines]
        self.assertEqual(len(set(widths)), 1)
        self.assertEqual(widths[0], 14)

    def test_border_title_none_or_disabled(self) -> None:
        # Style with no border should not include border title
        s_no_border = Style().border_title("Title").render("Content")
        self.assertNotIn("Title", s_no_border)

        # Style with top border disabled should not include border title
        s_no_top = (
            Style()
            .border(ROUNDED_BORDER, top=False)
            .border_title("Title")
            .render("Content")
        )
        self.assertNotIn("Title", s_no_top)

        # Style with border_title(None) should render standard border bar
        s_cleared = (
            Style()
            .border(ROUNDED_BORDER)
            .border_title("Title")
            .border_title(None)
            .render("Content")
        )
        self.assertNotIn("Title", s_cleared)
        lines = s_cleared.splitlines()
        self.assertTrue(lines[0].startswith("╭─"))


class TestCremaAdvancedEdgeCases(unittest.TestCase):
    def test_unclosed_style_gets_reset(self) -> None:
        # Style left open at end of text must have \x1b[0m appended to prevent bleed
        open_style = "\x1b[35mPurple Text Without Reset"
        wrapped = wrap_ansi(open_style, 30)
        self.assertTrue(wrapped.endswith("\x1b[0m"))

    def test_width_smaller_than_cjk_char(self) -> None:
        # A single CJK char (width 2) when width=1 should not cause an infinite loop
        cjk = "中"
        wrapped = wrap_ansi(cjk, 1)
        self.assertEqual(wrapped, "中")

    def test_consecutive_spaces_between_words(self) -> None:
        text = "Word1    Word2"
        # Fits in 20 cells: multiple spaces preserved
        wrapped_wide = wrap_ansi(text, 20)
        self.assertEqual(wrapped_wide, "Word1    Word2")

        # Wraps in 8 cells: inter-word spaces dropped
        wrapped_narrow = wrap_ansi(text, 8)
        self.assertEqual(wrapped_narrow, "Word1\nWord2")

    def test_linear_gradient_short_hex(self) -> None:
        res = linear_gradient("Test", "#F00", "#00F")
        self.assertEqual(strip_ansi(res), "Test")
        self.assertTrue(res.startswith("\x1b[38;2;255;0;0m"))
        self.assertTrue(res.endswith("\x1b[0m"))


if __name__ == "__main__":
    unittest.main()
