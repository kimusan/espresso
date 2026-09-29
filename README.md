# ☕ Espresso

> A lightweight, declarative Elm Architecture (TEA) terminal UI framework for Python.
> Inspired by Charm's **Bubble Tea**, **Lip Gloss**, and **Bubbles**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#features)
[![Architecture: TEA](https://img.shields.io/badge/architecture-Elm-orange.svg)](https://guide.elm-lang.org/architecture/)

```
       (  )   (   )  )
        ) (   )  (  (
        ( )  (    ) )
        _____________
       <_____________> ___
       |             |/ _ \
       |  ESPRESSO   | | | |
       |   CREMA     |_| |_|
       |___BEANS_____|\___/
       \_____________/
```

---

## 🌟 Why Espresso?

Terminal applications in Python have historically required heavy object-oriented widget hierarchies, complex retained-state DOM trees, or callback-laden curses wrappers.

**Espresso brings The Elm Architecture (TEA) to Python:**
1. **Purity & Determinism**: Your application state is a simple `Model`. Changes only happen through an `update(msg)` function.
2. **View is Pure**: Rendering is a simple `view() -> str` function that turns state into a styled ANSI string.
3. **No Race Conditions**: Background operations (network, timers, disk I/O) are isolated in `Cmd` (commands) that emit messages back into the event loop.
4. **Zero Dependencies**: Runs out of the box using Python's standard library (`asyncio`, `termios`, `tty`, `unicodedata`).
5. **Modern Python 3.10+ Ergonomics**: Native support for structural pattern matching (`match / case`).

---

## ☕ The Espresso Ecosystem

| Layer | Charm Equivalent | Description |
| :--- | :--- | :--- |
| **`espresso`** | `bubbletea` | **The Strong Base**: Core TEA framework, runtime event loop, raw terminal driver, command primitives. |
| **`espresso.crema`** | `lipgloss` | **The Smooth Crema**: Declarative styling, box model, TrueColor (24-bit RGB), ANSI 256, borders, border titles, TrueColor linear gradients, ANSI word-wrapping, and 2D layout alignment. |
| **`espresso.beans`** | `bubbles` | **The Flavorful Beans**: Reusable UI components including TextArea, Help, Timer, Stopwatch, Spinners, TextInputs, Tables, Viewports, and Progress bars. |

---

## 🚀 Quickstart

### Installation
```bash
pip install espresso-tui
```
*(Or clone the repository and run directly with Python 3.10+)*

### 1. Minimal Interactive Counter
```python
from espresso import Model, Msg, Cmd, KeyMsg, Program, quit_app

class Counter(Model):
    def __init__(self):
        self.count = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="+" | "up"):
                self.count += 1
            case KeyMsg(key="-" | "down"):
                self.count -= 1
            case KeyMsg(key="q" | "esc"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        return f"Count: {self.count}\n\n[+/-] Adjust  [q] Quit"

if __name__ == "__main__":
    Program(Counter()).run()
```

---

## 🎨 Crema: Declarative Terminal Styling

Crema brings CSS-like fluency and box-model precision to terminal strings:

```python
from espresso.crema import Style, ROUNDED_BORDER, Align

card = (
    Style()
    .bold(True)
    .foreground("#FAFAFA")
    .background("#7D56F4")
    .border(ROUNDED_BORDER)
    .border_foreground("#00E676")
    .border_title(" [ Espresso Crema ] ", align=Align.LEFT)
    .padding(1, 2)
    .width(40)
    .align(Align.CENTER)
    .render("Hello from Espresso Crema!")
)
print(card)
```

### Word-Wrapping & Linear Gradients
Crema includes advanced ANSI-aware text processing:
```python
from espresso.crema import wrap_ansi, linear_gradient

# Wrap text with full style preservation across soft line breaks
wrapped = wrap_ansi(long_styled_text, width=60)

# Smooth TrueColor linear RGB gradients across string characters
banner = linear_gradient("Espresso TrueColor Gradient", "#FF5E3A", "#FF2A68")
```

### Layout Primitives
Stack and stitch styled blocks side-by-side or vertically without breaking ANSI codes:
```python
from espresso.crema import join_horizontal, join_vertical, Align

split_view = join_horizontal(Align.TOP, left_sidebar, "  ", right_content)
```

---

## 🧩 Beans: Standard Component Library

Espresso includes ready-to-use building blocks that follow the exact same TEA model:

* **`TextArea`**: Multi-line interactive text editor with line numbers, cursor navigation, and viewport scrolling.
* **`Help`**: Adaptive hotkey documentation rendering compact single-line or multi-column full keybinding views.
* **`Timer`**: High-precision countdown timer driven by tea tick commands with formatted duration and percentage completion.
* **`Stopwatch`**: High-precision elapsed time tracker with split-second hundredths display and toggle/reset controls.
* **`Spinner`**: Animated loading indicators (`DOTS`, `LINE`, `PULSE`, `COFFEE`, `GLOBE`, `MOON`).
* **`TextInput`**: Single-line text input with blinking cursor, password masking, and navigation.
* **`Progress`**: Customizable gradient progress bars with percentage indicators.
* **`Table`**: Column-based tabular data viewer with navigable row selection and sticky headers.
* **`Viewport`**: Scrollable pane for viewing long-form text or logs.

---

## 📚 Examples Included

Explore the interactive demos in `examples/`:

| Example | Command | Highlights |
| :--- | :--- | :--- |
| **01 Counter** | `python3 examples/01_counter.py` | Basic Model-Update-View state transitions |
| **02 Shopping List** | `python3 examples/02_shopping_list.py` | List cursor navigation & item selection toggle |
| **03 Styled Dashboard** | `python3 examples/03_styled_layout.py` | Crema cards, TrueColor, tabs, side-by-side layout |
| **04 Fullscreen & Mouse** | `python3 examples/04_fullscreen_mouse.py` | Alt-screen mode, SGR mouse clicks, wheel scrolling, resize |
| **05 Beans Wizard** | `python3 examples/05_beans_showcase.py` | Multi-component wizard (TextInput, Table, Spinner, Progress, Viewport) |
| **06 Commit Helper** | `python3 examples/06_git_commit_helper.py` | Practical developer tool for Conventional Commits |
| **07 Editor** | `python3 examples/07_editor.py` | Multi-line text editor with TextArea, status bar, and Help |

---

## 📖 In-Depth Documentation

* [Architecture & The Elm Pattern](docs/architecture.md)
* [Crema Styling & Layout Guide](docs/crema_styling.md)
* [Beans Component Catalog](docs/beans_components.md)
* [GitHub Wiki Staging Files](docs/wiki_staging/)

---

## 🧪 Running Tests

Espresso includes a comprehensive automated test suite testing state transitions, ANSI parsing, and event loops deterministically:

```bash
PYTHONPATH=src python3 -m unittest discover tests
```

---

## 📄 License

MIT License. Copyright (c) 2026 Kim Schulz.
