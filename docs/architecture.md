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
