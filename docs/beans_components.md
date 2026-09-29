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
