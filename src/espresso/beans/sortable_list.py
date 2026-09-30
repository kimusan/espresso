"""Interactive SortableList component with mouse drag-and-drop and keyboard reordering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class SortableItem:
    """An item in the SortableList."""

    id: str
    title: str
    description: str = ""
    data: Any = None

    def __str__(self) -> str:
        return self.title


@dataclass(frozen=True)
class ItemReorderedMsg(Msg):
    """Message emitted whenever an item is moved to a new position."""

    old_index: int
    new_index: int
    item: Any


class SortableList(Model):
    """A reorderable list of items supporting mouse drag-and-drop and keyboard reordering."""

    def __init__(
        self,
        items: Sequence[Any] | None = None,
        width: int = 40,
        height: int = 10,
        handle_char: str = "⠿ ",
        item_formatter: Callable[[Any], str] | None = None,
        style: Style | None = None,
        selected_style: Style | None = None,
        picked_style: Style | None = None,
        handle_style: Style | None = None,
        target_indicator_style: Style | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        self.items: list[Any] = list(items or [])
        self.width = max(10, width)
        self.height = max(3, height)
        self.handle_char = handle_char
        self.offset_x = offset_x
        self.offset_y = offset_y
        def _default_formatter(it: Any) -> str:
            if isinstance(it, str):
                return it
            if hasattr(it, "title") and not callable(getattr(it, "title")):
                return str(it.title)
            return str(it)

        self.item_formatter = item_formatter or _default_formatter

        self.cursor: int = 0
        self.scroll_offset: int = 0
        self.picked_index: int | None = None  # Keyboard grab mode
        self.dragging_index: int | None = None  # Mouse drag mode
        self.drag_target_index: int | None = None  # Mouse drop target row
        self.focused: bool = True

        self.style = style or Style()
        self.selected_style = selected_style or Style().bold(True).foreground("#00E5FF")
        self.picked_style = picked_style or Style().bold(True).foreground("#FFFFFF").background("#7D56F4")
        self.handle_style = handle_style or Style().foreground("#555577")
        self.target_indicator_style = target_indicator_style or Style().bold(True).foreground("#FFD54F")

    def set_offset(self, x: int, y: int) -> None:
        """Set the top-left screen position offset (column, row) for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    @property
    def selected_item(self) -> Any | None:
        if 0 <= self.cursor < len(self.items):
            return self.items[self.cursor]
        return None

    def set_items(self, items: Sequence[Any]) -> None:
        """Update list items and adjust cursor bounds."""
        self.items = list(items)
        self.cursor = max(0, min(self.cursor, len(self.items) - 1))
        self.picked_index = None
        self.dragging_index = None
        self.drag_target_index = None
        self._adjust_scroll()

    def set_size(self, width: int, height: int) -> None:
        self.width = max(10, width)
        self.height = max(3, height)
        self._adjust_scroll()

    def move_item(self, from_idx: int, to_idx: int) -> Cmd | None:
        """Move item from from_idx to to_idx and emit ItemReorderedMsg."""
        if from_idx == to_idx or not (0 <= from_idx < len(self.items)) or not (0 <= to_idx < len(self.items)):
            return None

        item = self.items.pop(from_idx)
        self.items.insert(to_idx, item)
        self.cursor = to_idx
        self._adjust_scroll()

        def _emit() -> Msg:
            return ItemReorderedMsg(old_index=from_idx, new_index=to_idx, item=item)

        return _emit

    def _adjust_scroll(self) -> None:
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.height:
            self.scroll_offset = self.cursor - self.height + 1
        max_offset = max(0, len(self.items) - self.height)
        self.scroll_offset = max(0, min(self.scroll_offset, max_offset))

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[SortableList, Cmd | None]:
        """Handle keyboard navigation/reordering and mouse drag-and-drop."""
        if not self.focused:
            return self, None

        if isinstance(msg, MouseMsg):
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            # Map local y coordinate to list row index
            clicked_row = self.scroll_offset + local_y

            if msg.action == MouseAction.PRESS and msg.button == MouseButton.LEFT:
                if 0 <= local_x < self.width and 0 <= local_y < min(self.height, len(self.items) - self.scroll_offset):
                    if 0 <= clicked_row < len(self.items):
                        self.cursor = clicked_row
                        self.dragging_index = clicked_row
                        self.drag_target_index = clicked_row
                        self.picked_index = None
                        return self, None

            elif msg.action == MouseAction.MOTION:
                if self.dragging_index is not None:
                    target_row = max(0, min(len(self.items) - 1, clicked_row))
                    self.drag_target_index = target_row
                    return self, None

            elif msg.action == MouseAction.RELEASE:
                if self.dragging_index is not None:
                    from_idx = self.dragging_index
                    to_idx = self.drag_target_index if self.drag_target_index is not None else from_idx
                    self.dragging_index = None
                    self.drag_target_index = None
                    if from_idx != to_idx:
                        cmd = self.move_item(from_idx, to_idx)
                        return self, cmd
                    return self, None

            elif msg.button == MouseButton.WHEEL_UP:
                if 0 <= local_x < self.width and 0 <= local_y < self.height:
                    if self.scroll_offset > 0:
                        self.scroll_offset -= 1
                    return self, None

            elif msg.button == MouseButton.WHEEL_DOWN:
                if 0 <= local_x < self.width and 0 <= local_y < self.height:
                    max_offset = max(0, len(self.items) - self.height)
                    if self.scroll_offset < max_offset:
                        self.scroll_offset += 1
                    return self, None

        elif isinstance(msg, KeyMsg):
            match msg.key:
                case "shift+up" | "alt+up" | "ctrl+up" | "K":
                    # Direct move item up
                    idx = self.picked_index if self.picked_index is not None else self.cursor
                    if idx > 0:
                        cmd = self.move_item(idx, idx - 1)
                        if self.picked_index is not None:
                            self.picked_index = idx - 1
                        return self, cmd
                    return self, None

                case "shift+down" | "alt+down" | "ctrl+down" | "J":
                    # Direct move item down
                    idx = self.picked_index if self.picked_index is not None else self.cursor
                    if idx < len(self.items) - 1:
                        cmd = self.move_item(idx, idx + 1)
                        if self.picked_index is not None:
                            self.picked_index = idx + 1
                        return self, cmd
                    return self, None

                case "up" | "k":
                    if self.picked_index is not None:
                        # Move picked item up
                        if self.picked_index > 0:
                            from_idx = self.picked_index
                            to_idx = self.picked_index - 1
                            self.picked_index = to_idx
                            cmd = self.move_item(from_idx, to_idx)
                            return self, cmd
                    else:
                        if self.cursor > 0:
                            self.cursor -= 1
                            self._adjust_scroll()
                    return self, None

                case "down" | "j":
                    if self.picked_index is not None:
                        # Move picked item down
                        if self.picked_index < len(self.items) - 1:
                            from_idx = self.picked_index
                            to_idx = self.picked_index + 1
                            self.picked_index = to_idx
                            cmd = self.move_item(from_idx, to_idx)
                            return self, cmd
                    else:
                        if self.cursor < len(self.items) - 1:
                            self.cursor += 1
                            self._adjust_scroll()
                    return self, None

                case " " | "space" | "enter":
                    # Toggle pick up / drop
                    if self.picked_index is None:
                        self.picked_index = self.cursor
                    else:
                        self.picked_index = None
                    return self, None

                case "esc":
                    # Cancel pick up
                    self.picked_index = None
                    self.dragging_index = None
                    self.drag_target_index = None
                    return self, None

        return self, None

    def view(self) -> str:
        """Render the visible items with handles, cursor badges, and drag indicators."""
        if not self.items:
            empty_msg = "  (No items in list)"
            pad = " " * max(0, self.width - string_width(empty_msg))
            return f"{empty_msg}{pad}"

        end_idx = min(len(self.items), self.scroll_offset + self.height)
        lines: list[str] = []

        for idx in range(self.scroll_offset, end_idx):
            item = self.items[idx]
            label = self.item_formatter(item)
            handle = self.handle_style.render(self.handle_char)

            is_cursor = (idx == self.cursor)
            is_picked = (idx == self.picked_index)
            is_dragging = (idx == self.dragging_index)
            is_drop_target = (self.dragging_index is not None and idx == self.drag_target_index and idx != self.dragging_index)

            # Determine indicator and styles
            if is_picked or is_dragging:
                prefix = "● "
                body = f"{handle}{label} [HOLDING]"
                row_str = f"{prefix}{body}"
                row_styled = self.picked_style.render(row_str)
            elif is_drop_target:
                prefix = "▼ "
                body = f"{handle}{label}"
                row_str = f"{prefix}{body}"
                row_styled = self.target_indicator_style.render(row_str)
            elif is_cursor:
                prefix = "▶ "
                body = f"{handle}{label}"
                row_str = f"{prefix}{body}"
                row_styled = self.selected_style.render(row_str)
            else:
                prefix = "  "
                body = f"{handle}{label}"
                row_str = f"{prefix}{body}"
                row_styled = self.style.render(row_str)

            w = string_width(row_styled)
            pad = " " * max(0, self.width - w)
            lines.append(f"{row_styled}{pad}")

        # Pad remaining height
        blank = " " * self.width
        while len(lines) < self.height:
            lines.append(blank)

        return "\n".join(lines)
