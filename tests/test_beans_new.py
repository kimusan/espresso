"""Comprehensive unit tests for new Beans components:
Paginator, Dialog, List, FilePicker, Prompts, Toast, Tabs, and Tree.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from espresso.beans.dialog import Dialog, DialogResultMsg
from espresso.beans.filepicker import FilePicker, FileSelectMsg, format_file_size
from espresso.beans.list import List, ListItem, ListSelectMsg
from espresso.beans.paginator import Paginator, PaginatorType
from espresso.beans.prompt import (
    ConfirmPrompt,
    ConfirmSubmitMsg,
    MultiSelectPrompt,
    MultiSelectSubmitMsg,
    SelectPrompt,
    SelectSubmitMsg,
)
from espresso.beans.tabs import TabChangeMsg, TabStyle, Tabs
from espresso.beans.toast import ToastDismissMsg, ToastLevel, ToastManager
from espresso.beans.tree import Tree, TreeNode, TreeNodeSelectMsg
from espresso.core.keys import KeyMsg
from espresso.crema import strip_ansi


class TestPaginator(unittest.TestCase):
    def test_page_calculations(self) -> None:
        p = Paginator(page=0, per_page=10, total_items=25)
        self.assertEqual(p.total_pages, 3)
        self.assertFalse(p.on_last_page)
        self.assertTrue(p.on_first_page)

        # Slice bounds (accessible as method or property)
        self.assertEqual(p.slice_bounds(), (0, 10))
        self.assertEqual(p.slice_bounds, (0, 10))
        items = list(range(25))
        self.assertEqual(p.slice_items(items), list(range(10)))

        # Next page
        p.next_page()
        self.assertEqual(p.page, 1)
        self.assertEqual(p.slice_bounds(), (10, 20))
        self.assertEqual(p.slice_items(items), list(range(10, 20)))

        # Last page
        p.next_page()
        self.assertEqual(p.page, 2)
        self.assertTrue(p.on_last_page)
        self.assertEqual(p.slice_bounds(), (20, 25))
        self.assertEqual(p.slice_items(items), list(range(20, 25)))

        # Won't advance past last page
        p.next_page()
        self.assertEqual(p.page, 2)

    def test_key_navigation(self) -> None:
        p = Paginator(page=0, per_page=5, total_items=20)
        p, _ = p.update(KeyMsg("right"))
        self.assertEqual(p.page, 1)
        p, _ = p.update(KeyMsg("l"))
        self.assertEqual(p.page, 2)
        p, _ = p.update(KeyMsg("left"))
        self.assertEqual(p.page, 1)
        p, _ = p.update(KeyMsg("h"))
        self.assertEqual(p.page, 0)

    def test_rendering_modes(self) -> None:
        p = Paginator(page=0, per_page=5, total_items=15)
        # DOTS mode
        p.paginator_type = PaginatorType.DOTS
        dots_view = strip_ansi(p.view())
        self.assertIn("•", dots_view)
        self.assertIn("◦", dots_view)

        # NUMERIC mode
        p.paginator_type = PaginatorType.NUMERIC
        self.assertIn("1/3", strip_ansi(p.view()))

        # COMPACT mode
        p.paginator_type = PaginatorType.COMPACT
        self.assertIn("1 of 3", strip_ansi(p.view()))


class TestDialog(unittest.TestCase):
    def test_button_navigation(self) -> None:
        d = Dialog(title="Delete File?", message="Are you sure?", buttons=("Yes", "No", "Cancel"))
        self.assertEqual(d.selected_button, 0)

        d, _ = d.update(KeyMsg("right"))
        self.assertEqual(d.selected_button, 1)

        d, _ = d.update(KeyMsg("tab"))
        self.assertEqual(d.selected_button, 2)

        # Wrap around
        d, _ = d.update(KeyMsg("tab"))
        self.assertEqual(d.selected_button, 0)

        d, _ = d.update(KeyMsg("left"))
        self.assertEqual(d.selected_button, 2)

    def test_dialog_submission(self) -> None:
        d = Dialog(title="Save?", message="Save changes?", buttons=("Save", "Discard"))
        d, _ = d.update(KeyMsg("right"))  # select Discard
        d, cmd = d.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, DialogResultMsg)
        self.assertEqual(msg.action, "Discard")
        self.assertEqual(msg.button_index, 1)

    def test_dialog_cancel(self) -> None:
        d = Dialog(title="Save?", message="Save changes?")
        d, cmd = d.update(KeyMsg("esc"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, DialogResultMsg)
        self.assertEqual(msg.action, "Cancel")
        self.assertEqual(msg.button_index, 1)

    def test_dialog_view(self) -> None:
        d = Dialog(title="Warning", message="Low Disk Space")
        rendered = strip_ansi(d.view())
        self.assertIn("Warning", rendered)
        self.assertIn("Low Disk Space", rendered)
        self.assertIn("Confirm", rendered)


class TestList(unittest.TestCase):
    def test_navigation_and_selection(self) -> None:
        items = ["Apple", "Banana", "Cherry", "Date", "Elderberry"]
        l = List(items=items, height=6)
        self.assertEqual(l.cursor, 0)

        # Move down
        l, _ = l.update(KeyMsg("down"))
        self.assertEqual(l.cursor, 1)

        l, _ = l.update(KeyMsg("j"))
        self.assertEqual(l.cursor, 2)

        # Move up
        l, _ = l.update(KeyMsg("up"))
        self.assertEqual(l.cursor, 1)

        # Select
        l, cmd = l.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, ListSelectMsg)
        self.assertEqual(msg.item.title, "Banana")
        self.assertEqual(msg.index, 1)

    def test_filtering(self) -> None:
        items = [
            ListItem("Latte", "Steamed milk and espresso"),
            ListItem("Mocha", "Chocolate and espresso"),
            ListItem("Americano", "Espresso and water"),
        ]
        l = List(items=items, height=8)

        # Enter filter mode with '/'
        l, _ = l.update(KeyMsg("/"))
        self.assertTrue(l.filtering)

        # Type 'moc'
        for char in "moc":
            l, _ = l.update(KeyMsg(char))

        self.assertEqual(len(l.filtered_items), 1)
        self.assertEqual(l.filtered_items[0].title, "Mocha")

        # Esc exits filter mode
        l, _ = l.update(KeyMsg("esc"))
        self.assertFalse(l.filtering)
        self.assertEqual(l.filter_input.value, "")
        self.assertEqual(len(l.filtered_items), 3)

    def test_custom_items(self) -> None:
        item = ListItem("Settings", "App config", value={"debug": True})
        l = List(items=[item])
        self.assertEqual(l.selected_item.value, {"debug": True})


class TestFilePicker(unittest.TestCase):
    def test_directory_browsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create subfolder and files
            sub = tmppath / "subfolder"
            sub.mkdir()
            file1 = tmppath / "notes.txt"
            file1.write_text("Hello world")
            file2 = tmppath / "script.py"
            file2.write_text("print('test')")

            fp = FilePicker(directory=tmppath)
            self.assertEqual(fp.current_dir.resolve(), tmppath.resolve())

            # Find subfolder and file entries
            names = [e.name for e in fp.entries]
            self.assertIn("subfolder", names)
            self.assertIn("notes.txt", names)
            self.assertIn("script.py", names)

            # Select file
            fp.cursor = names.index("notes.txt")
            fp, cmd = fp.update(KeyMsg("enter"))
            self.assertIsNotNone(cmd)
            msg = cmd()
            self.assertIsInstance(msg, FileSelectMsg)
            self.assertEqual(msg.entry.name, "notes.txt")
            self.assertEqual(msg.path.resolve(), file1.resolve())

    def test_allowed_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "a.py").write_text("a")
            (tmppath / "b.txt").write_text("b")

            fp = FilePicker(directory=tmppath, allowed_extensions=(".py",))
            names = [e.name for e in fp.entries]
            self.assertIn("a.py", names)
            self.assertNotIn("b.txt", names)

    def test_format_file_size(self) -> None:
        self.assertEqual(format_file_size(500), "500 B")
        self.assertIn("KB", format_file_size(2048))
        self.assertIn("MB", format_file_size(1024 * 1024 * 5))


class TestPrompts(unittest.TestCase):
    def test_select_prompt(self) -> None:
        sp = SelectPrompt("Choose flavor:", ["Vanilla", "Chocolate", "Strawberry"])
        self.assertEqual(sp.cursor, 0)
        sp, _ = sp.update(KeyMsg("down"))
        self.assertEqual(sp.cursor, 1)

        sp, cmd = sp.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SelectSubmitMsg)
        self.assertEqual(msg.selected, "Chocolate")
        self.assertEqual(msg.index, 1)

    def test_multiselect_prompt(self) -> None:
        msp = MultiSelectPrompt("Pick toppings:", ["Sprinkles", "Fudge", "Caramel"])
        # Toggle first with space
        msp, _ = msp.update(KeyMsg("space"))
        self.assertIn(0, msp.selected_indices)

        # Move down and toggle third
        msp, _ = msp.update(KeyMsg("down"))
        msp, _ = msp.update(KeyMsg("down"))
        msp, _ = msp.update(KeyMsg("space"))
        self.assertIn(2, msp.selected_indices)

        msp, cmd = msp.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, MultiSelectSubmitMsg)
        self.assertEqual(msg.selected, ["Sprinkles", "Caramel"])
        self.assertEqual(msg.indices, [0, 2])

    def test_confirm_prompt(self) -> None:
        cp = ConfirmPrompt("Proceed?", default=False)
        self.assertFalse(cp.value)

        # Type 'y'
        cp, cmd = cp.update(KeyMsg("y"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, ConfirmSubmitMsg)
        self.assertTrue(msg.confirmed)

        # Type 'n'
        cp2 = ConfirmPrompt("Proceed?", default=True)
        cp2, cmd2 = cp2.update(KeyMsg("n"))
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertIsInstance(msg2, ConfirmSubmitMsg)
        self.assertFalse(msg2.confirmed)


class TestToastManager(unittest.TestCase):
    def test_toast_lifecycle(self) -> None:
        tm = ToastManager()
        self.assertFalse(tm.has_toasts)

        item, cmd = tm.add("Operation succeeded!", ToastLevel.SUCCESS, duration=5.0)
        self.assertTrue(tm.has_toasts)
        self.assertEqual(len(tm.toasts), 1)
        self.assertEqual(item.level, ToastLevel.SUCCESS)

        # Dismiss toast
        tm, _ = tm.update(ToastDismissMsg(toast_id=item.id))
        self.assertFalse(tm.has_toasts)
        self.assertEqual(len(tm.toasts), 0)

    def test_toast_rendering(self) -> None:
        tm = ToastManager()
        tm.add("Notice", ToastLevel.INFO)
        view = strip_ansi(tm.view())
        self.assertIn("Notice", view)
        self.assertIn("ℹ", view)


class TestTabs(unittest.TestCase):
    def test_tab_switching(self) -> None:
        tabs = Tabs(["Overview", "Logs", "Settings"])
        self.assertEqual(tabs.active_tab, 0)

        # Right arrow
        tabs, cmd = tabs.update(KeyMsg("right"))
        self.assertEqual(tabs.active_tab, 1)
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, TabChangeMsg)
        self.assertEqual(msg.title, "Logs")

        # Number key '3'
        tabs, cmd2 = tabs.update(KeyMsg("3"))
        self.assertEqual(tabs.active_tab, 2)
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertEqual(msg2.title, "Settings")

    def test_tab_styles(self) -> None:
        tabs = Tabs(["Tab A", "Tab B"], tab_style=TabStyle.BRACKET)
        view = strip_ansi(tabs.view())
        self.assertIn("[", view)
        self.assertIn("Tab A", view)


class TestTree(unittest.TestCase):
    def test_tree_expansion_and_selection(self) -> None:
        tree = Tree(
            nodes=[
                TreeNode(
                    label="Root",
                    children=[
                        TreeNode(label="Child 1"),
                        TreeNode(
                            label="Folder",
                            children=[
                                TreeNode(label="Grandchild"),
                            ],
                        ),
                    ],
                )
            ]
        )

        # Initially root is collapsed
        self.assertEqual(len(tree.flattened_nodes), 1)

        # Expand root with space
        tree, _ = tree.update(KeyMsg("space"))
        self.assertTrue(tree.nodes[0].expanded)
        self.assertEqual(len(tree.flattened_nodes), 3)  # Root, Child 1, Folder

        # Move down to Folder and expand it
        tree, _ = tree.update(KeyMsg("down"))  # to Child 1
        tree, _ = tree.update(KeyMsg("down"))  # to Folder
        tree, _ = tree.update(KeyMsg("right"))  # expand
        self.assertEqual(len(tree.flattened_nodes), 4)  # Root, Child 1, Folder, Grandchild

        # Move to Grandchild and select
        tree, _ = tree.update(KeyMsg("down"))
        tree, cmd = tree.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, TreeNodeSelectMsg)
        self.assertEqual(msg.node.label, "Grandchild")

    def test_tree_rendering(self) -> None:
        tree = Tree(
            nodes=[
                TreeNode("Parent", children=[TreeNode("Child")], expanded=True)
            ]
        )
        view = strip_ansi(tree.view())
        self.assertIn("Parent", view)
        self.assertIn("Child", view)
        self.assertIn("└──", view)


if __name__ == "__main__":
    unittest.main()
