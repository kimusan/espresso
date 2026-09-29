"""TextInput component for interactive single-line text entry."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style


class EchoMode(Enum):
    """Controls how text input characters are displayed."""

    NORMAL = "normal"
    PASSWORD = "password"
    NONE = "none"


class TextInput(Model):
    """Single-line text input field."""

    def __init__(
        self,
        placeholder: str = "",
        prompt: str = "> ",
        char_limit: int = 256,
        echo_mode: EchoMode = EchoMode.NORMAL,
        style: Style | None = None,
        placeholder_style: Style | None = None,
        prompt_style: Style | None = None,
    ) -> None:
        self.value = ""
        self.cursor_pos = 0
        self.placeholder = placeholder
        self.prompt = prompt
        self.char_limit = char_limit
        self.echo_mode = echo_mode
        self.focused = True

        self.style = style or Style().foreground("#FAFAFA")
        self.placeholder_style = placeholder_style or Style().foreground("#666666")
        self.prompt_style = prompt_style or Style().bold(True).foreground("#7D56F4")

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False

    def set_value(self, val: str) -> None:
        self.value = val[: self.char_limit]
        self.cursor_pos = len(self.value)

    def update(self, msg: Msg) -> tuple[TextInput, Cmd | None]:
        if not self.focused:
            return self, None

        match msg:
            case KeyMsg(key="left"):
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                return self, None

            case KeyMsg(key="right"):
                if self.cursor_pos < len(self.value):
                    self.cursor_pos += 1
                return self, None

            case KeyMsg(key="home" | "ctrl+a"):
                self.cursor_pos = 0
                return self, None

            case KeyMsg(key="end" | "ctrl+e"):
                self.cursor_pos = len(self.value)
                return self, None

            case KeyMsg(key="backspace"):
                if self.cursor_pos > 0:
                    self.value = self.value[: self.cursor_pos - 1] + self.value[self.cursor_pos :]
                    self.cursor_pos -= 1
                return self, None

            case KeyMsg(key="delete"):
                if self.cursor_pos < len(self.value):
                    self.value = self.value[: self.cursor_pos] + self.value[self.cursor_pos + 1 :]
                return self, None

            case KeyMsg(key=k) if k.char is not None and not (k.ctrl or k.alt):
                if len(self.value) < self.char_limit:
                    self.value = self.value[: self.cursor_pos] + k.char + self.value[self.cursor_pos :]
                    self.cursor_pos += 1
                return self, None

        return self, None

    def view(self) -> str:
        prompt_rendered = self.prompt_style.render(self.prompt)

        # Placeholder display when empty and not focused or focused with no text
        if not self.value:
            if self.focused:
                # Show blinking block cursor on top of first placeholder char
                cursor_char = self.placeholder[0] if self.placeholder else " "
                rest_placeholder = self.placeholder[1:] if len(self.placeholder) > 1 else ""
                cursor_styled = f"\033[7m{cursor_char}\033[0m"
                return f"{prompt_rendered}{cursor_styled}{self.placeholder_style.render(rest_placeholder)}"
            return f"{prompt_rendered}{self.placeholder_style.render(self.placeholder)}"

        # Mask text if password mode
        if self.echo_mode == EchoMode.PASSWORD:
            display_chars = "•" * len(self.value)
        elif self.echo_mode == EchoMode.NONE:
            display_chars = ""
        else:
            display_chars = self.value

        if not self.focused:
            return f"{prompt_rendered}{self.style.render(display_chars)}"

        # Render cursor in the string
        before = display_chars[: self.cursor_pos]
        cur_char = display_chars[self.cursor_pos] if self.cursor_pos < len(display_chars) else " "
        after = display_chars[self.cursor_pos + 1 :] if self.cursor_pos < len(display_chars) else ""

        cursor_rendered = f"\033[7m{cur_char}\033[0m"
        return f"{prompt_rendered}{self.style.render(before)}{cursor_rendered}{self.style.render(after)}"
