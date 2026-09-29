"""Declarative fluent styling engine (Lip Gloss equivalent for Python)."""

from __future__ import annotations

import copy
from enum import Enum
from typing import Any, Union

from espresso.crema.border import Border
from espresso.crema.color import Color, is_no_color, parse_color
from espresso.crema.width import char_width, string_width, strip_ansi, truncate_ansi


class Align(Enum):
    """Horizontal and vertical alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


def _parse_box_sides(top: int, right: int | None = None, bottom: int | None = None, left: int | None = None) -> tuple[int, int, int, int]:
    """Parse CSS-style shorthand for 1, 2, 3, or 4 arguments into (top, right, bottom, left)."""
    if right is None and bottom is None and left is None:
        return (top, top, top, top)
    if bottom is None and left is None and right is not None:
        return (top, right, top, right)
    if left is None and right is not None and bottom is not None:
        return (top, right, bottom, right)
    return (top, right or 0, bottom or 0, left or 0)


class Style:
    """A fluent, chainable, immutable styling rule for terminal text."""

    def __init__(self) -> None:
        # Text styling
        self._bold = False
        self._faint = False
        self._italic = False
        self._underline = False
        self._strikethrough = False
        self._reverse = False
        self._fg: Color | None = None
        self._bg: Color | None = None

        # Dimensions & Alignment
        self._width: int | None = None
        self._height: int | None = None
        self._h_align: Align = Align.LEFT
        self._v_align: Align = Align.TOP

        # Box Model
        self._padding: tuple[int, int, int, int] = (0, 0, 0, 0)  # top, right, bottom, left
        self._margin: tuple[int, int, int, int] = (0, 0, 0, 0)
        self._border: Border | None = None
        self._border_sides: tuple[bool, bool, bool, bool] = (True, True, True, True)  # top, right, bottom, left
        self._border_fg: Color | None = None
        self._border_bg: Color | None = None
        self._border_title: str | None = None
        self._border_title_align: Align = Align.LEFT

    def copy(self) -> Style:
        """Create a deep copy of this Style for modification."""
        return copy.deepcopy(self)

    # Text attributes
    def bold(self, val: bool = True) -> Style:
        """Set or unset the bold text attribute."""
        s = self.copy()
        s._bold = val
        return s

    def faint(self, val: bool = True) -> Style:
        """Set or unset the faint/dim text attribute."""
        s = self.copy()
        s._faint = val
        return s

    def italic(self, val: bool = True) -> Style:
        """Set or unset the italic text attribute."""
        s = self.copy()
        s._italic = val
        return s

    def underline(self, val: bool = True) -> Style:
        """Set or unset the underline text attribute."""
        s = self.copy()
        s._underline = val
        return s

    def strikethrough(self, val: bool = True) -> Style:
        """Set or unset the strikethrough text attribute."""
        s = self.copy()
        s._strikethrough = val
        return s

    def reverse(self, val: bool = True) -> Style:
        """Set or unset the reverse video text attribute."""
        s = self.copy()
        s._reverse = val
        return s

    # Colors
    def foreground(self, color: Union[str, int, Color, tuple[int, int, int]]) -> Style:
        """Set the foreground text color (hex, ANSI int, RGB tuple, or Color)."""
        s = self.copy()
        s._fg = parse_color(color)
        return s

    def background(self, color: Union[str, int, Color, tuple[int, int, int]]) -> Style:
        """Set the background color (hex, ANSI int, RGB tuple, or Color)."""
        s = self.copy()
        s._bg = parse_color(color)
        return s

    # Sizing & Alignment
    def width(self, w: int | None) -> Style:
        """Set target inner content width in visual cells."""
        s = self.copy()
        s._width = w
        return s

    def height(self, h: int | None) -> Style:
        """Set target minimum box height in rows."""
        s = self.copy()
        s._height = h
        return s

    def align(self, h_align: Align) -> Style:
        """Set horizontal text alignment (LEFT, CENTER, RIGHT)."""
        s = self.copy()
        s._h_align = h_align
        return s

    def align_vertical(self, v_align: Align) -> Style:
        """Set vertical text alignment (TOP, CENTER, BOTTOM) when height is set."""
        s = self.copy()
        s._v_align = v_align
        return s

    # Spacing
    def padding(self, top: int, right: int | None = None, bottom: int | None = None, left: int | None = None) -> Style:
        """Set inner padding using CSS shorthand: (all) or (top/bottom, left/right) or (top, right, bottom, left)."""
        s = self.copy()
        s._padding = _parse_box_sides(top, right, bottom, left)
        return s

    def margin(self, top: int, right: int | None = None, bottom: int | None = None, left: int | None = None) -> Style:
        """Set outer margin using CSS shorthand: (all) or (top/bottom, left/right) or (top, right, bottom, left)."""
        s = self.copy()
        s._margin = _parse_box_sides(top, right, bottom, left)
        return s

    # Borders
    def border(self, b: Border | None, top: bool = True, right: bool = True, bottom: bool = True, left: bool = True) -> Style:
        """Set the border characters and selectively enable/disable specific sides."""
        s = self.copy()
        s._border = b
        s._border_sides = (top, right, bottom, left)
        return s

    def border_foreground(self, color: Union[str, int, Color, tuple[int, int, int]]) -> Style:
        """Set the border foreground color."""
        s = self.copy()
        s._border_fg = parse_color(color)
        return s

    def border_background(self, color: Union[str, int, Color, tuple[int, int, int]]) -> Style:
        """Set the border background color."""
        s = self.copy()
        s._border_bg = parse_color(color)
        return s

    def border_title(self, title: str | None, align: Align = Align.LEFT) -> Style:
        """Embed an optional styled title into the top border line."""
        s = self.copy()
        s._border_title = title
        s._border_title_align = align
        return s

    # Rendering
    def _text_prefix(self) -> str:
        """Generate open ANSI escape sequences for text attributes and colors."""
        if is_no_color():
            return ""
        codes: list[str] = []
        if self._bold:
            codes.append("\x1b[1m")
        if self._faint:
            codes.append("\x1b[2m")
        if self._italic:
            codes.append("\x1b[3m")
        if self._underline:
            codes.append("\x1b[4m")
        if self._strikethrough:
            codes.append("\x1b[9m")
        if self._reverse:
            codes.append("\x1b[7m")
        if self._fg is not None:
            codes.append(self._fg.render_fg())
        if self._bg is not None:
            codes.append(self._bg.render_bg())
        return "".join(codes)

    def _border_prefix(self) -> str:
        if is_no_color():
            return ""
        codes = []
        if self._border_fg is not None:
            codes.append(self._border_fg.render_fg())
        if self._border_bg is not None:
            codes.append(self._border_bg.render_bg())
        return "".join(codes)

    def render(self, *parts: Any) -> str:
        """Format and render text content according to the style rules."""
        raw_text = " ".join(str(p) for p in parts)
        lines = raw_text.splitlines() if raw_text else [""]

        # 1. Determine inner content width
        max_line_w = max((string_width(l) for l in lines), default=0)
        target_inner_w = max_line_w
        if self._width is not None:
            target_inner_w = max(self._width, max_line_w)
        elif self._border_title is not None and self._border is not None:
            pad_top, pad_right, pad_bottom, pad_left = self._padding
            title_w = string_width(self._border_title)
            needed_w = max(0, title_w + 2 - (pad_left + pad_right))
            target_inner_w = max(target_inner_w, needed_w)

        # 2. Horizontal alignment & line padding
        aligned_lines: list[str] = []
        for line in lines:
            line_w = string_width(line)
            diff = max(0, target_inner_w - line_w)
            if self._h_align == Align.CENTER:
                left_pad = diff // 2
                right_pad = diff - left_pad
                aligned_lines.append(f"{' ' * left_pad}{line}{' ' * right_pad}")
            elif self._h_align == Align.RIGHT:
                aligned_lines.append(f"{' ' * diff}{line}")
            else:  # LEFT
                aligned_lines.append(f"{line}{' ' * diff}")

        # 3. Apply text styling to the lines
        prefix = self._text_prefix()
        suffix = "\x1b[0m" if prefix else ""
        styled_lines = [f"{prefix}{l}{suffix}" if l.strip() or prefix else l for l in aligned_lines]

        # 4. Apply box model padding (top, right, bottom, left)
        pad_top, pad_right, pad_bottom, pad_left = self._padding
        padded_lines: list[str] = []
        inner_box_w = target_inner_w + pad_left + pad_right

        bg_open = ""
        bg_close = ""
        if self._bg is not None and not is_no_color():
            bg_open = self._bg.render_bg()
            bg_close = "\x1b[0m"

        blank_row = f"{bg_open}{' ' * inner_box_w}{bg_close}" if bg_open else " " * inner_box_w
        left_pad_str = f"{bg_open}{' ' * pad_left}{bg_close}" if (bg_open and pad_left > 0) else " " * pad_left
        right_pad_str = f"{bg_open}{' ' * pad_right}{bg_close}" if (bg_open and pad_right > 0) else " " * pad_right

        for _ in range(pad_top):
            padded_lines.append(blank_row)

        for line in styled_lines:
            padded_lines.append(f"{left_pad_str}{line}{right_pad_str}")

        for _ in range(pad_bottom):
            padded_lines.append(blank_row)

        # 5. Apply borders
        bordered_lines: list[str] = []
        b_prefix = self._border_prefix()
        b_suffix = "\x1b[0m" if b_prefix else ""

        if self._border is not None:
            b = self._border
            b_top, b_right, b_bottom, b_left = self._border_sides

            # Top border row
            if b_top:
                tl = b.top_left if b_left else ""
                tr = b.top_right if b_right else ""
                if self._border_title and inner_box_w > 0:
                    title = self._border_title
                    avail_w = max(0, inner_box_w - 2) if inner_box_w >= 4 else inner_box_w
                    if string_width(title) > avail_w:
                        title = truncate_ansi(title, avail_w)
                    t_width = string_width(title)
                    remaining = max(0, inner_box_w - t_width)

                    if self._border_title_align == Align.CENTER:
                        left_len = remaining // 2
                        right_len = remaining - left_len
                    elif self._border_title_align == Align.RIGHT:
                        left_len = max(0, remaining - 1) if remaining >= 1 else 0
                        right_len = remaining - left_len
                    else:  # Align.LEFT
                        left_len = 1 if remaining >= 1 else 0
                        right_len = remaining - left_len

                    left_bar = b.top * left_len
                    right_bar = b.top * right_len

                    left_part = f"{b_prefix}{tl}{left_bar}{b_suffix}" if (tl or left_bar) else ""
                    right_part = f"{b_prefix}{right_bar}{tr}{b_suffix}" if (right_bar or tr) else ""
                    title_part = title if (title.endswith("\x1b[0m") or "\x1b[" not in title) else f"{title}\x1b[0m"

                    bordered_lines.append(f"{left_part}{title_part}{right_part}")
                else:
                    border_bar = b.top * inner_box_w
                    bordered_lines.append(f"{b_prefix}{tl}{border_bar}{tr}{b_suffix}")

            # Content rows with side borders
            for row in padded_lines:
                left_char = f"{b_prefix}{b.left}{b_suffix}" if b_left else ""
                right_char = f"{b_prefix}{b.right}{b_suffix}" if b_right else ""
                bordered_lines.append(f"{left_char}{row}{right_char}")

            # Bottom border row
            if b_bottom:
                bl = b.bottom_left if b_left else ""
                br = b.bottom_right if b_right else ""
                border_bar = b.bottom * inner_box_w
                bordered_lines.append(f"{b_prefix}{bl}{border_bar}{br}{b_suffix}")
        else:
            bordered_lines = padded_lines

        # 6. Apply height & vertical alignment if height set
        if self._height is not None and len(bordered_lines) < self._height:
            box_w = string_width(bordered_lines[0]) if bordered_lines else inner_box_w
            v_diff = self._height - len(bordered_lines)
            empty_row = f"{bg_open}{' ' * box_w}{bg_close}" if (bg_open and self._border is None) else " " * box_w
            if self._v_align == Align.BOTTOM:
                bordered_lines = [empty_row] * v_diff + bordered_lines
            elif self._v_align == Align.CENTER:
                top_v = v_diff // 2
                bottom_v = v_diff - top_v
                bordered_lines = [empty_row] * top_v + bordered_lines + [empty_row] * bottom_v
            else:  # TOP
                bordered_lines = bordered_lines + [empty_row] * v_diff

        # 7. Apply margins (top, right, bottom, left)
        m_top, m_right, m_bottom, m_left = self._margin
        result_lines: list[str] = []
        row_w = string_width(bordered_lines[0]) if bordered_lines else 0
        total_w = row_w + m_left + m_right
        margin_empty = " " * total_w

        for _ in range(m_top):
            result_lines.append(margin_empty)

        for row in bordered_lines:
            result_lines.append(f"{' ' * m_left}{row}{' ' * m_right}")

        for _ in range(m_bottom):
            result_lines.append(margin_empty)

        return "\n".join(result_lines)

    def __call__(self, *parts: Any) -> str:
        return self.render(*parts)
