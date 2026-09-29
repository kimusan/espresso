"""Espresso: A lightweight, declarative Elm Architecture (TEA) TUI framework for Python.

Inspired by Bubble Tea, Lip Gloss, and Bubbles.

- espresso: Core TEA framework, event loop, and terminal driver.
- espresso.crema: Rich styling, box model, colors, and layout engine.
- espresso.beans: Reusable UI components.
"""

from espresso.core.keys import Key, KeyMsg
from espresso.core.program import Program
from espresso.core.tea import (
    BatchMsg,
    Cmd,
    Model,
    Msg,
    QuitMsg,
    TickMsg,
    WindowSizeMsg,
    batch,
    quit_app,
    sequence,
    tick,
)
from espresso import crema

__version__ = "0.1.0"

__all__ = [
    "Model",
    "Msg",
    "Cmd",
    "Program",
    "Key",
    "KeyMsg",
    "QuitMsg",
    "WindowSizeMsg",
    "BatchMsg",
    "TickMsg",
    "batch",
    "sequence",
    "tick",
    "quit_app",
    "crema",
]

