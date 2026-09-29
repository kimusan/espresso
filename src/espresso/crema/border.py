"""Terminal border definitions and presets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Border:
    """Defines the characters used to render a 2D box border."""

    top: str
    bottom: str
    left: str
    right: str
    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str


# Predefined border styles
ROUNDED_BORDER = Border(
    top="─",
    bottom="─",
    left="│",
    right="│",
    top_left="╭",
    top_right="╮",
    bottom_left="╰",
    bottom_right="╯",
)

NORMAL_BORDER = Border(
    top="─",
    bottom="─",
    left="│",
    right="│",
    top_left="┌",
    top_right="┐",
    bottom_left="└",
    bottom_right="┘",
)

DOUBLE_BORDER = Border(
    top="═",
    bottom="═",
    left="║",
    right="║",
    top_left="╔",
    top_right="╗",
    bottom_left="╚",
    bottom_right="╝",
)

THICK_BORDER = Border(
    top="━",
    bottom="━",
    left="┃",
    right="┃",
    top_left="┏",
    top_right="┓",
    bottom_left="┗",
    bottom_right="┛",
)

HIDDEN_BORDER = Border(
    top=" ",
    bottom=" ",
    left=" ",
    right=" ",
    top_left=" ",
    top_right=" ",
    bottom_left=" ",
    bottom_right=" ",
)

BLOCK_BORDER = Border(
    top="▀",
    bottom="▄",
    left="█",
    right="█",
    top_left="▛",
    top_right="▜",
    bottom_left="▙",
    bottom_right="▟",
)
