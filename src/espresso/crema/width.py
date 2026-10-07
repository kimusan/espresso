"""Unicode cell width calculation, ANSI sequence stripping, and safe truncation."""

from __future__ import annotations

import bisect
import re
import unicodedata
from functools import lru_cache
from typing import Iterator

from espresso.crema._cell_widths import CELL_WIDTHS

# Matches all standard ANSI CSI, OSC, and 2-byte escape sequences
ANSI_REGEX = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Set of BMP emojis that promote to 2 cells with VS16 or when rendered as emoji
EMOJI_BMP_WIDE: set[int] = {
    0x231A, 0x231B, 0x23E9, 0x23EA, 0x23EB, 0x23EC, 0x23ED, 0x23EE, 0x23EF, 0x23F0, 0x23F3,
    0x25FD, 0x25FE, 0x2614, 0x2615, 0x2648, 0x2649, 0x264A, 0x264B, 0x264C, 0x264D, 0x264E,
    0x264F, 0x2650, 0x2651, 0x2652, 0x2653, 0x267F, 0x2693, 0x26A1, 0x26AA, 0x26AB, 0x26BD,
    0x26BE, 0x26C4, 0x26C5, 0x26CE, 0x26D4, 0x26EA, 0x26F2, 0x26F3, 0x26F5, 0x26FA, 0x26FD,
    0x2702, 0x2705, 0x2708, 0x2709, 0x270A, 0x270B, 0x270C, 0x270D, 0x270F, 0x2712, 0x2714,
    0x2716, 0x271D, 0x2721, 0x2728, 0x2733, 0x2734, 0x2744, 0x2747, 0x274C, 0x274E, 0x2753,
    0x2754, 0x2755, 0x2757, 0x2763, 0x2764, 0x2795, 0x2796, 0x2797, 0x27A1, 0x27B0, 0x27BF,
    0x2B05, 0x2B06, 0x2B07, 0x2B1B, 0x2B1C, 0x2B50, 0x2B55,
}


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape codes from text."""
    return ANSI_REGEX.sub("", text)


@lru_cache(maxsize=8192)
def codepoint_width(code: int) -> int:
    """Return the visual cell width (0, 1, or 2) of a single Unicode codepoint.

    - Wide / Fullwidth characters and emojis occupy 2 cells.
    - Zero-width joiners, skin-tone modifiers, format controls, and combining marks occupy 0 cells.
    - Standard characters and fallback/unassigned glyphs occupy 1 cell.
    """
    # Control characters / null
    if code < 32 or (127 <= code < 160):
        return 0

    # Fast-path for standard ASCII characters
    if code < 127:
        return 1

    # Common zero-width formatting codepoints
    if code in (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0xFEFF):
        return 0

    # Skin tone modifiers (Fitzpatrick scale: U+1F3FB to U+1F3FF) modify the base emoji
    if 0x1F3FB <= code <= 0x1F3FF:
        return 0

    # Tag characters for subdivision flags (U+E0020 to U+E007F)
    if 0xE0020 <= code <= 0xE007F:
        return 0

    # Variation selectors (VS1-VS16: U+FE00-U+FE0F, VS17-VS256: U+E0100-U+E01EF)
    if (0xFE00 <= code <= 0xFE0F) or (0xE0100 <= code <= 0xE01EF):
        return 0

    # Combining marks, non-spacing marks, enclosing marks, format chars
    ch = chr(code)
    cat = unicodedata.category(ch)
    if cat in ("Mn", "Me", "Cf"):
        return 0

    # Look up in standard CELL_WIDTHS table
    idx = bisect.bisect_right(CELL_WIDTHS, (code, float("inf"), float("inf"))) - 1
    if idx >= 0:
        start, end, w = CELL_WIDTHS[idx]
        if start <= code <= end:
            return 0 if w < 0 else w

    # East Asian Width properties (W = Wide, F = Fullwidth)
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):
        return 2

    return 1


def char_width(char: str) -> int:
    """Return the visual cell width of a single Unicode character."""
    if not char:
        return 0
    return codepoint_width(ord(char[0]))


def iter_graphemes(clean_text: str) -> Iterator[tuple[str, int]]:
    """Yield (grapheme_string, cell_width) for each visual cluster in clean (non-ANSI) text.

    Correctly handles:
    - Zero Width Joiner (ZWJ) sequences (e.g. 🏴‍☠️, 🏳️‍🌈, 👨‍👩‍👧‍👦, 🧑‍💻)
    - Ligatures without explicit ZWJ (e.g. 🏴☠️ or 🏴☠ pirate flag)
    - Skin-tone modifiers (Fitzpatrick scale: 👍🏽, 👩🏾‍🦱)
    - Regional Indicator flag pairs (e.g. 🇩🇰, 🇺🇸)
    - Keycap sequences (e.g. 1️⃣, #️⃣)
    - Variation Selectors (VS16 emoji presentation, VS15 text presentation)
    - Combining diacritics / marks (e.g. e + ◌́)
    """
    i = 0
    n = len(clean_text)
    while i < n:
        start = i
        ch = clean_text[i]
        code = ord(ch)

        # 1. Regional Indicator pairs (Country flags e.g. 🇩🇰)
        if 0x1F1E6 <= code <= 0x1F1FF:
            if i + 1 < n and 0x1F1E6 <= ord(clean_text[i + 1]) <= 0x1F1FF:
                yield clean_text[i : i + 2], 2
                i += 2
                continue
            else:
                yield ch, 1
                i += 1
                continue

        # 2. Subdivision flags (U+1F3F4 followed by tag chars up to U+E007F)
        if code == 0x1F3F4 and i + 1 < n and (0xE0020 <= ord(clean_text[i + 1]) <= 0xE007F):
            j = i + 1
            while j < n and (0xE0020 <= ord(clean_text[j]) <= 0xE007F):
                j += 1
            yield clean_text[i:j], 2
            i = j
            continue

        # 3. Base character width
        base_w = char_width(ch)
        i += 1

        # 4. Consume combining characters, variation selectors, skin tone modifiers, and ZWJ sequences
        while i < n:
            next_ch = clean_text[i]
            next_code = ord(next_ch)

            # Keycap combiner: base + (optional VS16) + \u20e3
            if next_ch == "\u20e3":
                base_w = 2
                i += 1
                break

            # Variation selector 16: promotes base_w 1 to 2 for emoji presentation
            if next_ch == "\ufe0f":
                if base_w == 1:
                    base_w = 2
                i += 1
                continue

            # Variation selector 15 (text presentation): forces 1 cell
            if next_ch == "\ufe0e":
                base_w = 1
                i += 1
                continue

            # Zero-width joiner (ZWJ) sequence:
            # Terminals (VTE, Alacritty, xterm) do not ligature multi-emoji sequences like flags/families
            # into a single 2-cell glyph, advancing the cursor for each distinct emoji component.
            # However, gender signs (♂ U+2642, ♀ U+2640) and hair style modifiers (U+1F9B0..U+1F9B3)
            # modify the preceding person emoji and do NOT add extra cell width (width remains 2).
            if next_ch == "\u200d":
                i += 1
                if i < n:
                    joined_ch = clean_text[i]
                    joined_code = ord(joined_ch)
                    i += 1
                    has_vs16 = False
                    if i < n and clean_text[i] == "\ufe0f":
                        has_vs16 = True
                        i += 1
                    elif i < n and clean_text[i] == "\ufe0e":
                        i += 1

                    if joined_code in (0x2640, 0x2642) or (0x1F9B0 <= joined_code <= 0x1F9B3):
                        pass
                    else:
                        joined_w = codepoint_width(joined_code)
                        if has_vs16 and joined_w == 1:
                            joined_w = 2
                        base_w += joined_w
                continue

            # Skin tone modifiers (Fitzpatrick)
            if 0x1F3FB <= next_code <= 0x1F3FF:
                base_w = max(base_w, 2)
                i += 1
                continue

            # Any 0-width codepoints (combining diacritics, variation selectors, tags, format controls)
            if codepoint_width(next_code) == 0:
                i += 1
                continue

            break

        yield clean_text[start:i], base_w


def string_width(text: str) -> int:
    """Calculate total visual cell width of a string, ignoring ANSI escape sequences."""
    return sum(w for _, w in iter_graphemes(strip_ansi(text)))


def truncate_ansi(text: str, max_width: int, tail: str = "…") -> str:
    """Truncate a styled string to max_width visual cells without corrupting ANSI codes or splitting graphemes."""
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
            if code in ("\x1b[0m", "\x1b[m"):
                ansi_open.clear()
            else:
                ansi_open.append(code)

        for cluster, cw in iter_graphemes(token):
            if current_w + cw > target_w:
                # Add tail and close any open ANSI styles
                buf.append(tail)
                if ansi_open:
                    buf.append("\x1b[0m")
                return "".join(buf)

            buf.append(cluster)
            current_w += cw

    buf.append(tail)
    if ansi_open:
        buf.append("\x1b[0m")
    return "".join(buf)
