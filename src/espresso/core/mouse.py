"""Mouse event definitions and XTerm SGR 1006 decoding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Union

from espresso.core.tea import Msg


class MouseButton(Enum):
    """Mouse buttons."""

    NONE = "none"
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"
    WHEEL_UP = "wheel_up"
    WHEEL_DOWN = "wheel_down"
    WHEEL_LEFT = "wheel_left"
    WHEEL_RIGHT = "wheel_right"


class MouseAction(Enum):
    """Mouse actions."""

    PRESS = "press"
    RELEASE = "release"
    MOTION = "motion"
    DOUBLE_CLICK = "double_click"


@dataclass(frozen=True)
class MouseMsg(Msg):
    """Message emitted on mouse interaction (click, scroll, drag, release)."""

    x: int  # 0-indexed column
    y: int  # 0-indexed row
    button: MouseButton
    action: MouseAction
    ctrl: bool = False
    alt: bool = False
    shift: bool = False

    def __str__(self) -> str:
        return f"MouseMsg({self.button.value}, {self.action.value}, x={self.x}, y={self.y})"

    def translate(self, dx: int, dy: int) -> MouseMsg:
        """Return a new MouseMsg offset by (dx, dy)."""
        return MouseMsg(
            x=self.x + dx,
            y=self.y + dy,
            button=self.button,
            action=self.action,
            ctrl=self.ctrl,
            alt=self.alt,
            shift=self.shift,
        )

    def relative_to(self, origin_x: int = 0, origin_y: int = 0) -> MouseMsg:
        """Return a new MouseMsg relative to an (origin_x, origin_y) coordinate."""
        return MouseMsg(
            x=self.x - origin_x,
            y=self.y - origin_y,
            button=self.button,
            action=self.action,
            ctrl=self.ctrl,
            alt=self.alt,
            shift=self.shift,
        )


# SGR 1006 pattern: \x1b[<b;x;y(M|m)
SGR_MOUSE_REGEX = re.compile(r"^\x1b\[<(\d+);(\d+);(\d+)([Mm])")


def parse_sgr_mouse(seq: str) -> tuple[MouseMsg | None, int]:
    """Parse an SGR 1006 mouse escape sequence.

    Returns (MouseMsg or None, number of characters consumed).
    """
    match = SGR_MOUSE_REGEX.match(seq)
    if not match:
        return None, 0

    btn_code = int(match.group(1))
    col = int(match.group(2)) - 1  # Convert to 0-indexed
    row = int(match.group(3)) - 1
    type_char = match.group(4)
    consumed = match.end()

    # Modifiers
    shift = bool(btn_code & 4)
    alt = bool(btn_code & 8)
    ctrl = bool(btn_code & 16)
    is_motion = bool(btn_code & 32)
    is_wheel = bool(btn_code & 64)

    # Action
    if type_char == "m":
        action = MouseAction.RELEASE
    elif is_motion:
        action = MouseAction.MOTION
    else:
        action = MouseAction.PRESS

    # Button
    if is_wheel:
        wheel_dir = btn_code & 3
        if wheel_dir == 0:
            button = MouseButton.WHEEL_UP
        elif wheel_dir == 1:
            button = MouseButton.WHEEL_DOWN
        elif wheel_dir == 2:
            button = MouseButton.WHEEL_LEFT
        else:
            button = MouseButton.WHEEL_RIGHT
    else:
        base_btn = btn_code & 3
        if base_btn == 0:
            button = MouseButton.LEFT
        elif base_btn == 1:
            button = MouseButton.MIDDLE
        elif base_btn == 2:
            button = MouseButton.RIGHT
        else:
            button = MouseButton.NONE

    return MouseMsg(
        x=col,
        y=row,
        button=button,
        action=action,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
    ), consumed


class MouseGestureTracker:
    """Tracks mouse click timing and location to detect double-click events."""

    def __init__(self, timeout: float = 0.35, max_distance: int = 1) -> None:
        self.timeout = timeout
        self.max_distance = max_distance
        self.last_click_time: float = 0.0
        self.last_click_x: int = -999
        self.last_click_y: int = -999
        self.last_click_btn: MouseButton = MouseButton.NONE

    def process(self, msg: MouseMsg, current_time: float | None = None) -> MouseMsg:
        """Process incoming MouseMsg. If a second PRESS occurs quickly at the same position, return DOUBLE_CLICK."""
        if msg.action != MouseAction.PRESS:
            return msg

        import time
        now = time.monotonic() if current_time is None else current_time
        dt = now - self.last_click_time
        dx = abs(msg.x - self.last_click_x)
        dy = abs(msg.y - self.last_click_y)

        is_double = (
            dt <= self.timeout
            and dx <= self.max_distance
            and dy <= self.max_distance
            and msg.button == self.last_click_btn
            and msg.button in (MouseButton.LEFT, MouseButton.RIGHT, MouseButton.MIDDLE)
        )

        if is_double:
            self.last_click_time = 0.0
            return MouseMsg(
                x=msg.x,
                y=msg.y,
                button=msg.button,
                action=MouseAction.DOUBLE_CLICK,
                ctrl=msg.ctrl,
                alt=msg.alt,
                shift=msg.shift,
            )

        self.last_click_time = now
        self.last_click_x = msg.x
        self.last_click_y = msg.y
        self.last_click_btn = msg.button
        return msg

