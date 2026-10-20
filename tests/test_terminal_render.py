"""Unit tests verifying raw mode carriage return formatting and non-blocking recovery."""

from __future__ import annotations

import io
import unittest

from espresso import Model, Msg, Program
from espresso.core.terminal import TerminalDriver


class SimpleModel:
    def init(self):
        return None

    def update(self, msg: Msg):
        return self, None

    def view(self) -> str:
        return "Line 1\nLine 2\nLine 3"


class MockBlockingStream(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.should_raise_once = True

    def write(self, s: str) -> int:
        if self.should_raise_once:
            self.should_raise_once = False
            raise BlockingIOError("[Errno 11] Resource temporarily unavailable")
        return super().write(s)


class TestTerminalRenderFormatting(unittest.TestCase):
    def test_inline_render_uses_carriage_returns(self) -> None:
        out = io.StringIO()
        p = Program(SimpleModel(), alt_screen=False, output_stream=out)
        p._render(p.model.view())
        output = out.getvalue()

        # Must contain \r\n to prevent diagonal staircase skew in raw mode
        self.assertIn("\r\n", output)
        self.assertIn("\r", output)

    def test_alt_screen_render_uses_carriage_returns(self) -> None:
        out = io.StringIO()
        p = Program(SimpleModel(), alt_screen=True, output_stream=out)
        p._render(p.model.view())
        output = out.getvalue()

        # In alt screen, lines are placed with row;col coordinate jump and cleared before line text
        self.assertIn("\x1b[1;1H", output)
        self.assertIn("\x1b[2KLine 1", output)
        self.assertIn("\x1b[2;1H", output)
        self.assertIn("\x1b[2KLine 2", output)


    def test_synchronized_update_double_buffering(self) -> None:
        out = io.StringIO()
        p = Program(SimpleModel(), alt_screen=True, output_stream=out)
        p._render(p.model.view())
        output = out.getvalue()

        # Output must be wrapped in DEC Mode 2026 synchronized update delimiters
        self.assertTrue(output.startswith("\x1b[?2026h"))
        self.assertTrue(output.endswith("\x1b[?2026l"))

    def test_line_diffing_overwrites_inplace_without_blanking(self) -> None:
        out = io.StringIO()
        p = Program(SimpleModel(), alt_screen=True, output_stream=out)
        # Frame 1
        p._render("Line 1\nLine 2\nLine 3")
        # Frame 2 with change on line 2
        out.truncate(0)
        out.seek(0)
        p._render("Line 1\nLine 2 Updated\nLine 3")
        output = out.getvalue()

        # Must overwrite line 2 in-place without blanking with \x1b[2K before drawing
        self.assertIn("\x1b[2;1HLine 2 Updated\x1b[K", output)
        self.assertNotIn("\x1b[2;1H\x1b[2K", output)

    def test_blocking_io_recovery(self) -> None:
        out = MockBlockingStream()
        p = Program(SimpleModel(), output_stream=out)
        # Should catch BlockingIOError gracefully and not crash
        p._render(p.model.view())
        self.assertIn("Line 1", out.getvalue())


if __name__ == "__main__":
    unittest.main()
