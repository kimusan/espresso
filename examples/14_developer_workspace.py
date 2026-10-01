#!/usr/bin/env python3
"""Flagship Demo 14: Espresso Developer Workspace.

Integrates:
- GitTree: Git-decorated collapsible project file explorer
- CodeViewer: Syntax-highlighted source code editor viewer
- BarChart: TrueColor metrics dashboard with real-time resource telemetry
- CommandPalette: Fuzzy spotlight search and command runner (Ctrl+P)
- Grid & Crema: Responsive multi-pane layout with mouse hit testing
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure local espresso package is importable
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from espresso import Cmd, KeyMsg, Model, MouseAction, MouseButton, MouseMsg, Msg, Program, WindowSizeMsg, tick
from espresso.beans import (
    BarChart,
    BarChartSelectMsg,
    BarItem,
    BarOrientation,
    CodeViewer,
    CommandPalette,
    CommandPaletteCloseMsg,
    CommandPaletteSelectMsg,
    GitFileStatus,
    GitTree,
    GitTreeSelectMsg,
    GitTreeToggleMsg,
    PaletteItem,
    THEME_DRACULA,
    THEME_ESPRESSO,
    THEME_MONOKAI,
)
from espresso.crema import (
    DOUBLE_BORDER,
    ROUNDED_BORDER,
    THICK_BORDER,
    Grid,
    Style,
    join_horizontal,
    join_vertical,
    string_width,
    strip_ansi,
    truncate_ansi,
)

FILES_CONTENT = {
    "src/main.py": '''"""Espresso Developer Workspace Entrypoint."""

from __future__ import annotations

import asyncio
from espresso import Program, Model, KeyMsg
from espresso.beans import GitTree, BarChart, CommandPalette
from espresso.crema import Style, Grid


class Workspace(Model):
    """Next-generation terminal development workspace."""

    def __init__(self) -> None:
        self.version = "0.2.0"
        self.theme = "espresso"

    def run(self) -> None:
        print(f"Launching Espresso Workspace v{self.version}")


if __name__ == "__main__":
    Workspace().run()
''',
    "src/app.py": '''"""Core application state and business logic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ServiceConfig:
    name: str = "espresso-service"
    port: int = 8080
    workers: int = 4
    enable_telemetry: bool = True


class AppController:
    """Manages active sessions and worker pools."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.is_running = False

    async def start(self) -> None:
        self.is_running = True
        print(f"Server started on port {self.config.port}")
''',
    "tests/test_app.py": '''"""Unit test suite for workspace services."""

import unittest


class TestWorkspace(unittest.TestCase):
    def test_service_initialization(self) -> None:
        self.assertTrue(True)

    def test_pure_standard_library(self) -> None:
        import sys
        # Zero external dependencies guarantee
        self.assertIn("espresso", sys.modules)


if __name__ == "__main__":
    unittest.main()
''',
    "pyproject.toml": '''[project]
name = "espresso-tui"
version = "0.2.0"
description = "Lightweight Elm Architecture TUI framework for Python."
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
espresso = "espresso.cli:main"
''',
    "README.md": '''# Espresso TUI ☕

A lightweight, declarative Elm Architecture (TEA) TUI framework
written in 100% pure Python standard library.

## Features
- Complete Elm Architecture (Model, Msg, Cmd, Sub)
- Crema styling engine inspired by Lip Gloss
- 30+ reusable Bean widgets inspired by Bubbles
- Built-in CLI tool: `espresso run`, `espresso gallery`, `espresso new`
''',
}

WORKSPACE_TREE_PATHS = {
    "src/main.py": GitFileStatus.MODIFIED,
    "src/app.py": GitFileStatus.ADDED,
    "tests/test_app.py": GitFileStatus.UNTRACKED,
    "pyproject.toml": GitFileStatus.MODIFIED,
    "README.md": GitFileStatus.CLEAN,
}


class WorkspaceMsg(Msg):
    """Base message for workspace actions."""


class TelemetryTickMsg(Msg):
    """Timer message to update CPU / RAM telemetry metrics."""


class WorkspaceModel(Model):
    """Flagship developer workspace tying all Espresso Beans together."""

    def __init__(self) -> None:
        self.width = 110
        self.height = 30
        self.show_tree = True
        self.active_file = "src/main.py"
        self.active_pane = "editor"  # "tree", "editor", "metrics"
        self.status_message = "Ready. Press Ctrl+P for Command Palette, Tab to switch panes, q to quit."
        self.tick_counter = 0

        # 1. Project Explorer (GitTree)
        self.tree = GitTree.from_paths(
            WORKSPACE_TREE_PATHS,
            branch="feature/beans-v0.2.0",
            root_name="espresso-workspace",
            width=28,
            height=20,
        )

        # 2. Source Code Viewer (CodeViewer)
        self.code_viewer = CodeViewer(
            code=FILES_CONTENT[self.active_file],
            filename=self.active_file,
            width=48,
            height=20,
            theme=THEME_ESPRESSO,
            show_line_numbers=True,
        )

        # 3. Resource Telemetry (BarChart)
        self.metrics_items = [
            BarItem(label="CPU Core 0", value=42.0, formatter=lambda v: f"{v:.0f}%"),
            BarItem(label="CPU Core 1", value=68.0, formatter=lambda v: f"{v:.0f}%"),
            BarItem(label="RAM Usage", value=54.0, formatter=lambda v: f"{v:.0f}%"),
            BarItem(label="Coverage", value=98.0, formatter=lambda v: f"{v:.0f}%"),
            BarItem(label="Disk Cache", value=31.0, formatter=lambda v: f"{v:.0f}%"),
        ]
        self.metrics_chart = BarChart(
            items=self.metrics_items,
            title="System Telemetry",
            orientation=BarOrientation.HORIZONTAL,
            width=30,
            height=10,
            gradient_colors=("#00E5FF", "#7D56F4", "#F7768E"),
        )

        # 4. Command Palette (CommandPalette)
        palette_items = [
            PaletteItem("search_files", "Files: Quick Open", "Search and open workspace files", "Ctrl+P", "Files"),
            PaletteItem("git_status", "Git: View Status", "Show modified and untracked files", "Ctrl+G", "Git"),
            PaletteItem("theme_espresso", "Theme: Espresso Classic", "Default warm coffee palette", "", "Preferences"),
            PaletteItem("theme_dracula", "Theme: Dracula", "Popular dark purple/cyan theme", "", "Preferences"),
            PaletteItem("theme_monokai", "Theme: Monokai Pro", "Vibrant code syntax theme", "", "Preferences"),
            PaletteItem("toggle_tree", "View: Toggle Explorer", "Show or hide file tree pane", "Ctrl+B", "View"),
            PaletteItem("run_tests", "Test: Run Unit Tests", "Execute 330+ pure standard library tests", "Ctrl+T", "Test"),
            PaletteItem("open_main", "Open: src/main.py", "Main entry point file", "", "Files"),
            PaletteItem("open_app", "Open: src/app.py", "Core application service file", "", "Files"),
            PaletteItem("open_tests", "Open: tests/test_app.py", "Unit test suite file", "", "Files"),
            PaletteItem("open_pyproject", "Open: pyproject.toml", "Build configuration and scripts", "", "Files"),
            PaletteItem("open_readme", "Open: README.md", "Documentation guide", "", "Files"),
            PaletteItem("quit_app", "Quit: Exit Workspace", "Exit the workspace safely", "q", "Application"),
        ]
        self.command_palette = CommandPalette(
            items=palette_items,
            width=64,
            max_height=14,
            placeholder="Type a command, file, or action...",
            is_open=False,
            toggle_key="ctrl+p",
        )

    def init(self) -> tuple[Model, Cmd]:
        """Start background telemetry simulation ticker."""
        return self, tick(0.8, lambda: TelemetryTickMsg())

    def update(self, msg: Msg) -> tuple[Model, Cmd]:
        """Handle workspace messages and route to active components."""
        # 1. Handle Window Resize
        if isinstance(msg, WindowSizeMsg):
            self.width = max(80, msg.width)
            self.height = max(24, msg.height)
            self._recalculate_dimensions()
            return self, None

        # 2. Handle Telemetry Tick
        if isinstance(msg, TelemetryTickMsg):
            self.tick_counter += 1
            # Slightly modulate metrics for realistic dashboard animation
            c0 = 35.0 + ((self.tick_counter * 7) % 45)
            c1 = 50.0 + ((self.tick_counter * 11) % 40)
            ram = 52.0 + ((self.tick_counter * 3) % 15)
            self.metrics_items[0].value = min(99.0, c0)
            self.metrics_items[1].value = min(99.0, c1)
            self.metrics_items[2].value = min(95.0, ram)
            self.metrics_chart.set_items(self.metrics_items)
            return self, tick(0.8, lambda: TelemetryTickMsg())

        # 3. Handle Command Palette Open/Close/Select
        if self.command_palette.is_open or (isinstance(msg, KeyMsg) and str(msg.key).lower() == "ctrl+p"):
            new_cp, cp_cmd = self.command_palette.update(msg)
            self.command_palette = new_cp  # type: ignore[assignment]
            if cp_cmd is not None:
                # Execute command palette callback
                produced_msg = cp_cmd() if callable(cp_cmd) else None
                if isinstance(produced_msg, CommandPaletteSelectMsg):
                    action_cmd = self._handle_palette_selection(produced_msg.item)
                    if action_cmd is not None:
                        return self, action_cmd
            return self, None

        # 4. Handle Global Keypresses
        if isinstance(msg, KeyMsg):
            key = str(msg.key).lower()
            if key in ("q", "ctrl+c"):
                from espresso import quit_app
                return self, quit_app()

            elif key == "tab":
                panes = ["tree", "editor", "metrics"] if self.show_tree else ["editor", "metrics"]
                curr_idx = panes.index(self.active_pane) if self.active_pane in panes else 0
                self.active_pane = panes[(curr_idx + 1) % len(panes)]
                self.status_message = f"Focused pane: {self.active_pane.upper()}"
                return self, None

            elif key == "ctrl+b":
                self._toggle_tree()
                return self, None

            elif key == "ctrl+t":
                self.status_message = "Ran 334 tests: 100% OK (0.17s)"
                return self, None

        # 5. Route to Active Component or Mouse Hit Testing
        if isinstance(msg, MouseMsg):
            # Check if clicked in top header search bar to open command palette
            if msg.action == MouseAction.PRESS and msg.y == 0 and 16 <= msg.x <= 45:
                self.command_palette.open()
                return self, None

            tree_w, _, metrics_w = self._compute_pane_widths()

            # Route to tree (if visible)
            if self.show_tree and msg.x < tree_w:
                self.active_pane = "tree"
                new_tree, cmd = self.tree.update(msg)
                self.tree = new_tree  # type: ignore[assignment]
                if cmd is not None:
                    res = cmd() if callable(cmd) else None
                    if isinstance(res, GitTreeSelectMsg):
                        self._load_file(res.path)
                return self, None

            # Route to metrics
            elif msg.x >= self.width - metrics_w:
                self.active_pane = "metrics"
                new_chart, cmd = self.metrics_chart.update(msg)
                self.metrics_chart = new_chart  # type: ignore[assignment]
                return self, None

            # Route to editor
            else:
                self.active_pane = "editor"
                new_cv, cmd = self.code_viewer.update(msg)
                self.code_viewer = new_cv  # type: ignore[assignment]
                return self, None

        # Keyboard dispatch by active pane
        if self.active_pane == "tree":
            new_tree, cmd = self.tree.update(msg)
            self.tree = new_tree  # type: ignore[assignment]
            if cmd is not None:
                res = cmd() if callable(cmd) else None
                if isinstance(res, GitTreeSelectMsg):
                    self._load_file(res.path)
            elif isinstance(msg, KeyMsg) and str(msg.key).lower() == "enter":
                # Check current node
                selected = self.tree.get_selected_node()
                if selected:
                    node, path = selected
                    if not node.is_dir:
                        self._load_file(path)
            return self, None

        elif self.active_pane == "editor":
            new_cv, cmd = self.code_viewer.update(msg)
            self.code_viewer = new_cv  # type: ignore[assignment]
            return self, None

        elif self.active_pane == "metrics":
            new_chart, cmd = self.metrics_chart.update(msg)
            self.metrics_chart = new_chart  # type: ignore[assignment]
            return self, None

        return self, None

    def _load_file(self, full_path: str) -> None:
        """Load selected file into the CodeViewer."""
        cleaned_path = full_path.replace("espresso-workspace/", "").strip("/")
        if cleaned_path in FILES_CONTENT:
            self.active_file = cleaned_path
            self.code_viewer.filename = cleaned_path
            self.code_viewer.set_code(FILES_CONTENT[cleaned_path])
            self.status_message = f"Loaded file: {cleaned_path}"
        else:
            self.status_message = f"Selected: {cleaned_path}"

    def _handle_palette_selection(self, item: PaletteItem) -> Cmd | None:
        """Execute selected palette action."""
        if item.id == "theme_espresso":
            self.code_viewer.theme = THEME_ESPRESSO
            self.code_viewer._rebuild_content()
            self.status_message = "Theme changed to Espresso"
        elif item.id == "theme_dracula":
            self.code_viewer.theme = THEME_DRACULA
            self.code_viewer._rebuild_content()
            self.status_message = "Theme changed to Dracula"
        elif item.id == "theme_monokai":
            self.code_viewer.theme = THEME_MONOKAI
            self.code_viewer._rebuild_content()
            self.status_message = "Theme changed to Monokai"
        elif item.id == "toggle_tree":
            self._toggle_tree()
        elif item.id == "run_tests":
            self.status_message = "Ran 334 tests: 100% OK (0.17s)"
        elif item.id == "quit_app":
            from espresso import quit_app
            return quit_app()
        elif item.id.startswith("open_"):
            fname = item.title.replace("Open: ", "").strip()
            self._load_file(fname)
        return None

    def _toggle_tree(self) -> None:
        """Toggle Explorer sidebar visibility."""
        self.show_tree = not self.show_tree
        if not self.show_tree and self.active_pane == "tree":
            self.active_pane = "editor"
        self.status_message = "Explorer: Shown [Ctrl+B]" if self.show_tree else "Explorer: Hidden [Ctrl+B]"

    def _compute_pane_widths(self) -> tuple[int, int, int]:
        """Compute responsive widths for (tree, editor, metrics)."""
        if self.show_tree:
            if self.width < 90:
                tree_w = 22
                metrics_w = 26
            elif self.width < 105:
                tree_w = 25
                metrics_w = 28
            else:
                tree_w = 28
                metrics_w = 32
        else:
            tree_w = 0
            metrics_w = 26 if self.width < 90 else (28 if self.width < 105 else 32)

        editor_w = max(20, self.width - tree_w - metrics_w)
        return tree_w, editor_w, metrics_w

    def _recalculate_dimensions(self) -> None:
        """Adjust component dimensions based on terminal width and height."""
        # Top header is 1 row, bottom status is 1 row. Total body height:
        body_h = max(10, self.height - 2)
        tree_w, editor_w, metrics_w = self._compute_pane_widths()

        self.tree.width = tree_w
        self.tree.height = body_h

        # editor_w and body_h are outer dimensions; editor_border adds 2 to width and 2 to height
        self.code_viewer.set_size(max(10, editor_w - 2), max(2, body_h - 2))

        self.metrics_chart.width = metrics_w
        chart_h = body_h // 2
        self.metrics_chart.height = chart_h

    def view(self) -> str:
        """Render the complete developer workspace."""
        self._recalculate_dimensions()
        inner_w = self.width
        body_h = max(10, self.height - 2)
        tree_w, editor_w, metrics_w = self._compute_pane_widths()

        # 1. Top Header Bar
        logo = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1).render("☕ ESPRESSO IDE")
        search_btn = Style().foreground("#BB9AF7").render(" 🔍 Search [Ctrl+P] ")
        file_tab = Style().bold(True).foreground("#00E5FF").render(f"  📄 {self.active_file}")
        branch_badge = Style().foreground("#9ECE6A").bold(True).render("  ⎇ feature/beans-v0.2.0")

        left_hdr = f"{logo}{search_btn}{file_tab}{branch_badge}"
        right_hdr = Style().foreground("#888888").render("Pure Python • Zero Wheels ")
        rh_w = string_width(right_hdr)
        avail_lh = max(0, inner_w - rh_w)
        left_trunc = truncate_ansi(left_hdr, avail_lh, tail="")
        lh_w = string_width(left_trunc)
        gap = max(0, inner_w - lh_w - rh_w)
        top_bar = f"{left_trunc}{' ' * gap}{right_hdr}"
        top_bar = truncate_ansi(top_bar, inner_w, tail="")

        # 2. Main Body
        if self.show_tree:
            self.tree.set_offset(0, 1)
            tree_view = self.tree.view()

        # Center Pane: CodeViewer
        editor_x = tree_w
        max_title_w = max(4, editor_w - 4)
        editor_title = truncate_ansi(f" Editor: {self.active_file} ", max_title_w, tail="")
        editor_border = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF" if self.active_pane == "editor" else "#555555")
            .border_title(editor_title)
            .width(editor_w - 2)
            .height(body_h)
        )
        editor_framed = editor_border.render(self.code_viewer.view())

        # Right Pane: Metrics + Quick Notes Panel
        metrics_x = editor_x + editor_w
        self.metrics_chart.set_offset(metrics_x, 1)
        chart_view = self.metrics_chart.view()

        # Quick notes card underneath chart
        notes_content = (
            "• Pure Python standard library\n"
            "• 334 tests passing with 100% precision\n"
            "• Mouse double-click & gestures\n"
            "• Built-in CLI tool: espresso\n"
            "• Full TrueColor gradient styling"
        )
        notes_h = body_h - (body_h // 2)
        notes_panel = Grid.panel(
            "Release Notes v0.2.0",
            notes_content,
            width=metrics_w,
            height=notes_h,
            border_foreground="#7AA2F7",
        )
        right_pane = join_vertical(chart_view, notes_panel)

        # Combine panes horizontally
        if self.show_tree:
            main_body = join_horizontal(tree_view, editor_framed, right_pane)
        else:
            main_body = join_horizontal(editor_framed, right_pane)

        # 3. Bottom Status Bar
        focus_badge = Style().bold(True).background("#2A2A3D").foreground("#00E5FF").padding(0, 1).render(f" PANE: {self.active_pane.upper()} ")
        fb_w = string_width(focus_badge)
        shortcuts = Style().foreground("#888888").render("Tab: Switch Pane • Ctrl+P: Palette • q: Quit ")
        sc_w = string_width(shortcuts)
        avail_st = max(0, inner_w - fb_w - sc_w - 2)
        status_text = Style().foreground("#C0CAF5").render(f"  {self.status_message}")
        status_trunc = truncate_ansi(status_text, avail_st, tail="…") if string_width(status_text) > avail_st else status_text
        left_status = f"{focus_badge}{status_trunc}"
        ls_w = string_width(left_status)
        st_gap = max(0, inner_w - ls_w - sc_w)
        bottom_bar = f"{left_status}{' ' * st_gap}{shortcuts}"
        bottom_bar = truncate_ansi(bottom_bar, inner_w, tail="")

        # Combine screen
        full_screen = "\n".join([top_bar, main_body, bottom_bar])

        # 4. If Command Palette is open, overlay it on top!
        if self.command_palette.is_open:
            full_screen = self.command_palette.overlay(full_screen)

        return full_screen


def main() -> None:
    """Launch Developer Workspace demo."""
    model = WorkspaceModel()
    program = Program(model, alt_screen=True, mouse=True)
    program.run()


if __name__ == "__main__":
    main()
