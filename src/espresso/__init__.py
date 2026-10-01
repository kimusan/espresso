"""Espresso: A lightweight, declarative Elm Architecture (TEA) TUI framework for Python.

Inspired by Bubble Tea, Lip Gloss, and Bubbles.

- espresso: Core TEA framework, event loop, and terminal driver.
- espresso.crema: Rich styling, box model, colors, and layout engine.
- espresso.beans: Reusable UI components.
"""

from espresso.core.keys import Key, KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.program import Program
from espresso.core.tea import (
    BatchMsg,
    Cmd,
    DisableMouseMsg,
    EnableMouseMsg,
    Model,
    Msg,
    QuitMsg,
    TickMsg,
    WindowSizeMsg,
    batch,
    disable_mouse,
    enable_mouse,
    quit_app,
    sequence,
    tick,
)
from espresso import beans, crema

__version__ = "1.0.0"

__all__ = [
    "Model",
    "Msg",
    "Cmd",
    "Program",
    "Key",
    "KeyMsg",
    "MouseMsg",
    "MouseButton",
    "MouseAction",
    "EnableMouseMsg",
    "DisableMouseMsg",
    "enable_mouse",
    "disable_mouse",
    "QuitMsg",
    "WindowSizeMsg",
    "BatchMsg",
    "TickMsg",
    "batch",
    "sequence",
    "tick",
    "quit_app",
    "crema",
    "beans",
]



