"""Unit tests for GitTree bean."""

from __future__ import annotations

import unittest

from espresso.beans.git_tree import GitFileNode, GitFileStatus, GitTree
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestGitTree(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = {
            "src/app.py": GitFileStatus.MODIFIED,
            "src/utils/helpers.py": GitFileStatus.ADDED,
            "README.md": GitFileStatus.CLEAN,
            "tests/test_app.py": GitFileStatus.UNTRACKED,
        }
        self.tree = GitTree.from_paths(self.paths, branch="feature/beans")

    def test_from_paths_hierarchy(self) -> None:
        root = self.tree.root
        self.assertEqual(root.name, "workspace")
        self.assertTrue(root.is_dir)

        # Children of workspace should include src, tests, README.md
        child_names = [c.name for c in root.children]
        self.assertIn("src", child_names)
        self.assertIn("tests", child_names)
        self.assertIn("README.md", child_names)

    def test_flatten_visible(self) -> None:
        visible = self.tree.flatten_visible()
        names = [node.name for node, _, _ in visible]
        self.assertIn("workspace", names)
        self.assertIn("src", names)
        self.assertIn("app.py", names)
        self.assertIn("helpers.py", names)

    def test_fold_and_expand_keyboard(self) -> None:
        # Move cursor to 'src' (row 1, since workspace is row 0)
        self.tree.update(KeyMsg("down"))
        node, path = self.tree.get_selected_node()
        self.assertEqual(node.name, "src")
        self.assertTrue(node.is_expanded)

        # Press space to toggle collapse
        self.tree.update(KeyMsg("space"))
        self.assertFalse(node.is_expanded)

        # 'app.py' should no longer be in flatten_visible
        names = [n.name for n, _, _ in self.tree.flatten_visible()]
        self.assertNotIn("app.py", names)

        # Press right to expand
        self.tree.update(KeyMsg("right"))
        self.assertTrue(node.is_expanded)

        names2 = [n.name for n, _, _ in self.tree.flatten_visible()]
        self.assertIn("app.py", names2)

    def test_mouse_interactions(self) -> None:
        self.tree.set_offset(0, 0)
        # Header is 2 rows (y=0, 1), so row 0 in tree is at y=2, row 1 at y=3
        click_msg = MouseMsg(x=5, y=3, button=MouseButton.LEFT, action=MouseAction.PRESS)
        self.tree.update(click_msg)
        self.assertEqual(self.tree.cursor, 1)

        # Double click to toggle folder
        dbl_msg = MouseMsg(x=5, y=3, button=MouseButton.LEFT, action=MouseAction.DOUBLE_CLICK)
        node, _ = self.tree.get_selected_node()
        self.assertTrue(node.is_expanded)
        self.tree.update(dbl_msg)
        self.assertFalse(node.is_expanded)

    def test_view_rendering(self) -> None:
        view_str = self.tree.view()
        self.assertIn("feature/beans", view_str)
        self.assertIn("src", view_str)
        self.assertIn("[M]", view_str)
