"""Responsive proportional grid layout engine (Stickers-inspired FlexBox).

Modeled after 76creates/stickers.
Provides Cell, Row, and FlexBox for 2D responsive layouts with proportional
ratio weights, minimum constraints, zero-jitter rounding, and dynamic callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence, Union

from espresso.crema.layout import join_horizontal, join_vertical
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi

ContentFn = Callable[[int, int], str]
CellContent = Union[str, ContentFn]


def distribute_space(
    total_space: int,
    items: Sequence[tuple[int | None, int, int]],  # (fixed, min_val, ratio)
) -> list[int]:
    """Distribute total_space among items with zero rounding jitter.

    Each item specifies:
    - fixed: exact size if specified, or None
    - min_val: minimum size constraint
    - ratio: proportional weight (>= 1)
    """
    n = len(items)
    if n == 0:
        return []
    if n == 1:
        return [max(items[0][1], items[0][0] if items[0][0] is not None else total_space)]

    allocations = [0] * n
    flex_indices: list[int] = []
    fixed_used = 0

    # 1. Allocate fixed items
    for i, (fixed, min_val, _) in enumerate(items):
        if fixed is not None:
            size = max(min_val, fixed)
            allocations[i] = size
            fixed_used += size
        else:
            flex_indices.append(i)

    # If no flex items, return fixed allocations adjusted
    if not flex_indices:
        return allocations

    # 2. Distribute remaining space proportionally by ratio
    remaining_space = max(0, total_space - fixed_used)
    sum_ratios = sum(items[i][2] for i in flex_indices)
    if sum_ratios <= 0:
        sum_ratios = len(flex_indices)

    # First pass: base proportional allocation
    flex_allocated = 0
    remainders: list[tuple[float, int]] = []
    for i in flex_indices:
        ratio = max(1, items[i][2])
        exact = (remaining_space * ratio) / sum_ratios
        base = int(exact)
        rem = exact - base
        allocations[i] = max(items[i][1], base)
        flex_allocated += base
        remainders.append((rem, i))

    # Second pass: distribute leftover units to highest fractional remainders
    leftover = remaining_space - flex_allocated
    remainders.sort(key=lambda x: x[0], reverse=True)
    for k in range(min(leftover, len(remainders))):
        idx = remainders[k][1]
        allocations[idx] += 1

    # Final pass: guarantee exact total_space match
    diff = total_space - sum(allocations)
    if diff != 0 and flex_indices:
        # Adjust last flex item to absorb any constraint difference
        allocations[flex_indices[-1]] = max(items[flex_indices[-1]][1], allocations[flex_indices[-1]] + diff)

    return allocations


@dataclass
class Cell:
    """An individual cell within a FlexBox row."""

    content: CellContent = ""
    ratio_x: int = 1
    ratio_y: int = 1
    min_width: int = 0
    min_height: int = 0
    fixed_width: int | None = None
    fixed_height: int | None = None
    style: Style | None = None

    def set_content(self, content: CellContent) -> Cell:
        self.content = content
        return self

    def set_ratio(self, ratio_x: int = 1, ratio_y: int = 1) -> Cell:
        self.ratio_x = max(1, ratio_x)
        self.ratio_y = max(1, ratio_y)
        return self

    def set_min_dimensions(self, min_width: int = 0, min_height: int = 0) -> Cell:
        self.min_width = max(0, min_width)
        self.min_height = max(0, min_height)
        return self

    def set_fixed_dimensions(self, width: int | None = None, height: int | None = None) -> Cell:
        self.fixed_width = width
        self.fixed_height = height
        return self

    def set_style(self, style: Style | None) -> Cell:
        self.style = style
        return self

    def render(self, width: int, height: int) -> str:
        """Render cell content formatted to exact (width, height) box."""
        w = max(0, width)
        h = max(0, height)
        if w == 0 or h == 0:
            return ""

        # Produce raw string
        if callable(self.content):
            raw = self.content(w, h)
        else:
            raw = str(self.content)

        # Apply cell container style if defined
        if self.style is not None:
            raw = self.style.render(raw)

        # Pad and clamp each line to w, and pad line count to h
        raw_lines = raw.splitlines() if raw else []
        lines: list[str] = []
        for line in raw_lines[:h]:
            line_w = string_width(line)
            if line_w > w:
                truncated = truncate_ansi(line, w)
                pad = max(0, w - string_width(truncated))
                lines.append(truncated + (" " * pad))
            else:
                lines.append(line + (" " * (w - line_w)))

        while len(lines) < h:
            lines.append(" " * w)

        return "\n".join(lines[:h])


@dataclass
class Row:
    """A horizontal row of cells within a FlexBox."""

    ratio_y: int = 1
    height: int | None = None
    cells: list[Cell] = field(default_factory=list)

    def add_cell(self, cell: Cell) -> Row:
        self.cells.append(cell)
        return self

    def new_cell(
        self,
        content: CellContent = "",
        ratio_x: int = 1,
        min_width: int = 0,
        fixed_width: int | None = None,
        style: Style | None = None,
    ) -> Cell:
        """Create, append, and return a new cell in this row."""
        cell = Cell(
            content=content,
            ratio_x=ratio_x,
            min_width=min_width,
            fixed_width=fixed_width,
            style=style,
        )
        self.cells.append(cell)
        return cell


class FlexBox:
    """A 2D responsive proportional grid layout container."""

    def __init__(self, width: int = 80, height: int = 24) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.rows: list[Row] = []

    def set_dimensions(self, width: int, height: int) -> FlexBox:
        self.width = max(1, width)
        self.height = max(1, height)
        return self

    def add_row(self, row: Row) -> FlexBox:
        self.rows.append(row)
        return self

    def new_row(self, ratio_y: int = 1, height: int | None = None) -> Row:
        """Create, append, and return a new row in this flexbox."""
        row = Row(ratio_y=max(1, ratio_y), height=height)
        self.rows.append(row)
        return row

    def render(self) -> str:
        """Render the complete 2D flexbox grid to a formatted terminal string."""
        if not self.rows or self.width <= 0 or self.height <= 0:
            return ""

        # 1. Distribute vertical space among rows
        row_specs = [(r.height, 0, r.ratio_y) for r in self.rows]
        row_heights = distribute_space(self.height, row_specs)

        rendered_rows: list[str] = []

        # 2. Render each row
        for row, r_h in zip(self.rows, row_heights):
            if r_h <= 0:
                continue

            if not row.cells:
                empty_row = "\n".join([" " * self.width] * r_h)
                rendered_rows.append(empty_row)
                continue

            # Distribute horizontal space among cells in row
            cell_specs = [(c.fixed_width, c.min_width, c.ratio_x) for c in row.cells]
            cell_widths = distribute_space(self.width, cell_specs)

            # Render each cell in row
            rendered_cells = [
                cell.render(c_w, r_h) for cell, c_w in zip(row.cells, cell_widths) if c_w > 0
            ]

            if not rendered_cells:
                empty_row = "\n".join([" " * self.width] * r_h)
                rendered_rows.append(empty_row)
                continue

            joined_row = join_horizontal(Align.TOP, *rendered_cells)
            rendered_rows.append(joined_row)

        return join_vertical(Align.LEFT, *rendered_rows)

    def view(self) -> str:
        """Alias for render()."""
        return self.render()
