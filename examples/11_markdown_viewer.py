#!/usr/bin/env python3
"""Example 11: Interactive Terminal Markdown Viewer.

Showcases the MarkdownViewer component with full document parsing,
headings, styled inline formatting, fenced code blocks, blockquotes,
multi-level lists, and smooth viewport scrolling.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, MouseMsg, Msg, Program, WindowSizeMsg, quit_app
from espresso.beans import MarkdownViewer, Tabs, TabStyle
from espresso.crema import ROUNDED_BORDER, Style, join_horizontal, join_vertical, string_width

SAMPLE_DOC_1 = """# ☕ Espresso TUI Framework

> A lightweight, declarative Elm Architecture (TEA) framework for Python terminal apps.
> Inspired by Bubble Tea, Lip Gloss, and Bubbles.

---

## 🌟 Key Pillars

1. **The Elm Architecture (TEA)**
   - Pure functional Model-Update-View state loop.
   - Declarative command dispatching with zero external runtime dependencies.
2. **Crema Styling Engine**
   - CSS-inspired box model with padding, margins, borders, and alignments.
   - 24-bit Truecolor gradients and adaptive light/dark theme detection.
3. **Beans Standard Library**
   - Over 25 production-ready terminal UI components.
   - Fully interactive with keyboard and mouse tracking.

---

## 📦 Quick Start Code

Here is how you initialize an interactive Espresso application:

```python
from espresso import Model, Program

class Counter(Model):
    def __init__(self):
        self.count = 0

    def update(self, msg):
        if msg.key == "up":
            self.count += 1
        return self, None

    def view(self):
        return f"Count: {self.count}"

Program(Counter()).run()
```

---

## 🚀 Component Highlights

- **MarkdownViewer**: Native terminal Markdown rendering.
- **CodeViewer**: Syntax-highlighted code with line numbers.
- **PipelineProgress**: Multi-stage task execution runner.
- **QuickFix**: Neovim-style diagnostic bottom drawer.
- **DetailSelector**: Selection menu with live synchronized preview card.
- **ImageViewer**: Truecolor ANSI 24-bit half-block pixel graphics.

### Markdown Features Supported
- **Bold** and *Italic* text formatting.
- `Inline code snippets` with distinct backgrounds.
- ~~Strikethrough~~ and [clickable markdown links](https://github.com/charmbracelet/bubbletea).
- Blockquotes with colored left accent bars.
- Multi-level nested bullet points and numbered lists.
"""

SAMPLE_DOC_2 = """# 🎨 Crema Styling Engine

Crema provides declarative terminal layout and color capabilities.

## 🌈 Gradients & Colors

You can blend any two colors with ease:

```python
from espresso.crema import Style, linear_gradient

colors = linear_gradient("#7D56F4", "#00E5FF", steps=20)
for col in colors:
    print(Style().foreground(col).render("█"), end="")
```

---

## 📐 Box Model

- **Padding**: Internal breathing room `padding(top, right, bottom, left)`.
- **Borders**: `ROUNDED_BORDER`, `DOUBLE_BORDER`, `HIDDEN_BORDER`.
- **Alignments**: `Align.LEFT`, `Align.CENTER`, `Align.RIGHT`.

> [!TIP]
> Always test your TUIs in both dark and light terminal backgrounds using AdaptiveColor!
"""

SAMPLE_DOC_3 = """# 🛠️ Architecture & Philosophy

Espresso follows strict architectural guidelines:

1. **Zero Runtime Dependencies**
   - Pure Python 3.10+ standard library.
   - No external C extensions or binary wheels required.
2. **Double-Buffered Renderer**
   - Zero-flicker line diffing buffer.
   - Updates only modified screen cells.
3. **SGR 1006 Mouse Protocol**
   - Pixel-perfect clicks, drags, and mouse wheel navigation.
"""

DOCS = [
    ("Overview", SAMPLE_DOC_1),
    ("Crema Styles", SAMPLE_DOC_2),
    ("Architecture", SAMPLE_DOC_3),
]


class MarkdownViewerApp(Model):
    def __init__(self) -> None:
        self.width = 80
        self.height = 24
        self.active_doc_idx = 0

        self.tabs = Tabs(
            titles=[d[0] for d in DOCS],
            active_tab=0,
            tab_style=TabStyle.PILL,
            show_numbers=True,
        )

        self.viewer = MarkdownViewer(
            content=DOCS[0][1],
            width=self.width - 4,
            height=self.height - 6,
            show_footer=True,
        )

        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.border_style = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4")
        self.footer_style = Style().foreground("#8888AA")

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MarkdownViewerApp, Cmd | None]:
        if isinstance(msg, WindowSizeMsg):
            self.width = max(60, msg.width)
            self.height = max(16, msg.height)
            self.viewer.set_size(self.width - 4, self.height - 6)
            return self, None

        if isinstance(msg, MouseMsg):
            self.viewer, cmd = self.viewer.update(msg)
            return self, cmd

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app
                case "1" | "2" | "3":
                    idx = int(msg.key) - 1
                    if idx != self.active_doc_idx:
                        self.active_doc_idx = idx
                        self.tabs.set_active(idx)
                        self.viewer.set_content(DOCS[idx][1])
                    return self, None
                case "tab":
                    idx = (self.active_doc_idx + 1) % len(DOCS)
                    self.active_doc_idx = idx
                    self.tabs.set_active(idx)
                    self.viewer.set_content(DOCS[idx][1])
                    return self, None

        self.viewer, cmd = self.viewer.update(msg)
        return self, cmd

    def view(self) -> str:
        # Header bar
        header_title = self.title_style.render("📖 Markdown Document Browser")
        tabs_bar = self.tabs.view()
        header = f"{header_title}   {tabs_bar}"

        # Markdown viewport inside rounded border
        card_h = self.viewer.height + 2
        card = self.border_style.width(self.width - 2).height(card_h).render(self.viewer.view())

        # Footer help
        help_text = "Tab / 1-3: Switch document • ↑/↓ or j/k: Scroll • PgUp/PgDn: Jump • q: Quit • Mouse Wheel enabled"
        footer = self.footer_style.render(help_text)

        return f"{header}\n{card}\n{footer}"


def main() -> None:
    Program(MarkdownViewerApp()).run()


if __name__ == "__main__":
    main()
