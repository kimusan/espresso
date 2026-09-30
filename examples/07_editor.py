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
from espresso.beans import (
    CodeViewer,
    Help,
    KeyBinding,
    KeyMap,
    QuickFix,
    QuickFixItem,
    QuickFixSelectMsg,
    Stopwatch,
    StopwatchTickMsg,
    TextArea,
)
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
        self.preview = KeyBinding("ctrl+p", "toggle syntax preview")
        self.diagnostics = KeyBinding("ctrl+x", "toggle diagnostics")
        self.line_nums = KeyBinding("ctrl+l", "toggle line numbers")
        self.toggle_help = KeyBinding("ctrl+h", "toggle full help")
        self.quit = KeyBinding("ctrl+q", "quit editor")
        self.nav_arrows = KeyBinding("↑/↓/←/→", "navigate cursor")
        self.nav_home = KeyBinding("home/end", "jump to line start/end")
        self.tab = KeyBinding("tab", "indent 4 spaces")
        self.page = KeyBinding("pgup/pgdn", "scroll by page")

    def short_help(self) -> list[KeyBinding]:
        return [self.save, self.preview, self.diagnostics, self.toggle_help, self.quit]

    def full_help(self) -> list[list[KeyBinding]]:
        return [
            [self.save, self.preview, self.diagnostics, self.line_nums],
            [self.toggle_help, self.quit, self.nav_arrows, self.page],
        ]


class EditorApp(Model):
    def __init__(self) -> None:
        self.filename = "src/brew.py"
        self.status_message = "Ready"
        self.status_time = time.monotonic()
        self.is_modified = False
        self.preview_mode = False

        # Component 1: TextArea
        self.textarea = TextArea(
            placeholder="Type your code here...",
            show_line_numbers=True,
            height=16,
            width=76,
        )
        self.textarea.set_value(SAMPLE_CODE)

        # Component 2: CodeViewer (syntax-highlighted preview mode)
        self.codeviewer = CodeViewer(
            code=SAMPLE_CODE,
            language="python",
            width=76,
            height=16,
            show_footer=False,
            filename=self.filename,
        )

        # Component 3: QuickFix (diagnostics drawer)
        sample_diagnostics = [
            QuickFixItem(file=self.filename, line=5, col=5, message="variable 'crema' could be annotated as Final", severity="info", code="C0103"),
            QuickFixItem(file=self.filename, line=12, col=23, message="default argument 'Kim' hardcoded; consider config parameter", severity="hint", code="W0102"),
            QuickFixItem(file=self.filename, line=20, col=11, message="call to 'brew_espresso' not verified by runtime contract", severity="warning", code="W1201"),
        ]
        self.quickfix = QuickFix(items=sample_diagnostics, height=6)

        # Component 4: Help
        self.keymap = EditorKeyMap()
        self.help = Help(self.keymap, width=78)

        # Component 5: Stopwatch (session timer)
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
                editor_h = max(6, h - 8)
                self.textarea.width = editor_w
                self.textarea.height = editor_h
                self.codeviewer.set_size(editor_w, editor_h)
                self.help.width = editor_w + 2
                self.quickfix.height = min(8, max(4, h // 3))
                return self, None

            case QuickFixSelectMsg(item=item):
                target_line = max(0, item.line - 1)
                target_col = max(0, item.col - 1)
                lines = self.textarea.lines
                if target_line < len(lines):
                    target_col = min(target_col, len(lines[target_line]))
                self.textarea.cursor = (target_line, target_col)
                self.codeviewer.set_cursor_line(item.line)
                self.status_message = f"Jumped to line {item.line}: {item.message}"
                return self, None

            case KeyMsg(key="ctrl+q"):
                return self, quit_app

            case KeyMsg(key="ctrl+s"):
                self.is_modified = False
                cur_time = time.strftime("%H:%M:%S")
                self.status_message = f"Saved at {cur_time}"
                return self, None

            case KeyMsg(key="ctrl+p"):
                self.preview_mode = not self.preview_mode
                if self.preview_mode:
                    self.codeviewer.set_code(self.textarea.value)
                    self.codeviewer.set_cursor_line(self.textarea.cursor[0] + 1)
                    self.status_message = "Syntax Preview Mode (Ctrl+P to edit)"
                else:
                    target_line = max(0, self.codeviewer.cursor_line - 1)
                    lines = self.textarea.lines
                    col = 0
                    if target_line < len(lines):
                        col = min(self.textarea.cursor[1], len(lines[target_line]))
                    self.textarea.cursor = (target_line, col)
                    self.status_message = "Edit Mode (Ctrl+P for syntax preview)"
                return self, None

            case KeyMsg(key="ctrl+x"):
                self.quickfix.toggle()
                self.status_message = "Diagnostics opened" if self.quickfix.is_open else "Diagnostics closed"
                return self, None

            case KeyMsg(key="ctrl+l"):
                self.textarea.toggle_line_numbers()
                self.codeviewer.show_line_numbers = self.textarea.show_line_numbers
                self.codeviewer.set_code(self.codeviewer.code)
                state = "enabled" if self.textarea.show_line_numbers else "disabled"
                self.status_message = f"Line numbers {state}"
                return self, None

            case KeyMsg(key="ctrl+h" | "f1"):
                self.help.toggle()
                return self, None

            case StopwatchTickMsg():
                self.stopwatch, cmd = self.stopwatch.update(msg)
                return self, cmd

            case KeyMsg() if self.quickfix.is_open and msg.key in ("esc", "q", "up", "k", "down", "j", "enter"):
                self.quickfix, cmd = self.quickfix.update(msg)
                return self, cmd

            case KeyMsg(key="esc") if not self.quickfix.is_open:
                return self, quit_app

            case KeyMsg():
                if self.preview_mode:
                    self.codeviewer, cmd = self.codeviewer.update(msg)
                    return self, cmd
                else:
                    old_val = self.textarea.value
                    self.textarea, cmd = self.textarea.update(msg)
                    if self.textarea.value != old_val:
                        self.is_modified = True
                        self.status_message = "Editing..."
                    return self, cmd

        return self, None

    def view(self) -> str:
        # Header
        mode_badge = " [PREVIEW] " if self.preview_mode else " [EDIT] "
        badge = self.title_style.render(f"☕ ESPRESSO{mode_badge}")
        file_info = f" {self.file_style.render(self.filename)}"
        header = f"{badge}{file_info}"

        # Editor Box
        box_h = (self.textarea.height + 2) if self.textarea.height else None
        box = self.box_style
        if self.textarea.width:
            box = box.width(self.textarea.width)
        if box_h:
            box = box.height(box_h)

        if self.preview_mode:
            content_view = self.codeviewer.view()
        else:
            content_view = self.textarea.view()
        editor_view = box.render(content_view)

        # Status Bar
        if self.preview_mode:
            total_lines = self.codeviewer.total_lines
            cursor_info = f" Ln {self.codeviewer.cursor_line} of {total_lines} (Syntax Preview) "
        else:
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
        self.help.width = bar_w
        help_rendered = self.help.view()

        base_view = join_vertical(Align.LEFT, header, editor_view, status_line, help_rendered)
        total_h = len(base_view.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
        return self.quickfix.wrap_view(base_view, width=bar_w, height=total_h)


if __name__ == "__main__":
    app = EditorApp()
    p = Program(app, alt_screen=True)
    p.run()
