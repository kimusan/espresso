"""Tactile Slider and RangeSlider components supporting mouse drag and keyboard adjustment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width


@dataclass(frozen=True)
class SliderChangeMsg(Msg):
    """Message emitted whenever a Slider's value changes."""

    value: float
    percent: float


@dataclass(frozen=True)
class RangeSliderChangeMsg(Msg):
    """Message emitted whenever a RangeSlider's interval changes."""

    low: float
    high: float
    percent_low: float
    percent_high: float


class Slider(Model):
    """Interactive numeric slider with tactile mouse drag tracking and keyboard navigation."""

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 100.0,
        value: float = 0.0,
        step: float = 1.0,
        width: int = 30,
        label: str = "",
        show_value: bool = True,
        value_format: str = "{value:.0f}%",
        track_char: str = "─",
        filled_char: str = "━",
        thumb_char: str = "●",
        track_style: Style | None = None,
        filled_style: Style | None = None,
        thumb_style: Style | None = None,
        label_style: Style | None = None,
        value_style: Style | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        self.min_val = min_val
        self.max_val = max(min_val + 0.001, max_val)
        self.step = max(0.001, step)
        self.width = max(10, width)
        self.label = label
        self.show_value = show_value
        self.value_format = value_format
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.track_char = track_char
        self.filled_char = filled_char
        self.thumb_char = thumb_char

        self.track_style = track_style or Style().foreground("#444466")
        self.filled_style = filled_style or Style().foreground("#7D56F4")
        self.thumb_style = thumb_style or Style().bold(True).foreground("#00E5FF")
        self.label_style = label_style or Style().bold(True).foreground("#FFFFFF")
        self.value_style = value_style or Style().foreground("#8888AA")

        self.is_dragging: bool = False
        self.focused: bool = True
        self._value = max(self.min_val, min(self.max_val, value))

    def set_offset(self, x: int, y: int) -> None:
        """Set the top-left screen position offset (column, row) for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val: float) -> None:
        self.set_value(val)

    @property
    def percent(self) -> float:
        """Normalized percentage from 0.0 to 1.0."""
        span = self.max_val - self.min_val
        if span <= 0:
            return 0.0
        return max(0.0, min(1.0, (self._value - self.min_val) / span))

    def set_value(self, val: float) -> Cmd | None:
        """Set value with step quantization and clamping, emitting SliderChangeMsg if changed."""
        clamped = max(self.min_val, min(self.max_val, val))
        steps = round((clamped - self.min_val) / self.step)
        quantized = self.min_val + steps * self.step
        quantized = max(self.min_val, min(self.max_val, quantized))

        if quantized != self._value:
            self._value = quantized
            v, p = self._value, self.percent
            def _emit() -> Msg:
                return SliderChangeMsg(value=v, percent=p)
            return _emit
        return None

    def _track_layout(self) -> tuple[int, int]:
        """Returns (track_start_x, track_length)."""
        label_w = string_width(self.label) + 1 if self.label else 0
        sample_val = self.value_format.format(value=self.max_val)
        val_w = string_width(sample_val) + 1 if self.show_value else 0
        track_w = max(5, self.width - label_w - val_w)
        return label_w, track_w

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Slider, Cmd | None]:
        """Handle mouse clicks, drag motion, and keyboard step adjustment."""
        label_w, track_w = self._track_layout()

        if isinstance(msg, MouseMsg):
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            # Mouse wheel
            if msg.button == MouseButton.WHEEL_UP:
                if local_y == 0 and label_w <= local_x <= label_w + track_w:
                    cmd = self.set_value(self._value + self.step)
                    return self, cmd
                return self, None
            elif msg.button == MouseButton.WHEEL_DOWN:
                if local_y == 0 and label_w <= local_x <= label_w + track_w:
                    cmd = self.set_value(self._value - self.step)
                    return self, cmd
                return self, None

            # Click or Drag
            if msg.action == MouseAction.PRESS and msg.button == MouseButton.LEFT:
                if local_y == 0 and label_w <= local_x <= label_w + track_w:
                    self.is_dragging = True
                    ratio = (local_x - label_w) / max(1, track_w - 1)
                    target_val = self.min_val + ratio * (self.max_val - self.min_val)
                    cmd = self.set_value(target_val)
                    return self, cmd

            elif msg.action == MouseAction.MOTION and self.is_dragging:
                ratio = (local_x - label_w) / max(1, track_w - 1)
                ratio = max(0.0, min(1.0, ratio))
                target_val = self.min_val + ratio * (self.max_val - self.min_val)
                cmd = self.set_value(target_val)
                return self, cmd

            elif msg.action == MouseAction.RELEASE:
                if self.is_dragging:
                    self.is_dragging = False
                    return self, None

        elif isinstance(msg, KeyMsg) and self.focused:
            match msg.key:
                case "right" | "up" | "l" | "k":
                    cmd = self.set_value(self._value + self.step)
                    return self, cmd
                case "left" | "down" | "h" | "j":
                    cmd = self.set_value(self._value - self.step)
                    return self, cmd
                case "pgup" | "pageup":
                    cmd = self.set_value(self._value + 5 * self.step)
                    return self, cmd
                case "pgdn" | "pagedown":
                    cmd = self.set_value(self._value - 5 * self.step)
                    return self, cmd
                case "home":
                    cmd = self.set_value(self.min_val)
                    return self, cmd
                case "end":
                    cmd = self.set_value(self.max_val)
                    return self, cmd

        return self, None

    def view(self) -> str:
        """Render the slider track, filled progress, thumb knob, and value badge."""
        label_part = f"{self.label_style.render(self.label)} " if self.label else ""
        _, track_w = self._track_layout()

        # Thumb position along track (0 to track_w - 1)
        thumb_idx = int(round(self.percent * (track_w - 1)))
        thumb_idx = max(0, min(track_w - 1, thumb_idx))

        filled_part = self.filled_char * thumb_idx
        thumb_part = self.thumb_char
        unfilled_part = self.track_char * (track_w - 1 - thumb_idx)

        styled_track = (
            f"{self.filled_style.render(filled_part)}"
            f"{self.thumb_style.render(thumb_part)}"
            f"{self.track_style.render(unfilled_part)}"
        )

        val_part = ""
        if self.show_value:
            fmt_val = self.value_format.format(value=self._value)
            val_part = f" {self.value_style.render(fmt_val)}"

        return f"{label_part}{styled_track}{val_part}"


class RangeSlider(Model):
    """Dual-thumb range slider for selecting intervals [low, high]."""

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 100.0,
        low: float = 20.0,
        high: float = 80.0,
        step: float = 1.0,
        width: int = 30,
        label: str = "",
        show_value: bool = True,
        value_format: str = "{low:.0f} - {high:.0f}",
        track_char: str = "─",
        range_char: str = "━",
        thumb_char: str = "●",
        track_style: Style | None = None,
        range_style: Style | None = None,
        thumb_style: Style | None = None,
        active_thumb_style: Style | None = None,
        label_style: Style | None = None,
        value_style: Style | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        self.min_val = min_val
        self.max_val = max(min_val + 0.001, max_val)
        self.step = max(0.001, step)
        self.width = max(10, width)
        self.label = label
        self.show_value = show_value
        self.value_format = value_format
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.track_char = track_char
        self.range_char = range_char
        self.thumb_char = thumb_char

        self.track_style = track_style or Style().foreground("#444466")
        self.range_style = range_style or Style().foreground("#7D56F4")
        self.thumb_style = thumb_style or Style().bold(True).foreground("#00E5FF")
        self.active_thumb_style = active_thumb_style or Style().bold(True).foreground("#FF007F")
        self.label_style = label_style or Style().bold(True).foreground("#FFFFFF")
        self.value_style = value_style or Style().foreground("#8888AA")

        self.active_thumb: str = "low"  # "low" or "high"
        self.dragging_thumb: str | None = None
        self.focused: bool = True

        self._low = max(self.min_val, min(self.max_val, low))
        self._high = max(self._low, min(self.max_val, high))

    def set_offset(self, x: int, y: int) -> None:
        """Set the top-left screen position offset (column, row) for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    @property
    def low(self) -> float:
        return self._low

    @property
    def high(self) -> float:
        return self._high

    @property
    def percent_low(self) -> float:
        span = self.max_val - self.min_val
        return 0.0 if span <= 0 else max(0.0, min(1.0, (self._low - self.min_val) / span))

    @property
    def percent_high(self) -> float:
        span = self.max_val - self.min_val
        return 0.0 if span <= 0 else max(0.0, min(1.0, (self._high - self.min_val) / span))

    def set_range(self, low: float, high: float) -> Cmd | None:
        """Update range interval with step quantization and mutual clamping."""
        clamped_low = max(self.min_val, min(self.max_val, low))
        clamped_high = max(self.min_val, min(self.max_val, high))
        if clamped_low > clamped_high:
            clamped_low, clamped_high = clamped_high, clamped_low

        steps_l = round((clamped_low - self.min_val) / self.step)
        steps_h = round((clamped_high - self.min_val) / self.step)
        q_low = max(self.min_val, min(self.max_val, self.min_val + steps_l * self.step))
        q_high = max(q_low, min(self.max_val, self.min_val + steps_h * self.step))

        if q_low != self._low or q_high != self._high:
            self._low = q_low
            self._high = q_high
            l, h = self._low, self._high
            pl, ph = self.percent_low, self.percent_high
            def _emit() -> Msg:
                return RangeSliderChangeMsg(low=l, high=h, percent_low=pl, percent_high=ph)
            return _emit
        return None

    def _track_layout(self) -> tuple[int, int]:
        label_w = string_width(self.label) + 1 if self.label else 0
        sample_val = self.value_format.format(low=self.min_val, high=self.max_val)
        val_w = string_width(sample_val) + 1 if self.show_value else 0
        track_w = max(5, self.width - label_w - val_w)
        return label_w, track_w

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[RangeSlider, Cmd | None]:
        label_w, track_w = self._track_layout()

        if isinstance(msg, MouseMsg):
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            if msg.action == MouseAction.PRESS and msg.button == MouseButton.LEFT:
                if local_y == 0 and label_w <= local_x <= label_w + track_w:
                    ratio = max(0.0, min(1.0, (local_x - label_w) / max(1, track_w - 1)))
                    target_val = self.min_val + ratio * (self.max_val - self.min_val)
                    # Pick closer thumb
                    dist_low = abs(target_val - self._low)
                    dist_high = abs(target_val - self._high)
                    if dist_low <= dist_high:
                        self.dragging_thumb = "low"
                        self.active_thumb = "low"
                        cmd = self.set_range(target_val, self._high)
                    else:
                        self.dragging_thumb = "high"
                        self.active_thumb = "high"
                        cmd = self.set_range(self._low, target_val)
                    return self, cmd

            elif msg.action == MouseAction.MOTION and self.dragging_thumb is not None:
                ratio = max(0.0, min(1.0, (local_x - label_w) / max(1, track_w - 1)))
                target_val = self.min_val + ratio * (self.max_val - self.min_val)
                if self.dragging_thumb == "low":
                    cmd = self.set_range(min(target_val, self._high), self._high)
                else:
                    cmd = self.set_range(self._low, max(target_val, self._low))
                return self, cmd

            elif msg.action == MouseAction.RELEASE:
                if self.dragging_thumb is not None:
                    self.dragging_thumb = None
                    return self, None

        elif isinstance(msg, KeyMsg) and self.focused:
            match msg.key:
                case "tab":
                    self.active_thumb = "high" if self.active_thumb == "low" else "low"
                    return self, None
                case "right" | "up" | "l" | "k":
                    if self.active_thumb == "low":
                        cmd = self.set_range(min(self._low + self.step, self._high), self._high)
                    else:
                        cmd = self.set_range(self._low, self._high + self.step)
                    return self, cmd
                case "left" | "down" | "h" | "j":
                    if self.active_thumb == "low":
                        cmd = self.set_range(self._low - self.step, self._high)
                    else:
                        cmd = self.set_range(self._low, max(self._high - self.step, self._low))
                    return self, cmd

        return self, None

    def view(self) -> str:
        label_part = f"{self.label_style.render(self.label)} " if self.label else ""
        _, track_w = self._track_layout()

        idx_low = int(round(self.percent_low * (track_w - 1)))
        idx_high = int(round(self.percent_high * (track_w - 1)))
        idx_low = max(0, min(track_w - 1, idx_low))
        idx_high = max(idx_low, min(track_w - 1, idx_high))

        left_track = self.track_char * idx_low
        mid_range = self.range_char * max(0, idx_high - idx_low - 1)
        right_track = self.track_char * max(0, track_w - 1 - idx_high)

        style_l = self.active_thumb_style if self.active_thumb == "low" else self.thumb_style
        style_h = self.active_thumb_style if self.active_thumb == "high" else self.thumb_style

        if idx_low == idx_high:
            # Overlapping thumbs
            thumb_str = self.thumb_style.render(self.thumb_char)
            track_rendered = f"{self.track_style.render(left_track)}{thumb_str}{self.track_style.render(right_track)}"
        else:
            thumb_l = style_l.render(self.thumb_char)
            thumb_h = style_h.render(self.thumb_char)
            range_rendered = self.range_style.render(mid_range)
            track_rendered = f"{self.track_style.render(left_track)}{thumb_l}{range_rendered}{thumb_h}{self.track_style.render(right_track)}"

        val_part = ""
        if self.show_value:
            fmt_val = self.value_format.format(low=self._low, high=self._high)
            val_part = f" {self.value_style.render(fmt_val)}"

        return f"{label_part}{track_rendered}{val_part}"
