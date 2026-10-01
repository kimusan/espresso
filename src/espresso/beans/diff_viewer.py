"""High-fidelity terminal Git diff visualizer with Unified and Split views and intra-line highlighting."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


class DiffMode(Enum):
    """Display layout mode for the diff viewer."""

    UNIFIED = "unified"  # Single column unified diff
    SPLIT = "split"      # Side-by-side dual pane diff


@dataclass
class DiffLine:
    """A single line within a diff."""

    line_type: str  # "+", "-", " ", "@", or "empty" (for split alignment)
    content: str
    old_lineno: int | None = None
    new_lineno: int | None = None
    tokens: list[tuple[str, str]] | None = None  # (text, token_type: "same", "added", "removed")


@dataclass
class DiffHunk:
    """A hunk block within a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[DiffLine]


class DiffViewer(Model):
    """An interactive diff viewer component supporting unified and side-by-side rendering."""

    def __init__(
        self,
        diff_text: str | None = None,
        old_text: str | None = None,
        new_text: str | None = None,
        fromfile: str = "a/file",
        tofile: str = "b/file",
        mode: DiffMode = DiffMode.UNIFIED,
        width: int = 80,
        height: int = 20,
        show_header: bool = True,
        show_line_numbers: bool = True,
        highlight_words: bool = True,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        self.width = max(20, width)
        self.height = max(5, height)
        self.mode = mode
        self.show_header = show_header
        self.show_line_numbers = show_line_numbers
        self.highlight_words = highlight_words
        self.fromfile = fromfile
        self.tofile = tofile
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.scroll_y: int = 0
        self.scroll_x: int = 0
        self.focused: bool = True

        # Styles
        self.header_style = Style().bold(True).foreground("#FFFFFF").background("#333344")
        self.hunk_style = Style().foreground("#00E5FF").bold(True)
        self.added_style = Style().foreground("#A5D6A7").background("#1B3A24")
        self.added_highlight_style = Style().foreground("#FFFFFF").background("#2E7D32").bold(True)
        self.removed_style = Style().foreground("#EF9A9A").background("#3E1C1C")
        self.removed_highlight_style = Style().foreground("#FFFFFF").background("#C62828").bold(True)
        self.context_style = Style().foreground("#CCCCCC")
        self.gutter_style = Style().foreground("#666688")
        self.divider_style = Style().foreground("#444466")

        self.hunks: list[DiffHunk] = []
        self.stats_additions = 0
        self.stats_deletions = 0

        if diff_text is not None:
            self.set_diff(diff_text)
        elif old_text is not None and new_text is not None:
            self.compare(old_text, new_text, fromfile, tofile)

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset for mouse interaction."""
        self.offset_x = x
        self.offset_y = y

    def set_size(self, width: int, height: int) -> None:
        """Resize viewer bounds."""
        self.width = max(20, width)
        self.height = max(5, height)

    def compare(self, old_text: str, new_text: str, fromfile: str = "a/file", tofile: str = "b/file") -> None:
        """Generate unified diff between old_text and new_text and load it."""
        self.fromfile = fromfile
        self.tofile = tofile
        old_lines = old_text.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
        new_lines = new_text.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)

        raw_diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile))
        diff_str = "".join(raw_diff)
        self.set_diff(diff_str)

    def set_diff(self, diff_text: str) -> None:
        """Parse raw unified diff text into hunks and lines with intra-line word diffs."""
        self.hunks = []
        self.stats_additions = 0
        self.stats_deletions = 0
        self.scroll_y = 0
        self.scroll_x = 0

        raw_lines = diff_text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        hunk_regex = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)")

        current_hunk: DiffHunk | None = None
        old_lineno = 0
        new_lineno = 0

        for line in raw_lines:
            # Check for hunk header
            hunk_match = hunk_regex.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2) or 1)
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4) or 1)
                heading = hunk_match.group(5).strip()

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    header=line,
                    lines=[],
                )
                self.hunks.append(current_hunk)
                old_lineno = old_start
                new_lineno = new_start
                continue

            if current_hunk is None:
                # File header lines (--- a/..., +++ b/...)
                continue

            if line.startswith("+"):
                self.stats_additions += 1
                current_hunk.lines.append(DiffLine("+", line[1:], old_lineno=None, new_lineno=new_lineno))
                new_lineno += 1
            elif line.startswith("-"):
                self.stats_deletions += 1
                current_hunk.lines.append(DiffLine("-", line[1:], old_lineno=old_lineno, new_lineno=None))
                old_lineno += 1
            elif line.startswith(" ") or line == "":
                content = line[1:] if line.startswith(" ") else line
                current_hunk.lines.append(DiffLine(" ", content, old_lineno=old_lineno, new_lineno=new_lineno))
                old_lineno += 1
                new_lineno += 1

        # Compute intra-line word highlighting for changed line pairs
        if self.highlight_words:
            self._compute_word_diffs()

    def _compute_word_diffs(self) -> None:
        """Find adjacent deletion-addition pairs and compute word-level changes."""
        for hunk in self.hunks:
            i = 0
            n = len(hunk.lines)
            while i < n:
                # Find consecutive deleted lines followed by added lines
                del_lines: list[tuple[int, DiffLine]] = []
                while i < n and hunk.lines[i].line_type == "-":
                    del_lines.append((i, hunk.lines[i]))
                    i += 1

                add_lines: list[tuple[int, DiffLine]] = []
                while i < n and hunk.lines[i].line_type == "+":
                    add_lines.append((i, hunk.lines[i]))
                    i += 1

                # If pair of deleted and added lines exists (e.g. 1-to-1 modification)
                if len(del_lines) == 1 and len(add_lines) == 1:
                    d_idx, d_line = del_lines[0]
                    a_idx, a_line = add_lines[0]
                    self._highlight_pair(d_line, a_line)
                elif del_lines and add_lines:
                    # Multi-line match by closest similarity
                    for (_, dl), (_, al) in zip(del_lines, add_lines):
                        self._highlight_pair(dl, al)

                if not del_lines and not add_lines:
                    i += 1

    def _highlight_pair(self, del_line: DiffLine, add_line: DiffLine) -> None:
        """Use SequenceMatcher to tokenize words and mark modified segments."""
        s1 = del_line.content
        s2 = add_line.content

        # Split into words/whitespace tokens
        tokens1 = re.findall(r"\w+|\s+|[^\w\s]", s1)
        tokens2 = re.findall(r"\w+|\s+|[^\w\s]", s2)

        matcher = difflib.SequenceMatcher(None, tokens1, tokens2)
        d_tokens: list[tuple[str, str]] = []
        a_tokens: list[tuple[str, str]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                text1 = "".join(tokens1[i1:i2])
                d_tokens.append((text1, "same"))
                text2 = "".join(tokens2[j1:j2])
                a_tokens.append((text2, "same"))
            elif tag == "delete":
                text = "".join(tokens1[i1:i2])
                d_tokens.append((text, "removed"))
            elif tag == "insert":
                text = "".join(tokens2[j1:j2])
                a_tokens.append((text, "added"))
            elif tag == "replace":
                d_tokens.append(("".join(tokens1[i1:i2]), "removed"))
                a_tokens.append(("".join(tokens2[j1:j2]), "added"))

        del_line.tokens = d_tokens
        add_line.tokens = a_tokens

    def toggle_mode(self) -> None:
        """Toggle between UNIFIED and SPLIT diff modes."""
        self.mode = DiffMode.SPLIT if self.mode == DiffMode.UNIFIED else DiffMode.UNIFIED

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[DiffViewer, Cmd | None]:
        """Handle keyboard scrolling and mouse wheel navigation."""
        if not self.focused:
            return self, None

        if isinstance(msg, MouseMsg):
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            if 0 <= local_x < self.width and 0 <= local_y < self.height:
                if msg.button == MouseButton.WHEEL_UP:
                    self.scroll_y = max(0, self.scroll_y - 2)
                    return self, None
                elif msg.button == MouseButton.WHEEL_DOWN:
                    self.scroll_y += 2
                    return self, None

        elif isinstance(msg, KeyMsg):
            match msg.key:
                case "up" | "k":
                    self.scroll_y = max(0, self.scroll_y - 1)
                    return self, None
                case "down" | "j":
                    self.scroll_y += 1
                    return self, None
                case "left" | "h":
                    self.scroll_x = max(0, self.scroll_x - 4)
                    return self, None
                case "right" | "l":
                    self.scroll_x += 4
                    return self, None
                case "pageup" | "pgup":
                    self.scroll_y = max(0, self.scroll_y - max(1, self.height - 2))
                    return self, None
                case "pagedown" | "pgdn":
                    self.scroll_y += max(1, self.height - 2)
                    return self, None
                case "home":
                    self.scroll_y = 0
                    self.scroll_x = 0
                    return self, None
                case "tab" | "m":
                    self.toggle_mode()
                    return self, None

        return self, None

    def _render_tokens(self, tokens: list[tuple[str, str]], is_added: bool) -> str:
        """Render tokens with word-level highlight styles."""
        parts: list[str] = []
        for text, token_type in tokens:
            if token_type == "same":
                parts.append((self.added_style if is_added else self.removed_style).render(text))
            elif token_type == "added":
                parts.append(self.added_highlight_style.render(text))
            elif token_type == "removed":
                parts.append(self.removed_highlight_style.render(text))
        return "".join(parts)

    def _build_unified_lines(self) -> list[str]:
        """Construct full unified diff output lines."""
        rendered: list[str] = []

        for hunk in self.hunks:
            # Hunk header
            hunk_header_styled = self.hunk_style.render(f"  {hunk.header}")
            rendered.append(hunk_header_styled)

            for line in hunk.lines:
                # Gutter line numbers
                if self.show_line_numbers:
                    old_str = f"{line.old_lineno:4d}" if line.old_lineno is not None else "    "
                    new_str = f"{line.new_lineno:4d}" if line.new_lineno is not None else "    "
                    gutter = self.gutter_style.render(f"{old_str} {new_str} │ ")
                else:
                    gutter = ""

                # Line content with possible intra-line tokens
                type_prefix = line.line_type
                if line.tokens is not None and self.highlight_words:
                    body = self._render_tokens(line.tokens, is_added=(line.line_type == "+"))
                elif line.line_type == "+":
                    body = self.added_style.render(f"{line.content}")
                elif line.line_type == "-":
                    body = self.removed_style.render(f"{line.content}")
                else:
                    body = self.context_style.render(f"{line.content}")

                prefix_styled = (
                    self.added_style.render("+ ") if line.line_type == "+"
                    else self.removed_style.render("- ") if line.line_type == "-"
                    else self.context_style.render("  ")
                )
                rendered.append(f"{gutter}{prefix_styled}{body}")

        return rendered

    def _build_split_lines(self) -> list[str]:
        """Construct side-by-side dual pane diff output lines."""
        rendered: list[str] = []
        half_w = max(10, (self.width - 3) // 2)

        for hunk in self.hunks:
            # Hunk header
            hunk_bar = self.hunk_style.render(f"── {hunk.header} ".ljust(self.width, "─"))
            rendered.append(hunk_bar)

            # Align deletions and additions side by side
            i = 0
            n = len(hunk.lines)
            while i < n:
                del_block: list[DiffLine] = []
                add_block: list[DiffLine] = []

                while i < n and hunk.lines[i].line_type == "-":
                    del_block.append(hunk.lines[i])
                    i += 1
                while i < n and hunk.lines[i].line_type == "+":
                    add_block.append(hunk.lines[i])
                    i += 1

                if not del_block and not add_block:
                    # Context line on both sides
                    ctx = hunk.lines[i]
                    i += 1
                    left_num = f"{ctx.old_lineno:4d} " if ctx.old_lineno is not None else "     "
                    right_num = f"{ctx.new_lineno:4d} " if ctx.new_lineno is not None else "     "
                    left_text = truncate_ansi(f"{left_num}  {ctx.content}", half_w)
                    right_text = truncate_ansi(f"{right_num}  {ctx.content}", half_w)

                    left_pad = " " * max(0, half_w - string_width(left_text))
                    right_pad = " " * max(0, half_w - string_width(right_text))
                    div = self.divider_style.render(" │ ")
                    rendered.append(f"{self.context_style.render(left_text)}{left_pad}{div}{self.context_style.render(right_text)}{right_pad}")
                    continue

                # Align block pairs
                max_rows = max(len(del_block), len(add_block))
                for r in range(max_rows):
                    # Left side (deleted)
                    if r < len(del_block):
                        d_line = del_block[r]
                        num_str = f"{d_line.old_lineno:4d} " if d_line.old_lineno is not None else "     "
                        if d_line.tokens and self.highlight_words:
                            t_body = self._render_tokens(d_line.tokens, is_added=False)
                            left_raw = f"{num_str}- {t_body}"
                        else:
                            left_raw = self.removed_style.render(f"{num_str}- {d_line.content}")
                    else:
                        left_raw = self.context_style.render("     · ")

                    # Right side (added)
                    if r < len(add_block):
                        a_line = add_block[r]
                        num_str = f"{a_line.new_lineno:4d} " if a_line.new_lineno is not None else "     "
                        if a_line.tokens and self.highlight_words:
                            t_body = self._render_tokens(a_line.tokens, is_added=True)
                            right_raw = f"{num_str}+ {t_body}"
                        else:
                            right_raw = self.added_style.render(f"{num_str}+ {a_line.content}")
                    else:
                        right_raw = self.context_style.render("     · ")

                    left_trunc = truncate_ansi(left_raw, half_w)
                    right_trunc = truncate_ansi(right_raw, half_w)
                    left_pad = " " * max(0, half_w - string_width(left_trunc))
                    right_pad = " " * max(0, half_w - string_width(right_trunc))
                    div = self.divider_style.render(" │ ")
                    rendered.append(f"{left_trunc}{left_pad}{div}{right_trunc}{right_pad}")

        return rendered

    def view(self) -> str:
        """Render the diff viewer within allocated width and height."""
        # Top Header Bar
        lines: list[str] = []
        header_h = 0
        if self.show_header:
            mode_badge = f"[{self.mode.value.upper()}]"
            stats = f"+{self.stats_additions} / -{self.stats_deletions}"
            file_info = f"{self.fromfile} ➔ {self.tofile}"
            header_text = f" 🔍 DIFF {mode_badge}  {file_info}  ({stats}, {len(self.hunks)} hunks) [Tab: toggle mode]"
            pad = " " * max(0, self.width - string_width(header_text))
            header_rendered = self.header_style.render(truncate_ansi(f"{header_text}{pad}", self.width))
            lines.append(header_rendered)
            header_h = 1

        body_height = max(1, self.height - header_h)

        # Build raw lines
        all_lines = self._build_unified_lines() if self.mode == DiffMode.UNIFIED else self._build_split_lines()

        if not all_lines:
            empty_msg = Style().faint(True).render("  (No changes detected / empty diff)")
            lines.append(empty_msg)
            while len(lines) < self.height:
                lines.append("")
            return "\n".join(lines)

        # Clamp vertical scroll
        max_scroll = max(0, len(all_lines) - body_height)
        self.scroll_y = max(0, min(self.scroll_y, max_scroll))

        visible_slice = all_lines[self.scroll_y : self.scroll_y + body_height]
        for row in visible_slice:
            # Horizontal scroll & pad
            row_w = string_width(row)
            if row_w < self.width:
                lines.append(f"{row}{' ' * (self.width - row_w)}")
            else:
                lines.append(truncate_ansi(row, self.width))

        # Pad to full height
        while len(lines) < self.height:
            lines.append(" " * self.width)

        return "\n".join(lines)
