#!/usr/bin/env python3
"""Example 18: Terminal Image Protocols and Sixel/Kitty Graphics.

Demonstrates Espresso's ImageViewer with native terminal graphics protocols (DEC Sixel,
Kitty Graphics Protocol) alongside cell-based fallbacks (24-bit half-blocks, Braille, ASCII).
Includes auto-detection, interactive native protocol deselection, and tmux passthrough.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import (
    Cmd,
    KeyMsg,
    Model,
    Msg,
    Program,
    QuitMsg,
    quit_app,
)
from espresso.crema import (
    Align,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
)
from espresso.beans.image import (
    ImageViewer,
    TerminalGraphicsProtocol,
    decode_sixel,
    detect_terminal_graphics,
    detect_terminal_name,
    encode_kitty,
    encode_sixel,
    is_inside_tmux,
    supports_graphics_protocol,
)


def generate_plasma_matrix(w: int, h: int, t: float = 0.0) -> list[list[tuple[int, int, int]]]:
    """Generate a vibrant color plasma matrix."""
    matrix: list[list[tuple[int, int, int]]] = []
    for y in range(h):
        row: list[tuple[int, int, int]] = []
        for x in range(w):
            v1 = math.sin(x * 0.15 + t)
            v2 = math.sin(y * 0.2 + t)
            v3 = math.sin((x + y) * 0.15 + t)
            v4 = math.sin(math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2) * 0.2)
            v = (v1 + v2 + v3 + v4) / 4.0

            r = int((math.sin(v * math.pi) * 0.5 + 0.5) * 255)
            g = int((math.cos(v * math.pi) * 0.5 + 0.5) * 255)
            b = int((math.sin(v * math.pi + 2.0) * 0.5 + 0.5) * 255)
            row.append((r, g, b))
        matrix.append(row)
    return matrix


class TerminalImageApp(Model):
    """Interactive demo of terminal image protocols."""

    def __init__(self) -> None:
        self.width = 80
        self.height = 24
        self.plasma_w = 48
        self.plasma_h = 32
        self.plasma = generate_plasma_matrix(self.plasma_w, self.plasma_h)

        # Initialize ImageViewer
        self.viewer = ImageViewer(
            pixels=self.plasma,
            width=36,
            height=14,
            protocol=TerminalGraphicsProtocol.AUTO,
            enable_native=True,
            title="Terminal Graphics Demo",
        )
        self.status = "Press 'p' to cycle protocol, 't' to toggle native graphics, 'q' to quit."

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="q" | "Q" | "ctrl+c"):
                self.viewer.clear()
                return self, quit_app()

            case KeyMsg(key="p" | "P"):
                protocols = [
                    TerminalGraphicsProtocol.AUTO,
                    TerminalGraphicsProtocol.KITTY,
                    TerminalGraphicsProtocol.SIXEL,
                    TerminalGraphicsProtocol.HALF_BLOCK,
                    TerminalGraphicsProtocol.BRAILLE,
                    TerminalGraphicsProtocol.ASCII,
                ]
                idx = protocols.index(self.viewer.protocol) if self.viewer.protocol in protocols else 0
                next_proto = protocols[(idx + 1) % len(protocols)]
                self.viewer.set_protocol(next_proto)
                eff = self.viewer._resolve_protocol()
                supported = self.viewer.is_protocol_supported(eff)
                host_term = detect_terminal_name()
                if not supported and eff in (TerminalGraphicsProtocol.SIXEL, TerminalGraphicsProtocol.KITTY):
                    if is_inside_tmux() and not self.viewer.allow_tmux_passthrough:
                        reason = "requires tmux passthrough ('m')"
                    else:
                        reason = f"unsupported by host terminal {host_term}"
                    self.status = f"Selected {next_proto.value.upper()} (Warning: {reason}; terminal will not render image)"
                else:
                    self.status = f"Protocol changed to {next_proto.value.upper()} (effective: {eff.value.upper()})"
                return self, None

            case KeyMsg(key="t" | "T"):
                self.viewer.toggle_native()
                eff = self.viewer._resolve_protocol()
                state = "ENABLED" if self.viewer.enable_native else "DESELECTED"
                self.status = f"Native hardware graphics {state} (effective: {eff.value.upper()})"
                return self, None

            case KeyMsg(key="m" | "M"):
                self.viewer.toggle_tmux_passthrough()
                eff = self.viewer._resolve_protocol()
                tmux_active = is_inside_tmux()
                if not tmux_active:
                    state = "ENABLED" if self.viewer.allow_tmux_passthrough else "DISABLED"
                    self.status = f"Tmux passthrough is {state} (effective only inside tmux sessions; currently direct terminal)"
                else:
                    state = f"ENABLED (Effective: {eff.value.upper()})" if self.viewer.allow_tmux_passthrough else "DISABLED (Safe cell fallback)"
                    self.status = f"Tmux passthrough is now {state}"
                return self, None

            case _:
                self.viewer, cmd = self.viewer.update(msg)
                return self, cmd

    def view(self) -> str:
        eff = self.viewer._resolve_protocol()
        detected = detect_terminal_graphics(allow_tmux_passthrough=True)
        host_term = detect_terminal_name()
        tmux_active = is_inside_tmux()
        is_supported = self.viewer.is_protocol_supported(eff)

        header = (
            Style()
            .bold(True)
            .foreground("#FFFFFF")
            .background("#6200EA")
            .padding(0, 2)
            .render("🖼️ ESPRESSO TERMINAL IMAGE PROTOCOLS (SIXEL & KITTY)")
        )

        left_view = self.viewer.view()

        # Format effective protocol line with support status
        if eff in (TerminalGraphicsProtocol.KITTY, TerminalGraphicsProtocol.SIXEL):
            if is_supported:
                eff_color = "#00FF66"
                eff_label = eff.value.upper()
            else:
                eff_color = "#FF5252"
                eff_label = f"{eff.value.upper()} ⚠️ (UNSUPPORTED BY {host_term.upper()})"
        else:
            eff_color = "#FFD700"
            eff_label = eff.value.upper()

        info_box = [
            Style().bold(True).foreground("#00E5FF").render("Current Configuration:"),
            f"• Selected Protocol: {Style().bold(True).foreground('#FFFF00').render(self.viewer.protocol.value.upper())}",
            f"• Effective Protocol: {Style().bold(True).foreground(eff_color).render(eff_label)}",
            f"• Native Hardware: {Style().bold(True).render('Enabled' if self.viewer.enable_native else 'Deselected (Forced Cell)')}",
            "",
            Style().bold(True).foreground("#FF9100").render("Environment Detection:"),
            f"• Host Terminal: {Style().foreground('#00E5FF').render(host_term)}",
            f"• Detected Protocol: {Style().foreground('#00E5FF').render(f'{detected.value.upper()} (Host)' if tmux_active else detected.value.upper())}",
            f"• Inside Tmux: {Style().foreground('#FF5252' if tmux_active else '#69F0AE').render('YES' if tmux_active else 'NO')}",
            f"• Tmux Passthrough: {Style().foreground('#69F0AE' if self.viewer.allow_tmux_passthrough else '#FFD700').render('ENABLED' if self.viewer.allow_tmux_passthrough else 'DISABLED (SAFE)')}",
        ]

        if not is_supported and eff in (TerminalGraphicsProtocol.SIXEL, TerminalGraphicsProtocol.KITTY):
            info_box.extend([
                "",
                Style().bold(True).foreground("#FF5252").render("⚠️ Compatibility Note:"),
            ])
            if eff == TerminalGraphicsProtocol.SIXEL and host_term == "Ghostty":
                info_box.extend([
                    Style().foreground("#FF8A80").render("Ghostty intentionally does not implement DEC Sixel."),
                    Style().foreground("#FF8A80").render("It implements Kitty graphics protocol exclusively."),
                    Style().foreground("#FF8A80").render("Use Kitty ('p') or half-blocks for graphics."),
                ])
            elif is_inside_tmux() and not self.viewer.allow_tmux_passthrough:
                info_box.extend([
                    Style().foreground("#FF8A80").render("Hardware graphics require tmux passthrough."),
                    Style().foreground("#FF8A80").render("Press 'm' to enable passthrough mode."),
                ])
            else:
                info_box.extend([
                    Style().foreground("#FF8A80").render(f"{eff.value.upper()} is not supported by {host_term}."),
                    Style().foreground("#FF8A80").render("Use Kitty ('p') or half-blocks for graphics."),
                ])

        info_box.extend([
            "",
            Style().bold(True).foreground("#FFFFFF").render("Interactive Commands:"),
            f"• {Style().foreground('#69F0AE').render('p')}: Cycle Protocol (Auto ⇄ Kitty ⇄ Sixel ⇄ Half-block ⇄ Braille ⇄ ASCII)",
            f"• {Style().foreground('#69F0AE').render('t')}: Toggle Native Graphics (Deselect / Reselect)",
            f"• {Style().foreground('#69F0AE').render('m')}: Toggle Tmux Passthrough mode",
            f"• {Style().foreground('#FF5252').render('q')}: Quit Demo",
        ])

        right_panel = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7C4DFF")
            .padding(1, 2)
            .render("\n".join(info_box))
        )

        left_panel = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .padding(1, 1)
            .render(left_view)
        )

        body = join_horizontal(Align.TOP, left_panel, "  ", right_panel)
        status_bar = Style().foreground("#AAAAAA").italic(True).render(self.status)

        return join_vertical(Align.LEFT, header, "", body, "", status_bar)


def main() -> None:
    app = TerminalImageApp()
    Program(app, alt_screen=True).run()


if __name__ == "__main__":
    main()
