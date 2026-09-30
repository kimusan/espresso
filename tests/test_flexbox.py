"""Unit tests for the Stickers-inspired FlexBox responsive grid layout engine."""

from __future__ import annotations

import unittest

from espresso.crema import Cell, FlexBox, Row, Style, string_width
from espresso.crema.flexbox import distribute_space


class TestFlexBox(unittest.TestCase):
    def test_distribute_space_proportions(self) -> None:
        # 100 space across ratios 1, 2, 1
        items = [(None, 0, 1), (None, 0, 2), (None, 0, 1)]
        res = distribute_space(100, items)
        self.assertEqual(res, [25, 50, 25])
        self.assertEqual(sum(res), 100)

        # 101 space across ratios 1, 2, 1 -> remainder 1 goes to highest fractional
        res101 = distribute_space(101, items)
        self.assertEqual(sum(res101), 101)

    def test_distribute_space_with_fixed_and_min(self) -> None:
        # Fixed 20, and two flex items with 1:1 ratio over 100 total
        items = [(20, 0, 1), (None, 0, 1), (None, 0, 1)]
        res = distribute_space(100, items)
        self.assertEqual(res, [20, 40, 40])
        self.assertEqual(sum(res), 100)

        # Min constraint: min 45 on flex item
        items_min = [(None, 45, 1), (None, 0, 1)]
        res_min = distribute_space(80, items_min)
        self.assertGreaterEqual(res_min[0], 45)
        self.assertEqual(sum(res_min), 80)

    def test_cell_static_and_dynamic_render(self) -> None:
        c1 = Cell(content="Hello")
        rendered1 = c1.render(10, 3)
        lines1 = rendered1.splitlines()
        self.assertEqual(len(lines1), 3)
        self.assertEqual(string_width(lines1[0]), 10)
        self.assertTrue(lines1[0].startswith("Hello"))

        # Dynamic callback
        c2 = Cell(content=lambda w, h: f"Box:{w}x{h}")
        rendered2 = c2.render(12, 2)
        lines2 = rendered2.splitlines()
        self.assertEqual(len(lines2), 2)
        self.assertEqual(string_width(lines2[0]), 12)
        self.assertTrue(lines2[0].startswith("Box:12x2"))

    def test_flexbox_2x2_grid_exact_dimensions(self) -> None:
        fb = FlexBox(width=60, height=20)

        # Row 1: Header (fixed height 2) with 2 cells (1:1)
        r1 = fb.new_row(height=2)
        r1.new_cell("Top Left", ratio_x=1)
        r1.new_cell("Top Right", ratio_x=1)

        # Row 2: Main area (flexible height 18) with 3 cells (1:2:1)
        r2 = fb.new_row(ratio_y=1)
        r2.new_cell("Nav", ratio_x=1)
        r2.new_cell(lambda w, h: f"Main Content Area {w}x{h}", ratio_x=2)
        r2.new_cell("Aside", ratio_x=1)

        rendered = fb.render()
        lines = rendered.splitlines()

        # Check total height
        self.assertEqual(len(lines), 20)

        # Check total width on all lines
        for i, line in enumerate(lines):
            self.assertEqual(
                string_width(line),
                60,
                f"Line {i} visual width is {string_width(line)}, expected 60",
            )

    def test_flexbox_resize(self) -> None:
        fb = FlexBox(width=40, height=10)
        row = fb.new_row()
        row.new_cell("Left", ratio_x=1)
        row.new_cell("Right", ratio_x=1)

        lines1 = fb.render().splitlines()
        self.assertEqual(len(lines1), 10)
        self.assertEqual(string_width(lines1[0]), 40)

        # Resize
        fb.set_dimensions(80, 25)
        lines2 = fb.render().splitlines()
        self.assertEqual(len(lines2), 25)
        self.assertEqual(string_width(lines2[0]), 80)


if __name__ == "__main__":
    unittest.main()
