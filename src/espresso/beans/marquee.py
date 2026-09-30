"""Smooth horizontal scrolling Marquee text banner and ticker component."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.overlay import slice_ansi
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


class MarqueeMode(Enum):
    """Scrolling behavior of the marquee."""

    LOOP = "loop"      # Smooth infinite loop with configurable separator
    BOUNCE = "bounce"  # Scrolls to the end, pauses, and reverses direction


@dataclass(frozen=True)
class MarqueeTickMsg(Msg):
    """Message emitted on timer tick to advance the marquee animation."""

    tag: str = "marquee"


class Marquee(Model):
    """A fixed-width horizontally scrolling animated text banner."""

    def __init__(
        self,
        text: str,
        width: int = 30,
        mode: MarqueeMode = MarqueeMode.LOOP,
        speed: float = 0.12,
        pause_frames: int = 8,
        separator: str = "   ★   ",
        style: Style | None = None,
        tag: str = "marquee",
        auto_start: bool = True,
        loop_if_fits: bool = True,
    ) -> None:
        self.text = text
        self.width = max(4, width)
        self.mode = mode
        self.speed = max(0.01, speed)
        self.pause_frames = max(0, pause_frames)
        self.separator = separator
        self.style = style or Style()
        self.tag = tag
        self.auto_start = auto_start
        self.loop_if_fits = loop_if_fits

        self.offset: int = 0
        self.direction: int = 1  # 1 for forward, -1 for backward (bounce mode)
        self._pause_countdown: int = 0

    def set_text(self, text: str) -> None:
        """Update display text and reset scroll position."""
        self.text = text
        self.offset = 0
        self.direction = 1
        self._pause_countdown = 0

    def set_width(self, width: int) -> None:
        """Resize the marquee container width."""
        self.width = max(4, width)

    def step(self) -> None:
        """Advance the animation by one character step."""
        text_w = string_width(self.text)
        if self.mode == MarqueeMode.BOUNCE and text_w <= self.width:
            self.offset = 0
            return
        if self.mode == MarqueeMode.LOOP and not self.loop_if_fits and text_w <= self.width:
            self.offset = 0
            return

        if self._pause_countdown > 0:
            self._pause_countdown -= 1
            return

        if self.mode == MarqueeMode.LOOP:
            loop_unit = f"{self.text}{self.separator}"
            unit_len = string_width(loop_unit)
            self.offset = (self.offset + 1) % max(1, unit_len)

        elif self.mode == MarqueeMode.BOUNCE:
            max_offset = text_w - self.width
            new_offset = self.offset + self.direction

            if new_offset >= max_offset:
                self.offset = max_offset
                self.direction = -1
                self._pause_countdown = self.pause_frames
            elif new_offset <= 0:
                self.offset = 0
                self.direction = 1
                self._pause_countdown = self.pause_frames
            else:
                self.offset = new_offset

    def tick(self) -> Cmd:
        """Return a command that triggers a MarqueeTickMsg after self.speed."""
        tag = self.tag
        speed = self.speed

        async def _tick_async() -> Msg:
            await asyncio.sleep(speed)
            return MarqueeTickMsg(tag=tag)

        return _tick_async

    def init(self) -> Cmd | None:
        """Emit initial animation tick if auto_start is True."""
        if self.auto_start:
            if self.mode == MarqueeMode.LOOP and self.loop_if_fits:
                return self.tick()
            elif string_width(self.text) > self.width:
                return self.tick()
        return None

    def update(self, msg: Msg) -> tuple[Marquee, Cmd | None]:
        """Handle MarqueeTickMsg to advance frame and schedule next tick."""
        if isinstance(msg, MarqueeTickMsg) and msg.tag == self.tag:
            self.step()
            return self, self.tick()
        return self, None

    def view(self) -> str:
        """Render the visible slice of scrolling text padded to self.width."""
        text_w = string_width(self.text)

        # 1. Fits within window in non-looping or bounce mode: no scroll
        if self.mode == MarqueeMode.BOUNCE and text_w <= self.width:
            pad = " " * (self.width - text_w)
            return self.style.render(f"{self.text}{pad}")

        if self.mode == MarqueeMode.LOOP and not self.loop_if_fits and text_w <= self.width:
            pad = " " * (self.width - text_w)
            return self.style.render(f"{self.text}{pad}")

        # 2. Bounce mode slice
        if self.mode == MarqueeMode.BOUNCE:
            sliced = slice_ansi(self.text, self.offset, self.offset + self.width)
            w = string_width(sliced)
            pad = " " * max(0, self.width - w)
            return self.style.render(f"{sliced}{pad}")

        # 3. Loop mode: repeat pattern seamlessly
        loop_unit = f"{self.text}{self.separator}"
        unit_w = string_width(loop_unit)
        repeats = (self.width // max(1, unit_w)) + 3
        infinite_stream = loop_unit * repeats

        sliced = slice_ansi(infinite_stream, self.offset, self.offset + self.width)
        w = string_width(sliced)
        pad = " " * max(0, self.width - w)
        return self.style.render(f"{sliced}{pad}")
