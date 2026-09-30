"""Unit tests for Marquee component."""

from __future__ import annotations

import unittest

from espresso.beans.marquee import Marquee, MarqueeMode, MarqueeTickMsg
from espresso.crema import Style, string_width, strip_ansi


class TestMarquee(unittest.TestCase):
    def test_text_fits_width(self) -> None:
        mq = Marquee("Short text", width=20, loop_if_fits=False)
        v = strip_ansi(mq.view())
        self.assertEqual(string_width(v), 20)
        self.assertEqual(v.strip(), "Short text")

        # Step does not change offset if text fits and loop_if_fits is False
        mq.step()
        self.assertEqual(mq.offset, 0)

    def test_loop_mode_stepping(self) -> None:
        text = "Breaking News: Espresso 2.0 Released!"
        mq = Marquee(text, width=15, mode=MarqueeMode.LOOP, separator=" • ")
        self.assertEqual(mq.offset, 0)
        v0 = strip_ansi(mq.view())
        self.assertEqual(string_width(v0), 15)
        self.assertTrue(v0.startswith("Breaking News"))

        # Step advances offset
        mq.step()
        self.assertEqual(mq.offset, 1)
        v1 = strip_ansi(mq.view())
        self.assertEqual(string_width(v1), 15)
        self.assertTrue(v1.startswith("reaking News"))

    def test_bounce_mode(self) -> None:
        text = "Hello World"  # length 11
        mq = Marquee(text, width=8, mode=MarqueeMode.BOUNCE, pause_frames=1)
        # Max offset = 11 - 8 = 3

        mq.step()  # offset 1
        self.assertEqual(mq.offset, 1)
        mq.step()  # offset 2
        self.assertEqual(mq.offset, 2)
        mq.step()  # offset 3 (end reached, reverses direction, pauses)
        self.assertEqual(mq.offset, 3)
        self.assertEqual(mq.direction, -1)

        # Pause frame
        mq.step()
        self.assertEqual(mq.offset, 3)

        # Starts moving backward
        mq.step()
        self.assertEqual(mq.offset, 2)

    def test_update_tick_message(self) -> None:
        mq = Marquee("A long title that scrolls continuously", width=10)
        self.assertEqual(mq.offset, 0)

        mq, cmd = mq.update(MarqueeTickMsg(tag="marquee"))
        self.assertEqual(mq.offset, 1)
        self.assertIsNotNone(cmd)

    def test_styled_text_preserves_width(self) -> None:
        styled = Style().bold(True).foreground("#FF007F").render("Stylish Scrolling Header")
        mq = Marquee(styled, width=12)
        v = mq.view()
        self.assertEqual(string_width(v), 12)


if __name__ == "__main__":
    unittest.main()
