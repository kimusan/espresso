"""Draggable and resizable Splitter container component."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg, batch
from espresso.crema.layout import Align, join_horizontal, join_vertical
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


class SplitterOrientation(Enum):
    """Orientation of the split divider."""

    HORIZONTAL = "horizontal"  # Left and Right panes separated by a vertical divider bar
    VERTICAL = "vertical"      # Top and Bottom panes separated by a horizontal divider bar


@dataclass(frozen=True)
class SplitterResizeMsg(Msg):
    """Message emitted whenever the splitter divider is moved."""

    ratio: float
    pane1_size: int
    pane2_size: int
    orientation: SplitterOrientation


class Splitter(Model):
    """A dual-pane container separated by an interactive, draggable divider bar.

    Supports mouse drag-and-drop resizing, keyboard navigation, min/max pane
    size constraints, and automatic delegation of child Model events.
    """

    def __init__(
        self,
        pane1: Model | str | Callable[[], str],
        pane2: Model | str | Callable[[], str],
        orientation: SplitterOrientation = SplitterOrientation.HORIZONTAL,
        width: int = 80,
        height: int = 24,
        ratio: float = 0.5,
        min_pane1: int = 5,
        min_pane2: int = 5,
        divider_char: str | None = None,
        divider_handle: str | None = None,
        divider_style: Style | None = None,
        active_divider_style: Style | None = None,
    ) -> None:
        self.pane1 = pane1
        self.pane2 = pane2
        self.orientation = orientation
        self.width = max(10, width)
        self.height = max(4, height)
        self.min_pane1 = max(1, min_pane1)
        self.min_pane2 = max(1, min_pane2)
        self.ratio = max(0.05, min(0.95, ratio))
        self.is_dragging: bool = False
        self.is_focused: bool = True

        if divider_char is not None:
            self.divider_char = divider_char
        else:
            self.divider_char = "│" if self.orientation == SplitterOrientation.HORIZONTAL else "─"

        self.divider_handle = divider_handle or ("⋮" if self.orientation == SplitterOrientation.HORIZONTAL else "⋯")
        self.divider_style = divider_style or Style().foreground("#555577")
        self.active_divider_style = active_divider_style or Style().bold(True).foreground("#00E5FF").background("#333355")

        self._sync_children_sizes()

    @property
    def total_available(self) -> int:
        """Available units along the split dimension excluding the 1-cell divider."""
        if self.orientation == SplitterOrientation.HORIZONTAL:
            return max(self.min_pane1 + self.min_pane2, self.width - 1)
        return max(self.min_pane1 + self.min_pane2, self.height - 1)

    @property
    def pane1_size(self) -> int:
        """Calculated width or height of the first pane."""
        avail = self.total_available
        size = int(round(avail * self.ratio))
        return max(self.min_pane1, min(size, avail - self.min_pane2))

    @property
    def pane2_size(self) -> int:
        """Calculated width or height of the second pane."""
        return max(self.min_pane2, self.total_available - self.pane1_size)

    @property
    def divider_position(self) -> int:
        """0-indexed coordinate of the divider bar."""
        return self.pane1_size

    def set_ratio(self, ratio: float) -> Cmd | None:
        """Update ratio with clamping and notify child models."""
        self.ratio = max(0.05, min(0.95, ratio))
        # Ensure constrained by min sizes
        avail = self.total_available
        size = max(self.min_pane1, min(int(round(avail * self.ratio)), avail - self.min_pane2))
        self.ratio = size / max(1, avail)
        self._sync_children_sizes()

        p1, p2, o = self.pane1_size, self.pane2_size, self.orientation
        r = self.ratio

        def _emit() -> Msg:
            return SplitterResizeMsg(ratio=r, pane1_size=p1, pane2_size=p2, orientation=o)

        return _emit

    def set_position(self, pos: int) -> Cmd | None:
        """Set divider position directly in cells."""
        avail = self.total_available
        clamped = max(self.min_pane1, min(pos, avail - self.min_pane2))
        return self.set_ratio(clamped / max(1, avail))

    def set_size(self, width: int, height: int) -> None:
        """Resize the splitter and update child pane dimensions."""
        self.width = max(10, width)
        self.height = max(4, height)
        self._sync_children_sizes()

    def _sync_children_sizes(self) -> None:
        """Notify child components of their allocated bounds."""
        p1 = self.pane1_size
        p2 = self.pane2_size

        if self.orientation == SplitterOrientation.HORIZONTAL:
            w1, h1 = p1, self.height
            w2, h2 = p2, self.height
        else:
            w1, h1 = self.width, p1
            w2, h2 = self.width, p2

        for pane, (w, h) in [(self.pane1, (w1, h1)), (self.pane2, (w2, h2))]:
            if hasattr(pane, "set_size") and callable(pane.set_size):
                pane.set_size(w, h)
            elif hasattr(pane, "width") and hasattr(pane, "height"):
                pane.width = w
                pane.height = h

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        if isinstance(self.pane1, Model):
            c1 = self.pane1.init()
            if c1:
                cmds.append(c1)
        if isinstance(self.pane2, Model):
            c2 = self.pane2.init()
            if c2:
                cmds.append(c2)
        return batch(*cmds) if cmds else None

    def update(self, msg: Msg) -> tuple[Splitter, Cmd | None]:
        """Process keyboard arrow navigation, mouse dragging, and delegate to children."""
        resize_cmd: Cmd | None = None

        if isinstance(msg, MouseMsg):
            div_pos = self.divider_position
            target_coord = msg.x if self.orientation == SplitterOrientation.HORIZONTAL else msg.y

            if msg.action == MouseAction.PRESS and msg.button == MouseButton.LEFT:
                # Click directly on divider bar
                if target_coord == div_pos:
                    self.is_dragging = True
                    return self, None

            elif msg.action == MouseAction.MOTION:
                if self.is_dragging:
                    resize_cmd = self.set_position(target_coord)
                    return self, resize_cmd

            elif msg.action == MouseAction.RELEASE:
                if self.is_dragging:
                    self.is_dragging = False
                    return self, None

        elif isinstance(msg, KeyMsg) and self.is_focused:
            step = 5 if (msg.key.ctrl or msg.key.alt) else 1
            if self.orientation == SplitterOrientation.HORIZONTAL:
                match msg.key:
                    case "left" | "h":
                        resize_cmd = self.set_position(self.pane1_size - step)
                        return self, resize_cmd
                    case "right" | "l":
                        resize_cmd = self.set_position(self.pane1_size + step)
                        return self, resize_cmd
                    case "=" | "r":
                        resize_cmd = self.set_ratio(0.5)
                        return self, resize_cmd
            else:
                match msg.key:
                    case "up" | "k":
                        resize_cmd = self.set_position(self.pane1_size - step)
                        return self, resize_cmd
                    case "down" | "j":
                        resize_cmd = self.set_position(self.pane1_size + step)
                        return self, resize_cmd
                    case "=" | "r":
                        resize_cmd = self.set_ratio(0.5)
                        return self, resize_cmd

        # Forward unhandled events to child models
        child_cmds: list[Cmd] = []
        if isinstance(self.pane1, Model):
            self.pane1, c1 = self.pane1.update(msg)
            if c1:
                child_cmds.append(c1)
        if isinstance(self.pane2, Model):
            self.pane2, c2 = self.pane2.update(msg)
            if c2:
                child_cmds.append(c2)

        all_cmds = [c for c in [resize_cmd] + child_cmds if c is not None]
        return self, batch(*all_cmds) if all_cmds else None

    def _render_pane(self, pane: Model | str | Callable[[], str], target_w: int, target_h: int) -> list[str]:
        """Render a pane and format it to exact target_w and target_h lines."""
        if callable(pane) and not isinstance(pane, Model):
            raw = str(pane())
        elif isinstance(pane, Model):
            raw = pane.view()
        else:
            raw = str(pane)

        raw_lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n") if raw else [""]
        out_lines: list[str] = []

        for line in raw_lines[:target_h]:
            w = string_width(line)
            if w > target_w:
                out_lines.append(truncate_ansi(line, target_w))
            else:
                out_lines.append(f"{line}{' ' * (target_w - w)}")

        blank = " " * target_w
        while len(out_lines) < target_h:
            out_lines.append(blank)

        return out_lines

    def view(self) -> str:
        """Render the composite split layout with interactive divider."""
        d_style = self.active_divider_style if self.is_dragging else self.divider_style
        p1 = self.pane1_size
        p2 = self.pane2_size

        if self.orientation == SplitterOrientation.HORIZONTAL:
            lines1 = self._render_pane(self.pane1, p1, self.height)
            lines2 = self._render_pane(self.pane2, p2, self.height)

            # Build vertical divider column with centered handle
            mid_y = self.height // 2
            divider_lines: list[str] = []
            for y in range(self.height):
                char = self.divider_handle if (y == mid_y and self.divider_handle) else self.divider_char
                divider_lines.append(d_style.render(char))

            rows: list[str] = []
            for y in range(self.height):
                rows.append(f"{lines1[y]}{divider_lines[y]}{lines2[y]}")
            return "\n".join(rows)

        else:
            lines1 = self._render_pane(self.pane1, self.width, p1)
            lines2 = self._render_pane(self.pane2, self.width, p2)

            # Build horizontal divider row with centered handle
            mid_x = self.width // 2
            if self.divider_handle and self.width >= 3:
                left_len = mid_x - (len(self.divider_handle) // 2)
                right_len = max(0, self.width - left_len - len(self.divider_handle))
                div_str = (self.divider_char * left_len) + self.divider_handle + (self.divider_char * right_len)
            else:
                div_str = self.divider_char * self.width

            divider_line = d_style.render(div_str)
            all_lines = lines1 + [divider_line] + lines2
            return "\n".join(all_lines)
