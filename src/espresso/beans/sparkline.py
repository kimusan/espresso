"""Real-time streaming Sparkline component with Braille 2D curves and Block bar rendering."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.gradient import multi_gradient_colors
from espresso.crema.style import Style
from espresso.crema.width import string_width

BLOCK_BARS = (" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")

# Braille dot bitmasks for a 2-column by 4-row matrix per character
# Col 0: row 0=0x01, row 1=0x02, row 2=0x04, row 3=0x40
# Col 1: row 0=0x08, row 1=0x10, row 2=0x20, row 3=0x80
BRAILLE_MASKS: list[list[int]] = [
    [0x01, 0x08],  # row 0 (top)
    [0x02, 0x10],  # row 1
    [0x04, 0x20],  # row 2
    [0x40, 0x80],  # row 3 (bottom)
]


class SparklineMode(Enum):
    """Visual rendering mode of the sparkline."""

    BLOCK = "block"      # 8 vertical bar levels:  ▂▃▄▅▆▇█
    BRAILLE = "braille"  # High-resolution 2D sub-cell dot curve


@dataclass(frozen=True)
class SparklineTickMsg(Msg):
    """Message emitted on timer tick for animated live data streaming."""

    tag: str = "sparkline"


class Sparkline(Model):
    """Real-time streaming chart component for metrics, telemetry, and live feeds."""

    def __init__(
        self,
        data: Sequence[float] | None = None,
        width: int = 30,
        height: int = 1,
        mode: SparklineMode = SparklineMode.BRAILLE,
        min_val: float | None = None,
        max_val: float | None = None,
        label: str = "",
        show_stats: bool = True,
        show_trend: bool = True,
        style: Style | None = None,
        label_style: Style | None = None,
        stats_style: Style | None = None,
        gradient_stops: list[str] | None = None,
        tag: str = "sparkline",
    ) -> None:
        self.width = max(10, width)
        self.height = max(1, height)
        self.mode = mode
        self.min_val = min_val
        self.max_val = max_val
        self.label = label
        self.show_stats = show_stats
        self.show_trend = show_trend
        self.tag = tag

        self.style = style or Style().foreground("#00E5FF")
        self.label_style = label_style or Style().bold(True).foreground("#FFFFFF")
        self.stats_style = stats_style or Style().foreground("#8888AA")
        self.gradient_stops = gradient_stops

        self._data: list[float] = list(data or [])
        self._prune_data()

    @property
    def capacity(self) -> int:
        """Maximum number of horizontal points visible."""
        chart_w = self._chart_width()
        return chart_w * (2 if self.mode == SparklineMode.BRAILLE else 1)

    def _chart_width(self) -> int:
        """Width allocated strictly to the chart glyphs."""
        label_w = string_width(self.label) + 1 if self.label else 0
        stats_w = 0
        if self.show_stats:
            stats_w = 12  # rough reservation for "Cur: 100 ↗"
        return max(5, self.width - label_w - stats_w)

    def _prune_data(self) -> None:
        cap = self.capacity
        if len(self._data) > cap:
            self._data = self._data[-cap:]

    @property
    def data(self) -> list[float]:
        return list(self._data)

    def set_data(self, data: Sequence[float]) -> None:
        self._data = list(data)
        self._prune_data()

    def push(self, value: float) -> None:
        """Append a new data point and slide older data out."""
        self._data.append(value)
        self._prune_data()

    @property
    def current_value(self) -> float:
        return self._data[-1] if self._data else 0.0

    @property
    def min_value(self) -> float:
        return min(self._data) if self._data else 0.0

    @property
    def max_value(self) -> float:
        return max(self._data) if self._data else 0.0

    @property
    def average_value(self) -> float:
        return sum(self._data) / len(self._data) if self._data else 0.0

    @property
    def trend_glyph(self) -> str:
        """Return directional trend indicator."""
        if len(self._data) < 2:
            return "→"
        prev, cur = self._data[-2], self._data[-1]
        diff = cur - prev
        if diff > 0.01:
            return "↗"
        elif diff < -0.01:
            return "↘"
        return "→"

    def tick(self, interval: float = 0.5) -> Cmd:
        """Return a command that triggers a SparklineTickMsg after interval."""
        tag = self.tag
        async def _tick_async() -> Msg:
            await asyncio.sleep(interval)
            return SparklineTickMsg(tag=tag)
        return _tick_async

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Sparkline, Cmd | None]:
        return self, None

    def _render_block_chart(self, chart_w: int) -> list[str]:
        """Render 1D or multi-row block bar sparkline."""
        if not self._data:
            return [" " * chart_w] * self.height

        lo = self.min_val if self.min_val is not None else min(self._data)
        hi = self.max_val if self.max_val is not None else max(self._data)
        span = hi - lo if hi > lo else 1.0

        # Right-aligned data slice
        pts = self._data[-chart_w:]
        pad_pts = [lo] * (chart_w - len(pts)) + pts

        # Single row block rendering
        if self.height == 1:
            row_chars: list[str] = []
            for val in pad_pts:
                norm = max(0.0, min(1.0, (val - lo) / span))
                bar_idx = int(round(norm * 8))
                row_chars.append(BLOCK_BARS[bar_idx])
            return ["".join(row_chars)]

        # Multi-row block rendering
        rows: list[list[str]] = [[] for _ in range(self.height)]
        total_levels = self.height * 8

        for val in pad_pts:
            norm = max(0.0, min(1.0, (val - lo) / span))
            level = int(round(norm * total_levels))
            for row_idx in range(self.height):
                # row 0 is top, row H-1 is bottom
                row_from_bot = self.height - 1 - row_idx
                bot_threshold = row_from_bot * 8
                val_in_row = level - bot_threshold
                if val_in_row >= 8:
                    rows[row_idx].append(BLOCK_BARS[8])
                elif val_in_row <= 0:
                    rows[row_idx].append(" ")
                else:
                    rows[row_idx].append(BLOCK_BARS[val_in_row])

        return ["".join(r) for r in rows]

    def _render_braille_chart(self, chart_w: int) -> list[str]:
        """Render high-resolution sub-cell dot curve using Unicode Braille patterns."""
        total_sub_cols = chart_w * 2
        total_sub_rows = self.height * 4

        if not self._data:
            return [" " * chart_w] * self.height

        lo = self.min_val if self.min_val is not None else min(self._data)
        hi = self.max_val if self.max_val is not None else max(self._data)
        span = hi - lo if hi > lo else 1.0

        pts = self._data[-total_sub_cols:]
        pad_pts = [lo] * (total_sub_cols - len(pts)) + pts

        # Grid of braille cell masks: [char_row][char_col] -> bitmask
        grid = [[0 for _ in range(chart_w)] for _ in range(self.height)]

        for sub_col, val in enumerate(pad_pts):
            char_col = sub_col // 2
            dot_col = sub_col % 2

            norm = max(0.0, min(1.0, (val - lo) / span))
            # Sub row from bottom (0 = lowest, total_sub_rows-1 = highest)
            sub_row_from_bot = int(round(norm * (total_sub_rows - 1)))
            sub_row_from_top = total_sub_rows - 1 - sub_row_from_bot

            char_row = sub_row_from_top // 4
            dot_row = sub_row_from_top % 4

            if 0 <= char_row < self.height and 0 <= char_col < chart_w:
                grid[char_row][char_col] |= BRAILLE_MASKS[dot_row][dot_col]

        # Convert bitmasks to Unicode Braille characters
        out_rows: list[str] = []
        for r in range(self.height):
            line_chars: list[str] = []
            for c in range(chart_w):
                mask = grid[r][c]
                line_chars.append(chr(0x2800 + mask) if mask > 0 else " ")
            out_rows.append("".join(line_chars))

        return out_rows

    def view(self) -> str:
        """Render the complete sparkline view including label, chart curve, and metrics badge."""
        chart_w = self._chart_width()

        if self.mode == SparklineMode.BRAILLE:
            chart_rows = self._render_braille_chart(chart_w)
        else:
            chart_rows = self._render_block_chart(chart_w)

        # Style chart rows with gradient or solid style
        styled_chart_rows: list[str] = []
        if self.gradient_stops and self.height > 1:
            row_colors = multi_gradient_colors(self.gradient_stops, self.height)
            for idx, r in enumerate(chart_rows):
                styled_chart_rows.append(Style().foreground(row_colors[idx]).render(r))
        else:
            for r in chart_rows:
                styled_chart_rows.append(self.style.render(r))

        # Format stats badge
        stats_part = ""
        if self.show_stats:
            trend = f" {self.trend_glyph}" if self.show_trend else ""
            stats_str = f" {self.current_value:.1f}{trend}"
            stats_part = self.stats_style.render(stats_str)

        label_part = f"{self.label_style.render(self.label)} " if self.label else ""

        # For single row
        if self.height == 1:
            return f"{label_part}{styled_chart_rows[0]}{stats_part}"

        # For multi-row: vertically center the label and badge
        mid_y = self.height // 2
        blank_label = " " * string_width(label_part)
        blank_stats = " " * string_width(stats_part)

        final_lines: list[str] = []
        for y in range(self.height):
            l_prefix = label_part if y == mid_y else blank_label
            s_suffix = stats_part if y == mid_y else blank_stats
            final_lines.append(f"{l_prefix}{styled_chart_rows[y]}{s_suffix}")

        return "\n".join(final_lines)
