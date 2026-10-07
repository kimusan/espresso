"""Unit tests for Accordion bean component."""

from __future__ import annotations

import unittest

from espresso.beans.accordion import (
    Accordion,
    AccordionItem,
    AccordionSelectMsg,
    AccordionToggleMsg,
)
from espresso.beans.scroll_view import ScrollView
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema.width import strip_ansi


class TestAccordion(unittest.TestCase):
    def setUp(self) -> None:
        self.item1 = AccordionItem(
            id="sec1",
            title="Overview",
            content="This is section 1 overview text.",
            expanded=True,
            badge="New",
        )
        self.item2 = AccordionItem(
            id="sec2",
            title="Settings",
            content="Settings configuration details.",
            expanded=False,
        )
        self.item3 = AccordionItem(
            id="sec3",
            title="Advanced",
            content="Advanced parameters and options.",
            expanded=False,
            disabled=True,
        )

    def test_initial_state_and_view(self) -> None:
        acc = Accordion(items=[self.item1, self.item2, self.item3], width=50)
        self.assertEqual(acc.active_index, 0)
        self.assertFalse(acc.focus_child)
        self.assertEqual(len(acc.items), 3)

        rendered = acc.view()
        clean = strip_ansi(rendered)

        # Section 1 is expanded (▼), has badge [New], and displays content
        self.assertIn("▼", clean)
        self.assertIn("Overview", clean)
        self.assertIn("[New]", clean)
        self.assertIn("This is section 1 overview text.", clean)

        # Section 2 is collapsed (▶) and its content is NOT visible
        self.assertIn("▶", clean)
        self.assertIn("Settings", clean)
        self.assertNotIn("Settings configuration details.", clean)

    def test_header_navigation(self) -> None:
        acc = Accordion(items=[self.item1, self.item2, self.item3], width=50)

        # Move down from item 0 -> item 1
        acc, cmd = acc.update(KeyMsg(key="j"))
        self.assertEqual(acc.active_index, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, AccordionSelectMsg)
        self.assertEqual(msg.item_id, "sec2")

        # Move down from item 1 -> skips item 2 (disabled) and wraps to item 0
        acc, _ = acc.update(KeyMsg(key="down"))
        self.assertEqual(acc.active_index, 0)

        # Move up from item 0 -> skips disabled item 2 to item 1
        acc, _ = acc.update(KeyMsg(key="k"))
        self.assertEqual(acc.active_index, 1)

    def test_single_expand_mode(self) -> None:
        # Default allow_multiple=False
        acc = Accordion(items=[self.item1, self.item2], width=50, allow_multiple=False)
        self.assertTrue(self.item1.expanded)
        self.assertFalse(self.item2.expanded)

        # Move to item 2 and toggle (expand)
        acc, _ = acc.update(KeyMsg(key="j"))
        acc, cmd = acc.update(KeyMsg(key="enter"))

        self.assertFalse(self.item1.expanded)
        self.assertTrue(self.item2.expanded)
        self.assertIsNotNone(cmd)

    def test_multi_expand_mode(self) -> None:
        acc = Accordion(
            items=[
                AccordionItem(id="a", title="A", content="Content A", expanded=False),
                AccordionItem(id="b", title="B", content="Content B", expanded=False),
            ],
            width=50,
            allow_multiple=True,
        )

        # Expand A
        acc.expand("a")
        # Expand B
        acc.expand("b")
        self.assertTrue(acc.items[0].expanded)
        self.assertTrue(acc.items[1].expanded)

        clean = strip_ansi(acc.view())
        self.assertIn("Content A", clean)
        self.assertIn("Content B", clean)

        # Collapse all
        acc.collapse_all()
        self.assertFalse(acc.items[0].expanded)
        self.assertFalse(acc.items[1].expanded)

        # Expand all
        acc.expand_all()
        self.assertTrue(acc.items[0].expanded)
        self.assertTrue(acc.items[1].expanded)

    def test_child_bean_focus_and_event_forwarding(self) -> None:
        ti = TextInput(placeholder="Username...")
        item_input = AccordionItem(id="user", title="User Account", content=ti, expanded=True)
        acc = Accordion(items=[item_input], width=50)

        self.assertFalse(acc.focus_child)
        self.assertFalse(ti.focused)

        # Press Tab to focus child bean
        acc, _ = acc.update(KeyMsg(key="tab"))
        self.assertTrue(acc.focus_child)
        self.assertTrue(ti.focused)

        # Type characters into TextInput inside accordion
        acc, _ = acc.update(KeyMsg(key="a"))
        acc, _ = acc.update(KeyMsg(key="l"))
        acc, _ = acc.update(KeyMsg(key="i"))
        acc, _ = acc.update(KeyMsg(key="c"))
        acc, _ = acc.update(KeyMsg(key="e"))

        self.assertEqual(ti.value, "alice")
        clean = strip_ansi(acc.view())
        self.assertIn("alice", clean)

        # Press Esc to return to header navigation
        acc, _ = acc.update(KeyMsg(key="esc"))
        self.assertFalse(acc.focus_child)
        self.assertFalse(ti.focused)

    def test_mouse_header_clicks(self) -> None:
        acc = Accordion(items=[self.item1, self.item2], width=50, allow_multiple=False)
        self.assertTrue(self.item1.expanded)
        self.assertFalse(self.item2.expanded)

        # Header 0 is at y=0.
        # Header 1 is after item 0's content and separator.
        # Item 0 has: 1 header row + 1 content row = 2 rows, plus 1 separator = 3.
        # Header 1 starts at y=3.
        acc, cmd = acc.update(
            MouseMsg(x=10, y=3, button=MouseButton.LEFT, action=MouseAction.PRESS)
        )
        self.assertEqual(acc.active_index, 1)
        self.assertTrue(self.item2.expanded)
        self.assertFalse(self.item1.expanded)

    def test_add_and_remove_items(self) -> None:
        acc = Accordion(items=[self.item1], width=50)
        self.assertEqual(len(acc.items), 1)

        acc.add_item(AccordionItem(id="sec_new", title="New Section", content="More info"))
        self.assertEqual(len(acc.items), 2)
        self.assertIsNotNone(acc.get_item("sec_new"))

        acc.remove_item("sec1")
        self.assertEqual(len(acc.items), 1)
        self.assertIsNone(acc.get_item("sec1"))
        self.assertEqual(acc.items[0].id, "sec_new")

    def test_accordion_nested_with_scroll_view(self) -> None:
        # A ScrollView wrapping long text inside an AccordionItem
        long_text = "\n".join([f"Log line {i}" for i in range(20)])
        sv = ScrollView(child=long_text, width=40, height=5)
        item_scroll = AccordionItem(id="logs", title="System Logs", content=sv, expanded=True)

        acc = Accordion(items=[item_scroll], width=45)
        view_clean = strip_ansi(acc.view())

        # ScrollView renders 5 lines
        self.assertIn("Log line 0", view_clean)
        self.assertIn("Log line 4", view_clean)
        self.assertNotIn("Log line 10", view_clean)

        # Focus child and scroll the ScrollView down
        acc, _ = acc.update(KeyMsg(key="tab"))
        self.assertTrue(acc.focus_child)

        acc, _ = acc.update(KeyMsg(key="pagedown"))
        self.assertGreater(sv.y_offset, 0)


if __name__ == "__main__":
    unittest.main()
