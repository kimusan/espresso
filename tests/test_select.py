import unittest
from espresso.beans.select import Select, SelectChangeMsg
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestSelect(unittest.TestCase):
    def setUp(self):
        self.options = [
            ("public", "🌐 Public"),
            ("unlisted", "🔑 Unlisted"),
            ("private", "👥 Followers-only"),
            ("direct", "🔒 Direct"),
        ]

    def test_initial_state(self):
        sel = Select(options=self.options, value="public", id="vis_sel", width=25)
        self.assertEqual(sel.selected_value, "public")
        self.assertEqual(sel.selected_label, "🌐 Public")
        self.assertFalse(sel.is_open)
        self.assertIn("🌐 Public", sel.view())
        self.assertIn("▼", sel.view())

    def test_open_and_close(self):
        sel = Select(options=self.options)
        # Open with enter
        sel, cmd = sel.update(KeyMsg(key="enter"))
        self.assertTrue(sel.is_open)
        self.assertIsNone(cmd)
        self.assertIn("▲", sel.view())
        self.assertIn("🔑 Unlisted", sel.view())

        # Close with esc
        sel, cmd = sel.update(KeyMsg(key="esc"))
        self.assertFalse(sel.is_open)

    def test_navigation_and_selection(self):
        sel = Select(options=self.options, value="public", id="vis")
        sel.open()
        self.assertEqual(sel.cursor, 0)

        # Move down
        sel, _ = sel.update(KeyMsg(key="down"))
        self.assertEqual(sel.cursor, 1)

        # Move down again
        sel, _ = sel.update(KeyMsg(key="j"))
        self.assertEqual(sel.cursor, 2)

        # Select currently focused item ("private")
        sel, cmd = sel.update(KeyMsg(key="enter"))
        self.assertFalse(sel.is_open)
        self.assertEqual(sel.selected_value, "private")
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SelectChangeMsg)
        self.assertEqual(msg.id, "vis")
        self.assertEqual(msg.value, "private")
        self.assertEqual(msg.label, "👥 Followers-only")

    def test_direct_closed_navigation(self):
        sel = Select(options=self.options, value="unlisted", id="vis")
        # When closed, up moves to previous option directly
        sel, cmd = sel.update(KeyMsg(key="up"))
        self.assertEqual(sel.selected_value, "public")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd().value, "public")

    def test_mouse_interactions(self):
        sel = Select(options=self.options, value="public")
        # Click when closed opens dropdown
        sel, _ = sel.update(MouseMsg(x=5, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertTrue(sel.is_open)

        # Click on row 2 in dropdown (index 1 = "unlisted")
        sel, cmd = sel.update(MouseMsg(x=5, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertFalse(sel.is_open)
        self.assertEqual(sel.selected_value, "unlisted")
        self.assertIsNotNone(cmd)


if __name__ == "__main__":
    unittest.main()
