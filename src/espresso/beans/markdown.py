"""Terminal Markdown viewer component.

Inspired by mistakenelf/teacup/markdown.
Parses Markdown formatting (headings, code blocks, lists, blockquotes,
inline styles, links, and horizontal rules) and renders it with rich
ANSI terminal styles inside an interactive scrollable Viewport.
"""

from __future__ import annotations

import re
from typing import Sequence

from espresso.beans.viewport import Viewport
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


def render_markdown(text: str, width: int = 80) -> str:
    """Parse a markdown string and return terminal ANSI-styled lines."""
    lines: list[str] = []
    raw_lines = text.splitlines()

    # Pre-compile inline regexes
    bold_pattern = re.compile(r"(\*\*|__)(.*?)\1")
    italic_pattern = re.compile(r"(\*|_)(.*?)\1")
    code_pattern = re.compile(r"(`)(.*?)\1")
    strike_pattern = re.compile(r"(~~)(.*?)\1")
    link_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")

    # Styles
    h1_style = Style().bold(True).foreground("#00E5FF").underline(True)
    h2_style = Style().bold(True).foreground("#7D56F4")
    h3_style = Style().bold(True).foreground("#00E676")
    h4_style = Style().bold(True).foreground("#FFD54F")
    code_inline_style = Style().foreground("#FF80BF").background("#282A36")
    code_block_style = Style().foreground("#F8F8F2")
    quote_bar_style = Style().bold(True).foreground("#00E5FF")
    quote_text_style = Style().italic(True).foreground("#B0BEC5")
    hr_style = Style().foreground("#555577")
    bullet_style = Style().bold(True).foreground("#00E5FF")
    link_style = Style().underline(True).foreground("#80D8FF")
    dim_style = Style().faint(True)

    def style_inline(line_text: str) -> str:
        """Apply bold, italic, inline code, and link styling to text."""
        # Code first to prevent styling inside code
        def _code_sub(m: re.Match) -> str:
            return code_inline_style.render(f" {m.group(2)} ")

        line_text = code_pattern.sub(_code_sub, line_text)

        # Links: [text](url) -> text (url)
        def _link_sub(m: re.Match) -> str:
            t = link_style.render(m.group(1))
            u = dim_style.render(f"({m.group(2)})")
            return f"{t} {u}"

        line_text = link_pattern.sub(_link_sub, line_text)

        # Bold
        def _bold_sub(m: re.Match) -> str:
            return Style().bold(True).render(m.group(2))

        line_text = bold_pattern.sub(_bold_sub, line_text)

        # Italic
        def _italic_sub(m: re.Match) -> str:
            return Style().italic(True).render(m.group(2))

        line_text = italic_pattern.sub(_italic_sub, line_text)

        # Strikethrough
        def _strike_sub(m: re.Match) -> str:
            return Style().strikethrough(True).render(m.group(2))

        line_text = strike_pattern.sub(_strike_sub, line_text)

        return line_text

    in_code_block = False
    code_lang = ""

    for line in raw_lines:
        stripped = line.strip()

        # Fenced code block start/end
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = stripped[3:].strip()
                tag = f" [{code_lang}] " if code_lang else ""
                border_top = hr_style.render(f"┌─{tag}─" + "─" * max(0, width - 6 - len(tag)) + "┐")
                lines.append(border_top)
            else:
                in_code_block = False
                border_bottom = hr_style.render("└" + "─" * max(0, width - 4) + "┘")
                lines.append(border_bottom)
            continue

        if in_code_block:
            # Code block line with left border
            bar = hr_style.render("│ ")
            lines.append(f"{bar}{code_block_style.render(line)}")
            continue

        # Horizontal Rule
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
            lines.append(hr_style.render("─" * min(width, 70)))
            continue

        # Headings
        if stripped.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if match:
                level = len(match.group(1))
                h_text = style_inline(match.group(2))
                if level == 1:
                    lines.append(h1_style.render(f"# {h_text}"))
                elif level == 2:
                    lines.append(h2_style.render(f"## {h_text}"))
                elif level == 3:
                    lines.append(h3_style.render(f"### {h_text}"))
                elif level == 4:
                    lines.append(h4_style.render(f"#### {h_text}"))
                else:
                    lines.append(Style().bold(True).render(f"{'#' * level} {h_text}"))
                continue

        # Blockquote
        if stripped.startswith(">"):
            q_content = style_inline(stripped.lstrip("> ").strip())
            bar = quote_bar_style.render("▌ ")
            lines.append(f"{bar}{quote_text_style.render(q_content)}")
            continue

        # Unordered List
        if re.match(r"^(\*|-|\+)\s+", stripped):
            item_text = re.sub(r"^(\*|-|\+)\s+", "", stripped)
            # Check indentation
            indent_count = len(line) - len(line.lstrip())
            bullet = "•" if indent_count == 0 else "◦"
            styled_bullet = bullet_style.render(bullet)
            indent_spaces = " " * indent_count
            lines.append(f"{indent_spaces}  {styled_bullet} {style_inline(item_text)}")
            continue

        # Ordered List
        if re.match(r"^\d+\.\s+", stripped):
            match = re.match(r"^(\d+\.)\s+(.*)$", stripped)
            if match:
                num_prefix = bullet_style.render(match.group(1))
                item_text = style_inline(match.group(2))
                indent_count = len(line) - len(line.lstrip())
                indent_spaces = " " * indent_count
                lines.append(f"{indent_spaces}  {num_prefix} {item_text}")
                continue

        # Blank line
        if not stripped:
            lines.append("")
            continue

        # Normal Paragraph
        lines.append(style_inline(line))

    return "\n".join(lines)


class MarkdownViewer(Model):
    """A scrollable terminal markdown browser with rich formatting."""

    def __init__(
        self,
        content: str = "",
        width: int = 80,
        height: int = 20,
        show_scrollbar: bool = True,
        show_footer: bool = True,
    ) -> None:
        self.raw_content = content
        self.width = max(20, width)
        self.height = max(4, height)
        self.show_scrollbar = show_scrollbar
        self.show_footer = show_footer

        self.rendered_content = render_markdown(content, width=self.width)
        viewport_h = max(2, self.height - 1 if self.show_footer else self.height)
        self.viewport = Viewport(width=self.width, height=viewport_h)
        self.viewport.set_content(self.rendered_content)

        self.footer_style = Style().foreground("#666688")
        self.dim_style = Style().faint(True)

    def set_content(self, content: str) -> None:
        """Update and re-parse the markdown document."""
        self.raw_content = content
        self.rendered_content = render_markdown(content, width=self.width)
        self.viewport.set_content(self.rendered_content)
        self.viewport.y_offset = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MarkdownViewer, Cmd | None]:
        """Handle keyboard navigation and mouse wheel scrolling."""
        if isinstance(msg, KeyMsg):
            if msg.key in ("pgdown", "pagedown", "space"):
                self.viewport.y_offset = min(self.viewport.max_offset, self.viewport.y_offset + self.viewport.height)
                return self, None
            elif msg.key in ("pgup", "pageup"):
                self.viewport.y_offset = max(0, self.viewport.y_offset - self.viewport.height)
                return self, None
            elif msg.key in ("home", "g"):
                self.viewport.y_offset = 0
                return self, None
            elif msg.key in ("end", "G"):
                self.viewport.y_offset = self.viewport.max_offset
                return self, None

        self.viewport, cmd = self.viewport.update(msg)
        return self, cmd

    def view(self) -> str:
        """Render the scrollable markdown viewport with optional status footer."""
        out = self.viewport.view()
        if not self.show_footer:
            return out

        pct = int(self.viewport.scroll_percent * 100)
        at_top = (self.viewport.y_offset == 0)
        at_bottom = (self.viewport.y_offset >= self.viewport.max_offset)
        pos_str = "Top" if at_top else ("Bot" if at_bottom else f"{pct}%")
        nav_help = "↑/↓ or j/k to scroll • pgup/pgdn • g/G"
        footer_left = self.dim_style.render(nav_help)
        footer_right = self.footer_style.render(f"[{pos_str}]")

        pad = max(1, self.width - string_width(footer_left) - string_width(footer_right))
        footer = f"{footer_left}{' ' * pad}{footer_right}"
        return f"{out}\n{footer}"
