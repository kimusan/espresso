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


if __name__ == "__main__":
    unittest.main()
