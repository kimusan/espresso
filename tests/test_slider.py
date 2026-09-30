"""Unit tests for Slider and RangeSlider components."""

from __future__ import annotations

import unittest

from espresso.beans.slider import (
    RangeSlider,
    RangeSliderChangeMsg,
    Slider,
    SliderChangeMsg,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import strip_ansi


class TestSlider(unittest.TestCase):
    def test_initial_values_and_percent(self) -> None:
        s = Slider(min_val=0, max_val=100, value=50, width=20, label="Vol")
        self.assertEqual(s.value, 50)
        self.assertAlmostEqual(s.percent, 0.5)

        v = strip_ansi(s.view())
        self.assertIn("Vol", v)
        self.assertIn("50%", v)
        self.assertIn("●", v)

    def test_keyboard_navigation(self) -> None:
        s = Slider(min_val=0, max_val=10, value=5, step=1)

        # Right key +1
        s, cmd = s.update(KeyMsg("right"))
        self.assertEqual(s.value, 6)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SliderChangeMsg)
        self.assertEqual(msg.value, 6)

        # Left key -1
        s, _ = s.update(KeyMsg("left"))
        self.assertEqual(s.value, 5)

        # PageUp +5
        s, _ = s.update(KeyMsg("pageup"))
        self.assertEqual(s.value, 10)

        # Home to 0
        s, _ = s.update(KeyMsg("home"))
        self.assertEqual(s.value, 0)

        # End to 10
        s, _ = s.update(KeyMsg("end"))
        self.assertEqual(s.value, 10)

    def test_mouse_click_and_drag(self) -> None:
        s = Slider(min_val=0, max_val=100, value=0, width=25)
        label_w, track_w = s._track_layout()

        # Click at 50% along the track
        click_x = label_w + (track_w // 2)
        s, cmd = s.update(MouseMsg(x=click_x, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertTrue(s.is_dragging)
        self.assertAlmostEqual(s.percent, 0.5, delta=0.08)

        # Drag towards end (x = label_w + track_w)
        s, cmd = s.update(MouseMsg(x=label_w + track_w, y=0, button=MouseButton.LEFT, action=MouseAction.MOTION))
        self.assertEqual(s.value, 100)

        # Release mouse
        s, _ = s.update(MouseMsg(x=label_w + track_w, y=0, button=MouseButton.LEFT, action=MouseAction.RELEASE))
        self.assertFalse(s.is_dragging)

    def test_mouse_wheel(self) -> None:
        s = Slider(min_val=0, max_val=10, value=5, step=1)
        s, _ = s.update(MouseMsg(x=5, y=0, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
        self.assertEqual(s.value, 6)

        s, _ = s.update(MouseMsg(x=5, y=0, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertEqual(s.value, 5)


class TestRangeSlider(unittest.TestCase):
    def test_initial_values_and_view(self) -> None:
        rs = RangeSlider(min_val=0, max_val=100, low=25, high=75, width=30)
        self.assertEqual(rs.low, 25)
        self.assertEqual(rs.high, 75)
        self.assertAlmostEqual(rs.percent_low, 0.25)
        self.assertAlmostEqual(rs.percent_high, 0.75)

        v = strip_ansi(rs.view())
        self.assertIn("25 - 75", v)
        self.assertEqual(v.count("●"), 2)

    def test_keyboard_toggle_and_adjust(self) -> None:
        rs = RangeSlider(min_val=0, max_val=100, low=20, high=80, step=5)
        self.assertEqual(rs.active_thumb, "low")

        # Right key increments active thumb (low)
        rs, cmd = rs.update(KeyMsg("right"))
        self.assertEqual(rs.low, 25)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, RangeSliderChangeMsg)
        self.assertEqual(msg.low, 25)

        # Tab switches active thumb to "high"
        rs, _ = rs.update(KeyMsg("tab"))
        self.assertEqual(rs.active_thumb, "high")

        # Right key increments high
        rs, _ = rs.update(KeyMsg("right"))
        self.assertEqual(rs.high, 85)

    def test_mouse_drag_nearest_thumb(self) -> None:
        rs = RangeSlider(min_val=0, max_val=100, low=20, high=80, width=30)
        label_w, track_w = rs._track_layout()

        # Click near high thumb (~80% of track)
        click_high_x = label_w + int(track_w * 0.8)
        rs, cmd = rs.update(MouseMsg(x=click_high_x, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(rs.dragging_thumb, "high")

        # Drag high thumb to 90%
        drag_x = label_w + int(track_w * 0.9)
        rs, cmd = rs.update(MouseMsg(x=drag_x, y=0, button=MouseButton.LEFT, action=MouseAction.MOTION))
        self.assertGreaterEqual(rs.high, 85)

        # Release
        rs, _ = rs.update(MouseMsg(x=drag_x, y=0, button=MouseButton.LEFT, action=MouseAction.RELEASE))
        self.assertIsNone(rs.dragging_thumb)

    def test_multi_slider_row_isolation(self) -> None:
        # Simulate two sliders stacked vertically at row 4 and row 6
        s1 = Slider(min_val=0, max_val=100, value=10, width=30, offset_x=1, offset_y=4)
        s2 = Slider(min_val=0, max_val=100, value=20, width=30, offset_x=1, offset_y=6)

        # Click at screen row 4 (s1's row)
        click_msg = MouseMsg(x=15, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS)
        s1, _ = s1.update(click_msg)
        s2, _ = s2.update(click_msg)

        # Only s1 should be dragging
        self.assertTrue(s1.is_dragging)
        self.assertFalse(s2.is_dragging)

        # Drag at screen row 4
        drag_msg = MouseMsg(x=25, y=4, button=MouseButton.LEFT, action=MouseAction.MOTION)
        s1, _ = s1.update(drag_msg)
        s2, _ = s2.update(drag_msg)

        # s1 changed, s2 stayed at 20
        self.assertNotEqual(s1.value, 10)
        self.assertEqual(s2.value, 20)


if __name__ == "__main__":
    unittest.main()
