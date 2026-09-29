#!/usr/bin/env python3
"""Example 3: Beautiful Dashboard with Crema Styling.

Demonstrates Crema's Lip Gloss-inspired styling and layout capabilities:
- Dynamic per-tab content views (Overview, Metrics, Logs, Settings)
- TrueColor 24-bit gradients and borders
- Box model with rounded borders, padding, and alignment
- Embedded border titles (.border_title)
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

        # Full-width card style
        self.wide_card_style = (
            Style()
            .border(ROUNDED_BORDER)
            .padding(1, 2)
            .width(74)
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
            case KeyMsg(key="1" | "2" | "3" | "4"):
                self.active_tab = int(str(msg)) - 1
                return self, None
            case KeyMsg(key="q" | "ctrl+c" | "esc"):
                return self, quit_app
        return self, None

    def _render_overview(self) -> str:
        status_card = (
            self.card_style.copy()
            .border_foreground("#00E676")
            .border_title(" [ System Status ] ", align=Align.LEFT)
            .render(
                "\033[1;32m● System Online & Ready\033[0m\n\n"
                "• Engine:       Espresso TEA v0.1\n"
                "• Styler:       Crema Engine\n"
                "• Memory:       32.4 MB (0.2%)\n"
                "• Event Latency: 0.05 ms\n"
                "• Palette:      TrueColor (24-bit)"
            )
        )

        brew_card = (
            self.card_style.copy()
            .border_foreground("#FF9100")
            .border_title(" [ Machine Status ] ", align=Align.LEFT)
            .render(
                "\033[1;33m☕ Commercial Group Head\033[0m\n\n"
                "• Pressure:     9.2 bar (Optimal)\n"
                "• Temperature:  93.5 °C\n"
                "• Grind Size:   Fine Espresso\n"
                "• Yield Target: 36.0g / 28s\n"
                "• Profile:      Single Origin Kenya"
            )
        )

        return join_horizontal(Align.TOP, status_card, "  ", brew_card)

    def _render_metrics(self) -> str:
        perf_card = (
            self.card_style.copy()
            .border_foreground("#00B0FF")
            .border_title(" [ Performance ] ", align=Align.LEFT)
            .render(
                "\033[1;36m⚡ Event Loop Telemetry\033[0m\n\n"
                "• Render Frame:  [████████░░] 82%\n"
                "• Command Pool:  [████░░░░░░] 40%\n"
                "• Loop Jitter:   < 0.02 ms\n"
                "• Allocations:   Zero GC Pause\n"
                "• Queue Depth:   0 pending msg"
            )
        )

        flow_card = (
            self.card_style.copy()
            .border_foreground("#E056FD")
            .border_title(" [ Extraction Curves ] ", align=Align.LEFT)
            .render(
                "\033[1;35m📊 Flow Sensor Readings\033[0m\n\n"
                "• Pre-Infusion: 2.2 bar (4.0s)\n"
                "• Peak Pressure: 9.3 bar (18.2s)\n"
                "• Flow Rate:     2.1 ml/sec\n"
                "• Crema Density: 1.08 g/ml\n"
                "• Total Volume:  36.4 ml"
            )
        )

        return join_horizontal(Align.TOP, perf_card, "  ", flow_card)

    def _render_logs(self) -> str:
        log_lines = [
            "\033[1;34m[21:45:01]\033[0m  \033[1;32m[INFO]\033[0m   Water heater reached target temperature: 93.5 °C",
            "\033[1;34m[21:45:04]\033[0m  \033[1;32m[INFO]\033[0m   Pre-infusion pressure stabilized at 2.5 bar",
            "\033[1;34m[21:45:09]\033[0m  \033[1;33m[WARN]\033[0m   Flow resistance variance detected (+1.2%)",
            "\033[1;34m[21:45:14]\033[0m  \033[1;32m[INFO]\033[0m   Extraction target yield reached (36.2g in 27.8s)",
            "\033[1;34m[21:45:18]\033[0m  \033[1;36m[DEBUG]\033[0m  Auto-flush solenoid valve actuated (clean cycle complete)",
        ]

        return (
            self.wide_card_style.copy()
            .border_foreground("#7D56F4")
            .border_title(" [ Live Event Stream ] ", align=Align.LEFT)
            .render("\n".join(log_lines))
        )

    def _render_settings(self) -> str:
        settings_lines = [
            "• \033[1mColor Profile:\033[0m       \033[1;32mTrueColor 24-bit RGB\033[0m (auto-detected)",
            "• \033[1mRender Engine:\033[0m       \033[1;32mLine-Diffing Double Buffer\033[0m (flicker-free)",
            "• \033[1mPre-Infusion Delay:\033[0m  \033[1;36m4.0 seconds\033[0m",
            "• \033[1mGroup Temperature:\033[0m   \033[1;36m93.5 °C\033[0m (PID loop active)",
            "• \033[1mEnergy Saver Mode:\033[0m   \033[1;33mStandby after 30 minutes idle\033[0m",
        ]

        return (
            self.wide_card_style.copy()
            .border_foreground("#FF5252")
            .border_title(" [ Espresso Machine Configuration ] ", align=Align.LEFT)
            .render("\n".join(settings_lines))
        )

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
                    .background("#7D56F4")
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

        # Dynamic Content Panel based on active tab
        if self.active_tab == 0:
            content_view = self._render_overview()
        elif self.active_tab == 1:
            content_view = self._render_metrics()
        elif self.active_tab == 2:
            content_view = self._render_logs()
        else:
            content_view = self._render_settings()

        # Footer help bar
        footer = (
            Style()
            .foreground("#777777")
            .margin(1, 0, 0, 0)
            .render("Controls: [Tab/←/→, 1-4] Switch Tabs  •  [q] Quit")
        )

        return join_vertical(Align.LEFT, banner, nav_bar, "", content_view, footer)


if __name__ == "__main__":
    p = Program(Dashboard())
    p.run()
