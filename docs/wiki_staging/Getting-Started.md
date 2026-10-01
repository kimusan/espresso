# Getting Started with Espresso

## Requirements
- Python 3.10 or higher
- Linux, macOS, or Windows (via Windows Terminal or ConPTY)
- Zero external dependencies required!

## Installation
```bash
pip install espresso-tui
```

## Your First Application

Create a file named `app.py`:

```python
from espresso import Model, Msg, Cmd, KeyMsg, Program, quit_app

class App(Model):
    def __init__(self):
        self.message = "Press space to brew coffee!"

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key=" "):
                self.message = "☕ Coffee is brewing!"
            case KeyMsg(key="q" | "esc"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        return f"{self.message}\n\n[Space] Brew  [q] Quit"

if __name__ == "__main__":
    Program(App()).run()
```

Run it:
```bash
python3 app.py
```

## Built-in CLI Toolkit

Espresso includes the `espresso` command-line utility for exploration and development:

```bash
# List all 14 interactive built-in example applications
espresso list

# Run any example by ID (e.g. 14 for Developer Workspace)
espresso run 14

# Launch the interactive 39-component gallery
espresso gallery

# Scaffold a new TEA application with boilerplate ready to go
espresso new my_app.py
```
