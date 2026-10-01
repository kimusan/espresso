"""Bar chart bean with horizontal & vertical modes, auto-scaling, and TrueColor gradients.

Inspired by rich, asciigraph, and modern terminal analytics dashboards.
Supports sub-character precision bar rendering, TrueColor linear/multi-gradients,
interactive cursor navigation, value formatters, and mouse selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.gradient import multi_gradient_colors
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, strip_ansi, truncate_ansi

# Unicode fractional blocks for horizontal sub-character precision
HORIZ_BLOCKS = (" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█")

# Unicode vertical blocks for vertical columns
VERT_BLOCKS = (" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")


class BarOrientation(str, Enum):
    """Orientation of the bar chart."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class BarItem:
    """An individual data point/bar in the chart."""

    label: str
    value: float
    color: str | None = None
    formatter: Callable[[float], str] | None = None


@dataclass(frozen=True)
class BarChartSelectMsg(Msg):
    """Emitted when a bar is selected in the BarChart."""

    item: BarItem
    index: int


class BarChart(Model):
    """Interactive bar chart component with auto-scaling and TrueColor styling."""

    def __init__(
        self,
        items: Sequence[BarItem] = (),
        title: str = "Bar Chart",
        orientation: BarOrientation = BarOrientation.HORIZONTAL,
        width: int = 44,
        height: int = 12,
        min_value: float = 0.0,
        max_value: float | None = None,
        gradient_colors: tuple[str, ...] = ("#00E5FF", "#7D56F4", "#F7768E"),
        show_values: bool = True,
        show_labels: bool = True,
        cursor_enabled: bool = True,
        border_color: str = "#7D56F4",
    ) -> None:
        self.items: list[BarItem] = list(items)
        self.title = title
        self.orientation = orientation
        self.width = max(20, width)
        self.height = max(5, height)
        self.min_value = min_value
        self.max_value = max_value
        self.gradient_colors = gradient_colors
        self.show_values = show_values
        self.show_labels = show_labels
        self.cursor_enabled = cursor_enabled
        self.border_color = border_color

        self.cursor: int = 0
        self.offset_x: int = 0
        self.offset_y: int = 0

    def set_items(self, items: Sequence[BarItem]) -> None:
        """Update chart data."""
        self.items = list(items)
        if self.cursor >= len(self.items):
            self.cursor = max(0, len(self.items) - 1)

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset for mouse hit testing."""
        self.offset_x = x
        self.offset_y = y

    def _calc_max(self) -> float:
        if self.max_value is not None:
            return self.max_value
        if not self.items:
            return 1.0
        return max((it.value for it in self.items), default=1.0) or 1.0

    def update(self, msg: Msg) -> tuple[Model, Cmd]:
        """Handle keyboard navigation and mouse interactions."""
        if not self.items:
            return self, None

        if isinstance(msg, KeyMsg):
            key = str(msg.key).lower()

            if self.orientation == BarOrientation.HORIZONTAL:
                if key in ("up", "k"):
                    self.cursor = max(0, self.cursor - 1)
                    return self, None
                elif key in ("down", "j"):
                    self.cursor = min(len(self.items) - 1, self.cursor + 1)
                    return self, None
            else:
                if key in ("left", "h"):
                    self.cursor = max(0, self.cursor - 1)
                    return self, None
                elif key in ("right", "l"):
                    self.cursor = min(len(self.items) - 1, self.cursor + 1)
                    return self, None

            if key == "enter":
                if 0 <= self.cursor < len(self.items):
                    item = self.items[self.cursor]
                    idx = self.cursor
                    return self, lambda: BarChartSelectMsg(item=item, index=idx)

        elif isinstance(msg, MouseMsg):
            rel_x = msg.x - self.offset_x
            rel_y = msg.y - self.offset_y

            if self.orientation == BarOrientation.HORIZONTAL:
                # Rows start at y=1 (inside border)
                idx = rel_y - 1
                if 0 <= idx < len(self.items):
                    if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                        self.cursor = idx
                        item = self.items[idx]
                        return self, lambda: BarChartSelectMsg(item=item, index=idx)
            else:
                pass

        return self, None

    def _render_horizontal(self, inner_w: int) -> list[str]:
        lines: list[str] = []
        max_v = self._calc_max()

        max_label_w = max((string_width(it.label) for it in self.items), default=0) if self.show_labels else 0
        max_label_w = min(max_label_w, inner_w // 3)

        # Estimate value text width
        sample_vals = [it.formatter(it.value) if it.formatter else f"{it.value:.1f}" for it in self.items]
        max_val_w = max((string_width(v) for v in sample_vals), default=0) if self.show_values else 0

        bar_space = max(5, inner_w - max_label_w - max_val_w - (3 if max_label_w else 0) - (2 if max_val_w else 0) - 2)

        grad_stops = multi_gradient_colors(self.gradient_colors, max(2, bar_space))

        for idx, it in enumerate(self.items):
            is_selected = self.cursor_enabled and idx == self.cursor

            # Label part
            if self.show_labels:
                lbl = truncate_ansi(it.label, max_label_w)
                lw = string_width(lbl)
                label_part = f"{lbl}{' ' * (max_label_w - lw)} │ "
            else:
                label_part = ""

            # Value fraction
            norm = max(0.0, min(1.0, (it.value - self.min_value) / max(0.001, (max_v - self.min_value))))
            raw_len = norm * bar_space
            full_blocks = int(raw_len)
            frac_idx = int((raw_len - full_blocks) * 8)

            bar_chars: list[str] = []
            for b_i in range(full_blocks):
                color = it.color or grad_stops[min(b_i, len(grad_stops) - 1)]
                bar_chars.append(Style().foreground(color).render("█"))

            if frac_idx > 0 and full_blocks < bar_space:
                color = it.color or grad_stops[min(full_blocks, len(grad_stops) - 1)]
                bar_chars.append(Style().foreground(color).render(HORIZ_BLOCKS[frac_idx]))
                full_blocks += 1

            # Pad empty space
            empty_space = " " * max(0, bar_space - full_blocks)
            bar_part = "".join(bar_chars) + empty_space

            # Value part
            if self.show_values:
                v_str = it.formatter(it.value) if it.formatter else f"{it.value:.1f}"
                val_part = f" {Style().bold(True).render(v_str)}"
            else:
                val_part = ""

            prefix = "› " if is_selected else "  "
            pref_st = Style().foreground("#00E5FF").bold(True).render(prefix) if is_selected else prefix

            row = f"{pref_st}{label_part}{bar_part}{val_part}"
            row = truncate_ansi(row, inner_w)
            rw = string_width(row)
            if rw < inner_w:
                row += " " * (inner_w - rw)

            if is_selected:
                row = Style().background("#2A2A3D").render(row)

            lines.append(row)

        return lines

    def _render_vertical(self, inner_w: int) -> list[str]:
        lines: list[str] = []
        max_v = self._calc_max()
        # Reserved height: 1 for x-axis line, 1 for labels
        chart_h = max(2, self.height - 4)

        if not self.items:
            return [" " * inner_w] * chart_h

        col_w = max(2, inner_w // len(self.items))
        grad_stops = multi_gradient_colors(self.gradient_colors, max(2, chart_h))

        grid: list[list[str]] = [[" " * col_w for _ in self.items] for _ in range(chart_h)]

        for col_idx, it in enumerate(self.items):
            norm = max(0.0, min(1.0, (it.value - self.min_value) / max(0.001, (max_v - self.min_value))))
            raw_h = norm * chart_h
            full_blocks = int(raw_h)
            frac_idx = int((raw_h - full_blocks) * 8)

            for h in range(full_blocks):
                row_idx = chart_h - 1 - h
                color = it.color or grad_stops[min(h, len(grad_stops) - 1)]
                grid[row_idx][col_idx] = Style().foreground(color).render("█" * (col_w - 1) + " ")

            if frac_idx > 0 and full_blocks < chart_h:
                row_idx = chart_h - 1 - full_blocks
                color = it.color or grad_stops[min(full_blocks, len(grad_stops) - 1)]
                block_ch = VERT_BLOCKS[frac_idx]
                grid[row_idx][col_idx] = Style().foreground(color).render((block_ch * (col_w - 1)) + " ")

        for row in grid:
            r_str = "".join(row)
            r_w = string_width(r_str)
            if r_w < inner_w:
                r_str += " " * (inner_w - r_w)
            lines.append(r_str)

        # Axis line
        lines.append(Style().foreground("#555555").render("─" * inner_w))

        # Labels line
        lbl_parts: list[str] = []
        for i, it in enumerate(self.items):
            is_sel = self.cursor_enabled and i == self.cursor
            lbl = truncate_ansi(it.label, col_w - 1)
            lw = string_width(lbl)
            padded = lbl + (" " * (col_w - lw))
            if is_sel:
                padded = Style().foreground("#00E5FF").bold(True).render(padded)
            lbl_parts.append(padded)
        l_row = "".join(lbl_parts)
        l_w = string_width(l_row)
        if l_w < inner_w:
            l_row += " " * (inner_w - l_w)
        lines.append(l_row)

        return lines

    def view(self) -> str:
        """Render the bar chart."""
        inner_w = self.width - 2

        if self.orientation == BarOrientation.HORIZONTAL:
            lines = self._render_horizontal(inner_w)
        else:
            lines = self._render_vertical(inner_w)

        # Pad height
        while len(lines) < self.height - 2:
            lines.append(" " * inner_w)

        border_st = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(self.border_color)
            .border_title(f" {self.title} " if self.title else None)
            .width(inner_w)
        )
        return border_st.render("\n".join(lines))
