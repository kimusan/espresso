"""Git-aware file tree bean with status badges, branch header, and directory folding.

Inspired by Neovim Neo-tree, Lazygit, and VS Code Explorer with Git decorations.
Displays collapsible file trees with status indicators ([M]odified, [A]dded, [D]eleted,
[?]untracked, [U]nmerged), branch status badges, and full mouse + keyboard navigation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, strip_ansi, truncate_ansi


class GitFileStatus(str, Enum):
    """Git working tree file status."""

    CLEAN = ""
    MODIFIED = "M"
    ADDED = "A"
    DELETED = "D"
    UNTRACKED = "?"
    UNMERGED = "U"
    RENAMED = "R"


@dataclass
class GitFileNode:
    """A node in the git file tree."""

    name: str
    is_dir: bool = False
    status: GitFileStatus | str = GitFileStatus.CLEAN
    children: list[GitFileNode] = field(default_factory=list)
    is_expanded: bool = True
    staged: bool = False
    data: Any = None
    path: str = ""

    def add_child(self, child: GitFileNode) -> GitFileNode:
        self.children.append(child)
        return child


@dataclass(frozen=True)
class GitTreeSelectMsg(Msg):
    """Emitted when a node is selected in the GitTree."""

    node: GitFileNode
    path: str


@dataclass(frozen=True)
class GitTreeToggleMsg(Msg):
    """Emitted when a directory is expanded or collapsed."""

    node: GitFileNode
    expanded: bool


class GitTree(Model):
    """Interactive multi-column Git-decorated file tree."""

    def __init__(
        self,
        root: GitFileNode,
        branch: str = "main",
        width: int = 32,
        height: int = 16,
        show_branch_header: bool = True,
        border_color: str = "#7D56F4",
    ) -> None:
        self.root = root
        self.branch = branch
        self.width = max(20, width)
        self.height = max(6, height)
        self.show_branch_header = show_branch_header
        self.border_color = border_color

        self.cursor: int = 0
        self.scroll_offset: int = 0

        self.offset_x: int = 0
        self.offset_y: int = 0

    @classmethod
    def from_paths(
        cls,
        paths: dict[str, str | GitFileStatus],
        branch: str = "main",
        root_name: str = "workspace",
        width: int = 32,
        height: int = 16,
    ) -> GitTree:
        """Construct a GitTree hierarchically from a dict of {relative_path: status}."""
        root = GitFileNode(name=root_name, is_dir=True, is_expanded=True, path="")

        for path_str, status_val in sorted(paths.items()):
            parts = path_str.strip("/").split("/")
            curr = root
            curr_path = ""
            for i, part in enumerate(parts):
                is_last = i == len(parts) - 1
                curr_path = f"{curr_path}/{part}" if curr_path else part

                found = None
                for child in curr.children:
                    if child.name == part:
                        found = child
                        break

                if found is None:
                    status = status_val if is_last else GitFileStatus.CLEAN
                    node = GitFileNode(
                        name=part,
                        is_dir=not is_last,
                        status=status,
                        path=curr_path,
                        is_expanded=True,
                    )
                    curr.children.append(node)
                    # Sort directories first, then files
                    curr.children.sort(key=lambda n: (not n.is_dir, n.name.lower()))
                    curr = node
                else:
                    curr = found

        return cls(root=root, branch=branch, width=width, height=height)

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset for mouse hit testing."""
        self.offset_x = x
        self.offset_y = y

    def flatten_visible(self) -> list[tuple[GitFileNode, int, str]]:
        """Flatten visible tree into a list of (node, depth, path)."""
        result: list[tuple[GitFileNode, int, str]] = []

        def _traverse(node: GitFileNode, depth: int, parent_path: str) -> None:
            current_path = f"{parent_path}/{node.name}" if parent_path else node.name
            if depth >= 0:  # Include root or children
                result.append((node, depth, current_path))
            if node.is_dir and node.is_expanded:
                for child in node.children:
                    _traverse(child, depth + 1, current_path)

        _traverse(self.root, 0, "")
        return result

    def get_selected_node(self) -> tuple[GitFileNode, str] | None:
        """Return currently selected (node, path)."""
        visible = self.flatten_visible()
        if 0 <= self.cursor < len(visible):
            node, _, path = visible[self.cursor]
            return node, path
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd]:
        """Handle keyboard navigation and mouse interactions."""
        visible = self.flatten_visible()
        max_visible = self.height - (4 if self.show_branch_header else 2)

        if isinstance(msg, KeyMsg):
            key = str(msg.key).lower()

            if key in ("up", "k"):
                if visible:
                    self.cursor = max(0, self.cursor - 1)
                    self._adjust_scroll(max_visible)
                return self, None

            elif key in ("down", "j"):
                if visible:
                    self.cursor = min(len(visible) - 1, self.cursor + 1)
                    self._adjust_scroll(max_visible)
                return self, None

            elif key in ("left", "h"):
                if visible and 0 <= self.cursor < len(visible):
                    node, _, _ = visible[self.cursor]
                    if node.is_dir and node.is_expanded:
                        node.is_expanded = False
                        return self, lambda: GitTreeToggleMsg(node=node, expanded=False)
                return self, None

            elif key in ("right", "l"):
                if visible and 0 <= self.cursor < len(visible):
                    node, _, _ = visible[self.cursor]
                    if node.is_dir and not node.is_expanded:
                        node.is_expanded = True
                        return self, lambda: GitTreeToggleMsg(node=node, expanded=True)
                return self, None

            elif key == "space":
                if visible and 0 <= self.cursor < len(visible):
                    node, _, _ = visible[self.cursor]
                    if node.is_dir:
                        node.is_expanded = not node.is_expanded
                        return self, lambda: GitTreeToggleMsg(node=node, expanded=node.is_expanded)
                return self, None

            elif key == "enter":
                if visible and 0 <= self.cursor < len(visible):
                    node, _, path = visible[self.cursor]
                    if node.is_dir:
                        node.is_expanded = not node.is_expanded
                        return self, lambda: GitTreeToggleMsg(node=node, expanded=node.is_expanded)
                    return self, lambda: GitTreeSelectMsg(node=node, path=path)

        elif isinstance(msg, MouseMsg):
            rel_x = msg.x - self.offset_x
            rel_y = msg.y - self.offset_y

            if msg.button == MouseButton.WHEEL_UP:
                self.cursor = max(0, self.cursor - 1)
                self._adjust_scroll(max_visible)
                return self, None
            elif msg.button == MouseButton.WHEEL_DOWN:
                if visible:
                    self.cursor = min(len(visible) - 1, self.cursor + 1)
                    self._adjust_scroll(max_visible)
                return self, None

            # Start of rows: y=2 if header, y=1 if no header
            start_y = 2 if self.show_branch_header else 1
            row_idx = rel_y - start_y
            if 0 <= row_idx < max_visible:
                target_idx = self.scroll_offset + row_idx
                if 0 <= target_idx < len(visible):
                    self.cursor = target_idx
                    node, _, path = visible[target_idx]
                    if msg.action == MouseAction.DOUBLE_CLICK:
                        if node.is_dir:
                            node.is_expanded = not node.is_expanded
                            return self, lambda: GitTreeToggleMsg(node=node, expanded=node.is_expanded)
                        else:
                            return self, lambda: GitTreeSelectMsg(node=node, path=path)
                    return self, None

        return self, None

    def _adjust_scroll(self, max_visible: int) -> None:
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + max_visible:
            self.scroll_offset = self.cursor - max_visible + 1

    def _format_status_badge(self, status: GitFileStatus | str, staged: bool = False) -> str:
        s_val = status.value if isinstance(status, GitFileStatus) else str(status)
        if not s_val:
            return ""

        badge = f"[{s_val}]"
        if s_val == "M":
            st = Style().foreground("#E0AF68").bold(True)  # Yellow/Orange
        elif s_val == "A":
            st = Style().foreground("#9ECE6A").bold(True)  # Green
        elif s_val == "D":
            st = Style().foreground("#F7768E").bold(True)  # Red
        elif s_val == "?":
            st = Style().foreground("#7AA2F7")             # Blue
        elif s_val == "U":
            st = Style().foreground("#BB9AF7").bold(True)  # Magenta
        elif s_val == "R":
            st = Style().foreground("#7DCFFF")             # Cyan
        else:
            st = Style().foreground("#888888")

        rendered = st.render(badge)
        if staged:
            st_stage = Style().foreground("#9ECE6A").bold(True).render("+")
            rendered = f"{st_stage}{rendered}"
        return rendered

    def view(self) -> str:
        """Render the Git file tree."""
        inner_w = self.width - 2
        visible = self.flatten_visible()
        max_visible = max(1, self.height - (4 if self.show_branch_header else 2))

        lines: list[str] = []

        # 1. Branch Header
        if self.show_branch_header:
            b_icon = Style().foreground("#BB9AF7").bold(True).render("⎇")
            b_name = Style().foreground("#7DCFFF").bold(True).render(f" {self.branch}")
            # Count modified / untracked
            mods = sum(1 for n, _, _ in visible if str(n.status) in ("M", "GitFileStatus.MODIFIED"))
            adds = sum(1 for n, _, _ in visible if str(n.status) in ("A", "?", "GitFileStatus.ADDED", "GitFileStatus.UNTRACKED"))
            stats = f" (~{mods} +{adds})" if (mods or adds) else ""
            stat_st = Style().foreground("#888888").faint(True).render(stats)

            hdr_text = f" {b_icon}{b_name}{stat_st}"
            hdr_text = truncate_ansi(hdr_text, inner_w)
            hw = string_width(hdr_text)
            if hw < inner_w:
                hdr_text += " " * (inner_w - hw)
            lines.append(hdr_text)

            # Header separator
            sep = Style().foreground(self.border_color).render("─" * inner_w)
            lines.append(sep)

        # 2. Visible Nodes
        view_slice = visible[self.scroll_offset : self.scroll_offset + max_visible]
        for i, (node, depth, path) in enumerate(view_slice):
            actual_idx = self.scroll_offset + i
            is_selected = actual_idx == self.cursor

            # Indent
            indent = "  " * depth
            # Fold icon or file icon
            if node.is_dir:
                fold_icon = "▾ " if node.is_expanded else "▸ "
                fold_st = Style().foreground("#7AA2F7").bold(True).render(fold_icon)
                dir_st = Style().foreground("#FFFFFF").bold(True)
                icon_part = f"{fold_st}{dir_st.render(node.name)}/"
            else:
                ext = node.name.rsplit(".", 1)[-1].lower() if "." in node.name else ""
                if ext in ("py", "pyw"):
                    f_icon = "🐍 "
                elif ext in ("md", "txt"):
                    f_icon = "📝 "
                elif ext in ("json", "yaml", "toml"):
                    f_icon = "⚙️  "
                else:
                    f_icon = "📄 "
                name_st = Style().foreground("#C0CAF5")
                icon_part = f"{f_icon}{name_st.render(node.name)}"

            left_part = f"{indent}{icon_part}"
            badge = self._format_status_badge(node.status, node.staged)

            b_w = string_width(badge)
            avail_l = max(5, inner_w - b_w - (1 if b_w else 0))
            left_trunc = truncate_ansi(left_part, avail_l)
            l_w = string_width(left_trunc)

            gap = max(0, inner_w - l_w - b_w)
            row = f"{left_trunc}{' ' * gap}{badge}"

            if is_selected:
                row = Style().background("#2A2A3D").bold(True).render(row)

            lines.append(row)

        # Pad height
        while len(lines) < self.height - 2:
            lines.append(" " * inner_w)

        # Frame card
        border_st = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(self.border_color)
            .border_title(" Explorer ")
            .width(inner_w)
        )
        return border_st.render("\n".join(lines))
