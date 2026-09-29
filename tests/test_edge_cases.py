"""Comprehensive edge-case tests for Espresso, Crema, and Beans.

Covers:
- Empty strings, whitespace-only, and zero-length inputs
- Zero and negative terminal dimensions (widths and heights)
- Unicode combining accents and non-spacing marks
- Multi-byte emojis and East Asian Wide characters
- Extreme values, NaN, and zero-division protection
- Rapid and out-of-order tick commands
"""

from __future__ import annotations

import math
import unittest

from espresso.beans import (
    Column,
    EchoMode,
    Help,
    KeyBinding,
    Progress,
    Spinner,
    SpinnerTickMsg,
    Stopwatch,
    StopwatchTickMsg,
    Table,
    TextArea,
    TextInput,
    Timer,
    TimerTickMsg,
    TimerTimeoutMsg,
    Viewport,
)
from espresso.core.keys import Key, KeyMsg
from espresso.crema import (
    ROUNDED_BORDER,
    Align,
    Style,
    TrueColor,
    char_width,
    gradient,
    hex_to_rgb,
    join_horizontal,
    join_vertical,
    linear_gradient,
    parse_color,
    place,
    string_width,
    strip_ansi,
    truncate_ansi,
    wrap_ansi,
)


class TestEmptyAndZeroInputs(unittest.TestCase):
    """Test handling of empty strings, whitespace, and zero-length inputs."""

    def test_crema_width_empty_and_whitespace(self) -> None:
        self.assertEqual(char_width(""), 0)
        self.assertEqual(string_width(""), 0)
        self.assertEqual(strip_ansi(""), "")
        self.assertEqual(truncate_ansi("", 10), "")
        self.assertEqual(truncate_ansi("Hello", 0), "")
        self.assertEqual(truncate_ansi("Hello", -5), "")

        # Whitespace-only strings
        self.assertEqual(string_width("   "), 3)
        self.assertEqual(strip_ansi("   "), "   ")
        self.assertEqual(truncate_ansi("     ", 3), "  …")

    def test_wrap_ansi_empty_and_whitespace(self) -> None:
        self.assertEqual(wrap_ansi("", 10), "")
        self.assertEqual(wrap_ansi("Hello", 0), "")
        self.assertEqual(wrap_ansi("Hello", -5), "")
        self.assertEqual(wrap_ansi("     ", 3), "   \n  ")

    def test_crema_layout_empty_blocks(self) -> None:
        self.assertEqual(join_horizontal(Align.TOP), "")
        self.assertEqual(join_horizontal(Align.TOP, "", "", ""), "")
        self.assertEqual(join_vertical(Align.LEFT), "")
        self.assertEqual(join_vertical(Align.LEFT, "", ""), "")
        self.assertEqual(place(0, 0, Align.CENTER, Align.CENTER, ""), "")
        self.assertEqual(place(10, 0, Align.CENTER, Align.CENTER, "test"), "")

    def test_gradient_empty_and_newlines(self) -> None:
        self.assertEqual(linear_gradient("", "#000000", "#FFFFFF"), "")
        self.assertEqual(linear_gradient("\n\n\n", "#FF0000", "#0000FF"), "\n\n\n")
        self.assertEqual(gradient("#000000", "#FFFFFF", 0), [])
        self.assertEqual(gradient("#000000", "#FFFFFF", -3), [])

    def test_style_render_empty(self) -> None:
        s = Style().border(ROUNDED_BORDER).padding(1, 1)
        res = s.render("")
        self.assertTrue(len(res) > 0)
        lines = res.splitlines()
        self.assertEqual(len(lines), 5)  # top border, top pad, content, bot pad, bot border

    def test_beans_empty_state_handling(self) -> None:
        # TextInput
        ti = TextInput(placeholder="")
        ti.set_value("")
        self.assertEqual(ti.value, "")
        self.assertEqual(ti.cursor_pos, 0)
        self.assertNotIn("None", ti.view())

        # TextArea
        ta = TextArea(placeholder="")
        ta.set_value("")
        self.assertEqual(ta.value, "")
        self.assertEqual(ta.cursor, (0, 0))
        self.assertEqual(ta.line_count, 1)

        # Viewport
        vp = Viewport(width=20, height=5)
        vp.set_content("")
        self.assertEqual(vp.lines, [])
        self.assertEqual(vp.max_offset, 0)
        self.assertEqual(vp.scroll_percent, 1.0)

        # Table
        tb = Table(columns=[], rows=[])
        self.assertIsNone(tb.selected_row)
        tb_view = tb.view()
        self.assertIsInstance(tb_view, str)

        # Help
        h = Help([])
        self.assertEqual(h.view(), "")


class TestZeroTerminalDimensions(unittest.TestCase):
    """Test behavior when terminal or component widths/heights are zero or negative."""

    def test_style_zero_dimensions(self) -> None:
        s_zero_w = Style().width(0).render("content")
        self.assertIn("content", s_zero_w)

        s_neg_w = Style().width(-10).render("content")
        self.assertIn("content", s_neg_w)

        s_zero_h = Style().height(0).render("content")
        self.assertIn("content", s_zero_h)

    def test_help_zero_and_negative_width(self) -> None:
        bindings = [KeyBinding("q", "quit"), KeyBinding("s", "save")]
        h_zero = Help(bindings, width=0)
        self.assertEqual(h_zero.view(), "")

        h_neg = Help(bindings, width=-10)
        self.assertEqual(h_neg.view(), "")

    def test_textarea_zero_dimensions(self) -> None:
        ta_zero_w = TextArea(width=0, height=5)
        self.assertEqual(ta_zero_w.view(), "")

        ta_neg_w = TextArea(width=-5, height=5)
        self.assertEqual(ta_neg_w.view(), "")

        ta_zero_h = TextArea(width=20, height=0)
        self.assertEqual(ta_zero_h.view(), "")

        ta_neg_h = TextArea(width=20, height=-3)
        self.assertEqual(ta_neg_h.view(), "")

    def test_viewport_zero_dimensions(self) -> None:
        vp_zero_w = Viewport(width=0, height=5)
        vp_zero_w.set_content("some text")
        self.assertEqual(vp_zero_w.view(), "")

        vp_zero_h = Viewport(width=20, height=0)
        vp_zero_h.set_content("some text")
        self.assertEqual(vp_zero_h.view(), "")

    def test_progress_zero_width(self) -> None:
        p = Progress(width=0, percent=0.5)
        v = p.view()
        self.assertIn("50%", v)

        # Setting direct attribute to 0
        p.width = 0
        v2 = p.view()
        self.assertIn("50%", v2)

    def test_table_zero_height(self) -> None:
        tb = Table([Column("Col", 10)], [["val1"], ["val2"]], height=0)
        v = tb.view()
        # Should render headers but 0 body rows
        self.assertNotIn("val1", v)
        self.assertIn("Col", v)


class TestCombiningAccentsAndUnicode(unittest.TestCase):
    """Test unicode combining accents, zero-width marks, and normalizations."""

    def test_combining_accents_widths(self) -> None:
        # e + combining acute accent (\u0301)
        decomposed_e = "e\u0301"
        self.assertEqual(len(decomposed_e), 2)
        self.assertEqual(char_width("e"), 1)
        self.assertEqual(char_width("\u0301"), 0)
        self.assertEqual(string_width(decomposed_e), 1)

        # cafe\u0301 vs café
        decomposed_cafe = "cafe\u0301"
        composed_cafe = "café"
        self.assertEqual(string_width(decomposed_cafe), 4)
        self.assertEqual(string_width(composed_cafe), 4)

    def test_combining_accents_wrapping_and_truncation(self) -> None:
        decomposed = "cafe\u0301"
        wrapped = wrap_ansi(decomposed, 4)
        self.assertEqual(wrapped, decomposed)

        # Truncation
        truncated = truncate_ansi(decomposed, 3, tail="…")
        self.assertEqual(truncated, "ca…")

    def test_combining_accents_in_textarea(self) -> None:
        ta = TextArea()
        ta.insert_text("cafe\u0301")
        self.assertEqual(ta.value, "cafe\u0301")
        self.assertEqual(ta.cursor, (0, 5))  # 5 python characters

        # Backspace should delete the combining accent first
        ta.update(KeyMsg("backspace"))
        self.assertEqual(ta.value, "cafe")
        self.assertEqual(ta.cursor, (0, 4))


class TestMultiByteEmojisAndWideCharacters(unittest.TestCase):
    """Test multi-byte UTF-8 emojis, wide characters, and complex sequences."""

    def test_emoji_and_cjk_widths(self) -> None:
        # 3-byte and 4-byte emojis
        coffee = "☕"  # 3 bytes, width 2
        rocket = "🚀"  # 4 bytes, width 2
        party = "🎉"   # 4 bytes, width 2
        fire = "🔥"    # 4 bytes, width 2
        cjk = "中"     # 3 bytes, width 2

        self.assertEqual(char_width(coffee), 2)
        self.assertEqual(char_width(rocket), 2)
        self.assertEqual(char_width(party), 2)
        self.assertEqual(char_width(fire), 2)
        self.assertEqual(char_width(cjk), 2)

        combined = "☕🚀🎉🔥中"
        self.assertEqual(string_width(combined), 10)

    def test_emoji_word_wrapping(self) -> None:
        emojis = "🚀 ☕ 🎉 🔥"
        wrapped = wrap_ansi(emojis, 5)
        lines = wrapped.splitlines()
        for line in lines:
            self.assertLessEqual(string_width(line), 5)
        self.assertEqual(len(lines), 2)

    def test_emoji_linear_gradient(self) -> None:
        emojis = "☕🚀🎉"
        colored = linear_gradient(emojis, "#FF0000", "#0000FF")
        self.assertEqual(strip_ansi(colored), emojis)
        self.assertEqual(string_width(colored), 6)
        self.assertTrue(colored.endswith("\x1b[0m"))

    def test_textinput_with_emojis(self) -> None:
        ti = TextInput()
        ti.set_value("🚀☕")
        self.assertEqual(ti.value, "🚀☕")
        self.assertEqual(ti.cursor_pos, 2)

        # Backspace removes one emoji
        ti.update(KeyMsg("backspace"))
        self.assertEqual(ti.value, "🚀")
        self.assertEqual(ti.cursor_pos, 1)

    def test_textarea_with_emojis(self) -> None:
        ta = TextArea()
        ta.insert_text("Hello 🚀\nWorld ☕")
        self.assertEqual(ta.line_count, 2)
        self.assertEqual(ta.cursor, (1, 7))

        v = ta.view()
        self.assertIn("🚀", v)
        self.assertIn("☕", v)


class TestExtremeValuesAndZeroDivision(unittest.TestCase):
    """Test extreme parameters, NaN, negative values, and zero division protection."""

    def test_progress_zero_division_and_extremes(self) -> None:
        # Zero percent
        p_zero = Progress(percent=0.0)
        self.assertEqual(p_zero.percent, 0.0)
        self.assertIn("0%", p_zero.view())

        # Full percent
        p_full = Progress(percent=1.0)
        self.assertEqual(p_full.percent, 1.0)
        self.assertIn("100%", p_full.view())

        # Negative percent clamped to 0.0
        p_neg = Progress(percent=-10.0)
        self.assertEqual(p_neg.percent, 0.0)

        # Overflow percent clamped to 1.0
        p_over = Progress(percent=999.0)
        self.assertEqual(p_over.percent, 1.0)

        # NaN percent
        p_nan = Progress(percent=float("nan"))
        self.assertEqual(p_nan.percent, 0.0)
        p_nan.set_percent(float("nan"))
        self.assertEqual(p_nan.percent, 0.0)

    def test_timer_zero_timeout_and_extremes(self) -> None:
        # Zero timeout
        t_zero = Timer(timeout=0.0, auto_start=True)
        self.assertEqual(t_zero.percent, 1.0)
        self.assertEqual(t_zero.remaining, 0.0)
        self.assertIsNone(t_zero.init())
        self.assertEqual(t_zero.view(), "00:00")

        # Negative timeout
        t_neg = Timer(timeout=-5.0)
        self.assertEqual(t_neg.initial_timeout, 0.0)
        self.assertEqual(t_neg.percent, 1.0)

        # NaN timeout
        t_nan = Timer(timeout=float("nan"))
        self.assertEqual(t_nan.initial_timeout, 0.0)

        # Negative interval clamped to 0.001
        t_inv = Timer(timeout=10.0, interval=-1.0)
        self.assertEqual(t_inv.interval, 0.001)

        # set_remaining with negative value
        t_rem = Timer(timeout=10.0, auto_start=False)
        t_rem.set_remaining(-5.0)
        self.assertEqual(t_rem.remaining, 0.0)
        self.assertTrue(t_rem.timedout)

    def test_stopwatch_extremes_and_huge_elapsed(self) -> None:
        sw = Stopwatch(interval=-5.0)
        self.assertEqual(sw.interval, 0.001)

        # Negative elapsed clamped to 0.0
        sw.set_elapsed(-10.0)
        self.assertEqual(sw.elapsed, 0.0)

        # NaN elapsed
        sw.set_elapsed(float("nan"))
        self.assertEqual(sw.elapsed, 0.0)

        # Extreme elapsed time: 1,000,000 seconds (~277 hours)
        sw.set_elapsed(1_000_000.0)
        self.assertEqual(sw.view(), "277:46:40.00")

    def test_spinner_empty_frames_and_fps_extremes(self) -> None:
        # Empty frames fallback to DOTS
        sp_empty = Spinner(frames=[])
        self.assertGreater(len(sp_empty.frames), 0)
        self.assertIsNotNone(sp_empty.view())

        # Negative and zero FPS clamped
        sp_fps0 = Spinner(fps=0.0)
        self.assertEqual(sp_fps0.interval, 1.0)

        sp_fps_neg = Spinner(fps=-10.0)
        self.assertEqual(sp_fps_neg.interval, 1.0)

        # High FPS
        sp_fast = Spinner(fps=100.0)
        self.assertAlmostEqual(sp_fast.interval, 0.01)

    def test_hex_to_rgb_and_parse_color_edge_cases(self) -> None:
        # Short 3-char hex
        self.assertEqual(hex_to_rgb("F0A"), (255, 0, 170))
        self.assertEqual(hex_to_rgb("#F0A"), (255, 0, 170))

        # Invalid hex raises ValueError
        with self.assertRaises(ValueError):
            hex_to_rgb("xyz")
        with self.assertRaises(ValueError):
            hex_to_rgb("#12345")  # 5 characters

        # parse_color fallbacks
        c_invalid = parse_color("invalid_color_string")
        self.assertEqual(c_invalid.render_fg(), "")
        self.assertEqual(c_invalid.render_bg(), "")

    def test_gradient_edge_steps(self) -> None:
        # Exactly 1 step
        g1 = gradient("#000000", "#FFFFFF", 1)
        self.assertEqual(len(g1), 1)
        self.assertEqual(g1[0], TrueColor(0, 0, 0))

        # Exactly 2 steps
        g2 = gradient("#000000", "#FFFFFF", 2)
        self.assertEqual(len(g2), 2)
        self.assertEqual(g2[0], TrueColor(0, 0, 0))
        self.assertEqual(g2[1], TrueColor(255, 255, 255))


class TestRapidTickCommands(unittest.TestCase):
    """Test out-of-order, stale, and rapid tick commands."""

    def test_timer_stale_tick_ignored(self) -> None:
        t = Timer(timeout=10.0, tag="my_timer", auto_start=True)
        t.init()
        initial_id = t._tick_id

        # Stale tick message with previous id
        t.update(TimerTickMsg(tag="my_timer", id=initial_id - 1))
        self.assertEqual(t._tick_id, initial_id)
        self.assertEqual(t.remaining, 10.0)

        # Mismatched tag ignored
        t.update(TimerTickMsg(tag="other_tag", id=initial_id))
        self.assertEqual(t.remaining, 10.0)

        # Timer stopped should ignore incoming tick
        t.stop()
        self.assertFalse(t.running)
        t.update(TimerTickMsg(tag="my_timer", id=t._tick_id))
        self.assertFalse(t.running)

    def test_stopwatch_stale_tick_ignored(self) -> None:
        sw = Stopwatch(tag="my_sw", auto_start=False)
        sw.set_elapsed(2.5)
        initial_id = sw._tick_id

        # Stale tick message
        sw.update(StopwatchTickMsg(tag="my_sw", id=initial_id - 1))
        self.assertEqual(sw._tick_id, initial_id)
        self.assertEqual(sw.elapsed, 2.5)

        # Mismatched tag
        sw.update(StopwatchTickMsg(tag="other_tag", id=initial_id))
        self.assertEqual(sw.elapsed, 2.5)

        # Stopped stopwatch ignores tick
        self.assertFalse(sw.running)
        sw.update(StopwatchTickMsg(tag="my_sw", id=sw._tick_id))
        self.assertFalse(sw.running)
        self.assertEqual(sw.elapsed, 2.5)

    def test_spinner_large_frame_wrap(self) -> None:
        sp = Spinner(tag="my_sp")
        # Extremely large frame number should wrap smoothly without error
        sp.update(SpinnerTickMsg(tag="my_sp", frame=1_000_003))
        self.assertEqual(sp.frame_idx, 1_000_003 % len(sp.frames))

        # Mismatched tag ignored
        old_frame = sp.frame_idx
        sp.update(SpinnerTickMsg(tag="other_sp", frame=5))
        self.assertEqual(sp.frame_idx, old_frame)

    def test_rapid_timer_lifecycle(self) -> None:
        t = Timer(timeout=5.0, auto_start=False)
        # Rapid sequence of start/stop/toggle/reset
        for _ in range(50):
            t.start()
            t.stop()
            t.toggle()
            t.reset(timeout=5.0)
        self.assertFalse(t.running)
        self.assertEqual(t.remaining, 5.0)


if __name__ == "__main__":
    unittest.main()
