"""Unit tests for keys and ANSI escape sequence parsing."""

from __future__ import annotations

import unittest

from espresso.core.keys import Key, KeyMsg, parse_keys


class TestKeys(unittest.TestCase):
    def test_key_string_comparisons(self) -> None:
        k = KeyMsg("q")
        self.assertEqual(k, "q")
        self.assertEqual(k.key, "q")
        self.assertEqual(k.key.char, "q")

        enter_msg = KeyMsg("enter")
        self.assertEqual(enter_msg, "enter")
        self.assertEqual(enter_msg.key, "enter")
        self.assertIsNone(enter_msg.key.char)

    def test_parse_printable_ascii(self) -> None:
        keys = list(parse_keys("hello"))
        self.assertEqual(len(keys), 5)
        chars = [k.key.name for k in keys]
        self.assertEqual(chars, ["h", "e", "l", "l", "o"])

    def test_parse_control_characters(self) -> None:
        # Ctrl+C is ASCII 3, Enter is \r (13) or \n (10), Tab is \t (9)
        keys = list(parse_keys("\x03\r\t"))
        self.assertEqual([k.key.name for k in keys], ["ctrl+c", "enter", "tab"])
        self.assertTrue(keys[0].key.ctrl)

    def test_parse_arrows(self) -> None:
        # ANSI CSI arrow sequences: \x1b[A, \x1b[B, \x1b[C, \x1b[D
        keys = list(parse_keys("\x1b[A\x1b[B\x1b[C\x1b[D"))
        self.assertEqual([k.key.name for k in keys], ["up", "down", "right", "left"])

    def test_parse_modified_arrows(self) -> None:
        # Shift+Up (\x1b[1;2A), Ctrl+Down (\x1b[1;5B)
        keys = list(parse_keys("\x1b[1;2A\x1b[1;5B"))
        self.assertEqual([k.key.name for k in keys], ["shift+up", "ctrl+down"])
        self.assertTrue(keys[0].key.shift)
        self.assertTrue(keys[1].key.ctrl)

    def test_parse_alt_keys(self) -> None:
        # Alt+A is \x1ba
        keys = list(parse_keys("\x1ba"))
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0].key.name, "alt+a")
        self.assertTrue(keys[0].key.alt)

    def test_parse_solitary_escape(self) -> None:
        keys = list(parse_keys("\x1b"))
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0].key.name, "esc")

    def test_parse_function_keys(self) -> None:
        # F1 (\x1bOP) and F5 (\x1b[15~)
        keys = list(parse_keys("\x1bOP\x1b[15~"))
        self.assertEqual([k.key.name for k in keys], ["f1", "f5"])


if __name__ == "__main__":
    unittest.main()
