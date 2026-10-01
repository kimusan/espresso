# Espresso Architecture & The Elm Architecture (TEA)

## Overview

Espresso is built on **The Elm Architecture (TEA)**, an architectural pattern that originated in the Elm programming language and was brought to the command line by Charm's **Bubble Tea** in Go.

TEA provides strict unidirectional data flow and deterministic state transitions, eliminating spaghetti callbacks, mutable shared state bugs, and race conditions.

---

## The Core Triad: Model, Update, View

Every interactive application or component in Espresso implements three primitives:

```
                  ┌──────────────────────┐
                  │        Input         │
                  │ (Key, Mouse, Resize) │
                  └──────────┬───────────┘
                             │
                             ▼
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│ Initial State│────>│  update(msg)  │────>│   view()     │───> Terminal
└──────────────┘     └───────┬───────┘     └──────────────┘
                             │
                             ▼
                     ┌───────────────┐
                     │   Cmd (I/O)   │
                     └───────┬───────┘
                             │ (emits new Msg)
                             └───────────┘
```

### 1. `Model` (State)
The `Model` represents the complete state of the application at any given moment. In Python, this is typically a class or dataclass storing user input, cursor positions, loaded data, and view flags.

```python
class MyModel:
    def __init__(self):
        self.count = 0
```

### 2. `update(self, msg: Msg) -> tuple[Model, Cmd | None]`
The `update` function handles state transitions. It receives an event (`Msg`) and returns:
1. The updated `Model`
2. An optional `Cmd` (asynchronous work to execute)

```python
def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
    match msg:
        case KeyMsg(key="enter"):
            return self, self.submit_data()
        case DataReceivedMsg(payload=data):
            self.data = data
            return self, None
    return self, None
```

### 3. `view(self) -> str`
The `view` function is pure string rendering. It inspects the current state of `self` and returns a string with ANSI escape codes representing how the terminal should look. It produces no side effects.

```python
def view(self) -> str:
    return f"Current count: {self.count}"
```

---

## Why Synchronous `update()` with Asynchronous `Cmd`?

A common pitfall in Python async programming is introducing race conditions by doing asynchronous work directly inside event handlers:

```python
# ANTI-PATTERN: Prone to race conditions and out-of-order state corruption
async def on_button_click():
    data = await fetch_slow_data()  # Other clicks can happen while suspended!
    self.state = data
```

In Espresso:
1. `update()` is **strictly synchronous** by default. State transitions are instantaneous and serialized.
2. Long-running I/O (network requests, timers, subprocesses) is wrapped in a `Cmd`.
3. When the `Cmd` completes, it yields a new `Msg` (e.g. `DataReceivedMsg`) back into the program queue.
4. This ensures that state is never updated out-of-order, and testing requires zero async mocking!

---

## Commands (`Cmd`)

A `Cmd` in Espresso is a callable that returns a `Msg` (or `None`). It can be:
- A synchronous function: `def my_cmd() -> Msg:`
- An async coroutine: `async def my_cmd() -> Msg:`

### Built-in Command Combinators

* **`espresso.batch(*cmds)`**: Runs multiple commands concurrently and dispatches their messages as they finish.
* **`espresso.sequence(*cmds)`**: Runs commands one after another in order.
* **`espresso.tick(duration, msg)`**: Waits for a duration and emits a timer message.
* **`espresso.quit_app`**: Instructs the event loop to shut down cleanly.
* **`espresso.enable_mouse`**: Dynamic command returned by `update()` to activate SGR mouse tracking.
* **`espresso.disable_mouse`**: Dynamic command returned by `update()` to deactivate SGR mouse tracking.

---

## Input Events (`Msg`)

Espresso translates low-level terminal byte sequences into strongly-typed messages dispatched to `update(msg)`:

1. **`KeyMsg(key, runes, alt, ctrl)`**: Keyboard strokes (e.g. `key="enter"`, `key="ctrl+c"`, `key="up"`).
2. **`MouseMsg(action, button, x, y, alt, ctrl, shift)`**: SGR 1006 mouse events:
   - `action`: `MouseAction.PRESS`, `RELEASE`, `MOTION`, `DOUBLE_CLICK`
   - `button`: `MouseButton.LEFT`, `RIGHT`, `MIDDLE`, `WHEEL_UP`, `WHEEL_DOWN`, `WHEEL_LEFT`, `WHEEL_RIGHT`
   - `x`, `y`: 0-indexed terminal column and row coordinates.
   - Coordinate helpers: `.translate(dx, dy)` and `.relative_to(origin_x, origin_y)` for nested component coordinate transformation.
3. **`WindowSizeMsg(width, height)`**: Terminal window resize events.

---

## Mouse Gesture Tracking (`MouseGestureTracker`)

Low-level terminal mouse drivers emit discrete raw mouse press, release, and motion events. To enable rich desktop-grade interactions, Espresso provides `MouseGestureTracker`:

- **Double-Click Synthesis**: Detects when two `MouseAction.PRESS` events occur within a configurable time threshold (default 350ms) and spatial tolerance ($\le 1$ cell), emitting a synthetic `MouseAction.DOUBLE_CLICK` event.
- **Drag & Drop**: Enables smooth tracking of drag trajectories across component boundaries for sliders, splitters, and sortable lists.
- **Sub-Component Routing**: Mouse coordinates can be shifted into local sub-component space using `msg.relative_to(origin_x, origin_y)`.

```python
from espresso.core.mouse import MouseGestureTracker, MouseAction, MouseMsg

tracker = MouseGestureTracker(timeout=0.35)

def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
    if isinstance(msg, MouseMsg):
        # Synthesize double clicks transparently
        msg = tracker.process(msg)
        if msg.action == MouseAction.DOUBLE_CLICK:
            self.toggle_expanded()
    return self, None
```

---

## High-Performance Alt-Screen Line Diffing

A major historical drawback of terminal UIs is visual flicker caused by full-screen clearing (`\x1b[2J` or `\x1b[H\x1b[2J`) between frames. Espresso solves this with a **line-diffing terminal renderer**:

1. **Line Cache**: Retains the exact line buffer of the previously rendered frame (`self._last_rendered_lines`).
2. **Deterministic Diffing**: Upon receiving a new frame string from `model.view()`, splits it into lines and compares each row against the cache.
3. **Targeted ANSI Invalidation**: Only modified lines are sent to stdout. Cursor jump escapes (`\x1b[{row};1H`) jump directly to the changed row, followed by an erase-in-line sequence (`\x1b[2K`) and the new row content.
4. **Boundary Clamping**: Every rendered frame is strictly clamped to `min(term_h, len(new_lines))` and truncated to `term_w` with `truncate_ansi()`, completely preventing terminal scroll-creep and auto-wrap overflows.

```
Frame N:          Frame N+1:          Output sent to terminal:
┌──────────┐     ┌──────────┐
│ Line 1   │     │ Line 1   │        (Skipped - matches cache)
│ Line 2   │ ──> │ Line 2 * │  ───>  \x1b[2;1H\x1b[2KLine 2 *
│ Line 3   │     │ Line 3   │        (Skipped - matches cache)
└──────────┘     └──────────┘
```

---

## Sub-Model ("Bean") Composition

Components in Espresso are simply smaller models that implement `init`, `update`, and `view`.

A parent model delegates to child models:
```python
class ParentApp(Model):
    def __init__(self):
        self.text_input = TextInput()

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        self.text_input, cmd = self.text_input.update(msg)
        return self, cmd

    def view(self) -> str:
        return f"Form:\n{self.text_input.view()}"
```

---

## Built-in CLI Tool Architecture (`espresso`)

Espresso installs a standalone command-line executable (`espresso`) designed for development, debugging, and rapid prototyping:

```bash
# Discover all 14 interactive example programs
espresso list

# Execute any example by ID or file path
espresso run 14
espresso run 08

# Open the 39-component visual interactive gallery
espresso gallery

# Scaffold an idiomatic TEA application template
espresso new my_app.py

# Print version and environment info
espresso --version
```

### CLI Implementation Principles
- **Zero-Dependency Launcher**: Operates using Python's standard `argparse` and `subprocess` modules.
- **Dynamic Example Discovery**: Inspects `examples/` directory and extracts program descriptions dynamically.
- **Scaffolder (`espresso new`)**: Emits a clean, typed starter template pre-wired with Elm architecture, `Program`, alt-screen mode, mouse handling, and Crema styling.
