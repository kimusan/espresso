"""Interactive detail selector component with synchronized preview card.

Inspired by mritd/bubbles/selector.
Combines a single-choice selection list on top with a live synchronized
detail/preview card below, collapsing to a clean summary on submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class DetailItem:
    """An item in the DetailSelector with associated preview details."""

    title: str
    value: Any = None
    tag: str = ""
    details: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.title


@dataclass(frozen=True)
class DetailSelectMsg(Msg):
    """Message emitted when an item in the DetailSelector is selected."""

    item: DetailItem
    index: int


class DetailSelector(Model):
    """Selection list with real-time detail preview card."""

    def __init__(
        self,
        items: Sequence[DetailItem | str] = (),
        prompt: str = "Select an option:",
        width: int = 50,
        per_page: int = 5,
        collapse_on_select: bool = False,
    ) -> None:
        self.prompt = prompt
        self.width = max(35, width)
        self.per_page = max(2, per_page)
        self.collapse_on_select = collapse_on_select

        self.items: list[DetailItem] = [
            it if isinstance(it, DetailItem) else DetailItem(title=str(it))
            for it in items
        ]
        self.cursor: int = 0
        self.page: int = 0
        self.selected_item: DetailItem | None = self.items[0] if self.items else None
        self.is_submitted: bool = False

        # Styles
        self.prompt_style = Style().bold(True).foreground("#FFFFFF")
        self.cursor_style = Style().bold(True).foreground("#00E676")
        self.selected_title_style = Style().bold(True).foreground("#00E676")
        self.item_style = Style().foreground("#E0E0E0")
        self.tag_style = Style().bold(True).foreground("#7D56F4")
        self.dim_style = Style().faint(True)
        self.border_style = Style().border(ROUNDED_BORDER).border_foreground("#00E5FF")
        self.success_style = Style().bold(True).foreground("#00E676")

    @property
    def total_pages(self) -> int:
        if not self.items:
            return 1
        return (len(self.items) + self.per_page - 1) // self.per_page

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[DetailSelector, Cmd | None]:
        """Handle keyboard navigation and item selection."""
        if self.is_submitted:
            return self, None

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.WHEEL_UP:
                if self.cursor > 0:
                    self.cursor -= 1
                    self.page = self.cursor // self.per_page
                    self.selected_item = self.items[self.cursor]
                return self, None
            elif msg.button == MouseButton.WHEEL_DOWN:
                if self.cursor < len(self.items) - 1:
                    self.cursor += 1
                    self.page = self.cursor // self.per_page
                    self.selected_item = self.items[self.cursor]
                return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    if self.cursor < len(self.items) - 1:
                        self.cursor += 1
                        self.page = self.cursor // self.per_page
                        self.selected_item = self.items[self.cursor]
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                        self.page = self.cursor // self.per_page
                        self.selected_item = self.items[self.cursor]
                    return self, None
                case "enter":
                    if self.items and 0 <= self.cursor < len(self.items):
                        item = self.items[self.cursor]
                        self.selected_item = item
                        self.is_submitted = True
                        def _emit() -> Msg:
                            return DetailSelectMsg(item=item, index=self.cursor)
                        return self, _emit

        return self, None

    def view(self) -> str:
        """Render the selection list and bottom details card."""
        if self.is_submitted and self.collapse_on_select and self.selected_item:
            icon = self.success_style.render("✔")
            tag_text = f" [{self.selected_item.tag}]" if self.selected_item.tag else ""
            return f"{icon} {self.prompt_style.render(self.prompt)} {self.selected_title_style.render(self.selected_item.title)}{self.tag_style.render(tag_text)}"

        lines: list[str] = []

        # 1. Header Prompt & Page Counter
        page_info = f"({self.cursor + 1}/{len(self.items)})" if self.items else "(0/0)"
        prompt_line = f"{self.prompt_style.render(self.prompt)} {self.dim_style.render(page_info)}"
        lines.append(prompt_line)
        lines.append("")

        # 2. Options List
        start = self.page * self.per_page
        end = min(len(self.items), start + self.per_page)
        visible_items = self.items[start:end]

        for idx, item in enumerate(visible_items):
            global_idx = start + idx
            is_active = (global_idx == self.cursor)

            cursor_str = self.cursor_style.render("» ") if is_active else "  "
            num_str = self.dim_style.render(f"[{global_idx + 1}] ")
            tag_str = self.tag_style.render(f"[{item.tag}] ") if item.tag else ""
            title_styled = self.selected_title_style.render(item.title) if is_active else self.item_style.render(item.title)

            lines.append(f"{cursor_str}{num_str}{tag_str}{title_styled}")

        lines.append("")

        # 3. Synchronized Details Preview Card
        curr_item = self.items[self.cursor] if self.items and 0 <= self.cursor < len(self.items) else None
        detail_lines: list[str] = []

        if curr_item:
            card_title = Style().bold(True).foreground("#00E5FF").render(f" {curr_item.title} ")
            detail_lines.append(card_title)
            detail_lines.append(self.dim_style.render("─" * (self.width - 6)))

            if curr_item.details:
                detail_lines.append(Style().foreground("#D0D0D0").render(curr_item.details))

            if curr_item.metadata:
                detail_lines.append("")
                for k, v in curr_item.metadata.items():
                    k_str = Style().foreground("#8888AA").render(f"{k}:")
                    v_str = Style().foreground("#FAFAFA").render(str(v))
                    detail_lines.append(f"{k_str} {v_str}")
        else:
            detail_lines.append(self.dim_style.render("No item selected"))

        card = self.border_style.width(self.width - 2).render("\n".join(detail_lines))
        lines.append(card)

        # 4. Help Footer
        lines.append(self.dim_style.render("↑/↓ navigate • enter select"))

        return "\n".join(lines)
