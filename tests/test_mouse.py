"""Unit tests for mouse event decoding."""

from __future__ import annotations

import unittest

from espresso import MouseAction, MouseButton, MouseMsg
from espresso.core.keys import parse_keys
from espresso.core.mouse import parse_sgr_mouse


class TestMouseParser(unittest.TestCase):
    def test_parse_left_click_press(self) -> None:
        # \x1b[<0;15;8M -> Left click press at col 15, row 8 (1-indexed) -> (14, 7)
        msg, consumed = parse_sgr_mouse("\x1b[<0;15;8M")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.button, MouseButton.LEFT)
        self.assertEqual(msg.action, MouseAction.PRESS)
        self.assertEqual(msg.x, 14)
        self.assertEqual(msg.y, 7)
        self.assertEqual(consumed, len("\x1b[<0;15;8M"))

    def test_parse_left_click_release(self) -> None:
        # \x1b[<0;15;8m -> Release
        msg, consumed = parse_sgr_mouse("\x1b[<0;15;8m")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.button, MouseButton.LEFT)
        self.assertEqual(msg.action, MouseAction.RELEASE)

    def test_parse_wheel_events(self) -> None:
        # Wheel up: 64
        msg_up, _ = parse_sgr_mouse("\x1b[<64;10;5M")
        self.assertIsNotNone(msg_up)
        self.assertEqual(msg_up.button, MouseButton.WHEEL_UP)

        # Wheel down: 65
        msg_down, _ = parse_sgr_mouse("\x1b[<65;10;5M")
        self.assertIsNotNone(msg_down)
        self.assertEqual(msg_down.button, MouseButton.WHEEL_DOWN)

    def test_parse_keys_stream_with_mouse(self) -> None:
        raw_stream = "a\x1b[<0;10;10Mq"
        events = list(parse_keys(raw_stream))
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0], "a")
        self.assertIsInstance(events[1], MouseMsg)
        self.assertEqual(events[1].button, MouseButton.LEFT)
        self.assertEqual(events[2], "q")


if __name__ == "__main__":
    unittest.main()
