"""Unit tests for Confetti 2D particle physics emitter."""

from __future__ import annotations

import unittest

from espresso.beans.confetti import Confetti, ConfettiMode, ConfettiTickMsg
from espresso.crema import strip_ansi


class TestConfetti(unittest.TestCase):
    def test_initial_state(self) -> None:
        c = Confetti(width=60, height=20)
        self.assertFalse(c.is_active)
        self.assertEqual(len(c.particles), 0)
        self.assertIsNone(c.init())

    def test_fire_burst(self) -> None:
        c = Confetti(width=60, height=20)
        cmd = c.fire(count=30, mode=ConfettiMode.BURST, origin=(30, 10))
        self.assertTrue(c.is_active)
        self.assertEqual(len(c.particles), 30)
        self.assertIsNotNone(cmd)

        # Check particles initialized around origin
        for p in c.particles:
            self.assertEqual(p.x, 30)
            self.assertEqual(p.y, 10)
            self.assertGreater(p.life, 0)

    def test_fire_cannon_and_rain(self) -> None:
        c = Confetti(width=60, height=20)
        c.fire(count=20, mode=ConfettiMode.CANNON)
        self.assertEqual(len(c.particles), 20)

        c.clear()
        self.assertFalse(c.is_active)

        c.fire(count=25, mode=ConfettiMode.RAIN)
        self.assertEqual(len(c.particles), 25)
        for p in c.particles:
            self.assertLessEqual(p.y, 3.0)

    def test_particle_physics_advance_and_expiration(self) -> None:
        c = Confetti(width=60, height=20, fps=30.0, gravity=20.0)
        c.fire(count=10, mode=ConfettiMode.BURST)

        # Step physics until all particles expire
        ticks = 0
        while c.is_active and ticks < 200:
            c, cmd = c.update(ConfettiTickMsg(tag=c.tag, active_particles=len(c.particles)))
            ticks += 1

        self.assertFalse(c.is_active, "All particles should eventually expire")
        self.assertIsNone(cmd)

    def test_overlay_rendering(self) -> None:
        c = Confetti(width=40, height=10)
        bg = "Hello World\nLine 2 of card\nFooter Line"
        # When no particles, overlay is identical to background
        res1 = c.overlay(bg)
        self.assertEqual(res1, bg)

        # Fire burst at col 0, row 0
        c.fire(count=5, mode=ConfettiMode.BURST, origin=(0, 0))
        res2 = c.overlay(bg)
        self.assertEqual(len(res2.split("\n")), len(bg.split("\n")))

    def test_standalone_view(self) -> None:
        c = Confetti(width=30, height=8)
        c.fire(count=10, mode=ConfettiMode.BURST, origin=(15, 4))
        v = c.view()
        lines = v.split("\n")
        self.assertEqual(len(lines), 8)


    def test_overlay_preserves_multi_cell_emoji_width(self) -> None:
        from espresso.beans.confetti import Particle
        from espresso.crema.width import string_width

        c = Confetti(width=40, height=5)
        line = "│ [1] 🏠 Home  │ [2] 🏙️ Local  │"
        orig_w = string_width(line)

        # 🏙️ is at visual column 21 (spanning 21 and 22)
        # Particle on first cell of emoji
        c.particles = [Particle(21.0, 0.0, 0.0, 0.0, "*", "#FF007F", 10, 10)]
        res_col21 = c.overlay(line)
        self.assertEqual(string_width(res_col21), orig_w)
        self.assertIn("*", strip_ansi(res_col21))
        # Ensure right border didn't shift
        self.assertTrue(strip_ansi(res_col21).endswith("│"))

        # Particle on second cell of emoji
        c.particles = [Particle(22.0, 0.0, 0.0, 0.0, "*", "#00E5FF", 10, 10)]
        res_col22 = c.overlay(line)
        self.assertEqual(string_width(res_col22), orig_w)
        self.assertIn("*", strip_ansi(res_col22))
        self.assertTrue(strip_ansi(res_col22).endswith("│"))

        # Particles on both cells of emoji
        c.particles = [
            Particle(21.0, 0.0, 0.0, 0.0, "*", "#FF007F", 10, 10),
            Particle(22.0, 0.0, 0.0, 0.0, "+", "#00E5FF", 10, 10),
        ]
        res_both = c.overlay(line)
        self.assertEqual(string_width(res_both), orig_w)
        self.assertIn("*+", strip_ansi(res_both))
        self.assertTrue(strip_ansi(res_both).endswith("│"))

        # Once particles are gone, emoji is completely restored
        c.clear()
        self.assertEqual(c.overlay(line), line)

    def test_overlay_preserves_ansi_styling(self) -> None:
        from espresso.beans.confetti import Particle
        c = Confetti(width=40, height=5)
        line = "\x1b[32mGreenStart \x1b[1mBoldMid\x1b[0m \x1b[34mBlueEnd\x1b[0m"
        # Particle in middle of BoldMid (col 13)
        c.particles = [Particle(13.0, 0.0, 0.0, 0.0, "*", "#FF007F", 10, 10)]
        res = c.overlay(line)
        # Should contain particle and BlueEnd should still have blue style
        self.assertIn("*", strip_ansi(res))
        self.assertIn("\x1b[34m", res)

    def test_overlay_beyond_line_width(self) -> None:
        from espresso.beans.confetti import Particle
        from espresso.crema.width import string_width

        c = Confetti(width=40, height=5)
        line = "Short"
        c.particles = [Particle(10.0, 0.0, 0.0, 0.0, "*", "#FF007F", 10, 10)]
        res = c.overlay(line)
        self.assertEqual(string_width(res), 11)
        self.assertEqual(strip_ansi(res), "Short     *")


if __name__ == "__main__":
    unittest.main()
