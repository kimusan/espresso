"""Core Elm Architecture (TEA) framework primitives."""

from espresso.core.keys import Key, KeyMsg, parse_keys
from espresso.core.mouse import MouseAction, MouseButton, MouseGestureTracker, MouseMsg, parse_sgr_mouse
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
from espresso.core.terminal import TerminalDriver

__all__ = [
    "Key",
    "KeyMsg",
    "parse_keys",
    "MouseMsg",
    "MouseButton",
    "MouseAction",
    "MouseGestureTracker",
    "parse_sgr_mouse",
    "Program",
    "Model",
    "Msg",
    "Cmd",
    "QuitMsg",
    "WindowSizeMsg",
    "BatchMsg",
    "TickMsg",
    "batch",
    "sequence",
    "tick",
    "quit_app",
    "TerminalDriver",
]

