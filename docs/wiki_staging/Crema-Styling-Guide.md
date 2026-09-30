# Crema Styling Guide

## Fluent Style Builder

Crema styles are created with `Style()` and chainable setters:

```python
from espresso.crema import Style, ROUNDED_BORDER, Align

header_style = (
    Style()
    .bold(True)
    .foreground("#FAFAFA")
    .background("#7D56F4")
    .padding(1, 2)
    .border(ROUNDED_BORDER)
    .border_title(" [ Dashboard ] ", align=Align.LEFT)
    .width(40)
    .align(Align.CENTER)
)
```

## Border Titles

Embed styled titles directly into the top border line with left, center, or right alignment:
- `.border_title(" [ Title ] ", align=Align.LEFT)`
- `.border_title(" [ Title ] ", align=Align.CENTER)`
- `.border_title(" [ Title ] ", align=Align.RIGHT)`

## ANSI Word Wrapping

`wrap_ansi(text, width)` wraps text to fit within width visual cells while preserving ANSI sequences and color styles without bleeding across line boundaries:

```python
from espresso.crema import wrap_ansi

wrapped = wrap_ansi(styled_text, width=40)
```

## TrueColor Linear Gradients

Smoothly interpolate 24-bit RGB foreground colors across characters while respecting the `NO_COLOR` standard:

```python
from espresso.crema import linear_gradient, gradient

# Gradient string
banner = linear_gradient("ESPRESSO CREMA", "#FF5E3A", "#FF2A68")

# Palette generator
palette = gradient("#00E676", "#7D56F4", steps=8)
```

## Layout Primitives & Overlays

- `join_horizontal(align, *blocks)`: Combine blocks horizontally side-by-side.
- `join_vertical(align, *blocks)`: Stack blocks vertically.
- `place(w, h, h_align, v_align, content)`: Center or position content inside a bounding box.
- `place_overlay(base, overlay, center=True, dim_backdrop=True)`: Composite floating modals and dialogs with backdrop dimming.

## Box Background Fills & Gradients

- `.background("#1E1035")`: Solid background color fill.
- `.background_gradient("#1A090D", "#4A1525", direction="vertical")`: 2-color linear background gradient.
- `.background_gradient_multi(["#120826", "#1E1035", "#2D1219"], direction="horizontal")`: Multi-stop linear gradient.

## Responsive Proportional Grid (`FlexBox`)

Responsive 2D grid container with zero-jitter remainder allocation, proportional ratio weights, minimum bounds, and cell render callbacks:

```python
from espresso.crema import FlexBox, Style, ROUNDED_BORDER

flex = FlexBox(width=80, height=20)
row = flex.new_row(ratio_y=1)
row.new_cell("Left Sidebar", ratio_x=1, min_width=20)
row.new_cell("Main Content", ratio_x=3)
print(flex.render())
```
