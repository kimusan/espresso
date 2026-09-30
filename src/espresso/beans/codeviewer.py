"""Syntax-highlighted source code viewer component.

Inspired by mistakenelf/teacup/code.
Provides lexical syntax highlighting (Python, JavaScript/TypeScript, Go,
Rust, JSON, YAML, SQL, Shell, Markdown) using pure Python standard library,
with line numbers, active line indicator, and smooth viewport scrolling.
"""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from espresso.beans.viewport import Viewport
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


class SyntaxTheme:
    """Color palette for syntax highlighting."""

    def __init__(
        self,
        keyword: str = "#FF79C6",
        builtin: str = "#8BE9FD",
        string: str = "#F1FA8C",
        number: str = "#BD93F9",
        comment: str = "#6272A4",
        function: str = "#50FA7B",
        operator: str = "#FF79C6",
        type_name: str = "#8BE9FD",
        default: str = "#F8F8F2",
        gutter: str = "#44475A",
        active_gutter: str = "#50FA7B",
    ) -> None:
        self.keyword = Style().foreground(keyword).bold(True)
        self.builtin = Style().foreground(builtin)
        self.string = Style().foreground(string)
        self.number = Style().foreground(number)
        self.comment = Style().foreground(comment).italic(True)
        self.function = Style().foreground(function).bold(True)
        self.operator = Style().foreground(operator)
        self.type_name = Style().foreground(type_name).bold(True)
        self.default = Style().foreground(default)
        self.gutter = Style().foreground(gutter)
        self.active_gutter = Style().foreground(active_gutter).bold(True)


# Predefined Themes
THEME_ESPRESSO = SyntaxTheme(
    keyword="#7D56F4",
    builtin="#00E5FF",
    string="#00E676",
    number="#FFB300",
    comment="#606080",
    function="#00E5FF",
    operator="#FF7043",
    type_name="#AB47BC",
    default="#E0E0E0",
    gutter="#444466",
    active_gutter="#00E676",
)

THEME_DRACULA = SyntaxTheme(
    keyword="#FF79C6",
    builtin="#8BE9FD",
    string="#F1FA8C",
    number="#BD93F9",
    comment="#6272A4",
    function="#50FA7B",
    operator="#FF79C6",
    type_name="#8BE9FD",
    default="#F8F8F2",
    gutter="#44475A",
    active_gutter="#50FA7B",
)

THEME_MONOKAI = SyntaxTheme(
    keyword="#F92672",
    builtin="#66D9EF",
    string="#E6DB74",
    number="#AE81FF",
    comment="#75715E",
    function="#A6E22E",
    operator="#F92672",
    type_name="#66D9EF",
    default="#F8F8F2",
    gutter="#49483E",
    active_gutter="#A6E22E",
)


def highlight_python(code: str, theme: SyntaxTheme) -> list[str]:
    """Highlight Python source code using the standard library tokenize module."""
    raw_lines = code.splitlines()
    if not code.strip():
        return [theme.default.render(l) for l in raw_lines]

    tokens_by_line: dict[int, list[tokenize.TokenInfo]] = {i + 1: [] for i in range(len(raw_lines))}
    try:
        reader = io.StringIO(code).readline
        for tok in tokenize.generate_tokens(reader):
            line_no = tok.start[0]
            if line_no in tokens_by_line:
                tokens_by_line[line_no].append(tok)
    except Exception:
        # Fallback to plain rendering if tokenize fails on partial input
        return [theme.default.render(l) for l in raw_lines]

    py_keywords = {
        "def", "class", "return", "if", "elif", "else", "for", "while", "import",
        "from", "as", "try", "except", "finally", "with", "yield", "async", "await",
        "lambda", "pass", "break", "continue", "raise", "match", "case", "in", "is",
        "and", "or", "not", "assert", "global", "nonlocal",
    }
    py_builtins = {"True", "False", "None", "self", "cls", "int", "str", "float", "bool", "list", "dict", "set", "tuple", "len", "print", "range"}

    highlighted_lines: list[str] = []
    for line_no, original_line in enumerate(raw_lines, 1):
        toks = tokens_by_line.get(line_no, [])
        if not toks:
            highlighted_lines.append(theme.default.render(original_line))
            continue

        rendered_line = ""
        last_col = 0
        for tok in toks:
            # Skip ENDMARKER or non-visible tokens
            if tok.type in (tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE):
                continue

            s_col = tok.start[1]
            e_col = tok.end[1]

            # Append any whitespace preceding this token
            if s_col > last_col:
                rendered_line += original_line[last_col:s_col]

            val = tok.string
            match tok.type:
                case tokenize.NAME:
                    if val in py_keywords:
                        rendered_line += theme.keyword.render(val)
                    elif val in py_builtins:
                        rendered_line += theme.builtin.render(val)
                    else:
                        rendered_line += theme.default.render(val)
                case tokenize.STRING:
                    rendered_line += theme.string.render(val)
                case tokenize.NUMBER:
                    rendered_line += theme.number.render(val)
                case tokenize.COMMENT:
                    rendered_line += theme.comment.render(val)
                case tokenize.OP:
                    rendered_line += theme.operator.render(val)
                case _:
                    rendered_line += theme.default.render(val)

            last_col = e_col

        # Append remaining line suffix if any
        if last_col < len(original_line):
            rendered_line += original_line[last_col:]

        highlighted_lines.append(rendered_line)

    return highlighted_lines


def highlight_code(code: str, language: str = "python", theme: SyntaxTheme | None = None) -> list[str]:
    """Highlight source code lines based on language identifier."""
    th = theme or THEME_ESPRESSO
    lang = language.lower().lstrip(".")

    if lang in ("py", "python"):
        return highlight_python(code, th)

    # Generic regex tokenization for other languages
    raw_lines = code.splitlines()
    kw_re = re.compile(r"\b(func|fn|function|var|let|const|type|struct|interface|package|import|export|return|if|else|switch|case|for|select|match|impl|trait|pub)\b")
    num_re = re.compile(r"\b\d+(\.\d+)?\b")
    str_re = re.compile(r"(\".*?\"|'.*?'|`.*?`)")
    com_re = re.compile(r"(//.*$|#.*$|/\*.*?\*/)")

    out: list[str] = []
    for line in raw_lines:
        line_styled = com_re.sub(lambda m: th.comment.render(m.group(0)), line)
        if line_styled == line:
            line_styled = str_re.sub(lambda m: th.string.render(m.group(0)), line)
            line_styled = kw_re.sub(lambda m: th.keyword.render(m.group(0)), line_styled)
            line_styled = num_re.sub(lambda m: th.number.render(m.group(0)), line_styled)
        out.append(line_styled)
    return out


class CodeViewer(Model):
    """A scrollable syntax-highlighted source code viewer with line numbers."""

    def __init__(
        self,
        code: str = "",
        language: str = "python",
        width: int = 80,
        height: int = 20,
        theme: SyntaxTheme | None = None,
        show_line_numbers: bool = True,
        highlight_lines: set[int] | None = None,
        cursor_line: int = 1,
        filename: str = "",
        show_footer: bool = True,
    ) -> None:
        self.code = code
        self.language = language
        self.width = max(20, width)
        self.height = max(4, height)
        self.theme = theme or THEME_ESPRESSO
        self.show_line_numbers = show_line_numbers
        self.highlight_lines = highlight_lines or set()
        self.cursor_line = max(1, cursor_line)
        self.filename = filename
        self.show_footer = show_footer

        self.viewport = Viewport(width=self.width, height=max(2, self.height - (1 if show_footer else 0)))
        self._rebuild_content()

    def _rebuild_content(self) -> None:
        raw_lines = self.code.splitlines() or [""]
        highlighted = highlight_code(self.code, self.language, self.theme)

        gutter_w = max(2, len(str(len(raw_lines))))
        formatted_lines: list[str] = []

        for idx, h_line in enumerate(highlighted, 1):
            is_cursor = (idx == self.cursor_line)
            is_highlighted = idx in self.highlight_lines

            if self.show_line_numbers:
                g_style = self.theme.active_gutter if is_cursor else self.theme.gutter
                num_str = f"{idx:>{gutter_w}}"
                marker = "▶" if is_cursor else ("●" if is_highlighted else " ")
                gutter_part = f"{g_style.render(num_str)} {g_style.render('│')} {marker} "
            else:
                marker = "▶ " if is_cursor else "  "
                gutter_part = marker

            formatted_lines.append(f"{gutter_part}{h_line}")

        self.viewport.set_content("\n".join(formatted_lines))

    def set_code(self, code: str, language: str | None = None) -> None:
        """Update code content and re-render."""
        self.code = code
        if language is not None:
            self.language = language
        self._rebuild_content()

    def set_cursor_line(self, line: int) -> None:
        """Set the active cursor line and adjust viewport."""
        self.cursor_line = max(1, line)
        self._rebuild_content()
        # Keep cursor in view
        target_offset = self.cursor_line - 1
        if target_offset < self.viewport.y_offset:
            self.viewport.y_offset = target_offset
        elif target_offset >= self.viewport.y_offset + self.viewport.height:
            self.viewport.y_offset = target_offset - self.viewport.height + 1

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[CodeViewer, Cmd | None]:
        """Handle keyboard navigation and scrolling."""
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    total_lines = len(self.code.splitlines())
                    if self.cursor_line < total_lines:
                        self.set_cursor_line(self.cursor_line + 1)
                    return self, None
                case "up" | "k":
                    if self.cursor_line > 1:
                        self.set_cursor_line(self.cursor_line - 1)
                    return self, None
                case "pgdown" | "pagedown":
                    total_lines = len(self.code.splitlines())
                    self.set_cursor_line(min(total_lines, self.cursor_line + self.viewport.height))
                    return self, None
                case "pgup" | "pageup":
                    self.set_cursor_line(max(1, self.cursor_line - self.viewport.height))
                    return self, None
                case "home" | "g":
                    self.set_cursor_line(1)
                    return self, None
                case "end" | "G":
                    self.set_cursor_line(len(self.code.splitlines()))
                    return self, None

        self.viewport, cmd = self.viewport.update(msg)
        return self, cmd

    def view(self) -> str:
        """Render the code viewport with bottom status bar."""
        body = self.viewport.view()
        if not self.show_footer:
            return body

        total_lines = len(self.code.splitlines())
        name = self.filename or f"snippet.{self.language}"
        pct = int(self.viewport.scroll_percent * 100)
        status_left = Style().bold(True).foreground("#00E5FF").render(f" {name} ")
        status_mid = Style().faint(True).render(f"({self.language.upper()})")
        status_right = Style().foreground("#8888AA").render(f"Ln {self.cursor_line}/{total_lines} ({pct}%) ")

        left_side = f"{status_left}{status_mid}"
        pad = max(1, self.width - string_width(left_side) - string_width(status_right))
        footer = f"{left_side}{' ' * pad}{status_right}"

        return f"{body}\n{footer}"
