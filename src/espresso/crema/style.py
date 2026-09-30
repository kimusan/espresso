"""Declarative fluent styling engine (Lip Gloss equivalent for Python)."""

from __future__ import annotations

import copy
from enum import Enum
from typing import Any, Sequence, Union

from espresso.crema.border import Border
from espresso.crema.color import Color, TrueColor, is_no_color, parse_color
from espresso.crema.gradient import multi_gradient_colors
from espresso.crema.width import char_width, string_width, strip_ansi, truncate_ansi


def _apply_horizontal_gradient_bg(
    row: str,
    colors: list[TrueColor],
    default_attr_prefix: str = "",
) -> str:
    """Render a text row across horizontal TrueColor gradient background cells."""
    if not colors or is_no_color():
        return row

    out: list[str] = []
    x = 0
    i = 0
    n = len(row)
    active_attr = default_attr_prefix
    w = len(colors)

    while i < n:
        if row[i] == "\x1b":
            j = i + 1
            while j < n and row[j] != "m":
                j += 1
            if j < n and row[j] == "m":
                seq = row[i : j + 1]
                if seq == "\x1b[0m":
                    active_attr = default_attr_prefix
                else:
                    active_attr = seq
                i = j + 1
                continue
            else:
                i += 1
                continue

        ch = row[i]
        cw = char_width(ch)
        bg = colors[min(x, w - 1)].render_bg()
        out.append(f"{bg}{active_attr}{ch}")
        x += cw
        i += 1

    out.append("\x1b[0m")
    return "".join(out)


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
        self._bg_gradient: tuple[list[Any], str] | None = None  # (stops, "vertical" | "horizontal")

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

    def background(self, color: Union[str, int, Color, tuple[int, int, int]] | None) -> Style:
        """Set the solid background color (hex, ANSI int, RGB tuple, or Color)."""
        s = self.copy()
        s._bg = parse_color(color) if color is not None else None
        s._bg_gradient = None
        return s

    def background_gradient(
        self,
        start_color: Union[str, tuple[int, int, int], TrueColor, Color],
        end_color: Union[str, tuple[int, int, int], TrueColor, Color],
        direction: str = "vertical",
    ) -> Style:
        """Fill box interior with a 2-color linear background gradient ('vertical' or 'horizontal')."""
        s = self.copy()
        s._bg = None
        s._bg_gradient = ([start_color, end_color], direction)
        return s

    def background_gradient_multi(
        self,
        colors: Sequence[Union[str, tuple[int, int, int], TrueColor, Color]],
        direction: str = "vertical",
    ) -> Style:
        """Fill box interior with a multi-stop background gradient ('vertical' or 'horizontal')."""
        s = self.copy()
        s._bg = None
        s._bg_gradient = (list(colors), direction)
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
    def _text_attributes_prefix(self) -> str:
        """Generate open ANSI escape sequences for text attributes and foreground color."""
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
        return "".join(codes)

    def _text_prefix(self) -> str:
        """Generate open ANSI escape sequences for text attributes and colors."""
        attr = self._text_attributes_prefix()
        if self._bg is not None and not is_no_color():
            return f"{attr}{self._bg.render_bg()}"
        return attr

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
        if not raw_text:
            lines = [""]
        else:
            lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

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
        pad_top, pad_right, pad_bottom, pad_left = self._padding
        inner_box_w = target_inner_w + pad_left + pad_right

        aligned_content_rows: list[str] = []
        for line in lines:
            line_w = string_width(line)
            diff = max(0, target_inner_w - line_w)
            if self._h_align == Align.CENTER:
                left_pad = diff // 2
                right_pad = diff - left_pad
                content_part = f"{' ' * left_pad}{line}{' ' * right_pad}"
            elif self._h_align == Align.RIGHT:
                content_part = f"{' ' * diff}{line}"
            else:  # LEFT
                content_part = f"{line}{' ' * diff}"
            aligned_content_rows.append(f"{' ' * pad_left}{content_part}{' ' * pad_right}")

        # 3. Build full unstyled box rows (padding top + content + padding bottom)
        blank_row = " " * inner_box_w
        box_rows: list[str] = []
        for _ in range(pad_top):
            box_rows.append(blank_row)
        for r in aligned_content_rows:
            box_rows.append(r)
        for _ in range(pad_bottom):
            box_rows.append(blank_row)

        # 4. Handle target height & vertical alignment
        border_h_cost = 0
        if self._border is not None:
            b_top, _, b_bottom, _ = self._border_sides
            if b_top:
                border_h_cost += 1
            if b_bottom:
                border_h_cost += 1

        if self._height is not None:
            needed_rows = max(0, self._height - border_h_cost)
            if len(box_rows) < needed_rows:
                v_diff = needed_rows - len(box_rows)
                if self._v_align == Align.BOTTOM:
                    box_rows = [blank_row] * v_diff + box_rows
                elif self._v_align == Align.CENTER:
                    top_v = v_diff // 2
                    bottom_v = v_diff - top_v
                    box_rows = [blank_row] * top_v + box_rows + [blank_row] * bottom_v
                else:  # TOP
                    box_rows = box_rows + [blank_row] * v_diff

        # 5. Apply background & text attribute styling to box_rows
        attr_prefix = self._text_attributes_prefix()
        styled_box_rows: list[str] = []

        if self._bg_gradient is not None and not is_no_color():
            stops, direction = self._bg_gradient
            if direction == "horizontal":
                col_colors = multi_gradient_colors(stops, inner_box_w)
                styled_box_rows = [_apply_horizontal_gradient_bg(r, col_colors, attr_prefix) for r in box_rows]
            else:  # vertical
                total_h = len(box_rows)
                row_colors = multi_gradient_colors(stops, max(1, total_h))
                for idx, r in enumerate(box_rows):
                    bg_code = row_colors[idx].render_bg()
                    clean_r = r.replace("\x1b[0m", f"\x1b[0m{bg_code}{attr_prefix}")
                    styled_box_rows.append(f"{bg_code}{attr_prefix}{clean_r}\x1b[0m")
        elif self._bg is not None and not is_no_color():
            bg_code = self._bg.render_bg()
            for r in box_rows:
                clean_r = r.replace("\x1b[0m", f"\x1b[0m{bg_code}{attr_prefix}")
                styled_box_rows.append(f"{bg_code}{attr_prefix}{clean_r}\x1b[0m")
        else:
            suffix = "\x1b[0m" if attr_prefix else ""
            styled_box_rows = [f"{attr_prefix}{r}{suffix}" if (r.strip() or attr_prefix) else r for r in box_rows]

        # 6. Apply borders
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
            for row in styled_box_rows:
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
            bordered_lines = styled_box_rows

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
