"""ANSI-aware word wrapping preserving styling sequences and visual width across breaks."""

from __future__ import annotations

import re
from typing import Sequence

from espresso.crema.width import ANSI_REGEX, char_width, iter_graphemes, string_width


class AnsiState:
    """Tracks active SGR formatting attributes and colors."""

    def __init__(self) -> None:
        self.bold = False
        self.faint = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        self.reverse = False
        self.fg: str | None = None
        self.bg: str | None = None

    def is_active(self) -> bool:
        return bool(
            self.bold
            or self.faint
            or self.italic
            or self.underline
            or self.strikethrough
            or self.reverse
            or self.fg
            or self.bg
        )

    def reset(self) -> None:
        self.bold = False
        self.faint = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        self.reverse = False
        self.fg = None
        self.bg = None

    def to_ansi(self) -> str:
        parts: list[str] = []
        if self.bold:
            parts.append("\x1b[1m")
        if self.faint:
            parts.append("\x1b[2m")
        if self.italic:
            parts.append("\x1b[3m")
        if self.underline:
            parts.append("\x1b[4m")
        if self.strikethrough:
            parts.append("\x1b[9m")
        if self.reverse:
            parts.append("\x1b[7m")
        if self.fg:
            parts.append(self.fg)
        if self.bg:
            parts.append(self.bg)
        return "".join(parts)

    def apply_code(self, seq: str) -> None:
        if not (seq.startswith("\x1b[") and seq.endswith("m")):
            return
        param_str = seq[2:-1]
        if not param_str:
            self.reset()
            return
        raw_tokens = param_str.replace(":", ";").split(";")
        tokens: list[int] = []
        for t in raw_tokens:
            if t == "":
                tokens.append(0)
            elif t.isdigit():
                tokens.append(int(t))
        i = 0
        n = len(tokens)
        while i < n:
            cmd = tokens[i]
            if cmd == 0:
                self.reset()
                i += 1
            elif cmd == 1:
                self.bold = True
                i += 1
            elif cmd == 2:
                self.faint = True
                i += 1
            elif cmd == 3:
                self.italic = True
                i += 1
            elif cmd == 4:
                self.underline = True
                i += 1
            elif cmd == 7:
                self.reverse = True
                i += 1
            elif cmd == 9:
                self.strikethrough = True
                i += 1
            elif cmd in (21, 22):
                self.bold = False
                self.faint = False
                i += 1
            elif cmd == 23:
                self.italic = False
                i += 1
            elif cmd == 24:
                self.underline = False
                i += 1
            elif cmd == 27:
                self.reverse = False
                i += 1
            elif cmd == 29:
                self.strikethrough = False
                i += 1
            elif (30 <= cmd <= 37) or (90 <= cmd <= 97):
                self.fg = f"\x1b[{cmd}m"
                i += 1
            elif cmd == 39:
                self.fg = None
                i += 1
            elif (40 <= cmd <= 47) or (100 <= cmd <= 107):
                self.bg = f"\x1b[{cmd}m"
                i += 1
            elif cmd == 49:
                self.bg = None
                i += 1
            elif cmd == 38:
                if i + 2 < n and tokens[i + 1] == 5:
                    self.fg = f"\x1b[38;5;{tokens[i + 2]}m"
                    i += 3
                elif i + 4 < n and tokens[i + 1] == 2:
                    self.fg = f"\x1b[38;2;{tokens[i + 2]};{tokens[i + 3]};{tokens[i + 4]}m"
                    i += 5
                else:
                    i += 1
            elif cmd == 48:
                if i + 2 < n and tokens[i + 1] == 5:
                    self.bg = f"\x1b[48;5;{tokens[i + 2]}m"
                    i += 3
                elif i + 4 < n and tokens[i + 1] == 2:
                    self.bg = f"\x1b[48;2;{tokens[i + 2]};{tokens[i + 3]};{tokens[i + 4]}m"
                    i += 5
                else:
                    i += 1
            else:
                i += 1


def _parse_paragraph(paragraph: str) -> list[tuple[str, list[tuple[bool, str, int]], int]]:
    """Parse paragraph into a list of ('space'|'word', items, visual_width)."""
    elements: list[tuple[str, list[tuple[bool, str, int]], int]] = []
    current_type: str | None = None
    current_items: list[tuple[bool, str, int]] = []
    current_w = 0

    last_end = 0
    for match in ANSI_REGEX.finditer(paragraph):
        start, end = match.span()
        if start > last_end:
            text_chunk = paragraph[last_end:start]
            for cluster, cw in iter_graphemes(text_chunk):
                is_space = cluster.isspace()
                elem_type = "space" if is_space else "word"
                if current_type is None:
                    current_type = elem_type
                elif current_type != elem_type:
                    elements.append((current_type, current_items, current_w))
                    current_items = []
                    current_w = 0
                    current_type = elem_type
                current_items.append((False, cluster, cw))
                current_w += cw
        ansi_code = match.group(0)
        current_items.append((True, ansi_code, 0))
        last_end = end

    if last_end < len(paragraph):
        text_chunk = paragraph[last_end:]
        for cluster, cw in iter_graphemes(text_chunk):
            is_space = cluster.isspace()
            elem_type = "space" if is_space else "word"
            if current_type is None:
                current_type = elem_type
            elif current_type != elem_type:
                elements.append((current_type, current_items, current_w))
                current_items = []
                current_w = 0
                current_type = elem_type
            current_items.append((False, cluster, cw))
            current_w += cw

    if current_items:
        elements.append((current_type or "word", current_items, current_w))

    return elements


def wrap_ansi(text: str, width: int) -> str:
    """Wrap text to fit within width visual cells while preserving ANSI sequences without color bleeding.

    - Accurately accounts for East Asian fullwidth characters and emoji widths (2 cells).
    - Preserves ANSI formatting across soft and hard line wraps without leaking into surrounding terminal area.
    - Preserves original newline characters in multi-line strings.
    """
    if width <= 0:
        return ""
    if not text:
        return ""

    paragraphs = text.split("\n")
    state = AnsiState()
    result_lines: list[str] = []

    for paragraph in paragraphs:
        if not paragraph:
            result_lines.append("")
            continue

        elements = _parse_paragraph(paragraph)
        p_lines: list[str] = []
        current_line: list[str] = []
        current_w = 0

        # If state is active from a preceding line, reopen it on the current line
        if state.is_active():
            current_line.append(state.to_ansi())

        for idx, (elem_type, items, elem_w) in enumerate(elements):
            if elem_type == "space":
                if current_w == 0 and not p_lines:
                    # Leading whitespace on first line of paragraph
                    if elem_w <= width:
                        current_line.append("".join(val for _, val, _ in items))
                        current_w += elem_w
                        for is_ansi, val, _ in items:
                            if is_ansi:
                                state.apply_code(val)
                    else:
                        # Split leading whitespace across lines
                        for is_ansi, val, cw in items:
                            if is_ansi:
                                state.apply_code(val)
                                current_line.append(val)
                            else:
                                if current_w + cw > width and current_w > 0:
                                    if state.is_active():
                                        current_line.append("\x1b[0m")
                                    p_lines.append("".join(current_line))
                                    current_line = []
                                    current_w = 0
                                    if state.is_active():
                                        current_line.append(state.to_ansi())
                                current_line.append(val)
                                current_w += cw
                elif current_w > 0:
                    # Inter-word whitespace: look ahead to next word
                    next_word_w = 0
                    if idx + 1 < len(elements) and elements[idx + 1][0] == "word":
                        next_word_w = elements[idx + 1][2]

                    if next_word_w > 0 and (current_w + elem_w + next_word_w <= width):
                        # Next word fits on current line with this space
                        current_line.append("".join(val for _, val, _ in items))
                        current_w += elem_w
                        for is_ansi, val, _ in items:
                            if is_ansi:
                                state.apply_code(val)
                    elif next_word_w > 0:
                        # Next word won't fit: wrap line, drop space, but apply ANSI state changes
                        for is_ansi, val, _ in items:
                            if is_ansi:
                                state.apply_code(val)
                        if state.is_active():
                            current_line.append("\x1b[0m")
                        p_lines.append("".join(current_line))
                        current_line = []
                        current_w = 0
                        if state.is_active():
                            current_line.append(state.to_ansi())
                    else:
                        # Trailing space at end of paragraph
                        if current_w + elem_w <= width:
                            current_line.append("".join(val for _, val, _ in items))
                            current_w += elem_w
                        for is_ansi, val, _ in items:
                            if is_ansi:
                                state.apply_code(val)
            else:
                # Word
                if current_w + elem_w <= width:
                    current_line.append("".join(val for _, val, _ in items))
                    current_w += elem_w
                    for is_ansi, val, _ in items:
                        if is_ansi:
                            state.apply_code(val)
                else:
                    # Word does not fit on current line
                    if current_w > 0:
                        if state.is_active():
                            current_line.append("\x1b[0m")
                        p_lines.append("".join(current_line))
                        current_line = []
                        current_w = 0
                        if state.is_active():
                            current_line.append(state.to_ansi())

                    if elem_w <= width:
                        current_line.append("".join(val for _, val, _ in items))
                        current_w = elem_w
                        for is_ansi, val, _ in items:
                            if is_ansi:
                                state.apply_code(val)
                    else:
                        # Word exceeds width on its own: split character by character
                        for is_ansi, val, cw in items:
                            if is_ansi:
                                state.apply_code(val)
                                current_line.append(val)
                            else:
                                if current_w + cw > width and current_w > 0:
                                    if state.is_active():
                                        current_line.append("\x1b[0m")
                                    p_lines.append("".join(current_line))
                                    current_line = []
                                    current_w = 0
                                    if state.is_active():
                                        current_line.append(state.to_ansi())
                                current_line.append(val)
                                current_w += cw

        if current_line:
            if state.is_active():
                current_line.append("\x1b[0m")
            p_lines.append("".join(current_line))

        result_lines.extend(p_lines)

    return "\n".join(result_lines)
