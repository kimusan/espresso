"""Unit tests for Crema 2D overlay compositing and ANSI-aware string slicing."""

from __future__ import annotations

import unittest

from espresso.crema import place_overlay, slice_ansi, strip_ansi


class TestSliceAnsi(unittest.TestCase):
    def test_plain_slice(self) -> None:
        text = "Hello, World!"
        # slice 0 to 5 -> "Hello"
        self.assertEqual(slice_ansi(text, 0, 5), "Hello")
        # slice 7 to 12 -> "World"
        self.assertEqual(slice_ansi(text, 7, 12), "World")
        # slice from 7 to end
        self.assertEqual(slice_ansi(text, 7), "World!")

    def test_slice_out_of_bounds(self) -> None:
        text = "Test"
        self.assertEqual(slice_ansi(text, 10, 20), "")
        self.assertEqual(slice_ansi(text, 0, 100), "Test")

    def test_slice_with_ansi_codes(self) -> None:
        # Styled string: "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        text = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        # Visual text: "Red Green" (len 9)
        # Slicing 0 to 3 should return Red with color
        res1 = slice_ansi(text, 0, 3)
        self.assertEqual(strip_ansi(res1), "Red")
        self.assertIn("\x1b[31m", res1)

        # Slicing 4 to 9 should return Green with green color
        res2 = slice_ansi(text, 4, 9)
        self.assertEqual(strip_ansi(res2), "Green")
        self.assertIn("\x1b[32m", res2)

    def test_slice_middle_preserves_active_style(self) -> None:
        # "\x1b[34mBlueberry\x1b[0m"
        text = "\x1b[34mBlueberry\x1b[0m"
        # Visual: "Blueberry" (len 9). Slice 4 to 9 -> "berry"
        res = slice_ansi(text, 4, 9)
        self.assertEqual(strip_ansi(res), "berry")
        # Should carry the blue style from before col 4
        self.assertTrue(res.startswith("\x1b[34m"))

    def test_slice_emoji_boundary_clamping(self) -> None:
        from espresso.crema.width import string_width

        text = "[2] 🏙️ Local"
        # Visual columns: '['(0), '2'(1), ']'(2), ' '(3), '🏙️'(4..5), ' '(6), 'Local'(7..11)
        # Slicing 0..5 (pad=False): 🏙️ spans 4..6 so it cannot fit in 0..5. Sliced text should be '[2] ' (w=4)
        s1 = slice_ansi(text, 0, 5, pad=False)
        self.assertEqual(string_width(s1), 4)
        self.assertEqual(s1, "[2] ")

        # Slicing 0..5 (pad=True): pads the 1 remaining cell with space to reach 5
        s1_pad = slice_ansi(text, 0, 5, pad=True)
        self.assertEqual(string_width(s1_pad), 5)
        self.assertEqual(s1_pad, "[2]  ")

        # Slicing starting at col 5 (straddling 🏙️): col 5 is the second cell of 🏙️.
        # It replaces the straddling cell with space and continues with ' Local'
        s2 = slice_ansi(text, 5)
        self.assertEqual(string_width(s2), 7)
        self.assertEqual(s2, "  Local")



class TestPlaceOverlay(unittest.TestCase):
    def test_basic_overlay_coordinates(self) -> None:
        base = "....\n....\n....\n...."
        overlay = "XX\nXX"
        result = place_overlay(base, overlay, x=1, y=1)
        expected = (
            "....\n"
            ".XX.\n"
            ".XX.\n"
            "...."
        )
        self.assertEqual(result, expected)

    def test_overlay_at_zero_zero(self) -> None:
        base = "....\n...."
        overlay = "A\nB"
        result = place_overlay(base, overlay, x=0, y=0)
        expected = "A...\nB..."
        self.assertEqual(result, expected)

    def test_overlay_centered(self) -> None:
        # base: 6 cols x 4 lines
        base = "......\n......\n......\n......"
        overlay = "XX\nXX"
        # overlay is 2x2. center in 6x4: x = (6-2)//2 = 2, y = (4-2)//2 = 1
        result = place_overlay(base, overlay, center=True)
        expected = (
            "......\n"
            "..XX..\n"
            "..XX..\n"
            "......"
        )
        self.assertEqual(result, expected)

    def test_overlay_dim_backdrop(self) -> None:
        base = "AAAA\nBBBB"
        overlay = "X"
        result = place_overlay(base, overlay, x=1, y=0, dim_backdrop=True)
        # Should include faint ANSI escape \x1b[2m
        self.assertIn("\x1b[2m", result)
        # Stripped should match replacing position
        self.assertEqual(strip_ansi(result), "AXAA\nBBBB")

    def test_overlay_clamping(self) -> None:
        base = "..\n.."
        overlay = "YYYY\nYYYY\nYYYY"
        # Placing at 0, 0 should truncate to fit base lines
        result = place_overlay(base, overlay, x=0, y=0)
        lines = result.split("\n")
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(strip_ansi(line), "YY")


if __name__ == "__main__":
    unittest.main()
