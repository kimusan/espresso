"""Paginator component for managing and rendering pagination state."""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Sequence, TypeVar

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.color import parse_color
from espresso.crema.style import Style

T = TypeVar("T")


class PaginatorType(Enum):
    """Visual presentation style for the paginator."""

    DOTS = "dots"        # • • ◦ ◦
    NUMERIC = "numeric"  # 1/5
    COMPACT = "compact"  # Page 1 of 5 (1-10 of 42)


class BoundsTuple(tuple):
    """A tuple of (start, end) indices that is also callable as bounds()."""

    def __call__(self) -> tuple[int, int]:
        return self


class Paginator(Model):
    """Component managing page offsets and rendering pagination indicators.

    Modeled after charmbracelet/bubbles/paginator.
    """

    def __init__(
        self,
        page: int = 0,
        per_page: int = 10,
        total_items: int = 0,
        paginator_type: PaginatorType = PaginatorType.DOTS,
        active_dot: str = "•",
        inactive_dot: str = "◦",
    ) -> None:
        self.page = max(0, page)
        self.per_page = max(1, per_page)
        self.total_items = max(0, total_items)
        self.type = paginator_type

        self.active_dot = active_dot
        self.inactive_dot = inactive_dot

        self.active_dot_style: Style = Style().bold(True).foreground("#7D56F4")
        self.inactive_dot_style: Style = Style().faint(True)
        self.numeric_style: Style = Style().foreground("#FAFAFA")

    @property
    def total_pages(self) -> int:
        """Compute the total number of pages."""
        if self.total_items <= 0:
            return 1
        return max(1, math.ceil(self.total_items / self.per_page))

    @property
    def on_first_page(self) -> bool:
        """Return True if currently on the first page."""
        return self.page == 0

    @property
    def on_last_page(self) -> bool:
        """Return True if currently on the last page."""
        return self.page >= self.total_pages - 1

    @property
    def paginator_type(self) -> PaginatorType:
        """Return the current paginator visual type."""
        return self.type

    @paginator_type.setter
    def paginator_type(self, val: PaginatorType) -> None:
        self.type = val

    @property
    def slice_bounds(self) -> BoundsTuple:
        """Return (start, end) index bounds for the current page.

        Can be accessed as a property or called as a method.
        """
        start = self.page * self.per_page
        end = min(start + self.per_page, self.total_items) if self.total_items > 0 else start + self.per_page
        return BoundsTuple((start, end))

    def slice_items(self, items: Sequence[T]) -> Sequence[T]:
        """Return the items slice for the current page."""
        start, end = self.slice_bounds
        return items[start:end]

    def set_total(self, total: int) -> None:
        """Update total item count and clamp current page."""
        self.total_items = max(0, total)
        if self.page >= self.total_pages:
            self.page = max(0, self.total_pages - 1)

    def set_page(self, page: int) -> None:
        """Set the page index, clamped to [0, total_pages - 1]."""
        self.page = max(0, min(page, self.total_pages - 1))

    def next_page(self) -> None:
        """Advance to the next page if available."""
        if not self.on_last_page:
            self.page += 1

    def prev_page(self) -> None:
        """Move to the previous page if available."""
        if not self.on_first_page:
            self.page -= 1

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Paginator, Cmd | None]:
        """Handle navigation key events (arrows, pgup/pgdn, h/l)."""
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "right" | "l" | "pgdown":
                    self.next_page()
                    return self, None
                case "left" | "h" | "pgup":
                    self.prev_page()
                    return self, None
        return self, None

    def view(self) -> str:
        """Render the paginator widget string."""
        total = self.total_pages
        cur = self.page

        if self.type == PaginatorType.DOTS:
            dots: list[str] = []
            for i in range(total):
                if i == cur:
                    dots.append(self.active_dot_style.render(self.active_dot))
                else:
                    dots.append(self.inactive_dot_style.render(self.inactive_dot))
            return " ".join(dots)

        elif self.type == PaginatorType.NUMERIC:
            text = f"{cur + 1}/{total}"
            return self.numeric_style.render(text)

        else:  # PaginatorType.COMPACT
            start, end = self.slice_bounds
            if self.total_items > 0:
                text = f"Page {cur + 1} of {total} ({start + 1}-{end} of {self.total_items})"
            else:
                text = f"Page {cur + 1} of {total}"
            return self.numeric_style.render(text)
