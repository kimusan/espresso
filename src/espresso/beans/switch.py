"""Switch toggle component for interactive boolean selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width


@dataclass(frozen=True)
class SwitchToggledMsg(Msg):
    """Message emitted whenever a Switch is toggled."""

    id: str
    value: bool


class Switch(Model):
    """Interactive toggle switch component supporting keyboard and mouse toggling."""

    def __init__(
        self,
        value: bool = False,
        label: str = "",
        id: str = "",
        active_color: str = "#00E676",
        inactive_color: str = "#555566",
        active_text: str = "ON",
        inactive_text: str = "OFF",
        disabled: bool = False,
        focused: bool = True,
    ) -> None:
        self.value = value
        self.label = label
        self.id = id
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.active_text = active_text
        self.inactive_text = inactive_text
        self.disabled = disabled
        self.focused = focused

        # Styles
        self.active_style = Style().bold(True).foreground(self.active_color)
        self.inactive_style = Style().foreground(self.inactive_color)
        self.label_style = Style().foreground("#EEEEEE")
        self.focus_style = Style().bold(True).foreground("#00E5FF")
        self.disabled_style = Style().faint(True)

    def init(self) -> Cmd | None:
        """TEA lifecycle init."""
        return None

    def focus(self) -> None:
        """Enable keyboard focus."""
        self.focused = True

    def blur(self) -> None:
        """Remove keyboard focus."""
        self.focused = False

    def toggle(self) -> tuple[Switch, Cmd | None]:
        """Toggle value and emit message if not disabled."""
        if self.disabled:
            return self, None
        self.value = not self.value
        val = self.value
        sw_id = self.id
        def _cmd() -> Msg:
            return SwitchToggledMsg(id=sw_id, value=val)
        return self, _cmd

    def set_value(self, val: bool) -> tuple[Switch, Cmd | None]:
        """Explicitly set switch state."""
        if self.value == val or self.disabled:
            return self, None
        self.value = val
        sw_id = self.id
        def _cmd() -> Msg:
            return SwitchToggledMsg(id=sw_id, value=val)
        return self, _cmd

    def update(self, msg: Msg) -> tuple[Switch, Cmd | None]:
        """Process keyboard, mouse, and custom toggle messages."""
        if self.disabled:
            return self, None

        if isinstance(msg, KeyMsg) and self.focused:
            match msg.key:
                case "enter" | " ":
                    return self.toggle()
                case "right" | "l":
                    return self.set_value(True)
                case "left" | "h":
                    return self.set_value(False)

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                return self.toggle()

        return self, None

    def view(self) -> str:
        """Render the switch toggle and optional label."""
        if self.disabled:
            state_text = self.active_text if self.value else self.inactive_text
            toggle_str = self.disabled_style.render(f"[ {state_text} ]")
            label_str = self.disabled_style.render(f" {self.label}") if self.label else ""
            return f"{toggle_str}{label_str}"

        if self.value:
            slider = self.active_style.render(f"●─ {self.active_text} ")
            toggle_str = f"[{slider}]"
        else:
            slider = self.inactive_style.render(f" ─● {self.inactive_text}")
            toggle_str = f"[{slider}]"

        if self.focused:
            toggle_str = self.focus_style.render(toggle_str)

        label_str = f" {self.label_style.render(self.label)}" if self.label else ""
        return f"{toggle_str}{label_str}"
