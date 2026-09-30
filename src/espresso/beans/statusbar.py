"""Responsive multi-section status bar component.

Modeled after knipferrc/teacup/statusbar.
Provides Left, Center, and Right section clusters, intelligent width-based
truncation, priority preservation, and powerline/pill styling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class StatusSection:
    """A single segment in a StatusBar."""

    text: str
    style: Style | None = None
    priority: int = 1  # Higher priority stays visible when space is tight
    icon: str = ""

    def render(self) -> str:
        content = f"{self.icon} {self.text}".strip() if self.icon else self.text
        if self.style is not None:
            return self.style.render(content)
        return content

    @property
    def visual_width(self) -> int:
        content = f"{self.icon} {self.text}".strip() if self.icon else self.text
        if self.style is not None:
            return string_width(self.style.render(content))
        return string_width(content)


class StatusBar(Model):
    """A responsive terminal status bar with left, center, and right sections."""

    def __init__(
        self,
        left: Sequence[StatusSection | str] = (),
        center: Sequence[StatusSection | str] = (),
        right: Sequence[StatusSection | str] = (),
        width: int = 80,
        background: str = "#1A1A24",
        separator: str = " ",
    ) -> None:
        self.left: list[StatusSection] = [
            s if isinstance(s, StatusSection) else StatusSection(text=str(s)) for s in left
        ]
        self.center: list[StatusSection] = [
            s if isinstance(s, StatusSection) else StatusSection(text=str(s), priority=0) for s in center
        ]
        self.right: list[StatusSection] = [
            s if isinstance(s, StatusSection) else StatusSection(text=str(s)) for s in right
        ]
        self.width = max(10, width)
        self.background = background
        self.separator = separator
        self.bar_style = Style().background(background)

    def set_left(self, sections: Sequence[StatusSection | str]) -> StatusBar:
        self.left = [s if isinstance(s, StatusSection) else StatusSection(text=str(s)) for s in sections]
        return self

    def set_center(self, sections: Sequence[StatusSection | str]) -> StatusBar:
        self.center = [s if isinstance(s, StatusSection) else StatusSection(text=str(s), priority=0) for s in sections]
        return self

    def set_right(self, sections: Sequence[StatusSection | str]) -> StatusBar:
        self.right = [s if isinstance(s, StatusSection) else StatusSection(text=str(s)) for s in sections]
        return self

    def set_width(self, width: int) -> StatusBar:
        self.width = max(10, width)
        return self

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[StatusBar, Cmd | None]:
        return self, None

    def view(self) -> str:
        """Render the status bar with responsive space allocation."""
        total_w = self.width

        # Render Left sections
        left_rendered = [s.render() for s in self.left]
        left_str = self.separator.join(left_rendered)
        left_w = string_width(left_str)

        # Render Right sections
        right_rendered = [s.render() for s in self.right]
        right_str = self.separator.join(right_rendered)
        right_w = string_width(right_str)

        # Render Center sections
        center_rendered = [s.render() for s in self.center]
        center_str = self.separator.join(center_rendered)
        center_w = string_width(center_str)

        # Check if everything fits comfortably
        needed_w = left_w + (1 if left_w else 0) + center_w + (1 if center_w else 0) + right_w
        if needed_w <= total_w:
            # Full layout with centered content
            # Center position relative to total width
            avail = total_w - left_w - right_w
            if center_w > 0:
                # Distribute space around center
                left_pad = max(1, (avail - center_w) // 2)
                right_pad = max(1, avail - center_w - left_pad)
                bar = f"{left_str}{' ' * left_pad}{center_str}{' ' * right_pad}{right_str}"
            else:
                bar = f"{left_str}{' ' * avail}{right_str}"
        elif left_w + right_w + 2 <= total_w:
            # Center doesn't fit, but Left and Right do: drop or truncate center
            avail = total_w - left_w - right_w
            if center_w > 0 and avail >= 6:
                trunc_center = truncate_ansi(center_str, avail - 2)
                cur_cw = string_width(trunc_center)
                rem = avail - cur_cw
                l_pad = rem // 2
                r_pad = rem - l_pad
                bar = f"{left_str}{' ' * l_pad}{trunc_center}{' ' * r_pad}{right_str}"
            else:
                bar = f"{left_str}{' ' * avail}{right_str}"
        else:
            # Tight width: drop lower priority sections from right and left
            all_sections = [(s, 'L') for s in self.left] + [(s, 'R') for s in self.right]
            # Keep highest priority sections that fit
            all_sections.sort(key=lambda item: item[0].priority, reverse=True)
            active_left: list[StatusSection] = []
            active_right: list[StatusSection] = []
            used = 0
            for sec, side in all_sections:
                sec_w = sec.visual_width + 1
                if used + sec_w <= total_w:
                    if side == 'L':
                        active_left.append(sec)
                    else:
                        active_right.append(sec)
                    used += sec_w

            l_str = self.separator.join(s.render() for s in active_left)
            r_str = self.separator.join(s.render() for s in active_right)
            rem = max(0, total_w - string_width(l_str) - string_width(r_str))
            bar = f"{l_str}{' ' * rem}{r_str}"

        # Clamp and style background
        final_line = truncate_ansi(bar, total_w)
        line_w = string_width(final_line)
        if line_w < total_w:
            final_line += " " * (total_w - line_w)

        return self.bar_style.render(final_line)
