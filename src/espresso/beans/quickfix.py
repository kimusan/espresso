"""Neovim-style QuickFix diagnostics drawer component.

Inspired by Genekkion/theHermit.
Displays a dockable, collapsible diagnostics list of errors, warnings,
and lint issues that can overlay or dock at the bottom of the screen
while background views continue updating.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.overlay import place_overlay
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class QuickFixItem:
    """An individual diagnostic item in the QuickFix drawer."""

    file: str
    line: int
    col: int = 1
    message: str = ""
    severity: str = "error"  # "error", "warning", "info", "hint"
    code: str = ""

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}:{self.col}"
        cd = f" [{self.code}]" if self.code else ""
        return f"{loc}{cd} {self.message}"


@dataclass(frozen=True)
class QuickFixSelectMsg(Msg):
    """Message emitted when an item in the QuickFix list is selected."""

    item: QuickFixItem
    index: int


class QuickFix(Model):
    """Collapsible diagnostics drawer that docks at the bottom of a view."""

    def __init__(
        self,
        items: Sequence[QuickFixItem] = (),
        title: str = "Diagnostics",
        height: int = 8,
        is_open: bool = False,
        toggle_key: str = "ctrl+x",
    ) -> None:
        self.items: list[QuickFixItem] = list(items)
        self.title = title
        self.height = max(4, height)
        self.is_open = is_open
        self.toggle_key = toggle_key
        self.cursor: int = 0
        self.scroll_offset: int = 0

        # Styles
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.cursor_style = Style().bold(True).foreground("#00E676")
        self.error_badge = Style().bold(True).foreground("#FFFFFF").background("#FF5252").padding(0, 1)
        self.warn_badge = Style().bold(True).foreground("#000000").background("#FFD54F").padding(0, 1)
        self.info_badge = Style().bold(True).foreground("#FFFFFF").background("#00E5FF").padding(0, 1)
        self.hint_badge = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.file_style = Style().bold(True).foreground("#80D8FF")
        self.line_style = Style().foreground("#FFD54F")
        self.dim_style = Style().faint(True)
        self.border_style = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4")

    @property
    def selected_item(self) -> QuickFixItem | None:
        """Return the currently highlighted item."""
        if 0 <= self.cursor < len(self.items):
            return self.items[self.cursor]
        return None

    def toggle(self) -> None:
        """Toggle drawer open / closed."""
        self.is_open = not self.is_open

    def set_items(self, items: Sequence[QuickFixItem]) -> None:
        """Replace diagnostics items and reset cursor."""
        self.items = list(items)
        self.cursor = 0
        self.scroll_offset = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[QuickFix, Cmd | None]:
        """Handle navigation, selection, and toggling."""
        if isinstance(msg, MouseMsg):
            if not self.is_open:
                return self, None
            if msg.button == MouseButton.WHEEL_UP:
                if self.cursor > 0:
                    self.cursor -= 1
                    if self.cursor < self.scroll_offset:
                        self.scroll_offset = self.cursor
                return self, None
            elif msg.button == MouseButton.WHEEL_DOWN:
                if self.cursor < len(self.items) - 1:
                    self.cursor += 1
                    visible_rows = self.height - 3
                    if self.cursor >= self.scroll_offset + visible_rows:
                        self.scroll_offset = self.cursor - visible_rows + 1
                return self, None

        if isinstance(msg, KeyMsg):
            if msg.key == self.toggle_key:
                self.toggle()
                return self, None

            if not self.is_open:
                return self, None

            match msg.key:
                case "esc" | "q":
                    self.is_open = False
                    return self, None
                case "down" | "j":
                    if self.cursor < len(self.items) - 1:
                        self.cursor += 1
                        visible_rows = max(1, self.height - 3)
                        if self.cursor >= self.scroll_offset + visible_rows:
                            self.scroll_offset = self.cursor - visible_rows + 1
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                        if self.cursor < self.scroll_offset:
                            self.scroll_offset = self.cursor
                    return self, None
                case "enter":
                    item = self.selected_item
                    if item is not None:
                        def _emit_select() -> Msg:
                            return QuickFixSelectMsg(item=item, index=self.cursor)
                        return self, _emit_select

        return self, None

    def render_drawer(self, width: int) -> str:
        """Render the standalone drawer content bounded by width."""
        w = max(40, width)
        inner_w = w - 4

        # Header
        err_count = sum(1 for it in self.items if it.severity == "error")
        warn_count = sum(1 for it in self.items if it.severity == "warning")
        counts = f"{err_count} err, {warn_count} warn"
        header = f"{self.title_style.render(self.title)} {self.dim_style.render(f'({len(self.items)} items - {counts})')}"

        visible_rows = max(1, self.height - 3)
        page_items = self.items[self.scroll_offset : self.scroll_offset + visible_rows]

        body_lines: list[str] = [header, ""]

        if not self.items:
            body_lines.append(self.dim_style.render("  No diagnostic issues found. All clean!"))
        else:
            for idx, item in enumerate(page_items):
                global_idx = self.scroll_offset + idx
                is_sel = (global_idx == self.cursor)

                cursor_str = self.cursor_style.render("▶ ") if is_sel else "  "

                # Severity tag
                sev = item.severity.lower()
                if sev == "error":
                    badge = self.error_badge.render("ERR")
                elif sev == "warning":
                    badge = self.warn_badge.render("WARN")
                elif sev == "info":
                    badge = self.info_badge.render("INFO")
                else:
                    badge = self.hint_badge.render("HINT")

                loc_str = f"{self.file_style.render(item.file)}:{self.line_style.render(str(item.line))}"
                code_str = f" {self.dim_style.render(item.code)}" if item.code else ""
                msg_str = f" - {item.message}"

                row_text = f"{cursor_str}{badge} {loc_str}{code_str}{msg_str}"
                body_lines.append(truncate_ansi(row_text, inner_w))

        # Pad to height
        while len(body_lines) < self.height:
            body_lines.append("")

        card = self.border_style.width(w - 2).render("\n".join(body_lines[: self.height]))
        return card

    def wrap_view(self, background_view: str, width: int, height: int) -> str:
        """Compose the QuickFix drawer over the bottom lines of the background view."""
        if not self.is_open:
            return background_view

        drawer_str = self.render_drawer(width)
        drawer_lines = drawer_str.splitlines()
        dh = len(drawer_lines)
        top = max(0, height - dh)

        # Ensure background lines span at least width and height
        bg_lines = [l + " " * max(0, width - string_width(l)) for l in background_view.splitlines()]
        while len(bg_lines) < height:
            bg_lines.append(" " * width)
        padded_bg = "\n".join(bg_lines)

        # Overlay drawer at bottom
        return place_overlay(padded_bg, drawer_str, x=0, y=top)
