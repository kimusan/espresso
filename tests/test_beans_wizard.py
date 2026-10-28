"""Unit tests for Wizard multi-step guided flow bean."""

from __future__ import annotations

import unittest

from espresso.beans.wizard import (
    Wizard,
    WizardBackMsg,
    WizardCancelMsg,
    WizardCompleteMsg,
    WizardNextMsg,
    WizardStep,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Model, Msg
from espresso.crema import strip_ansi


class DummyFormModel(Model):
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.width = 0
        self.height = 0

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def init(self):
        return None

    def update(self, msg: Msg):
        if isinstance(msg, KeyMsg):
            if msg.key.char:
                self.value += msg.key.char
        return self, None

    def view(self) -> str:
        return f"Form Value: {self.value}"


class TestWizard(unittest.TestCase):
    def setUp(self) -> None:
        self.form_step2 = DummyFormModel(value="user_input")

        def _validate_step1() -> tuple[bool, str]:
            if self.step1_valid:
                return True, ""
            return False, "Step 1 validation failed!"

        self.step1_valid = True

        self.steps = [
            WizardStep(
                id="provider",
                title="Provider",
                content="Choose server type",
                description="Select your email provider",
                validate=_validate_step1,
            ),
            WizardStep(
                id="credentials",
                title="Credentials",
                content=self.form_step2,
                description="Enter login credentials",
            ),
            WizardStep(
                id="verify",
                title="Verify",
                content="Review & Confirm settings",
                description="Verify connection",
            ),
        ]
        self.wizard = Wizard(
            steps=self.steps,
            allow_cancel=True,
            width=70,
            height=16,
            data={"initial_config": "yes"},
        )

    def test_initial_state_and_rendering(self) -> None:
        self.assertEqual(self.wizard.current_step, 0)
        v = strip_ansi(self.wizard.view())
        self.assertIn("1. Provider", v)
        self.assertIn("2. Credentials", v)
        self.assertIn("3. Verify", v)
        self.assertIn("Select your email provider", v)
        self.assertIn("Next >", v)
        self.assertIn("Cancel", v)

    def test_next_step_advancement(self) -> None:
        # Step 0 -> Step 1
        self.wizard, cmd = self.wizard.update(KeyMsg("enter"))
        self.assertEqual(self.wizard.current_step, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, WizardNextMsg)
        self.assertEqual(msg.from_step, 0)
        self.assertEqual(msg.to_step, 1)

    def test_validation_blocks_advancement(self) -> None:
        self.step1_valid = False
        self.wizard, cmd = self.wizard.update(KeyMsg("enter"))
        # Remains on step 0
        self.assertEqual(self.wizard.current_step, 0)
        self.assertIsNone(cmd)
        self.assertEqual(self.wizard.error_message, "Step 1 validation failed!")

        # Error banner visible in view
        v = strip_ansi(self.wizard.view())
        self.assertIn("Step 1 validation failed!", v)

        # Fix validation
        self.step1_valid = True
        self.wizard, cmd2 = self.wizard.update(KeyMsg("enter"))
        self.assertEqual(self.wizard.current_step, 1)
        self.assertEqual(self.wizard.error_message, "")
        self.assertIsNotNone(cmd2)

    def test_back_navigation_and_state_preservation(self) -> None:
        # Move to step 1
        self.wizard.next_step()
        self.assertEqual(self.wizard.current_step, 1)

        # Type into step 2's form model
        self.wizard, _ = self.wizard.update(KeyMsg("x"))
        self.assertEqual(self.form_step2.value, "user_inputx")

        # Navigate back to step 0
        self.wizard, cmd_back = self.wizard.update(KeyMsg("esc"))
        self.assertEqual(self.wizard.current_step, 0)
        self.assertIsNotNone(cmd_back)
        msg_back = cmd_back()
        self.assertIsInstance(msg_back, WizardBackMsg)
        self.assertEqual(msg_back.from_step, 1)
        self.assertEqual(msg_back.to_step, 0)

        # Navigate forward to step 1 again: form model still has "user_inputx"
        self.wizard.next_step()
        self.assertEqual(self.wizard.current_step, 1)
        self.assertEqual(self.form_step2.value, "user_inputx")

    def test_final_step_completion(self) -> None:
        # Step 0 -> Step 1
        self.wizard.next_step()
        # Step 1 -> Step 2
        self.wizard.next_step()
        self.assertEqual(self.wizard.current_step, 2)

        # On step 2 (last step), button label is Finish
        v = strip_ansi(self.wizard.view())
        self.assertIn("Finish ✔", v)

        # Enter completes wizard
        self.wizard.data["auth_token"] = "xyz123"
        self.wizard, cmd = self.wizard.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, WizardCompleteMsg)
        self.assertEqual(msg.data["auth_token"], "xyz123")
        self.assertEqual(msg.data["initial_config"], "yes")

    def test_cancel_flow(self) -> None:
        # On step 0, Esc triggers cancel
        self.wizard, cmd = self.wizard.update(KeyMsg("esc"))
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), WizardCancelMsg)

    def test_mouse_button_clicks(self) -> None:
        # Button bar row y
        _ = self.wizard.view()  # Computes _button_bounds and _button_row_y
        btn_y = self.wizard._button_row_y

        # Click Next button
        next_x0, next_x1 = 0, 0
        for b_id, x0, x1 in self.wizard._button_bounds:
            if b_id == "next":
                next_x0, next_x1 = x0, x1
                break

        self.wizard, cmd = self.wizard.update(
            MouseMsg(x=next_x0 + 1, y=btn_y, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertEqual(self.wizard.current_step, 1)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), WizardNextMsg)

    def test_mouse_header_badge_click(self) -> None:
        # Advance to step 1
        self.wizard.next_step()
        self.assertEqual(self.wizard.current_step, 1)

        _ = self.wizard.view()
        # Step 0 badge is at x0..x1 on row 1
        step0_x0, step0_x1 = self.wizard._step_bounds[0][1], self.wizard._step_bounds[0][2]
        self.wizard, cmd = self.wizard.update(
            MouseMsg(x=step0_x0 + 1, y=1, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertEqual(self.wizard.current_step, 0)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), WizardBackMsg)

    def test_mouse_content_model_forwarding(self) -> None:
        # Move to step 1 which has DummyFormModel
        self.wizard.next_step()
        _ = self.wizard.view()

        content_y = self.wizard._content_start_y
        # Click inside content area
        self.wizard, _ = self.wizard.update(
            MouseMsg(x=10, y=content_y, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        # Form model received mouse event
        self.assertEqual(self.wizard.current_step, 1)


if __name__ == "__main__":
    unittest.main()
