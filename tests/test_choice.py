import unittest
from espresso.beans.choice import (
    Checkbox,
    CheckboxToggledMsg,
    RadioChangeMsg,
    RadioSet,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestRadioSet(unittest.TestCase):
    def test_initial_state(self):
        rs = RadioSet(options=["Option A", "Option B", "Option C"], selected_index=1, id="r1")
        self.assertEqual(rs.selected_index, 1)
        self.assertEqual(rs.selected_value, "Option B")
        self.assertIn("(•)", rs.view())
        self.assertIn("Option B", rs.view())

    def test_keyboard_navigation(self):
        rs = RadioSet(options=[("a", "Choice A"), ("b", "Choice B"), ("c", "Choice C")], id="r_test")
        self.assertEqual(rs.selected_index, 0)

        # Down arrow
        rs, cmd = rs.update(KeyMsg(key="down"))
        self.assertEqual(rs.selected_index, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, RadioChangeMsg)
        self.assertEqual(msg.id, "r_test")
        self.assertEqual(msg.index, 1)
        self.assertEqual(msg.value, "b")

        # Number key direct jump
        rs, cmd = rs.update(KeyMsg(key="3"))
        self.assertEqual(rs.selected_index, 2)
        self.assertEqual(cmd().value, "c")

    def test_mouse_select(self):
        rs = RadioSet(options=["Alpha", "Beta", "Gamma"], id="r_m")
        rs, cmd = rs.update(MouseMsg(x=2, y=1, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(rs.selected_index, 1)
        self.assertEqual(cmd().value, "Beta")


class TestCheckbox(unittest.TestCase):
    def test_initial_state(self):
        cb = Checkbox(label="Enable image preview", checked=False, id="cb1")
        self.assertFalse(cb.checked)
        self.assertIn("[ ]", cb.view())
        self.assertIn("Enable image preview", cb.view())

    def test_toggle(self):
        cb = Checkbox(label="Agree", checked=False, id="cb_agree")
        cb, cmd = cb.update(KeyMsg(key="enter"))
        self.assertTrue(cb.checked)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, CheckboxToggledMsg)
        self.assertEqual(msg.id, "cb_agree")
        self.assertTrue(msg.checked)
        self.assertIn("[✓]", cb.view())

        # Space toggles off
        cb, cmd = cb.update(KeyMsg(key=" "))
        self.assertFalse(cb.checked)
        self.assertFalse(cmd().checked)

    def test_mouse_toggle(self):
        cb = Checkbox(label="Agree", checked=False)
        cb, cmd = cb.update(MouseMsg(x=0, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertTrue(cb.checked)
        self.assertIsNotNone(cmd)


if __name__ == "__main__":
    unittest.main()
