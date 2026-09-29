"""Spinner component for animated loading indicators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.tea import Cmd, Model, Msg, tick
from espresso.crema.style import Style

# Presets
DOTS = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
LINE = ("|", "/", "-", "\\")
PULSE = ("█", "▓", "▒", "░", "▒", "▓")
POINTS = ("∙∙∙", "●∙∙", "∙●∙", "∙∙●")
MOON = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
GLOBE = ("🌍", "🌎", "🌏")
COFFEE = ("☕ ", "♨️ ", "☕ ", "✨ ")


@dataclass(frozen=True)
class SpinnerTickMsg(Msg):
    """Message emitted on each animation tick of a spinner."""

    tag: str
    frame: int


class Spinner(Model):
    """Animated loading spinner component."""

    def __init__(
        self,
        frames: Sequence[str] = DOTS,
        fps: float = 12.0,
        style: Style | None = None,
        tag: str = "spinner",
    ) -> None:
        self.frames = tuple(frames)
        self.interval = 1.0 / max(1.0, fps)
        self.style = style or Style().foreground("#7D56F4")
        self.tag = tag
        self.frame_idx = 0

    def init(self) -> Cmd | None:
        return self._next_tick()

    def _next_tick(self) -> Cmd:
        next_idx = (self.frame_idx + 1) % len(self.frames)
        return tick(self.interval, SpinnerTickMsg(tag=self.tag, frame=next_idx))

    def update(self, msg: Msg) -> tuple[Spinner, Cmd | None]:
        if isinstance(msg, SpinnerTickMsg) and msg.tag == self.tag:
            self.frame_idx = msg.frame % len(self.frames)
            return self, self._next_tick()
        return self, None

    def view(self) -> str:
        current_frame = self.frames[self.frame_idx]
        return self.style.render(current_frame)
