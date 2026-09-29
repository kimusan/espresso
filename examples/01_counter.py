#!/usr/bin/env python3
"""Example 1: Interactive Counter.

Demonstrates the classic Elm Architecture (TEA) pattern:
- Model: Simple state holding the current count.
- Update: Pure state transitions handling key events.
- View: String-based terminal rendering.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, quit_app


class Counter(Model):
    def __init__(self, count: int = 0) -> None:
        self.count = count

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="+" | "up" | "k"):
                self.count += 1
                return self, None
            case KeyMsg(key="-" | "down" | "j"):
                self.count -= 1
                return self, None
            case KeyMsg(key="q" | "Q" | "ctrl+c" | "esc"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        lines = [
            "☕ Espresso Interactive Counter",
            "──────────────────────────────",
            f" Current Count:  \033[1;36m{self.count}\033[0m",
            "",
            " Controls:",
            "   [+ / ↑ / k] Increment",
            "   [- / ↓ / j] Decrement",
            "   [q / esc]   Quit",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    p = Program(Counter())
    p.run()
