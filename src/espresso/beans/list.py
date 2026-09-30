"""Interactive, filterable, and paginated list component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from espresso.beans.paginator import Paginator, PaginatorType
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class ListItem:
    """An individual item in a List component."""

    title: str
    description: str = ""
    value: Any = None

    def __str__(self) -> str:
        return self.title


@dataclass(frozen=True)
class ListSelectMsg(Msg):
    """Message emitted when an item in the List is selected with Enter."""

    item: ListItem
    index: int


class List(Model):
    """A feature-rich, searchable, and paginated terminal list.

    Modeled after charmbracelet/bubbles/list.
    """

    def __init__(
        self,
        items: Sequence[ListItem | str] = (),
        title: str = "Items",
        per_page: int = 6,
        width: int = 40,
        height: int | None = None,
        show_title: bool = True,
        show_filter: bool = True,
        show_pagination: bool = True,
        show_help: bool = True,
    ) -> None:
        self.raw_items: list[ListItem] = [
            it if isinstance(it, ListItem) else ListItem(title=str(it))
            for it in items
        ]
        self.title = title
        self.width = max(20, width)
        self.height = height
        self.per_page = max(1, height if height is not None else per_page)

        self.show_title = show_title
        self.show_filter = show_filter
        self.show_pagination = show_pagination
        self.show_help = show_help

        self.cursor = 0
        self.filtering = False
        self.filter_input = TextInput(placeholder="Type to filter...")
        self.filter_input.focus()

        self.paginator = Paginator(
            per_page=self.per_page,
            total_items=len(self.raw_items),
            paginator_type=PaginatorType.COMPACT,
        )

        # Styling
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.cursor_style = Style().bold(True).foreground("#00E676")
        self.selected_item_style = Style().bold(True).foreground("#00E676")
        self.item_style = Style().foreground("#E0E0E0")
        self.desc_style = Style().faint(True)
        self.dim_style = Style().faint(True)

    @property
    def filtered_items(self) -> list[ListItem]:
        """Return the items matching the current filter query."""
        query = self.filter_input.value.strip().lower()
        if not query:
            return self.raw_items
        return [
            it for it in self.raw_items
            if query in it.title.lower() or (it.description and query in it.description.lower())
        ]

    @property
    def selected_item(self) -> ListItem | None:
        """Return the currently highlighted ListItem, or None if empty."""
        items = self.filtered_items
        if 0 <= self.cursor < len(items):
            return items[self.cursor]
        return None

    def set_items(self, items: Sequence[ListItem | str]) -> None:
        """Replace list items and reset cursor."""
        self.raw_items = [
            it if isinstance(it, ListItem) else ListItem(title=str(it))
            for it in items
        ]
        self.cursor = 0
        self.paginator.set_page(0)
        self.paginator.set_total(len(self.filtered_items))

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[List, Cmd | None]:
        """Handle keyboard input for filtering, navigation, and selection."""
        if self.filtering:
            if isinstance(msg, KeyMsg):
                if msg.key == "esc":
                    self.filtering = False
                    self.filter_input.set_value("")
                    self.paginator.set_total(len(self.filtered_items))
                    self.cursor = 0
                    return self, None
                if msg.key == "enter":
                    self.filtering = False
                    return self, None
            # Forward input to filter TextInput
            self.filter_input, cmd = self.filter_input.update(msg)
            # Update paginator with new filter count
            self.paginator.set_total(len(self.filtered_items))
            self.cursor = max(0, min(self.cursor, max(0, len(self.filtered_items) - 1)))
            return self, cmd

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "/":
                    if self.show_filter:
                        self.filtering = True
                        self.filter_input.focus()
                        return self, None
                case "down" | "j":
                    f_items = self.filtered_items
                    if self.cursor < len(f_items) - 1:
                        self.cursor += 1
                        page = self.cursor // self.per_page
                        self.paginator.set_page(page)
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                        page = self.cursor // self.per_page
                        self.paginator.set_page(page)
                    return self, None
                case "pgdown" | "right" | "l":
                    self.paginator.next_page()
                    self.cursor = self.paginator.page * self.per_page
                    return self, None
                case "pgup" | "left" | "h":
                    self.paginator.prev_page()
                    self.cursor = self.paginator.page * self.per_page
                    return self, None
                case "home" | "g":
                    self.cursor = 0
                    self.paginator.set_page(0)
                    return self, None
                case "end" | "G":
                    f_items = self.filtered_items
                    if f_items:
                        self.cursor = len(f_items) - 1
                        self.paginator.set_page(self.cursor // self.per_page)
                    return self, None
                case "enter":
                    selected = self.selected_item
                    if selected is not None:
                        def _emit_select() -> Msg:
                            return ListSelectMsg(item=selected, index=self.cursor)
                        return self, _emit_select

        return self, None

    def view(self) -> str:
        """Render the complete list view."""
        lines: list[str] = []
        f_items = self.filtered_items
        self.paginator.set_total(len(f_items))

        # 1. Header with title and counter
        if self.show_title:
            count_str = f"({len(f_items)}/{len(self.raw_items)})" if len(f_items) != len(self.raw_items) else f"({len(self.raw_items)})"
            title_line = f"{self.title_style.render(self.title)} {self.dim_style.render(count_str)}"
            lines.append(title_line)

        # 2. Filter input bar
        if self.show_filter:
            if self.filtering:
                filter_bar = f"/ {self.filter_input.view()}"
                lines.append(filter_bar)
            elif self.filter_input.value:
                filter_bar = f"{self.dim_style.render('Filter:')} {self.filter_input.value} {self.dim_style.render('(press / to edit, esc to clear)')}"
                lines.append(filter_bar)

        if lines:
            lines.append("")

        # 3. Item list for current page
        start, end = self.paginator.slice_bounds
        page_items = f_items[start:end]

        if not page_items:
            lines.append(self.dim_style.render("  No matching items found."))
        else:
            for idx, item in enumerate(page_items):
                global_idx = start + idx
                is_selected = (global_idx == self.cursor)

                cursor_marker = "▶ " if is_selected else "  "
                cursor_styled = self.cursor_style.render(cursor_marker) if is_selected else cursor_marker

                item_styled = self.selected_item_style.render(item.title) if is_selected else self.item_style.render(item.title)
                lines.append(f"{cursor_styled}{item_styled}")

                if item.description:
                    desc_text = f"    {truncate_ansi(item.description, self.width - 6)}"
                    lines.append(self.desc_style.render(desc_text))

        # 4. Footer with paginator & shortcuts
        lines.append("")
        footer_parts: list[str] = []
        if self.show_pagination and self.paginator.total_pages > 1:
            footer_parts.append(self.paginator.view())

        if self.show_help:
            help_text = "↑/↓ nav • / filter • enter select"
            footer_parts.append(self.dim_style.render(help_text))

        if footer_parts:
            lines.append("  ".join(footer_parts))

        return "\n".join(lines)
