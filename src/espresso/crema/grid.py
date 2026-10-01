"""Declarative responsive Grid and multi-column layout engine for Crema."""

from __future__ import annotations

import math
from typing import Sequence

from espresso.crema.border import Border, ROUNDED_BORDER
from espresso.crema.layout import join_horizontal, join_vertical
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


class Grid:
    """Declarative terminal grid layout composer."""

    @staticmethod
    def columns(
        cards: Sequence[str],
        cols: int = 2,
        col_widths: Sequence[int] | None = None,
        gap: int = 1,
        total_width: int | None = None,
    ) -> str:
        """Lay out items in a multi-column grid with configurable gap spacing.

        Args:
            cards: List of rendered multi-line string cells.
            cols: Number of columns.
            col_widths: Optional explicit widths for each column.
            gap: Spaces between columns.
            total_width: If provided and col_widths is None, calculates equal column widths.

        Returns:
            Rendered composite multi-line grid string.
        """
        if not cards:
            return ""

        cols = max(1, cols)
        gap_str = " " * max(0, gap)

        # Determine widths
        widths: list[int] = []
        if col_widths is not None:
            widths = list(col_widths[:cols])
            while len(widths) < cols:
                widths.append(widths[-1] if widths else 20)
        elif total_width is not None:
            available = max(0, total_width - (gap * (cols - 1)))
            base_w = available // cols
            remainder = available % cols
            widths = [base_w + (1 if i < remainder else 0) for i in range(cols)]
        else:
            # Derive width from maximum natural width of items in each column
            widths = [0] * cols
            for idx, c in enumerate(cards):
                col_idx = idx % cols
                card_w = max((string_width(line) for line in c.split("\n")), default=0)
                widths[col_idx] = max(widths[col_idx], card_w)

        # Group cards into rows of length cols
        rendered_grid_rows: list[str] = []
        for i in range(0, len(cards), cols):
            row_items = cards[i : i + cols]
            # Format each card in this row to its column width
            formatted_cells: list[str] = []
            max_cell_h = 0
            for col_idx, card_str in enumerate(row_items):
                target_w = widths[col_idx]
                lines = card_str.split("\n")
                padded_lines: list[str] = []
                for l in lines:
                    w = string_width(l)
                    if w < target_w:
                        padded_lines.append(f"{l}{' ' * (target_w - w)}")
                    elif w > target_w:
                        padded_lines.append(truncate_ansi(l, target_w))
                    else:
                        padded_lines.append(l)
                max_cell_h = max(max_cell_h, len(padded_lines))
                formatted_cells.append("\n".join(padded_lines))

            # Pad height of all cells in row to match
            equal_h_cells: list[str] = []
            for col_idx, f_cell in enumerate(formatted_cells):
                target_w = widths[col_idx]
                c_lines = f_cell.split("\n")
                while len(c_lines) < max_cell_h:
                    c_lines.append(" " * target_w)
                equal_h_cells.append("\n".join(c_lines))

            # Join horizontally with gap
            row_str = gap_str.join(
                [equal_h_cells[k] if k < len(equal_h_cells) else (" " * widths[k]) for k in range(cols)]
            )
            # Actually use line-by-line joining to respect multi-line cells
            row_lines: list[str] = []
            for r in range(max_cell_h):
                line_parts: list[str] = []
                for k in range(cols):
                    if k < len(equal_h_cells):
                        cell_lines = equal_h_cells[k].split("\n")
                        line_parts.append(cell_lines[r] if r < len(cell_lines) else (" " * widths[k]))
                    else:
                        line_parts.append(" " * widths[k])
                row_lines.append(gap_str.join(line_parts))

            rendered_grid_rows.append("\n".join(row_lines))

        return "\n".join(rendered_grid_rows)

    @staticmethod
    def auto_fit(
        cards: Sequence[str],
        total_width: int,
        min_col_width: int = 25,
        gap: int = 1,
    ) -> str:
        """Automatically fit as many columns as possible into total_width.

        Args:
            cards: List of rendered card strings.
            total_width: Available terminal canvas width.
            min_col_width: Minimum width allowed per column.
            gap: Column horizontal gap.
        """
        if not cards or total_width <= 0:
            return ""

        # Calculate max columns
        cols = max(1, (total_width + gap) // max(1, min_col_width + gap))
        cols = min(cols, len(cards))
        return Grid.columns(cards, cols=cols, gap=gap, total_width=total_width)

    @staticmethod
    def panel(
        title: str,
        content: str,
        width: int = 40,
        height: int | None = None,
        border: Border = ROUNDED_BORDER,
        border_foreground: str = "#7D56F4",
        title_style: Style | None = None,
    ) -> str:
        """Construct a framed card panel with title badge and content.

        Args:
            title: Panel header text.
            content: Inner multi-line body text.
            width: Total outer width.
            height: Total outer height (optional).
            border: Border style preset.
            border_foreground: ANSI hex color for the border.
            title_style: Custom style for the title badge.
        """
        w = max(10, width)
        inner_w = max(4, w - 2)

        # Truncate content lines if they exceed inner_w to preserve outer panel width
        lines = content.split("\n")
        truncated_lines = [
            truncate_ansi(line, inner_w) if string_width(line) > inner_w else line
            for line in lines
        ]

        st = Style().border(border).border_foreground(border_foreground).width(inner_w)
        if title:
            st = st.border_title(f" {title} ")
        if height is not None:
            st = st.height(height)

        return st.render("\n".join(truncated_lines))

