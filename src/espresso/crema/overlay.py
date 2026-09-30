"""2D screen buffer overlay compositor for modal dialogs, popups, and toasts."""

from __future__ import annotations

import re
from typing import Optional

from espresso.crema.width import char_width, string_width

TOKEN_REGEX = re.compile(r"(\x1b\[[0-9;]*[a-zA-Z])|([^\x1b]+)|(\x1b)")


def slice_ansi(line: str, start_col: int, end_col: Optional[int] = None, pad: bool = False) -> str:
    """Slice an ANSI-escaped string by visual cell indices [start_col, end_col).

    Preserves active ANSI codes when entering the slice, preserves any ANSI
    codes inside the slice, and closes any open ANSI codes cleanly at the end.
    Does not add ANSI escape codes to unstyled plain text.
    """
    if end_col is not None and start_col >= end_col:
        return ""

    cur_col = 0
    active_codes: list[str] = []
    has_opened_style = False
    in_slice = False
    out: list[str] = []

    for match in TOKEN_REGEX.finditer(line):
        code = match.group(1)
        text = match.group(2)
        raw_esc = match.group(3)

        if code:
            if code in ("\x1b[0m", "\x1b[m"):
                active_codes.clear()
            else:
                active_codes.append(code)

            if in_slice:
                out.append(code)
            continue

        if raw_esc:
            continue

        if text:
            for ch in text:
                cw = char_width(ch)
                if cur_col + cw <= start_col:
                    cur_col += cw
                    continue

                if not in_slice:
                    in_slice = True
                    if active_codes:
                        out.extend(active_codes)
                        has_opened_style = True

                if end_col is not None and cur_col >= end_col:
                    break

                out.append(ch)
                cur_col += cw

                if end_col is not None and cur_col >= end_col:
                    break

        if end_col is not None and cur_col >= end_col:
            break

    if pad and end_col is not None and cur_col < end_col:
        out.append(" " * (end_col - cur_col))

    if has_opened_style and active_codes:
        out.append("\x1b[0m")

    return "".join(out)


def place_overlay(
    base: str,
    overlay: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    center: bool = False,
    dim_backdrop: bool = False,
) -> str:
    """Composite an overlay (modal, popup, tooltip) on top of a base view.

    Args:
        base: The background multi-line screen view.
        overlay: The foreground modal or dialog box to overlay.
        x: Optional horizontal column offset (0-indexed).
        y: Optional vertical row offset (0-indexed).
        center: If True, or if x and y are None, centers overlay over base.
        dim_backdrop: If True, applies faint/dim styling to background cells.

    Returns:
        The composited terminal view string.
    """
    base_lines = base.replace("\r\n", "\n").replace("\r", "\n").split("\n") if base else []
    overlay_lines = overlay.replace("\r\n", "\n").replace("\r", "\n").split("\n") if overlay else []

    if not overlay_lines:
        return base
    if not base_lines:
        return overlay

    base_h = len(base_lines)
    base_w = max((string_width(l) for l in base_lines), default=0)
    overlay_h = len(overlay_lines)
    overlay_w = max((string_width(l) for l in overlay_lines), default=0)

    if center or (x is None and y is None):
        pos_x = max(0, (base_w - overlay_w) // 2)
        pos_y = max(0, (base_h - overlay_h) // 2)
    else:
        pos_x = max(0, x if x is not None else 0)
        pos_y = max(0, y if y is not None else 0)

    out_lines: list[str] = []

    for r in range(base_h):
        base_r = base_lines[r]
        curr_bw = string_width(base_r)
        if curr_bw < base_w:
            base_r = f"{base_r}{' ' * (base_w - curr_bw)}"

        if pos_y <= r < pos_y + overlay_h:
            overlay_r = overlay_lines[r - pos_y]
            max_overlay_w = max(0, base_w - pos_x)
            overlay_r_visible = slice_ansi(overlay_r, 0, max_overlay_w)

            left_part = slice_ansi(base_r, 0, pos_x)
            right_part = slice_ansi(base_r, pos_x + string_width(overlay_r_visible), base_w)

            if dim_backdrop:
                if left_part:
                    left_part = f"\x1b[2m{left_part}\x1b[0m"
                if right_part:
                    right_part = f"\x1b[2m{right_part}\x1b[0m"

            out_lines.append(f"{left_part}{overlay_r_visible}{right_part}")
        else:
            if dim_backdrop and base_r.strip():
                out_lines.append(f"\x1b[2m{base_r}\x1b[0m")
            else:
                out_lines.append(base_r)

    return "\n".join(out_lines)
