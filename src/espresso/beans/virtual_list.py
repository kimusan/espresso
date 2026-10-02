"""Virtualized scrollable list component for high-performance timeline and item feeds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Sequence, TypeVar

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi

T = TypeVar("T")


@dataclass(frozen=True)
class VirtualListSelectMsg(Msg):
    """Message emitted when an item in a VirtualList is confirmed/selected."""

    index: int
    item: Any


@dataclass(frozen=True)
class VirtualListChangeMsg(Msg):
    """Message emitted when the active selection index in a VirtualList moves."""

    index: int
    item: Any


class VirtualList(Model, Generic[T]):
    """Virtualized list component that slices and renders only visible items in the viewport."""

    def __init__(
        self,
        items: Sequence[T] | None = None,
        render_item: Callable[[T, bool, int], str] | None = None,
        selected_index: int = 0,
        width: int = 80,
        height: int = 20,
        show_scrollbar: bool = True,
        focused: bool = True,
    ) -> None:
        self.items: list[T] = list(items) if items is not None else []
        self.render_item = render_item or (lambda it, sel, w: f"{'▶ ' if sel else '  '}{str(it)}")
        self.width = max(10, width)
        self.height = max(3, height)
        self.show_scrollbar = show_scrollbar
        self.focused = focused

        self.selected_index = max(0, min(selected_index, max(0, len(self.items) - 1)))
        self.item_offset = 0
        self._height_cache: dict[tuple[int, int], int] = {}

        # Styles
        self.scrollbar_track_style = Style().foreground("#333344")
        self.scrollbar_thumb_style = Style().foreground("#7D56F4").bold(True)
        self.empty_style = Style().faint(True)

    @property
    def selected_item(self) -> T | None:
        """Return the currently selected item, or None if list is empty."""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None

    def invalidate_cache(self) -> None:
        """Clear cached item heights and readjust scroll."""
        self._height_cache.clear()
        self._adjust_scroll()

    def _item_height(self, index: int) -> int:
        """Calculate and cache the rendered height in rows for item at index."""
        if 0 <= index < len(self.items):
            content_w = self.width - (1 if self.show_scrollbar else 0)
            cache_key = (index, content_w)
            if cache_key in self._height_cache:
                return self._height_cache[cache_key]
            rendered = self.render_item(self.items[index], index == self.selected_index, content_w)
            h = max(1, len(rendered.splitlines()))
            self._height_cache[cache_key] = h
            return h
        return 1

    def set_items(self, items: Sequence[T], keep_anchor: bool = False, anchor_id_fn: Callable[[T], Any] | None = None) -> None:
        """Update items with optional anchor key preservation."""
        self._height_cache.clear()
        old_anchor = None
        if keep_anchor and anchor_id_fn and self.selected_item is not None:
            old_anchor = anchor_id_fn(self.selected_item)

        self.items = list(items)
        if not self.items:
            self.selected_index = 0
            self.item_offset = 0
            return

        if old_anchor is not None and anchor_id_fn:
            for idx, it in enumerate(self.items):
                if anchor_id_fn(it) == old_anchor:
                    self.selected_index = idx
                    self._adjust_scroll()
                    return

        self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))
        self._adjust_scroll()

    def select(self, index: int) -> tuple[VirtualList[T], Cmd | None]:
        """Move selection to specified index and emit change message."""
        if not self.items:
            return self, None
        new_idx = max(0, min(index, len(self.items) - 1))
        if new_idx == self.selected_index:
            return self, None
        self.selected_index = new_idx
        self._adjust_scroll()
        sel_item = self.items[self.selected_index]
        def _cmd() -> Msg:
            return VirtualListChangeMsg(index=new_idx, item=sel_item)
        return self, _cmd

    def _adjust_scroll(self) -> None:
        """Keep selected item within visible window, properly accounting for variable-height items."""
        if not self.items:
            self.item_offset = 0
            return

        self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))

        # Case 1: Selected item is scrolled above the visible window
        if self.selected_index < self.item_offset:
            self.item_offset = self.selected_index
            return

        # Case 2: Selected item is at or below item_offset.
        # Fast-forward if selected_index is far below item_offset to avoid O(N) scans
        if self.selected_index - self.item_offset > self.height:
            self.item_offset = self.selected_index - self.height

        # Calculate total lines from item_offset through selected_index
        total_lines = sum(self._item_height(i) for i in range(self.item_offset, self.selected_index + 1))

        # Advance item_offset until selected item fits within self.height
        while self.item_offset < self.selected_index and total_lines > self.height:
            total_lines -= self._item_height(self.item_offset)
            self.item_offset += 1

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False

    def set_size(self, width: int, height: int) -> None:
        """Update dimensions and adjust visible viewport."""
        w = max(1, width)
        h = max(1, height)
        if w != self.width:
            self._height_cache.clear()
        self.width = w
        self.height = h
        self._adjust_scroll()

    def update(self, msg: Msg) -> tuple[VirtualList[T], Cmd | None]:
        if not self.items or not self.focused:
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    return self.select(self.selected_index + 1)
                case "up" | "k":
                    return self.select(self.selected_index - 1)
                case "g" | "home":
                    return self.select(0)
                case "G" | "end":
                    return self.select(len(self.items) - 1)
                case "pageup" | "ctrl+u":
                    avg_h = self._item_height(self.selected_index)
                    jump = max(1, self.height // avg_h)
                    return self.select(max(0, self.selected_index - jump))
                case "pagedown" | "ctrl+d":
                    avg_h = self._item_height(self.selected_index)
                    jump = max(1, self.height // avg_h)
                    return self.select(min(len(self.items) - 1, self.selected_index + jump))
                case "enter" | " ":
                    sel_idx = self.selected_index
                    sel_it = self.items[sel_idx]
                    def _confirm_cmd() -> Msg:
                        return VirtualListSelectMsg(index=sel_idx, item=sel_it)
                    return self, _confirm_cmd

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.WHEEL_UP:
                return self.select(max(0, self.selected_index - 1))
            elif msg.button == MouseButton.WHEEL_DOWN:
                return self.select(min(len(self.items) - 1, self.selected_index + 1))
            elif msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                if self.show_scrollbar and msg.x >= self.width - 1 and self.items:
                    ratio = max(0.0, min(1.0, msg.y / max(1, self.height - 1)))
                    target = int(round(ratio * (len(self.items) - 1)))
                    return self.select(target)
                cur_y = 0
                for idx in range(self.item_offset, len(self.items)):
                    h = self._item_height(idx)
                    if cur_y <= msg.y < cur_y + h:
                        return self.select(idx)
                    cur_y += h
                    if cur_y >= self.height:
                        break

        return self, None

    def view(self) -> str:
        """Render the visible items with optional scrollbar."""
        if not self.items:
            empty_msg = self.empty_style.render("No items to display")
            return f"{empty_msg}\n" * min(3, self.height)

        content_w = self.width - (1 if self.show_scrollbar else 0)
        lines: list[str] = []

        # Slice visible items
        idx = self.item_offset
        while idx < len(self.items) and len(lines) < self.height:
            item = self.items[idx]
            is_selected = (idx == self.selected_index and self.focused)
            rendered_block = self.render_item(item, is_selected, content_w)
            for l in rendered_block.splitlines():
                if len(lines) >= self.height:
                    break
                truncated = truncate_ansi(l, content_w)
                pad = max(0, content_w - string_width(truncated))
                lines.append(f"{truncated}{' ' * pad}")
            idx += 1

        # Fill remaining height with blank rows if fewer lines rendered
        while len(lines) < self.height:
            lines.append(" " * content_w)

        # Composite scrollbar if requested
        if self.show_scrollbar and self.height > 0:
            total_items = max(1, len(self.items))
            thumb_size = max(1, int(round((self.height / total_items) * self.height)))
            max_scroll = max(1, total_items - 1)
            thumb_pos = int((self.selected_index / max_scroll) * (self.height - thumb_size))
            thumb_pos = max(0, min(self.height - thumb_size, thumb_pos))

            for r in range(self.height):
                if thumb_pos <= r < thumb_pos + thumb_size:
                    bar_char = self.scrollbar_thumb_style.render("█")
                else:
                    bar_char = self.scrollbar_track_style.render("│")
                lines[r] = f"{lines[r]}{bar_char}"

        return "\n".join(lines)
