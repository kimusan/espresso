"""Espresso: A lightweight, declarative Elm Architecture (TEA) TUI framework for Python.

Inspired by Bubble Tea, Lip Gloss, and Bubbles.

- espresso: Core TEA framework, event loop, and terminal driver.
- espresso.crema: Rich styling, box model, colors, and layout engine.
- espresso.beans: Reusable UI components.
"""

from espresso.core.keys import Key, KeyMsg, PasteMsg
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
from espresso.beans.card_list import (
    CardActivateMsg,
    CardItem,
    CardList,
    CardSelectMsg,
)
from espresso.beans.menubar import (
    MenuBar,
    MenuCategory,
    MenuCloseMsg,
    MenuItem,
    MenuOpenMsg,
    MenuSelectMsg,
)
from espresso.beans.multi_splitter import (
    MultiSplitter,
    MultiSplitterResizeMsg,
)
from espresso.beans.wizard import (
    Wizard,
    WizardBackMsg,
    WizardCancelMsg,
    WizardCompleteMsg,
    WizardNextMsg,
    WizardStep,
)

__version__ = "1.2.0"

__all__ = [
    "Model",
    "Msg",
    "Cmd",
    "Program",
    "Key",
    "KeyMsg",
    "PasteMsg",
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
    # Beans additions
    "MenuBar",
    "MenuItem",
    "MenuCategory",
    "MenuSelectMsg",
    "MenuOpenMsg",
    "MenuCloseMsg",
    "MultiSplitter",
    "MultiSplitterResizeMsg",
    "Wizard",
    "WizardStep",
    "WizardNextMsg",
    "WizardBackMsg",
    "WizardCompleteMsg",
    "WizardCancelMsg",
    "CardList",
    "CardItem",
    "CardSelectMsg",
    "CardActivateMsg",
]



