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
    .width(40)
    .align(Align.CENTER)
)
```

## Layout Primitives

- `join_horizontal(align, *blocks)`: Combine blocks horizontally side-by-side.
- `join_vertical(align, *blocks)`: Stack blocks vertically.
- `place(w, h, h_align, v_align, content)`: Center or position content inside a bounding box.
