#!/usr/bin/env python3
"""Example 7: Interactive Code Editor.

Showcases the Beans TextArea component with line numbers,
an interactive Help bar with compact and full keymap modes,
and a live session Stopwatch in the status bar.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, WindowSizeMsg, batch, quit_app
from espresso.beans import Help, KeyBinding, KeyMap, Stopwatch, StopwatchTickMsg, TextArea
from espresso.crema import (
    Align,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
    string_width,
)

SAMPLE_CODE = '''# Welcome to the Espresso Code Editor!
# A lightweight, declarative TUI editor built in pure Python with TEA.

def brew_espresso(shots: int = 2) -> str:
    crema = "Rich, golden hazelnut crema"
    body = f"{shots} shots of 100% Arabica bean extract"
    return f"Perfect Espresso: {body} with {crema}"

class Barista:
    """Master craftsperson of coffee and TUIs."""
    def __init__(self, name: str = "Kim") -> None:
        self.name = name
        self.served: int = 0

    def serve(self, order: str) -> None:
        self.served += 1
        print(f"[{self.name}] Enjoy your freshly brewed {order}!")

if __name__ == "__main__":
    print(brew_espresso(shots=2))
'''


class EditorKeyMap:
    """Keybinding definitions for editor navigation and operations."""

    def __init__(self) -> None:
        self.save = KeyBinding("ctrl+s", "save file")
        self.line_nums = KeyBinding("ctrl+l", "toggle line numbers")
        self.toggle_help = KeyBinding("ctrl+h", "toggle full help")
        self.quit = KeyBinding("ctrl+q", "quit editor")
        self.nav_arrows = KeyBinding("↑/↓/←/→", "navigate cursor")
        self.nav_home = KeyBinding("home/end", "jump to line start/end")
        self.tab = KeyBinding("tab", "indent 4 spaces")
        self.page = KeyBinding("pgup/pgdn", "scroll by page")

    def short_help(self) -> list[KeyBinding]:
        return [self.save, self.line_nums, self.toggle_help, self.quit]

    def full_help(self) -> list[list[KeyBinding]]:
        return [
            [self.save, self.line_nums, self.toggle_help, self.quit],
            [self.nav_arrows, self.nav_home, self.tab, self.page],
        ]


class EditorApp(Model):
    def __init__(self) -> None:
        self.filename = "src/brew.py"
        self.status_message = "Ready"
        self.status_time = time.monotonic()
        self.is_modified = False

        # Component 1: TextArea
        self.textarea = TextArea(
            placeholder="Type your code here...",
            show_line_numbers=True,
            height=16,
            width=76,
        )
        self.textarea.set_value(SAMPLE_CODE)

        # Component 2: Help
        self.keymap = EditorKeyMap()
        self.help = Help(self.keymap, width=78)

        # Component 3: Stopwatch (session timer)
        self.stopwatch = Stopwatch(interval=0.5, auto_start=True)

        # Styling
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.file_style = Style().bold(True).foreground("#00D7D7")
        self.box_style = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4")
        self.status_bar_style = Style().background("#222222").foreground("#CCCCCC")
        self.saved_style = Style().bold(True).foreground("#00E676")
        self.modified_style = Style().bold(True).foreground("#FFAA00")

    def init(self) -> Cmd | None:
        return self.stopwatch.init()

    def update(self, msg: Msg) -> tuple[EditorApp, Cmd | None]:
        match msg:
            case WindowSizeMsg(width=w, height=h):
                editor_w = max(40, w - 4)
                # Subtract header (3 lines) and footer/help (4-6 lines)
                editor_h = max(6, h - 9)
                self.textarea.width = editor_w
                self.textarea.height = editor_h
                self.help.width = editor_w
                return self, None

            case KeyMsg(key="ctrl+q" | "esc"):
                return self, quit_app

            case KeyMsg(key="ctrl+s"):
                self.is_modified = False
                cur_time = time.strftime("%H:%M:%S")
                self.status_message = f"Saved at {cur_time}"
                return self, None

            case KeyMsg(key="ctrl+l"):
                self.textarea.toggle_line_numbers()
                state = "enabled" if self.textarea.show_line_numbers else "disabled"
                self.status_message = f"Line numbers {state}"
                return self, None

            case KeyMsg(key="ctrl+h"):
                self.help.toggle()
                return self, None

            case StopwatchTickMsg():
                self.stopwatch, cmd = self.stopwatch.update(msg)
                return self, cmd

            case KeyMsg():
                old_val = self.textarea.value
                self.textarea, cmd = self.textarea.update(msg)
                if self.textarea.value != old_val:
                    self.is_modified = True
                    self.status_message = "Editing..."
                return self, cmd

        return self, None

    def view(self) -> str:
        # Header
        badge = self.title_style.render("☕ ESPRESSO")
        file_info = f" {self.file_style.render(self.filename)}"
        header = f"{badge}{file_info}"

        # Editor Box
        editor_view = self.box_style.render(self.textarea.view())

        # Status Bar
        row, col = self.textarea.cursor
        total_lines = self.textarea.line_count
        cursor_info = f" Ln {row + 1}, Col {col + 1} ({total_lines} lines) "

        if self.is_modified:
            mod_badge = self.modified_style.render(" ● Modified ")
        else:
            mod_badge = self.saved_style.render(" ✔ Saved ")

        session_str = f" Session: {self.stopwatch.view()} "
        status_text = f" {self.status_message} "

        # Layout status bar
        left_status = f"{cursor_info}{mod_badge}{status_text}"
        right_status = session_str
        bar_w = max(40, (self.textarea.width or 76) + 2)
        spacing = max(1, bar_w - string_width(left_status) - string_width(right_status))
        status_line = self.status_bar_style.render(left_status + (" " * spacing) + right_status)

        # Help bar
        help_rendered = self.help.view()

        return join_vertical(Align.LEFT, header, editor_view, status_line, "", help_rendered)


if __name__ == "__main__":
    app = EditorApp()
    p = Program(app)
    p.run()
