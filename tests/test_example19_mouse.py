"""Unit tests verifying mouse control across Example 19 Desktop Showcase."""

import importlib
import unittest
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.keys import KeyMsg
from espresso.beans.card_list import CardSelectMsg, CardActivateMsg
from espresso.beans.menubar import MenuSelectMsg
from espresso.beans.textinput import TextInput

ex19 = importlib.import_module("examples.19_desktop_beans_showcase")
DesktopShowcaseApp = ex19.DesktopShowcaseApp
FolderSelectMsg = ex19.FolderSelectMsg
EmailActionMsg = ex19.EmailActionMsg
ProviderSelector = ex19.ProviderSelector
CredentialsForm = ex19.CredentialsForm
SecurityOptions = ex19.SecurityOptions
FolderTreePane = ex19.FolderTreePane
MessageDetailPane = ex19.MessageDetailPane


class TestExample19MouseControl(unittest.TestCase):
    def setUp(self) -> None:
        self.app = DesktopShowcaseApp()

    def test_folder_tree_pane_mouse_click_and_wheel(self) -> None:
        folder_pane = FolderTreePane()
        # Row 0: Header, Row 1: Border, Row 2: Inbox, Row 3: Starred
        press_msg = MouseMsg(x=5, y=3, button=MouseButton.LEFT, action=MouseAction.PRESS)
        new_pane, cmd = folder_pane.update(press_msg)
        self.assertEqual(new_pane.selected_folder_id, "starred")
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, FolderSelectMsg)
        self.assertEqual(msg.folder_id, "starred")

        # Test wheel down
        wheel_msg = MouseMsg(x=5, y=3, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS)
        new_pane2, cmd2 = new_pane.update(wheel_msg)
        self.assertEqual(new_pane2.selected_folder_id, "sent")
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertEqual(msg2.folder_id, "sent")

    def test_message_detail_pane_toolbar_click_and_scroll(self) -> None:
        app = DesktopShowcaseApp()
        detail_pane = app.detail_pane
        # Render view to populate _btn_bounds
        detail_pane.view()
        self.assertTrue(len(detail_pane._btn_bounds) > 0)

        # Click on Star button (action 0)
        action_name, x0, x1 = detail_pane._btn_bounds[0]
        click_x = (x0 + x1) // 2
        star_msg = MouseMsg(x=click_x, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS)
        _, cmd = detail_pane.update(star_msg)
        self.assertIsNotNone(cmd)
        res = cmd()
        self.assertIsInstance(res, EmailActionMsg)
        self.assertEqual(res.action, "star")

        # Mouse wheel scroll
        self.assertEqual(detail_pane.scroll_y, 0)
        wheel_down = MouseMsg(x=10, y=10, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS)
        detail_pane.update(wheel_down)
        self.assertEqual(detail_pane.scroll_y, 1)

    def test_provider_selector_mouse_interaction(self) -> None:
        selector = ProviderSelector()
        self.assertEqual(selector.selected_idx, 0)

        # Click second option (row 2 -> option index 1)
        click_msg = MouseMsg(x=5, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS)
        selector.update(click_msg)
        self.assertEqual(selector.selected_idx, 1)

        # Wheel down to third option
        wheel_msg = MouseMsg(x=5, y=2, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS)
        selector.update(wheel_msg)
        self.assertEqual(selector.selected_idx, 2)

    def test_credentials_form_click_to_focus(self) -> None:
        inp1 = TextInput(prompt="Field 1: ")
        inp2 = TextInput(prompt="Field 2: ")
        inp3 = TextInput(prompt="Field 3: ")
        form = CredentialsForm(inp1, inp2, inp3)
        self.assertEqual(form.focus_idx, 0)
        self.assertTrue(inp1.focused)
        self.assertFalse(inp2.focused)

        # Click row 2 (Field 2)
        click_msg = MouseMsg(x=12, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS)
        form.update(click_msg)
        self.assertEqual(form.focus_idx, 1)
        self.assertFalse(inp1.focused)
        self.assertTrue(inp2.focused)

    def test_security_options_checkbox_toggle(self) -> None:
        sec = SecurityOptions()
        initial_val = sec.options[0]["checked"]
        click_msg = MouseMsg(x=4, y=0, button=MouseButton.LEFT, action=MouseAction.PRESS)
        sec.update(click_msg)
        self.assertNotEqual(sec.options[0]["checked"], initial_val)

    def test_status_bar_button_clicks(self) -> None:
        app = DesktopShowcaseApp()
        # Render view to populate _status_buttons
        app.view()
        self.assertFalse(app.show_wizard)

        # Find wizard button and click it on bottom status bar row (y = height - 1)
        btn_name, x0, x1 = next(b for b in app._status_buttons if b[0] == "wizard")
        click_x = (x0 + x1) // 2
        click_msg = MouseMsg(x=click_x, y=app.height - 1, button=MouseButton.LEFT, action=MouseAction.PRESS)
        app.update(click_msg)
        self.assertTrue(app.show_wizard)

        # Click backdrop outside modal wizard to cancel
        backdrop_click = MouseMsg(x=2, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS)
        app.update(backdrop_click)
        self.assertFalse(app.show_wizard)


if __name__ == "__main__":
    unittest.main()
