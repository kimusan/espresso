#!/usr/bin/env python3
"""Example 10: New Beans Gallery Showcase.

Interactive showcase demonstrating the full suite of newly added components:
1. Tabs: Tab bar navigation with hotkeys (1-4, Left/Right)
2. List & Paginator: Filterable list with search (/) and pagination
3. FilePicker: Interactive filesystem browser with file sizes and hidden file toggle (.)
4. Prompts: SelectPrompt, MultiSelectPrompt, and ConfirmPrompt
5. Tree: Collapsible hierarchical directory tree
6. Dialog & 2D Overlay: Modal card composited on top with backdrop dimming (press 'd')
7. ToastManager: Transient auto-dismissing toast notifications (press 't')
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, WindowSizeMsg, quit_app
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
    Paginator,
    PaginatorType,
    SelectPrompt,
    SelectSubmitMsg,
    TabChangeMsg,
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
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
    place_overlay,
)


class ComponentGallery(Model):
    def __init__(self) -> None:
        self.width = 90
        self.height = 26

        # --- Component 1: Tabs ---
        self.tabs = Tabs(
            titles=["Filterable List", "File Picker", "CLI Prompts", "Tree View"],
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
        ]
        self.list = List(
            items=list_items,
            title="Component Catalog",
            per_page=5,
            width=46,
            height=12,
        )
        self.selected_list_info = "Press Enter on any item to inspect"

        # --- Component 3: FilePicker ---
        project_root = Path(__file__).resolve().parent.parent
        self.file_picker = FilePicker(
            directory=project_root,
            height=12,
            width=54,
            show_hidden=False,
            dir_allowed=True,
        )
        self.selected_file_info = f"Current Directory: {project_root.name}"

        # --- Component 4: Prompts ---
        self.select_prompt = SelectPrompt(
            question="Select deployment target:",
            options=["Production Cluster", "Staging Environment", "Local Container", "Bare Metal"],
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
                                TreeNode("keys.py (Key parser)"),
                                TreeNode("program.py (Runtime engine)"),
                            ],
                        ),
                        TreeNode(
                            label="crema",
                            expanded=True,
                            children=[
                                TreeNode("style.py (Style box model)"),
                                TreeNode("color.py (ANSI/RGB/Adaptive)"),
                                TreeNode("overlay.py (2D layer compositor)"),
                                TreeNode("gradient.py (Color gradients)"),
                            ],
                        ),
                        TreeNode(
                            label="beans",
                            expanded=True,
                            children=[
                                TreeNode("list.py (Filterable list)"),
                                TreeNode("filepicker.py (Filesystem picker)"),
                                TreeNode("dialog.py (Modal overlay)"),
                                TreeNode("prompt.py (CLI prompts)"),
                                TreeNode("toast.py (Toast manager)"),
                                TreeNode("tabs.py (Tab navigation)"),
                                TreeNode("tree.py (Collapsible tree)"),
                            ],
                        ),
                    ],
                ),
                TreeNode(
                    label="examples",
                    expanded=True,
                    children=[
                        TreeNode("05_beans_showcase.py"),
                        TreeNode("08_rss_reader.py"),
                        TreeNode("10_component_gallery.py"),
                    ],
                ),
                TreeNode(
                    label="tests",
                    children=[
                        TreeNode("test_beans_new.py"),
                        TreeNode("test_overlay.py"),
                    ],
                ),
            ],
        )
        self.tree = Tree(nodes=[tree_root])
        self.selected_tree_info = "Navigate with arrows, Space/Enter to expand"

        # --- Component 6: Toast Manager ---
        self.toast_manager = ToastManager()

        # --- Component 7: Modal Dialog ---
        self.show_dialog = False
        self.dialog = Dialog(
            title="Deploy Application",
            message="Are you sure you want to deploy the latest release to the production cluster?",
            buttons=("Deploy Now", "Cancel"),
            width=46,
            border_foreground="#00E676",
        )

        # Styling
        self.panel_style = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#4A4A6A")
            .padding(1, 2)
        )
        self.hint_style = Style().foreground("#8888AA")
        self.accent_style = Style().bold(True).foreground("#00E5FF")

    def init(self) -> Cmd | None:
        # Show welcome toast on startup
        _, toast_cmd = self.toast_manager.add(
            "Welcome to the Beans Component Gallery!",
            ToastLevel.INFO,
            duration=3.5,
        )
        return toast_cmd

    def update(self, msg: Msg) -> tuple[ComponentGallery, Cmd | None]:
        cmds: list[Cmd] = []

        # Handle window resize
        if isinstance(msg, WindowSizeMsg):
            self.width = max(80, msg.width)
            self.height = max(24, msg.height)
            return self, None

        # Handle Toast Dismiss Msg
        if isinstance(msg, ToastDismissMsg):
            self.toast_manager, t_cmd = self.toast_manager.update(msg)
            if t_cmd:
                cmds.append(t_cmd)
            return self, None

        # If modal dialog is open, route keyboard events exclusively to Dialog
        if self.show_dialog:
            if isinstance(msg, KeyMsg):
                self.dialog, d_cmd = self.dialog.update(msg)
                if d_cmd:
                    res_msg = d_cmd()
                    if isinstance(res_msg, DialogResultMsg):
                        self.show_dialog = False
                        # Trigger toast based on dialog result
                        if res_msg.action == "Deploy Now":
                            _, toast_cmd = self.toast_manager.add(
                                "Deployment sequence initiated!",
                                ToastLevel.SUCCESS,
                                duration=4.0,
                            )
                            cmds.append(toast_cmd)
                        else:
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
                case "d" | "m":
                    self.show_dialog = True
                    return self, None
                case "t":
                    # Spawn a random toast notification
                    samples = [
                        ("Build completed in 1.42s", ToastLevel.SUCCESS),
                        ("Cache miss on key 'catalog_v2'", ToastLevel.WARNING),
                        ("Database connection established", ToastLevel.INFO),
                        ("Failed to sync remote repository", ToastLevel.ERROR),
                    ]
                    text, lvl = random.choice(samples)
                    _, toast_cmd = self.toast_manager.add(text, lvl, duration=3.0)
                    cmds.append(toast_cmd)
                    return self, toast_cmd
                case "tab":
                    # Cycle active tab
                    next_tab = (self.tabs.active_tab + 1) % len(self.tabs.titles)
                    self.tabs, _ = self.tabs.update(KeyMsg(str(next_tab + 1)))
                    return self, None
                case "shift+tab":
                    prev_tab = (self.tabs.active_tab - 1) % len(self.tabs.titles)
                    self.tabs, _ = self.tabs.update(KeyMsg(str(prev_tab + 1)))
                    return self, None
                case "1" | "2" | "3" | "4":
                    self.tabs, _ = self.tabs.update(msg)
                    return self, None

        # Route events to active tab component
        curr_tab = self.tabs.active_tab

        if curr_tab == 0:
            # Tab 0: Filterable List
            self.list, list_cmd = self.list.update(msg)
            if list_cmd:
                sub_msg = list_cmd()
                if isinstance(sub_msg, ListSelectMsg):
                    self.selected_list_info = f"Selected: {sub_msg.item.title} ({sub_msg.item.description})"
                    _, toast_cmd = self.toast_manager.add(
                        f"Selected item: {sub_msg.item.title}",
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
                    self.selected_file_info = f"Selected: {sub_msg.path.name} ({'Dir' if sub_msg.is_dir else 'File'})"
                    _, toast_cmd = self.toast_manager.add(
                        f"Picked {sub_msg.path.name}",
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

            # Route to currently active prompt
            if self.active_prompt_idx == 0:
                self.select_prompt, p_cmd = self.select_prompt.update(msg)
                if p_cmd:
                    sub_msg = p_cmd()
                    if isinstance(sub_msg, SelectSubmitMsg):
                        _, toast_cmd = self.toast_manager.add(
                            f"Target chosen: {sub_msg.selected}",
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
                        _, toast_cmd = self.toast_manager.add(
                            f"Enabled {len(sub_msg.selected)} pipelines",
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
                        status_str = "Confirmed! Proceeding..." if sub_msg.confirmed else "Cancelled."
                        _, toast_cmd = self.toast_manager.add(status_str, lvl, duration=3.0)
                        cmds.append(toast_cmd)

            return self, cmds[0] if cmds else None

        elif curr_tab == 3:
            # Tab 3: Tree View
            self.tree, t_cmd = self.tree.update(msg)
            if t_cmd:
                sub_msg = t_cmd()
                if isinstance(sub_msg, TreeNodeSelectMsg):
                    self.selected_tree_info = f"Node: {sub_msg.node.label}"
                    _, toast_cmd = self.toast_manager.add(
                        f"Selected node: {sub_msg.node.label}",
                        ToastLevel.INFO,
                        duration=2.5,
                    )
                    cmds.append(toast_cmd)
            return self, cmds[0] if cmds else None

        return self, None

    def _render_tab_content(self) -> str:
        curr_tab = self.tabs.active_tab

        if curr_tab == 0:
            # List Tab: Left column is list, right column is preview details
            list_rendered = self.list.view()
            detail_box = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#00E5FF")
                .padding(1, 2)
                .width(36)
                .render(
                    f"{Style().bold(True).foreground('#00E5FF').render('Item Inspector')}\n\n"
                    f"{self.selected_list_info}\n\n"
                    f"{self.hint_style.render('Keys:')}\n"
                    f"• {Style().foreground('#00E676').render('↑/↓ or j/k')}: Navigate\n"
                    f"• {Style().foreground('#00E676').render('/')}: Filter items\n"
                    f"• {Style().foreground('#00E676').render('Enter')}: Select item\n"
                    f"• {Style().foreground('#00E676').render('Esc')}: Clear filter\n"
                )
            )
            return join_horizontal(Align.TOP, list_rendered, "  ", detail_box)

        elif curr_tab == 1:
            # FilePicker Tab
            fp_rendered = self.file_picker.view()
            info_box = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#FF9100")
                .padding(1, 2)
                .width(28)
                .render(
                    f"{Style().bold(True).foreground('#FF9100').render('File Details')}\n\n"
                    f"{self.selected_file_info}\n\n"
                    f"{self.hint_style.render('Keys:')}\n"
                    f"• {Style().foreground('#00E676').render('↑/↓')}: Browse\n"
                    f"• {Style().foreground('#00E676').render('Enter')}: Open/Select\n"
                    f"• {Style().foreground('#00E676').render('Backspace')}: Parent dir\n"
                    f"• {Style().foreground('#00E676').render('.')}: Toggle hidden\n"
                )
            )
            return join_horizontal(Align.TOP, fp_rendered, "  ", info_box)

        elif curr_tab == 2:
            # Prompts Tab: Stack all 3 prompts
            p0 = self.select_prompt.view()
            p1 = self.multiselect_prompt.view()
            p2 = self.confirm_prompt.view()

            card0 = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#7D56F4" if self.active_prompt_idx == 0 else "#333344")
                .padding(0, 1)
                .render(p0)
            )
            card1 = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#7D56F4" if self.active_prompt_idx == 1 else "#333344")
                .padding(0, 1)
                .render(p1)
            )
            card2 = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#7D56F4" if self.active_prompt_idx == 2 else "#333344")
                .padding(0, 1)
                .render(p2)
            )

            prompt_col = join_vertical(Align.LEFT, card0, card1, card2)
            hint_box = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#7D56F4")
                .padding(1, 2)
                .width(32)
                .render(
                    f"{Style().bold(True).foreground('#7D56F4').render('Prompt Controls')}\n\n"
                    f"Active: Prompt #{self.active_prompt_idx + 1}\n\n"
                    f"{self.hint_style.render('Navigation:')}\n"
                    f"• {Style().foreground('#00E676').render('PgUp/PgDn')}: Switch Prompt\n"
                    f"• {Style().foreground('#00E676').render('↑/↓')}: Select option\n"
                    f"• {Style().foreground('#00E676').render('Space')}: Toggle checkbox\n"
                    f"• {Style().foreground('#00E676').render('a')}: Select all\n"
                    f"• {Style().foreground('#00E676').render('Enter')}: Submit\n"
                )
            )
            return join_horizontal(Align.TOP, prompt_col, "  ", hint_box)

        elif curr_tab == 3:
            # Tree Tab
            tree_rendered = self.tree.view()
            tree_box = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#00E676")
                .padding(1, 2)
                .width(44)
                .render(tree_rendered)
            )
            info_box = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground("#00E676")
                .padding(1, 2)
                .width(36)
                .render(
                    f"{Style().bold(True).foreground('#00E676').render('Hierarchy Explorer')}\n\n"
                    f"{self.selected_tree_info}\n\n"
                    f"{self.hint_style.render('Tree Keys:')}\n"
                    f"• {Style().foreground('#00E676').render('↑/↓')}: Navigate nodes\n"
                    f"• {Style().foreground('#00E676').render('Space/Right')}: Expand\n"
                    f"• {Style().foreground('#00E676').render('Left')}: Collapse / Parent\n"
                    f"• {Style().foreground('#00E676').render('Enter')}: Select node\n"
                )
            )
            return join_horizontal(Align.TOP, tree_box, "  ", info_box)

        return ""

    def view(self) -> str:
        # 1. Header with title and Tabs
        header_title = (
            Style()
            .bold(True)
            .foreground("#FAFAFA")
            .background("#7D56F4")
            .padding(0, 2)
            .render("ESPRESSO BEANS COMPONENT GALLERY")
        )
        tabs_view = self.tabs.view()
        header = join_horizontal(Align.CENTER, header_title, "   ", tabs_view)

        # 2. Main Tab Content
        content = self._render_tab_content()

        # 3. Footer Bar with hotkey hints and active toasts
        hotkey_hints = (
            f"  {Style().bold(True).foreground('#00E5FF').render('Tab')}: Switch Tab  •  "
            f"{Style().bold(True).foreground('#00E5FF').render('1-4')}: Quick Jump  •  "
            f"{Style().bold(True).foreground('#00E5FF').render('d')}: Modal Dialog  •  "
            f"{Style().bold(True).foreground('#00E5FF').render('t')}: Trigger Toast  •  "
            f"{Style().bold(True).foreground('#FF5252').render('q')}: Quit"
        )
        footer_style = Style().foreground("#A0A0C0")
        footer = footer_style.render(hotkey_hints)

        # 4. Toasts (if active, render below content)
        toast_view = self.toast_manager.view()

        # Assemble base view
        sections = [header, "", content, ""]
        if toast_view:
            sections.append(toast_view)
        sections.append(footer)
        base_view = join_vertical(Align.LEFT, *sections)

        # 5. Composite Dialog Modal overlay if active
        if self.show_dialog:
            dialog_view = self.dialog.view()
            return place_overlay(base_view, dialog_view, center=True, dim_backdrop=True)

        return base_view


def main() -> None:
    app = ComponentGallery()
    prog = Program(app, alt_screen=True)
    prog.run()


if __name__ == "__main__":
    main()
