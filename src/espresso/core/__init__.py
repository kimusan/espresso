"""Core Elm Architecture (TEA) framework primitives."""

from espresso.core.keys import Key, KeyMsg, parse_keys
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
