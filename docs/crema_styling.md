# Crema Styling & Layout Guide

`espresso.crema` is a declarative styling, box model, and layout engine for terminal interfaces inspired by Charm's **Lip Gloss**.

---

## The `Style` Class

Styles are immutable, chainable objects. Modifying a style returns a new copy, making styles easy to share and extend.

```python
from espresso.crema import Style, ROUNDED_BORDER, Align

base_style = Style().foreground("#FAFAFA").padding(1, 2)
card_style = base_style.border(ROUNDED_BORDER).border_foreground("#7D56F4")
alert_style = base_style.border(ROUNDED_BORDER).border_foreground("#FF5252")
```

---

## Colors

Crema supports:
1. **TrueColor (24-bit RGB)**: Hex strings like `"#7D56F4"` or RGB tuples `(125, 86, 244)`.
2. **ANSI 256 Palette**: Integers from `0` to `255`.
3. **Adaptive Colors**: Automatically switch between light and dark terminal backgrounds.
4. **NO_COLOR Standard**: If `NO_COLOR` is present in the environment, ANSI colors are suppressed.

```python
style = Style().foreground("#00E676").background(235)
```

---

## Text Attributes

Enable text decorations:
```python
style = (
    Style()
    .bold(True)
    .italic(True)
    .underline(True)
    .faint(True)
    .strikethrough(True)
    .reverse(True)
)
```

---

## Box Model (Padding, Margin & Borders)

Crema implements the standard CSS box model:

```
┌ Margin ──────────────────────────────────────────┐
│  ┌ Border ────────────────────────────────────┐  │
│  │  ┌ Padding ─────────────────────────────┐  │  │
│  │  │  Content text                        │  │  │
│  │  └──────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Padding & Margins
Supports CSS shorthand:
* 1 argument: all 4 sides (`padding(1)`)
* 2 arguments: (top/bottom, left/right) (`padding(1, 2)`)
* 4 arguments: (top, right, bottom, left) (`padding(1, 2, 1, 2)`)

### Borders
Predefined border styles:
* `ROUNDED_BORDER`: `╭ ─ ╮ │ ╯ ─ ╰ │`
* `NORMAL_BORDER`: `┌ ─ ┐ │ ┘ ─ └ │`
* `DOUBLE_BORDER`: `╔ ═ ╗ ║ ╝ ═ ╚ ║`
* `THICK_BORDER`: `┏ ━ ┓ ┃ ┛ ━ ┗ ┃`
* `BLOCK_BORDER`: `▀ ▄ █`
* `HIDDEN_BORDER`: `" "` (useful for alignment without visible lines)

```python
style = (
    Style()
    .border(ROUNDED_BORDER)
    .border_foreground("#E056FD")
    .padding(1, 2)
    .margin(1, 0)
)
```

### Border Titles
Embed styled titles directly into the top border bar with custom alignment:

```python
from espresso.crema import Style, ROUNDED_BORDER, Align

panel = (
    Style()
    .border(ROUNDED_BORDER)
    .border_foreground("#7D56F4")
    .border_title(" [ System Status ] ", align=Align.LEFT)
    .width(40)
    .render("All systems operational.")
)
print(panel)
```

Available title alignments:
- `Align.LEFT`: `╭─ [ Title ] ──────────╮`
- `Align.CENTER`: `╭─────── [ Title ] ───────╮`
- `Align.RIGHT`: `╭────────── [ Title ] ─╮`

If explicit box width is smaller than the title, Crema safely truncates the title with an ellipsis (`…`) while preserving box geometry and corner connections.

---

## Word Wrapping (`wrap_ansi`)

Standard `textwrap` corrupts terminal strings containing ANSI escape codes, miscalculating visual character widths and causing color bleeding across wrapped lines.

Crema provides `wrap_ansi(text, width)`:
* **Preserves ANSI Sequences**: Active styles (colors, bold, underline) are carried over cleanly into wrapped lines.
* **Prevents Color Bleeding**: Lines automatically terminate with reset codes (`\x1b[0m`) and reopen styles on the next line.
* **Accurate Unicode Widths**: Evaluates CJK fullwidth characters and multi-byte emojis as 2 visual cells.
* **Preserves Hard Breaks**: Existing newlines and paragraph breaks are respected.

```python
from espresso.crema import wrap_ansi, Style

styled_text = Style().bold(True).foreground("#FF5252").render(
    "Warning: The database connection timed out after multiple retry attempts across availability zones."
)

wrapped = wrap_ansi(styled_text, width=35)
print(wrapped)
```

---

## TrueColor Linear Gradients

Crema provides TrueColor (24-bit RGB) linear interpolation across text strings and palette generation.

### `linear_gradient(text, start_hex, end_hex)`
Smoothly interpolates foreground RGB values across the printable characters of a string:

```python
from espresso.crema import linear_gradient

# Horizontal TrueColor gradient from coral to neon pink
banner = linear_gradient("ESPRESSO TERMINAL UI", "#FF5E3A", "#FF2A68")
print(banner)

# Multi-line gradient preserving newlines and preventing background bleed
multiline_banner = linear_gradient("WELCOME\nTO\nESPRESSO", "#00E676", "#7D56F4")
print(multiline_banner)
```

<p align="center">
  <img src="https://raw.githubusercontent.com/kimusan/espresso/main/assets/demos/demo_colors_and_gradients.gif" alt="Crema TrueColor Linear Gradients and Box Model" width="700" />
</p>

### `gradient(start_color, end_color, steps)`
Generate a sequence of `TrueColor` steps for styling tables, progress bars, or charts:

```python
from espresso.crema import gradient, Style

colors = gradient("#00E676", "#FF5252", steps=10)
for idx, col in enumerate(colors):
    print(Style().foreground(col).render(f"Step {idx + 1:2d}"))
```

All gradient functions automatically respect the `NO_COLOR` environment standard, rendering clean unstyled text when requested.

---

## 2D Layout Primitives

Crema provides layout utilities that combine multi-line ASCII blocks without corrupting ANSI colors or cell alignments.

### `join_horizontal(align, *blocks)`
Place blocks side by side:
```python
from espresso.crema import join_horizontal, Align

layout = join_horizontal(Align.TOP, left_pane, "  ", right_pane)
```

### `join_vertical(align, *blocks)`
Stack blocks vertically with horizontal alignment:
```python
from espresso.crema import join_vertical, Align

layout = join_vertical(Align.CENTER, header, content, footer)
```

### `place(width, height, h_align, v_align, content)`
Place a block inside a fixed-size 2D bounding box:
```python
from espresso.crema import place, Align

centered_box = place(80, 24, Align.CENTER, Align.CENTER, card)
```

### `place_overlay(base, overlay, x=None, y=None, center=False, dim_backdrop=False)`
Composite floating modals, popups, or dialog boxes directly over a background view with optional backdrop dimming:
```python
from espresso.crema import place_overlay

# Center modal dialog with dimmed background screen
composited = place_overlay(screen_view, dialog.view(), center=True, dim_backdrop=True)
```

---

## Box Background Fills & Gradients

`Style` supports solid color fills as well as 2-color and multi-stop background gradients across the interior of boxes:

```python
from espresso.crema import Style, ROUNDED_BORDER, Align

# 1. Solid background fill
card = (
    Style()
    .background("#1E1035")
    .foreground("#FAFAFA")
    .padding(1, 2)
    .width(40)
    .render("Solid background card")
)

# 2. Linear background gradient (vertical or horizontal)
gradient_card = (
    Style()
    .background_gradient("#1A090D", "#4A1525", direction="vertical")
    .foreground("#FFFFFF")
    .border(ROUNDED_BORDER)
    .border_foreground("#FF5E3A")
    .width(40)
    .height(6)
    .align(Align.CENTER)
    .align_vertical(Align.CENTER)
    .render("Gradient Filled Box")
)

# 3. Multi-stop linear gradient
multi_card = (
    Style()
    .background_gradient_multi(["#120826", "#1E1035", "#2D1219"], direction="horizontal")
    .width(50)
    .height(4)
    .render("Multi-stop gradient interior")
)
```

---

## Responsive Proportional Grid (`FlexBox`)

Inspired by `charm-and-friends/stickers`, `espresso.crema.flexbox` provides a 2D responsive grid layout container with:
- **Proportional ratio weights**: Columns and rows allocate space according to `ratio_x` and `ratio_y`.
- **Zero-jitter remainder distribution**: Extra pixel units are distributed across fractional remainders without column drifting.
- **Constraints**: Support for `fixed_width`, `fixed_height`, `min_width`, and `min_height`.
- **Dynamic callbacks**: Cells can take a string or a callable `(width, height) -> str` to render content tailored to the exact allocated dimensions.

### Usage
```python
from espresso.crema import FlexBox, Style, ROUNDED_BORDER

flex = FlexBox(width=80, height=20)

# Row 1: Header (fixed height 3)
r1 = flex.new_row(height=3)
r1.new_cell(
    content="Header Banner",
    style=Style().background("#7D56F4").bold(True).foreground("#FFFFFF")
)

# Row 2: Proportional Split (Sidebar ratio 1, Main content ratio 3)
r2 = flex.new_row(ratio_y=1)
r2.new_cell(
    content=lambda w, h: f"Sidebar ({w}x{h})",
    ratio_x=1,
    min_width=18,
    style=Style().border(ROUNDED_BORDER).border_foreground("#555577")
)
r2.new_cell(
    content=lambda w, h: f"Main Content Area ({w}x{h})",
    ratio_x=3,
    style=Style().border(ROUNDED_BORDER).border_foreground("#00E5FF")
)

# Render formatted grid
print(flex.render())
```

---

## Multi-Column Grid & Framed Panels (`Grid`)

`espresso.crema.Grid` provides high-level static layout helpers for rendering multi-column grids and framed card panels with zero boilerplate.

### 1. Fixed Column Grid (`Grid.columns`)
Lays out a sequence of rendered card strings across a fixed number of columns with configurable column gaps and widths:

```python
from espresso.crema import Grid

# Equal column distribution within a total terminal width
grid_str = Grid.columns(
    cards=[card1, card2, card3, card4],
    cols=2,
    gap=2,
    total_width=80,
)

# Explicit column widths
custom_grid = Grid.columns(
    cards=[sidebar, main_pane],
    cols=2,
    col_widths=[25, 55],
    gap=1,
)
```

### 2. Responsive Auto-Fitting Grid (`Grid.auto_fit`)
Automatically calculates the optimal number of columns that can fit within the available canvas width given a minimum column width:

```python
# Automatically fits 1, 2, 3, or more columns based on terminal width
responsive_grid = Grid.auto_fit(
    cards=[card1, card2, card3, card4, card5],
    total_width=terminal_width,
    min_col_width=28,
    gap=2,
)
```

### 3. Framed Card Panels (`Grid.panel`)
Constructs a styled, framed panel container with an embedded title badge, custom borders, and automatic content line truncation to prevent horizontal overflow:

```python
from espresso.crema import Grid, ROUNDED_BORDER

panel = Grid.panel(
    title="System Metrics",
    content="CPU: 12%\nMemory: 4.2GB / 16GB\nLoad: 0.85",
    width=34,
    height=8,
    border=ROUNDED_BORDER,
    border_foreground="#7D56F4",
)
```
