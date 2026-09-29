"""Beans: Standard library of reusable TUI components for Espresso.

Inspired by Bubbles.
"""

from espresso.beans.help import Help, KeyBinding, KeyMap
from espresso.beans.progress import Progress
from espresso.beans.spinner import (
    COFFEE,
    DOTS,
    GLOBE,
    LINE,
    MOON,
    POINTS,
    PULSE,
    Spinner,
    SpinnerTickMsg,
)
from espresso.beans.table import Column, Table
from espresso.beans.textarea import TextArea
from espresso.beans.textinput import EchoMode, TextInput
from espresso.beans.timer import (
    Stopwatch,
    StopwatchTickMsg,
    Timer,
    TimerTickMsg,
    TimerTimeoutMsg,
)
from espresso.beans.viewport import Viewport

__all__ = [
    # Spinner
    "Spinner",
    "SpinnerTickMsg",
    "DOTS",
    "LINE",
    "PULSE",
    "POINTS",
    "MOON",
    "GLOBE",
    "COFFEE",
    # TextInput
    "TextInput",
    "EchoMode",
    # TextArea
    "TextArea",
    # Help & Keys
    "Help",
    "KeyBinding",
    "KeyMap",
    # Timer & Stopwatch
    "Timer",
    "TimerTickMsg",
    "TimerTimeoutMsg",
    "Stopwatch",
    "StopwatchTickMsg",
    # Progress
    "Progress",
    # Viewport
    "Viewport",
    # Table
    "Table",
    "Column",
]
