"""Table component for structured data presentation with row selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class Column:
    """Table column definition."""

    title: str
    width: int
    align: Align = Align.LEFT


class Table(Model):
    """Data table with navigable row selection."""

    def __init__(
        self,
        columns: Sequence[Column],
        rows: Sequence[Sequence[str]],
        height: int = 10,
        selected_style: Style | None = None,
        header_style: Style | None = None,
    ) -> None:
        self.columns = list(columns)
        self.rows = [list(r) for r in rows]
        self.height = height
        self.cursor = 0
        self.y_offset = 0

        self.selected_style = selected_style or Style().bold(True).foreground("#FFFFFF").background("#7D56F4")
        self.header_style = header_style or Style().bold(True).foreground("#E056FD")

    def init(self) -> Cmd | None:
        """Initialize component lifecycle (no-op for Table)."""
        return None

    @property
    def selected_row(self) -> Sequence[str] | None:
        """Return the currently selected row data, or None if empty."""
        if 0 <= self.cursor < len(self.rows):
            return self.rows[self.cursor]
        return None

    def update(self, msg: Msg) -> tuple[Table, Cmd | None]:
        """Navigate table rows using arrow keys (up/down) or vim bindings (k/j/g/G)."""
        match msg:
            case KeyMsg(key="up" | "k"):
                if self.cursor > 0:
                    self.cursor -= 1
                    if self.cursor < self.y_offset:
                        self.y_offset = self.cursor
                return self, None

            case KeyMsg(key="down" | "j"):
                if self.cursor < len(self.rows) - 1:
                    self.cursor += 1
                    if self.cursor >= self.y_offset + self.height:
                        self.y_offset = self.cursor - self.height + 1
                return self, None

            case KeyMsg(key="home" | "g"):
                self.cursor = 0
                self.y_offset = 0
                return self, None

            case KeyMsg(key="end" | "G"):
                if self.rows:
                    self.cursor = len(self.rows) - 1
                    self.y_offset = max(0, len(self.rows) - self.height)
                return self, None

        return self, None

    def view(self) -> str:
        """Render the styled table headers, separator, and visible body rows."""
        lines: list[str] = []

        # 1. Header row
        header_cells = []
        for col in self.columns:
            w = col.width
            title = truncate_ansi(col.title, w, tail="")
            diff = max(0, w - string_width(title))
            if col.align == Align.RIGHT:
                cell = f"{' ' * diff}{title}"
            elif col.align == Align.CENTER:
                lp = diff // 2
                rp = diff - lp
                cell = f"{' ' * lp}{title}{' ' * rp}"
            else:
                cell = f"{title}{' ' * diff}"
            header_cells.append(cell)

        header_line = " │ ".join(header_cells)
        lines.append(self.header_style.render(header_line))

        # Separator row
        sep_cells = ["─" * col.width for col in self.columns]
        lines.append("─┼─".join(sep_cells))

        # 2. Body rows
        visible_rows = self.rows[self.y_offset : self.y_offset + self.height]
        for idx, row in enumerate(visible_rows):
            actual_row_idx = self.y_offset + idx
            is_selected = actual_row_idx == self.cursor

            row_cells = []
            for col_idx, col in enumerate(self.columns):
                val = row[col_idx] if col_idx < len(row) else ""
                val_trunc = truncate_ansi(val, col.width, tail="…")
                diff = max(0, col.width - string_width(val_trunc))
                if col.align == Align.RIGHT:
                    cell = f"{' ' * diff}{val_trunc}"
                elif col.align == Align.CENTER:
                    lp = diff // 2
                    rp = diff - lp
                    cell = f"{' ' * lp}{val_trunc}{' ' * rp}"
                else:
                    cell = f"{val_trunc}{' ' * diff}"
                row_cells.append(cell)

            line_text = " │ ".join(row_cells)
            if is_selected:
                lines.append(self.selected_style.render(line_text))
            else:
                lines.append(line_text)

        return "\n".join(lines)
