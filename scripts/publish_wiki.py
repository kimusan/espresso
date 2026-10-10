#!/usr/bin/env python3
"""Script to build and publish comprehensive GitHub Wiki pages for Espresso.

Builds up-to-date wiki markdown files from docs/ and README.md:
  - Home.md
  - Getting-Started.md
  - The-Elm-Architecture.md
  - Crema-Styling-Guide.md
  - Beans-Component-Catalog.md
  - Release-and-Packaging.md
  - _Sidebar.md
  - _Footer.md

Usage:
  # Generate wiki pages locally into build/wiki/ for inspection:
  python3 scripts/publish_wiki.py --dry-run

  # Publish directly to GitHub Wiki repository (via git or token):
  python3 scripts/publish_wiki.py --push

  # In GitHub Actions (using GITHUB_TOKEN):
  python3 scripts/publish_wiki.py --token "${GITHUB_TOKEN}" --repo "kimusan/espresso"
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

# Styling
C_RESET = "\x1b[0m"
C_BOLD = "\x1b[1m"
C_RED = "\x1b[31m"
C_GREEN = "\x1b[32m"
C_YELLOW = "\x1b[33m"
C_BLUE = "\x1b[34m"
C_CYAN = "\x1b[36m"


def build_home_page() -> str:
    return r"""# Welcome to the Espresso Wiki

**Espresso** is a lightweight, declarative terminal UI framework for Python inspired by Charm's **Bubble Tea**, **Lip Gloss**, and **Bubbles**.

Built purely with the **Python standard library** (zero external dependencies), Espresso brings deterministic state transitions, rich TrueColor terminal styling, and a modular component ecosystem to Python developers.

<p align="center">
  <img src="https://raw.githubusercontent.com/kimusan/espresso/main/assets/demos/demo_steaming_espresso_3a.gif" alt="Espresso Steaming Coffee Cup" width="700" />
</p>

---

## 📚 Table of Contents

| Section | Description |
| :--- | :--- |
| **[[Getting Started\|Getting-Started]]** | Requirements, installation (`pip install espressoTUI`), standalone `.pyz` runner, first TEA application, and CLI commands. |
| **[[The Elm Architecture\|The-Elm-Architecture]]** | Model-Update-View triad, `Cmd` async isolation, mouse gesture tracking, alt-screen line-diffing engine, and sub-model composition. |
| **[[Crema Styling Guide\|Crema-Styling-Guide]]** | Declarative styles, TrueColor linear/multi-gradients, border titles, ANSI word wrapping, `FlexBox`, and responsive multi-column `Grid`. |
| **[[Beans Component Catalog\|Beans-Component-Catalog]]** | Comprehensive reference for all 39 standard UI beans with full code examples, keyboard controls, and configuration options. |
| **[[Release & Packaging\|Release-and-Packaging]]** | Package distribution formats (Wheel, sdist, universal zipapp, standalone native binaries), PyPI Trusted Publishing, and `./scripts/release.py`. |

---

## 🏛️ Ecosystem Architecture at a Glance

| Layer | Charm Equivalent | Description |
| :--- | :--- | :--- |
| **`espresso`** | `bubbletea` | **The Strong Base**: Core TEA framework, runtime event loop, raw terminal driver, command primitives, flicker-free line-diffing alt-screen renderer, SGR mouse tracking, and desktop gesture engine (`MouseGestureTracker`). |
| **`espresso.crema`** | `lipgloss` | **The Smooth Crema**: Declarative styling, box model, TrueColor (24-bit RGB), ANSI 256, borders, border titles, TrueColor linear gradients, ANSI word-wrapping, 2D layout alignment, `FlexBox`, and responsive `Grid`. |
| **`espresso.beans`** | `bubbles` | **The Flavorful Beans**: 39 reusable UI components including TextArea, GitTree, CommandPalette, BarChart, Splitter, Sliders, Form, DiffViewer, SortableList, Confetti, CodeViewer, MarkdownViewer, Tables, Viewports, and more. |
| **`espresso` CLI** | — | **The Toolkit**: Standalone developer executable for listing built-in examples, launching the interactive gallery, running scripts, and scaffolding new applications. |

---

## 🧩 39 Standard UI Beans

| Component | Description |
| :--- | :--- |
| **`Spinner`** | Animated activity indicators (`DOTS`, `LINE`, `PULSE`, `POINTS`, `COFFEE`, `GLOBE`, `MOON`). |
| **`TextInput`** | Interactive text field with cursor blinking, navigation, and password masking. |
| **`Progress`** | Smooth percentage progress bars with custom styles and dynamic width scaling. |
| **`Viewport`** | Scrollable viewport for long terminal content with mouse wheel support. |
| **`Table`** | Column-formatted interactive table with row selection, headers, and pagination. |
| **`TextArea`** | Multi-line text editor with line numbering, cursor navigation, and viewport scrolling. |
| **`Help`** | Adaptive keybinding helper rendering compact single-line or full multi-column hotkey lists. |
| **`Timer`** | High-precision countdown timer driven by tick commands with formatted duration. |
| **`Stopwatch`** | High-precision stopwatch tracking elapsed time with split-second hundredths display. |
| **`Paginator`** | Pagination controller supporting bullet dots, numeric counters, and compact ranges. |
| **`Dialog`** | Modal dialog confirmation box with custom button actions and backdrop dimming. |
| **`List`** | Filterable list with real-time search query filtering, badges, and cursor selection. |
| **`FilePicker`** | Terminal filesystem browser with human-readable file sizes and extension filtering. |
| **`Prompt`** | Interactive CLI prompt suite: `SelectPrompt`, `MultiSelectPrompt`, `ConfirmPrompt`. |
| **`ToastManager`** | Transient toast notification manager with severity levels (`INFO`, `SUCCESS`, `WARN`, `ERROR`). |
| **`Tabs`** | Tab bar navigation header with styles (`PILL`, `LINE`, `BRACKET`) and numeric hotkeys. |
| **`Tree`** | Hierarchical collapsible tree view with Unicode connectors and node selection. |
| **`StatusBar`** | Responsive multi-section status bar with Left, Center, and Right priority clusters. |
| **`Metric` / `MetricGroup`** | KPI stat cards and tags with trend indicators (`UP`, `DOWN`, `NEUTRAL`) and delta metrics. |
| **`NavStack`** | Hierarchical view router with push/pop transitions, breadcrumbs, and message routing. |
| **`DatePicker`** | Interactive calendar date picker with month/year navigation and date clamping. |
| **`PipelineProgress`** | Multi-stage task execution pipeline with live status badges and execution times. |
| **`MarkdownViewer`** | Pure Python GitHub-flavored markdown viewer with code blocks, tables, and scrolling. |
| **`CodeViewer`** | Syntax-highlighted code viewer (Python, JS, Go, Rust, SQL, JSON) with cursor highlighting. |
| **`QuickFix`** | Diagnostic bottom drawer for linter issues with severity badges and view compositing. |
| **`DetailSelector`** | Dual-pane master-detail list selector with real-time preview panel. |
| **`ImageViewer`** | Terminal graphics viewer rendering TrueColor half-blocks (`▀`) and ASCII grayscale. |
| **`Splitter`** | Dual-pane container (`Left \| Right` or `Top / Bottom`) with draggable divider bar. |
| **`Slider` / `RangeSlider`** | Direct-manipulation numeric slider and dual-thumb range bar with mouse dragging. |
| **`Sparkline`** | High-resolution Unicode Braille curves (4× vertical resolution) and 1D block bars. |
| **`Marquee`** | Smoothly scrolling animated text ticker with loop and bounce physics. |
| **`SortableList`** | Reorderable list supporting mouse drag-and-drop and keyboard `Space`+`Arrows`. |
| **`Spring`** | Physical damped harmonic oscillator simulation with analytical differential equation solver. |
| **`Confetti`** | 2D celebratory particle physics emitter (radial bursts, cannons, rain) with drag & gravity. |
| **`DiffViewer`** | Git diff visualizer with Unified and Split dual-pane views and intra-line word diffs. |
| **`Form` / `FormBuilder`** | Multi-field form container with validation, inline error badges, and Tab cycling. |
| **`CommandPalette`** | Spotlight search runner (`Ctrl+P` / `Cmd+P`) with recents tracking and modal overlay. |
| **`GitTree`** | Collapsible Git file tree with status badges (`[M]`, `[A]`, `[D]`, `[?]`) and branch header. |
| **`BarChart`** | Horizontal and vertical bar charts with sub-character precision and TrueColor gradients. |
"""


def build_getting_started() -> str:
    return """# Getting Started with Espresso

## Requirements
- Python 3.10 or higher
- Linux, macOS, or Windows (via Windows Terminal or ConPTY)
- **Zero external dependencies required!**

---

## Installation

### Option 1: Via PyPI
```bash
pip install espressoTUI
```

### Option 2: Universal Standalone Executable (Zero Installation)
Download the standalone `espresso.pyz` from GitHub Releases:
```bash
curl -LO https://github.com/kimusan/espresso/releases/latest/download/espresso.pyz
chmod +x espresso.pyz
./espresso.pyz gallery
```

### Option 3: Pre-compiled Native Binaries (No Python Runtime Required)
Pre-compiled standalone binaries are available on every GitHub release:
- **Linux x86_64**: `espresso-linux-x86_64`
- **macOS Apple Silicon**: `espresso-macos-arm64`
- **macOS Intel**: `espresso-macos-x86_64`
- **Windows x86_64**: `espresso-windows-x86_64.exe`

---

## Your First Application

Create a file named `app.py`:

```python
from espresso import Model, Msg, Cmd, KeyMsg, Program, quit_app
from espresso.crema import Style, ROUNDED_BORDER

class CounterApp(Model):
    def __init__(self) -> None:
        self.count = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="+" | "up" | "k"):
                self.count += 1
            case KeyMsg(key="-" | "down" | "j"):
                self.count -= 1
            case KeyMsg(key="q" | "esc"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        box = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .padding(1, 3)
            .border_title(" Espresso Counter ")
        )
        body = f"Counter value: {self.count}\\n\\nPress [+] / [-] to count, [q] to quit."
        return box.render(body)

if __name__ == "__main__":
    Program(CounterApp(), alt_screen=True, mouse=True).run()
```

Run it:
```bash
python3 app.py
```

---

## Built-in CLI Toolkit

Espresso includes the `espresso` command-line utility for exploring examples and scaffolding new applications:

```bash
# List all 14 interactive built-in example applications
espresso list

# Run any example by ID (e.g. 14 for Developer Workspace)
espresso run 14
espresso run 08

# Launch the interactive 39-component gallery
espresso gallery

# Scaffold a new TEA application with boilerplate ready to go
espresso new my_app.py
```

---

## Next Steps

- Learn the architectural core in **[[The Elm Architecture|The-Elm-Architecture]]**.
- Discover styling and layouts in **[[Crema Styling Guide|Crema-Styling-Guide]]**.
- Browse ready-to-use components in **[[Beans Component Catalog|Beans-Component-Catalog]]**.
"""


def build_sidebar() -> str:
    return """### Espresso Documentation
* **[[Home]]**
* **[[Getting Started|Getting-Started]]**
* **[[The Elm Architecture|The-Elm-Architecture]]**
* **[[Crema Styling Guide|Crema-Styling-Guide]]**
* **[[Beans Component Catalog|Beans-Component-Catalog]]**
* **[[Release & Packaging|Release-and-Packaging]]**

---

### External Links
* [GitHub Repository](https://github.com/kimusan/espresso)
* [PyPI Project (espressoTUI)](https://pypi.org/project/espressoTUI)
* [Interactive Examples](https://github.com/kimusan/espresso/tree/main/examples)
* [GitHub Releases](https://github.com/kimusan/espresso/releases)
"""


def build_footer() -> str:
    return """---
*Espresso TUI Documentation • Built with pure Python standard library • [GitHub](https://github.com/kimusan/espresso)*
"""


def read_doc_file(filename: str) -> str:
    filepath = DOCS_DIR / filename
    if not filepath.exists():
        print(f"{C_RED}Error:{C_RESET} {filepath} does not exist!")
        sys.exit(1)
    return filepath.read_text(encoding="utf-8")


def generate_wiki_files(output_dir: Path) -> None:
    """Generate all wiki pages in the specified output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Home
    (output_dir / "Home.md").write_text(build_home_page(), encoding="utf-8")
    # 2. Getting-Started
    (output_dir / "Getting-Started.md").write_text(build_getting_started(), encoding="utf-8")
    # 3. The-Elm-Architecture (from docs/architecture.md)
    (output_dir / "The-Elm-Architecture.md").write_text(read_doc_file("architecture.md"), encoding="utf-8")
    # 4. Crema-Styling-Guide (from docs/crema_styling.md)
    (output_dir / "Crema-Styling-Guide.md").write_text(read_doc_file("crema_styling.md"), encoding="utf-8")
    # 5. Beans-Component-Catalog (from docs/beans_components.md)
    (output_dir / "Beans-Component-Catalog.md").write_text(read_doc_file("beans_components.md"), encoding="utf-8")
    # 6. Release-and-Packaging (from docs/releasing.md)
    (output_dir / "Release-and-Packaging.md").write_text(read_doc_file("releasing.md"), encoding="utf-8")
    # 7. _Sidebar & _Footer
    (output_dir / "_Sidebar.md").write_text(build_sidebar(), encoding="utf-8")
    (output_dir / "_Footer.md").write_text(build_footer(), encoding="utf-8")

    print(f"{C_GREEN}✓{C_RESET} Generated 8 wiki pages in {output_dir}")


def publish_to_git(wiki_dir: Path, repo: str, token: str | None = None) -> bool:
    """Push generated wiki pages to GitHub Wiki repository."""
    if token:
        remote_url = f"https://x-access-token:{token}@github.com/{repo}.wiki.git"
    else:
        remote_url = f"https://github.com/{repo}.wiki.git"

    with tempfile.TemporaryDirectory() as tmp_clone_dir:
        clone_path = Path(tmp_clone_dir)

        print(f"\n{C_BOLD}Attempting to clone wiki repository:{C_RESET} {C_CYAN}https://github.com/{repo}.wiki.git{C_RESET}")
        clone_res = subprocess.run(
            ["git", "clone", remote_url, str(clone_path)],
            capture_output=True,
            text=True,
        )

        if clone_res.returncode != 0:
            print(f"{C_YELLOW}⚠ Could not clone wiki repository automatically.{C_RESET}")
            print(f"{C_BOLD}Why this happens:{C_RESET}")
            print("  GitHub only creates the wiki git repository AFTER the first wiki page is created in the web UI.")
            print(f"\n{C_BOLD}How to initialize your GitHub Wiki (one-time setup):{C_RESET}")
            print(f"  1. Go to: {C_CYAN}https://github.com/{repo}/settings{C_RESET}")
            print("     Under 'Features', make sure 'Wikis' is checked.")
            print(f"  2. Visit: {C_CYAN}https://github.com/{repo}/wiki{C_RESET}")
            print("     Click 'Create the first page' and save it.")
            print("  3. Re-run this script to sync all pages automatically!")
            return False

        # Copy generated files to clone dir
        for item in wiki_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, clone_path / item.name)

        # Git add, commit, push
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=clone_path)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=clone_path)
        subprocess.run(["git", "add", "."], cwd=clone_path)

        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=clone_path, capture_output=True, text=True)
        if not status_res.stdout.strip():
            print(f"{C_GREEN}✓{C_RESET} GitHub Wiki is already up-to-date. No changes needed.")
            return True

        commit_res = subprocess.run(
            ["git", "commit", "-m", "docs(wiki): synchronize wiki with repository documentation"],
            cwd=clone_path,
            capture_output=True,
            text=True,
        )
        if commit_res.returncode != 0:
            print(f"{C_RED}Failed to commit wiki changes:\n{commit_res.stderr}{C_RESET}")
            return False

        push_res = subprocess.run(["git", "push", "origin", "master"], cwd=clone_path, capture_output=True, text=True)
        if push_res.returncode != 0:
            # Fallback to main branch
            push_res = subprocess.run(["git", "push", "origin", "main"], cwd=clone_path, capture_output=True, text=True)

        if push_res.returncode != 0:
            print(f"{C_RED}Failed to push to wiki repository:\n{push_res.stderr}{C_RESET}")
            return False

        print(f"\n{C_GREEN}{C_BOLD}✓ Successfully published all documentation to GitHub Wiki!{C_RESET}")
        print(f"View it live at: {C_CYAN}https://github.com/{repo}/wiki{C_RESET}\n")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="publish_wiki.py",
        description="Build and publish comprehensive documentation to GitHub Wiki.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate wiki files locally in build/wiki/ without pushing to GitHub",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push generated wiki pages to GitHub Wiki repository",
    )
    parser.add_argument(
        "--repo",
        default="kimusan/espresso",
        help="GitHub repository in owner/repo format (default: kimusan/espresso)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub Personal Access Token or GITHUB_TOKEN for authentication",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "build" / "wiki",
        help="Local directory to output wiki markdown files (default: build/wiki/)",
    )

    args = parser.parse_args()

    print(f"\n{C_BOLD}{C_CYAN}☕ Espresso Wiki Publisher{C_RESET}")
    print(f"{C_BLUE}──────────────────────────────────────────{C_RESET}")

    generate_wiki_files(args.out_dir)

    if args.dry_run or not args.push:
        print(f"\n{C_GREEN}Wiki pages generated locally at:{C_RESET} {C_CYAN}{args.out_dir}{C_RESET}")
        for f in sorted(args.out_dir.iterdir()):
            size_kb = f.stat().st_size / 1024
            print(f"  • {f.name:<28} ({size_kb:5.1f} KB)")
        if not args.push:
            print(f"\nTo push to the GitHub Wiki, run:")
            print(f"  {C_CYAN}python3 scripts/publish_wiki.py --push{C_RESET}\n")
        return

    # Push to git
    publish_to_git(args.out_dir, args.repo, args.token)


if __name__ == "__main__":
    main()
