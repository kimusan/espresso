"""Composite form container with field validation, Tab focus cycling, and submit dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg, batch
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style
from espresso.crema.width import string_width


class FormSubmitMsg(Msg):
    """Message emitted when form is successfully submitted with valid values."""

    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def __str__(self) -> str:
        return f"FormSubmitMsg({self.values})"


@dataclass
class FormField:
    """A single field inside a Form."""

    id: str
    label: str
    bean: Any
    validator: Callable[[Any], str | None] | None = None
    required: bool = False
    hint: str = ""
    error: str | None = None

    def get_value(self) -> Any:
        """Extract current value from the field's underlying bean."""
        b = self.bean
        if hasattr(b, "get_value") and callable(b.get_value):
            return b.get_value()
        if hasattr(b, "value"):
            return b.value
        if hasattr(b, "date"):
            return b.date
        if hasattr(b, "selected_date"):
            return b.selected_date
        if hasattr(b, "low") and hasattr(b, "high"):
            return (b.low, b.high)
        return str(b)

    def validate(self) -> bool:
        """Run validation rules and update self.error."""
        val = self.get_value()
        if self.required:
            if val is None or (isinstance(val, str) and not val.strip()):
                self.error = f"{self.label} is required"
                return False

        if self.validator is not None:
            err = self.validator(val)
            if err:
                self.error = err
                return False

        self.error = None
        return True


class Form(Model):
    """Interactive multi-field Form container with validation and keyboard focus cycling."""

    def __init__(
        self,
        fields: Sequence[FormField] | None = None,
        title: str = "Form",
        submit_label: str = "Submit",
        width: int = 50,
        offset_x: int = 0,
        offset_y: int = 0,
        style: Style | None = None,
    ) -> None:
        self.fields: list[FormField] = list(fields or [])
        self.title = title
        self.submit_label = submit_label
        self.width = max(25, width)
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.active_index: int = 0  # index into self.fields, or len(fields) for submit button
        self.submitted_values: dict[str, Any] | None = None

        # Styles
        self.style = style or Style()
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.active_label_style = Style().bold(True).foreground("#00E5FF")
        self.inactive_label_style = Style().foreground("#AAAAAA")
        self.error_style = Style().foreground("#FF5252").bold(True)
        self.hint_style = Style().faint(True)
        self.submit_active_style = Style().bold(True).foreground("#FFFFFF").background("#00C853").padding(0, 2)
        self.submit_inactive_style = Style().foreground("#CCCCCC").background("#333344").padding(0, 2)

        self._sync_focus()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset coordinates for mouse clicks."""
        self.offset_x = x
        self.offset_y = y

    def add_field(self, field: FormField) -> None:
        """Add a field to the form."""
        self.fields.append(field)
        self._sync_focus()

    def _sync_focus(self) -> None:
        """Propagate active focus state to each bean."""
        for idx, f in enumerate(self.fields):
            is_active = (idx == self.active_index)
            b = f.bean
            if is_active:
                if hasattr(b, "focus") and callable(b.focus):
                    b.focus()
                elif hasattr(b, "focused"):
                    b.focused = True
            else:
                if hasattr(b, "blur") and callable(b.blur):
                    b.blur()
                elif hasattr(b, "focused"):
                    b.focused = False

    def validate_all(self) -> bool:
        """Validate all fields. Returns True if entire form is valid."""
        all_valid = True
        first_invalid = None

        for idx, f in enumerate(self.fields):
            ok = f.validate()
            if not ok and all_valid:
                all_valid = False
                first_invalid = idx

        if not all_valid and first_invalid is not None:
            self.active_index = first_invalid
            self._sync_focus()

        return all_valid

    def get_values(self) -> dict[str, Any]:
        """Collect dictionary of {field_id: value} for all fields."""
        return {f.id: f.get_value() for f in self.fields}

    def submit(self) -> Cmd | None:
        """Validate form and return FormSubmitMsg command if valid."""
        if self.validate_all():
            vals = self.get_values()
            self.submitted_values = vals

            def _emit() -> Msg:
                return FormSubmitMsg(values=vals)

            return _emit
        return None

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        for f in self.fields:
            if isinstance(f.bean, Model):
                c = f.bean.init()
                if c:
                    cmds.append(c)
        return batch(*cmds) if cmds else None

    def update(self, msg: Msg) -> tuple[Form, Cmd | None]:
        """Handle Tab cycling, Enter submit, mouse clicks, and bean updates."""
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "tab":
                    # Move to next field or submit button
                    self.active_index = (self.active_index + 1) % (len(self.fields) + 1)
                    self._sync_focus()
                    return self, None

                case "shift+tab":
                    # Move to previous field or submit button
                    self.active_index = (self.active_index - 1) % (len(self.fields) + 1)
                    self._sync_focus()
                    return self, None

                case "up":
                    curr_bean = self.fields[self.active_index].bean if 0 <= self.active_index < len(self.fields) else None
                    if curr_bean is None or curr_bean.__class__.__name__ != "TextArea":
                        self.active_index = (self.active_index - 1) % (len(self.fields) + 1)
                        self._sync_focus()
                        return self, None

                case "down":
                    curr_bean = self.fields[self.active_index].bean if 0 <= self.active_index < len(self.fields) else None
                    if curr_bean is None or curr_bean.__class__.__name__ != "TextArea":
                        self.active_index = (self.active_index + 1) % (len(self.fields) + 1)
                        self._sync_focus()
                        return self, None

                case "ctrl+s":
                    # Instant submit
                    cmd = self.submit()
                    return self, cmd

                case "enter":
                    # If focused on submit button or last field
                    if self.active_index == len(self.fields):
                        cmd = self.submit()
                        return self, cmd

        if isinstance(msg, MouseMsg) and msg.button == MouseButton.LEFT:
            local_y = msg.y - self.offset_y
            curr_y = 2 if self.title else 0
            field_clicked = False
            for idx, f in enumerate(self.fields):
                b_lines = 1
                if isinstance(f.bean, Model):
                    b_lines = max(1, len(f.bean.view().split("\n")))
                extra = 1 if (f.error or f.hint) else 0
                field_h = 1 + b_lines + extra + 1
                if curr_y <= local_y < curr_y + field_h:
                    self.active_index = idx
                    self._sync_focus()
                    field_clicked = True
                    break
                curr_y += field_h

            if not field_clicked and local_y >= curr_y:
                self.active_index = len(self.fields)
                self._sync_focus()
                cmd = self.submit()
                return self, cmd

        # Delegate event to currently active field bean
        cmds: list[Cmd] = []
        if 0 <= self.active_index < len(self.fields):
            active_field = self.fields[self.active_index]
            if isinstance(active_field.bean, Model):
                active_field.bean, c = active_field.bean.update(msg)
                if c:
                    cmds.append(c)

        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        """Render the structured form card with fields, hints, errors, and submit button."""
        lines: list[str] = []

        if self.title:
            lines.append(self.title_style.render(self.title))
            lines.append("")

        for idx, f in enumerate(self.fields):
            is_active = (idx == self.active_index)
            label_style = self.active_label_style if is_active else self.inactive_label_style
            req_marker = " *" if f.required else ""
            focus_marker = "▶ " if is_active else "  "

            # 1. Field Label
            label_text = f"{focus_marker}{f.label}{req_marker}"
            lines.append(label_style.render(label_text))

            # 2. Field Bean Widget
            if isinstance(f.bean, Model):
                b_view = f.bean.view()
            elif callable(f.bean):
                b_view = str(f.bean())
            else:
                b_view = str(f.bean)

            # Indent bean view
            for b_line in b_view.split("\n"):
                lines.append(f"   {b_line}")

            # 3. Hint or Error
            if f.error:
                lines.append(f"   {self.error_style.render(f'⚠ {f.error}')}")
            elif f.hint:
                lines.append(f"   {self.hint_style.render(f.hint)}")

            lines.append("")

        # Submit button
        is_btn_active = (self.active_index == len(self.fields))
        btn_style = self.submit_active_style if is_btn_active else self.submit_inactive_style
        btn_marker = "▶ " if is_btn_active else "  "
        btn_rendered = btn_style.render(f"{btn_marker}[ {self.submit_label} ]")
        lines.append(f"   {btn_rendered}")

        return "\n".join(lines)
