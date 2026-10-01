"""Unit tests for Spring and SpringValue physics animation engine."""

from __future__ import annotations

import unittest

from espresso.beans.spring import Spring, SpringTickMsg, SpringValue
from espresso.crema import strip_ansi


class TestSpringValue(unittest.TestCase):
    def test_initial_state(self) -> None:
        sv = SpringValue(value=0.0, target=100.0)
        self.assertEqual(sv.value, 0.0)
        self.assertEqual(sv.target, 100.0)
        self.assertEqual(sv.velocity, 0.0)
        self.assertFalse(sv.is_settled)

    def test_underdamped_settlement(self) -> None:
        # Underdamped oscillator should approach target and settle
        sv = SpringValue(value=0.0, target=50.0, stiffness=150.0, damping=0.6)
        dt = 0.016  # ~60fps

        # Step forward for 2 seconds (125 steps)
        overshot = False
        for _ in range(150):
            val, vel = sv.update(dt)
            if val > 50.0:
                overshot = True
            if sv.is_settled:
                break

        self.assertTrue(overshot, "Underdamped spring should exhibit overshoot")
        self.assertTrue(sv.is_settled)
        self.assertAlmostEqual(sv.value, 50.0, places=2)
        self.assertEqual(sv.velocity, 0.0)

    def test_critically_damped(self) -> None:
        sv = SpringValue(value=0.0, target=50.0, stiffness=100.0, damping=1.0)
        dt = 0.02
        for _ in range(150):
            sv.update(dt)
            if sv.is_settled:
                break
        self.assertTrue(sv.is_settled)
        self.assertAlmostEqual(sv.value, 50.0, places=2)

    def test_overdamped(self) -> None:
        sv = SpringValue(value=0.0, target=50.0, stiffness=100.0, damping=1.8)
        dt = 0.02
        for _ in range(250):
            sv.update(dt)
            if sv.is_settled:
                break
        self.assertTrue(sv.is_settled)
        self.assertAlmostEqual(sv.value, 50.0, places=2)

    def test_snap_to(self) -> None:
        sv = SpringValue(value=10.0, target=50.0)
        sv.velocity = 25.0
        sv.snap_to(80.0)
        self.assertEqual(sv.value, 80.0)
        self.assertEqual(sv.target, 80.0)
        self.assertEqual(sv.velocity, 0.0)
        self.assertTrue(sv.is_settled)


class TestSpringModel(unittest.TestCase):
    def test_spring_widget_view(self) -> None:
        sp = Spring(value=25.0, target=75.0, width=40, label="Gauge")
        v = strip_ansi(sp.view())
        self.assertIn("Gauge", v)
        self.assertIn("●", v)
        self.assertIn("▼", v)
        self.assertIn("25.0", v)
        self.assertIn("75.0", v)

    def test_set_target_and_ticks(self) -> None:
        sp = Spring(value=0.0, target=0.0, width=30)
        self.assertTrue(sp.is_settled)

        # Set target returns a tick command
        cmd = sp.set_target(100.0)
        self.assertIsNotNone(cmd)
        self.assertFalse(sp.is_settled)

        # Process a tick message
        sp, next_cmd = sp.update(SpringTickMsg(tag=sp.tag, value=sp.value, velocity=sp.velocity, is_settled=False))
        self.assertGreater(sp.value, 0.0)
        self.assertIsNotNone(next_cmd)


if __name__ == "__main__":
    unittest.main()
