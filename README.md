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
| **`espresso`** | `bubbletea` | **The Strong Base**: Core TEA framework, runtime event loop, raw terminal driver, command primitives, line-diffing alt-screen renderer, SGR mouse tracking, and gesture engine. |
| **`espresso.crema`** | `lipgloss` | **The Smooth Crema**: Declarative styling, box model, TrueColor (24-bit RGB), ANSI 256, borders, border titles, TrueColor linear gradients, ANSI word-wrapping, 2D layout alignment, FlexBox, and responsive Grid. |
| **`espresso.beans`** | `bubbles` | **The Flavorful Beans**: 39 reusable UI components including TextArea, GitTree, CommandPalette, BarChart, Splitter, Sliders, Form, DiffViewer, SortableList, Confetti, CodeViewer, MarkdownViewer, Tables, Viewports, and more. |

---

## 🚀 Quickstart

### Installation

**Via PyPI**:
```bash
pip install espressoTUI
```

**Universal Standalone Executable (Zero Installation)**:
Download the standalone `espresso.pyz` from [GitHub Releases](https://github.com/kimusan/espresso/releases):
```bash
curl -LO https://github.com/kimusan/espresso/releases/latest/download/espresso.pyz
chmod +x espresso.pyz
./espresso.pyz gallery
```

**Native Binaries (No Python Runtime Required)**:
Pre-compiled self-contained native binaries are available on every release for:
- **Linux x86_64**: `espresso-linux-x86_64`
- **macOS Apple Silicon**: `espresso-macos-arm64`
- **macOS Intel**: `espresso-macos-x86_64`
- **Windows x86_64**: `espresso-windows-x86_64.exe`

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

### Layout Primitives, Responsive Grid & Overlays
Stack and stitch styled blocks side-by-side, vertically, in a proportional flex layout, or in a responsive multi-column grid:
```python
from espresso.crema import join_horizontal, join_vertical, place_overlay, Grid, FlexBox, Align

# 1. 2D Side-by-side join
split_view = join_horizontal(Align.TOP, left_sidebar, "  ", right_content)

# 2. Multi-column grid & auto-fitting panels
grid_view = Grid.columns([card1, card2, card3], cols=3, gap=1, total_width=80)
card_panel = Grid.panel("System Metrics", metrics_text, width=32, height=12)

# 3. Responsive proportional layout (FlexBox)
flex = FlexBox(width=80, height=24)
row = flex.new_row(ratio_y=1)
row.new_cell("Sidebar", ratio_x=1, min_width=20)
row.new_cell("Main View", ratio_x=3)

# 4. Floating modal compositor with backdrop dimming
screen = place_overlay(background_view, dialog.view(), center=True, dim_backdrop=True)
```

---

## 🖱️ First-Class Mouse & Gesture Support

Espresso provides built-in mouse tracking (SGR 1006) with advanced gesture synthesis:

- **Program Toggle**: `Program(App(), mouse=True)` or `Program(App()).with_mouse(True)`
- **Dynamic TEA Commands**: Emit `enable_mouse` or `disable_mouse` commands directly from `update()`
- **Event Handling**: Pattern match `MouseMsg(action, button, x, y)` in `update()`
- **Gestures Supported**: `MouseAction.PRESS`, `RELEASE`, `MOTION`, `DOUBLE_CLICK`, and drag-and-drop tracking with `MouseGestureTracker`

---

## 🧩 Beans: Standard Component Library

Espresso includes **39 ready-to-use building blocks** that follow the exact same TEA model:

* **`TextArea`**: Multi-line interactive text editor with line numbers, cursor navigation, and viewport scrolling.
* **`Help`**: Adaptive hotkey documentation rendering compact single-line or multi-column full keybinding views.
* **`Timer`**: High-precision countdown timer driven by tea tick commands with formatted duration and percentage completion.
* **`Stopwatch`**: High-precision elapsed time tracker with split-second hundredths display and toggle/reset controls.
* **`Spinner`**: Animated loading indicators (`DOTS`, `LINE`, `PULSE`, `COFFEE`, `GLOBE`, `MOON`).
* **`TextInput`**: Single-line text input with blinking cursor, password masking, and navigation.
* **`Progress`**: Customizable gradient progress bars with percentage indicators.
* **`Table`**: Column-based tabular data viewer with navigable row selection and sticky headers.
* **`Viewport`**: Scrollable pane for viewing long-form text or logs.
* **`Paginator`**: Pagination manager with bullet dots, numeric counters, descriptive ranges, and zero-jitter bounds slicing.
* **`Dialog`**: Modal confirmation and decision box with custom action buttons and `place_overlay` backdrop dimming.
* **`List`**: Searchable, filterable list with real-time `/` search query input, pagination, and selection events.
* **`FilePicker`**: Interactive directory browser with file size formatting, extension filters, and hidden file toggle.
* **`Prompt`**: CLI prompts (`SelectPrompt`, `MultiSelectPrompt` checkboxes, and `ConfirmPrompt` `[y/N]`).
* **`ToastManager`**: Transient notification alerts (`INFO`, `SUCCESS`, `WARNING`, `ERROR`) with auto-dismiss timers.
* **`Tabs`**: Top tab bar navigation with customizable styles (`PILL`, `LINE`, `BRACKET`) and hotkeys 1-9.
* **`Tree`**: Hierarchical collapsible tree view with Unicode branch connectors (`├──`, `└──`).
* **`StatusBar`**: Multi-section responsive status bar with Left/Center/Right clusters and priority-based auto-truncation.
* **`Metric` & `MetricGroup`**: Dashboard KPI stat cards, tags, and summary lists with delta trend arrows and inverted metrics.
* **`NavStack`**: Hierarchical view router with push/pop management, breadcrumb trails, and automatic message forwarding.
* **`DatePicker`**: Interactive calendar date picker with month/year navigation, mouse selection, and date range clamping.
* **`PipelineProgress`**: Multi-stage CI/CD workflow pipeline visualizer with real-time spinners, checkmarks, and timestamps.
* **`MarkdownViewer`**: Streaming GitHub-flavored markdown viewer with code blocks, tables, lists, and mouse scrolling.
* **`CodeViewer`**: Syntax-highlighted source code editor viewer (Python, JS, Go, Rust, SQL, JSON) with line numbers and themes.
* **`QuickFix`**: Interactive diagnostics and code action list with severity badges (`ERROR`, `WARNING`, `INFO`).
* **`DetailSelector`**: Master-detail dual-pane list selector with real-time preview panels and category filtering.
* **`ImageViewer`**: Terminal ASCII and Unicode half-block TrueColor image renderer for BMP and PPM formats.
* **`Splitter`**: Interactive dual-pane container (`Horizontal` / `Vertical`) with draggable divider bar and keyboard resizing.
* **`Slider` & `RangeSlider`**: Tactile numeric sliders and dual-thumb range bars with mouse dragging.
* **`Sparkline`**: High-resolution 2D Unicode Braille curves and 1D block charts with trend indicators.
* **`Marquee`**: Animated horizontal scrolling text banner with loop and bounce physics.
* **`SortableList`**: Reorderable list with drag-and-drop mouse handling and visual drop targets.
* **`Spring`**: Physical damped harmonic oscillator simulation solving harmonic differential equations.
* **`Confetti`**: 2D celebratory particle physics emitter (radial bursts, cannons, rain) with drag & gravity.
* **`DiffViewer`**: Git diff visualizer with Unified and Split dual-pane views and intra-line word diffs.
* **`Form` & `FormBuilder`**: Composite multi-field container with field/form validation, error badges, and Tab cycling.
* **`CommandPalette`**: Fuzzy spotlight search runner (Ctrl+P / Cmd+P) with recents tracking and modal overlay.
* **`GitTree`**: Multi-column collapsible file tree with Git status badges (`[M]`, `[A]`, `[D]`, `[?]`) and branch headers.
* **`BarChart`**: Horizontal and vertical bar charts with sub-character precision, auto-scaling, and TrueColor gradients.

---

## 🛠️ Built-in CLI Tool

Espresso includes a powerful command-line interface for running and scaffolding applications:

```bash
# List all 14 built-in interactive examples
espresso list

# Run any example by ID or file path
espresso run 14
espresso run 10

# Launch interactive component gallery
espresso gallery

# Scaffold a production-ready Espresso TEA app
espresso new my_dashboard.py
```

---

## 📚 Examples Included

Explore the interactive demos in `examples/`:

| Example | Command | Highlights |
| :--- | :--- | :--- |
| **01 Counter** | `espresso run 01` | Basic Model-Update-View state transitions |
| **02 Shopping List** | `espresso run 02` | List cursor navigation & item selection toggle |
| **03 Styled Dashboard** | `espresso run 03` | Crema cards, TrueColor, tabs, side-by-side layout |
| **04 Fullscreen & Mouse** | `espresso run 04` | Alt-screen mode, SGR mouse clicks, wheel scrolling, resize |
| **05 Beans Wizard** | `espresso run 05` | Multi-component wizard (TextInput, Table, Spinner, Progress, Viewport) |
| **06 Commit Helper** | `espresso run 06` | Practical developer tool for Conventional Commits |
| **07 Editor** | `espresso run 07` | Multi-line text editor with TextArea, status bar, and Help |
| **08 RSS Reader** | `espresso run 08` | Fullscreen 3-panel RSS reader with live feed fetching from schulz.dk |
| **09 Colors & Gradients** | `espresso run 09` | TrueColor showcase, multi-stop gradients, box background fills, palette cycling |
| **10 Component Gallery** | `espresso run 10` | Full-window edge-to-edge gallery of 20+ beans, mouse support, tabs, modals, prompts |
| **11 Markdown Viewer** | `espresso run 11` | Streaming GitHub-flavored markdown viewer with code blocks and mouse scrolling |
| **12 Interactive & Animated** | `espresso run 12` | Splitter, Sliders, Marquee, and SortableList with mouse drag |
| **13 Physics & Tools** | `espresso run 13` | Confetti physics engine, forms with validation, and diff viewer |
| **14 Developer Workspace** | `espresso run 14` | Flagship IDE integrating GitTree, BarChart, CodeViewer, and CommandPalette |

---

## 📖 In-Depth Documentation

* [Architecture & The Elm Pattern](docs/architecture.md)
* [Crema Styling & Layout Guide](docs/crema_styling.md)
* [Beans Component Catalog](docs/beans_components.md)
* [Release & Packaging Guide](docs/releasing.md)
* [GitHub Project Wiki](https://github.com/kimusan/espresso/wiki)

---

## 🧪 Running Tests

Espresso includes a comprehensive automated test suite testing state transitions, ANSI parsing, and event loops deterministically:

```bash
PYTHONPATH=src python3 -m unittest discover tests
```

---

## 📄 License

MIT License. Copyright (c) 2026 Kim Schulz.
