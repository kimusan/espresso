"""Interactive CLI prompts: Select, MultiSelect, and Confirm components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style


# Messages
@dataclass(frozen=True)
class SelectSubmitMsg(Msg):
    """Message emitted when an option in a SelectPrompt is chosen."""

    selected: Any
    index: int


@dataclass(frozen=True)
class MultiSelectSubmitMsg(Msg):
    """Message emitted when options in a MultiSelectPrompt are submitted."""

    selected: list[Any]
    indices: list[int]


@dataclass(frozen=True)
class ConfirmSubmitMsg(Msg):
    """Message emitted when a ConfirmPrompt is answered."""

    confirmed: bool


class SelectPrompt(Model):
    """A single-choice selection prompt with keyboard navigation.

    Modeled after erikgeiser/promptkit select.
    """

    def __init__(
        self,
        question: str,
        options: Sequence[Any],
        default_index: int = 0,
    ) -> None:
        self.question = question
        self.options = list(options)
        self.cursor = max(0, min(default_index, max(0, len(self.options) - 1)))
        self.submitted = False

        self.q_style = Style().bold(True).foreground("#7D56F4")
        self.active_style = Style().bold(True).foreground("#00E676")
        self.normal_style = Style().foreground("#D0D0D0")
        self.dim_style = Style().faint(True)

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[SelectPrompt, Cmd | None]:
        if self.submitted:
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    if self.cursor < len(self.options) - 1:
                        self.cursor += 1
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                    return self, None
                case "enter" | " ":
                    self.submitted = True
                    selected = self.options[self.cursor]
                    def _emit() -> Msg:
                        return SelectSubmitMsg(selected=selected, index=self.cursor)
                    return self, _emit

        return self, None

    def view(self) -> str:
        lines: list[str] = [f"? {self.q_style.render(self.question)}"]

        if self.submitted:
            ans = str(self.options[self.cursor])
            lines.append(f"  {self.active_style.render('✔ ' + ans)}")
            return "\n".join(lines)

        for idx, opt in enumerate(self.options):
            is_active = (idx == self.cursor)
            pointer = "▶ " if is_active else "  "
            icon = "● " if is_active else "○ "
            label = str(opt)

            if is_active:
                styled = self.active_style.render(f"{pointer}{icon}{label}")
            else:
                styled = self.normal_style.render(f"{pointer}{icon}{label}")
            lines.append(styled)

        lines.append(self.dim_style.render("  (Use ↑/↓ arrows, Enter to choose)"))
        return "\n".join(lines)


class MultiSelectPrompt(Model):
    """A multi-choice checkbox prompt with toggle and select-all.

    Modeled after erikgeiser/promptkit multi-selection.
    """

    def __init__(
        self,
        question: str,
        options: Sequence[Any],
        default_selected: Sequence[int] = (),
    ) -> None:
        self.question = question
        self.options = list(options)
        self.cursor = 0
        self.selected_indices: set[int] = set(default_selected)
        self.submitted = False

        self.q_style = Style().bold(True).foreground("#7D56F4")
        self.checked_style = Style().bold(True).foreground("#00E676")
        self.cursor_style = Style().bold(True).foreground("#00E5FF")
        self.normal_style = Style().foreground("#D0D0D0")
        self.dim_style = Style().faint(True)

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MultiSelectPrompt, Cmd | None]:
        if self.submitted:
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    if self.cursor < len(self.options) - 1:
                        self.cursor += 1
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                    return self, None
                case " " | "space":
                    # Toggle current option
                    if self.cursor in self.selected_indices:
                        self.selected_indices.remove(self.cursor)
                    else:
                        self.selected_indices.add(self.cursor)
                    return self, None
                case "a":
                    # Toggle select all
                    if len(self.selected_indices) == len(self.options):
                        self.selected_indices.clear()
                    else:
                        self.selected_indices = set(range(len(self.options)))
                    return self, None
                case "enter":
                    self.submitted = True
                    sorted_idx = sorted(self.selected_indices)
                    chosen = [self.options[i] for i in sorted_idx]
                    def _emit() -> Msg:
                        return MultiSelectSubmitMsg(selected=chosen, indices=sorted_idx)
                    return self, _emit

        return self, None

    def view(self) -> str:
        lines: list[str] = [f"? {self.q_style.render(self.question)}"]

        if self.submitted:
            sorted_idx = sorted(self.selected_indices)
            ans = ", ".join(str(self.options[i]) for i in sorted_idx) if sorted_idx else "(none)"
            lines.append(f"  {self.checked_style.render('✔ ' + ans)}")
            return "\n".join(lines)

        for idx, opt in enumerate(self.options):
            is_cursor = (idx == self.cursor)
            is_checked = (idx in self.selected_indices)

            pointer = "▶ " if is_cursor else "  "
            box = "[x] " if is_checked else "[ ] "
            label = str(opt)

            item_text = f"{pointer}{box}{label}"
            if is_cursor:
                styled = self.cursor_style.render(item_text)
            elif is_checked:
                styled = self.checked_style.render(item_text)
            else:
                styled = self.normal_style.render(item_text)

            lines.append(styled)

        lines.append(self.dim_style.render("  (Space to toggle, 'a' all, Enter to finish)"))
        return "\n".join(lines)


class ConfirmPrompt(Model):
    """A boolean confirmation prompt [y/N] or [Y/n]."""

    def __init__(
        self,
        question: str,
        default: bool = True,
    ) -> None:
        self.question = question
        self.default = default
        self.value = default
        self.submitted = False

        self.q_style = Style().bold(True).foreground("#7D56F4")
        self.ans_style = Style().bold(True).foreground("#00E676")
        self.dim_style = Style().faint(True)

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[ConfirmPrompt, Cmd | None]:
        if self.submitted:
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "y" | "Y":
                    self.value = True
                    self.submitted = True
                    def _emit_y() -> Msg:
                        return ConfirmSubmitMsg(confirmed=True)
                    return self, _emit_y
                case "n" | "N":
                    self.value = False
                    self.submitted = True
                    def _emit_n() -> Msg:
                        return ConfirmSubmitMsg(confirmed=False)
                    return self, _emit_n
                case "tab" | "left" | "right":
                    self.value = not self.value
                    return self, None
                case "enter":
                    self.submitted = True
                    def _emit_val() -> Msg:
                        return ConfirmSubmitMsg(confirmed=self.value)
                    return self, _emit_val

        return self, None

    def view(self) -> str:
        if self.submitted:
            ans_str = "Yes" if self.value else "No"
            return f"? {self.q_style.render(self.question)} {self.ans_style.render('✔ ' + ans_str)}"

        yes_str = "[ Yes ]" if self.value else "  Yes  "
        no_str = "[ No ]" if not self.value else "  No  "

        if self.value:
            btn_yes = Style().bold(True).foreground("#000000").background("#00E676").padding(0, 1).render(yes_str)
            btn_no = Style().faint(True).padding(0, 1).render(no_str)
        else:
            btn_yes = Style().faint(True).padding(0, 1).render(yes_str)
            btn_no = Style().bold(True).foreground("#000000").background("#FF5E3A").padding(0, 1).render(no_str)

        return f"? {self.q_style.render(self.question)}  {btn_yes}  {btn_no}"
