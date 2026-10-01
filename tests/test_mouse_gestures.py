"""Unit tests for MouseGestureTracker and double-click detection."""

from __future__ import annotations

import unittest

from espresso import MouseAction, MouseButton, MouseMsg
from espresso.core.mouse import MouseGestureTracker


class TestMouseGestures(unittest.TestCase):
    def test_single_click_passes_through(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        msg = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
        res = tracker.process(msg, current_time=1.0)
        self.assertEqual(res.action, MouseAction.PRESS)
        self.assertEqual(res.button, MouseButton.LEFT)

    def test_double_click_detected(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        m1 = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
        m2 = MouseMsg(x=11, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)

        r1 = tracker.process(m1, current_time=1.0)
        self.assertEqual(r1.action, MouseAction.PRESS)

        r2 = tracker.process(m2, current_time=1.2)
        self.assertEqual(r2.action, MouseAction.DOUBLE_CLICK)
        self.assertEqual(r2.x, 11)
        self.assertEqual(r2.y, 5)
        self.assertEqual(r2.button, MouseButton.LEFT)

    def test_double_click_timeout_exceeded(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        m1 = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
        m2 = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)

        r1 = tracker.process(m1, current_time=1.0)
        self.assertEqual(r1.action, MouseAction.PRESS)

        r2 = tracker.process(m2, current_time=1.4)  # 0.40s later > 0.35s
        self.assertEqual(r2.action, MouseAction.PRESS)

    def test_double_click_distance_exceeded(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        m1 = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
        m2 = MouseMsg(x=13, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)  # dx = 3 > 1

        tracker.process(m1, current_time=1.0)
        r2 = tracker.process(m2, current_time=1.1)
        self.assertEqual(r2.action, MouseAction.PRESS)

    def test_double_click_different_button(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        m1 = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
        m2 = MouseMsg(x=10, y=5, button=MouseButton.RIGHT, action=MouseAction.PRESS)

        tracker.process(m1, current_time=1.0)
        r2 = tracker.process(m2, current_time=1.1)
        self.assertEqual(r2.action, MouseAction.PRESS)
        self.assertEqual(r2.button, MouseButton.RIGHT)

    def test_triple_click_handling(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        m = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)

        r1 = tracker.process(m, current_time=1.0)
        self.assertEqual(r1.action, MouseAction.PRESS)

        r2 = tracker.process(m, current_time=1.1)
        self.assertEqual(r2.action, MouseAction.DOUBLE_CLICK)

        # Third click right after should be PRESS (starting a new potential double click)
        r3 = tracker.process(m, current_time=1.2)
        self.assertEqual(r3.action, MouseAction.PRESS)

    def test_non_press_actions_ignored(self) -> None:
        tracker = MouseGestureTracker(timeout=0.35, max_distance=1)
        m_rel = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.RELEASE)
        m_mot = MouseMsg(x=10, y=5, button=MouseButton.NONE, action=MouseAction.MOTION)

        self.assertEqual(tracker.process(m_rel, current_time=1.0).action, MouseAction.RELEASE)
        self.assertEqual(tracker.process(m_mot, current_time=1.1).action, MouseAction.MOTION)
