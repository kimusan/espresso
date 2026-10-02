import unittest
from espresso.beans.switch import Switch, SwitchToggledMsg
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestSwitch(unittest.TestCase):
    def test_initial_state(self):
        sw = Switch(value=False, label="Notifications", id="notif_sw")
        self.assertFalse(sw.value)
        self.assertEqual(sw.label, "Notifications")
        self.assertEqual(sw.id, "notif_sw")
        self.assertTrue(sw.focused)
        self.assertIn("OFF", sw.view())
        self.assertIn("Notifications", sw.view())

    def test_toggle_keyboard(self):
        sw = Switch(value=False, id="sw1")
        # Enter toggles
        sw, cmd = sw.update(KeyMsg(key="enter"))
        self.assertTrue(sw.value)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SwitchToggledMsg)
        self.assertEqual(msg.id, "sw1")
        self.assertTrue(msg.value)

        # Space toggles
        sw, cmd = sw.update(KeyMsg(key=" "))
        self.assertFalse(sw.value)
        msg = cmd()
        self.assertFalse(msg.value)

    def test_directional_keys(self):
        sw = Switch(value=False)
        # right turns on
        sw, cmd = sw.update(KeyMsg(key="right"))
        self.assertTrue(sw.value)
        self.assertIsNotNone(cmd)

        # right again does nothing if already on
        sw, cmd = sw.update(KeyMsg(key="right"))
        self.assertTrue(sw.value)
        self.assertIsNone(cmd)

        # left turns off
        sw, cmd = sw.update(KeyMsg(key="left"))
        self.assertFalse(sw.value)
        self.assertIsNotNone(cmd)

    def test_mouse_toggle(self):
        sw = Switch(value=False, id="sw_m")
        mouse_msg = MouseMsg(x=0, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS)
        sw, cmd = sw.update(mouse_msg)
        self.assertTrue(sw.value)
        self.assertIsNotNone(cmd)
        self.assertTrue(cmd().value)

    def test_disabled_state(self):
        sw = Switch(value=False, disabled=True)
        sw, cmd = sw.update(KeyMsg(key="enter"))
        self.assertFalse(sw.value)
        self.assertIsNone(cmd)
        self.assertIn("[ OFF ]", sw.view())

    def test_focus_and_blur(self):
        sw = Switch(value=True, focused=False)
        sw.focus()
        self.assertTrue(sw.focused)
        sw.blur()
        self.assertFalse(sw.focused)
        # When blurred, key events are ignored
        sw, cmd = sw.update(KeyMsg(key="enter"))
        self.assertTrue(sw.value)
        self.assertIsNone(cmd)


if __name__ == "__main__":
    unittest.main()
