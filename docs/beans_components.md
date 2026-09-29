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
