"""Unicode cell width calculation, ANSI sequence stripping, and safe truncation."""

from __future__ import annotations

import re
import unicodedata

# Matches all standard ANSI CSI, OSC, and 2-byte escape sequences
ANSI_REGEX = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape codes from text."""
    return ANSI_REGEX.sub("", text)


def char_width(char: str) -> int:
    """Return the visual cell width of a single Unicode character.

    - Wide / Fullwidth characters and emojis occupy 2 cells.
    - Zero-width joiners and non-spacing combining marks occupy 0 cells.
    - Standard characters occupy 1 cell.
    """
    if not char:
        return 0

    code = ord(char[0])

    # Control characters / null
    if code < 32 or (127 <= code < 160):
        return 0

    # Combining marks, non-spacing marks, enclosing marks, format chars (like ZWJ)
    cat = unicodedata.category(char)
    if cat in ("Mn", "Me", "Cf"):
        return 0

    # East Asian Width properties
    # W = Wide, F = Fullwidth
    eaw = unicodedata.east_asian_width(char)
    if eaw in ("W", "F"):
        return 2

    # Common Emoji Ranges (pictographs, emoticons, transport, supplemental symbols)
    # Emojis in the Supplementary Multilingual Plane (SMP) that may have EAW='N'
    if 0x1F300 <= code <= 0x1FAFF:
        return 2

    return 1


def string_width(text: str) -> int:
    """Calculate total visual cell width of a string, ignoring ANSI escape sequences."""
    clean = strip_ansi(text)
    return sum(char_width(ch) for ch in clean)


def truncate_ansi(text: str, max_width: int, tail: str = "…") -> str:
    """Truncate a styled string to max_width visual cells without corrupting ANSI codes."""
    if max_width <= 0:
        return ""

    if string_width(text) <= max_width:
        return text

    tail_w = string_width(tail)
    target_w = max(0, max_width - tail_w)

    current_w = 0
    buf: list[str] = []
    ansi_open: list[str] = []

    tokens = ANSI_REGEX.split(text)
    codes = ANSI_REGEX.findall(text)

    # Reconstruct tokens with their corresponding codes
    for idx, token in enumerate(tokens):
        if idx > 0 and idx - 1 < len(codes):
            code = codes[idx - 1]
            buf.append(code)
            if code == "\x1b[0m":
                ansi_open.clear()
            else:
                ansi_open.append(code)

        for ch in token:
            cw = char_width(ch)
            if current_w + cw > target_w:
                # Add tail and close any open ANSI styles
                buf.append(tail)
                if ansi_open:
                    buf.append("\x1b[0m")
                return "".join(buf)

            buf.append(ch)
            current_w += cw

    buf.append(tail)
    if ansi_open:
        buf.append("\x1b[0m")
    return "".join(buf)
