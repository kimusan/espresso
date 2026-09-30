"""Unit tests for MarkdownViewer component and markdown rendering."""

from __future__ import annotations

import unittest

from espresso.beans.markdown import MarkdownViewer, render_markdown
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import ROUNDED_BORDER, Style, strip_ansi


class TestMarkdownViewer(unittest.TestCase):
    def test_render_elements(self) -> None:
        md = """# Main Header
## Sub Header
### Section

This is **bold** text and *italic* text with `inline_code`.

> Important note blockquote

- Item 1
- Item 2
  - Subitem A

1. First step
2. Second step

---

```python
def test():
    return 42
```
"""
        rendered = render_markdown(md, width=60)
        clean = strip_ansi(rendered)

        self.assertIn("# Main Header", clean)
        self.assertIn("## Sub Header", clean)
        self.assertIn("### Section", clean)
        self.assertIn("bold", clean)
        self.assertIn("italic", clean)
        self.assertIn("inline_code", clean)
        self.assertIn("▌ Important note blockquote", clean)
        self.assertIn("• Item 1", clean)
        self.assertIn("• Item 2", clean)
        self.assertIn("◦ Subitem A", clean)
        self.assertIn("1. First step", clean)
        self.assertIn("2. Second step", clean)
        self.assertIn("def test():", clean)
        self.assertIn("return 42", clean)

    def test_markdown_viewer_scrolling(self) -> None:
        long_md = "\n".join([f"Line {i} of content" for i in range(50)])
        viewer = MarkdownViewer(content=long_md, width=40, height=10)

        self.assertEqual(viewer.viewport.y_offset, 0)
        v0 = strip_ansi(viewer.view())
        self.assertIn("Line 0", v0)

        # Scroll down
        viewer, _ = viewer.update(KeyMsg("down"))
        self.assertEqual(viewer.viewport.y_offset, 1)

        viewer, _ = viewer.update(KeyMsg("j"))
        self.assertEqual(viewer.viewport.y_offset, 2)

        # Page down
        viewer, _ = viewer.update(KeyMsg("pgdown"))
        self.assertGreater(viewer.viewport.y_offset, 2)

        # Home key returns to top
        viewer, _ = viewer.update(KeyMsg("home"))
        self.assertEqual(viewer.viewport.y_offset, 0)

    def test_mouse_wheel_scroll(self) -> None:
        long_md = "\n".join([f"Para {i}" for i in range(30)])
        viewer = MarkdownViewer(content=long_md, width=40, height=8)

        # Wheel down
        viewer, _ = viewer.update(MouseMsg(x=5, y=5, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertEqual(viewer.viewport.y_offset, 1)

        # Wheel up
        viewer, _ = viewer.update(MouseMsg(x=5, y=5, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
        self.assertEqual(viewer.viewport.y_offset, 0)

    def test_set_size(self) -> None:
        viewer = MarkdownViewer(content="# Title\n\nBody", width=40, height=10)
        viewer.set_size(60, 15)
        self.assertEqual(viewer.width, 60)
        self.assertEqual(viewer.height, 15)
        self.assertEqual(viewer.viewport.width, 60)

    def test_markdown_viewer_empty_lines_scrolling_constant_height(self) -> None:
        """Verify MarkdownViewer row count and border box height remain constant during scroll."""
        md = "# Heading 1\n\n\nParagraph 1\n\n\nParagraph 2\n\n"
        viewer = MarkdownViewer(content=md, width=40, height=6, show_footer=False)
        box = Style().border(ROUNDED_BORDER).width(42)

        for offset in range(viewer.viewport.max_offset + 1):
            viewer.viewport.y_offset = offset
            v = viewer.view()
            lines = v.split("\n")
            self.assertEqual(len(lines), viewer.viewport.height, f"MarkdownViewer height changed at offset {offset}")
            b = box.render(v)
            b_lines = b.split("\n")
            self.assertEqual(len(b_lines), viewer.viewport.height + 2, f"Border height changed at offset {offset}")


if __name__ == "__main__":
    unittest.main()
