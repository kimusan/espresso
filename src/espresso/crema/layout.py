"""2D terminal layout composition utilities (join_horizontal, join_vertical, place)."""

from __future__ import annotations

from typing import Sequence

from espresso.crema.style import Align
from espresso.crema.width import string_width


def join_horizontal(align: Align, *blocks: str) -> str:
    """Join multiple multi-line string blocks horizontally side-by-side."""
    non_empty = [b for b in blocks if b]
    if not non_empty:
        return ""

    block_lines: list[list[str]] = [b.splitlines() for b in non_empty]
    max_height = max(len(lines) for lines in block_lines)

    # Pad each block to max_height with blank lines according to alignment
    padded_blocks: list[list[str]] = []
    for lines in block_lines:
        w = max((string_width(l) for l in lines), default=0)
        empty = " " * w
        diff = max_height - len(lines)

        if diff <= 0:
            padded_blocks.append(lines)
            continue

        if align == Align.BOTTOM:
            padded = [empty] * diff + lines
        elif align == Align.CENTER:
            top_pad = diff // 2
            bot_pad = diff - top_pad
            padded = [empty] * top_pad + lines + [empty] * bot_pad
        else:  # TOP
            padded = lines + [empty] * diff

        padded_blocks.append(padded)

    # Zip corresponding rows together
    result_rows: list[str] = []
    for row_idx in range(max_height):
        row_segments = [b[row_idx] for b in padded_blocks]
        result_rows.append("".join(row_segments))

    return "\n".join(result_rows)


def join_vertical(align: Align, *blocks: str) -> str:
    """Stack multiple string blocks vertically, aligning them horizontally."""
    non_empty = [b for b in blocks if b]
    if not non_empty:
        return ""

    all_lines: list[str] = []
    for b in non_empty:
        all_lines.extend(b.splitlines())

    max_width = max((string_width(l) for l in all_lines), default=0)

    aligned_lines: list[str] = []
    for line in all_lines:
        w = string_width(line)
        diff = max_width - w
        if diff <= 0:
            aligned_lines.append(line)
        elif align == Align.CENTER:
            left = diff // 2
            right = diff - left
            aligned_lines.append(f"{' ' * left}{line}{' ' * right}")
        elif align == Align.RIGHT:
            aligned_lines.append(f"{' ' * diff}{line}")
        else:  # LEFT
            aligned_lines.append(f"{line}{' ' * diff}")

    return "\n".join(aligned_lines)


def place(width: int, height: int, h_align: Align, v_align: Align, content: str) -> str:
    """Place content inside a box of (width, height) cells with given alignments."""
    lines = content.splitlines() if content else [""]
    # 1. Horizontal placement
    h_aligned: list[str] = []
    for line in lines:
        w = string_width(line)
        diff = max(0, width - w)
        if h_align == Align.CENTER:
            left = diff // 2
            right = diff - left
            h_aligned.append(f"{' ' * left}{line}{' ' * right}")
        elif h_align == Align.RIGHT:
            h_aligned.append(f"{' ' * diff}{line}")
        else:  # LEFT
            h_aligned.append(f"{line}{' ' * diff}")

    # 2. Vertical placement
    v_diff = max(0, height - len(h_aligned))
    empty_row = " " * width
    if v_align == Align.BOTTOM:
        result = [empty_row] * v_diff + h_aligned
    elif v_align == Align.CENTER:
        top_pad = v_diff // 2
        bot_pad = v_diff - top_pad
        result = [empty_row] * top_pad + h_aligned + [empty_row] * bot_pad
    else:  # TOP
        result = h_aligned + [empty_row] * v_diff

    return "\n".join(result[:height])
