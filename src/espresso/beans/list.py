"""Interactive, filterable, and paginated/scrollable list component.

Inspired by charmbracelet/bubbles/list and treilik/bubblelister.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Sequence

from espresso.beans.paginator import Paginator, PaginatorType
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


class PaginationMode(Enum):
    """Navigation and display mode for list items."""

    PAGINATED = "paginated"  # Discrete multi-item pages using Paginator
    SCROLL = "scroll"        # Continuous smooth scrolling viewport


@dataclass
class ListItem:
    """An individual item in a List component."""

    title: str
    description: str = ""
    value: Any = None
    badge: str = ""
    badge_style: Style | None = None

    def __str__(self) -> str:
        return self.title


@dataclass(frozen=True)
class ListSelectMsg(Msg):
    """Message emitted when an item in the List is selected with Enter or Click."""

    item: ListItem
    index: int


class List(Model):
    """A feature-rich, searchable, and paginated or scrollable terminal list.

    Modeled after charmbracelet/bubbles/list and treilik/bubblelister.
    Supports continuous scrolling, absolute and Vim relative numbering,
    right-aligned badges/suffixes, tree continuation guides, and custom item renderers.
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
        pagination_mode: PaginationMode = PaginationMode.PAGINATED,
        show_numbers: bool = False,
        relative_numbers: bool = False,
        show_tree_guides: bool = False,
        show_scrollbar: bool = False,
        prefix_fn: Callable[[ListItem, int, bool], str] | None = None,
        suffix_fn: Callable[[ListItem, int, bool], str] | None = None,
        item_renderer: Callable[[ListItem, int, bool, int], str] | None = None,
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

        self.pagination_mode = pagination_mode
        self.show_numbers = show_numbers
        self.relative_numbers = relative_numbers
        self.show_tree_guides = show_tree_guides
        self.show_scrollbar = show_scrollbar

        self.prefix_fn = prefix_fn
        self.suffix_fn = suffix_fn
        self.item_renderer = item_renderer

        self.cursor = 0
        self.scroll_offset = 0
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
        self.number_style = Style().faint(True)
        self.badge_style = Style().faint(True)
        self.guide_style = Style().faint(True)

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

    @property
    def visible_slice(self) -> tuple[int, int]:
        """Return (start, end) index bounds for currently visible items."""
        f_items = self.filtered_items
        total = len(f_items)
        if total == 0:
            return 0, 0

        if self.pagination_mode == PaginationMode.SCROLL:
            start = max(0, min(self.scroll_offset, max(0, total - 1)))
            end = min(total, start + self.per_page)
            return start, end
        else:
            return self.paginator.slice_bounds

    def _sync_scroll(self) -> None:
        """Keep scroll_offset and paginator in sync with cursor."""
        f_len = len(self.filtered_items)
        if f_len == 0:
            self.scroll_offset = 0
            self.cursor = 0
            return

        self.cursor = max(0, min(self.cursor, f_len - 1))
        if self.pagination_mode == PaginationMode.SCROLL:
            if self.cursor < self.scroll_offset:
                self.scroll_offset = self.cursor
            elif self.cursor >= self.scroll_offset + self.per_page:
                self.scroll_offset = self.cursor - self.per_page + 1
            max_offset = max(0, f_len - self.per_page)
            self.scroll_offset = max(0, min(self.scroll_offset, max_offset))
        else:
            page = self.cursor // self.per_page
            self.paginator.set_page(page)

    def set_items(self, items: Sequence[ListItem | str]) -> None:
        """Replace list items and reset cursor and scroll position."""
        self.raw_items = [
            it if isinstance(it, ListItem) else ListItem(title=str(it))
            for it in items
        ]
        self.cursor = 0
        self.scroll_offset = 0
        self.paginator.set_page(0)
        self.paginator.set_total(len(self.filtered_items))

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[List, Cmd | None]:
        """Handle keyboard and mouse input for navigation, filtering, and selection."""
        if self.filtering:
            if isinstance(msg, KeyMsg):
                if msg.key == "esc":
                    self.filtering = False
                    self.filter_input.set_value("")
                    self.paginator.set_total(len(self.filtered_items))
                    self.cursor = 0
                    self.scroll_offset = 0
                    return self, None
                if msg.key == "enter":
                    self.filtering = False
                    return self, None
            # Forward input to filter TextInput
            self.filter_input, cmd = self.filter_input.update(msg)
            # Update paginator with new filter count
            self.paginator.set_total(len(self.filtered_items))
            self._sync_scroll()
            return self, cmd

        # Mouse event handling
        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.WHEEL_UP:
                if self.cursor > 0:
                    self.cursor -= 1
                    self._sync_scroll()
                return self, None

            if msg.button == MouseButton.WHEEL_DOWN:
                if self.cursor < len(self.filtered_items) - 1:
                    self.cursor += 1
                    self._sync_scroll()
                return self, None

            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                f_items = self.filtered_items
                start, end = self.visible_slice
                page_items = f_items[start:end]

                # Calculate header row count
                header_lines = 0
                if self.show_title:
                    header_lines += 1
                if self.show_filter:
                    if self.filtering or bool(self.filter_input.value):
                        header_lines += 1
                if header_lines > 0:
                    header_lines += 1  # Blank separator line

                current_y = header_lines
                for idx, item in enumerate(page_items):
                    global_idx = start + idx
                    if self.item_renderer is not None:
                        item_h = len(self.item_renderer(item, global_idx, global_idx == self.cursor, self.width).splitlines())
                    else:
                        item_h = 1
                        if item.description:
                            item_h += len(item.description.splitlines()) or 1

                    if current_y <= msg.y < current_y + item_h:
                        self.cursor = global_idx
                        self._sync_scroll()
                        selected = item
                        def _emit_select() -> Msg:
                            return ListSelectMsg(item=selected, index=self.cursor)
                        return self, _emit_select

                    current_y += item_h

                return self, None

        # Keyboard event handling
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
                        self._sync_scroll()
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                        self._sync_scroll()
                    return self, None
                case "pgdown" | "right" | "l":
                    f_items = self.filtered_items
                    if self.pagination_mode == PaginationMode.SCROLL:
                        if f_items:
                            self.cursor = min(len(f_items) - 1, self.cursor + self.per_page)
                            self._sync_scroll()
                    else:
                        self.paginator.next_page()
                        self.cursor = self.paginator.page * self.per_page
                    return self, None
                case "pgup" | "left" | "h":
                    f_items = self.filtered_items
                    if self.pagination_mode == PaginationMode.SCROLL:
                        if f_items:
                            self.cursor = max(0, self.cursor - self.per_page)
                            self._sync_scroll()
                    else:
                        self.paginator.prev_page()
                        self.cursor = self.paginator.page * self.per_page
                    return self, None
                case "home" | "g":
                    self.cursor = 0
                    self._sync_scroll()
                    return self, None
                case "end" | "G":
                    f_items = self.filtered_items
                    if f_items:
                        self.cursor = len(f_items) - 1
                        self._sync_scroll()
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

        # 3. Item list for current page / viewport
        start, end = self.visible_slice
        page_items = f_items[start:end]

        if not page_items:
            lines.append(self.dim_style.render("  No matching items found."))
        else:
            # Scrollbar calculation
            total_items = len(f_items)
            show_sb = self.show_scrollbar and total_items > self.per_page
            thumb_h = max(1, int(len(page_items) * len(page_items) / total_items)) if show_sb else 0
            max_offset = max(1, total_items - len(page_items)) if show_sb else 1
            curr_offset = self.scroll_offset if self.pagination_mode == PaginationMode.SCROLL else start
            thumb_top = int((curr_offset / max_offset) * (len(page_items) - thumb_h)) if show_sb else 0

            # Numbering calculation
            max_num = total_items
            num_width = max(2, len(str(max_num)))

            for idx, item in enumerate(page_items):
                global_idx = start + idx
                is_selected = (global_idx == self.cursor)

                # Custom item renderer branch
                if self.item_renderer is not None:
                    rendered = self.item_renderer(item, global_idx, is_selected, self.width)
                    for r_line in rendered.splitlines():
                        lines.append(r_line)
                    continue

                # Scrollbar character for this slot
                sb_char = ""
                sb_style = None
                if show_sb:
                    if thumb_top <= idx < thumb_top + thumb_h:
                        sb_char = "█"
                        sb_style = self.cursor_style
                    else:
                        sb_char = "│"
                        sb_style = self.dim_style

                # Tree guide prefix
                guide_str = ""
                desc_guide_str = ""
                if self.show_tree_guides:
                    is_first = (idx == 0)
                    is_last = (idx == len(page_items) - 1)
                    if is_first:
                        guide_str = "╭ "
                    elif is_last and not item.description:
                        guide_str = "╰ "
                    else:
                        guide_str = "├ "

                    if item.description:
                        desc_guide_str = "╰   " if is_last else "│   "

                guide_rendered = self.guide_style.render(guide_str) if guide_str else ""
                desc_guide_rendered = self.guide_style.render(desc_guide_str) if desc_guide_str else ""

                # Number prefix
                num_str = ""
                if self.relative_numbers:
                    if is_selected:
                        num_str = f"{global_idx + 1:>{num_width}} "
                    else:
                        num_str = f"{abs(global_idx - self.cursor):>{num_width}} "
                elif self.show_numbers:
                    num_str = f"{global_idx + 1:>{num_width}}. "

                num_rendered = (self.cursor_style if is_selected else self.number_style).render(num_str) if num_str else ""

                # Cursor marker or custom prefix
                if self.prefix_fn is not None:
                    prefix_str = self.prefix_fn(item, global_idx, is_selected)
                    prefix_rendered = prefix_str
                else:
                    cursor_marker = "▶ " if is_selected else "  "
                    prefix_str = cursor_marker
                    prefix_rendered = self.cursor_style.render(cursor_marker) if is_selected else cursor_marker

                # Title styling
                title_style = self.selected_item_style if is_selected else self.item_style

                # Badge / Suffix
                badge_text = ""
                if self.suffix_fn is not None:
                    badge_text = self.suffix_fn(item, global_idx, is_selected)
                elif item.badge:
                    badge_text = item.badge

                badge_style = item.badge_style if item.badge_style is not None else self.badge_style
                badge_rendered = badge_style.render(badge_text) if badge_text else ""

                # Calculate horizontal spacing
                left_fixed_w = string_width(guide_str) + string_width(num_str) + string_width(prefix_str)
                badge_w = string_width(badge_text)
                sb_w = 2 if show_sb else 0  # " " + char

                if badge_text:
                    avail_title_w = max(4, self.width - left_fixed_w - badge_w - sb_w - 1)
                    title_to_render = truncate_ansi(item.title, avail_title_w)
                    rendered_title = title_style.render(title_to_render)
                    pad_len = max(1, self.width - left_fixed_w - string_width(title_to_render) - badge_w - sb_w)
                    item_line = f"{guide_rendered}{num_rendered}{prefix_rendered}{rendered_title}{' ' * pad_len}{badge_rendered}"
                else:
                    avail_title_w = max(4, self.width - left_fixed_w - sb_w)
                    title_to_render = truncate_ansi(item.title, avail_title_w) if self.width > 0 else item.title
                    rendered_title = title_style.render(title_to_render)
                    item_line = f"{guide_rendered}{num_rendered}{prefix_rendered}{rendered_title}"
                    if show_sb:
                        pad_len = max(1, self.width - left_fixed_w - string_width(title_to_render) - sb_w)
                        item_line = f"{item_line}{' ' * pad_len}"

                if show_sb:
                    sb_rendered = sb_style.render(sb_char) if sb_style else sb_char
                    item_line = f"{item_line} {sb_rendered}"

                lines.append(item_line)

                # Description line (if any)
                if item.description:
                    if self.show_tree_guides:
                        indent_w = string_width(num_str)
                        desc_indent = " " * indent_w
                    else:
                        indent_w = string_width(num_str) + 4
                        desc_indent = " " * indent_w

                    avail_desc_w = max(10, self.width - string_width(desc_guide_str) - indent_w - sb_w - 2)
                    desc_text = truncate_ansi(item.description, avail_desc_w)
                    rendered_desc = self.desc_style.render(desc_text)
                    desc_line = f"{desc_guide_rendered}{desc_indent}{rendered_desc}"

                    if show_sb:
                        track_sb = self.dim_style.render("│")
                        pad_len = max(1, self.width - string_width(desc_guide_str) - indent_w - string_width(desc_text) - sb_w)
                        desc_line = f"{desc_line}{' ' * pad_len} {track_sb}"

                    lines.append(desc_line)

        # 4. Footer with paginator / scroll indicator & shortcuts
        lines.append("")
        footer_parts: list[str] = []
        if self.show_pagination:
            if self.pagination_mode == PaginationMode.SCROLL and len(f_items) > 0:
                pos_percent = int(((self.cursor + 1) / len(f_items)) * 100)
                scroll_indicator = f"{self.cursor + 1}/{len(f_items)} ({pos_percent}%)"
                footer_parts.append(self.dim_style.render(scroll_indicator))
            elif self.pagination_mode == PaginationMode.PAGINATED and self.paginator.total_pages > 1:
                footer_parts.append(self.paginator.view())

        if self.show_help:
            help_text = "↑/↓ nav • / filter • enter select"
            footer_parts.append(self.dim_style.render(help_text))

        if footer_parts:
            lines.append("  ".join(footer_parts))

        return "\n".join(lines)
