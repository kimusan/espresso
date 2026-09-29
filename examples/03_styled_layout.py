#!/usr/bin/env python3
"""Example 3: Beautiful Dashboard with Crema Styling.

Demonstrates Crema's Lip Gloss-inspired styling and layout capabilities:
- TrueColor 24-bit gradients and borders
- Box model with rounded borders, padding, and alignment
- 2D multi-panel layout using join_horizontal and join_vertical
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, quit_app
from espresso.crema import (
    Align,
    DOUBLE_BORDER,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
)


class Dashboard(Model):
    def __init__(self) -> None:
        self.active_tab = 0
        self.tabs = ["Overview", "Metrics", "Logs", "Settings"]

        # Base card style
        self.card_style = (
            Style()
            .border(ROUNDED_BORDER)
            .padding(1, 2)
            .width(36)
        )

        # Header style
        self.header_style = (
            Style()
            .bold(True)
            .foreground("#FAFAFA")
            .background("#7D56F4")
            .padding(0, 2)
            .margin(0, 0, 1, 0)
        )

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="tab" | "right" | "l"):
                self.active_tab = (self.active_tab + 1) % len(self.tabs)
                return self, None
            case KeyMsg(key="shift+tab" | "left" | "h"):
                self.active_tab = (self.active_tab - 1) % len(self.tabs)
                return self, None
            case KeyMsg(key="q" | "ctrl+c" | "esc"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        # Title Banner
        banner = self.header_style.render("☕ ESPRESSO TUI DASHBOARD • POWERED BY CREMA")

        # Tab navigation bar
        tab_rendered = []
        for i, name in enumerate(self.tabs):
            if i == self.active_tab:
                s = (
                    Style()
                    .bold(True)
                    .foreground("#FFFFFF")
                    .background("#E056FD")
                    .padding(0, 1)
                )
            else:
                s = (
                    Style()
                    .foreground("#888888")
                    .padding(0, 1)
                )
            tab_rendered.append(s.render(f"[{i + 1}] {name}"))

        nav_bar = "  ".join(tab_rendered)

        # Left Card: System Status
        status_card = (
            self.card_style.copy()
            .border_foreground("#00E676")
            .render(
                "\033[1;32m● System Status\033[0m\n\n"
                "• Engine:       Espresso TEA\n"
                "• Styler:       Crema Engine\n"
                "• Memory:       32.4 MB (0.2%)\n"
                "• Latency:      0.18 ms\n"
                "• Terminal:     TrueColor (24-bit)"
            )
        )

        # Right Card: Active Brew Stats
        brew_card = (
            self.card_style.copy()
            .border_foreground("#FF9100")
            .render(
                "\033[1;33m☕ Brew Machine Stats\033[0m\n\n"
                "• Pressure:     9.2 bar (Optimal)\n"
                "• Temperature:  93.5 °C\n"
                "• Grind Size:   Fine Espresso\n"
                "• Yield:        36g / 28s\n"
                "• Profile:      Single Origin Kenya"
            )
        )

        # Side-by-side panels
        panels = join_horizontal(Align.TOP, status_card, "  ", brew_card)

        # Footer help bar
        footer = (
            Style()
            .foreground("#777777")
            .margin(1, 0, 0, 0)
            .render("Controls: [Tab/←/→] Switch Tabs  •  [q] Quit")
        )

        return join_vertical(Align.LEFT, banner, nav_bar, "", panels, footer)


if __name__ == "__main__":
    p = Program(Dashboard())
    p.run()
