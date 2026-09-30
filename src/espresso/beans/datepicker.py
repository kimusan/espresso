"""Interactive terminal calendar date picker component.

Inspired by EthanEFung/bubble-datepicker.
Provides a monthly calendar grid for viewing and selecting dates with keyboard
and mouse navigation, month/year focus cycling, and date constraints.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import Border, ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width


class DatePickerFocus(Enum):
    """Focus zone within the DatePicker component."""

    NONE = "none"            # Inactive or read-only
    CALENDAR = "calendar"    # Navigating days in the calendar grid
    MONTH = "month"          # Changing active month in the header
    YEAR = "year"            # Changing active year in the header


@dataclass(frozen=True)
class DateSelectMsg(Msg):
    """Message emitted when a date is confirmed/selected."""

    date: date


@dataclass(frozen=True)
class DateChangeMsg(Msg):
    """Message emitted whenever the highlighted cursor date changes."""

    date: date


def _add_months(d: date, months: int) -> date:
    """Add or subtract months from a date, clamping day to month end."""
    new_year = d.year + (d.month - 1 + months) // 12
    new_month = (d.month - 1 + months) % 12 + 1
    max_days = calendar.monthrange(new_year, new_month)[1]
    new_day = min(d.day, max_days)
    return date(new_year, new_month, new_day)


def _add_years(d: date, years: int) -> date:
    """Add or subtract years from a date, clamping day for leap years."""
    new_year = d.year + years
    max_days = calendar.monthrange(new_year, d.month)[1]
    new_day = min(d.day, max_days)
    return date(new_year, d.month, new_day)


class DatePicker(Model):
    """A monthly calendar date picker component.

    Modeled after EthanEFung/bubble-datepicker.
    """

    def __init__(
        self,
        value: Optional[date] = None,
        cursor_date: Optional[date] = None,
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        first_day_of_week: int = 6,  # 6 = Sunday (default), 0 = Monday
        focus: DatePickerFocus = DatePickerFocus.CALENDAR,
        show_header: bool = True,
        show_help: bool = True,
        border: Optional[Border] = ROUNDED_BORDER,
        border_foreground: str = "#7D56F4",
        background: Optional[str] = None,
    ) -> None:
        today = date.today()
        self.value: Optional[date] = value
        self.cursor_date: date = cursor_date or value or today
        self.min_date: Optional[date] = min_date
        self.max_date: Optional[date] = max_date
        self.first_day_of_week: int = first_day_of_week
        self.focus: DatePickerFocus = focus
        self.show_header: bool = show_header
        self.show_help: bool = show_help
        self.border: Optional[Border] = border
        self.border_foreground: str = border_foreground
        self.background: Optional[str] = background

        # Clamp cursor to min/max if needed
        self._clamp_cursor()

        # Styles
        self.header_style = Style().bold(True).foreground("#FAFAFA")
        self.header_focused_style = Style().bold(True).foreground("#000000").background("#00E5FF").padding(0, 1)
        self.nav_arrow_style = Style().bold(True).foreground("#7D56F4")
        self.day_names_style = Style().bold(True).foreground("#8888AA")
        self.date_style = Style().foreground("#E0E0E0")
        self.padding_date_style = Style().faint(True).foreground("#555566")
        self.today_style = Style().bold(True).foreground("#00E5FF").underline(True)
        self.selected_style = Style().bold(True).foreground("#000000").background("#00E676")
        self.cursor_style = Style().bold(True).foreground("#000000").background("#7D56F4")
        self.disabled_style = Style().faint(True).foreground("#444455").strikethrough(True)
        self.help_style = Style().faint(True)

    @property
    def selected_date(self) -> Optional[date]:
        """Alias for value."""
        return self.value

    @selected_date.setter
    def selected_date(self, val: Optional[date]) -> None:
        self.value = val

    def _clamp_cursor(self) -> None:
        """Ensure cursor_date satisfies min_date and max_date constraints."""
        if self.min_date and self.cursor_date < self.min_date:
            self.cursor_date = self.min_date
        if self.max_date and self.cursor_date > self.max_date:
            self.cursor_date = self.max_date

    def is_disabled(self, d: date) -> bool:
        """Return True if date is outside min_date .. max_date."""
        if self.min_date and d < self.min_date:
            return True
        if self.max_date and d > self.max_date:
            return True
        return False

    def is_today(self, d: date) -> bool:
        """Return True if date is today."""
        return d == date.today()

    def is_selected(self, d: date) -> bool:
        """Return True if date is the confirmed selected date."""
        return self.value is not None and d == self.value

    def is_cursor(self, d: date) -> bool:
        """Return True if date is currently highlighted by the cursor."""
        return d == self.cursor_date

    def set_focus(self, focus: DatePickerFocus) -> DatePicker:
        """Set current component focus."""
        self.focus = focus
        return self

    def select_date(self, d: Optional[date] = None) -> Cmd | None:
        """Select a date (defaults to cursor_date) and emit DateSelectMsg."""
        target = d or self.cursor_date
        if not self.is_disabled(target):
            self.value = target
            self.cursor_date = target
            def _emit() -> Msg:
                return DateSelectMsg(date=target)
            return _emit
        return None

    def set_date(self, d: date) -> Cmd | None:
        """Set cursor and value to date, emitting DateSelectMsg."""
        self.cursor_date = d
        self._clamp_cursor()
        self.value = self.cursor_date
        def _emit() -> Msg:
            return DateSelectMsg(date=self.cursor_date)
        return _emit

    def next_month(self) -> Cmd | None:
        """Advance cursor by 1 month."""
        new_date = _add_months(self.cursor_date, 1)
        if self.max_date and new_date > self.max_date:
            new_date = self.max_date
        if new_date != self.cursor_date:
            self.cursor_date = new_date
            def _emit() -> Msg:
                return DateChangeMsg(date=self.cursor_date)
            return _emit
        return None

    def prev_month(self) -> Cmd | None:
        """Move cursor back by 1 month."""
        new_date = _add_months(self.cursor_date, -1)
        if self.min_date and new_date < self.min_date:
            new_date = self.min_date
        if new_date != self.cursor_date:
            self.cursor_date = new_date
            def _emit() -> Msg:
                return DateChangeMsg(date=self.cursor_date)
            return _emit
        return None

    def next_year(self) -> Cmd | None:
        """Advance cursor by 1 year."""
        new_date = _add_years(self.cursor_date, 1)
        if self.max_date and new_date > self.max_date:
            new_date = self.max_date
        if new_date != self.cursor_date:
            self.cursor_date = new_date
            def _emit() -> Msg:
                return DateChangeMsg(date=self.cursor_date)
            return _emit
        return None

    def prev_year(self) -> Cmd | None:
        """Move cursor back by 1 year."""
        new_date = _add_years(self.cursor_date, -1)
        if self.min_date and new_date < self.min_date:
            new_date = self.min_date
        if new_date != self.cursor_date:
            self.cursor_date = new_date
            def _emit() -> Msg:
                return DateChangeMsg(date=self.cursor_date)
            return _emit
        return None

    def today(self) -> Cmd | None:
        """Jump cursor to today."""
        t = date.today()
        if self.min_date and t < self.min_date:
            t = self.min_date
        if self.max_date and t > self.max_date:
            t = self.max_date
        if t != self.cursor_date:
            self.cursor_date = t
            def _emit() -> Msg:
                return DateChangeMsg(date=self.cursor_date)
            return _emit
        return None

    def _move_days(self, days: int) -> Cmd | None:
        """Move cursor date by given number of days."""
        new_date = self.cursor_date + timedelta(days=days)
        if self.min_date and new_date < self.min_date:
            new_date = self.min_date
        if self.max_date and new_date > self.max_date:
            new_date = self.max_date
        if new_date != self.cursor_date:
            self.cursor_date = new_date
            def _emit() -> Msg:
                return DateChangeMsg(date=self.cursor_date)
            return _emit
        return None

    def handle_mouse_click(self, rel_x: int, rel_y: int) -> tuple[DatePicker, Cmd | None]:
        """Handle a mouse click with coordinates relative to the DatePicker interior."""
        # Check header row (row 0 when show_header is True)
        if self.show_header and rel_y == 0:
            # Layout: ◀   Month Year   ▶
            # < is around x in 0..3, > is around x >= 17
            if rel_x <= 3:
                cmd = self.prev_month()
                return self, cmd
            elif rel_x >= 17:
                cmd = self.next_month()
                return self, cmd
            elif 4 <= rel_x <= 11:
                self.focus = DatePickerFocus.MONTH
                return self, None
            elif 12 <= rel_x <= 16:
                self.focus = DatePickerFocus.YEAR
                return self, None

        # Calendar rows
        cal_row_offset = 2 if self.show_header else 1
        row_idx = rel_y - cal_row_offset
        if row_idx >= 0:
            cal = calendar.Calendar(firstweekday=self.first_day_of_week)
            weeks = cal.monthdatescalendar(self.cursor_date.year, self.cursor_date.month)
            if row_idx < len(weeks):
                col_idx = rel_x // 3
                if 0 <= col_idx < 7:
                    target_date = weeks[row_idx][col_idx]
                    if not self.is_disabled(target_date):
                        self.cursor_date = target_date
                        self.value = target_date
                        def _emit() -> Msg:
                            return DateSelectMsg(date=target_date)
                        return self, _emit
        return self, None

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[DatePicker, Cmd | None]:
        """Process keyboard navigation and mouse interactions."""
        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.WHEEL_UP:
                cmd = self.prev_month()
                return self, cmd
            elif msg.button == MouseButton.WHEEL_DOWN:
                cmd = self.next_month()
                return self, cmd
            elif msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                # If offset is border-adjusted, check if border is present
                border_offset = 1 if self.border else 0
                return self.handle_mouse_click(msg.x - border_offset, msg.y - border_offset)

        if not isinstance(msg, KeyMsg):
            return self, None

        key = msg.key

        # Global focus cycling
        if key == "tab":
            if self.focus == DatePickerFocus.CALENDAR:
                self.focus = DatePickerFocus.MONTH
            elif self.focus == DatePickerFocus.MONTH:
                self.focus = DatePickerFocus.YEAR
            else:
                self.focus = DatePickerFocus.CALENDAR
            return self, None

        if key == "shift+tab":
            if self.focus == DatePickerFocus.CALENDAR:
                self.focus = DatePickerFocus.YEAR
            elif self.focus == DatePickerFocus.YEAR:
                self.focus = DatePickerFocus.MONTH
            else:
                self.focus = DatePickerFocus.CALENDAR
            return self, None

        # Mode: MONTH
        if self.focus == DatePickerFocus.MONTH:
            match key:
                case "left" | "h" | "up" | "k":
                    cmd = self.prev_month()
                    return self, cmd
                case "right" | "l" | "down" | "j":
                    cmd = self.next_month()
                    return self, cmd
                case "enter" | " ":
                    self.focus = DatePickerFocus.CALENDAR
                    return self, None
                case "esc":
                    self.focus = DatePickerFocus.CALENDAR
                    return self, None

        # Mode: YEAR
        if self.focus == DatePickerFocus.YEAR:
            match key:
                case "left" | "h" | "down" | "j":
                    cmd = self.prev_year()
                    return self, cmd
                case "right" | "l" | "up" | "k":
                    cmd = self.next_year()
                    return self, cmd
                case "enter" | " ":
                    self.focus = DatePickerFocus.CALENDAR
                    return self, None
                case "esc":
                    self.focus = DatePickerFocus.CALENDAR
                    return self, None

        # Mode: CALENDAR
        if self.focus == DatePickerFocus.CALENDAR:
            match key:
                case "left" | "h":
                    cmd = self._move_days(-1)
                    return self, cmd
                case "right" | "l":
                    cmd = self._move_days(1)
                    return self, cmd
                case "up" | "k":
                    cmd = self._move_days(-7)
                    return self, cmd
                case "down" | "j":
                    cmd = self._move_days(7)
                    return self, cmd
                case "pageup" | "[":
                    cmd = self.prev_month()
                    return self, cmd
                case "pagedown" | "]":
                    cmd = self.next_month()
                    return self, cmd
                case "{":
                    cmd = self.prev_year()
                    return self, cmd
                case "}":
                    cmd = self.next_year()
                    return self, cmd
                case "t":
                    cmd = self.today()
                    return self, cmd
                case "enter" | " ":
                    cmd = self.select_date()
                    return self, cmd

        return self, None

    def view(self) -> str:
        """Render the datepicker calendar widget."""
        lines: list[str] = []
        cal = calendar.Calendar(firstweekday=self.first_day_of_week)
        curr_year = self.cursor_date.year
        curr_month = self.cursor_date.month

        # 1. Header (Month Year with Navigation Arrows)
        if self.show_header:
            month_name = calendar.month_name[curr_month]
            if self.focus == DatePickerFocus.MONTH:
                m_str = self.header_focused_style.render(month_name)
            else:
                m_str = self.header_style.render(month_name)

            if self.focus == DatePickerFocus.YEAR:
                y_str = self.header_focused_style.render(str(curr_year))
            else:
                y_str = self.header_style.render(str(curr_year))

            prev_arrow = self.nav_arrow_style.render("◀")
            next_arrow = self.nav_arrow_style.render("▶")

            center_text = f"{m_str} {y_str}"
            center_len = string_width(month_name) + 1 + string_width(str(curr_year))
            if self.focus in (DatePickerFocus.MONTH, DatePickerFocus.YEAR):
                center_len += 2  # padding on focused badge

            # Total width of calendar grid is 20 chars
            total_w = 20
            rem = max(1, total_w - 2 - center_len)
            l_pad = rem // 2
            r_pad = rem - l_pad

            header_line = f"{prev_arrow}{' ' * l_pad}{center_text}{' ' * r_pad}{next_arrow}"
            lines.append(header_line)

        # 2. Weekday abbreviations
        day_headers: list[str] = []
        for wd in cal.iterweekdays():
            abbr = calendar.day_abbr[wd][:2]
            day_headers.append(self.day_names_style.render(abbr))
        lines.append(" ".join(day_headers))

        # 3. Calendar Day Grid
        weeks = cal.monthdatescalendar(curr_year, curr_month)
        for week in weeks:
            row_cells: list[str] = []
            for d in week:
                day_str = f"{d.day:2d}"
                is_curr_month = (d.month == curr_month)
                is_cur = self.is_cursor(d)
                is_sel = self.is_selected(d)
                is_tod = self.is_today(d)
                is_dis = self.is_disabled(d)

                if is_dis:
                    cell = self.disabled_style.render(day_str)
                elif is_cur and self.focus == DatePickerFocus.CALENDAR:
                    cell = self.cursor_style.render(day_str)
                elif is_sel:
                    cell = self.selected_style.render(day_str)
                elif is_tod:
                    cell = self.today_style.render(day_str)
                elif is_curr_month:
                    cell = self.date_style.render(day_str)
                else:
                    cell = self.padding_date_style.render(day_str)

                row_cells.append(cell)
            lines.append(" ".join(row_cells))

        # 4. Optional navigation help footer
        if self.show_help:
            lines.append("")
            if self.focus == DatePickerFocus.CALENDAR:
                help_text = "arrows nav • enter pick • tab focus"
            elif self.focus == DatePickerFocus.MONTH:
                help_text = "←/→ month • enter return"
            else:
                help_text = "←/→ year • enter return"
            lines.append(self.help_style.render(help_text))

        content = "\n".join(lines)

        # Optional Crema box border
        if self.border is not None:
            box_style = (
                Style()
                .border(self.border)
                .border_foreground(self.border_foreground)
                .padding(0, 1)
            )
            if self.background is not None:
                box_style = box_style.background(self.background)
            return box_style.render(content)

        return content
