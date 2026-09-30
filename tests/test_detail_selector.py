"""Unit tests for DetailSelector component."""

from __future__ import annotations

import unittest

from espresso.beans.detail_selector import DetailItem, DetailSelectMsg, DetailSelector
from espresso.core.keys import KeyMsg
from espresso.crema import strip_ansi


class TestDetailSelector(unittest.TestCase):
    def test_navigation_and_details_sync(self) -> None:
        items = [
            DetailItem(title="feat", tag="FEATURE", details="Introducing new features", metadata={"Scope": "minor"}),
            DetailItem(title="fix", tag="BUGFIX", details="Bug fix for existing behavior", metadata={"Scope": "patch"}),
        ]
        ds = DetailSelector(items=items, prompt="Select commit type:")
        self.assertEqual(ds.cursor, 0)
        self.assertEqual(ds.selected_item.title, "feat")

        v0 = strip_ansi(ds.view())
        self.assertIn("» [1] [FEATURE] feat", v0)
        self.assertIn("Introducing new features", v0)
        self.assertIn("Scope: minor", v0)

        # Move down to 'fix'
        ds, _ = ds.update(KeyMsg("down"))
        self.assertEqual(ds.cursor, 1)
        self.assertEqual(ds.selected_item.title, "fix")

        v1 = strip_ansi(ds.view())
        self.assertIn("» [2] [BUGFIX] fix", v1)
        self.assertIn("Bug fix for existing behavior", v1)
        self.assertIn("Scope: patch", v1)

    def test_submission_and_collapsed_view(self) -> None:
        items = [DetailItem(title="release", tag="DEPLOY", details="Cut release tag")]
        ds = DetailSelector(items=items, collapse_on_select=True)

        ds, cmd = ds.update(KeyMsg("enter"))
        self.assertTrue(ds.is_submitted)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, DetailSelectMsg)
        self.assertEqual(msg.item.title, "release")

        # Collapsed view shows single line summary
        v_done = strip_ansi(ds.view())
        self.assertIn("✔", v_done)
        self.assertIn("release", v_done)
        self.assertIn("[DEPLOY]", v_done)
        # Detailed card is collapsed
        self.assertNotIn("Cut release tag", v_done)


if __name__ == "__main__":
    unittest.main()
