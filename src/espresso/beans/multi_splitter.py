"""Multi-pane resizable layout component supporting 3 or more panes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from espresso.beans.splitter import SplitterOrientation
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg, batch
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class MultiSplitterResizeMsg(Msg):
    """Message emitted whenever a divider in the multi-splitter is adjusted."""

    divider_index: int
    sizes: list[int]
    ratios: list[float]
    orientation: SplitterOrientation


class MultiSplitter(Model):
    """A multi-pane container supporting 3 or more resizable panes with draggable dividers.

    Supports mouse drag-and-drop resizing across independent dividers, keyboard nudging,
    minimum pane size constraints, proportional terminal resizing, and child event forwarding.
    """

    def __init__(
        self,
        panes: list[Model | str | Callable[[], str]],
        ratios: list[float] | None = None,
        min_sizes: list[int] | None = None,
        orientation: SplitterOrientation = SplitterOrientation.HORIZONTAL,
        width: int = 80,
        height: int = 24,
        divider_char: str | None = None,
        divider_handle: str | None = None,
        divider_style: Style | None = None,
        active_divider_style: Style | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        self.panes = list(panes)
        self.orientation = orientation
        self.width = max(10, width)
        self.height = max(4, height)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.is_dragging: bool = False
        self.active_divider_idx: int = 0
        self.is_focused: bool = True

        n = len(self.panes)
        if min_sizes is not None and len(min_sizes) == n:
            self.min_sizes = [max(1, s) for s in min_sizes]
        else:
            self.min_sizes = [5] * n

        if ratios is not None and len(ratios) == n:
            tot = sum(ratios)
            self.ratios = [r / tot for r in ratios] if tot > 0 else [1.0 / max(1, n)] * n
        else:
            self.ratios = [1.0 / max(1, n)] * n

        if divider_char is not None:
            self.divider_char = divider_char
        else:
            self.divider_char = "│" if self.orientation == SplitterOrientation.HORIZONTAL else "─"

        if divider_handle is not None:
            self.divider_handle = divider_handle
        else:
            self.divider_handle = "⋮" if self.orientation == SplitterOrientation.HORIZONTAL else "⋯"

        self.divider_style = divider_style or Style().foreground("#555577")
        self.active_divider_style = active_divider_style or Style().bold(True).foreground("#00E5FF").background("#333355")

        self._sync_children_sizes()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset coordinates (column, row) for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    @property
    def num_panes(self) -> int:
        return len(self.panes)

    @property
    def num_dividers(self) -> int:
        return max(0, len(self.panes) - 1)

    @property
    def total_available(self) -> int:
        """Available units along the split dimension excluding divider cells."""
        n_divs = self.num_dividers
        min_total = sum(self.min_sizes)
        dim = self.width if self.orientation == SplitterOrientation.HORIZONTAL else self.height
        return max(min_total, dim - n_divs)

    @property
    def pane_sizes(self) -> list[int]:
        """Calculated width or height for each pane."""
        n = self.num_panes
        if n == 0:
            return []
        if n == 1:
            return [self.total_available]

        avail = self.total_available
        raw = [int(round(avail * r)) for r in self.ratios]
        sizes = [max(self.min_sizes[i], raw[i]) for i in range(n)]

        diff = avail - sum(sizes)
        while diff != 0:
            if diff > 0:
                best_idx = max(range(n), key=lambda i: self.ratios[i])
                sizes[best_idx] += 1
                diff -= 1
            else:
                reducible = [i for i in range(n) if sizes[i] > self.min_sizes[i]]
                if not reducible:
                    break
                best_idx = max(reducible, key=lambda i: sizes[i])
                sizes[best_idx] -= 1
                diff += 1

        return sizes

    def pane_start(self, index: int) -> int:
        """Starting cell coordinate (0-indexed) for pane at index."""
        sizes = self.pane_sizes
        return sum(sizes[:index]) + index

    def divider_position(self, divider_idx: int) -> int:
        """Coordinate of divider separating pane divider_idx and divider_idx + 1."""
        sizes = self.pane_sizes
        return sum(sizes[: divider_idx + 1]) + divider_idx

    def set_size(self, width: int, height: int) -> None:
        """Resize the multi-splitter and proportionally update child pane dimensions."""
        self.width = max(10, width)
        self.height = max(4, height)
        self._sync_children_sizes()

    def _sync_children_sizes(self) -> None:
        """Notify child components of their allocated bounds."""
        sizes = self.pane_sizes
        for i, pane in enumerate(self.panes):
            if i >= len(sizes):
                break
            sz = sizes[i]
            if self.orientation == SplitterOrientation.HORIZONTAL:
                pw, ph = sz, self.height
            else:
                pw, ph = self.width, sz

            if hasattr(pane, "set_size") and callable(pane.set_size):
                pane.set_size(pw, ph)
            elif hasattr(pane, "width") and hasattr(pane, "height"):
                pane.width = pw
                pane.height = ph

            if hasattr(pane, "set_offset") and callable(pane.set_offset):
                pane.set_offset(0, 0)

    def nudge_divider(self, divider_idx: int, delta: int) -> Cmd | None:
        """Nudge divider position by delta cells while respecting min_sizes."""
        if self.num_dividers == 0 or not (0 <= divider_idx < self.num_dividers):
            return None

        sizes = self.pane_sizes
        combined = sizes[divider_idx] + sizes[divider_idx + 1]
        min_a = self.min_sizes[divider_idx]
        min_b = self.min_sizes[divider_idx + 1]

        new_a = sizes[divider_idx] + delta
        new_a = max(min_a, min(new_a, combined - min_b))
        new_b = combined - new_a

        sizes[divider_idx] = new_a
        sizes[divider_idx + 1] = new_b

        avail = max(1, self.total_available)
        self.ratios = [sz / avail for sz in sizes]
        self._sync_children_sizes()

        idx = divider_idx
        sz_copy = list(sizes)
        rat_copy = list(self.ratios)
        ori = self.orientation

        return lambda: MultiSplitterResizeMsg(
            divider_index=idx, sizes=sz_copy, ratios=rat_copy, orientation=ori
        )

    def set_divider_position(self, divider_idx: int, target_coord: int) -> Cmd | None:
        """Move divider directly to target_coord cell within component bounds."""
        if self.num_dividers == 0 or not (0 <= divider_idx < self.num_dividers):
            return None

        start_a = self.pane_start(divider_idx)
        current_a = self.pane_sizes[divider_idx]
        desired_a = target_coord - start_a
        delta = desired_a - current_a
        return self.nudge_divider(divider_idx, delta)

    def set_ratios(self, ratios: list[float]) -> Cmd | None:
        """Set split ratios and notify child models."""
        n = self.num_panes
        if len(ratios) == n and sum(ratios) > 0:
            tot = sum(ratios)
            self.ratios = [r / tot for r in ratios]
            self._sync_children_sizes()
            sz_copy = list(self.pane_sizes)
            rat_copy = list(self.ratios)
            ori = self.orientation
            return lambda: MultiSplitterResizeMsg(
                divider_index=self.active_divider_idx,
                sizes=sz_copy,
                ratios=rat_copy,
                orientation=ori,
            )
        return None

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        for pane in self.panes:
            if isinstance(pane, Model):
                c = pane.init()
                if c:
                    cmds.append(c)
        return batch(*cmds) if cmds else None

    def update(self, msg: Msg) -> tuple[MultiSplitter, Cmd | None]:
        """Process keyboard navigation, mouse dragging, and delegate to children."""
        resize_cmd: Cmd | None = None

        if isinstance(msg, MouseMsg):
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            target_coord = local_x if self.orientation == SplitterOrientation.HORIZONTAL else local_y
            other_coord = local_y if self.orientation == SplitterOrientation.HORIZONTAL else local_x
            max_other = self.height if self.orientation == SplitterOrientation.HORIZONTAL else self.width

            # 1. Mouse Wheel on Dividers
            if msg.button in (MouseButton.WHEEL_UP, MouseButton.WHEEL_DOWN) and 0 <= other_coord < max_other:
                for d_idx in range(self.num_dividers):
                    d_pos = self.divider_position(d_idx)
                    if abs(target_coord - d_pos) <= 1:
                        step = -1 if msg.button == MouseButton.WHEEL_UP else 1
                        return self, self.nudge_divider(d_idx, step)

            # 2. Double-Click on Divider resets adjacent panes to equal split
            if msg.action == MouseAction.DOUBLE_CLICK and msg.button == MouseButton.LEFT:
                if 0 <= other_coord < max_other:
                    for d_idx in range(self.num_dividers):
                        d_pos = self.divider_position(d_idx)
                        if abs(target_coord - d_pos) <= 1:
                            sizes = self.pane_sizes
                            combined = sizes[d_idx] + sizes[d_idx + 1]
                            half = combined // 2
                            delta = half - sizes[d_idx]
                            return self, self.nudge_divider(d_idx, delta)

            # 3. Right-Click on Divider equalizes all ratios
            if msg.button == MouseButton.RIGHT and msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                if 0 <= other_coord < max_other:
                    for d_idx in range(self.num_dividers):
                        d_pos = self.divider_position(d_idx)
                        if abs(target_coord - d_pos) <= 1:
                            n = max(1, self.num_panes)
                            return self, self.set_ratios([1.0 / n] * n)

            # 4. Left-Press on Divider begins drag
            if msg.action == MouseAction.PRESS and msg.button == MouseButton.LEFT:
                if 0 <= other_coord < max_other:
                    for d_idx in range(self.num_dividers):
                        d_pos = self.divider_position(d_idx)
                        if abs(target_coord - d_pos) <= 1:
                            self.is_dragging = True
                            self.active_divider_idx = d_idx
                            resize_cmd = self.set_divider_position(d_idx, target_coord)
                            return self, resize_cmd

            # 5. Motion updates dragged divider position
            elif msg.action == MouseAction.MOTION:
                if self.is_dragging and 0 <= self.active_divider_idx < self.num_dividers:
                    resize_cmd = self.set_divider_position(self.active_divider_idx, target_coord)
                    return self, resize_cmd

            # 6. Release finishes drag
            elif msg.action == MouseAction.RELEASE:
                if self.is_dragging:
                    self.is_dragging = False
                    sz_copy = list(self.pane_sizes)
                    rat_copy = list(self.ratios)
                    idx = self.active_divider_idx
                    ori = self.orientation
                    return self, lambda: MultiSplitterResizeMsg(
                        divider_index=idx, sizes=sz_copy, ratios=rat_copy, orientation=ori
                    )

            # 7. Delegate unhandled mouse events (clicks, wheel, hover) to child panes
            if not self.is_dragging:
                sizes = self.pane_sizes
                child_cmds: list[Cmd] = []
                for i, pane in enumerate(self.panes):
                    if not isinstance(pane, Model):
                        continue
                    p_start = self.pane_start(i)
                    p_sz = sizes[i] if i < len(sizes) else 0

                    if self.orientation == SplitterOrientation.HORIZONTAL:
                        if p_start <= local_x < p_start + p_sz and 0 <= local_y < self.height:
                            pane_msg = msg.relative_to(self.offset_x + p_start, self.offset_y)
                            self.panes[i], c = pane.update(pane_msg)
                            if c:
                                child_cmds.append(c)
                    else:
                        if p_start <= local_y < p_start + p_sz and 0 <= local_x < self.width:
                            pane_msg = msg.relative_to(self.offset_x, self.offset_y + p_start)
                            self.panes[i], c = pane.update(pane_msg)
                            if c:
                                child_cmds.append(c)

                return self, batch(*child_cmds) if child_cmds else None

        elif isinstance(msg, KeyMsg) and self.is_focused:
            k = str(msg.key).lower()
            step = 5 if (msg.key.ctrl or msg.key.alt) else 1

            # Tab or Shift+Tab cycles active divider
            if k == "tab":
                if self.num_dividers > 0:
                    self.active_divider_idx = (self.active_divider_idx + 1) % self.num_dividers
                return self, None
            if k in ("shift+tab", "backtab"):
                if self.num_dividers > 0:
                    self.active_divider_idx = (self.active_divider_idx - 1) % self.num_dividers
                return self, None

            # Number keys '1'..'9' directly select divider
            if k.isdigit() and 1 <= int(k) <= self.num_dividers:
                self.active_divider_idx = int(k) - 1
                return self, None

            # Equalize
            if k in ("=", "r"):
                n = max(1, self.num_panes)
                return self, self.set_ratios([1.0 / n] * n)

            # Resizing nudges
            if self.orientation == SplitterOrientation.HORIZONTAL:
                if k in ("left", "h", "ctrl+left", "alt+left"):
                    return self, self.nudge_divider(self.active_divider_idx, -step)
                if k in ("right", "l", "ctrl+right", "alt+right"):
                    return self, self.nudge_divider(self.active_divider_idx, step)
            else:
                if k in ("up", "k", "ctrl+up", "alt+up"):
                    return self, self.nudge_divider(self.active_divider_idx, -step)
                if k in ("down", "j", "ctrl+down", "alt+down"):
                    return self, self.nudge_divider(self.active_divider_idx, step)

        # Delegate unhandled messages to child models
        child_cmds = []
        for i, pane in enumerate(self.panes):
            if isinstance(pane, Model):
                self.panes[i], c = pane.update(msg)
                if c:
                    child_cmds.append(c)

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
        """Render the composite multi-split layout with interactive dividers."""
        n = self.num_panes
        if n == 0:
            return ""

        sizes = self.pane_sizes

        if self.orientation == SplitterOrientation.HORIZONTAL:
            rendered_panes = [
                self._render_pane(self.panes[i], sizes[i], self.height) for i in range(n)
            ]

            mid_y = self.height // 2
            divider_cols: list[list[str]] = []
            for d_idx in range(self.num_dividers):
                is_active = (d_idx == self.active_divider_idx) and (self.is_dragging or self.is_focused)
                style = self.active_divider_style if is_active else self.divider_style
                col: list[str] = []
                for y in range(self.height):
                    ch = self.divider_handle if (y == mid_y and self.divider_handle) else self.divider_char
                    col.append(style.render(ch))
                divider_cols.append(col)

            rows: list[str] = []
            for y in range(self.height):
                row_parts: list[str] = []
                for i in range(n):
                    row_parts.append(rendered_panes[i][y])
                    if i < self.num_dividers:
                        row_parts.append(divider_cols[i][y])
                rows.append("".join(row_parts))

            return "\n".join(rows)

        else:
            rendered_panes = [
                self._render_pane(self.panes[i], self.width, sizes[i]) for i in range(n)
            ]

            mid_x = self.width // 2
            divider_rows: list[str] = []
            for d_idx in range(self.num_dividers):
                is_active = (d_idx == self.active_divider_idx) and (self.is_dragging or self.is_focused)
                style = self.active_divider_style if is_active else self.divider_style

                if self.divider_handle and self.width >= 3:
                    left_len = mid_x - (len(self.divider_handle) // 2)
                    right_len = max(0, self.width - left_len - len(self.divider_handle))
                    div_str = (self.divider_char * left_len) + self.divider_handle + (self.divider_char * right_len)
                else:
                    div_str = self.divider_char * self.width
                divider_rows.append(style.render(div_str))

            all_lines: list[str] = []
            for i in range(n):
                all_lines.extend(rendered_panes[i])
                if i < self.num_dividers:
                    all_lines.append(divider_rows[i])

            return "\n".join(all_lines)
