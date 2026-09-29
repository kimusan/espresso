"""TrueColor linear color gradients for terminal text."""

from __future__ import annotations

from typing import Union

from espresso.crema.color import TrueColor, is_no_color
from espresso.crema.width import strip_ansi


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    """Parse a hex color string ('#RRGGBB', 'RRGGBB', '#RGB', or 'RGB') into an (R, G, B) tuple."""
    h = hex_code.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Invalid hex color string: {hex_code}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _to_rgb(c: Union[str, tuple[int, int, int], TrueColor]) -> tuple[int, int, int]:
    if isinstance(c, TrueColor):
        return c.r, c.g, c.b
    if isinstance(c, (tuple, list)) and len(c) == 3:
        return int(c[0]), int(c[1]), int(c[2])
    if isinstance(c, str):
        return hex_to_rgb(c)
    raise ValueError(f"Cannot convert color to RGB: {c}")


def gradient(
    start_color: Union[str, tuple[int, int, int], TrueColor],
    end_color: Union[str, tuple[int, int, int], TrueColor],
    steps: int,
) -> list[TrueColor]:
    """Generate a list of TrueColor steps linearly interpolating between two colors."""
    if steps <= 0:
        return []

    r1, g1, b1 = _to_rgb(start_color)
    r2, g2, b2 = _to_rgb(end_color)

    if steps == 1:
        return [TrueColor(r1, g1, b1)]

    colors: list[TrueColor] = []
    denom = steps - 1
    for i in range(steps):
        t = i / denom
        r = max(0, min(255, round(r1 + t * (r2 - r1))))
        g = max(0, min(255, round(g1 + t * (g2 - g1))))
        b = max(0, min(255, round(b1 + t * (b2 - b1))))
        colors.append(TrueColor(r, g, b))

    return colors


def linear_gradient(text: str, start_hex: str, end_hex: str) -> str:
    """Smoothly interpolate 24-bit TrueColor foreground RGB across the characters of a string.

    - Preserves newlines and prevents terminal color bleeding.
    - Honors the NO_COLOR standard.
    """
    if not text:
        return ""

    if is_no_color():
        return strip_ansi(text)

    clean = strip_ansi(text)
    if not clean:
        return ""

    # Count non-newline printable characters across which to interpolate the gradient
    printable_chars = [ch for ch in clean if ch != "\n"]
    n_chars = len(printable_chars)
    if n_chars == 0:
        return clean

    colors = gradient(start_hex, end_hex, n_chars)

    out: list[str] = []
    c_idx = 0
    in_color = False

    for ch in clean:
        if ch == "\n":
            if in_color:
                out.append("\x1b[0m")
                in_color = False
            out.append("\n")
        else:
            col = colors[c_idx]
            c_idx += 1
            out.append(f"{col.render_fg()}{ch}")
            in_color = True

    if in_color:
        out.append("\x1b[0m")

    return "".join(out)
