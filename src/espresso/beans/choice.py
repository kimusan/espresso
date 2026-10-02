"""Form choice components: RadioSet and Checkbox."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width


@dataclass(frozen=True)
class RadioChangeMsg(Msg):
    """Message emitted when the selected option in a RadioSet changes."""

    id: str
    index: int
    value: str


@dataclass(frozen=True)
class CheckboxToggledMsg(Msg):
    """Message emitted when a Checkbox is toggled."""

    id: str
    checked: bool


class RadioSet(Model):
    """Single-choice radio button group component."""

    def __init__(
        self,
        options: Sequence[str | tuple[str, str]],
        selected_index: int = 0,
        id: str = "",
        disabled: bool = False,
        focused: bool = True,
    ) -> None:
        self.raw_options = list(options)
        self.options: list[tuple[str, str]] = []
        for opt in self.raw_options:
            if isinstance(opt, tuple):
                self.options.append((opt[0], opt[1]))
            else:
                self.options.append((str(opt), str(opt)))

        self.selected_index = max(0, min(selected_index, max(0, len(self.options) - 1)))
        self.cursor = self.selected_index
        self.id = id
        self.disabled = disabled
        self.focused = focused

        # Styles
        self.active_dot_style = Style().bold(True).foreground("#00E676")
        self.inactive_dot_style = Style().foreground("#666688")
        self.selected_label_style = Style().bold(True).foreground("#FFFFFF")
        self.unselected_label_style = Style().foreground("#CCCCCC")
        self.cursor_style = Style().bold(True).foreground("#00E5FF")
        self.disabled_style = Style().faint(True)

    @property
    def selected_value(self) -> str:
        if 0 <= self.selected_index < len(self.options):
            return self.options[self.selected_index][0]
        return ""

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False

    def select(self, index: int) -> tuple[RadioSet, Cmd | None]:
        if 0 <= index < len(self.options) and not self.disabled:
            self.selected_index = index
            self.cursor = index
            radio_id = self.id
            val = self.options[index][0]
            def _cmd() -> Msg:
                return RadioChangeMsg(id=radio_id, index=index, value=val)
            return self, _cmd
        return self, None

    def update(self, msg: Msg) -> tuple[RadioSet, Cmd | None]:
        if self.disabled or not self.options:
            return self, None

        if isinstance(msg, KeyMsg) and self.focused:
            match msg.key:
                case "up" | "k":
                    self.cursor = (self.cursor - 1) % len(self.options)
                    return self.select(self.cursor)
                case "down" | "j":
                    self.cursor = (self.cursor + 1) % len(self.options)
                    return self.select(self.cursor)
                case "enter" | " ":
                    return self.select(self.cursor)
                case "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9":
                    idx = int(str(msg.key)) - 1
                    if idx < len(self.options):
                        return self.select(idx)

        if isinstance(msg, MouseMsg) and not self.disabled:
            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                if 0 <= msg.y < len(self.options):
                    return self.select(msg.y)

        return self, None

    def view(self) -> str:
        lines: list[str] = []
        for idx, (val, label) in enumerate(self.options):
            is_selected = (idx == self.selected_index)
            is_cursor = (idx == self.cursor and self.focused)

            if self.disabled:
                dot = "(•)" if is_selected else "( )"
                lines.append(self.disabled_style.render(f"  {dot} {label}"))
                continue

            prefix = "▶ " if is_cursor else "  "
            if is_selected:
                bullet = self.active_dot_style.render("(•)")
                lbl = self.selected_label_style.render(label)
            else:
                bullet = self.inactive_dot_style.render("( )")
                lbl = self.unselected_label_style.render(label)

            line = f"{prefix}{bullet} {lbl}"
            if is_cursor:
                lines.append(self.cursor_style.render(prefix) + f"{bullet} {lbl}")
            else:
                lines.append(line)

        return "\n".join(lines)


class Checkbox(Model):
    """Independent multi-state checkbox component."""

    def __init__(
        self,
        label: str,
        checked: bool = False,
        id: str = "",
        disabled: bool = False,
        focused: bool = True,
    ) -> None:
        self.label = label
        self.checked = checked
        self.id = id
        self.disabled = disabled
        self.focused = focused

        self.check_style = Style().bold(True).foreground("#00E676")
        self.empty_style = Style().foreground("#666688")
        self.label_style = Style().foreground("#EEEEEE")
        self.focus_style = Style().bold(True).foreground("#00E5FF")
        self.disabled_style = Style().faint(True)

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False

    def toggle(self) -> tuple[Checkbox, Cmd | None]:
        if self.disabled:
            return self, None
        self.checked = not self.checked
        chk_id = self.id
        is_chk = self.checked
        def _cmd() -> Msg:
            return CheckboxToggledMsg(id=chk_id, checked=is_chk)
        return self, _cmd

    def update(self, msg: Msg) -> tuple[Checkbox, Cmd | None]:
        if self.disabled:
            return self, None

        if isinstance(msg, KeyMsg) and self.focused:
            match msg.key:
                case "enter" | " ":
                    return self.toggle()

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                return self.toggle()

        return self, None

    def view(self) -> str:
        if self.disabled:
            box = "[✓]" if self.checked else "[ ]"
            return self.disabled_style.render(f"{box} {self.label}")

        box_str = self.check_style.render("[✓]") if self.checked else self.empty_style.render("[ ]")
        lbl_str = self.label_style.render(self.label)
        line = f"{box_str} {lbl_str}"
        if self.focused:
            return self.focus_style.render("▶ ") + line
        return f"  {line}"
