import unittest
from espresso.beans.virtual_list import (
    VirtualList,
    VirtualListChangeMsg,
    VirtualListSelectMsg,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestVirtualList(unittest.TestCase):
    def setUp(self):
        self.items = [f"Post #{i}: Test content" for i in range(50)]

    def test_initial_state(self):
        vl = VirtualList(items=self.items, width=40, height=10)
        self.assertEqual(vl.selected_index, 0)
        self.assertEqual(vl.selected_item, "Post #0: Test content")
        self.assertEqual(vl.item_offset, 0)
        view_lines = vl.view().splitlines()
        self.assertEqual(len(view_lines), 10)
        self.assertIn("Post #0", view_lines[0])

    def test_navigation_and_scrolling(self):
        vl = VirtualList(items=self.items, width=40, height=5)
        # Move down 4 times
        for _ in range(4):
            vl, _ = vl.update(KeyMsg(key="j"))
        self.assertEqual(vl.selected_index, 4)
        self.assertEqual(vl.item_offset, 0)

        # Move down to 5th item -> offset should scroll to keep it in view
        vl, cmd = vl.update(KeyMsg(key="down"))
        self.assertEqual(vl.selected_index, 5)
        self.assertEqual(vl.item_offset, 1)
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), VirtualListChangeMsg)

        # Jump to bottom G
        vl, _ = vl.update(KeyMsg(key="G"))
        self.assertEqual(vl.selected_index, 49)
        self.assertEqual(vl.item_offset, 45)

        # Jump to top g
        vl, _ = vl.update(KeyMsg(key="g"))
        self.assertEqual(vl.selected_index, 0)
        self.assertEqual(vl.item_offset, 0)

    def test_selection_confirmation(self):
        vl = VirtualList(items=self.items, selected_index=3)
        vl, cmd = vl.update(KeyMsg(key="enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, VirtualListSelectMsg)
        self.assertEqual(msg.index, 3)
        self.assertEqual(msg.item, "Post #3: Test content")

    def test_mouse_scroll(self):
        vl = VirtualList(items=self.items, selected_index=5)
        # Scroll up
        vl, _ = vl.update(MouseMsg(x=0, y=0, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
        self.assertEqual(vl.selected_index, 4)

        # Scroll down
        vl, _ = vl.update(MouseMsg(x=0, y=0, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
        self.assertEqual(vl.selected_index, 5)

    def test_set_items_with_anchor(self):
        posts = [{"id": f"p_{i}", "text": f"Toot {i}"} for i in range(10)]
        vl = VirtualList(items=posts, selected_index=3)
        self.assertEqual(vl.selected_item["id"], "p_3")

        # Prepend 2 new posts
        new_posts = [{"id": "p_new_1", "text": "New"}, {"id": "p_new_2", "text": "New 2"}] + posts
        # Set items with anchor preserving p_3
        vl.set_items(new_posts, keep_anchor=True, anchor_id_fn=lambda p: p["id"])
        # Should now be index 5, still pointing to p_3
        self.assertEqual(vl.selected_index, 5)
        self.assertEqual(vl.selected_item["id"], "p_3")

    def test_multiline_items_scrolling(self):
        # 10 items, each 6 lines tall, in a 15-line viewport
        items = list(range(10))
        def render_block(it, sel, w):
            return "\n".join([f"Item {it} Line {l}" for l in range(6)])

        vl = VirtualList(items=items, render_item=render_block, width=40, height=15)
        self.assertEqual(vl.item_offset, 0)
        self.assertEqual(vl.selected_index, 0)

        # Move down to item 1 (total lines = 6 + 6 = 12 <= 15) -> still fits
        vl, _ = vl.update(KeyMsg(key="j"))
        self.assertEqual(vl.selected_index, 1)
        self.assertEqual(vl.item_offset, 0)

        # Move down to item 2 (total lines = 6*3 = 18 > 15) -> must scroll down to offset 1
        vl, _ = vl.update(KeyMsg(key="j"))
        self.assertEqual(vl.selected_index, 2)
        self.assertEqual(vl.item_offset, 1)

        # Move down to item 3 -> must scroll down to offset 2
        vl, _ = vl.update(KeyMsg(key="j"))
        self.assertEqual(vl.selected_index, 3)
        self.assertEqual(vl.item_offset, 2)

        # Move back up to item 2 (above item 3, but >= offset 2) -> offset stays 2
        vl, _ = vl.update(KeyMsg(key="k"))
        self.assertEqual(vl.selected_index, 2)
        self.assertEqual(vl.item_offset, 2)

        # Move back up to item 1 (< offset 2) -> must scroll up to offset 1
        vl, _ = vl.update(KeyMsg(key="k"))
        self.assertEqual(vl.selected_index, 1)
        self.assertEqual(vl.item_offset, 1)

        # Jump to end G (item 9)
        vl, _ = vl.update(KeyMsg(key="G"))
        self.assertEqual(vl.selected_index, 9)
        # In a 15-line viewport, 2 items of height 6 fit (12 lines), so offset must be 8
        self.assertEqual(vl.item_offset, 8)

    def test_multiline_mouse_hit_testing(self):
        # Items of 5 lines each
        items = ["A", "B", "C"]
        def render_block(it, sel, w):
            return "\n".join([f"{it}_{l}" for l in range(5)])

        vl = VirtualList(items=items, render_item=render_block, width=30, height=15)
        # Click at y=7 (which falls in item B: y=0..4 is A, y=5..9 is B)
        vl, _ = vl.update(MouseMsg(x=5, y=7, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(vl.selected_index, 1)
        self.assertEqual(vl.selected_item, "B")

    def test_cursor_and_scroll_offset_properties(self):
        vl = VirtualList(items=self.items, selected_index=4)
        self.assertEqual(vl.cursor, 4)
        self.assertEqual(vl.scroll_offset, 0)

        # Set cursor property
        vl.cursor = 10
        self.assertEqual(vl.cursor, 10)
        self.assertEqual(vl.selected_index, 10)

        # Set scroll_offset property
        vl.scroll_offset = 3
        self.assertEqual(vl.scroll_offset, 3)
        self.assertEqual(vl.item_offset, 3)


if __name__ == "__main__":
    unittest.main()
