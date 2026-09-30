# Beans: Standard Component Library

`espresso.beans` provides modular, reusable components following The Elm Architecture.

---

## 1. Spinner

The `Spinner` component renders animated loading indicators driven by tick commands.

### Usage
```python
from espresso.beans import Spinner, DOTS, COFFEE

spinner = Spinner(frames=COFFEE, fps=4.0)

# In Parent Model:
def init(self):
    return self.spinner.init()

def update(self, msg):
    self.spinner, cmd = self.spinner.update(msg)
    return self, cmd

def view(self):
    return f"Loading {self.spinner.view()}..."
```

### Presets Available
- `DOTS`: `⠋`, `⠙`, `⠹`, `⠸`, `⠼`, `⠴`, `⠦`, `⠧`, `⠇`, `⠏`
- `LINE`: `|`, `/`, `-`, `\`
- `PULSE`: `█`, `▓`, `▒`, `░`
- `POINTS`: `∙∙∙`, `●∙∙`, `∙●∙`, `∙∙●`
- `COFFEE`: `☕ `, `♨️ `, `✨ `
- `GLOBE`: `🌍`, `🌎`, `🌏`
- `MOON`: `🌑`, `🌒`, `🌓`, `🌔`, `🌕`

---

## 2. TextInput

The `TextInput` component provides interactive single-line text entry with cursor blinking and navigation.

### Usage
```python
from espresso.beans import TextInput, EchoMode

input_field = TextInput(
    placeholder="Enter your name...",
    prompt="Name: ",
    echo_mode=EchoMode.NORMAL  # Or EchoMode.PASSWORD
)

def update(self, msg):
    self.input_field, cmd = self.input_field.update(msg)
    return self, cmd
```

### Features
- Arrow navigation (Left, Right, Home, End)
- Backspace and Delete editing
- Masking with `EchoMode.PASSWORD`
- Character length limits (`char_limit`)
- `focus()` and `blur()` state toggles

---

## 3. Progress

The `Progress` component provides a customizable progress bar.

### Usage
```python
from espresso.beans import Progress
from espresso.crema import Style

bar = Progress(
    width=40,
    percent=0.75,
    fill_style=Style().foreground("#00E676")
)

def view(self):
    return bar.view()
```

---

## 4. Viewport

The `Viewport` component creates a scrollable rectangular viewing pane for long text or logs.

### Usage
```python
from espresso.beans import Viewport

vp = Viewport(width=60, height=10)
vp.set_content("Long text content with many lines...")

def update(self, msg):
    self.vp, cmd = self.vp.update(msg)
    return self, cmd
```

### Navigation Keys
- `Up` / `k`: Scroll up 1 line
- `Down` / `j`: Scroll down 1 line
- `PageUp` / `ctrl+u`: Scroll up 1 full page
- `PageDown` / `ctrl+d`: Scroll down 1 full page
- `Home` / `g`: Jump to top
- `End` / `G`: Jump to bottom
- Mouse Wheel Up / Down

---

## 5. Table

The `Table` component displays tabular data with column formatting and keyboard row navigation.

### Usage
```python
from espresso.beans import Table, Column
from espresso.crema import Align

columns = [
    Column("ID", width=6),
    Column("Name", width=20),
    Column("Role", width=15),
    Column("Salary", width=10, align=Align.RIGHT)
]

rows = [
    ["1", "Alice Jensen", "Engineer", "$120,000"],
    ["2", "Bob Smith", "Designer", "$110,000"],
    ["3", "Charlie Brown", "Manager", "$135,000"]
]

table = Table(columns, rows, height=5)

def update(self, msg):
    self.table, cmd = self.table.update(msg)
    return self, cmd
```

---

## 6. TextArea

The `TextArea` component provides an interactive multi-line text editor with customizable line numbers, viewport scrolling, tab indentation, and cursor navigation.

### Usage
```python
from espresso.beans import TextArea
from espresso.crema import Style

editor = TextArea(
    placeholder="Write your notes here...",
    width=60,
    height=12,
    show_line_numbers=True,
    tab_size=4,
    line_number_style=Style().foreground("#555555"),
    cursor_line_number_style=Style().bold(True).foreground("#7D56F4")
)

def update(self, msg):
    self.editor, cmd = self.editor.update(msg)
    return self, cmd

def view(self):
    return self.editor.view()
```

### Features
- **Line Numbers**: Optional gutter column with active cursor line highlighting (`show_line_numbers=True`, `toggle_line_numbers()`).
- **Cursor Navigation**: Arrow keys (`Up`, `Down`, `Left`, `Right`), `Home` / `End`, `PageUp` / `PageDown`.
- **Text Editing**: Character insertion, `Backspace` (merging lines), `Delete`, and `Enter`.
- **Indentation**: Configurable `tab_size` inserting soft spaces on `Tab`.
- **Limits**: Optional `char_limit` and `max_lines` constraints.
- **Scroll Synchronization**: Automatic vertical and horizontal viewport tracking.

---

## 7. Help

The `Help` component displays keyboard shortcut documentation. It dynamically toggles between a compact single-line view and a multi-column full reference.

### Usage
```python
from espresso.beans import Help, KeyBinding

# Define key bindings
bindings = [
    KeyBinding("enter", "submit order"),
    KeyBinding("tab", "next field"),
    KeyBinding("ctrl+c", "quit app"),
    KeyBinding("?", "toggle full help", help_key="?")
]

help_view = Help(bindings, width=60, show_all=False)

def update(self, msg):
    match msg:
        case KeyMsg(key="?"):
            self.help_view.toggle()
    return self, None

def view(self):
    return self.help_view.view()
```

### Modes
- **Compact View (`show_all=False`)**: Displays a single horizontal line of hotkeys separated by `short_separator` (` • `), automatically truncating items that exceed `width`.
- **Full View (`show_all=True`)**: Displays multi-column side-by-side grouped keybindings with aligned descriptions.
- **`KeyMap` Protocol Support**: Pass custom container objects implementing `short_help()` and `full_help()`.

---

## 8. Timer

The `Timer` component provides a high-precision countdown timer driven by Tea `tick` commands.

### Usage
```python
from espresso.beans import Timer, TimerTimeoutMsg

timer = Timer(timeout=60.0, interval=1.0, auto_start=True, tag="session_timer")

def init(self):
    return self.timer.init()

def update(self, msg):
    match msg:
        case TimerTimeoutMsg(tag="session_timer"):
            print("Session expired!")
            return self, None
    self.timer, cmd = self.timer.update(msg)
    return self, cmd

def view(self):
    return f"Time Remaining: {self.timer.view()} ({int(self.timer.percent * 100)}%)"
```

### Methods & Properties
- `start()` / `stop()` / `toggle()`: Controls countdown state.
- `reset(timeout=None, start=False)`: Restores original or specifies a new duration.
- `remaining` / `elapsed`: Current time remaining and elapsed in seconds.
- `percent`: Completion progress from `0.0` (just started) to `1.0` (timed out).
- `format_fn`: Optional custom formatter callback `(float) -> str`.

---

## 9. Stopwatch

The `Stopwatch` component measures elapsed time with sub-second accuracy.

### Usage
```python
from espresso.beans import Stopwatch

sw = Stopwatch(interval=0.1, auto_start=True)

def init(self):
    return self.sw.init()

def update(self, msg):
    self.sw, cmd = self.sw.update(msg)
    return self, cmd

def view(self):
    return f"Elapsed: {self.sw.view()}"  # e.g., "01:23.45"
```

### Controls
- `start()`: Resumes tracking elapsed time.
- `stop()`: Freezes the stopwatch.
- `toggle()`: Flips between running and stopped states.
- `reset(start=False)`: Clears elapsed time back to `0.0`.

---

## 10. Paginator

The `Paginator` component calculates page offsets and renders pagination dots, page counts, or item range summaries.

### Usage
```python
from espresso.beans import Paginator, PaginatorType

items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5", "Item 6"]
paginator = Paginator(per_page=2, total_items=len(items), paginator_type=PaginatorType.DOTS)

def update(self, msg):
    self.paginator, cmd = self.paginator.update(msg)
    return self, cmd

def view(self):
    # Slice the current page items
    start, end = self.paginator.slice_bounds
    page_items = items[start:end]
    content = "\n".join(f"• {item}" for item in page_items)
    return f"{content}\n\n{self.paginator.view()}"
```

### Presentation Types (`PaginatorType`)
- `PaginatorType.DOTS`: Bullet indicators (`• • ◦ ◦`)
- `PaginatorType.NUMERIC`: Page ratio (`1/5`)
- `PaginatorType.COMPACT`: Descriptive range (`Page 1 of 5 (1-10 of 42)`)

### Key Bindings & Methods
- `Left` / `h` / `PageUp`: Previous page (`prev_page()`)
- `Right` / `l` / `PageDown`: Next page (`next_page()`)
- `slice_bounds`: Returns `(start, end)` tuple for slicing your data
- `slice_items(items)`: Directly slices a list or sequence
- `set_total(count)`: Updates the total item count and clamps current page

---

## 11. Dialog

The `Dialog` component renders a centered floating confirmation or decision modal card with action buttons.

### Usage
```python
from espresso.beans import Dialog, DialogResultMsg
from espresso.crema import place_overlay

dialog = Dialog(
    title="Confirm Action",
    message="Are you sure you want to delete this file?",
    buttons=("Delete", "Cancel"),
    width=44
)

def update(self, msg):
    match msg:
        case DialogResultMsg(action=action, button_index=idx):
            if action == "Delete":
                delete_target_file()
            self.show_dialog = False
            return self, None

    self.dialog, cmd = self.dialog.update(msg)
    return self, cmd

def view(self):
    base_view = render_main_ui()
    if self.show_dialog:
        # Composite modal on top with dimmed background
        return place_overlay(base_view, self.dialog.view(), center=True, dim_backdrop=True)
    return base_view
```

### Features & Controls
- `Tab` / `Right` / `l`: Move focus to next button
- `Shift+Tab` / `Left` / `h`: Move focus to previous button
- `Enter` / `Space`: Confirm focused button and emit `DialogResultMsg(action, button_index)`
- `Esc`: Auto-selects "Cancel" if present, emitting `DialogResultMsg`

---

## 12. List

The `List` component is an interactive, searchable, and paginated or continuously scrollable list with real-time substring filtering, inspired by `charmbracelet/bubbles/list` and `treilik/bubblelister`.

### Key Features
- **Pagination Modes**: Discrete pages with `Paginator` (`PaginationMode.PAGINATED`) or smooth continuous line-by-line scrolling (`PaginationMode.SCROLL`) with dynamic percentage position indicators.
- **Badges & Suffixes**: First-class right-aligned badges on `ListItem` (`badge="PROD"`, `badge_style=...`) or dynamic suffixes via `suffix_fn`.
- **Line Numbering**: Absolute 1-based indexing (`show_numbers=True`) and Vim-style relative distance numbering (`relative_numbers=True`).
- **Tree Guides**: Connected continuation guides for multi-line items (`show_tree_guides=True` using `╭`, `├`, `│`, `╰`).
- **Custom Renderers**: Completely customize item rows with `item_renderer` or customize cursor markers with `prefix_fn`.
- **Scrollbar**: Visual vertical scrollbar track (`│`) and thumb (`█`) via `show_scrollbar=True`.
- **Native Mouse Support**: Wheel scrolling (`WHEEL_UP` / `WHEEL_DOWN`) and left-click selection emitting `ListSelectMsg`.

### Usage
```python
from espresso.beans import List, ListItem, ListSelectMsg, PaginationMode
from espresso.crema import Style

items = [
    ListItem(title="deploy-prod", description="Roll out Kubernetes cluster", badge="PROD", badge_style=Style().foreground("#00E676").bold(True)),
    ListItem(title="db-migrate", description="Execute pending schema migrations", badge="DB", badge_style=Style().foreground("#29B6F6")),
    ListItem(title="run-tests", description="Execute comprehensive test suite", badge="CI", badge_style=Style().foreground("#AB47BC")),
]

list_view = List(
    items=items,
    title="Operations",
    per_page=5,
    width=50,
    pagination_mode=PaginationMode.SCROLL,
    show_numbers=True,
    relative_numbers=False,
    show_tree_guides=True,
    show_scrollbar=True,
)

def update(self, msg):
    match msg:
        case ListSelectMsg(item=item, index=idx):
            print(f"Executed: {item.title} (index {idx})")
            return self, None

    self.list_view, cmd = self.list_view.update(msg)
    return self, cmd

def view(self):
    return self.list_view.view()
```

### Keyboard & Mouse Shortcuts
- `↑` / `k`: Move cursor up
- `↓` / `j`: Move cursor down
- `PageUp` / `PageDown`: Jump by page / viewport height
- `Home` / `g`: Jump to first item
- `End` / `G`: Jump to last item
- `/`: Open inline search filter field
- `Esc`: Clear search filter and close filter mode
- `Enter`: Select highlighted item, emitting `ListSelectMsg(item, index)`
- `Mouse Wheel`: Scroll list up and down
- `Mouse Click`: Select and highlight the clicked item row

---

## 13. FilePicker

The `FilePicker` component provides an interactive terminal directory browser with file size formatting and hidden file filtering.

### Usage
```python
from espresso.beans import FilePicker, FileSelectMsg, format_file_size

picker = FilePicker(
    directory=".",
    allowed_extensions=[".py", ".md", ".json"],
    show_hidden=False,
    file_allowed=True,
    dir_allowed=False,
    height=10,
    width=50
)

def update(self, msg):
    match msg:
        case FileSelectMsg(path=path, is_dir=is_dir):
            print(f"Chosen file: {path}")
            return self, None

    self.picker, cmd = self.picker.update(msg)
    return self, cmd

def view(self):
    return self.picker.view()
```

### Shortcuts & Controls
- `↑` / `k`, `↓` / `j`: Navigate items
- `Enter` / `→` / `l`: Enter folder or select file (emits `FileSelectMsg`)
- `Backspace` / `←` / `h`: Navigate up to parent directory
- `.`: Toggle hidden file visibility
- `format_file_size(size_bytes)`: Utility function formatting bytes into `B`, `KB`, `MB`, `GB`, `TB`

---

## 14. Prompt (Select, MultiSelect, Confirm)

`espresso.beans` provides three interactive prompt components for terminal forms and CLI wizards.

### 1. `SelectPrompt` (Single Choice)
```python
from espresso.beans import SelectPrompt, SelectSubmitMsg

prompt = SelectPrompt(
    question="Choose your deployment environment:",
    options=["Development", "Staging", "Production"],
    default_index=0
)

def update(self, msg):
    match msg:
        case SelectSubmitMsg(selected=choice, index=idx):
            print(f"Deploying to: {choice}")
            return self, None
    self.prompt, cmd = self.prompt.update(msg)
    return self, cmd
```

### 2. `MultiSelectPrompt` (Multiple Checkboxes)
```python
from espresso.beans import MultiSelectPrompt, MultiSelectSubmitMsg

multi = MultiSelectPrompt(
    question="Select components to install:",
    options=["Auth", "Database", "Redis Cache", "Telemetry"],
    default_selected=[0, 1]
)

def update(self, msg):
    match msg:
        case MultiSelectSubmitMsg(selected=items, indices=idxs):
            print(f"Selected: {items}")
            return self, None
    self.multi, cmd = self.multi.update(msg)
    return self, cmd
```
- `Space`: Toggle checkbox `[x]`
- `a`: Toggle select all

### 3. `ConfirmPrompt` (Yes/No Confirmation)
```python
from espresso.beans import ConfirmPrompt, ConfirmSubmitMsg

confirm = ConfirmPrompt(question="Proceed with migration?", default=True)

def update(self, msg):
    match msg:
        case ConfirmSubmitMsg(confirmed=ok):
            if ok:
                run_migration()
            return self, None
    self.confirm, cmd = self.confirm.update(msg)
    return self, cmd
```
- `y` / `n`: Instant choose Yes or No
- `Tab` / `Left` / `Right`: Toggle active choice, `Enter` to submit

---

## 15. ToastManager

The `ToastManager` component manages transient, auto-dismissing notification banners.

### Usage
```python
from espresso.beans import ToastManager, ToastLevel, ToastDismissMsg

toasts = ToastManager()

def trigger_alert(self):
    # add() returns (ToastItem, Cmd) where Cmd is an async auto-dismiss timer
    item, cmd = self.toasts.add("Build succeeded!", level=ToastLevel.SUCCESS, duration=3.0)
    return cmd

def update(self, msg):
    # Handles ToastDismissMsg automatically when timer expires
    self.toasts, cmd = self.toasts.update(msg)
    return self, cmd

def view(self):
    # Render main content with toasts positioned in top corner or overlay
    return f"{main_content}\n{self.toasts.view()}"
```

### Severity Levels (`ToastLevel`)
- `ToastLevel.INFO`: Cyan accent (`ℹ `)
- `ToastLevel.SUCCESS`: Green accent (`✔ `)
- `ToastLevel.WARNING`: Gold accent (`⚠ `)
- `ToastLevel.ERROR`: Red accent (`✖ `)

---

## 16. Tabs

The `Tabs` component renders a top horizontal tab bar with keyboard navigation and number shortcuts.

### Usage
```python
from espresso.beans import Tabs, TabStyle, TabChangeMsg

tabs = Tabs(
    titles=["Overview", "Logs", "Metrics", "Settings"],
    active_tab=0,
    tab_style=TabStyle.PILL,
    show_numbers=True
)

def update(self, msg):
    match msg:
        case TabChangeMsg(index=idx, title=title):
            self.current_screen = idx
            return self, None

    self.tabs, cmd = self.tabs.update(msg)
    return self, cmd

def view(self):
    return f"{self.tabs.view()}\n\n{render_tab_content(self.current_screen)}"
```

### Styles (`TabStyle`)
- `TabStyle.PILL`: High-contrast filled background pill (`1 Overview`)
- `TabStyle.LINE`: Underline accent (`1 Overview`)
- `TabStyle.BRACKET`: Bracketed indicators (`[ 1 Overview ]`)

### Navigation Controls
- `Tab` / `Shift+Tab`: Next / previous tab
- `1` through `9`: Direct hotkey jump to corresponding tab index
- `Left` / `Right` / `h` / `l`: Step between adjacent tabs

---

## 17. Tree

The `Tree` component displays hierarchical folder or object trees with Unicode branches and expand/collapse support.

### Usage
```python
from espresso.beans import Tree, TreeNode, TreeNodeSelectMsg

nodes = [
    TreeNode("src", children=[
        TreeNode("espresso", children=[
            TreeNode("core"),
            TreeNode("crema"),
            TreeNode("beans"),
        ], expanded=True),
        TreeNode("main.py"),
    ], expanded=True),
    TreeNode("README.md"),
]

tree = Tree(nodes=nodes)

def update(self, msg):
    match msg:
        case TreeNodeSelectMsg(node=node):
            print(f"Selected: {node.label}")
            return self, None

    self.tree, cmd = self.tree.update(msg)
    return self, cmd

def view(self):
    return self.tree.view()
```

### Navigation & Shortcuts
- `↑` / `k`, `↓` / `j`: Navigate visible tree rows
- `Right` / `l` / `Space`: Expand collapsed branch or toggle node
- `Left` / `h`: Collapse branch, or jump to parent node
- `Enter`: Select node and emit `TreeNodeSelectMsg(node)`

---

## 18. StatusBar

The `StatusBar` component renders responsive, multi-section status bars with priority-based auto-truncation for narrow terminal viewports.

### Usage
```python
from espresso.beans import StatusBar, StatusSection
from espresso.crema import Style

status_bar = StatusBar(
    left=[
        StatusSection("NORMAL", style=Style().bold(True).background("#7D56F4").padding(0, 1), priority=3),
        StatusSection("main.py", priority=2),
    ],
    center=[
        StatusSection("UTF-8", priority=0),
    ],
    right=[
        StatusSection("42:15", priority=2),
        StatusSection("98% Ready", icon="⚡", style=Style().foreground("#00E676"), priority=3),
    ],
    width=80,
    background="#1A1A24"
)

def view(self):
    return status_bar.view()
```

### Responsive Space Allocation
- **Comfortable Width**: Center cluster is perfectly centered between Left and Right clusters.
- **Medium Width**: Center cluster is smoothly truncated with ellipsis (`…`) while preserving Left and Right.
- **Narrow Width**: Sections with lowest `priority` are dynamically dropped, guaranteeing high-priority badges remain visible without line wrapping.

---

## 19. Metric & MetricGroup

The `Metric` and `MetricGroup` components render dashboard KPI cards, tags, and summary lists with trend deltas and directional styling.

### Usage
```python
from espresso.beans import Metric, MetricGroup, MetricLayout, MetricTrend, LayoutDirection

metrics = MetricGroup(
    metrics=[
        Metric(label="Revenue", value="$42,500", delta="+12.4%", trend=MetricTrend.UP),
        Metric(label="Latency", value="45", unit="ms", delta="-8ms", trend=MetricTrend.DOWN, invert_trend=True),
        Metric(label="Error Rate", value="0.02%", delta="0%", trend=MetricTrend.NEUTRAL),
    ],
    layout=MetricLayout.CARD,
    direction=LayoutDirection.HORIZONTAL
)

def view(self):
    return metrics.view()
```

### Layouts (`MetricLayout`)
- `MetricLayout.CARD`: Bordered stat card with large value, unit, delta, and arrow indicator
- `MetricLayout.TAG`: Compact inline pill badge (`[ Label: Value (delta) ]`)
- `MetricLayout.LIST`: Dotted key-value row (`Revenue ......... $42,500 ▲ +12.4%`)

### Features
- `invert_trend=True`: Inverts color logic for metrics where lower is better (e.g. Latency, Error Rate: DOWN is green, UP is red)
- Horizontal and vertical stacking via `LayoutDirection`

---

## 20. NavStack

The `NavStack` component provides view stack routing with automatic breadcrumb navigation (`Home › Category › Detail`) and history management.

### Usage
```python
from espresso.beans import NavStack, NavPushMsg, NavPopMsg

nav = NavStack(initial_title="Dashboard", initial_model=DashboardModel())

# Push a sub-view
def open_user_details(self, user_id):
    return self.nav.push("User Details", UserDetailModel(user_id))

# Pop back to previous view
def go_back(self):
    model, cmd = self.nav.pop()
    return cmd

def update(self, msg):
    # NavStack automatically delegates messages to the active top model
    self.nav, cmd = self.nav.update(msg)
    return self, cmd

def view(self):
    # Renders breadcrumbs on top followed by the active model view
    return self.nav.view()
```

### Features
- Automatic message forwarding to the active view on top of the stack
- `auto_pop_on_back=True`: Automatically pops the top view on `Esc` or `Backspace`
- Breadcrumbs trail rendering (`breadcrumbs_view()`)
- Lifecycle notifications (`NavPushMsg`, `NavPopMsg`)

---

## 21. DatePicker

The `DatePicker` component provides an interactive monthly calendar widget for selecting dates, inspired by `EthanEFung/bubble-datepicker`. It features keyboard and mouse navigation, month and year focus cycling, day-of-week custom start day, and min/max date boundary clamping.

### Usage
```python
from datetime import date
from espresso.beans import DatePicker, DateSelectMsg, DateChangeMsg
from espresso.crema import ROUNDED_BORDER

picker = DatePicker(
    value=date.today(),
    cursor_date=date.today(),
    min_date=date(2025, 1, 1),
    max_date=date(2027, 12, 31),
    first_day_of_week=6,  # 6 = Sunday (default), 0 = Monday
    show_header=True,
    show_help=True,
    border=ROUNDED_BORDER,
    border_foreground="#7D56F4",
)

def update(self, msg):
    match msg:
        case DateSelectMsg(date=selected_date):
            print(f"Date selected: {selected_date}")
            return self, None
        case DateChangeMsg(date=active_date):
            print(f"Cursor moved: {active_date}")
            return self, None

    self.picker, cmd = self.picker.update(msg)
    return self, cmd

def view(self):
    return self.picker.view()
```

### Key Bindings & Shortcuts
- **Calendar Mode**:
  - `←` / `h`, `→` / `l`: Move cursor ±1 day
  - `↑` / `k`, `↓` / `j`: Move cursor ±7 days (previous / next week)
  - `[` / `PageUp`: Move to previous month
  - `]` / `PageDown`: Move to next month
  - `{` / `}`: Move to previous / next year (handles leap days automatically)
  - `t`: Jump cursor to today's date
  - `Enter` / `Space`: Confirm date selection (emits `DateSelectMsg`)
  - `Tab` / `Shift+Tab`: Cycle focus between `CALENDAR` ⇄ `MONTH` ⇄ `YEAR`
- **Month Mode**:
  - `←` / `h` / `↑` / `k`: Previous month
  - `→` / `l` / `↓` / `j`: Next month
  - `Enter` / `Space` / `Esc`: Return focus to calendar grid
- **Year Mode**:
  - `←` / `h` / `↓` / `j`: Previous year
  - `→` / `l` / `↑` / `k`: Next year
  - `Enter` / `Space` / `Esc`: Return focus to calendar grid

### Mouse Controls
- **Header Arrows**: Click `◀` or `▶` to advance or retreat months.
- **Header Text**: Click on the month or year name to switch focus directly to `MONTH` or `YEAR`.
- **Date Cells**: Click on any date cell to jump to that date, select it, and emit `DateSelectMsg`.
- **Mouse Wheel**: Wheel up / down scrolls months backward / forward.

### Methods & Properties
- `selected_date` / `value`: The currently confirmed `date` (or `None`).
- cursor_date: The highlighted `date` cursor.
- `select_date(d=None)`: Selects specified or current cursor date.
- `set_date(d)`: Sets both cursor and selected date.
- `set_focus(focus)`: Switch focus between `CALENDAR`, `MONTH`, `YEAR`, `NONE`.
- `is_today(d)`, `is_selected(d)`, `is_disabled(d)`: Date status helpers.

---

## 22. PipelineProgress

The `PipelineProgress` component manages multi-stage asynchronous task execution pipelines, inspired by `mritd/bubbles/progressbar`. It displays a live visual progress bar, per-stage status badges (`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `SKIPPED`), elapsed execution times, and failure diagnostics.

### Usage
```python
from espresso.beans import PipelineProgress, PipelineStage, StageStatus

stages = [
    PipelineStage(title="Fetch Source & Deps", status=StageStatus.SUCCESS, duration=0.82),
    PipelineStage(title="Lint & Static Analysis", status=StageStatus.SUCCESS, duration=1.14),
    PipelineStage(title="Run Unit Tests", status=StageStatus.RUNNING, duration=0.14),
    PipelineStage(title="Build Optimized Wheel", status=StageStatus.PENDING),
    PipelineStage(title="Publish to Registry", status=StageStatus.PENDING),
]

pipeline = PipelineProgress(
    stages=stages,
    title="Release Pipeline",
    width=50,
    show_stages=True,
    show_timer=True,
)

def update(self, msg):
    self.pipeline, cmd = self.pipeline.update(msg)
    return self, cmd

def view(self):
    return self.pipeline.view()
```

### Features & Controls
- **Stages**: List of `PipelineStage` objects with custom `action` callables or manual state tracking.
- **Messages**: Emits `StageStartMsg`, `StageCompleteMsg`, `StageFailedMsg`, and `PipelineCompleteMsg`.
- **Keyboard / API**:
  - `start()`: Begin automated async pipeline execution.
  - `reset()`: Reset all stages to initial pending state.
  - `advance()`: Advance the active stage to completion and start the next.

---

## 23. MarkdownViewer

The `MarkdownViewer` component provides a pure Python terminal Markdown document viewer, inspired by `mistakenelf/teacup/markdown`. It parses and renders headings (H1-H6), bold, italic, code spans, fenced code blocks, blockquotes with `▌` bars, nested bullet and numbered lists, and horizontal rules, wrapped in a smooth scrollable `Viewport` with scroll percentage footer.

### Usage
```python
from espresso.beans import MarkdownViewer

doc = """# Release Notes
Welcome to **Espresso 0.2.0**!
- Added `MarkdownViewer`
- Added `CodeViewer`
> Simple, declarative, pure Python.
"""

md_viewer = MarkdownViewer(
    markdown=doc,
    width=70,
    height=20,
    show_footer=True,
    filename="CHANGELOG.md",
)

def update(self, msg):
    self.md_viewer, cmd = self.md_viewer.update(msg)
    return self, cmd

def view(self):
    return self.md_viewer.view()
```

### Key Bindings & Mouse Controls
- `↑` / `k`, `↓` / `j`: Scroll line by line.
- `PageUp` / `PageDown`: Scroll page by page.
- `Home` / `g`, `End` / `G`: Jump to document top / bottom.
- **Mouse Wheel**: Wheel up / down scrolls the document viewport.

---

## 24. CodeViewer

The `CodeViewer` component provides a syntax-highlighted source code viewer with line numbers, active cursor line highlight (`▶`), and smooth viewport scrolling, inspired by `mistakenelf/teacup/code`. It uses Python's standard library `tokenize` module for Python syntax and regex tokenizers for JavaScript/TypeScript, Go, Rust, JSON, YAML, SQL, Shell, and Markdown.

### Usage
```python
from espresso.beans import CodeViewer, THEME_ESPRESSO, THEME_DRACULA

viewer = CodeViewer(
    code='def brew(shots=2):\n    return f"{shots} shots"',
    language="python",
    width=60,
    height=15,
    theme=THEME_ESPRESSO,
    show_line_numbers=True,
    cursor_line=1,
)

def update(self, msg):
    self.viewer, cmd = self.viewer.update(msg)
    return self, cmd

def view(self):
    return self.viewer.view()
```

### Predefined Themes
- `THEME_ESPRESSO`: Hazelnut purple keywords, cyan builtins, vibrant green strings.
- `THEME_DRACULA`: Dracula palette with pink keywords, yellow strings, and purple numbers.
- `THEME_MONOKAI`: High-contrast green functions, orange numbers, and cyan operators.

### Key Bindings & Mouse Controls
- `↑` / `k`, `↓` / `j`: Move cursor line and scroll viewport smoothly.
- `PageUp` / `PageDown`: Move cursor and scroll by viewport height.
- `Home` / `g`, `End` / `G`: Jump to top or bottom line.
- **Mouse Wheel**: Wheel up / down scrolls code viewport.

---

## 25. QuickFix

The `QuickFix` component is a Neovim-style diagnostic bottom drawer for viewing compiler errors, warnings, and linter messages, inspired by `Genekkion/theHermit`. It displays items with severity badges (`ERR`, `WARN`, `INFO`, `HINT`), file paths, line/column numbers, and error codes. It can dock or overlay over any view using `wrap_view`.

### Usage
```python
from espresso.beans import QuickFix, QuickFixItem, QuickFixSelectMsg

items = [
    QuickFixItem(file="src/brew.py", line=12, col=5, message="variable 'crema' unused", severity="warn", code="W0612"),
    QuickFixItem(file="src/brew.py", line=25, col=1, message="syntax error: missing colon", severity="error", code="E0001"),
]

qf = QuickFix(items=items, height=6, toggle_key="ctrl+x")

def update(self, msg):
    match msg:
        case QuickFixSelectMsg(item=item, index=idx):
            print(f"Jump to {item.file}:{item.line}")
            return self, None

    self.qf, cmd = self.qf.update(msg)
    return self, cmd

def view(self):
    main_ui = "Main editor content..."
    return self.qf.wrap_view(main_ui, width=80, height=24)
```

### Key Bindings & Mouse Controls
- `Ctrl+X` (configurable): Toggle drawer open / closed.
- `↑` / `k`, `↓` / `j`: Navigate diagnostic items.
- `Enter`: Select diagnostic issue and emit `QuickFixSelectMsg`.
- `Esc` / `q`: Close drawer.
- **Mouse Wheel**: Wheel up / down scrolls diagnostic list.

---

## 26. DetailSelector

The `DetailSelector` component combines a single-choice selection list on top with a live synchronized preview card below, inspired by `mritd/bubbles/selector`. When items are navigated, the card below updates dynamically with item details and metadata.

### Usage
```python
from espresso.beans import DetailSelector, DetailItem, DetailSelectMsg

items = [
    DetailItem(
        title="Espresso Runtime",
        tag="CORE",
        details="Declarative The Elm Architecture event loop.",
        metadata={"Version": "0.1.0"},
    ),
    DetailItem(
        title="Crema Engine",
        tag="STABLE",
        details="ANSI truecolor styling, 2D layer compositor.",
        metadata={"Engine": "Crema"},
    ),
]

selector = DetailSelector(items=items, prompt="Select Layer:", width=50, per_page=4)

def update(self, msg):
    match msg:
        case DetailSelectMsg(item=item, index=idx):
            print(f"Selected layer: {item.title}")
            return self, None

    self.selector, cmd = self.selector.update(msg)
    return self, cmd

def view(self):
    return self.selector.view()
```

### Key Bindings & Mouse Controls
- `↑` / `k`, `↓` / `j`: Move selection cursor and update preview card.
- `PageUp` / `PageDown`: Move page backward / forward.
- `Enter` / `Space`: Select highlighted item and emit `DetailSelectMsg`.
- **Mouse Wheel**: Wheel up / down scrolls through items.

---

## 27. ImageViewer

The `ImageViewer` component renders images and graphics in the terminal using 24-bit ANSI upper-half blocks (`▀`) and 10-step grayscale ASCII characters, inspired by `mistakenelf/teacup/image`. It provides pure Python standard library support for Netpbm PPM (`.ppm`), uncompressed 24-bit BMP (`.bmp`), and raw RGB pixel matrices, plus an optional Pillow bridge for PNG/JPEG when installed.

### Usage
```python
from espresso.beans import ImageViewer, RenderMode

# 1. From raw RGB matrix:
pixels = [
    [(255, 0, 0), (0, 255, 0)],
    [(0, 0, 255), (255, 255, 0)],
]
viewer = ImageViewer(pixels=pixels, width=40, height=20, mode=RenderMode.HALF_BLOCK)

# 2. From file (PPM or BMP natively):
# viewer = ImageViewer.from_file("assets/logo.ppm", width=60, height=30)

def update(self, msg):
    self.viewer, cmd = self.viewer.update(msg)
    return self, cmd

def view(self):
    return self.viewer.view()
```

### Features & Formats
- **24-bit ANSI Truecolor Half-Blocks**: Combines two vertical RGB pixels into a single `▀` character using foreground and background ANSI truecolor codes (`\x1b[38;2;R;G;Bm` + `\x1b[48;2;R;G;Bm`).
- **ASCII Grayscale Mode**: 10-level luminance mapping ramp (` .:-=+*#%@`) for monochrome or non-truecolor terminals.
- **Native Formats**: Supports Netpbm P3 (ASCII) and P6 (binary) PPM files, plus uncompressed 24-bit Windows BMP files with zero third-party dependencies.
- **Optional Pillow Bridge**: Automatically loads PNG, JPEG, GIF, and WebP if `PIL` is installed in the environment.
- **Viewport Navigation**: Arrow keys and mouse wheel scroll large images seamlessly.

---

## 28. Splitter

The `Splitter` component provides an interactive, draggable two-pane container (`Left | Right` or `Top / Bottom`) separated by a customizable divider bar. Users can resize panes directly with the mouse or via keyboard shortcuts.

### Usage
```python
from espresso.beans import Splitter, SplitterOrientation, SplitterResizeMsg

splitter = Splitter(
    pane1=tree_view,
    pane2=code_viewer,
    orientation=SplitterOrientation.HORIZONTAL,
    width=80,
    height=24,
    ratio=0.4,
    min_pane1=15,
    min_pane2=20,
)

def update(self, msg):
    match msg:
        case SplitterResizeMsg(ratio=r, pane1_size=p1, pane2_size=p2):
            print(f"Resized: {p1} | {p2} (ratio: {r:.2f})")
            return self, None

    self.splitter, cmd = self.splitter.update(msg)
    return self, cmd

def view(self):
    return self.splitter.view()
```

### Controls & Features
- **Mouse Drag**: Click and drag the divider bar (`│` or `─`) smoothly with the mouse.
- **Keyboard Arrows**: `←` / `→` (horizontal) or `↑` / `↓` (vertical) step by 1 cell.
- **Coarse Step**: `Ctrl+Arrows` steps by 5 cells.
- **Reset**: `=` or `r` resets to an even 50/50 split.
- **Child Sizing**: Automatically propagates dimensions to child models with `set_size(w, h)`.

---

## 29. Slider & RangeSlider

Tactile direct-manipulation numeric slider components supporting smooth mouse dragging, click-to-seek, and keyboard step adjustment.

### Usage
```python
from espresso.beans import Slider, RangeSlider, SliderChangeMsg, RangeSliderChangeMsg

# Single-thumb slider
vol_slider = Slider(
    min_val=0,
    max_val=100,
    value=65,
    step=1,
    width=35,
    label="Volume:",
    value_format="{value:.0f}%",
)

# Dual-thumb range slider
eq_slider = RangeSlider(
    min_val=20,
    max_val=20000,
    low=250,
    high=8000,
    step=10,
    width=45,
    label="Bandpass:",
    value_format="{low:.0f}Hz - {high:.0f}Hz",
)

def update(self, msg):
    match msg:
        case SliderChangeMsg(value=val, percent=pct):
            print(f"Volume adjusted: {val} ({pct*100:.1f}%)")
            return self, None
        case RangeSliderChangeMsg(low=l, high=h):
            print(f"Range adjusted: {l} to {h}")
            return self, None

    self.vol_slider, c1 = self.vol_slider.update(msg)
    self.eq_slider, c2 = self.eq_slider.update(msg)
    return self, batch(c1, c2)
```

### Controls
- **Mouse Click**: Click anywhere on the track to seek to that value.
- **Mouse Drag**: Click and drag thumb knob (`●`) smoothly across the track.
- **Mouse Wheel**: Wheel up / down increments or decrements by `step`.
- **Keyboard**: `←` / `→` (or `h` / `l`), `PageUp` / `PageDown` (5× step), `Home` / `End`.
- **RangeSlider Tab**: Press `Tab` to switch active thumb between `low` and `high`.

---

## 30. Sparkline

The `Sparkline` component renders real-time streaming data visualizations using either high-resolution 2D Unicode Braille curves (4× vertical resolution) or 1D vertical block bars (`  ▂▃▄▅▆▇█`).

### Usage
```python
from espresso.beans import Sparkline, SparklineMode, SparklineTickMsg

# Braille 2D curve with Truecolor gradient
sparkline = Sparkline(
    width=50,
    height=3,
    mode=SparklineMode.BRAILLE,
    label="CPU Load:",
    min_val=0,
    max_val=100,
    gradient_stops=["#00E5FF", "#7D56F4", "#FF007F"],
)

def update(self, msg):
    if isinstance(msg, TelemetryMsg):
        # Stream new data point
        self.sparkline.push(msg.cpu_usage)
        return self, None

    return self, None

def view(self):
    return self.sparkline.view()
```

### Features & Modes
- **`SparklineMode.BRAILLE`**: Uses Unicode Braille patterns (U+2800..U+28FF) mapping 2 horizontal dots by 4 vertical dots per cell, achieving ultra-smooth curves in tight terminal spaces.
- **`SparklineMode.BLOCK`**: 8-level vertical block character bars (`  ▂▃▄▅▆▇█`).
- **Telemetry & Stats**: Built-in current value badge, min/max/average properties, and directional trend indicators (`↗`, `↘`, `→`).
- **Vertical Gradients**: Smoothly colors multi-row sparklines via Crema's `multi_gradient_colors`.

---

## 31. Marquee

The `Marquee` component provides a fixed-width, smoothly scrolling animated text banner or ticker for news feeds, track titles, and alert headers.

### Usage
```python
from espresso.beans import Marquee, MarqueeMode, MarqueeTickMsg

marquee = Marquee(
    text="🚀 Espresso 2.0: High-performance TUI framework in pure Python • 28+ Beans components • SGR mouse dragging",
    width=40,
    speed=0.1,
    mode=MarqueeMode.LOOP,
    separator="   ★   ",
)

def init(self):
    return self.marquee.init()

def update(self, msg):
    self.marquee, cmd = self.marquee.update(msg)
    return self, cmd

def view(self):
    return self.marquee.view()
```

### Modes & Configuration
- **`MarqueeMode.LOOP`**: Continuous seamless looping with configurable separator.
- **`MarqueeMode.BOUNCE`**: Scrolls from beginning to end, pauses for `pause_frames`, then smoothly reverses direction.
- **Auto-Fit**: Automatically disables scrolling and renders static text if the string fits within `width`.

---

## 32. SortableList

The `SortableList` component allows users to reorder items dynamically via mouse drag-and-drop or intuitive keyboard shortcuts.

### Usage
```python
from espresso.beans import SortableList, SortableItem, ItemReorderedMsg

items = [
    SortableItem(id="1", title="Write tests"),
    SortableItem(id="2", title="Implement feature"),
    SortableItem(id="3", title="Deploy release"),
]

sortable = SortableList(items=items, width=40, height=8)

def update(self, msg):
    match msg:
        case ItemReorderedMsg(old_index=old, new_index=new, item=it):
            print(f"Moved '{it}' from position {old} to {new}")
            return self, None

    self.sortable, cmd = self.sortable.update(msg)
    return self, cmd

def view(self):
    return self.sortable.view()
```

### Controls
- **Mouse Drag-and-Drop**: Click on any row, drag it up or down to the target position, and release to commit. A highlighted `[HOLDING]` badge and insertion marker (`▼ `) indicate the drop target in real time.
- **Keyboard Reordering**:
  - `Space` / `Enter`: Grab highlighted item into holding mode.
  - `↑` / `↓` (or `k` / `j`): Move the grabbed item up or down.
  - `Space` / `Enter`: Drop item at current position.
  - `Esc`: Cancel grab and return item to original position.


