"""Espresso CLI - Terminal User Interface development toolkit.

Usage:
    espresso list                     List all built-in example applications
    espresso run <id_or_file>         Run an example by number/name or run a python script
    espresso gallery                  Launch the interactive component gallery
    espresso new <app_name>           Scaffold a new Espresso TEA application
    espresso --version                Show version information
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure src is on sys.path when executed directly as a script
_pkg_root = str(Path(__file__).resolve().parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from espresso import __version__

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"

EXAMPLES = [
    ("01", "01_counter.py", "Minimal TEA counter with increments, decrements, and quit"),
    ("02", "02_shopping_list.py", "Interactive list selection with checkboxes"),
    ("03", "03_styled_layout.py", "Crema styling, box models, and multi-column layout"),
    ("04", "04_fullscreen_mouse.py", "Fullscreen alternate screen with mouse tracking"),
    ("05", "05_beans_showcase.py", "Spinners, text inputs, paginators, and progress bars"),
    ("06", "06_git_commit_helper.py", "Multi-field interactive form for commit messages"),
    ("07", "07_editor.py", "Multi-line text editor with cursor positioning and syntax hints"),
    ("08", "08_rss_reader.py", "Production multi-pane RSS feed reader with async HTTP"),
    ("09", "09_colors_and_gradients.py", "TrueColor 24-bit gradients, palettes, and themes"),
    ("10", "10_component_gallery.py", "Comprehensive interactive component gallery"),
    ("11", "11_markdown_viewer.py", "Streaming GitHub-flavored markdown viewer"),
    ("12", "12_interactive_and_animated.py", "Splitters, sliders, marquees, and sortable lists"),
    ("13", "13_physics_and_tools.py", "Confetti physics engine, forms, and diff viewer"),
    ("14", "14_developer_workspace.py", "Flagship IDE with GitTree, BarChart, and CommandPalette"),
]

NEW_APP_TEMPLATE = '''"""Espresso TUI Application."""

from __future__ import annotations

import asyncio
from espresso import Model, Msg, Cmd, KeyMsg, Program, MouseMsg
from espresso.crema import Style, ROUNDED_BORDER


class AppModel(Model):
    def __init__(self) -> None:
        self.counter = 0

    def init(self) -> tuple[Model, Cmd]:
        return self, None

    def update(self, msg: Msg) -> tuple[Model, Cmd]:
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, Cmd.quit() if hasattr(Cmd, "quit") else None
                case "up" | "k" | "+":
                    self.counter += 1
                case "down" | "j" | "-":
                    self.counter -= 1
        return self, None

    def view(self) -> str:
        box_style = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .padding(1, 3)
            .border_title(" Espresso App ")
        )
        content = f"Counter: {self.counter}\\n\\nPress [+] / [-] to count, [q] to quit."
        return box_style.render(content)


def main() -> None:
    program = Program(AppModel(), alt_screen=True, mouse=True)
    asyncio.run(program.run())


if __name__ == "__main__":
    main()
'''


def cmd_list(args: argparse.Namespace) -> int:
    """List available built-in examples."""
    print(f"\x1b[1;38;2;125;86;244mEspresso Built-in Examples (v{__version__})\x1b[0m\n")
    print(f" {'ID':<4} {'File':<30} Description")
    print(f" {'─'*4:<4} {'─'*30:<30} {'─'*40}")
    for num, fname, desc in EXAMPLES:
        print(f" \x1b[1;36m{num:<4}\x1b[0m \x1b[1m{fname:<30}\x1b[0m {desc}")
    print("\nRun any example with: \x1b[1;32mespresso run <id>\x1b[0m (e.g. \x1b[32mespresso run 14\x1b[0m)")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run an example by ID or file path."""
    target = args.target

    # 1. Check if target is a numeric ID or matches an example
    matched_file: Path | None = None
    for num, fname, _ in EXAMPLES:
        if target in (num, str(int(num) if num.isdigit() else ""), fname, fname.replace(".py", "")):
            candidate = EXAMPLES_DIR / fname
            if candidate.exists():
                matched_file = candidate
                break

    # 2. Check if target is an existing path
    if matched_file is None:
        p = Path(target)
        if p.exists() and p.is_file():
            matched_file = p

    if matched_file is None:
        print(f"\x1b[1;31mError:\x1b[0m Could not find example or file: {target}")
        print("Run \x1b[1;32mespresso list\x1b[0m to see all available examples.")
        return 1

    # Run script with current python interpreter
    env = dict(os.environ)
    src_dir = str(Path(__file__).resolve().parent.parent)
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}:{existing_pp}" if existing_pp else src_dir

    try:
        proc = subprocess.run([sys.executable, str(matched_file)], env=env)
        return proc.returncode
    except KeyboardInterrupt:
        return 0


def cmd_gallery(args: argparse.Namespace) -> int:
    """Launch the interactive component gallery."""
    gallery_file = EXAMPLES_DIR / "10_component_gallery.py"
    if not gallery_file.exists():
        print(f"\x1b[1;31mError:\x1b[0m Component gallery not found at {gallery_file}")
        return 1

    env = dict(os.environ)
    src_dir = str(Path(__file__).resolve().parent.parent)
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}:{existing_pp}" if existing_pp else src_dir

    try:
        proc = subprocess.run([sys.executable, str(gallery_file)], env=env)
        return proc.returncode
    except KeyboardInterrupt:
        return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Scaffold a new Espresso TEA application."""
    name = args.name.strip()
    if not name.endswith(".py"):
        target_path = Path(f"{name}.py")
    else:
        target_path = Path(name)

    if target_path.exists():
        print(f"\x1b[1;31mError:\x1b[0m File '{target_path}' already exists.")
        return 1

    target_path.write_text(NEW_APP_TEMPLATE, encoding="utf-8")
    print(f"\x1b[1;32mCreated:\x1b[0m {target_path}")
    print(f"Run your application with: \x1b[1mpython3 {target_path}\x1b[0m or \x1b[1mespresso run {target_path}\x1b[0m")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="espresso",
        description="Espresso: Lightweight, declarative Elm Architecture (TEA) TUI framework for Python.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"espressoTUI {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # espresso list
    subparsers.add_parser("list", help="List all built-in example applications")

    # espresso run <target>
    run_parser = subparsers.add_parser("run", help="Run an example by ID or run a script")
    run_parser.add_argument("target", help="Example number (e.g. 14, 01) or python file path")

    # espresso gallery
    subparsers.add_parser("gallery", help="Launch interactive component gallery")

    # espresso new <name>
    new_parser = subparsers.add_parser("new", help="Scaffold a new Espresso TEA application")
    new_parser.add_argument("name", help="Name of the new application file (e.g. my_app.py)")

    parsed_args = parser.parse_args(argv)

    if parsed_args.command == "list":
        return cmd_list(parsed_args)
    elif parsed_args.command == "run":
        return cmd_run(parsed_args)
    elif parsed_args.command == "gallery":
        return cmd_gallery(parsed_args)
    elif parsed_args.command == "new":
        return cmd_new(parsed_args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
