"""Unit tests for BarChart bean."""

from __future__ import annotations

import unittest

from espresso.beans.bar_chart import BarChart, BarItem, BarOrientation
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestBarChart(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            BarItem(label="CPU", value=45.0, formatter=lambda v: f"{v:.0f}%"),
            BarItem(label="Memory", value=80.0, formatter=lambda v: f"{v:.0f}%"),
            BarItem(label="Disk", value=25.0, formatter=lambda v: f"{v:.0f}%"),
        ]
        self.chart = BarChart(items=self.items, title="System Metrics", orientation=BarOrientation.HORIZONTAL)

    def test_initial_state_and_max(self) -> None:
        self.assertEqual(len(self.chart.items), 3)
        self.assertEqual(self.chart.cursor, 0)
        self.assertEqual(self.chart._calc_max(), 80.0)

    def test_horizontal_navigation(self) -> None:
        self.chart.update(KeyMsg("down"))
        self.assertEqual(self.chart.cursor, 1)

        self.chart.update(KeyMsg("down"))
        self.assertEqual(self.chart.cursor, 2)

        self.chart.update(KeyMsg("up"))
        self.assertEqual(self.chart.cursor, 1)

    def test_vertical_navigation(self) -> None:
        v_chart = BarChart(items=self.items, orientation=BarOrientation.VERTICAL)
        v_chart.update(KeyMsg("right"))
        self.assertEqual(v_chart.cursor, 1)

        v_chart.update(KeyMsg("left"))
        self.assertEqual(v_chart.cursor, 0)

    def test_mouse_click_selection(self) -> None:
        self.chart.set_offset(0, 0)
        # Inside border, row 0 is y=1, row 1 is y=2
        click_msg = MouseMsg(x=10, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS)
        self.chart.update(click_msg)
        self.assertEqual(self.chart.cursor, 1)

    def test_horizontal_view_rendering(self) -> None:
        view_str = self.chart.view()
        self.assertIn("System Metrics", view_str)
        self.assertIn("CPU", view_str)
        self.assertIn("45%", view_str)
        self.assertIn("Memory", view_str)
        self.assertIn("80%", view_str)

    def test_vertical_view_rendering(self) -> None:
        v_chart = BarChart(items=self.items, orientation=BarOrientation.VERTICAL)
        v_view = v_chart.view()
        self.assertIn("CPU", v_view)
        self.assertIn("Disk", v_view)
