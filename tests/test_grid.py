"""Unit tests for Grid layout engine in Crema."""

from __future__ import annotations

import unittest

from espresso.crema.grid import Grid
from espresso.crema.width import string_width, strip_ansi


class TestGrid(unittest.TestCase):
    def test_columns_empty(self) -> None:
        self.assertEqual(Grid.columns([]), "")

    def test_columns_natural_widths(self) -> None:
        c1 = "A1\nA2"
        c2 = "B111\nB222"
        res = Grid.columns([c1, c2], cols=2, gap=2)
        lines = res.split("\n")
        self.assertEqual(len(lines), 2)
        # c1 has width 2, gap is 2, c2 has width 4 -> total line width is 2 + 2 + 4 = 8
        self.assertEqual(string_width(strip_ansi(lines[0])), 8)
        self.assertTrue(lines[0].startswith("A1  B111"))

    def test_columns_total_width(self) -> None:
        cards = ["Card 1", "Card 2", "Card 3"]
        res = Grid.columns(cards, cols=3, gap=1, total_width=32)
        lines = res.split("\n")
        self.assertTrue(len(lines) >= 1)
        # 32 total width, 2 gaps of 1 -> 30 available -> 10 per column
        for line in lines:
            self.assertEqual(string_width(strip_ansi(line)), 32)

    def test_columns_explicit_widths(self) -> None:
        cards = ["Alpha", "Beta"]
        res = Grid.columns(cards, cols=2, col_widths=[15, 20], gap=1)
        lines = res.split("\n")
        self.assertEqual(string_width(strip_ansi(lines[0])), 15 + 1 + 20)

    def test_auto_fit(self) -> None:
        cards = ["C1", "C2", "C3", "C4"]
        # total_width = 60, min_col_width = 25 -> 2 columns
        res = Grid.auto_fit(cards, total_width=60, min_col_width=25, gap=2)
        lines = res.split("\n")
        # 4 cards in 2 columns = 2 rows
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(string_width(strip_ansi(line)), 60)

    def test_panel(self) -> None:
        panel_str = Grid.panel("Stats", "CPU: 45%\nRAM: 12GB", width=30)
        lines = panel_str.split("\n")
        self.assertTrue(len(lines) >= 3)
        self.assertIn("Stats", lines[0] + lines[1])
        for line in lines:
            self.assertEqual(string_width(strip_ansi(line)), 30)
