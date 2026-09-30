#!/usr/bin/env python3
"""Example 10: Full-Window Beans Component Gallery.

Interactive showcase demonstrating the full suite of newly added components
in a responsive, edge-to-edge full-window terminal layout:
1. Tabs: Top tab navigation bar with hotkeys (1-4, Tab / Shift-Tab)
2. List & Paginator: Filterable list with search (/) and live pagination
3. FilePicker: Interactive filesystem browser with file sizes and hidden file toggle (.)
4. Prompts: SelectPrompt, MultiSelectPrompt (checkboxes), and ConfirmPrompt
5. Tree: Collapsible hierarchical directory tree
6. Dialog & 2D Overlay: Modal card composited on top with backdrop dimming (press 'd')
7. ToastManager: Transient auto-dismissing toast notifications (press 't')
"""

from __future__ import annotations

import random
import shutil
import sys
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
    Dialog,
    DialogResultMsg,
    FilePicker,
    FileSelectMsg,
    List,
    ListItem,
    ListSelectMsg,
    MultiSelectPrompt,
    MultiSelectSubmitMsg,
    SelectPrompt,
    SelectSubmitMsg,
    TabStyle,
    Tabs,
    ToastDismissMsg,
    ToastLevel,
    ToastManager,
    Tree,
    TreeNode,
    TreeNodeSelectMsg,
    LayoutDirection,
    Metric,
    MetricGroup,
    MetricLayout,
    MetricTrend,
    NavStack,
    StatusBar,
    StatusSection,
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
            titles=["Filterable List", "File Picker", "CLI Prompts", "Tree View", "FlexBox & KPIs"],
            active_tab=0,
            tab_style=TabStyle.PILL,
            show_numbers=True,
        )

        # --- Component 2: List & Paginator ---
        list_items = [
            ListItem("Espresso TEA", "Lightweight Pure Python TUI Framework", "framework"),
            ListItem("Crema Style Engine", "Declarative styling, borders, and gradients", "styling"),
            ListItem("Beans Components", "Standard library of reusable UI widgets", "widgets"),
            ListItem("Terminal Parser", "ANSI escape codes and mouse tracking", "terminal"),
            ListItem("Overlay Compositor", "2D layer compositing with backdrop dimming", "overlay"),
            ListItem("Paginator", "Dots, numeric, and compact pagination indicators", "paginator"),
            ListItem("FilePicker", "Interactive directory browser with file size formats", "filesystem"),
            ListItem("Dialog & Modal", "Card dialog with action buttons and keyboard focus", "dialog"),
            ListItem("Interactive Prompts", "Select, MultiSelect checkboxes, and Confirm prompts", "prompts"),
            ListItem("Collapsible Tree", "Hierarchical tree view with branch guides", "tree"),
            ListItem("Toast Notifications", "Auto-dismissing asynchronous alerts", "toast"),
            ListItem("Line Diffing Buffer", "Zero-flicker double buffered screen redraw", "renderer"),
            ListItem("SGR Mouse Protocol", "Mouse clicks, dragging, and wheel scrolling", "mouse"),
            ListItem("Adaptive Colors", "Light/Dark background detection & NO_COLOR", "color"),
            ListItem("Responsive FlexBox", "Stickers-inspired 2D proportional grid with ratios", "layout"),
            ListItem("Multi-Section StatusBar", "Teacup-inspired responsive header/footer bar", "statusbar"),
            ListItem("KPI Metric Cards", "OrtizAlec-inspired stat cards with trend arrows", "metric"),
            ListItem("NavStack & Breadcrumbs", "BubbleO-inspired view stack with breadcrumb trail", "navstack"),
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
        self.active_prompt_idx = 0  # 0: select, 1: multi, 2: confirm

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
        content_h, w_left, _ = self._calc_layout()
        inner_w_left = max(10, w_left - 4)
        inner_h = max(4, content_h - 2)

        # Update List dimensions
        self.list.width = inner_w_left
        self.list.per_page = max(2, (inner_h - 5) // 2)
        self.list.paginator.per_page = self.list.per_page
        self.list.paginator.set_total(len(self.list.filtered_items))

        # Update FilePicker dimensions
        self.file_picker.width = inner_w_left
        self.file_picker.height = inner_h - 2

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
                if msg.y == 2:
                    return self.update(KeyMsg("/"))
                elif msg.y >= 3:
                    item_idx_on_page = (msg.y - 3) // 2
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
                if msg.y >= 3:
                    entry_idx_on_screen = msg.y - 3
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
                # Tab 2: CLI Prompts
                if msg.y <= 7:
                    self.active_prompt_idx = 0
                    opt_idx = msg.y - 3
                    if 0 <= opt_idx < len(self.select_prompt.options):
                        self.select_prompt.cursor = opt_idx
                        return self.update(KeyMsg("enter"))
                elif msg.y <= 15:
                    self.active_prompt_idx = 1
                    opt_idx = msg.y - 10
                    if 0 <= opt_idx < len(self.multiselect_prompt.options):
                        self.multiselect_prompt.cursor = opt_idx
                        return self.update(KeyMsg(" "))
                else:
                    self.active_prompt_idx = 2
                    if msg.x < w_left // 2:
                        return self.update(KeyMsg("y"))
                    else:
                        return self.update(KeyMsg("n"))

            elif curr_tab == 3:
                # Tab 3: Tree View
                if msg.y >= 3:
                    node_idx = msg.y - 3
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
                case "1" | "2" | "3" | "4" | "5":
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
            # Tab 2: CLI Prompts
            if isinstance(msg, KeyMsg) and msg.key in ("pgup", "pgdown"):
                if msg.key == "pgdown":
                    self.active_prompt_idx = (self.active_prompt_idx + 1) % 3
                else:
                    self.active_prompt_idx = (self.active_prompt_idx - 1) % 3
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

        return self, None

    def _render_tab_panels(self, content_h: int, w_left: int, w_right: int) -> tuple[str, str]:
        curr_tab = self.tabs.active_tab

        if curr_tab == 0:
            # Tab 0: List & Inspector
            list_content = self.list.view()
            p_left = make_panel("📦 Component Catalog", list_content, w_left, content_h, border_fg="#7D56F4")

            item = self.selected_item
            inspector_lines = [
                f"{Style().bold(True).foreground('#00E5FF').render(item.title)}",
                f"{Style().foreground('#D0D0D0').render(item.description)}",
                "",
                f"{Style().foreground('#8888AA').render('Category:')} {Style().bold(True).foreground('#FFD54F').render(str(item.value).upper())}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Code Usage:')}",
                f"{Style().foreground('#666688').render('----------------------------------------')}",
                f"{Style().foreground('#A0FFA0').render('from espresso.beans import List, ListItem')}",
                "",
                f"{Style().foreground('#E0E0E0').render('items = [ListItem(\"Title\", \"Desc\")]')}",
                f"{Style().foreground('#E0E0E0').render('catalog = List(items, per_page=6)')}",
                f"{Style().foreground('#666688').render('----------------------------------------')}",
                "",
                f"{Style().bold(True).foreground('#FFA726').render('Keyboard Controls:')}",
                f"• {Style().foreground('#00E676').render('↑ / ↓ or j / k')}: Navigate items",
                f"• {Style().foreground('#00E676').render('/')}: Live fuzzy search / filter",
                f"• {Style().foreground('#00E676').render('Enter')}: Select & inspect item",
                f"• {Style().foreground('#00E676').render('Esc')}: Clear search query",
                f"• {Style().foreground('#00E676').render('PgUp / PgDn')}: Jump page",
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

            summary_lines = [
                f"{Style().bold(True).foreground('#E040FB').render('Configuration State')}",
                "",
                f"{Style().foreground('#8888AA').render('Target Host:')} {Style().bold(True).foreground('#00E5FF').render(str(sel_opt))}",
                f"{Style().foreground('#8888AA').render('Pipelines:')} {Style().bold(True).foreground('#00E676').render(f'{multi_cnt} selected')}",
                f"{Style().foreground('#8888AA').render('Deploy Flag:')} {Style().bold(True).foreground('#FFD54F').render(conf_val)}",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Prompt Navigation:')}",
                f"• {Style().foreground('#00E676').render('PgUp / PgDn')}: Switch active prompt card",
                f"• {Style().foreground('#00E676').render('↑ / ↓ or j / k')}: Navigate choices",
                f"• {Style().foreground('#00E676').render('Space')}: Toggle checkbox",
                f"• {Style().foreground('#00E676').render('a')}: Select all / Deselect all",
                f"• {Style().foreground('#00E676').render('y / n')}: Fast confirm answer",
                f"• {Style().foreground('#00E676').render('Enter')}: Submit selection",
                "",
                f"{Style().bold(True).foreground('#FAFAFA').render('Active Focus:')} Prompt #{self.active_prompt_idx + 1}",
            ]
            p_right = make_panel("📊 Configuration Summary", "\n".join(summary_lines), w_right, content_h, border_fg="#7C4DFF")
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
        tab_names = ["LIST & PAGINATOR", "FILESYSTEM PICKER", "CLI PROMPTS", "CODEBASE TREE", "FLEXBOX & KPIS"]
        active_name = tab_names[self.tabs.active_tab]
        tab_badge = (
            Style()
            .bold(True)
            .foreground("#000000")
            .background("#00E676")
            .padding(0, 1)
            .render(f" TAB {self.tabs.active_tab + 1}/5: {active_name} ")
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
