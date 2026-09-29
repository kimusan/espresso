"""Unit tests for advanced Beans components: TextArea, Help, and Timer/Stopwatch."""

from __future__ import annotations

import unittest

from espresso.beans.help import Help, KeyBinding, KeyMap
from espresso.beans.textarea import TextArea
from espresso.beans.timer import (
    Stopwatch,
    StopwatchTickMsg,
    Timer,
    TimerTickMsg,
    TimerTimeoutMsg,
)
from espresso.core.keys import Key, KeyMsg
from espresso.crema import strip_ansi


class TestTextAreaComponent(unittest.TestCase):
    def test_initial_state(self) -> None:
        ta = TextArea()
        self.assertEqual(ta.value, "")
        self.assertEqual(ta.lines, [""])
        self.assertEqual(ta.line_count, 1)
        self.assertEqual(ta.cursor, (0, 0))

    def test_typing_simple(self) -> None:
        ta = TextArea()
        ta.update(KeyMsg("a"))
        ta.update(KeyMsg("b"))
        ta.update(KeyMsg("c"))
        self.assertEqual(ta.value, "abc")
        self.assertEqual(ta.cursor, (0, 3))

    def test_enter_and_multiline(self) -> None:
        ta = TextArea()
        ta.update(KeyMsg("f"))
        ta.update(KeyMsg("o"))
        ta.update(KeyMsg("o"))
        ta.update(KeyMsg("enter"))
        ta.update(KeyMsg("b"))
        ta.update(KeyMsg("a"))
        ta.update(KeyMsg("r"))
        self.assertEqual(ta.lines, ["foo", "bar"])
        self.assertEqual(ta.value, "foo\nbar")
        self.assertEqual(ta.line_count, 2)
        self.assertEqual(ta.cursor, (1, 3))

    def test_arrow_navigation(self) -> None:
        ta = TextArea()
        ta.set_value("first\nsecond")
        # Cursor starts at (1, 6)
        self.assertEqual(ta.cursor, (1, 6))

        # Up
        ta.update(KeyMsg("up"))
        self.assertEqual(ta.cursor, (0, 5))

        # Left to start of line 0
        for _ in range(5):
            ta.update(KeyMsg("left"))
        self.assertEqual(ta.cursor, (0, 0))

        # Left at (0, 0) should clamp
        ta.update(KeyMsg("left"))
        self.assertEqual(ta.cursor, (0, 0))

        # Down to line 1
        ta.update(KeyMsg("down"))
        self.assertEqual(ta.cursor, (1, 0))

        # Left wraps to end of line 0
        ta.update(KeyMsg("left"))
        self.assertEqual(ta.cursor, (0, 5))

        # Right wraps to start of line 1
        ta.update(KeyMsg("right"))
        self.assertEqual(ta.cursor, (1, 0))

    def test_home_and_end(self) -> None:
        ta = TextArea()
        ta.set_value("hello world")
        self.assertEqual(ta.cursor, (0, 11))

        ta.update(KeyMsg("home"))
        self.assertEqual(ta.cursor, (0, 0))

        ta.update(KeyMsg("end"))
        self.assertEqual(ta.cursor, (0, 11))

        ta.update(KeyMsg("ctrl+a"))
        self.assertEqual(ta.cursor, (0, 0))

        ta.update(KeyMsg("ctrl+e"))
        self.assertEqual(ta.cursor, (0, 11))

    def test_backspace_within_and_across_lines(self) -> None:
        ta = TextArea()
        ta.set_value("ab\ncd")
        # Cursor at (1, 2)
        ta.update(KeyMsg("backspace"))
        self.assertEqual(ta.value, "ab\nc")
        self.assertEqual(ta.cursor, (1, 1))

        ta.update(KeyMsg("backspace"))
        self.assertEqual(ta.value, "ab\n")
        self.assertEqual(ta.cursor, (1, 0))

        # Backspace at start of line 1 merges with line 0
        ta.update(KeyMsg("backspace"))
        self.assertEqual(ta.value, "ab")
        self.assertEqual(ta.line_count, 1)
        self.assertEqual(ta.cursor, (0, 2))

    def test_delete_within_and_across_lines(self) -> None:
        ta = TextArea()
        ta.set_value("ab\ncd")
        ta.set_cursor(0, 1)  # Between 'a' and 'b'

        ta.update(KeyMsg("delete"))
        self.assertEqual(ta.value, "a\ncd")

        # Now cursor at (0, 1) is at end of line 0 ("a"), delete merges next line
        ta.update(KeyMsg("delete"))
        self.assertEqual(ta.value, "acd")
        self.assertEqual(ta.line_count, 1)

    def test_tab_indentation(self) -> None:
        ta = TextArea(tab_size=4)
        ta.update(KeyMsg("tab"))
        self.assertEqual(ta.value, "    ")
        self.assertEqual(ta.cursor, (0, 4))

    def test_set_value_and_clear(self) -> None:
        ta = TextArea()
        ta.set_value("one\ntwo\nthree")
        self.assertEqual(ta.line_count, 3)
        self.assertEqual(ta.cursor, (2, 5))

        ta.clear()
        self.assertEqual(ta.value, "")
        self.assertEqual(ta.cursor, (0, 0))
        self.assertEqual(ta.line_count, 1)

    def test_insert_text_multiline(self) -> None:
        ta = TextArea()
        ta.set_value("hello world")
        ta.set_cursor(0, 5)
        ta.insert_text(" beautiful\nnew")
        self.assertEqual(ta.lines, ["hello beautiful", "new world"])
        self.assertEqual(ta.cursor, (1, 3))

    def test_line_numbers_toggle_and_rendering(self) -> None:
        ta = TextArea(show_line_numbers=True)
        ta.set_value("line 1\nline 2")
        view_with_nums = ta.view()
        self.assertIn("1 │", view_with_nums)
        self.assertIn("2 │", view_with_nums)

        ta.toggle_line_numbers()
        self.assertFalse(ta.show_line_numbers)
        view_without_nums = ta.view()
        self.assertNotIn("│", view_without_nums)

    def test_cursor_rendering_and_blur(self) -> None:
        ta = TextArea()
        ta.set_value("abc")
        # Focused by default - should contain inverted video ANSI sequence
        v_focused = ta.view()
        self.assertIn("\033[7m", v_focused)

        ta.blur()
        self.assertFalse(ta.focused)
        v_blurred = ta.view()
        self.assertNotIn("\033[7m", v_blurred)

        # Keys ignored when blurred
        ta.update(KeyMsg("x"))
        self.assertEqual(ta.value, "abc")

    def test_scrolling_height(self) -> None:
        ta = TextArea(height=3)
        ta.set_value("\n".join(f"line {i}" for i in range(10)))
        # Cursor at line 9, so row_offset must have shifted
        self.assertGreater(ta.row_offset, 0)
        v = ta.view()
        self.assertIn("line 9", v)
        self.assertNotIn("line 0", v)

    def test_char_limit_and_max_lines(self) -> None:
        ta = TextArea(char_limit=5, max_lines=2)
        ta.insert_text("abc")
        ta.insert_text("de")
        # Limit reached
        ta.insert_text("f")
        self.assertEqual(ta.value, "abcde")

        # Max lines constraint
        ta.set_cursor(0, 2)
        ta.update(KeyMsg("enter"))
        self.assertEqual(ta.line_count, 2)
        # Attempting second enter when max_lines=2
        ta.update(KeyMsg("enter"))
        self.assertEqual(ta.line_count, 2)


class TestHelpComponent(unittest.TestCase):
    def test_keybinding_matching(self) -> None:
        kb1 = KeyBinding("q", "quit")
        self.assertTrue(kb1.matches("q"))
        self.assertTrue(kb1.matches(KeyMsg("q")))
        self.assertTrue(kb1.matches(Key("q")))
        self.assertFalse(kb1.matches("x"))

        kb_multi = KeyBinding(["ctrl+c", "esc"], "abort", help_key="esc/ctrl+c")
        self.assertEqual(kb_multi.help_key, "esc/ctrl+c")
        self.assertTrue(kb_multi.matches("esc"))
        self.assertTrue(kb_multi.matches("ctrl+c"))

        kb_disabled = KeyBinding("enter", "submit", enabled=False)
        self.assertFalse(kb_disabled.matches("enter"))

    def test_short_help_rendering(self) -> None:
        bindings = [
            KeyBinding("enter", "select"),
            KeyBinding("q", "quit"),
        ]
        help_comp = Help(bindings, short_separator=" • ")
        v = strip_ansi(help_comp.view())
        self.assertIn("enter select", v)
        self.assertIn("q quit", v)
        self.assertIn("•", v)

    def test_short_help_width_truncation(self) -> None:
        bindings = [
            KeyBinding("a", "action a"),
            KeyBinding("b", "action b"),
            KeyBinding("c", "action c"),
            KeyBinding("d", "action d"),
        ]
        # Very narrow width should drop later bindings
        help_comp = Help(bindings, width=20)
        v = strip_ansi(help_comp.view())
        self.assertIn("action a", v)
        self.assertNotIn("action d", v)

    def test_full_help_multi_column(self) -> None:
        groups = [
            [KeyBinding("ctrl+s", "save file"), KeyBinding("ctrl+q", "quit")],
            [KeyBinding("up", "move up"), KeyBinding("down", "move down")],
        ]
        help_comp = Help(groups, show_all=True)
        v = strip_ansi(help_comp.view())
        self.assertIn("save file", v)
        self.assertIn("move up", v)
        # Check side-by-side columns: multiple bindings on the same line
        lines = v.splitlines()
        self.assertTrue(any("save file" in l and "move up" in l for l in lines))

    def test_help_toggle(self) -> None:
        bindings = [KeyBinding("?", "help")]
        h = Help(bindings, show_all=False)
        self.assertFalse(h.show_all)
        h.toggle()
        self.assertTrue(h.show_all)

    def test_keymap_protocol(self) -> None:
        class SampleKeyMap:
            def short_help(self) -> list[KeyBinding]:
                return [KeyBinding("q", "quit")]

            def full_help(self) -> list[list[KeyBinding]]:
                return [[KeyBinding("q", "quit")], [KeyBinding("?", "help")]]

        h = Help(SampleKeyMap())
        self.assertIn("q quit", strip_ansi(h.view()))
        h.toggle()
        self.assertIn("help", strip_ansi(h.view()))


class TestTimerAndStopwatchComponents(unittest.TestCase):
    def test_timer_initialization_and_properties(self) -> None:
        timer = Timer(timeout=10.0, interval=1.0, auto_start=True)
        cmd = timer.init()
        self.assertIsNotNone(cmd)
        self.assertTrue(timer.running)
        self.assertEqual(timer.timeout, 10.0)
        self.assertAlmostEqual(timer.remaining, 10.0, delta=0.1)
        self.assertAlmostEqual(timer.percent, 0.0, delta=0.05)

    def test_timer_start_stop_toggle_reset(self) -> None:
        timer = Timer(timeout=10.0, auto_start=False)
        self.assertFalse(timer.running)

        cmd = timer.start()
        self.assertIsNotNone(cmd)
        self.assertTrue(timer.running)

        # Toggle to pause
        timer.toggle()
        self.assertFalse(timer.running)

        # Toggle to resume
        cmd = timer.toggle()
        self.assertIsNotNone(cmd)
        self.assertTrue(timer.running)

        # Reset
        timer.reset(timeout=5.0)
        self.assertFalse(timer.running)
        self.assertEqual(timer.remaining, 5.0)
        self.assertEqual(timer.timeout, 5.0)

    def test_timer_tick_and_timeout(self) -> None:
        timer = Timer(timeout=5.0, interval=0.5, tag="test_timer", auto_start=False)
        timer.start()

        # Advance tick
        timer.set_remaining(2.5)
        _, next_cmd = timer.update(TimerTickMsg(tag="test_timer", id=timer._tick_id))
        self.assertIsNotNone(next_cmd)
        self.assertFalse(timer.timedout)

        # Simulate expiration
        timer.set_remaining(0.0)
        timer._target_time = 0.0
        _, timeout_cmd = timer.update(TimerTickMsg(tag="test_timer", id=timer._tick_id))
        self.assertIsNotNone(timeout_cmd)
        self.assertTrue(timer.timedout)
        self.assertFalse(timer.running)

        # Evaluate the timeout command
        msg = timeout_cmd()  # type: ignore[misc]
        self.assertIsInstance(msg, TimerTimeoutMsg)
        self.assertEqual(msg.tag, "test_timer")

    def test_timer_view_formatting(self) -> None:
        timer = Timer(timeout=65.0, interval=1.0, auto_start=False)
        self.assertEqual(timer.view(), "01:05")

        timer_precise = Timer(timeout=5.5, interval=0.1, auto_start=False)
        self.assertEqual(timer_precise.view(), "00:05.5")

        timer_custom = Timer(
            timeout=10.0,
            auto_start=False,
            format_fn=lambda rem: f"{int(rem)}s left",
        )
        self.assertEqual(timer_custom.view(), "10s left")

    def test_stopwatch_lifecycle_and_view(self) -> None:
        sw = Stopwatch(interval=0.1, tag="test_sw", auto_start=False)
        self.assertFalse(sw.running)
        self.assertEqual(sw.elapsed, 0.0)

        cmd = sw.start()
        self.assertIsNotNone(cmd)
        self.assertTrue(sw.running)

        # Set simulated elapsed time
        sw.set_elapsed(125.45)
        self.assertEqual(sw.view(), "02:05.45")

        # Update with tick produces next tick command
        _, next_cmd = sw.update(StopwatchTickMsg(tag="test_sw", id=sw._tick_id))
        self.assertIsNotNone(next_cmd)

        # Stop
        sw.stop()
        self.assertFalse(sw.running)
        self.assertAlmostEqual(sw.elapsed, 125.45, delta=0.1)

        # Reset
        sw.reset()
        self.assertEqual(sw.elapsed, 0.0)
        self.assertEqual(sw.view(), "00:00.00")


if __name__ == "__main__":
    unittest.main()
