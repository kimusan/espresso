#!/usr/bin/env python3
"""Example 4: Fullscreen Canvas with Mouse Interaction and Window Resizing.

Demonstrates Phase 3 capabilities:
- Alternate screen buffer (alt_screen=True)
- SGR mouse tracking (mouse=True)
- Window resizing handling (WindowSizeMsg)
- Double-buffered flicker-free rendering
- Interactive clickable UI elements
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import (
    Cmd,
    KeyMsg,
    Model,
    MouseAction,
    MouseButton,
    MouseMsg,
    Msg,
    Program,
    WindowSizeMsg,
    quit_app,
)
from espresso.crema import (
    Align,
    DOUBLE_BORDER,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
    place,
)


class FullscreenMouseApp(Model):
    def __init__(self) -> None:
        self.width = 80
        self.height = 24
        self.last_mouse_event = "None (click or scroll anywhere!)"
        self.counter = 0
        self.clicks: list[str] = []
        self.color_idx = 0
        self.colors = ["#7D56F4", "#00E676", "#FF9100", "#E056FD", "#00B0FF"]
        self.pressed_btn: str | None = None

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case WindowSizeMsg(width=w, height=h):
                self.width = w
                self.height = h
                return self, None

            case MouseMsg(button=btn, action=act, x=x, y=y) as mouse:
                self.last_mouse_event = f"Button: {btn.value} | Action: {act.value} | Coords: ({x}, {y})"

                # Wheel scrolling updates counter
                if btn == MouseButton.WHEEL_UP:
                    self.counter += 1
                elif btn == MouseButton.WHEEL_DOWN:
                    self.counter -= 1

                # Left click interaction
                if btn == MouseButton.LEFT:
                    if act == MouseAction.PRESS:
                        # Buttons are at rows 2..4:
                        # btn1: cols 0..21, btn2: cols 23..44, btn3: cols 46..63
                        if 2 <= y <= 4 and 0 <= x <= 21:
                            self.counter += 1
                            self.pressed_btn = "count"
                            self.clicks.append(f"Clicked [+ Count Button] at ({x}, {y})")
                        elif 2 <= y <= 4 and 23 <= x <= 44:
                            self.color_idx = (self.color_idx + 1) % len(self.colors)
                            self.pressed_btn = "theme"
                            self.clicks.append(f"Clicked [Switch Theme Button] at ({x}, {y})")
                        elif 2 <= y <= 4 and 46 <= x <= 63:
                            self.pressed_btn = "exit"
                            return self, quit_app
                        else:
                            self.clicks.append(f"Clicked canvas at ({x}, {y})")
                    elif act == MouseAction.RELEASE:
                        self.pressed_btn = None

                    if len(self.clicks) > 8:
                        self.clicks.pop(0)

                return self, None

            case KeyMsg(key="q" | "ctrl+c" | "esc"):
                return self, quit_app

            case KeyMsg(key="+" | "up"):
                self.counter += 1
                return self, None

            case KeyMsg(key="-" | "down"):
                self.counter -= 1
                return self, None

            case KeyMsg(key="c"):
                self.color_idx = (self.color_idx + 1) % len(self.colors)
                return self, None

        return self, None

    def view(self) -> str:
        active_color = self.colors[self.color_idx]

        # Header Title
        header = (
            Style()
            .bold(True)
            .foreground("#FFFFFF")
            .background(active_color)
            .padding(0, 2)
            .width(max(40, self.width - 4))
            .render("☕ ESPRESSO FULLSCREEN & MOUSE LAB")
        )

        # Interactive Buttons (Rows 2..4)
        btn1 = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(active_color)
            .padding(0, 1)
            .width(18)
            .align(Align.CENTER)
            .reverse(self.pressed_btn == "count")
            .render(f"+ Count: {self.counter}")
        )

        btn2 = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(active_color)
            .padding(0, 1)
            .width(18)
            .align(Align.CENTER)
            .reverse(self.pressed_btn == "theme")
            .render("🎨 Switch Theme")
        )

        btn3 = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#FF5252")
            .padding(0, 1)
            .width(14)
            .align(Align.CENTER)
            .reverse(self.pressed_btn == "exit")
            .render("\033[31m✕ Exit App\033[0m")
        )

        button_row = join_horizontal(Align.TOP, btn1, " ", btn2, " ", btn3)

        # Status Info Box
        info_content = (
            f"• Terminal Size:    {self.width} cols × {self.height} rows\n"
            f"• Last Mouse Event: \033[1;36m{self.last_mouse_event}\033[0m\n"
            f"• Active Theme:     {active_color}\n"
            f"• Wheel Scroll:     Up/Down increments & decrements count\n"
            f"• Mouse Buttons:    Click buttons above or scroll anywhere"
        )
        info_box = (
            Style()
            .border(ROUNDED_BORDER)
            .padding(1, 2)
            .width(max(50, self.width - 6))
            .render(info_content)
        )

        # Event History Log
        log_lines = ["\033[1;33mRecent Mouse Clicks:\033[0m"]
        if not self.clicks:
            log_lines.append("  (no clicks recorded yet - click buttons above!)")
        else:
            for click_entry in self.clicks:
                log_lines.append(f"  • {click_entry}")

        log_box = (
            Style()
            .border(ROUNDED_BORDER)
            .padding(0, 1)
            .width(max(50, self.width - 6))
            .render("\n".join(log_lines))
        )

        # Footer
        footer = (
            Style()
            .foreground("#888888")
            .render("Keys: [+] Increment  [-] Decrement  [c] Cycle Color  [q] Quit  |  Mouse: Left Click & Scroll")
        )

        content = join_vertical(Align.LEFT, header, " ", button_row, " ", info_box, " ", log_box, " ", footer)
        return content


if __name__ == "__main__":
    p = Program(FullscreenMouseApp(), alt_screen=True, mouse=True)
    p.run()
