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
