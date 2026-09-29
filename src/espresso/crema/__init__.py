"""Crema: Declarative terminal styling, box model, and layout engine for Espresso.

Inspired by Lip Gloss.
"""

from espresso.crema.border import (
    BLOCK_BORDER,
    DOUBLE_BORDER,
    HIDDEN_BORDER,
    NORMAL_BORDER,
    ROUNDED_BORDER,
    THICK_BORDER,
    Border,
)
from espresso.crema.color import (
    AdaptiveColor,
    ANSIColor,
    Color,
    TrueColor,
    is_no_color,
    parse_color,
)
from espresso.crema.gradient import gradient, hex_to_rgb, linear_gradient, multi_gradient, multi_gradient_colors
from espresso.crema.layout import join_horizontal, join_vertical, place
from espresso.crema.style import Align, Style
from espresso.crema.width import char_width, string_width, strip_ansi, truncate_ansi
from espresso.crema.wrap import wrap_ansi

__all__ = [
    # Style and Enums
    "Style",
    "Align",
    # Borders
    "Border",
    "ROUNDED_BORDER",
    "NORMAL_BORDER",
    "DOUBLE_BORDER",
    "THICK_BORDER",
    "HIDDEN_BORDER",
    "BLOCK_BORDER",
    # Colors and Gradients
    "Color",
    "TrueColor",
    "ANSIColor",
    "AdaptiveColor",
    "parse_color",
    "is_no_color",
    "gradient",
    "linear_gradient",
    "multi_gradient",
    "multi_gradient_colors",
    "hex_to_rgb",
    # Layout
    "join_horizontal",
    "join_vertical",
    "place",
    # Width, Wrapping, and ANSI
    "char_width",
    "string_width",
    "strip_ansi",
    "truncate_ansi",
    "wrap_ansi",
]
