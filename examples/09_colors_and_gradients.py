#!/usr/bin/env python3
"""Example 9: Comprehensive Colors, Backgrounds, and Gradients Showcase.

Demonstrates Crema's TrueColor styling, background fills, and gradient capabilities:
- Solid background colors on text, badges, and padded cards
- Foreground linear gradients across characters (linear_gradient)
- Multi-stop gradients smoothly interpolating across 3+ colors (multi_gradient)
- Background gradient ribbons and banners (linear_gradient/multi_gradient with background=True)
- Border foreground & background styling (.border_foreground, .border_background)
- Reverse video attributes (.reverse(True)) for active tags and buttons
- Real-time palette cycling (Space to cycle themes, Q to quit)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, WindowSizeMsg, quit_app
from espresso.crema import (
    Align,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
    linear_gradient,
    multi_gradient,
    string_width,
)

PALETTES = [
    {
        "name": "Cyberpunk Neon",
        "stops": ["#FF0055", "#FF00AA", "#9900FF", "#00E5FF", "#00FF66"],
        "bg_dark": "#120826",
        "bg_card": "#1E1035",
        "accent": "#00E5FF",
    },
    {
        "name": "Sunset Fire",
        "stops": ["#FF2A6D", "#FF5E3A", "#FFAA00", "#FFD700"],
        "bg_dark": "#1A090D",
        "bg_card": "#2D1219",
        "accent": "#FF5E3A",
    },
    {
        "name": "Aurora Borealis",
        "stops": ["#00F5D4", "#00BBF9", "#7B2CBF", "#5A189A", "#00F5D4"],
        "bg_dark": "#07131E",
        "bg_card": "#0F2338",
        "accent": "#00F5D4",
    },
    {
        "name": "Tokyo Night",
        "stops": ["#7AA2F7", "#BB9AF7", "#F7768E", "#FF9E64", "#9ECE6A"],
        "bg_dark": "#16161E",
        "bg_card": "#1F2335",
        "accent": "#7AA2F7",
    },
]


class ColorsAndGradientsDemo(Model):
    def __init__(self) -> None:
        self.palette_idx = 0
        self.term_width = 80
        self.term_height = 24

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        if isinstance(msg, WindowSizeMsg):
            self.term_width = msg.width
            self.term_height = msg.height
            return self, None

        if isinstance(msg, KeyMsg):
            if msg.key in ("q", "Q", "ctrl+c", "ctrl+z", "esc"):
                return self, quit_app
            if msg.key in (" ", "tab", "right", "down"):
                self.palette_idx = (self.palette_idx + 1) % len(PALETTES)
                return self, None
            if msg.key in ("left", "up"):
                self.palette_idx = (self.palette_idx - 1) % len(PALETTES)
                return self, None

        return self, None

    def view(self) -> str:
        palette = PALETTES[self.palette_idx]
        stops = palette["stops"]
        card_bg = palette["bg_card"]
        accent = palette["accent"]

        content_w = min(max(self.term_width - 4, 60), 84)

        # 1. Header with Multi-Stop Foreground Gradient
        header_text = "✦ ESPRESSO & CREMA : COLORS, BACKGROUNDS & GRADIENTS ✦"
        header_grad = multi_gradient(header_text, stops)
        header_bar = Style().bold(True).align(Align.CENTER).width(content_w).render(header_grad)

        # 2. Background Gradient Ribbon Banner
        banner_inner = f"  ▶ ACTIVE THEME: {palette['name'].upper()}  |  Press [Space] to switch theme  |  [Q] to quit  "
        padded_banner = banner_inner.center(content_w)
        bg_banner = multi_gradient(
            padded_banner,
            stops,
            background=True,
            fg_color="#000000",
        )

        # 3. Solid Background Cards with Padding
        card_w = (content_w - 4) // 2

        card1_body = (
            f"Background: {card_bg}\n"
            f"Padding: top=1, sides=2, bot=1\n"
            f"Solid card background fill seamlessly\n"
            f"colors all interior padding cells!"
        )
        card1 = (
            Style()
            .background(card_bg)
            .foreground("#E0E0E0")
            .border(ROUNDED_BORDER)
            .border_foreground(accent)
            .border_title(f" {palette['name']} Card ", Align.LEFT)
            .padding(1, 2)
            .width(card_w)
            .render(card1_body)
        )

        card2_body = (
            f"Accent: {accent}\n"
            f"Stops: {' → '.join(stops[:3])}\n"
            f"Supports 24-bit TrueColor, 256-ANSI,\n"
            f"hex strings, and RGB tuples."
        )
        card2 = (
            Style()
            .background(card_bg)
            .foreground("#E0E0E0")
            .border(ROUNDED_BORDER)
            .border_foreground(stops[1])
            .border_title(" TrueColor Engine ", Align.LEFT)
            .padding(1, 2)
            .width(card_w)
            .render(card2_body)
        )

        cards_row = join_horizontal(Align.TOP, card1, "  ", card2)

        # 4. Linear & Multi-Stop Gradient Progress Bars / Dividers
        bar_len = content_w - 20
        fg_bar = multi_gradient("━" * bar_len, stops)
        block_bar = multi_gradient("█" * int(bar_len * 0.72), stops) + ("░" * (bar_len - int(bar_len * 0.72)))

        bars_section = [
            Style().bold(True).foreground(accent).render("Linear & Multi-Stop Gradients:"),
            f"  Smooth Line  : {fg_bar}",
            f"  Progress 72% : {block_bar}",
        ]
        bars_rendered = "\n".join(bars_section)

        # 5. Badges & Reverse Video Highlights
        badge_style_1 = Style().bold(True).background(stops[0]).foreground("#FFFFFF").padding(0, 1)
        badge_style_2 = Style().bold(True).background(stops[1]).foreground("#FFFFFF").padding(0, 1)
        badge_style_3 = Style().bold(True).background(stops[2]).foreground("#FFFFFF").padding(0, 1)
        reverse_badge = Style().bold(True).foreground(accent).reverse(True).padding(0, 1)

        badges_line = (
            f"  Badges: {badge_style_1.render('RGB')} "
            f"{badge_style_2.render('GRADIENT')} "
            f"{badge_style_3.render('BACKGROUND')} "
            f"{reverse_badge.render('REVERSE VIDEO')}"
        )

        # 6. Linear Two-Stop Background Ribbon
        ribbon_text = f"  Smooth Two-Color Background Transition ({stops[0]} → {stops[-1]})  ".center(content_w)
        ribbon_bg = linear_gradient(
            ribbon_text,
            stops[0],
            stops[-1],
            background=True,
            fg_color="#FFFFFF",
        )

        # Combine all sections vertically
        output = join_vertical(
            Align.LEFT,
            "",
            header_bar,
            bg_banner,
            "",
            cards_row,
            "",
            bars_rendered,
            badges_line,
            "",
            ribbon_bg,
            "",
            Style().faint(True).align(Align.CENTER).width(content_w).render(
                f"Palette {self.palette_idx + 1} of {len(PALETTES)}: {palette['name']} • Press [Space] for next theme, [Q] to quit"
            ),
        )

        return output


def main() -> None:
    prog = Program(ColorsAndGradientsDemo(), alt_screen=True)
    prog.run()


if __name__ == "__main__":
    main()
