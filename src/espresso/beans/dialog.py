"""Dialog and modal confirmation component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import Border, ROUNDED_BORDER
from espresso.crema.style import Align, Style


@dataclass(frozen=True)
class DialogResultMsg(Msg):
    """Message emitted when an action button is selected in a Dialog."""

    action: str
    button_index: int


class Dialog(Model):
    """A floating modal dialog box with a title, body message, and action buttons.

    Modeled after rmhubbert/bubbletea-overlay and standard modal dialogs.
    """

    def __init__(
        self,
        title: str = "Confirm",
        message: str = "",
        buttons: Sequence[str] = ("Confirm", "Cancel"),
        width: int = 42,
        border: Border = ROUNDED_BORDER,
        border_foreground: str = "#7D56F4",
        background: str = "#1A1A24",
    ) -> None:
        self.title = title
        self.message = message
        self.buttons = list(buttons) if buttons else ["OK"]
        self.selected_button = 0
        self.width = max(24, width)

        self.border = border
        self.border_foreground = border_foreground
        self.background = background

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Dialog, Cmd | None]:
        """Handle button navigation (Tab, Left, Right) and submission (Enter)."""
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "tab" | "right" | "l":
                    self.selected_button = (self.selected_button + 1) % len(self.buttons)
                    return self, None
                case "shift+tab" | "left" | "h":
                    self.selected_button = (self.selected_button - 1) % len(self.buttons)
                    return self, None
                case "enter" | " ":
                    action = self.buttons[self.selected_button]
                    def _emit_result() -> Msg:
                        return DialogResultMsg(action=action, button_index=self.selected_button)
                    return self, _emit_result
                case "esc":
                    # Esc defaults to Cancel if available, or last button
                    cancel_idx = self.buttons.index("Cancel") if "Cancel" in self.buttons else (len(self.buttons) - 1)
                    action = self.buttons[cancel_idx]
                    def _emit_cancel() -> Msg:
                        return DialogResultMsg(action=action, button_index=cancel_idx)
                    return self, _emit_cancel
        return self, None

    def view(self) -> str:
        """Render the modal dialog card."""
        # Render action buttons
        btn_strs: list[str] = []
        for i, label in enumerate(self.buttons):
            if i == self.selected_button:
                btn_style = (
                    Style()
                    .bold(True)
                    .foreground("#000000")
                    .background("#00E676")
                    .padding(0, 2)
                )
                btn_strs.append(btn_style.render(label))
            else:
                btn_style = (
                    Style()
                    .foreground("#B0B0B0")
                    .background("#2A2A38")
                    .padding(0, 2)
                )
                btn_strs.append(btn_style.render(label))

        buttons_row = "   ".join(btn_strs)
        centered_buttons = Style().align(Align.CENTER).width(self.width - 6).render(buttons_row)

        body_lines: list[str] = []
        if self.message:
            body_lines.append(self.message)
            body_lines.append("")
        body_lines.append(centered_buttons)

        content = "\n".join(body_lines)

        card_style = (
            Style()
            .border(self.border)
            .border_foreground(self.border_foreground)
            .border_title(f" {self.title} " if self.title else None, Align.LEFT)
            .background(self.background)
            .foreground("#E0E0E0")
            .padding(1, 2)
            .width(self.width)
        )

        return card_style.render(content)
