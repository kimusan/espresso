#!/usr/bin/env python3
"""Example 10: Full-Window Beans Component Gallery.

Interactive showcase demonstrating the full suite of newly added components
in a responsive, edge-to-edge full-window terminal layout:
1. Tabs: Top tab navigation bar with hotkeys (1-6, Tab / Shift-Tab)
2. List & Paginator: Filterable list with search (/) and live pagination
3. FilePicker: Interactive filesystem browser with file sizes and hidden file toggle (.)
4. Prompts & DatePicker: SelectPrompt, MultiSelectPrompt, ConfirmPrompt, and DatePicker
5. Tree: Collapsible hierarchical directory tree
6. Dialog & 2D Overlay: Modal card composited on top with backdrop dimming (press 'd')
7. ToastManager: Transient auto-dismissing toast notifications (press 't')
8. Responsive FlexBox & Metrics: Proportional grid and KPI stats cards
9. Pipelines & Media: Multi-stage task runner, master-detail selector, and ANSI truecolor image viewer
"""

from __future__ import annotations

import random
import shutil
import sys
from datetime import date
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import (
    Cmd,
    KeyMsg,
    Model,
    MouseAction,
    MouseButton,
    MouseMsg,
    Msg,
    Program,
    WindowSizeMsg,
    batch,
    disable_mouse,
    enable_mouse,
    quit_app,
)
from espresso.beans import (
    ConfirmPrompt,
    ConfirmSubmitMsg,
    DateChangeMsg,
    DatePicker,
    DatePickerFocus,
    DateSelectMsg,
    DetailItem,
    DetailSelectMsg,
    DetailSelector,
    Dialog,
    DialogResultMsg,
    FilePicker,
    FileSelectMsg,
    ImageViewer,
    LayoutDirection,
    List,
    ListItem,
    ListSelectMsg,
    Metric,
    MetricGroup,
    MetricLayout,
    MetricTrend,
    MultiSelectPrompt,
    MultiSelectSubmitMsg,
    NavStack,
    PaginationMode,
    PipelineProgress,
    PipelineStage,
    RenderMode,
    SelectPrompt,
    SelectSubmitMsg,
    StageStatus,
    StatusBar,
    StatusSection,
    TabStyle,
    Tabs,
    ToastDismissMsg,
    ToastLevel,
    ToastManager,
    Tree,
    TreeNode,
    TreeNodeSelectMsg,
)
from espresso.crema import (
    Align,
    Cell,
    FlexBox,
    ROUNDED_BORDER,
    Row,
    Style,
    join_horizontal,
    join_vertical,
    place_overlay,
    string_width,
    truncate_ansi,
)


def make_panel(
    title: str,
    content: str,
    w: int,
    h: int,
    border_fg: str = "#4A4A6A",
    border_title_align: Align = Align.LEFT,
) -> str:
    """Render a framed box with guaranteed exact visual width w and exact line count h."""
    w = max(4, w)
    h = max(3, h)
    inner_w = max(0, w - 2)
    inner_h = max(0, h - 2)

    raw_lines = content.splitlines() if content else []
    # Truncate each line to inner_w
    formatted_lines = [truncate_ansi(l, inner_w) for l in raw_lines[:inner_h]]
    # Pad with spaces to reach inner_h so splitlines doesn't drop trailing empty strings
    while len(formatted_lines) < inner_h:
        formatted_lines.append(" " * inner_w)

    rendered = (
        Style()
        .border(ROUNDED_BORDER)
        .border_foreground(border_fg)
        .border_title(f" {title} " if title else None, border_title_align)
        .width(inner_w)
        .render("\n".join(formatted_lines))
    )

    res_lines = rendered.splitlines()
    while len(res_lines) < h:
        res_lines.append(" " * w)
    return "\n".join(res_lines[:h])


class ComponentGallery(Model):
    def __init__(self) -> None:
        # Query active terminal size on startup so first frame is full-screen
        ts = shutil.get_terminal_size((100, 30))
        self.width = max(80, ts.columns)
        self.height = max(24, ts.lines)

        self.status_msg = "Use Tab / Click to navigate tabs, 'd' for modal dialog, 't' for toast, 'm' for mouse, 'q' to quit"
        self.mouse_enabled = True

        # --- Component 1: Tabs ---
        self.tabs = Tabs(
            titles=["Filterable List", "File Picker", "CLI Prompts", "Tree View", "FlexBox & KPIs", "Pipelines & Media"],
            active_tab=0,
            tab_style=TabStyle.PILL,
            show_numbers=True,
        )

        # --- Component 2: List & Paginator ---
        list_items = [
            ListItem("Espresso TEA", "Lightweight Pure Python TUI Framework", "framework", badge="CORE", badge_style=Style().foreground("#00E676").bold(True)),
            ListItem("Crema Style Engine", "Declarative styling, borders, and gradients", "styling", badge="STABLE", badge_style=Style().foreground("#7D56F4")),
            ListItem("Beans Components", "Standard library of reusable UI widgets", "widgets", badge="NEW", badge_style=Style().foreground("#FFB300").bold(True)),
            ListItem("Terminal Parser", "ANSI escape codes and mouse tracking", "terminal", badge="CORE", badge_style=Style().foreground("#00E676")),
            ListItem("Overlay Compositor", "2D layer compositing with backdrop dimming", "overlay", badge="STABLE", badge_style=Style().foreground("#7D56F4")),
            ListItem("Paginator", "Dots, numeric, and compact pagination indicators", "paginator", badge="WIDGET", badge_style=Style().foreground("#29B6F6")),
            ListItem("FilePicker", "Interactive directory browser with file size formats", "filesystem", badge="WIDGET", badge_style=Style().foreground("#29B6F6")),
            ListItem("Dialog & Modal", "Card dialog with action buttons and keyboard focus", "dialog", badge="MODAL", badge_style=Style().foreground("#AB47BC")),
            ListItem("Interactive Prompts", "Select, MultiSelect checkboxes, and Confirm prompts", "prompts", badge="CLI", badge_style=Style().foreground("#26A69A")),
            ListItem("Collapsible Tree", "Hierarchical tree view with branch guides", "tree", badge="WIDGET", badge_style=Style().foreground("#29B6F6")),
            ListItem("Toast Notifications", "Auto-dismissing asynchronous alerts", "toast", badge="ALERT", badge_style=Style().foreground("#FFA726")),
            ListItem("Line Diffing Buffer", "Zero-flicker double buffered screen redraw", "renderer", badge="SPEED", badge_style=Style().foreground("#EC407A")),
            ListItem("SGR Mouse Protocol", "Mouse clicks, dragging, and wheel scrolling", "mouse", badge="INPUT", badge_style=Style().foreground("#26C6DA")),
            ListItem("Adaptive Colors", "Light/Dark background detection & NO_COLOR", "color", badge="THEME", badge_style=Style().foreground("#AB47BC")),
            ListItem("Responsive FlexBox", "Stickers-inspired 2D proportional grid with ratios", "layout", badge="LAYOUT", badge_style=Style().foreground("#FF7043")),
            ListItem("Multi-Section StatusBar", "Teacup-inspired responsive header/footer bar", "statusbar", badge="BAR", badge_style=Style().foreground("#7E57C2")),
            ListItem("KPI Metric Cards", "OrtizAlec-inspired stat cards with trend arrows", "metric", badge="STAT", badge_style=Style().foreground("#66BB6A")),
            ListItem("NavStack & Breadcrumbs", "BubbleO-inspired view stack with breadcrumb trail", "navstack", badge="NAV", badge_style=Style().foreground("#42A5F5")),
        ]
        self.list = List(
            items=list_items,
            title="Component Catalog",
            per_page=6,
            width=46,
            show_filter=True,
            show_pagination=True,
        )
        self.selected_item = list_items[0]

        # --- Component 3: FilePicker ---
        project_root = Path(__file__).resolve().parent.parent
        self.file_picker = FilePicker(
            directory=project_root,
            height=14,
            width=50,
            show_hidden=False,
            dir_allowed=True,
        )
        self.selected_file_str = f"{project_root.name} (Directory)"

        # --- Component 4: Prompts ---
        self.select_prompt = SelectPrompt(
            question="Select deployment target:",
            options=["Production Cluster", "Staging Environment", "Local Container", "Bare Metal Edge"],
        )
        self.multiselect_prompt = MultiSelectPrompt(
            question="Select build pipelines to trigger:",
            options=["Run Unit Tests", "Type Checking (mypy)", "Lint & Format", "Build Binary", "Publish Docs"],
            default_selected=[0, 2],
        )
        self.confirm_prompt = ConfirmPrompt(
            question="Deploy changes immediately?",
            default=False,
        )
        self.datepicker = DatePicker(
            value=date.today(),
            cursor_date=date.today(),
            show_header=True,
            show_help=True,
            border=ROUNDED_BORDER,
            border_foreground="#7C4DFF",
        )
        self.active_prompt_idx = 0  # 0: select, 1: multi, 2: confirm, 3: datepicker

        # --- Component 5: Collapsible Tree ---
        tree_root = TreeNode(
            label="espresso",
            expanded=True,
            children=[
                TreeNode(
                    label="src/espresso",
                    expanded=True,
                    children=[
                        TreeNode(
                            label="core",
                            expanded=True,
                            children=[
                                TreeNode("tea.py (The Elm Architecture)"),
                                TreeNode("keys.py (Key event parser)"),
                                TreeNode("program.py (Runtime engine & renderer)"),
                            ],
                        ),
                        TreeNode(
                            label="crema",
                            expanded=True,
                            children=[
                                TreeNode("style.py (Box model & borders)"),
                                TreeNode("color.py (ANSI / RGB / Adaptive)"),
                                TreeNode("overlay.py (2D layer compositor)"),
                                TreeNode("gradient.py (Color gradients)"),
                            ],
                        ),
                        TreeNode(
                            label="beans",
                            expanded=True,
                            children=[
                                TreeNode("list.py (Filterable list & paginator)"),
                                TreeNode("filepicker.py (Filesystem explorer)"),
                                TreeNode("dialog.py (Modal overlay card)"),
                                TreeNode("prompt.py (CLI prompts)"),
                                TreeNode("toast.py (Toast manager)"),
                                TreeNode("tabs.py (Tab navigation bar)"),
                                TreeNode("tree.py (Collapsible tree view)"),
                            ],
                        ),
                    ],
                ),
                TreeNode(
                    label="examples",
                    expanded=True,
                    children=[
                        TreeNode("05_beans_showcase.py (Coffee wizard)"),
                        TreeNode("08_rss_reader.py (Fullscreen RSS reader)"),
                        TreeNode("09_colors_and_gradients.py (Palette demo)"),
                        TreeNode("10_component_gallery.py (Full window gallery)"),
                    ],
                ),
                TreeNode(
                    label="tests",
                    children=[
                        TreeNode("test_beans_new.py (168 tests)"),
                        TreeNode("test_overlay.py (2D compositor tests)"),
                    ],
                ),
            ],
        )
        self.tree = Tree(nodes=[tree_root])
        self.selected_node_label = "espresso"

        # --- Component 6: Toast Manager ---
        self.toast_manager = ToastManager()

        # --- Component 7: Modal Dialog ---
        self.show_dialog = False
        self.dialog = Dialog(
            title="Deploy Application",
            message="Are you sure you want to deploy the latest release to the production cluster?\nAll microservices will undergo rolling updates.",
            buttons=("Deploy Now", "Cancel"),
            width=50,
            border_foreground="#00E676",
        )

        # --- Component 8: FlexBox & Metrics & NavStack ---
        self.metrics = MetricGroup(
            [
                Metric("Requests", "14,820", unit="/s", delta="+14.2%", trend=MetricTrend.UP, width=22),
                Metric("Latency", "18.4", unit="ms", delta="-2.1ms", trend=MetricTrend.DOWN, invert_trend=True, width=22),
                Metric("Cluster CPU", "46.8%", delta="+4.1%", trend=MetricTrend.UP, width=22),
                Metric("Memory", "3.2 GB", delta="-120MB", trend=MetricTrend.DOWN, invert_trend=True, width=22),
            ],
            layout=MetricLayout.CARD,
            direction=LayoutDirection.VERTICAL,
        )

        class ClusterDoc(Model):
            def __init__(self, title: str, body: str, hint: str):
                self.title = title
                self.body = body
                self.hint = hint
            def init(self): return None
            def update(self, msg): return self, None
            def view(self):
                lines = [
                    f"{Style().bold(True).foreground('#00E5FF').render(self.title)}",
                    f"{Style().foreground('#555577').render('--------------------------------------------------')}",
                    f"{Style().foreground('#D0D0D0').render(self.body)}",
                    "",
                    f"{Style().bold(True).foreground('#00E676').render(self.hint)}",
                ]
                return "\n".join(lines)

        self.nav_stack = NavStack(
            initial_title="Overview",
            initial_model=ClusterDoc(
                "Global Cluster Infrastructure (Level 1)",
                "• 8 worker nodes across us-east-1 (Primary) and eu-west-1 (Replica)\n"
                "• 48 container pods active, 0 restarts in the last 24h\n"
                "• Network mesh latency: 1.2ms (healthy)",
                "💡 Click below or press 'p' to drill down into Microservices →",
            ),
        )

        self.statusbar = StatusBar(
            left=[
                StatusSection("READY", Style().bold(True).foreground("#000000").background("#00E676").padding(0, 1), priority=3),
                StatusSection("git:main*", Style().foreground("#D0D0D0").background("#2A2A3E").padding(0, 1), priority=2),
            ],
            center=[
                StatusSection("cluster-prod-01.espresso.internal", Style().foreground("#FFD54F")),
            ],
            right=[
                StatusSection("py 3.12", Style().foreground("#8888AA")),
                StatusSection("utf-8", Style().foreground("#00E5FF")),
                StatusSection("100% HEALTH", Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1), priority=3),
            ],
            background="#161622",
        )

        # --- Component 9: PipelineProgress ---
        self.pipeline = PipelineProgress(
            stages=[
                PipelineStage(title="Fetch Source & Dependencies", status=StageStatus.SUCCESS, duration=0.82),
                PipelineStage(title="Lint & Static Analysis (flake8)", status=StageStatus.SUCCESS, duration=1.14),
                PipelineStage(title="Compile & Run Unit Tests (231 tests)", status=StageStatus.RUNNING, duration=0.14),
                PipelineStage(title="Build Optimized Wheel Distribution", status=StageStatus.PENDING),
                PipelineStage(title="Publish Artifacts to Registry", status=StageStatus.PENDING),
            ],
            title="CI/CD Release Pipeline",
            width=44,
            show_stages=True,
            show_timer=True,
        )

        # --- Component 10: DetailSelector ---
        self.detail_selector = DetailSelector(
            items=[
                DetailItem(
                    title="Espresso Runtime",
                    tag="CORE",
                    details="Declarative The Elm Architecture (TEA)\nevent loop with pure Python stdlib.\nZero external runtime dependencies.",
                    metadata={"Version": "0.1.0", "Type": "Engine"},
                ),
                DetailItem(
                    title="Crema Styling & 2D",
                    tag="STABLE",
                    details="Full ANSI truecolor & 256-color support,\n2D layer placement, gradient shading,\nand flexible rounded/double borders.",
                    metadata={"Engine": "Crema", "Status": "Ready"},
                ),
                DetailItem(
                    title="Beans Component Library",
                    tag="WIDGETS",
                    details="Rich library of 27+ terminal widgets\nincluding Table, Viewport, DatePicker,\nMarkdown, CodeViewer, QuickFix, etc.",
                    metadata={"Count": "27+", "License": "MIT"},
                ),
                DetailItem(
                    title="ANSI Half-Block Imaging",
                    tag="MEDIA",
                    details="Truecolor 24-bit half-block renderer (▀)\nsupporting PPM, BMP, and raw RGB matrices\nwith optional Pillow bridge.",
                    metadata={"Mode": "24-bit RGB", "Ramp": "10-step"},
                ),
            ],
            prompt="Select Framework Architecture Layer:",
            width=44,
            per_page=4,
        )

        # --- Component 11: ImageViewer ---
        sunset_matrix = []
        for y in range(20):
            row = []
            for x in range(32):
                r = min(255, int(255 * (1.0 - y / 25)))
                g = min(255, int(180 * (x / 32) * (1.0 - y / 30)))
                b = min(255, int(220 * (y / 20)))
                row.append((r, g, b))
            sunset_matrix.append(row)
        self.image_viewer = ImageViewer(
            pixels=sunset_matrix,
            width=38,
            height=12,
            mode=RenderMode.HALF_BLOCK,
            title="Espresso Sunset 24-bit Half-Block",
        )

        self._sync_child_dimensions()

    def _calc_layout(self) -> tuple[int, int, int]:
        """Calculate (content_h, w_left, w_right) to fill window edge-to-edge."""
        W = max(70, self.width)
        H = max(20, self.height)
        content_h = max(8, H - 2)  # 1 row header, 1 row footer
        w_left = max(35, int(W * 0.55))
        w_right = W - w_left
        return content_h, w_left, w_right

    def _sync_child_dimensions(self) -> None:
        content_h, w_left, w_right = self._calc_layout()
        inner_w_left = max(10, w_left - 4)
        inner_w_right = max(10, w_right - 4)
        inner_h = max(4, content_h - 2)

        # Update List dimensions
        self.list.width = inner_w_left
        self.list.per_page = max(2, (inner_h - 5) // 2)
        self.list.paginator.per_page = self.list.per_page
        self.list.paginator.set_total(len(self.list.filtered_items))

        # Update FilePicker dimensions
        self.file_picker.width = inner_w_left
        self.file_picker.height = inner_h - 2

        # Update Pipeline, DetailSelector, and ImageViewer dimensions
        if hasattr(self, "pipeline"):
            self.pipeline.width = inner_w_left
        if hasattr(self, "detail_selector"):
            self.detail_selector.width = inner_w_left
        if hasattr(self, "image_viewer"):
            self.image_viewer.width = inner_w_right
            self.image_viewer.height = max(4, min(14, inner_h // 2))
            self.image_viewer.viewport.width = self.image_viewer.width
            self.image_viewer.viewport.height = self.image_viewer.height
            self.image_viewer._rebuild_rendered()

    def init(self) -> Cmd | None:
        _, toast_cmd = self.toast_manager.add(
            "Welcome to the Beans Component Gallery!",
            ToastLevel.INFO,
            duration=3.5,
        )
        return toast_cmd

    def _handle_mouse(self, msg: MouseMsg) -> tuple[ComponentGallery, Cmd | None]:
        # Wheel scrolling behaves like Up/Down navigation keys
        if msg.button == MouseButton.WHEEL_UP:
            return self.update(KeyMsg("up"))
        if msg.button == MouseButton.WHEEL_DOWN:
            return self.update(KeyMsg("down"))

        # Only process left-click press events
        if msg.button != MouseButton.LEFT or msg.action != MouseAction.PRESS:
            return self, None

        # 1. Modal Dialog Click Handling
        if self.show_dialog:
            dialog_w = 50
            dialog_lines = self.dialog.view().splitlines()
            dialog_h = max(7, len(dialog_lines))
            dx = (self.width - dialog_w) // 2
            dy = (self.height - dialog_h) // 2

            # Click outside dialog modal: dismiss
            if msg.x < dx or msg.x >= dx + dialog_w or msg.y < dy or msg.y >= dy + dialog_h:
                self.show_dialog = False
                self.status_msg = "Dialog dismissed."
                _, toast_cmd = self.toast_manager.add("Dialog dismissed", ToastLevel.INFO, duration=2.0)
                return self, toast_cmd

            # Click inside dialog: check buttons row
            btn_row = dy + dialog_h - 2
            if msg.y in (btn_row, btn_row - 1):
                if msg.x < dx + (dialog_w // 2):
                    self.show_dialog = False
                    self.status_msg = "Deployment sequence initiated!"
                    _, toast_cmd = self.toast_manager.add(
                        "🚀 Deployment sequence initiated!",
                        ToastLevel.SUCCESS,
                        duration=4.0,
                    )
                    return self, toast_cmd
                else:
                    self.show_dialog = False
                    self.status_msg = "Deployment cancelled."
                    _, toast_cmd = self.toast_manager.add(
                        "Action cancelled.",
                        ToastLevel.WARNING,
                        duration=2.5,
                    )
                    return self, toast_cmd
            return self, None

        # 2. Header Row Click (row 0): Tabs navigation
        if msg.y == 0:
            curr_x = 30  # Offset after title badge
            for i, title in enumerate(self.tabs.titles):
                label = f"{i + 1} {title}" if self.tabs.show_numbers else title
                tab_w = string_width(label) + 2
                if curr_x <= msg.x < curr_x + tab_w:
                    self.tabs.set_active(i)
                    self.status_msg = f"Switched to {title}"
                    _, toast_cmd = self.toast_manager.add(
                        f"Switched to Tab {i + 1}: {title}",
                        ToastLevel.INFO,
                        duration=2.0,
                    )
                    return self, toast_cmd
                curr_x += tab_w + 2
            return self, None

        # 3. Footer Row Click (row self.height - 1): Action shortcuts
        if msg.y >= self.height - 1:
            if msg.x < 35:
                next_tab = (self.tabs.active_tab + 1) % len(self.tabs.titles)
                self.tabs.set_active(next_tab)
                return self, None

            if msg.x >= self.width - 10:
                return self, quit_app
            elif self.width - 28 <= msg.x < self.width - 10:
                return self.update(KeyMsg("m"))
            elif self.width - 40 <= msg.x < self.width - 28:
                return self.update(KeyMsg("t"))
            elif self.width - 55 <= msg.x < self.width - 40:
                self.show_dialog = True
                return self, None
            return self, None

        # 4. Content Panels Click
        content_h, w_left, w_right = self._calc_layout()
        curr_tab = self.tabs.active_tab

        if msg.x < w_left:
            # Left Panel Interaction
            if curr_tab == 0:
                # Tab 0: Filterable List
                # Row 2 is title, row 3 is blank, items start on row 4 (2 lines per item: title + desc)
                if msg.y == 2:
                    return self.update(KeyMsg("/"))
                elif msg.y >= 4:
                    item_idx_on_page = (msg.y - 4) // 2
                    start_idx = self.list.paginator.page * self.list.per_page
                    target_idx = start_idx + item_idx_on_page
                    if 0 <= target_idx < len(self.list.filtered_items):
                        self.list.cursor = target_idx
                        item = self.list.filtered_items[target_idx]
                        self.selected_item = item
                        self.status_msg = f"Inspecting: {item.title}"
                        _, toast_cmd = self.toast_manager.add(
                            f"Selected: {item.title}",
                            ToastLevel.SUCCESS,
                            duration=2.5,
                        )
                        return self, toast_cmd

            elif curr_tab == 1:
                # Tab 1: FilePicker
                # Row 2 is path, row 3 is blank, entries start on row 4 (1 line per entry)
                if msg.y == 2:
                    # Click path breadcrumb: go to parent directory
                    return self.update(KeyMsg("backspace"))
                elif msg.y >= 4:
                    entry_idx_on_screen = msg.y - 4
                    target_idx = self.file_picker.scroll_offset + entry_idx_on_screen
                    entries = self.file_picker.entries
                    if 0 <= target_idx < len(entries):
                        if self.file_picker.cursor == target_idx:
                            return self.update(KeyMsg("enter"))
                        else:
                            self.file_picker.cursor = target_idx
                            entry = entries[target_idx]
                            kind = "Directory" if entry.is_dir else "File"
                            self.selected_file_str = f"{entry.name} ({kind})"
                            self.status_msg = f"Browsing: {entry.name}"
                            return self, None

            elif curr_tab == 2:
                # Tab 2: CLI Prompts & DatePicker
                if msg.x < w_left:
                    # Card 0: rows 2-9 (options at rows 4-7)
                    if msg.y <= 9:
                        self.active_prompt_idx = 0
                        opt_idx = msg.y - 4
                        if 0 <= opt_idx < len(self.select_prompt.options):
                            self.select_prompt.cursor = opt_idx
                            return self.update(KeyMsg("enter"))
                    # Card 1: rows 10-18 (checkboxes at rows 12-16)
                    elif msg.y <= 18:
                        self.active_prompt_idx = 1
                        opt_idx = msg.y - 12
                        if 0 <= opt_idx < len(self.multiselect_prompt.options):
                            self.multiselect_prompt.cursor = opt_idx
                            return self.update(KeyMsg(" "))
                    # Card 2: rows 19-21 (question & buttons at row 20)
                    else:
                        self.active_prompt_idx = 2
                        if msg.x < w_left // 2:
                            return self.update(KeyMsg("y"))
                        else:
                            return self.update(KeyMsg("n"))
                else:
                    # Right side: DatePicker calendar click
                    self.active_prompt_idx = 3
                    dp_rel_x = msg.x - w_left - 3
                    dp_rel_y = msg.y - 9
                    if dp_rel_y >= 0:
                        self.datepicker, dp_cmd = self.datepicker.handle_mouse_click(dp_rel_x, dp_rel_y)
                        if dp_cmd:
                            msg_res = dp_cmd()
                            if isinstance(msg_res, DateSelectMsg):
                                self.status_msg = f"Scheduled date: {msg_res.date.strftime('%Y-%m-%d')}"
                                _, toast_cmd = self.toast_manager.add(
                                    f"📅 Scheduled: {msg_res.date.strftime('%B %d, %Y')}",
                                    ToastLevel.SUCCESS,
                                    duration=3.5,
                                )
                                return self, toast_cmd
                    return self, None

            elif curr_tab == 3:
                # Tab 3: Tree View
                # Nodes start immediately at row 2 (1 line per visible node)
                if msg.y >= 2:
                    node_idx = msg.y - 2
                    visible_nodes = self.tree.visible_nodes
                    if 0 <= node_idx < len(visible_nodes):
                        if self.tree.cursor == node_idx:
                            return self.update(KeyMsg(" "))
                        else:
                            self.tree.cursor = node_idx
                            node = visible_nodes[node_idx]
                            self.selected_node_label = node.label
                            self.status_msg = f"Inspecting node: {node.label}"
                            return self, None

            elif curr_tab == 4:
                # Tab 4: Click Left panel -> toggle metric layout
                layouts = [MetricLayout.CARD, MetricLayout.TAG, MetricLayout.LIST]
                next_idx = (layouts.index(self.metrics.layout) + 1) % len(layouts)
                self.metrics.layout = layouts[next_idx]
                layout_name = self.metrics.layout.value.upper()
                self.status_msg = f"Metrics layout switched to {layout_name}"
                _, toast_cmd = self.toast_manager.add(f"Metrics: {layout_name} mode", ToastLevel.INFO, duration=2.0)
                return self, toast_cmd

        else:
            # Right Panel Interaction
            if curr_tab == 2:
                self.active_prompt_idx = (self.active_prompt_idx + 1) % 3
                return self, None
            elif curr_tab == 4:
                return self._cycle_navstack()

        return self, None

    def _cycle_navstack(self) -> tuple[ComponentGallery, Cmd | None]:
        if self.nav_stack.depth == 1:
            class ServicesTier(Model):
                def init(self): return None
                def update(self, msg): return self, None
                def view(self):
                    lines = [
                        Style().bold(True).foreground("#00E676").render("Microservices Tier (Level 2)"),
                        Style().foreground("#555577").render("--------------------------------------------------"),
                        "• api-gateway: 4 pods (0.01% error rate)\n• auth-svc: 2 pods (0.8ms token validation)\n• billing-svc: 3 pods (PCI-DSS compliant)",
                        "",
                        Style().bold(True).foreground("#FFD54F").render("💡 Click again to drill down into Database Shards →"),
                    ]
                    return "\n".join(lines)
            self.nav_stack.push("Services", ServicesTier())
            self.status_msg = "Drilled down into Services"
            _, toast_cmd = self.toast_manager.add("NavStack: Pushed Services", ToastLevel.SUCCESS, duration=2.0)
            return self, toast_cmd
        elif self.nav_stack.depth == 2:
            class DatabaseTier(Model):
                def init(self): return None
                def update(self, msg): return self, None
                def view(self):
                    lines = [
                        Style().bold(True).foreground("#FFD54F").render("Database Cluster Shard 01 (Level 3)"),
                        Style().foreground("#555577").render("--------------------------------------------------"),
                        "• PostgreSQL 16 Primary: 4,800 IOPS (healthy)\n• Read replica us-east-1b: 0.1ms replication lag\n• WAL archive compression: 82%",
                        "",
                        Style().bold(True).foreground("#FF5252").render("💡 Click or press Esc to pop back to Overview ←"),
                    ]
                    return "\n".join(lines)
            self.nav_stack.push("Database", DatabaseTier())
            self.status_msg = "Drilled down into Database Shards"
            _, toast_cmd = self.toast_manager.add("NavStack: Pushed Database", ToastLevel.SUCCESS, duration=2.0)
            return self, toast_cmd
        else:
            self.nav_stack.pop()
            self.status_msg = "Popped NavStack to parent"
            _, toast_cmd = self.toast_manager.add("NavStack: Popped back", ToastLevel.INFO, duration=2.0)
            return self, toast_cmd

    def update(self, msg: Msg) -> tuple[ComponentGallery, Cmd | None]:
        cmds: list[Cmd] = []

        # Terminal Resize
        if isinstance(msg, WindowSizeMsg):
            self.width = max(70, msg.width)
            self.height = max(20, msg.height)
            self._sync_child_dimensions()
            return self, None

        # Mouse Events
        if isinstance(msg, MouseMsg):
            return self._handle_mouse(msg)

        # Toast Dismissal
        if isinstance(msg, ToastDismissMsg):
            self.toast_manager, t_cmd = self.toast_manager.update(msg)
            if t_cmd:
                cmds.append(t_cmd)
            return self, None

        # Modal Dialog takes priority if visible
        if self.show_dialog:
            if isinstance(msg, KeyMsg):
                self.dialog, d_cmd = self.dialog.update(msg)
                if d_cmd:
                    res_msg = d_cmd()
                    if isinstance(res_msg, DialogResultMsg):
                        self.show_dialog = False
                        if res_msg.action == "Deploy Now":
                            self.status_msg = "Deployment sequence initiated!"
                            _, toast_cmd = self.toast_manager.add(
                                "🚀 Deployment sequence initiated!",
                                ToastLevel.SUCCESS,
                                duration=4.0,
                            )
                            cmds.append(toast_cmd)
                        else:
                            self.status_msg = "Deployment cancelled."
                            _, toast_cmd = self.toast_manager.add(
                                "Action cancelled.",
                                ToastLevel.WARNING,
                                duration=2.5,
                            )
                            cmds.append(toast_cmd)
                return self, None

        # Global Hotkeys
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app
                case "d":
                    self.show_dialog = True
                    return self, None
                case "m":
                    self.mouse_enabled = not self.mouse_enabled
                    if self.mouse_enabled:
                        self.status_msg = "Mouse tracking enabled (SGR 1006)"
                        _, toast_cmd = self.toast_manager.add(
                            "🖱 Mouse tracking enabled",
                            ToastLevel.INFO,
                            duration=2.5,
                        )
                        return self, batch(enable_mouse(), toast_cmd)
                    else:
                        self.status_msg = "Mouse tracking disabled"
                        _, toast_cmd = self.toast_manager.add(
                            "🚫 Mouse tracking disabled",
                            ToastLevel.WARNING,
                            duration=2.5,
                        )
                        return self, batch(disable_mouse(), toast_cmd)
                case "t":
                    samples = [
                        ("Build completed successfully in 1.42s", ToastLevel.SUCCESS),
                        ("High memory utilization detected (82%)", ToastLevel.WARNING),
                        ("Database replica connected (cluster-eu-west)", ToastLevel.INFO),
                        ("Failed to reach registry endpoint", ToastLevel.ERROR),
                    ]
                    text, lvl = random.choice(samples)
                    self.status_msg = text
                    _, toast_cmd = self.toast_manager.add(text, lvl, duration=3.0)
                    cmds.append(toast_cmd)
                    return self, toast_cmd
                case "tab":
                    next_tab = (self.tabs.active_tab + 1) % len(self.tabs.titles)
                    self.tabs, _ = self.tabs.update(KeyMsg(str(next_tab + 1)))
                    return self, None
                case "shift+tab":
                    prev_tab = (self.tabs.active_tab - 1) % len(self.tabs.titles)
                    self.tabs, _ = self.tabs.update(KeyMsg(str(prev_tab + 1)))
                    return self, None
                case "1" | "2" | "3" | "4" | "5" | "6":
                    self.tabs, _ = self.tabs.update(msg)
                    return self, None
                case "p":
                    if self.tabs.active_tab == 4:
                        return self._cycle_navstack()
                case "b":
                    if self.tabs.active_tab == 4 and self.nav_stack.depth > 1:
                        self.nav_stack.pop()
                        return self, None
                case "l":
                    if self.tabs.active_tab == 4:
                        layouts = [MetricLayout.CARD, MetricLayout.TAG, MetricLayout.LIST]
                        next_idx = (layouts.index(self.metrics.layout) + 1) % len(layouts)
                        self.metrics.layout = layouts[next_idx]
                        return self, None

        # Delegate to active tab
        curr_tab = self.tabs.active_tab

        if curr_tab == 0:
            # Tab 0: Filterable List
            if isinstance(msg, KeyMsg) and not self.list.filtering:
                if msg.key == "n":
                    if not self.list.show_numbers and not self.list.relative_numbers:
                        self.list.show_numbers = True
                        self.list.relative_numbers = False
                        mode_name = "Absolute"
                    elif self.list.show_numbers and not self.list.relative_numbers:
                        self.list.show_numbers = True
                        self.list.relative_numbers = True
                        mode_name = "Vim Relative"
                    else:
                        self.list.show_numbers = False
                        self.list.relative_numbers = False
                        mode_name = "Off"
                    self.status_msg = f"List numbering: {mode_name}"
                    _, toast_cmd = self.toast_manager.add(f"Numbering: {mode_name}", ToastLevel.INFO, duration=2.0)
                    return self, toast_cmd
                elif msg.key == "s":
                    if self.list.pagination_mode == PaginationMode.PAGINATED:
                        self.list.pagination_mode = PaginationMode.SCROLL
                        mode_name = "Continuous Scroll"
                    else:
                        self.list.pagination_mode = PaginationMode.PAGINATED
                        mode_name = "Paginated"
                    self.list._sync_scroll()
                    self.status_msg = f"List mode: {mode_name}"
                    _, toast_cmd = self.toast_manager.add(f"List: {mode_name}", ToastLevel.INFO, duration=2.0)
                    return self, toast_cmd
                elif msg.key == "x":
                    self.list.show_tree_guides = not self.list.show_tree_guides
                    g_name = "ON" if self.list.show_tree_guides else "OFF"
                    self.status_msg = f"Tree guides: {g_name}"
                    _, toast_cmd = self.toast_manager.add(f"Tree Guides: {g_name}", ToastLevel.INFO, duration=2.0)
                    return self, toast_cmd

            self.list, list_cmd = self.list.update(msg)
            if list_cmd:
                sub_msg = list_cmd()
                if isinstance(sub_msg, ListSelectMsg):
                    self.selected_item = sub_msg.item
                    self.status_msg = f"Inspecting: {sub_msg.item.title}"
                    _, toast_cmd = self.toast_manager.add(
                        f"Selected: {sub_msg.item.title}",
                        ToastLevel.SUCCESS,
                        duration=2.5,
                    )
                    cmds.append(toast_cmd)
            return self, cmds[0] if cmds else None

        elif curr_tab == 1:
            # Tab 1: FilePicker
            self.file_picker, fp_cmd = self.file_picker.update(msg)
            if fp_cmd:
                sub_msg = fp_cmd()
                if isinstance(sub_msg, FileSelectMsg):
                    kind = "Directory" if sub_msg.is_dir else "File"
                    self.selected_file_str = f"{sub_msg.path.name} ({kind})"
                    self.status_msg = f"Browsing: {sub_msg.path.name}"
                    _, toast_cmd = self.toast_manager.add(
                        f"Picked {sub_msg.path.name} ({kind})",
                        ToastLevel.INFO,
                        duration=2.5,
                    )
                    cmds.append(toast_cmd)
            return self, cmds[0] if cmds else None

        elif curr_tab == 2:
            # Tab 2: CLI Prompts & DatePicker
            if isinstance(msg, KeyMsg) and msg.key in ("pgup", "pgdown"):
                if msg.key == "pgdown":
                    self.active_prompt_idx = (self.active_prompt_idx + 1) % 4
                else:
                    self.active_prompt_idx = (self.active_prompt_idx - 1) % 4
                return self, None

            if self.active_prompt_idx == 0:
                self.select_prompt, p_cmd = self.select_prompt.update(msg)
                if p_cmd:
                    sub_msg = p_cmd()
                    if isinstance(sub_msg, SelectSubmitMsg):
                        self.status_msg = f"Target selected: {sub_msg.selected}"
                        _, toast_cmd = self.toast_manager.add(
                            f"Target: {sub_msg.selected}",
                            ToastLevel.SUCCESS,
                            duration=3.0,
                        )
                        cmds.append(toast_cmd)
                        self.active_prompt_idx = 1
            elif self.active_prompt_idx == 1:
                self.multiselect_prompt, p_cmd = self.multiselect_prompt.update(msg)
                if p_cmd:
                    sub_msg = p_cmd()
                    if isinstance(sub_msg, MultiSelectSubmitMsg):
                        self.status_msg = f"Enabled {len(sub_msg.selected)} build pipelines"
                        _, toast_cmd = self.toast_manager.add(
                            f"Pipelines: {len(sub_msg.selected)} active",
                            ToastLevel.INFO,
                            duration=3.0,
                        )
                        cmds.append(toast_cmd)
                        self.active_prompt_idx = 2
            elif self.active_prompt_idx == 2:
                self.confirm_prompt, p_cmd = self.confirm_prompt.update(msg)
                if p_cmd:
                    sub_msg = p_cmd()
                    if isinstance(sub_msg, ConfirmSubmitMsg):
                        lvl = ToastLevel.SUCCESS if sub_msg.confirmed else ToastLevel.WARNING
                        status_str = "Confirmed! Proceeding..." if sub_msg.confirmed else "Deployment cancelled."
                        self.status_msg = status_str
                        _, toast_cmd = self.toast_manager.add(status_str, lvl, duration=3.0)
                        cmds.append(toast_cmd)
                        if sub_msg.confirmed:
                            self.active_prompt_idx = 3
            elif self.active_prompt_idx == 3:
                self.datepicker, p_cmd = self.datepicker.update(msg)
                if p_cmd:
                    sub_msg = p_cmd()
                    if isinstance(sub_msg, DateSelectMsg):
                        self.status_msg = f"Scheduled date: {sub_msg.date.strftime('%Y-%m-%d')}"
                        _, toast_cmd = self.toast_manager.add(
                            f"📅 Scheduled: {sub_msg.date.strftime('%B %d, %Y')}",
                            ToastLevel.SUCCESS,
                            duration=3.5,
                        )
                        cmds.append(toast_cmd)
                    elif isinstance(sub_msg, DateChangeMsg):
                        self.status_msg = f"Browsing calendar: {sub_msg.date.strftime('%B %Y')}"

            return self, cmds[0] if cmds else None

        elif curr_tab == 3:
            # Tab 3: Tree View
            self.tree, t_cmd = self.tree.update(msg)
            if t_cmd:
                sub_msg = t_cmd()
                if isinstance(sub_msg, TreeNodeSelectMsg):
                    self.selected_node_label = sub_msg.node.label
                    self.status_msg = f"Inspecting node: {sub_msg.node.label}"
                    _, toast_cmd = self.toast_manager.add(
                        f"Selected: {sub_msg.node.label}",
                        ToastLevel.INFO,
                        duration=2.5,
                    )
                    cmds.append(toast_cmd)
            return self, cmds[0] if cmds else None

        elif curr_tab == 4:
            # Tab 4: NavStack event delegation
            self.nav_stack, ns_cmd = self.nav_stack.update(msg)
            return self, ns_cmd

        elif curr_tab == 5:
            # Tab 5: Pipelines, DetailSelector, and ImageViewer
            cmds: list[Cmd] = []
            if isinstance(msg, KeyMsg):
                if msg.key == "a":
                    new_mode = RenderMode.ASCII if self.image_viewer.mode == RenderMode.HALF_BLOCK else RenderMode.HALF_BLOCK
                    self.image_viewer.mode = new_mode
                    self.image_viewer._rebuild_rendered()
                    self.status_msg = f"ImageViewer render mode: {new_mode.value.upper()}"
                    return self, None
                elif msg.key == "n":
                    advanced = False
                    for idx, s in enumerate(self.pipeline.stages):
                        if s.status == StageStatus.RUNNING:
                            s.status = StageStatus.SUCCESS
                            s.duration = round(random.uniform(0.4, 1.8), 2)
                            if idx + 1 < len(self.pipeline.stages):
                                self.pipeline.stages[idx + 1].status = StageStatus.RUNNING
                                self.status_msg = f"Started: {self.pipeline.stages[idx + 1].title}"
                            else:
                                self.pipeline.is_finished = True
                                self.status_msg = "Pipeline complete! All stages succeeded."
                                _, toast_cmd = self.toast_manager.add(
                                    "🚀 Pipeline build & deploy succeeded!",
                                    ToastLevel.SUCCESS,
                                    duration=3.0,
                                )
                                cmds.append(toast_cmd)
                            advanced = True
                            break
                        elif s.status == StageStatus.PENDING:
                            s.status = StageStatus.RUNNING
                            self.status_msg = f"Started: {s.title}"
                            advanced = True
                            break
                    if not advanced and self.pipeline.is_finished:
                        self.status_msg = "Pipeline already finished. Press 'r' to reset."
                    return self, cmds[0] if cmds else None
                elif msg.key == "r":
                    for idx, s in enumerate(self.pipeline.stages):
                        s.status = StageStatus.PENDING if idx > 0 else StageStatus.RUNNING
                    self.pipeline.is_finished = False
                    self.pipeline.is_failed = False
                    self.status_msg = "Pipeline reset to initial stage"
                    return self, None

            # Delegate to DetailSelector
            self.detail_selector, d_cmd = self.detail_selector.update(msg)
            if d_cmd:
                sub_msg = d_cmd()
                if isinstance(sub_msg, DetailSelectMsg):
                    self.status_msg = f"Selected: {sub_msg.item.title}"
                    _, toast_cmd = self.toast_manager.add(
                        f"Selected: {sub_msg.item.title} ({sub_msg.item.tag})",
                        ToastLevel.INFO,
                        duration=2.5,
                    )
                    cmds.append(toast_cmd)

            # Delegate to ImageViewer for scrolling
            self.image_viewer, i_cmd = self.image_viewer.update(msg)
            return self, cmds[0] if cmds else None

        return self, None

    def _render_tab_panels(self, content_h: int, w_left: int, w_right: int) -> tuple[str, str]:
        curr_tab = self.tabs.active_tab

        if curr_tab == 0:
            # Tab 0: List & Inspector
            list_content = self.list.view()
            p_left = make_panel("📦 Component Catalog", list_content, w_left, content_h, border_fg="#7D56F4")

            item = self.selected_item
            mode_badge = "SCROLL" if self.list.pagination_mode == PaginationMode.SCROLL else "PAGINATED"
            num_badge = "VIM RELATIVE" if self.list.relative_numbers else ("ABSOLUTE" if self.list.show_numbers else "OFF")
            guide_badge = "ON" if self.list.show_tree_guides else "OFF"
            item_badge = item.badge if (item and item.badge) else "NONE"

            inspector_lines = [
                f"{Style().bold(True).foreground('#00E5FF').render(item.title if item else 'None')}  {Style().foreground('#00E676').bold(True).render(f'[{item_badge}]') if item and item.badge else ''}",
                f"{Style().foreground('#D0D0D0').render(item.description if item else '')}",
                "",
                f"{Style().foreground('#8888AA').render('Category:')} {Style().bold(True).foreground('#FFD54F').render(str(item.value).upper() if item else 'NONE')}   {Style().foreground('#8888AA').render('Mode:')} {Style().bold(True).foreground('#29B6F6').render(mode_badge)}",
                f"{Style().foreground('#8888AA').render('Numbers:')} {Style().bold(True).foreground('#AB47BC').render(num_badge)}   {Style().foreground('#8888AA').render('Tree Guides:')} {Style().bold(True).foreground('#26A69A').render(guide_badge)}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Code Usage:')}",
                f"{Style().foreground('#666688').render('----------------------------------------')}",
                f"{Style().foreground('#A0FFA0').render('from espresso.beans import List, ListItem, PaginationMode')}",
                "",
                Style().foreground('#E0E0E0').render('items = [ListItem("Build", "Compile", badge="CI/CD")]'),
                f"{Style().foreground('#E0E0E0').render('lst = List(items, pagination_mode=PaginationMode.SCROLL)')}",
                f"{Style().foreground('#666688').render('----------------------------------------')}",
                "",
                f"{Style().bold(True).foreground('#FFA726').render('Controls & Toggles:')}",
                f"• {Style().foreground('#00E676').render('↑ / ↓ or j / k')}: Navigate items",
                f"• {Style().foreground('#00E676').render('s')}: Toggle scroll mode ({mode_badge})",
                f"• {Style().foreground('#00E676').render('n')}: Toggle numbering ({num_badge})",
                f"• {Style().foreground('#00E676').render('x')}: Toggle tree guides ({guide_badge})",
                f"• {Style().foreground('#00E676').render('/')}: Filter • {Style().foreground('#00E676').render('Enter')}: Select",
                f"• {Style().foreground('#00E676').render('Mouse')}: Click row to select, wheel to scroll",
            ]
            p_right = make_panel("🔍 Item Inspector", "\n".join(inspector_lines), w_right, content_h, border_fg="#00E5FF")
            return p_left, p_right

        elif curr_tab == 1:
            # Tab 1: FilePicker & Details
            fp_content = self.file_picker.view()
            p_left = make_panel("📁 Filesystem Explorer", fp_content, w_left, content_h, border_fg="#FF9100")

            entry = self.file_picker.selected_entry
            entry_name = entry.name if entry else "None"
            entry_type = "Directory" if (entry and entry.is_dir) else "Regular File"
            entry_size = f"{entry.size} bytes" if (entry and not entry.is_dir) else "N/A"
            curr_dir = str(self.file_picker.current_path)

            file_lines = [
                f"{Style().bold(True).foreground('#FFA726').render(entry_name)}",
                f"{Style().foreground('#8888AA').render('Type:')} {Style().foreground('#FAFAFA').render(entry_type)}",
                f"{Style().foreground('#8888AA').render('Size:')} {Style().foreground('#00E676').render(entry_size)}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Current Folder:')}",
                f"{Style().foreground('#00E5FF').render(truncate_ansi(curr_dir, w_right - 6))}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('FilePicker Features:')}",
                f"• {Style().foreground('#66BB6A').render('Human-readable sizes')} (KB, MB, GB)",
                f"• {Style().foreground('#66BB6A').render('Icons')} for folders (📁) and files (📄)",
                f"• {Style().foreground('#66BB6A').render('Hidden file filter')} toggleable with '.'",
                "",
                f"{Style().bold(True).foreground('#FFA726').render('Shortcuts:')}",
                f"• {Style().foreground('#00E676').render('↑ / ↓')}: Move selection cursor",
                f"• {Style().foreground('#00E676').render('Enter')}: Open folder / Pick file",
                f"• {Style().foreground('#00E676').render('Backspace / h')}: Go up to parent (..)",
                f"• {Style().foreground('#00E676').render('.')}: Toggle hidden files",
            ]
            p_right = make_panel("📄 File Details & Actions", "\n".join(file_lines), w_right, content_h, border_fg="#FFA726")
            return p_left, p_right

        elif curr_tab == 2:
            # Tab 2: CLI Prompts & Summary
            p0 = self.select_prompt.view()
            p1 = self.multiselect_prompt.view()
            p2 = self.confirm_prompt.view()

            card0 = Style().border(ROUNDED_BORDER).border_foreground("#00E5FF" if self.active_prompt_idx == 0 else "#33334A").render(p0)
            card1 = Style().border(ROUNDED_BORDER).border_foreground("#00E5FF" if self.active_prompt_idx == 1 else "#33334A").render(p1)
            card2 = Style().border(ROUNDED_BORDER).border_foreground("#00E5FF" if self.active_prompt_idx == 2 else "#33334A").render(p2)

            prompts_joined = join_vertical(Align.LEFT, card0, card1, card2)
            p_left = make_panel("⚡ Interactive CLI Prompts", prompts_joined, w_left, content_h, border_fg="#E040FB")

            sel_opt = self.select_prompt.options[self.select_prompt.cursor]
            multi_cnt = len(self.multiselect_prompt.selected_indices)
            conf_val = "Yes (Confirmed)" if self.confirm_prompt.value else "No (Declined)"
            sched_val = self.datepicker.value.strftime("%Y-%m-%d") if self.datepicker.value else "None"

            # Highlight datepicker border when active_prompt_idx == 3
            self.datepicker.border_foreground = "#00E5FF" if self.active_prompt_idx == 3 else "#33334A"

            summary_lines = [
                f"{Style().bold(True).foreground('#E040FB').render('Configuration State')}",
                f"{Style().foreground('#8888AA').render('Target Host:')} {Style().bold(True).foreground('#00E5FF').render(str(sel_opt))}",
                f"{Style().foreground('#8888AA').render('Pipelines:')} {Style().bold(True).foreground('#00E676').render(f'{multi_cnt} selected')}   {Style().foreground('#8888AA').render('Deploy Flag:')} {Style().bold(True).foreground('#FFD54F').render(conf_val)}",
                f"{Style().foreground('#8888AA').render('Scheduled Date:')} {Style().bold(True).foreground('#00E676').render(sched_val)}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('📅 DatePicker (bubble-datepicker):')}",
                self.datepicker.view(),
                "",
                f"{Style().bold(True).foreground('#FFA726').render('Navigation & Hotkeys:')}",
                f"• {Style().foreground('#00E676').render('PgUp / PgDn')}: Switch focus (Prompts 1-3 ⇄ DatePicker)",
                f"• {Style().foreground('#00E676').render('Arrows / hjkl')}: Move cursor / dates",
                f"• {Style().foreground('#00E676').render('Tab')}: In calendar, focus Month / Year",
                f"• {Style().foreground('#00E676').render('Enter')}: Submit choice / Pick date",
                f"• {Style().foreground('#00E676').render('Mouse')}: Click dates or ◀/▶ arrows directly",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Active Focus:')} " + (
                    f"Prompt #{self.active_prompt_idx + 1}" if self.active_prompt_idx < 3 else "📅 DatePicker Calendar"
                ),
            ]
            p_right = make_panel("📊 Configuration & Scheduling", "\n".join(summary_lines), w_right, content_h, border_fg="#7C4DFF")
            return p_left, p_right

        elif curr_tab == 3:
            # Tab 3: Tree View & Node Inspector
            tree_content = self.tree.view()
            p_left = make_panel("🌳 Project Codebase Tree", tree_content, w_left, content_h, border_fg="#00E676")

            node = self.tree.selected_node
            label = node.label if node else "None"
            is_dir = "Directory / Package" if (node and not node.is_leaf) else "Module / File"
            child_cnt = len(node.children) if (node and not node.is_leaf) else 0

            tree_lines = [
                f"{Style().bold(True).foreground('#00E676').render(label)}",
                f"{Style().foreground('#8888AA').render('Node Type:')} {Style().foreground('#FAFAFA').render(is_dir)}",
                f"{Style().foreground('#8888AA').render('Child Nodes:')} {Style().bold(True).foreground('#00E5FF').render(str(child_cnt))}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Tree Features:')}",
                f"• {Style().foreground('#66BB6A').render('Collapsible & expandable')} hierarchy",
                f"• {Style().foreground('#66BB6A').render('Unicode branch lines')} (├──, └──, │)",
                f"• {Style().foreground('#66BB6A').render('Parent jump')} on Left arrow",
                "",
                f"{Style().bold(True).foreground('#FFA726').render('Tree Controls:')}",
                f"• {Style().foreground('#00E676').render('↑ / ↓ or j / k')}: Navigate tree items",
                f"• {Style().foreground('#00E676').render('Space / →')}: Expand / collapse folder",
                f"• {Style().foreground('#00E676').render('← / h')}: Collapse folder / Jump to parent",
                f"• {Style().foreground('#00E676').render('Enter')}: Select node & inspect",
            ]
            p_right = make_panel("🌿 Node Inspector", "\n".join(tree_lines), w_right, content_h, border_fg="#69F0AE")
            return p_left, p_right

        elif curr_tab == 4:
            # Tab 4: Stickers FlexBox & Metrics & BubbleO NavStack & Teacup StatusBar
            inner_w_left = max(10, w_left - 4)
            inner_h = max(4, content_h - 2)

            # Left Panel: Responsive FlexBox Grid with Metric Cards & Tags
            fb = FlexBox(width=inner_w_left, height=inner_h)
            r1 = fb.new_row(ratio_y=4)
            r1.new_cell(
                content=lambda w, h: self.metrics.view(),
                ratio_x=1,
            )
            r2 = fb.new_row(ratio_y=1)
            hint_box = Style().foreground("#8888AA").render("💡 Click or press 'l' to toggle Metric layout (Card/Tag/List)\n💡 Press 'p' to push view, 'b' or Esc to pop NavStack")
            r2.new_cell(content=hint_box, ratio_x=1)

            p_left = make_panel("📊 Stickers FlexBox & Metrics", fb.render(), w_left, content_h, border_fg="#00E5FF")

            # Right Panel: NavStack Breadcrumbs + View + Teacup StatusBar
            nav_view = self.nav_stack.view()
            sb_str = self.statusbar.set_width(w_right - 4).view()
            p_right_content = join_vertical(Align.LEFT, nav_view, "", sb_str)
            p_right = make_panel("🧭 BubbleO NavStack & Teacup StatusBar", p_right_content, w_right, content_h, border_fg="#7D56F4")
            return p_left, p_right

        elif curr_tab == 5:
            # Tab 5: Pipelines, DetailSelector, and ImageViewer
            pipeline_view = self.pipeline.view()
            selector_view = self.detail_selector.view()
            p_left_content = join_vertical(Align.LEFT, pipeline_view, "", selector_view)
            p_left = make_panel("🚀 CI/CD Pipeline & DetailSelector", p_left_content, w_left, content_h, border_fg="#00E676")

            # Right panel: ImageViewer + Info
            img_view = self.image_viewer.view()
            mode_badge = "24-BIT HALF-BLOCK" if self.image_viewer.mode == RenderMode.HALF_BLOCK else "ASCII DENSITY"
            info_lines = [
                img_view,
                "",
                f"{Style().bold(True).foreground('#FFA726').render('Terminal Graphics (ImageViewer):')}",
                f"{Style().foreground('#8888AA').render('Renderer:')} {Style().bold(True).foreground('#00E5FF').render(mode_badge)}",
                f"{Style().foreground('#8888AA').render('Formats:')} {Style().foreground('#00E676').render('Netpbm PPM, 24-bit BMP, RGB matrix, Pillow bridge')}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Hotkeys & Navigation:')}",
                f"• {Style().foreground('#00E676').render('a')}: Toggle 24-bit Half-block (▀) ⇄ ASCII ramp",
                f"• {Style().foreground('#00E676').render('n')}: Advance Pipeline stage",
                f"• {Style().foreground('#00E676').render('r')}: Reset Pipeline execution",
                f"• {Style().foreground('#00E676').render('↑ / ↓ or j / k')}: Navigate DetailSelector items",
                f"• {Style().foreground('#00E676').render('Enter')}: Select DetailItem",
            ]
            p_right = make_panel("🖼️ ANSI Half-Block ImageViewer", "\n".join(info_lines), w_right, content_h, border_fg="#FF4081")
            return p_left, p_right

        return "", ""

    def _render_header(self, total_w: int) -> str:
        title_badge = (
            Style()
            .bold(True)
            .foreground("#FFFFFF")
            .background("#7D56F4")
            .padding(0, 2)
            .render("☕ ESPRESSO BEANS GALLERY")
        )
        tabs_str = self.tabs.view()
        left_part = f"{title_badge}  {tabs_str}"
        left_w = string_width(left_part)

        dim_badge = Style().foreground("#777799").render(f"[{total_w}x{self.height}] ")
        dim_w = string_width(dim_badge)

        spacing = max(1, total_w - left_w - dim_w)
        header_line = f"{left_part}{' ' * spacing}{dim_badge}"
        return Style().background("#1A1A28").render(truncate_ansi(header_line, total_w))

    def _render_footer(self, total_w: int) -> str:
        tab_names = ["LIST & PAGINATOR", "FILESYSTEM PICKER", "CLI PROMPTS", "CODEBASE TREE", "FLEXBOX & KPIS", "PIPELINES & MEDIA"]
        active_name = tab_names[self.tabs.active_tab]
        tab_badge = (
            Style()
            .bold(True)
            .foreground("#000000")
            .background("#00E676")
            .padding(0, 1)
            .render(f" TAB {self.tabs.active_tab + 1}/6: {active_name} ")
        )

        if self.toast_manager.has_toasts:
            latest_toast = self.toast_manager.toasts[-1]
            lvl_icons = {"success": "✔", "error": "✖", "warning": "⚠", "info": "ℹ"}
            icon = lvl_icons.get(latest_toast.level.value, "ℹ")
            status_text = f" {icon} {latest_toast.message} "
            status_part = Style().bold(True).foreground("#FFD54F").background("#2E2000").render(status_text)
        else:
            status_part = Style().foreground("#9999BB").render(f" {self.status_msg}")

        mouse_badge = (
            Style().bold(True).foreground("#00E676").render("[m] MOUSE: ON")
            if self.mouse_enabled
            else Style().foreground("#666688").render("[m] MOUSE: OFF")
        )

        hints = (
            f"{Style().bold(True).foreground('#00E5FF').render('[Tab]')} Next  "
            f"{Style().bold(True).foreground('#00E5FF').render('[d]')} Dialog  "
            f"{Style().bold(True).foreground('#00E5FF').render('[t]')} Toast  "
            f"{mouse_badge}  "
            f"{Style().bold(True).foreground('#FF5252').render('[q]')} Quit "
        )

        left_str = f"{tab_badge} {status_part}"
        left_w = string_width(left_str)
        hints_w = string_width(hints)

        spacing = max(1, total_w - left_w - hints_w)
        footer_line = f"{left_str}{' ' * spacing}{hints}"
        return Style().background("#14141E").render(truncate_ansi(footer_line, total_w))

    def view(self) -> str:
        total_w = self.width
        total_h = self.height
        content_h, w_left, w_right = self._calc_layout()

        # 1. Header (1 line)
        header = self._render_header(total_w)

        # 2. Main 2-Panel Content (content_h lines)
        p_left, p_right = self._render_tab_panels(content_h, w_left, w_right)
        panels_row = join_horizontal(Align.TOP, p_left, p_right)

        # 3. Footer Bar (1 line)
        footer = self._render_footer(total_w)

        base_view = join_vertical(Align.LEFT, header, panels_row, footer)

        # 4. Floating Modal Overlay if active
        if self.show_dialog:
            dialog_view = self.dialog.view()
            return place_overlay(base_view, dialog_view, center=True, dim_backdrop=True)

        return base_view


def main() -> None:
    app = ComponentGallery()
    prog = Program(app, alt_screen=True, mouse=True)
    prog.run()


if __name__ == "__main__":
    main()
