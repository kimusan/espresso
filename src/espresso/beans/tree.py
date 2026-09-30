"""Hierarchical collapsible tree view component."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style


@dataclass
class TreeNode:
    """A node in a hierarchical Tree."""

    label: str
    value: Any = None
    children: list[TreeNode] = field(default_factory=list)
    expanded: bool = False

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0


@dataclass(frozen=True)
class TreeNodeSelectMsg(Msg):
    """Message emitted when a TreeNode is selected with Enter."""

    node: TreeNode


class Tree(Model):
    """A collapsible, navigable hierarchical tree view component."""

    def __init__(
        self,
        nodes: Sequence[TreeNode],
    ) -> None:
        self.nodes = list(nodes)
        self.cursor = 0

        # Styles
        self.cursor_style = Style().bold(True).foreground("#00E676")
        self.active_node_style = Style().bold(True).foreground("#00E676")
        self.dir_style = Style().bold(True).foreground("#00E5FF")
        self.leaf_style = Style().foreground("#D0D0D0")
        self.dim_style = Style().faint(True)

    def _flatten_visible(self) -> list[tuple[TreeNode, int, str, TreeNode | None]]:
        """Return a flat list of (node, depth, prefix, parent) for all currently visible nodes."""
        result: list[tuple[TreeNode, int, str, TreeNode | None]] = []

        def _traverse(node_list: list[TreeNode], depth: int, prefix: str, parent: TreeNode | None) -> None:
            count = len(node_list)
            for idx, node in enumerate(node_list):
                is_last = (idx == count - 1)
                branch = "└── " if is_last else "├── "
                node_prefix = f"{prefix}{branch}"

                result.append((node, depth, node_prefix, parent))

                if node.expanded and node.children:
                    next_prefix = f"{prefix}{'    ' if is_last else '│   '}"
                    _traverse(node.children, depth + 1, next_prefix, node)

        _traverse(self.nodes, 0, "", None)
        return result

    @property
    def visible_nodes(self) -> list[TreeNode]:
        """Return a list of all currently visible TreeNodes."""
        return [node for node, _, _, _ in self._flatten_visible()]

    @property
    def flattened_nodes(self) -> list[TreeNode]:
        """Alias for visible_nodes."""
        return self.visible_nodes

    @property
    def selected_node(self) -> TreeNode | None:
        visible = self._flatten_visible()
        if 0 <= self.cursor < len(visible):
            return visible[self.cursor][0]
        return None

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Tree, Cmd | None]:
        """Handle tree navigation, expand/collapse, and node selection."""
        visible = self._flatten_visible()

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    if self.cursor < len(visible) - 1:
                        self.cursor += 1
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                    return self, None
                case "right" | "l" | " " | "space":
                    if 0 <= self.cursor < len(visible):
                        node, _, _, _ = visible[self.cursor]
                        if not node.is_leaf:
                            node.expanded = not node.expanded
                    return self, None
                case "left" | "h":
                    if 0 <= self.cursor < len(visible):
                        node, _, _, parent = visible[self.cursor]
                        if not node.is_leaf and node.expanded:
                            node.expanded = False
                        elif parent is not None:
                            # Jump cursor to parent node
                            for p_idx, (vis_node, _, _, _) in enumerate(visible):
                                if vis_node is parent:
                                    self.cursor = p_idx
                                    break
                    return self, None
                case "enter":
                    selected = self.selected_node
                    if selected is not None:
                        def _emit() -> Msg:
                            return TreeNodeSelectMsg(node=selected)
                        return self, _emit

        return self, None

    def view(self) -> str:
        """Render the tree hierarchy."""
        visible = self._flatten_visible()
        if not visible:
            return self.dim_style.render("  (Empty tree)")

        lines: list[str] = []
        for idx, (node, depth, prefix, _) in enumerate(visible):
            is_active = (idx == self.cursor)

            cursor_mark = "▶ " if is_active else "  "

            if node.is_leaf:
                exp_icon = "  "
                label_styled = self.leaf_style.render(node.label)
            else:
                exp_icon = "▼ " if node.expanded else "▶ "
                label_styled = self.dir_style.render(node.label)

            if is_active:
                cursor_styled = self.cursor_style.render(cursor_mark)
                label_styled = self.active_node_style.render(node.label)
            else:
                cursor_styled = cursor_mark

            tree_line = f"{cursor_styled}{self.dim_style.render(prefix)}{exp_icon}{label_styled}"
            lines.append(tree_line)

        return "\n".join(lines)
