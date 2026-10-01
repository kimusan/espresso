"""Unit tests for Form and FormField components."""

from __future__ import annotations

import unittest

from espresso.beans.form import Form, FormField, FormSubmitMsg
from espresso.beans.slider import Slider
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.crema import strip_ansi


class TestForm(unittest.TestCase):
    def test_form_initial_state_and_values(self) -> None:
        name_input = TextInput(value="Alice")
        age_slider = Slider(min_val=18, max_val=99, value=30)

        form = Form(
            fields=[
                FormField(id="name", label="Full Name", bean=name_input, required=True),
                FormField(id="age", label="Age", bean=age_slider),
            ],
            title="User Profile",
        )

        values = form.get_values()
        self.assertEqual(values["name"], "Alice")
        self.assertEqual(values["age"], 30)

        # Field 0 should be focused initially
        self.assertEqual(form.active_index, 0)
        self.assertTrue(name_input.focused)
        self.assertFalse(age_slider.focused)

    def test_tab_focus_cycling(self) -> None:
        t1 = TextInput(value="")
        t2 = TextInput(value="")
        form = Form(fields=[
            FormField(id="f1", label="Field 1", bean=t1),
            FormField(id="f2", label="Field 2", bean=t2),
        ])

        self.assertEqual(form.active_index, 0)
        self.assertTrue(t1.focused)

        # Tab to field 2
        form, _ = form.update(KeyMsg("tab"))
        self.assertEqual(form.active_index, 1)
        self.assertFalse(t1.focused)
        self.assertTrue(t2.focused)

        # Tab to submit button (index 2)
        form, _ = form.update(KeyMsg("tab"))
        self.assertEqual(form.active_index, 2)
        self.assertFalse(t1.focused)
        self.assertFalse(t2.focused)

        # Tab wraps around to field 1 (index 0)
        form, _ = form.update(KeyMsg("tab"))
        self.assertEqual(form.active_index, 0)
        self.assertTrue(t1.focused)

        # Shift+Tab wraps back to submit button
        form, _ = form.update(KeyMsg("shift+tab"))
        self.assertEqual(form.active_index, 2)

    def test_validation_required_and_custom(self) -> None:
        email_input = TextInput(value="")

        def _validate_email(val: str) -> str | None:
            if "@" not in str(val):
                return "Must contain @"
            return None

        form = Form(fields=[
            FormField(id="email", label="Email Address", bean=email_input, validator=_validate_email, required=True),
        ])

        # Attempt to submit empty form
        cmd = form.submit()
        self.assertIsNone(cmd, "Invalid form submit should return None")
        self.assertIsNotNone(form.fields[0].error)
        self.assertIn("required", form.fields[0].error)

        # Enter value without @
        email_input.set_value("notanemail")
        cmd2 = form.submit()
        self.assertIsNone(cmd2)
        self.assertIn("Must contain @", form.fields[0].error)

        # Enter valid email
        email_input.set_value("user@example.com")
        cmd3 = form.submit()
        self.assertIsNotNone(cmd3)
        msg = cmd3()
        self.assertIsInstance(msg, FormSubmitMsg)
        self.assertEqual(msg.values["email"], "user@example.com")
        self.assertIsNone(form.fields[0].error)

    def test_ctrl_s_and_enter_submit(self) -> None:
        t = TextInput(value="Valid")
        form = Form(fields=[FormField(id="f", label="F", bean=t)])

        # Ctrl+S submits from any field
        form, cmd = form.update(KeyMsg("ctrl+s"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, FormSubmitMsg)

        # Focus submit button and press Enter
        form.active_index = len(form.fields)  # submit button
        form, cmd2 = form.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertIsInstance(msg2, FormSubmitMsg)

    def test_form_view_rendering(self) -> None:
        form = Form(
            fields=[
                FormField(id="name", label="User Name", bean=TextInput(value="Bob"), hint="Enter handle"),
            ],
            title="Settings",
            submit_label="Save Changes",
        )
        v = strip_ansi(form.view())
        self.assertIn("Settings", v)
        self.assertIn("User Name", v)
        self.assertIn("Bob", v)
        self.assertIn("Enter handle", v)
        self.assertIn("Save Changes", v)


    def test_arrow_and_mouse_navigation(self) -> None:
        from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
        t1 = TextInput(value="One")
        t2 = TextInput(value="Two")
        form = Form(
            fields=[
                FormField(id="1", label="First", bean=t1),
                FormField(id="2", label="Second", bean=t2),
            ],
            title="Nav Test",
            offset_y=5,
        )
        self.assertEqual(form.active_index, 0)

        # Down arrow moves to field 1 (index 1)
        form, _ = form.update(KeyMsg("down"))
        self.assertEqual(form.active_index, 1)

        # Down arrow moves to submit button (index 2)
        form, _ = form.update(KeyMsg("down"))
        self.assertEqual(form.active_index, 2)

        # Up arrow moves back to field 1 (index 1)
        form, _ = form.update(KeyMsg("up"))
        self.assertEqual(form.active_index, 1)

        # Mouse click on field 0 area (local y = 2, so screen y = 5 + 2 = 7)
        form, _ = form.update(MouseMsg(x=10, y=7, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(form.active_index, 0)

        # Mouse click on submit button area (local y > 8)
        form, cmd = form.update(MouseMsg(x=10, y=20, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(form.active_index, 2)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, FormSubmitMsg)


if __name__ == "__main__":
    unittest.main()
