"""Unit tests for the release helper script."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

# Import release helper functions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from release import calculate_next_version, get_current_version


class TestReleaseScript(unittest.TestCase):
    def test_calculate_next_version_patch(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "patch"), "0.2.1")
        self.assertEqual(calculate_next_version("1.9.9", "patch"), "1.9.10")

    def test_calculate_next_version_minor(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "minor"), "0.3.0")
        self.assertEqual(calculate_next_version("0.2.5", "minor"), "0.3.0")

    def test_calculate_next_version_major(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "major"), "1.0.0")
        self.assertEqual(calculate_next_version("1.4.2", "major"), "2.0.0")

    def test_calculate_next_version_explicit(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "0.5.0"), "0.5.0")
        self.assertEqual(calculate_next_version("0.2.0", "1.0.0-rc1"), "1.0.0-rc1")

    def test_get_current_version(self) -> None:
        ver = get_current_version()
        self.assertRegex(ver, r"^\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
