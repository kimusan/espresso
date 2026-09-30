"""Unit tests for the DatePicker component."""

from __future__ import annotations

import unittest
from datetime import date

from espresso import KeyMsg, MouseAction, MouseButton, MouseMsg
from espresso.beans import (
    DateChangeMsg,
    DatePicker,
    DatePickerFocus,
    DateSelectMsg,
)
from espresso.crema import strip_ansi


class TestDatePicker(unittest.TestCase):
    def test_init_default(self) -> None:
        dp = DatePicker()
        self.assertEqual(dp.cursor_date, date.today())
        self.assertIsNone(dp.value)
        self.assertEqual(dp.focus, DatePickerFocus.CALENDAR)
        self.assertTrue(dp.show_header)
        self.assertTrue(dp.show_help)

    def test_init_explicit(self) -> None:
        target = date(2026, 10, 15)
        dp = DatePicker(
            value=target,
            cursor_date=target,
            min_date=date(2026, 10, 1),
            max_date=date(2026, 10, 31),
            focus=DatePickerFocus.MONTH,
        )
        self.assertEqual(dp.value, target)
        self.assertEqual(dp.selected_date, target)
        self.assertEqual(dp.cursor_date, target)
        self.assertEqual(dp.focus, DatePickerFocus.MONTH)
        self.assertTrue(dp.is_selected(target))
        self.assertTrue(dp.is_cursor(target))
        self.assertFalse(dp.is_disabled(target))
        self.assertTrue(dp.is_disabled(date(2026, 9, 30)))
        self.assertTrue(dp.is_disabled(date(2026, 11, 1)))

    def test_navigation_days(self) -> None:
        start = date(2026, 10, 15)
        dp = DatePicker(cursor_date=start)

        # Move right (+1 day)
        dp, cmd = dp.update(KeyMsg("right"))
        self.assertEqual(dp.cursor_date, date(2026, 10, 16))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertEqual(msg, DateChangeMsg(date(2026, 10, 16)))

        # Move left (-1 day)
        dp, _ = dp.update(KeyMsg("left"))
        self.assertEqual(dp.cursor_date, date(2026, 10, 15))

        # Move down (+7 days)
        dp, _ = dp.update(KeyMsg("down"))
        self.assertEqual(dp.cursor_date, date(2026, 10, 22))

        # Move up (-7 days)
        dp, _ = dp.update(KeyMsg("up"))
        self.assertEqual(dp.cursor_date, date(2026, 10, 15))

    def test_month_and_year_navigation(self) -> None:
        start = date(2026, 10, 31)
        dp = DatePicker(cursor_date=start)

        # Next month (October -> November has 30 days, clamps day)
        dp, _ = dp.update(KeyMsg("]"))
        self.assertEqual(dp.cursor_date, date(2026, 11, 30))

        # Previous month (November -> October)
        dp, _ = dp.update(KeyMsg("["))
        self.assertEqual(dp.cursor_date, date(2026, 10, 30))

        # Next year
        dp, _ = dp.update(KeyMsg("}"))
        self.assertEqual(dp.cursor_date, date(2027, 10, 30))

        # Previous year
        dp, _ = dp.update(KeyMsg("{"))
        self.assertEqual(dp.cursor_date, date(2026, 10, 30))

        # Leap year leap day test
        leap_day = date(2024, 2, 29)
        dp_leap = DatePicker(cursor_date=leap_day)
        dp_leap, _ = dp_leap.update(KeyMsg("}"))
        self.assertEqual(dp_leap.cursor_date, date(2025, 2, 28))

    def test_focus_cycling(self) -> None:
        dp = DatePicker(focus=DatePickerFocus.CALENDAR)

        # Tab: CALENDAR -> MONTH -> YEAR -> CALENDAR
        dp, _ = dp.update(KeyMsg("tab"))
        self.assertEqual(dp.focus, DatePickerFocus.MONTH)
        dp, _ = dp.update(KeyMsg("tab"))
        self.assertEqual(dp.focus, DatePickerFocus.YEAR)
        dp, _ = dp.update(KeyMsg("tab"))
        self.assertEqual(dp.focus, DatePickerFocus.CALENDAR)

        # Shift+Tab: reverse cycle
        dp, _ = dp.update(KeyMsg("shift+tab"))
        self.assertEqual(dp.focus, DatePickerFocus.YEAR)
        dp, _ = dp.update(KeyMsg("shift+tab"))
        self.assertEqual(dp.focus, DatePickerFocus.MONTH)
        dp, _ = dp.update(KeyMsg("shift+tab"))
        self.assertEqual(dp.focus, DatePickerFocus.CALENDAR)

    def test_month_focus_controls(self) -> None:
        dp = DatePicker(cursor_date=date(2026, 5, 10), focus=DatePickerFocus.MONTH)
        dp, _ = dp.update(KeyMsg("right"))
        self.assertEqual(dp.cursor_date.month, 6)
        dp, _ = dp.update(KeyMsg("left"))
        self.assertEqual(dp.cursor_date.month, 5)

        # Enter returns focus to CALENDAR
        dp, _ = dp.update(KeyMsg("enter"))
        self.assertEqual(dp.focus, DatePickerFocus.CALENDAR)

    def test_year_focus_controls(self) -> None:
        dp = DatePicker(cursor_date=date(2026, 5, 10), focus=DatePickerFocus.YEAR)
        dp, _ = dp.update(KeyMsg("right"))
        self.assertEqual(dp.cursor_date.year, 2027)
        dp, _ = dp.update(KeyMsg("left"))
        self.assertEqual(dp.cursor_date.year, 2026)

        # Esc returns focus to CALENDAR
        dp, _ = dp.update(KeyMsg("esc"))
        self.assertEqual(dp.focus, DatePickerFocus.CALENDAR)

    def test_select_date_action(self) -> None:
        target = date(2026, 7, 4)
        dp = DatePicker(cursor_date=target)

        # Pressing Enter selects date
        dp, cmd = dp.update(KeyMsg("enter"))
        self.assertEqual(dp.value, target)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertEqual(msg, DateSelectMsg(target))

    def test_min_max_date_clamping(self) -> None:
        min_d = date(2026, 10, 10)
        max_d = date(2026, 10, 15)
        dp = DatePicker(cursor_date=date(2026, 10, 10), min_date=min_d, max_date=max_d)

        # Attempt to move left past min_date
        dp, _ = dp.update(KeyMsg("left"))
        self.assertEqual(dp.cursor_date, min_d)

        # Move to max_date
        dp, _ = dp.update(KeyMsg("down"))
        self.assertEqual(dp.cursor_date, max_d)

        # Attempt to move right past max_date
        dp, _ = dp.update(KeyMsg("right"))
        self.assertEqual(dp.cursor_date, max_d)

    def test_today_shortcut(self) -> None:
        past = date(2020, 1, 1)
        dp = DatePicker(cursor_date=past)
        dp, cmd = dp.update(KeyMsg("t"))
        self.assertEqual(dp.cursor_date, date.today())
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd(), DateChangeMsg(date.today()))

    def test_mouse_interactions(self) -> None:
        dp = DatePicker(cursor_date=date(2026, 10, 15), border=None)

        # Mouse wheel up -> previous month
        dp, _ = dp.update(MouseMsg(action=MouseAction.PRESS, button=MouseButton.WHEEL_UP, x=0, y=0))
        self.assertEqual(dp.cursor_date.month, 9)

        # Mouse wheel down -> next month
        dp, _ = dp.update(MouseMsg(action=MouseAction.PRESS, button=MouseButton.WHEEL_DOWN, x=0, y=0))
        self.assertEqual(dp.cursor_date.month, 10)

        # Click on left arrow (<) in header (x=1, y=0)
        dp, _ = dp.update(MouseMsg(action=MouseAction.PRESS, button=MouseButton.LEFT, x=1, y=0))
        self.assertEqual(dp.cursor_date.month, 9)

        # Click on right arrow (>) in header (x=18, y=0)
        dp, _ = dp.update(MouseMsg(action=MouseAction.PRESS, button=MouseButton.LEFT, x=18, y=0))
        self.assertEqual(dp.cursor_date.month, 10)

        # Click on Month text in header (x=6, y=0)
        dp, _ = dp.update(MouseMsg(action=MouseAction.PRESS, button=MouseButton.LEFT, x=6, y=0))
        self.assertEqual(dp.focus, DatePickerFocus.MONTH)

    def test_view_content(self) -> None:
        target = date(2026, 10, 15)
        dp = DatePicker(cursor_date=target, value=target)
        view_text = dp.view()
        clean = strip_ansi(view_text)

        # Header contains Month and Year
        self.assertIn("October", clean)
        self.assertIn("2026", clean)

        # Contains weekday abbreviations
        self.assertIn("Su", clean)
        self.assertIn("Mo", clean)
        self.assertIn("Fr", clean)

        # Contains day numbers
        self.assertIn("15", clean)
        self.assertIn("31", clean)

        # Contains help text
        self.assertIn("arrows nav", clean)


if __name__ == "__main__":
    unittest.main()
