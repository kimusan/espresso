"""Viewport component for scrollable text panes."""

from __future__ import annotations

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import truncate_ansi


class Viewport(Model):
    """Scrollable rectangular viewport."""

    def __init__(self, width: int = 80, height: int = 20, style: Style | None = None) -> None:
        self.width = width
        self.height = height
        self.style = style or Style()
        self.lines: list[str] = []
        self.y_offset = 0

    def init(self) -> Cmd | None:
        return None

    def set_content(self, text: str) -> None:
        """Set the text content to be displayed in the viewport."""
        self.lines = text.splitlines() if text else []
        self.y_offset = min(self.y_offset, max(0, len(self.lines) - self.height))

    @property
    def max_offset(self) -> int:
        return max(0, len(self.lines) - self.height)

    @property
    def scroll_percent(self) -> float:
        if self.max_offset == 0:
            return 1.0
        return self.y_offset / self.max_offset

    def update(self, msg: Msg) -> tuple[Viewport, Cmd | None]:
        match msg:
            case KeyMsg(key="up" | "k"):
                if self.y_offset > 0:
                    self.y_offset -= 1
                return self, None

            case KeyMsg(key="down" | "j"):
                if self.y_offset < self.max_offset:
                    self.y_offset += 1
                return self, None

            case KeyMsg(key="pageup" | "ctrl+u"):
                self.y_offset = max(0, self.y_offset - self.height)
                return self, None

            case KeyMsg(key="pagedown" | "ctrl+d"):
                self.y_offset = min(self.max_offset, self.y_offset + self.height)
                return self, None

            case KeyMsg(key="home" | "g"):
                self.y_offset = 0
                return self, None

            case KeyMsg(key="end" | "G"):
                self.y_offset = self.max_offset
                return self, None

            case MouseMsg(button=MouseButton.WHEEL_UP):
                if self.y_offset > 0:
                    self.y_offset -= 1
                return self, None

            case MouseMsg(button=MouseButton.WHEEL_DOWN):
                if self.y_offset < self.max_offset:
                    self.y_offset += 1
                return self, None

        return self, None

    def view(self) -> str:
        visible = self.lines[self.y_offset : self.y_offset + self.height]
        # Truncate lines to viewport width
        truncated = [truncate_ansi(l, self.width, tail="") for l in visible]

        # Fill remaining height with blank rows if content is short
        while len(truncated) < self.height:
            truncated.append("")

        return self.style.render("\n".join(truncated))
