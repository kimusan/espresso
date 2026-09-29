#!/usr/bin/env python3
"""Example 6: Git Commit Helper TUI.

A practical command-line developer utility built with Espresso:
- Select Conventional Commit type (feat, fix, docs, refactor, test, chore)
- Input scope and commit summary
- Preview the formatted commit message with Crema box styling
- Print the exact git commit command upon exit
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, quit_app
from espresso.beans import Column, Table, TextInput
from espresso.crema import (
    Align,
    DOUBLE_BORDER,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
)


class CommitHelper(Model):
    def __init__(self) -> None:
        self.step = 0  # 0: Select Type, 1: Enter Scope, 2: Enter Description, 3: Completed
        self.commit_type = "feat"
        self.scope = ""
        self.description = ""

        # Type selection table
        cols = [Column("Type", 10), Column("Description", 45)]
        rows = [
            ["feat", "A new feature for the user or system"],
            ["fix", "A bug fix"],
            ["docs", "Documentation only changes"],
            ["style", "Formatting, missing semi colons, etc."],
            ["refactor", "A code change that neither fixes a bug nor adds a feature"],
            ["perf", "A code change that improves performance"],
            ["test", "Adding missing tests or correcting existing tests"],
            ["chore", "Changes to build process, tooling, or dependencies"],
        ]
        self.type_table = Table(cols, rows, height=8)

        # Inputs
        self.scope_input = TextInput(placeholder="e.g. core, crema, auth (optional)", prompt="Scope: ")
        self.desc_input = TextInput(placeholder="e.g. add support for truecolor gradients", prompt="Summary: ")

        self.box_style = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .padding(1, 2)
            .width(68)
        )

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="ctrl+c" | "esc"):
                return self, quit_app

        # Step 0: Type Table
        if self.step == 0:
            if isinstance(msg, KeyMsg) and msg == "enter":
                selected = self.type_table.selected_row
                if selected:
                    self.commit_type = selected[0]
                    self.step = 1
                return self, None
            self.type_table, cmd = self.type_table.update(msg)
            return self, cmd

        # Step 1: Scope Input
        elif self.step == 1:
            if isinstance(msg, KeyMsg) and msg == "enter":
                self.scope = self.scope_input.value.strip()
                self.step = 2
                return self, None
            self.scope_input, cmd = self.scope_input.update(msg)
            return self, cmd

        # Step 2: Description Input
        elif self.step == 2:
            if isinstance(msg, KeyMsg) and msg == "enter":
                if self.desc_input.value.strip():
                    self.description = self.desc_input.value.strip()
                    self.step = 3
                return self, None
            self.desc_input, cmd = self.desc_input.update(msg)
            return self, cmd

        # Step 3: Finished
        elif self.step == 3:
            if isinstance(msg, KeyMsg) and msg in ("enter", "q"):
                return self, quit_app

        return self, None

    def formatted_message(self) -> str:
        if self.scope:
            return f"{self.commit_type}({self.scope}): {self.description}"
        return f"{self.commit_type}: {self.description}"

    def view(self) -> str:
        header = (
            Style()
            .bold(True)
            .foreground("#FFFFFF")
            .background("#7D56F4")
            .padding(0, 2)
            .render("☕ CONVENTIONAL COMMIT HELPER")
        )

        steps_label = ["Select Type", "Enter Scope", "Enter Summary", "Review & Confirm"][self.step]
        sub = (
            Style()
            .foreground("#888888")
            .margin(0, 0, 1, 0)
            .render(f"Step {self.step + 1} of 4: {steps_label}")
        )

        body: str
        if self.step == 0:
            body = self.box_style.render(
                "Choose the Conventional Commit type:\n\n"
                f"{self.type_table.view()}\n\n"
                "\033[2m[↑/↓, k/j] Navigate   [Enter] Select\033[0m"
            )
        elif self.step == 1:
            body = self.box_style.render(
                f"Selected type: \033[1;32m{self.commit_type}\033[0m\n\n"
                "Enter an optional scope identifier (e.g. parser, api, ui):\n\n"
                f"{self.scope_input.view()}\n\n"
                "\033[2m[Enter] Continue (or leave empty for none)\033[0m"
            )
        elif self.step == 2:
            body = self.box_style.render(
                f"Selected type:  \033[1;32m{self.commit_type}\033[0m\n"
                f"Scope:          \033[1;36m{self.scope or '(none)'}\033[0m\n\n"
                "Enter a concise imperative description:\n\n"
                f"{self.desc_input.view()}\n\n"
                "\033[2m[Enter] Generate Commit\033[0m"
            )
        else:
            commit_str = self.formatted_message()
            body = self.box_style.copy().border_foreground("#00E676").render(
                "\033[1;32m✔ Commit Message Generated Successfully!\033[0m\n\n"
                f"  \033[1;37m{commit_str}\033[0m\n\n"
                f"Command to execute:\n"
                f"  \033[1;33mgit commit -m \"{commit_str}\"\033[0m\n\n"
                "\033[2mPress [Enter] or [q] to exit\033[0m"
            )

        return join_vertical(Align.LEFT, header, sub, body)


if __name__ == "__main__":
    app = CommitHelper()
    p = Program(app)
    p.run()

    if app.step == 3:
        print("\n\033[1;32mCopied commit message:\033[0m")
        print(f"git commit -m \"{app.formatted_message()}\"")
