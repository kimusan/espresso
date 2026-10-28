"""High-density two-line card list component with badges, tree nesting, and scrolling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class CardItem:
    """An individual 2-line data card item."""

    id: str
    title: str
    subtitle: str
    badge_text: str = ""
    badge_style: Style | None = None
    glyphs: str = ""               # Icons: unread dot (●), star (★), lock (🔒), attachment (📎)
    depth: int = 0                 # Tree indentation level (0 = root, 1+ = nested reply)
    is_unread: bool = False
    is_selected: bool = False
    data: Any = None


@dataclass(frozen=True)
class CardSelectMsg(Msg):
    """Message emitted when an item in the card list is selected."""

    item: CardItem
    index: int


@dataclass(frozen=True)
class CardActivateMsg(Msg):
    """Message emitted when an item is activated via Enter, Space, or double-click."""

    item: CardItem
    index: int


class CardList(Model):
    """A high-density two-line information list with badges, tree branches, and smooth scrolling.

    Supports keyboard arrow and vim keys navigation, mouse wheel scrolling and click-to-select,
    automatic viewport retention, and responsive truncation.
    """

    def __init__(
        self,
        items: list[CardItem] | None = None,
        selected_index: int = 0,
        width: int = 40,
        height: int = 20,
        offset_x: int = 0,
        offset_y: int = 0,
        item_style: Style | None = None,
        selected_item_style: Style | None = None,
        title_style: Style | None = None,
        unread_title_style: Style | None = None,
        subtitle_style: Style | None = None,
        selected_subtitle_style: Style | None = None,
        badge_style: Style | None = None,
        empty_text: str = "No items",
    ) -> None:
        self.items: list[CardItem] = list(items or [])
        self.width = max(10, width)
        self.height = max(2, height)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.empty_text = empty_text
        self.scroll_offset: int = 0

        self.selected_index: int = 0
        if self.items:
            self.selected_index = max(0, min(selected_index, len(self.items) - 1))
            self.items[self.selected_index].is_selected = True

        # Styles
        self.item_style = item_style or Style().foreground("#CDD6F4")
        self.selected_item_style = selected_item_style or Style().bold(True).background("#89B4FA").foreground("#11111B")
        self.title_style = title_style or Style().foreground("#CDD6F4")
        self.unread_title_style = unread_title_style or Style().bold(True).foreground("#FFFFFF")
        self.subtitle_style = subtitle_style or Style().foreground("#A6ADC8")
        self.selected_subtitle_style = selected_subtitle_style or Style().foreground("#181825")
        self.badge_style = badge_style or Style().foreground("#F9E2AF")

        self._is_mouse_down: bool = False

    @property
    def items_per_page(self) -> int:
        """Number of 2-line card items visible in the current viewport height."""
        return max(1, self.height // 2)

    def set_size(self, width: int, height: int) -> None:
        """Update viewport dimensions."""
        self.width = max(10, width)
        self.height = max(2, height)
        self._ensure_cursor_visible()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    def set_items(self, items: list[CardItem]) -> None:
        """Replace the list items and clamp the selection index."""
        self.items = list(items)
        if not self.items:
            self.selected_index = 0
            self.scroll_offset = 0
            return
        self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))
        for i, it in enumerate(self.items):
            it.is_selected = (i == self.selected_index)
        self._ensure_cursor_visible()

    def get_selected_item(self) -> CardItem | None:
        """Return the currently selected item, if any."""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None

    def _ensure_cursor_visible(self) -> None:
        """Keep selected item within the visible scroll window."""
        per_page = self.items_per_page
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + per_page:
            self.scroll_offset = self.selected_index - per_page + 1

        max_scroll = max(0, len(self.items) - per_page)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def select_index(self, index: int) -> Cmd | None:
        """Select item at given index and emit CardSelectMsg."""
        if not self.items:
            return None
        new_idx = max(0, min(index, len(self.items) - 1))
        self.selected_index = new_idx
        for i, it in enumerate(self.items):
            it.is_selected = (i == new_idx)
        self._ensure_cursor_visible()

        chosen = self.items[self.selected_index]
        idx = self.selected_index
        return lambda: CardSelectMsg(item=chosen, index=idx)

    def activate_current(self) -> Cmd | None:
        """Activate the currently selected item and emit CardActivateMsg."""
        if 0 <= self.selected_index < len(self.items):
            chosen = self.items[self.selected_index]
            idx = self.selected_index
            return lambda: CardActivateMsg(item=chosen, index=idx)
        return None

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[CardList, Cmd | None]:
        """Process keyboard arrow/vim navigation and mouse clicks/wheel/drag."""
        if isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k in ("up", "k"):
                return self, self.select_index(self.selected_index - 1)
            elif k in ("down", "j"):
                return self, self.select_index(self.selected_index + 1)
            elif k in ("home", "g"):
                return self, self.select_index(0)
            elif k in ("end", "g"):
                return self, self.select_index(len(self.items) - 1)
            elif k in ("pageup", "ctrl+u"):
                return self, self.select_index(self.selected_index - self.items_per_page)
            elif k in ("pagedown", "ctrl+d"):
                return self, self.select_index(self.selected_index + self.items_per_page)
            elif k in ("enter", " ", "space"):
                return self, self.activate_current()

        elif isinstance(msg, MouseMsg):
            rel_x = msg.x - self.offset_x
            rel_y = msg.y - self.offset_y

            if msg.action == MouseAction.RELEASE:
                self._is_mouse_down = False

            if 0 <= rel_x < self.width and 0 <= rel_y < self.height:
                # 1. Mouse Wheel Scrolling
                if msg.button in (MouseButton.WHEEL_UP, MouseButton.WHEEL_DOWN):
                    step = 3 if msg.ctrl else 1
                    delta = -step if msg.button == MouseButton.WHEEL_UP else step
                    return self, self.select_index(self.selected_index + delta)

                # 2. Double-Click to activate item directly
                if msg.action == MouseAction.DOUBLE_CLICK and msg.button == MouseButton.LEFT:
                    item_offset = rel_y // 2
                    clicked_idx = self.scroll_offset + item_offset
                    if 0 <= clicked_idx < len(self.items):
                        self.select_index(clicked_idx)
                        return self, self.activate_current()

                # 3. Left or Right Click Selection
                if msg.action == MouseAction.PRESS:
                    self._is_mouse_down = True
                    item_offset = rel_y // 2
                    clicked_idx = self.scroll_offset + item_offset
                    if 0 <= clicked_idx < len(self.items):
                        if clicked_idx == self.selected_index and msg.button == MouseButton.LEFT:
                            return self, self.activate_current()
                        return self, self.select_index(clicked_idx)
                    elif clicked_idx >= len(self.items) and self.items:
                        return self, self.select_index(len(self.items) - 1)

                # 4. Drag Selection on Mouse Motion while button is held
                elif msg.action == MouseAction.MOTION and self._is_mouse_down:
                    item_offset = rel_y // 2
                    clicked_idx = self.scroll_offset + item_offset
                    if 0 <= clicked_idx < len(self.items) and clicked_idx != self.selected_index:
                        return self, self.select_index(clicked_idx)

        return self, None

    def view(self) -> str:
        """Render the 2-line cards for all visible items in the viewport."""
        if not self.items:
            empty_msg = f"  ({self.empty_text})"
            pad = max(0, self.width - string_width(empty_msg))
            line = self.subtitle_style.render(empty_msg + (" " * pad))
            blank = " " * self.width
            out = [line] + [blank] * (self.height - 1)
            return "\n".join(out)

        per_page = self.items_per_page
        self._ensure_cursor_visible()
        visible = self.items[self.scroll_offset : self.scroll_offset + per_page]

        lines: list[str] = []
        for offset, item in enumerate(visible):
            abs_idx = self.scroll_offset + offset
            is_sel = (abs_idx == self.selected_index)

            # --- Line 1: Glyphs + Indent/Tree + Title + Spacing + Badge ---
            glyph_str = item.glyphs
            if item.is_unread and "●" not in glyph_str:
                glyph_str = f"● {glyph_str}".strip()

            glyph_part = f"{glyph_str} " if glyph_str.strip() else ""

            tree_prefix = ""
            if item.depth > 0:
                indent_spaces = "  " * (item.depth - 1)
                tree_prefix = f"{indent_spaces}╰─ "

            prefix = f"{glyph_part}{tree_prefix}"
            prefix_w = string_width(prefix)

            badge_txt = item.badge_text.strip()
            badge_w = string_width(badge_txt)

            # Available width for title
            avail_title = max(4, self.width - prefix_w - badge_w - 2)
            title_txt = truncate_ansi(item.title, avail_title)
            left_part = f"{prefix}{title_txt}"

            spacer_len = max(1, self.width - string_width(left_part) - badge_w)
            spacer = " " * spacer_len

            raw_line1 = f"{left_part}{spacer}{badge_txt}"
            line1_fitted = truncate_ansi(raw_line1, self.width)
            # Ensure padded to full width
            pad1 = max(0, self.width - string_width(line1_fitted))
            line1_full = line1_fitted + (" " * pad1)

            # --- Line 2: Indent + Subtitle ---
            tree_indent = " " * (item.depth * 2) if item.depth > 0 else ""
            line2_prefix = f"   {tree_indent}"
            avail_sub = max(4, self.width - string_width(line2_prefix))
            sub_txt = truncate_ansi(item.subtitle, avail_sub)
            raw_line2 = f"{line2_prefix}{sub_txt}"
            line2_fitted = truncate_ansi(raw_line2, self.width)
            pad2 = max(0, self.width - string_width(line2_fitted))
            line2_full = line2_fitted + (" " * pad2)

            # Styling
            if is_sel:
                rendered_l1 = self.selected_item_style.render(line1_full)
                sub_style = self.selected_subtitle_style
                if self.selected_item_style._bg is not None:
                    sub_style = sub_style.background(self.selected_item_style._bg)
                rendered_l2 = sub_style.render(line2_full)
            else:
                if item.is_unread:
                    rendered_l1 = self.unread_title_style.render(line1_full)
                else:
                    rendered_l1 = self.title_style.render(line1_full)
                rendered_l2 = self.subtitle_style.render(line2_full)

            lines.append(rendered_l1)
            lines.append(rendered_l2)

        # Pad remaining lines if viewport is larger than rendered items
        blank_row = " " * self.width
        while len(lines) < self.height:
            lines.append(blank_row)

        return "\n".join(lines[: self.height])
