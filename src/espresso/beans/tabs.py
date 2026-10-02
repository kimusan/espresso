"""Tab bar navigation component."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style
from espresso.crema.width import string_width


class TabStyle(Enum):
    """Visual presentation style of tab items."""

    PILL = "pill"          # Filled background pill
    LINE = "line"          # Underline indicator
    BRACKET = "bracket"    # [ Tab Name ]


@dataclass(frozen=True)
class TabChangeMsg(Msg):
    """Message emitted whenever the active tab changes."""

    index: int
    title: str


class Tabs(Model):
    """A first-class tab bar navigation component.

    Modeled after knipferrc/teacup/tab.
    """

    def __init__(
        self,
        titles: Sequence[str],
        active_tab: int = 0,
        tab_style: TabStyle = TabStyle.PILL,
        show_numbers: bool = True,
    ) -> None:
        self.titles = list(titles)
        self.active_tab = max(0, min(active_tab, max(0, len(self.titles) - 1)))
        self.tab_style = tab_style
        self.show_numbers = show_numbers

        # Styling
        self.active_pill = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.inactive_pill = Style().foreground("#9E9E9E").background("#252535").padding(0, 1)

        self.active_line = Style().bold(True).foreground("#00E676").underline(True)
        self.inactive_line = Style().foreground("#B0B0B0")

        self.active_bracket = Style().bold(True).foreground("#00E5FF")
        self.inactive_bracket = Style().faint(True)

    def set_active(self, index: int) -> Cmd | None:
        """Change active tab by index."""
        if 0 <= index < len(self.titles) and index != self.active_tab:
            self.active_tab = index
            title = self.titles[index]
            def _emit() -> Msg:
                return TabChangeMsg(index=index, title=title)
            return _emit
        return None

    def next_tab(self) -> Cmd | None:
        new_idx = (self.active_tab + 1) % len(self.titles)
        return self.set_active(new_idx)

    def prev_tab(self) -> Cmd | None:
        new_idx = (self.active_tab - 1) % len(self.titles)
        return self.set_active(new_idx)

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Tabs, Cmd | None]:
        """Handle keyboard switching (Tab, Shift+Tab, Left, Right, numbers 1-9)."""
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "tab" | "right" | "l":
                    cmd = self.next_tab()
                    return self, cmd
                case "shift+tab" | "left" | "h":
                    cmd = self.prev_tab()
                    return self, cmd
                case "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9":
                    target_idx = int(str(msg.key)) - 1
                    if target_idx < len(self.titles):
                        cmd = self.set_active(target_idx)
                        return self, cmd

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS and msg.y == 0:
                cur_x = 0
                sep_w = 3 if self.tab_style == TabStyle.LINE else 2
                extra_w = 0 if self.tab_style == TabStyle.LINE else 2
                for idx, title in enumerate(self.titles):
                    label = f"{idx + 1} {title}" if self.show_numbers else title
                    tab_w = string_width(label) + extra_w
                    if cur_x <= msg.x < cur_x + tab_w:
                        cmd = self.set_active(idx)
                        return self, cmd
                    cur_x += tab_w + sep_w
            elif msg.button == MouseButton.WHEEL_UP:
                return self, self.prev_tab()
            elif msg.button == MouseButton.WHEEL_DOWN:
                return self, self.next_tab()

        return self, None

    def view(self) -> str:
        """Render the tab bar."""
        tab_rendered: list[str] = []

        for idx, title in enumerate(self.titles):
            is_active = (idx == self.active_tab)
            label = f"{idx + 1} {title}" if self.show_numbers else title

            if self.tab_style == TabStyle.PILL:
                if is_active:
                    tab_rendered.append(self.active_pill.render(label))
                else:
                    tab_rendered.append(self.inactive_pill.render(label))

            elif self.tab_style == TabStyle.LINE:
                if is_active:
                    tab_rendered.append(self.active_line.render(label))
                else:
                    tab_rendered.append(self.inactive_line.render(label))

            else:  # BRACKET
                if is_active:
                    tab_rendered.append(self.active_bracket.render(f"[{label}]"))
                else:
                    tab_rendered.append(self.inactive_bracket.render(f" {label} "))

        separator = "  " if self.tab_style != TabStyle.LINE else "   "
        return separator.join(tab_rendered)
