#!/usr/bin/env python3
"""Example 2: Shopping List / Task Picker.

Demonstrates list state, cursor navigation, toggle selections, and key handling:
- Model: Tracks list items, cursor index, and checked state.
- Update: Handles Up/Down arrows, Space/Enter to toggle, 'q' to quit.
- View: Formatted interactive selection list.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, quit_app


class ShoppingList(Model):
    def __init__(self) -> None:
        self.items = [
            "Dark Roast Coffee Beans",
            "Oat Milk",
            "Raw Cane Sugar",
            "Espresso Cups",
            "Stainless Steel Tamper",
            "Pour-Over Filters",
        ]
        self.cursor = 0
        self.selected: set[int] = {0, 1}

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="up" | "k"):
                if self.cursor > 0:
                    self.cursor -= 1
                return self, None
            case KeyMsg(key="down" | "j"):
                if self.cursor < len(self.items) - 1:
                    self.cursor += 1
                return self, None
            case KeyMsg(key=" " | "enter" | "x"):
                if self.cursor in self.selected:
                    self.selected.remove(self.cursor)
                else:
                    self.selected.add(self.cursor)
                return self, None
            case KeyMsg(key="q" | "ctrl+c" | "esc"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        lines = [
            "☕ What should we pick up at the coffee shop?",
            "────────────────────────────────────────────",
        ]

        for i, item in enumerate(self.items):
            # Cursor indicator
            cursor_mark = ">" if self.cursor == i else " "

            # Checkbox state
            checked = "[x]" if i in self.selected else "[ ]"

            if self.cursor == i:
                lines.append(f" \033[1;33m{cursor_mark} {checked} {item}\033[0m")
            else:
                lines.append(f"  {checked} {item}")

        lines.extend([
            "",
            " Controls:",
            "   [↑/↓, k/j] Navigate  [Space/Enter] Toggle  [q] Quit",
        ])
        return "\n".join(lines)


if __name__ == "__main__":
    p = Program(ShoppingList())
    p.run()
