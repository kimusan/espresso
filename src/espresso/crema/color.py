"""Color representations and ANSI color sequence generators.

Supports:
- TrueColor 24-bit RGB (hex strings like "#FAFAFA" or RGB tuples)
- 256-color ANSI palette (0-255)
- Standard 16 terminal colors
- NO_COLOR environment standard compliance
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Union


def is_no_color() -> bool:
    """Return True if NO_COLOR environment variable is set (https://no-color.org)."""
    return bool(os.environ.get("NO_COLOR"))


class Color:
    """Base class for color representations."""

    def render_fg(self) -> str:
        """Return ANSI escape code for setting foreground color."""
        return ""

    def render_bg(self) -> str:
        """Return ANSI escape code for setting background color."""
        return ""


@dataclass(frozen=True)
class TrueColor(Color):
    """24-bit TrueColor RGB representation."""

    r: int
    g: int
    b: int

    def render_fg(self) -> str:
        if is_no_color():
            return ""
        return f"\x1b[38;2;{self.r};{self.g};{self.b}m"

    def render_bg(self) -> str:
        if is_no_color():
            return ""
        return f"\x1b[48;2;{self.r};{self.g};{self.b}m"


@dataclass(frozen=True)
class ANSIColor(Color):
    """8-bit ANSI 256 color representation (0-255)."""

    code: int

    def render_fg(self) -> str:
        if is_no_color():
            return ""
        if self.code < 8:
            return f"\x1b[{30 + self.code}m"
        elif self.code < 16:
            return f"\x1b[{90 + (self.code - 8)}m"
        return f"\x1b[38;5;{self.code}m"

    def render_bg(self) -> str:
        if is_no_color():
            return ""
        if self.code < 8:
            return f"\x1b[{40 + self.code}m"
        elif self.code < 16:
            return f"\x1b[{100 + (self.code - 8)}m"
        return f"\x1b[48;5;{self.code}m"


@dataclass(frozen=True)
class AdaptiveColor(Color):
    """Color that switches between light and dark terminal profiles."""

    light: Color
    dark: Color

    def current(self) -> Color:
        # Default to dark theme unless COLORFGBG indicates light (e.g. bg == 15)
        # In COLORFGBG="0;15", the second number is background
        cfg = os.environ.get("COLORFGBG", "")
        if ";" in cfg:
            parts = cfg.split(";")
            if len(parts) >= 2 and parts[-1].strip() in ("15", "7"):
                return self.light
        return self.dark

    def render_fg(self) -> str:
        return self.current().render_fg()

    def render_bg(self) -> str:
        return self.current().render_bg()


def parse_color(c: Union[str, int, Color, tuple[int, int, int]]) -> Color:
    """Parse a color from hex string, ANSI int, RGB tuple, or Color instance."""
    if isinstance(c, Color):
        return c

    if isinstance(c, int):
        return ANSIColor(c)

    if isinstance(c, (tuple, list)) and len(c) == 3:
        return TrueColor(int(c[0]), int(c[1]), int(c[2]))

    if isinstance(c, str):
        c = c.strip()
        # Hex color: #RRGGBB or #RGB
        if c.startswith("#"):
            hex_val = c[1:]
            if len(hex_val) == 3:
                hex_val = "".join(ch * 2 for ch in hex_val)
            if len(hex_val) == 6:
                r = int(hex_val[0:2], 16)
                g = int(hex_val[2:4], 16)
                b = int(hex_val[4:6], 16)
                return TrueColor(r, g, b)
        # Numeric string: "196" -> ANSIColor(196)
        if c.isdigit():
            return ANSIColor(int(c))

    # Fallback to no-op color
    return Color()
