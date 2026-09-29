#!/usr/bin/env python3
"""Example 5: Beans Showcase - Interactive Coffee Order Wizard.

Demonstrates composing multiple Beans components into a unified Elm Architecture app:
- TextInput: Enter customer name
- Table: Select coffee origin and blend
- Spinner & Progress: Simulating roasting and extraction
- Viewport: Scrollable order summary and tasting notes
- Crema: Rich styling, rounded borders, and layout
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, batch, quit_app, tick
from espresso.beans import (
    COFFEE,
    Column,
    Progress,
    Spinner,
    SpinnerTickMsg,
    Table,
    TextInput,
    Viewport,
)
from espresso.crema import (
    Align,
    DOUBLE_BORDER,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
)


class BrewTickMsg(Msg):
    pass


class BeansShowcase(Model):
    def __init__(self) -> None:
        self.step = 0  # 0: Name input, 1: Bean selection, 2: Brewing, 3: Receipt

        # Component 1: TextInput
        self.text_input = TextInput(placeholder="e.g. Kim", prompt="☕ Your Name: ")

        # Component 2: Table
        columns = [
            Column("Code", 6),
            Column("Roast / Origin", 24),
            Column("Notes", 22),
            Column("Price", 8, Align.RIGHT),
        ]
        rows = [
            ["ETH-1", "Ethiopia Yirgacheffe", "Floral, Bergamot, Peach", "$4.50"],
            ["COL-2", "Colombia Huila Supremo", "Caramel, Red Apple, Cocoa", "$4.00"],
            ["KEN-3", "Kenya Nyeri Peaberry", "Blackcurrant, Grapefruit", "$5.00"],
            ["GUA-4", "Guatemala Antigua", "Milk Chocolate, Spices", "$4.25"],
            ["ITA-5", "Classic Italian Espresso", "Dark Chocolate, Crema", "$3.75"],
        ]
        self.table = Table(columns, rows, height=6)

        # Component 3: Spinner & Progress
        self.spinner = Spinner(frames=COFFEE, fps=4.0, style=Style().bold(True).foreground("#FF9100"))
        self.progress = Progress(width=42, percent=0.0)
        self.brew_progress = 0.0

        # Component 4: Viewport
        self.viewport = Viewport(width=62, height=8)

        self.box_style = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .padding(1, 2)
            .width(66)
        )

    def init(self) -> Cmd | None:
        return self.spinner.init()

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        # Global quit
        if isinstance(msg, KeyMsg) and msg in ("ctrl+c", "esc"):
            return self, quit_app

        # Always update spinner
        if isinstance(msg, SpinnerTickMsg):
            self.spinner, cmd = self.spinner.update(msg)
            return self, cmd

        # Step 0: Customer Name Input
        if self.step == 0:
            if isinstance(msg, KeyMsg) and msg == "enter":
                if self.text_input.value.strip():
                    self.step = 1
                return self, None
            self.text_input, cmd = self.text_input.update(msg)
            return self, cmd

        # Step 1: Bean Selection Table
        elif self.step == 1:
            if isinstance(msg, KeyMsg) and msg == "enter":
                self.step = 2
                self.brew_progress = 0.0
                return self, tick(0.08, BrewTickMsg())
            self.table, cmd = self.table.update(msg)
            return self, cmd

        # Step 2: Brewing Simulation
        elif self.step == 2:
            if isinstance(msg, BrewTickMsg):
                self.brew_progress += 0.04
                self.progress.set_percent(self.brew_progress)
                if self.brew_progress >= 1.0:
                    self.step = 3
                    self._prepare_receipt()
                    return self, None
                return self, tick(0.08, BrewTickMsg())

        # Step 3: Receipt Viewport
        elif self.step == 3:
            if isinstance(msg, KeyMsg) and msg == "q":
                return self, quit_app
            self.viewport, cmd = self.viewport.update(msg)
            return self, cmd

        return self, None

    def _prepare_receipt(self) -> None:
        selected = self.table.selected_row or ["???", "Special Blend", "Notes", "$4.00"]
        name = self.text_input.value or "Valued Guest"
        receipt = [
            f"☕ ESPRESSO ARTISAN RECEIPT",
            f"────────────────────────────────────────────────────────",
            f"Customer:    {name}",
            f"Selection:   {selected[1]} ({selected[0]})",
            f"Flavor:      {selected[2]}",
            f"Total Paid:  {selected[3]}",
            f"",
            f"Extraction Report:",
            f"  • Extraction Pressure:  9.0 bar (Consistent)",
            f"  • Water Temperature:    93.2 °C",
            f"  • Ratio:                18g in / 36g out (1:2)",
            f"  • Extraction Time:      27.5 seconds",
            f"  • Crema Quality:        Golden hazelnut with tiger striping",
            f"",
            f"Thank you for ordering with Espresso!",
            f"Press [q] to exit or [↑/↓] to scroll receipt.",
        ]
        self.viewport.set_content("\n".join(receipt))

    def view(self) -> str:
        header = (
            Style()
            .bold(True)
            .foreground("#FFFFFF")
            .background("#7D56F4")
            .padding(0, 2)
            .render("☕ ESPRESSO CAFE • COMPONENT SHOWCASE")
        )

        step_indicator = (
            Style()
            .foreground("#AAAAAA")
            .margin(0, 0, 1, 0)
            .render(f"Step {self.step + 1} of 4: " + ["Enter Name", "Select Beans", "Brewing", "Order Summary"][self.step])
        )

        content: str
        if self.step == 0:
            prompt_box = (
                "Please enter your name to begin your custom roast order.\n\n"
                f"{self.text_input.view()}\n\n"
                "\033[2mPress [Enter] to continue, [Esc] to quit\033[0m"
            )
            content = self.box_style.render(prompt_box)

        elif self.step == 1:
            table_box = (
                "Select your preferred coffee bean profile:\n\n"
                f"{self.table.view()}\n\n"
                "\033[2m[↑/↓, k/j] Navigate   [Enter] Confirm Selection\033[0m"
            )
            content = self.box_style.render(table_box)

        elif self.step == 2:
            brew_box = (
                f"{self.spinner.view()} Brewing your custom espresso shot...\n\n"
                f"{self.progress.view()}\n\n"
                "\033[2mCalibrating grind size and pre-infusion pressure...\033[0m"
            )
            content = self.box_style.render(brew_box)

        else:
            receipt_box = (
                f"{self.viewport.view()}\n\n"
                f"\033[2mScroll: [↑/↓, k/j]   Exit: [q]\033[0m"
            )
            content = self.box_style.render(receipt_box)

        return join_vertical(Align.LEFT, header, step_indicator, content)


if __name__ == "__main__":
    p = Program(BeansShowcase())
    p.run()
