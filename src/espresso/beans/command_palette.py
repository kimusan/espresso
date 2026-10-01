"""Command Palette component for quick spotlight search, actions, and file opening.

Inspired by VS Code Command Palette (Ctrl+P / Cmd+P) and Neovim Telescope.
Provides fuzzy filtering across commands/actions, category groupings, shortcut badges,
recent usage tracking, and convenient modal overlay rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.overlay import place_overlay
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, strip_ansi, truncate_ansi


def _fuzzy_match(query: str, text: str) -> tuple[bool, int]:
    """Check if query is a subsequence of text and return (matches, score)."""
    if not query:
        return True, 0
    q = query.lower()
    t = text.lower()
    q_idx = 0
    score = 0
    prev_idx = -2
    for i, ch in enumerate(t):
        if q_idx < len(q) and ch == q[q_idx]:
            score += 10
            # Word boundary bonus
            if i == 0 or t[i - 1] in " /_.-:":
                score += 25
            # Consecutive match bonus
            if i == prev_idx + 1:
                score += 20
            prev_idx = i
            q_idx += 1
            if q_idx == len(q):
                # Remaining characters penalty
                score -= len(t)
                return True, score
    return False, 0


@dataclass
class PaletteItem:
    """An item in the Command Palette."""

    id: str
    title: str
    description: str = ""
    shortcut: str = ""
    category: str = "Commands"
    icon: str = "›"
    data: Any = None


@dataclass(frozen=True)
class CommandPaletteSelectMsg(Msg):
    """Emitted when an item is selected in the Command Palette."""

    item: PaletteItem
    query: str


@dataclass(frozen=True)
class CommandPaletteCloseMsg(Msg):
    """Emitted when the Command Palette is dismissed."""


class CommandPalette(Model):
    """Fuzzy spotlight command and file search palette."""

    def __init__(
        self,
        items: Sequence[PaletteItem] = (),
        width: int = 58,
        max_height: int = 14,
        placeholder: str = "Type a command or search...",
        is_open: bool = False,
        toggle_key: str = "ctrl+p",
        close_on_select: bool = True,
        border_color: str = "#7D56F4",
    ) -> None:
        self.items: list[PaletteItem] = list(items)
        self.width = max(30, width)
        self.max_height = max(6, max_height)
        self.placeholder = placeholder
        self.is_open = is_open
        self.toggle_key = toggle_key.lower()
        self.close_on_select = close_on_select
        self.border_color = border_color

        self.query: str = ""
        self.cursor: int = 0
        self.scroll_offset: int = 0
        self.recent_ids: list[str] = []

        # Hit testing coordinates
        self.offset_x: int = 0
        self.offset_y: int = 0

    def set_items(self, items: Sequence[PaletteItem]) -> None:
        """Update items in the palette."""
        self.items = list(items)
        self.cursor = 0
        self.scroll_offset = 0

    def open(self) -> None:
        """Open the palette."""
        self.is_open = True
        self.cursor = 0
        self.scroll_offset = 0
        self.query = ""

    def close(self) -> None:
        """Close the palette."""
        self.is_open = False

    def toggle(self) -> None:
        """Toggle palette visibility."""
        if self.is_open:
            self.close()
        else:
            self.open()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset for mouse hit testing."""
        self.offset_x = x
        self.offset_y = y

    def get_filtered_items(self) -> list[PaletteItem]:
        """Return items matching the current query, ranked by score and recency."""
        if not self.query.strip():
            # If no query, recent items first, then original order
            recents = [it for rid in self.recent_ids for it in self.items if it.id == rid]
            others = [it for it in self.items if it.id not in self.recent_ids]
            return recents + others

        scored: list[tuple[int, int, PaletteItem]] = []
        for idx, it in enumerate(self.items):
            m_title, s_title = _fuzzy_match(self.query, it.title)
            m_desc, s_desc = _fuzzy_match(self.query, it.description)
            m_cat, s_cat = _fuzzy_match(self.query, it.category)

            if m_title or m_desc or m_cat:
                total_score = (s_title * 3) + s_desc + (s_cat * 2)
                if it.id in self.recent_ids:
                    total_score += 50
                scored.append((total_score, -idx, it))

        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [t[2] for t in scored]

    def _select_current(self) -> tuple[Model, Cmd]:
        filtered = self.get_filtered_items()
        if 0 <= self.cursor < len(filtered):
            item = filtered[self.cursor]
            if item.id in self.recent_ids:
                self.recent_ids.remove(item.id)
            self.recent_ids.insert(0, item.id)
            if self.close_on_select:
                self.close()
            return self, Cmd.none()
        return self, Cmd.none()

    def update(self, msg: Msg) -> tuple[Model, Cmd]:
        """Handle keyboard and mouse events."""
        if isinstance(msg, KeyMsg):
            key = str(msg.key).lower()

            if key == self.toggle_key:
                self.toggle()
                return self, None

            if not self.is_open:
                return self, None

            if key == "esc":
                self.close()
                return self, lambda: CommandPaletteCloseMsg()

            filtered = self.get_filtered_items()
            max_visible = self.max_height - 5

            if key in ("up", "ctrl+p", "ctrl+k"):
                if filtered:
                    self.cursor = (self.cursor - 1) % len(filtered)
                    self._adjust_scroll(max_visible)
                return self, None

            if key in ("down", "ctrl+n", "ctrl+j"):
                if filtered:
                    self.cursor = (self.cursor + 1) % len(filtered)
                    self._adjust_scroll(max_visible)
                return self, None

            if key == "enter":
                if filtered and 0 <= self.cursor < len(filtered):
                    item = filtered[self.cursor]
                    if item.id in self.recent_ids:
                        self.recent_ids.remove(item.id)
                    self.recent_ids.insert(0, item.id)
                    q = self.query
                    if self.close_on_select:
                        self.close()
                    return self, lambda: CommandPaletteSelectMsg(item=item, query=q)
                return self, None

            if key == "backspace":
                if self.query:
                    self.query = self.query[:-1]
                    self.cursor = 0
                    self.scroll_offset = 0
                return self, None

            # Text input
            char = msg.key.char if hasattr(msg.key, "char") and msg.key.char else (str(msg.key) if len(str(msg.key)) == 1 else None)
            if char and len(char) == 1 and char.isprintable():
                self.query += char
                self.cursor = 0
                self.scroll_offset = 0
                return self, None

        elif isinstance(msg, MouseMsg) and self.is_open:
            filtered = self.get_filtered_items()
            max_visible = self.max_height - 5

            rel_x = msg.x - self.offset_x
            rel_y = msg.y - self.offset_y

            # Check wheel
            if msg.button == MouseButton.WHEEL_UP:
                self.cursor = max(0, self.cursor - 1)
                self._adjust_scroll(max_visible)
                return self, None
            elif msg.button == MouseButton.WHEEL_DOWN:
                if filtered:
                    self.cursor = min(len(filtered) - 1, self.cursor + 1)
                    self._adjust_scroll(max_visible)
                return self, None

            # Item rows start at y=3 (y=0 top border, y=1 search, y=2 sep, y=3 first item)
            item_row = rel_y - 3
            if 0 <= item_row < max_visible:
                idx = self.scroll_offset + item_row
                if 0 <= idx < len(filtered):
                    if msg.action == MouseAction.PRESS:
                        self.cursor = idx
                        return self, None
                    elif msg.action == MouseAction.DOUBLE_CLICK:
                        self.cursor = idx
                        item = filtered[idx]
                        if item.id in self.recent_ids:
                            self.recent_ids.remove(item.id)
                        self.recent_ids.insert(0, item.id)
                        q = self.query
                        if self.close_on_select:
                            self.close()
                        return self, lambda: CommandPaletteSelectMsg(item=item, query=q)

        return self, None

    def _adjust_scroll(self, max_visible: int) -> None:
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + max_visible:
            self.scroll_offset = self.cursor - max_visible + 1

    def view(self) -> str:
        """Render the command palette modal."""
        if not self.is_open:
            return ""

        inner_w = self.width - 2
        filtered = self.get_filtered_items()
        max_visible = max(1, self.max_height - 5)

        # 1. Search Box
        icon_st = Style().foreground("#00E5FF").bold(True)
        query_st = Style().foreground("#FFFFFF").bold(True)
        placeholder_st = Style().foreground("#666666").italic(True)

        if self.query:
            query_rendered = f"{query_st.render(self.query)}█"
        else:
            query_rendered = placeholder_st.render(self.placeholder)

        search_line = f" {icon_st.render('🔍')} {query_rendered}"
        search_line = truncate_ansi(search_line, inner_w)
        s_w = string_width(search_line)
        if s_w < inner_w:
            search_line += " " * (inner_w - s_w)

        # 2. Separator line
        sep_char = "─"
        sep_st = Style().foreground(self.border_color)
        sep_line = sep_st.render(sep_char * inner_w)

        # 3. Item List
        item_lines: list[str] = []
        visible_items = filtered[self.scroll_offset : self.scroll_offset + max_visible]

        if not filtered:
            empty_msg = "  No matching commands or files"
            empty_st = Style().foreground("#888888").italic(True)
            empty_line = empty_st.render(empty_msg)
            e_w = string_width(empty_line)
            if e_w < inner_w:
                empty_line += " " * (inner_w - e_w)
            item_lines.append(empty_line)
        else:
            for i, it in enumerate(visible_items):
                actual_idx = self.scroll_offset + i
                is_selected = actual_idx == self.cursor

                cat_st = Style().foreground("#7D56F4").bold(True)
                title_st = Style().foreground("#FFFFFF")
                desc_st = Style().foreground("#888888")
                sc_st = Style().foreground("#E0AF68").bold(True)

                if is_selected:
                    sel_bar = Style().foreground("#00E5FF").bold(True).render("› ")
                    title_st = title_st.foreground("#00E5FF").bold(True)
                else:
                    sel_bar = "  "

                cat_part = f"[{it.category}] " if it.category else ""
                title_part = f"{sel_bar}{cat_st.render(cat_part)}{title_st.render(it.title)}"

                desc_part = f" - {desc_st.render(it.description)}" if it.description else ""
                left_side = f"{title_part}{desc_part}"

                right_side = f"{sc_st.render(it.shortcut)} " if it.shortcut else ""

                r_w = string_width(right_side)
                avail_left = max(10, inner_w - r_w - 1)
                left_truncated = truncate_ansi(left_side, avail_left)
                l_w = string_width(left_truncated)

                gap = max(1, inner_w - l_w - r_w)
                row_str = f"{left_truncated}{' ' * gap}{right_side}"

                if is_selected:
                    # Subtle highlight background across the full width
                    row_st = Style().background("#2A2A3D")
                    row_str = row_st.render(row_str)

                item_lines.append(row_str)

        # Pad remaining rows to maintain consistent modal height
        while len(item_lines) < max_visible:
            item_lines.append(" " * inner_w)

        # 4. Status Bar
        count_text = f"{len(filtered)} items"
        hints = "↑↓ Select • Enter Run • Esc Close"
        status_l = Style().foreground("#666666").faint(True).render(f" {hints}")
        status_r = Style().foreground("#888888").bold(True).render(f"{count_text} ")
        st_l_w = string_width(status_l)
        st_r_w = string_width(status_r)
        gap = max(1, inner_w - st_l_w - st_r_w)
        status_line = f"{status_l}{' ' * gap}{status_r}"

        # Combine into card
        card_content = "\n".join([search_line, sep_line] + item_lines + [sep_line, status_line])
        border_st = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(self.border_color)
            .border_title(" Command Palette ")
            .width(inner_w)
        )
        return border_st.render(card_content)

    def overlay(self, base_view: str) -> str:
        """Helper to center and overlay the command palette on top of base_view."""
        if not self.is_open:
            return base_view

        modal = self.view()
        base_lines = base_view.split("\n")
        base_h = len(base_lines)
        base_w = max((string_width(l) for l in base_lines), default=80)

        modal_lines = modal.split("\n")
        modal_h = len(modal_lines)
        modal_w = max((string_width(l) for l in modal_lines), default=self.width)

        x = max(0, (base_w - modal_w) // 2)
        y = max(1, (base_h - modal_h) // 3)  # Position slightly above middle for spotlight feel

        self.set_offset(x, y)
        return place_overlay(base_view, modal, x, y)
