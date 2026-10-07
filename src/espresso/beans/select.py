"""Select / dropdown component for single-choice option picking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class SelectChangeMsg(Msg):
    """Message emitted whenever a new option is chosen in a Select component."""

    id: str
    value: str
    label: str


class Select(Model):
    """Compact single-choice dropdown selector supporting keyboard and mouse interaction."""

    def __init__(
        self,
        options: Sequence[tuple[str, str]],
        value: str | None = None,
        id: str = "",
        prompt: str = "Select option...",
        width: int = 28,
        max_height: int = 6,
        disabled: bool = False,
        focused: bool = True,
    ) -> None:
        self.options = list(options)
        self.id = id
        self.prompt = prompt
        self.width = max(16, width)
        self.max_height = max(3, max_height)
        self.disabled = disabled
        self.focused = focused

        self.selected_value = value if value is not None else (self.options[0][0] if self.options else "")
        self.is_open = False
        self.cursor = self._find_index_by_value(self.selected_value)
        self.scroll_offset = 0

        # Styles
        self.box_style = Style().border(ROUNDED_BORDER).border_foreground("#414868")
        self.focused_box_style = Style().border(ROUNDED_BORDER).border_foreground("#00E5FF")
        self.open_box_style = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4")
        self.selected_style = Style().bold(True).foreground("#FFFFFF")
        self.cursor_style = Style().bold(True).foreground("#00E5FF").background("#252836")
        self.item_style = Style().foreground("#C0C0C0")
        self.faint_style = Style().faint(True)

    def _find_index_by_value(self, val: str) -> int:
        for idx, (v, _) in enumerate(self.options):
            if v == val:
                return idx
        return 0

    @property
    def value(self) -> str:
        return self.selected_value

    @value.setter
    def value(self, val: str) -> None:
        self.set_value(val)

    def set_value(self, val: str) -> None:
        self.selected_value = val
        self.cursor = self._find_index_by_value(val)

    @property
    def selected_label(self) -> str:
        for v, l in self.options:
            if v == self.selected_value:
                return l
        return self.prompt

    def init(self) -> Cmd | None:
        """TEA lifecycle init."""
        return None

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False
        self.is_open = False

    def open(self) -> None:
        if not self.disabled and self.options:
            self.is_open = True
            self.cursor = self._find_index_by_value(self.selected_value)
            self._adjust_scroll()

    def close(self) -> None:
        self.is_open = False

    def _adjust_scroll(self) -> None:
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_height:
            self.scroll_offset = self.cursor - self.max_height + 1

    def choose(self, index: int) -> tuple[Select, Cmd | None]:
        if 0 <= index < len(self.options):
            val, label = self.options[index]
            self.selected_value = val
            self.cursor = index
            self.is_open = False
            sel_id = self.id
            def _cmd() -> Msg:
                return SelectChangeMsg(id=sel_id, value=val, label=label)
            return self, _cmd
        self.is_open = False
        return self, None

    def update(self, msg: Msg) -> tuple[Select, Cmd | None]:
        if self.disabled:
            return self, None

        if isinstance(msg, KeyMsg) and self.focused:
            if not self.is_open:
                match msg.key:
                    case "enter" | " " | "down" | "j":
                        self.open()
                        return self, None
                    case "up" | "k":
                        prev_idx = max(0, self._find_index_by_value(self.selected_value) - 1)
                        return self.choose(prev_idx)
            else:
                match msg.key:
                    case "up" | "k":
                        self.cursor = max(0, self.cursor - 1)
                        self._adjust_scroll()
                        return self, None
                    case "down" | "j":
                        self.cursor = min(len(self.options) - 1, self.cursor + 1)
                        self._adjust_scroll()
                        return self, None
                    case "enter" | " ":
                        return self.choose(self.cursor)
                    case "esc" | "q":
                        self.close()
                        return self, None

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                if not self.is_open:
                    self.open()
                    return self, None
                else:
                    # In open state, mouse click toggles or selects
                    row = msg.y
                    if 1 <= row <= len(self.options):
                        idx = self.scroll_offset + (row - 1)
                        return self.choose(idx)
                    self.close()
                    return self, None

        return self, None

    def view(self) -> str:
        """Render the compact closed box or expanded options list."""
        inner_w = max(10, self.width - 2)
        arrow = "▲" if self.is_open else "▼"
        label = self.selected_label
        avail_text_w = max(4, inner_w - 3)
        truncated_label = truncate_ansi(label, avail_text_w, tail="…")
        pad = max(1, inner_w - string_width(truncated_label) - 2)
        header_content = f"{truncated_label}{' ' * pad}{arrow}"

        if not self.is_open:
            st = self.focused_box_style if self.focused else self.box_style
            if self.disabled:
                st = st.faint(True)
            return st.width(inner_w).render(header_content)

        # Open state: header box followed by popup rows
        header_line = self.open_box_style.width(inner_w).render(header_content)

        visible_rows: list[str] = []
        end_idx = min(len(self.options), self.scroll_offset + self.max_height)
        for i in range(self.scroll_offset, end_idx):
            val, lbl = self.options[i]
            prefix = "▶ " if i == self.cursor else "  "
            item_text = truncate_ansi(f"{prefix}{lbl}", inner_w - 2, tail="…")
            pad_r = max(0, inner_w - string_width(item_text))
            full_row = f"{item_text}{' ' * pad_r}"

            if i == self.cursor:
                visible_rows.append(self.cursor_style.render(full_row))
            elif val == self.selected_value:
                visible_rows.append(self.selected_style.render(full_row))
            else:
                visible_rows.append(self.item_style.render(full_row))

        menu_content = "\n".join(visible_rows)
        menu_box = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4").width(inner_w).render(menu_content)
        return f"{header_line}\n{menu_box}"
