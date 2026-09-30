"""Unit tests for Sparkline component."""

from __future__ import annotations

import unittest

from espresso.beans.sparkline import Sparkline, SparklineMode, SparklineTickMsg
from espresso.crema import strip_ansi


class TestSparkline(unittest.TestCase):
    def test_push_and_data_streaming(self) -> None:
        sp = Sparkline(width=20, mode=SparklineMode.BLOCK)
        cap = sp.capacity

        for i in range(cap + 10):
            sp.push(float(i))

        # Must not exceed capacity
        self.assertEqual(len(sp.data), cap)
        self.assertEqual(sp.current_value, cap + 9)
        self.assertEqual(sp.trend_glyph, "↗")

    def test_trend_glyph_directions(self) -> None:
        sp = Sparkline()
        sp.push(10)
        sp.push(20)
        self.assertEqual(sp.trend_glyph, "↗")

        sp.push(5)
        self.assertEqual(sp.trend_glyph, "↘")

        sp.push(5)
        self.assertEqual(sp.trend_glyph, "→")

    def test_block_rendering(self) -> None:
        sp = Sparkline(data=[0, 25, 50, 75, 100], width=20, mode=SparklineMode.BLOCK, label="CPU")
        v = strip_ansi(sp.view())
        self.assertIn("CPU", v)
        self.assertIn("100.0", v)
        self.assertIn("█", v)

    def test_braille_rendering(self) -> None:
        data = [10, 20, 30, 40, 50, 40, 30, 20, 10]
        sp = Sparkline(data=data, width=25, height=2, mode=SparklineMode.BRAILLE, label="RAM")
        v = strip_ansi(sp.view())
        lines = v.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("RAM", v)
        # Check that braille characters were rendered (U+2800..U+28FF)
        has_braille = any(any(0x2800 <= ord(c) <= 0x28FF for c in line) for line in lines)
        self.assertTrue(has_braille)

    def test_multi_row_block_height(self) -> None:
        sp = Sparkline(data=[10, 50, 90], width=20, height=3, mode=SparklineMode.BLOCK)
        lines = sp.view().split("\n")
        self.assertEqual(len(lines), 3)

    def test_fixed_bounds(self) -> None:
        sp = Sparkline(data=[50], min_val=0, max_val=100, width=20, mode=SparklineMode.BLOCK)
        self.assertEqual(sp.min_val, 0)
        self.assertEqual(sp.max_val, 100)


if __name__ == "__main__":
    unittest.main()
