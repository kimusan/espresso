"""Multi-step guided wizard flow bean with validation and state preservation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import NORMAL_BORDER
from espresso.crema.layout import Align, join_vertical
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class WizardStep:
    """A single step within a multi-step guided wizard."""

    id: str
    title: str
    content: Model | str | Callable[[], str]
    description: str = ""
    can_go_back: bool = True
    validate: Callable[[], tuple[bool, str]] | None = None  # (is_valid, error_message)


@dataclass(frozen=True)
class WizardNextMsg(Msg):
    """Message emitted when advancing to the next wizard step."""

    from_step: int
    to_step: int


@dataclass(frozen=True)
class WizardBackMsg(Msg):
    """Message emitted when navigating back to a previous wizard step."""

    from_step: int
    to_step: int


@dataclass(frozen=True)
class WizardCompleteMsg(Msg):
    """Message emitted when the wizard successfully completes all steps."""

    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WizardCancelMsg(Msg):
    """Message emitted when the wizard is cancelled."""

    pass


class Wizard(Model):
    """A guided sequential flow managing steps, validation, and child model states.

    Features step badge headers, button bars with mouse hit-testing, non-destructive
    step navigation, and automatic forwarding of events to child step models.
    """

    def __init__(
        self,
        steps: list[WizardStep],
        current_step: int = 0,
        allow_cancel: bool = True,
        width: int = 70,
        height: int = 20,
        offset_x: int = 0,
        offset_y: int = 0,
        step_badge_style: Style | None = None,
        active_step_style: Style | None = None,
        completed_step_style: Style | None = None,
        button_style: Style | None = None,
        active_button_style: Style | None = None,
        disabled_button_style: Style | None = None,
        error_style: Style | None = None,
        border_style: Style | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.steps = list(steps)
        self.current_step = max(0, min(current_step, max(0, len(self.steps) - 1)))
        self.allow_cancel = allow_cancel
        self.width = max(30, width)
        self.height = max(10, height)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.error_message: str = ""
        self.data: dict[str, Any] = data if data is not None else {}

        # 0 = Content / Inputs, 1 = Back, 2 = Next/Finish, 3 = Cancel
        self.focused_button_idx: int = 0

        # Styles
        self.step_badge_style = step_badge_style or Style().foreground("#6C7086")
        self.active_step_style = active_step_style or Style().bold(True).background("#89B4FA").foreground("#11111B")
        self.completed_step_style = completed_step_style or Style().foreground("#A6E3A1")
        self.button_style = button_style or Style().background("#313244").foreground("#CDD6F4")
        self.active_button_style = active_button_style or Style().bold(True).background("#89B4FA").foreground("#11111B")
        self.disabled_button_style = disabled_button_style or Style().foreground("#585B70")
        self.error_style = error_style or Style().bold(True).foreground("#F38BA8")
        self.border_style = border_style or Style().foreground("#45475A")

        self._button_bounds: list[tuple[str, int, int]] = []  # (name, start_x, end_x)
        self._button_row_y: int = self.height - 2
        self._step_bounds: list[tuple[int, int, int]] = []  # (step_idx, start_x, end_x)
        self._content_start_y: int = 4
        self._content_end_y: int = max(4, self.height - 3)
        self._sync_content_size()

    @property
    def current(self) -> WizardStep | None:
        """Return the active WizardStep if any exists."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def set_size(self, width: int, height: int) -> None:
        """Update wizard layout dimensions."""
        self.width = max(30, width)
        self.height = max(10, height)
        self._sync_content_size()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    def _sync_content_size(self) -> None:
        """Inform child model of available inner content space."""
        inner_w = max(10, self.width - 4)
        inner_h = max(4, self.height - 7)  # Reserve for header, description, error, and buttons
        step = self.current
        if step and isinstance(step.content, Model):
            if hasattr(step.content, "set_size") and callable(step.content.set_size):
                step.content.set_size(inner_w, inner_h)
            elif hasattr(step.content, "width") and hasattr(step.content, "height"):
                step.content.width = inner_w
                step.content.height = inner_h

            if hasattr(step.content, "set_offset") and callable(step.content.set_offset):
                step.content.set_offset(0, 0)

    def next_step(self) -> Cmd | None:
        """Advance to the next step after running validation on the active step."""
        if not self.steps:
            return None

        step = self.steps[self.current_step]
        if step.validate is not None:
            is_valid, err_msg = step.validate()
            if not is_valid:
                self.error_message = err_msg or "Validation failed"
                return None

        self.error_message = ""
        if self.current_step < len(self.steps) - 1:
            old_step = self.current_step
            self.current_step += 1
            self._sync_content_size()
            curr = self.current_step
            return lambda: WizardNextMsg(from_step=old_step, to_step=curr)
        else:
            data_copy = dict(self.data)
            return lambda: WizardCompleteMsg(data=data_copy)

    def prev_step(self) -> Cmd | None:
        """Navigate back to the previous step without resetting state."""
        if self.current_step > 0:
            step = self.steps[self.current_step]
            if step.can_go_back:
                self.error_message = ""
                old_step = self.current_step
                self.current_step -= 1
                self._sync_content_size()
                curr = self.current_step
                return lambda: WizardBackMsg(from_step=old_step, to_step=curr)
        return None

    def cancel(self) -> Cmd | None:
        """Cancel the wizard flow if cancellation is allowed."""
        if self.allow_cancel:
            return lambda: WizardCancelMsg()
        return None

    def init(self) -> Cmd | None:
        step = self.current
        if step and isinstance(step.content, Model):
            return step.content.init()
        return None

    def update(self, msg: Msg) -> tuple[Wizard, Cmd | None]:
        """Handle keyboard navigation, mouse clicks on buttons, and forward to child content."""
        if isinstance(msg, MouseMsg):
            # 1. Clicks on Header step badges
            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK) and msg.button == MouseButton.LEFT:
                if msg.y == self.offset_y + 1:
                    rel_x = msg.x - self.offset_x
                    for s_idx, x0, x1 in self._step_bounds:
                        if x0 <= rel_x < x1:
                            if s_idx < self.current_step:
                                old_step = self.current_step
                                self.current_step = s_idx
                                self._sync_content_size()
                                curr = self.current_step
                                return self, lambda: WizardBackMsg(from_step=old_step, to_step=curr)
                            elif s_idx == self.current_step + 1:
                                return self, self.next_step()

            # 2. Clicks on Bottom Button Bar
            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK) and msg.button == MouseButton.LEFT:
                btn_y = self.offset_y + self._button_row_y
                if msg.y == btn_y:
                    rel_x = msg.x - self.offset_x
                    for btn_name, x0, x1 in self._button_bounds:
                        if x0 <= rel_x < x1:
                            if btn_name == "back":
                                return self, self.prev_step()
                            elif btn_name == "next":
                                return self, self.next_step()
                            elif btn_name == "cancel":
                                return self, self.cancel()

            # 3. Forward mouse events (clicks, motion, release, wheel) to child content model
            step = self.current
            if step and isinstance(step.content, Model):
                content_top = self.offset_y + self._content_start_y
                content_bottom = self.offset_y + self._content_end_y
                if content_top <= msg.y < content_bottom:
                    content_msg = msg.relative_to(self.offset_x + 2, content_top)
                    step.content, cmd = step.content.update(content_msg)
                    return self, cmd

        elif isinstance(msg, KeyMsg):
            k = str(msg.key).lower()

            # Global wizard keyboard controls
            if k == "esc":
                if self.current_step > 0:
                    return self, self.prev_step()
                elif self.allow_cancel:
                    return self, self.cancel()

            # Pass message to child content first (e.g. TextInput editing)
            step = self.current
            if step and isinstance(step.content, Model):
                new_content, child_cmd = step.content.update(msg)
                step.content = new_content
                # If child consumed an Enter or emitted a command, return it
                if child_cmd is not None:
                    return self, child_cmd

            # Enter advances if child model didn't intercept it
            if k == "enter":
                return self, self.next_step()

        return self, None

    def _render_header(self, inner_w: int) -> str:
        """Render step breadcrumbs bar: ✔ Step 1 ── ● Step 2 ── ○ Step 3."""
        badges: list[str] = []
        badge_lengths: list[int] = []
        self._step_bounds: list[tuple[int, int, int]] = []

        for idx, step in enumerate(self.steps):
            num = idx + 1
            if idx < self.current_step:
                raw_txt = f"✔ {num}. {step.title}"
                rendered = self.completed_step_style.render(raw_txt)
            elif idx == self.current_step:
                raw_txt = f" ● {num}. {step.title} "
                rendered = self.active_step_style.render(raw_txt)
            else:
                raw_txt = f"○ {num}. {step.title}"
                rendered = self.step_badge_style.render(raw_txt)

            badges.append(rendered)
            badge_lengths.append(string_width(raw_txt))

        cur_x = 2  # 1 border + 1 leading space
        sep_len = string_width(" ── ")
        for idx, blen in enumerate(badge_lengths):
            self._step_bounds.append((idx, cur_x, cur_x + blen))
            cur_x += blen + sep_len

        bar = " ── ".join(badges)
        return bar

    def _render_content(self, inner_w: int, inner_h: int) -> list[str]:
        """Render the content of the active step constrained to inner_w and inner_h."""
        step = self.current
        if not step:
            return [" " * inner_w] * inner_h

        if callable(step.content) and not isinstance(step.content, Model):
            raw = str(step.content())
        elif isinstance(step.content, Model):
            raw = step.content.view()
        else:
            raw = str(step.content)

        raw_lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n") if raw else [""]
        out_lines: list[str] = []

        for line in raw_lines[:inner_h]:
            w = string_width(line)
            if w > inner_w:
                out_lines.append(truncate_ansi(line, inner_w))
            else:
                out_lines.append(f"{line}{' ' * (inner_w - w)}")

        blank = " " * inner_w
        while len(out_lines) < inner_h:
            out_lines.append(blank)

        return out_lines

    def _render_button_bar(self, inner_w: int) -> str:
        """Render bottom action buttons: [ < Back ]   [ Next > ] / [ Finish ]   [ Cancel ]."""
        buttons: list[tuple[str, str, bool]] = []  # (id, label, enabled)

        # Back button
        can_back = self.current_step > 0 and (self.current.can_go_back if self.current else True)
        buttons.append(("back", "< Back", can_back))

        # Next / Finish button
        is_last = self.current_step == len(self.steps) - 1
        next_lbl = "Finish ✔" if is_last else "Next >"
        buttons.append(("next", next_lbl, True))

        # Cancel button
        if self.allow_cancel:
            buttons.append(("cancel", "Cancel", True))

        rendered_parts: list[str] = []
        buttons_info: list[tuple[str, str, bool, int]] = []

        for btn_id, label, enabled in buttons:
            btn_txt = f" [ {label} ] "
            btn_len = len(btn_txt)
            buttons_info.append((btn_id, label, enabled, btn_len))

            if not enabled:
                rendered = self.disabled_button_style.render(btn_txt)
            else:
                rendered = self.button_style.render(btn_txt)
            rendered_parts.append(rendered)

        btn_str = "  ".join(rendered_parts)
        w = string_width(btn_str)
        pad = max(0, inner_w - w)

        # Account for pad spaces in hit-test coordinates
        self._button_bounds = []
        cur_x = 2 + pad  # border (1) + space (1) + pad spaces
        for btn_id, label, enabled, btn_len in buttons_info:
            if enabled:
                self._button_bounds.append((btn_id, cur_x, cur_x + btn_len))
            cur_x += btn_len + 2

        return (" " * pad) + btn_str

    def view(self) -> str:
        """Render the complete bordered wizard dialog."""
        inner_w = max(10, self.width - 4)
        inner_h = max(4, self.height - 2)

        # 1. Header breadcrumbs
        header_raw = self._render_header(inner_w)
        header_line = truncate_ansi(header_raw, inner_w)

        # 2. Step description or separator
        step = self.current
        desc_line = ""
        if step and step.description:
            desc_line = truncate_ansi(Style().italic(True).foreground("#A6ADC8").render(step.description), inner_w)

        # 3. Error banner
        err_line = ""
        if self.error_message:
            err_line = truncate_ansi(self.error_style.render(f"⚠ {self.error_message}"), inner_w)

        # 4. Button bar
        button_line = self._render_button_bar(inner_w)

        # Calculate remaining content height
        overhead = 2  # header + empty line
        if desc_line:
            overhead += 1
        if err_line:
            overhead += 1
        overhead += 2  # empty line + button line

        content_h = max(2, inner_h - overhead)
        content_lines = self._render_content(inner_w, content_h)

        # Build rows inside frame
        body_rows: list[str] = [
            header_line,
        ]
        if desc_line:
            body_rows.append(desc_line)
        body_rows.append(" " * inner_w)

        self._content_start_y = len(body_rows) + 1  # 1-indexed border offset
        body_rows.extend(content_lines)
        self._content_end_y = len(body_rows) + 1

        if err_line:
            body_rows.append(err_line)
        body_rows.append(" " * inner_w)

        self._button_row_y = len(body_rows) + 1  # 1-indexed border offset
        body_rows.append(button_line)

        # Draw bordered frame
        b_tl = NORMAL_BORDER.top_left
        b_tr = NORMAL_BORDER.top_right
        b_bl = NORMAL_BORDER.bottom_left
        b_br = NORMAL_BORDER.bottom_right
        b_h = NORMAL_BORDER.top
        b_v = NORMAL_BORDER.left

        top_border = self.border_style.render(b_tl + (b_h * (inner_w + 2)) + b_tr)
        bottom_border = self.border_style.render(b_bl + (b_h * (inner_w + 2)) + b_br)

        output: list[str] = [top_border]
        for row in body_rows:
            pad = max(0, inner_w - string_width(row))
            formatted_row = f" {row}{' ' * pad} "
            v_edge = self.border_style.render(b_v)
            output.append(f"{v_edge}{formatted_row}{v_edge}")
        output.append(bottom_border)

        return "\n".join(output)
