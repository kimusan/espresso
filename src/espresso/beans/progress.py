"""Progress component for customizable progress bars."""

from __future__ import annotations

import math

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style


class Progress(Model):
    """Progress bar component."""

    def __init__(
        self,
        width: int = 40,
        percent: float = 0.0,
        fill_char: str = "█",
        empty_char: str = "░",
        show_percentage: bool = True,
        fill_style: Style | None = None,
        empty_style: Style | None = None,
    ) -> None:
        self.width = max(10, width)
        val = 0.0 if math.isnan(percent) else percent
        self.percent = max(0.0, min(1.0, val))
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.show_percentage = show_percentage

        self.fill_style = fill_style or Style().foreground("#00E676")
        self.empty_style = empty_style or Style().foreground("#444444")

    def init(self) -> Cmd | None:
        """Initialize component lifecycle (no-op for Progress)."""
        return None

    def set_percent(self, p: float) -> None:
        """Set the completion ratio clamped between 0.0 and 1.0."""
        val = 0.0 if math.isnan(p) else p
        self.percent = max(0.0, min(1.0, val))

    def update(self, msg: Msg) -> tuple[Progress, Cmd | None]:
        """Update progress state on incoming messages (no-op for static Progress)."""
        return self, None

    def view(self) -> str:
        """Render the styled progress bar with filled, empty, and optional percentage cells."""
        pct_text = f" {int(round(self.percent * 100)):3d}%" if self.show_percentage else ""
        bar_width = max(1, self.width - len(pct_text))

        filled_cells = int(round(bar_width * self.percent))
        empty_cells = bar_width - filled_cells

        filled_str = self.fill_char * filled_cells
        empty_str = self.empty_char * empty_cells

        return f"{self.fill_style.render(filled_str)}{self.empty_style.render(empty_str)}{pct_text}"

