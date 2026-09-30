"""Metric and KPI stat card display component.

Modeled after ortizalec/bubbles.
Provides individual Metric cards, badges, and MetricGroup collections
with trends, deltas, units, and responsive layouts (CARD, TAG, LIST).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER, Border
from espresso.crema.layout import join_horizontal, join_vertical
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


class MetricTrend(Enum):
    """Trend direction for delta changes."""

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class MetricLayout(Enum):
    """Visual presentation format for metrics."""

    CARD = "card"    # Boxed card with large value, label, and delta
    TAG = "tag"      # Compact badge [ Label: Value (delta) ]
    LIST = "list"    # Tabular key-value row


class LayoutDirection(Enum):
    """Layout direction for MetricGroup."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class Metric:
    """An individual metric or KPI stat value."""

    label: str
    value: str | int | float
    unit: str = ""
    delta: str = ""
    trend: MetricTrend = MetricTrend.NEUTRAL
    description: str = ""
    invert_trend: bool = False  # If True, DOWN is green and UP is red (e.g. latency, error rate)
    width: int = 24

    def render_card(self, border: Border = ROUNDED_BORDER, border_fg: str = "#7D56F4") -> str:
        """Render this metric as a bordered dashboard card."""
        w = max(16, self.width)
        inner_w = w - 4

        # 1. Label
        lbl_str = Style().bold(True).foreground("#8888AA").render(truncate_ansi(self.label.upper(), inner_w))

        # 2. Value + Unit
        val_str = str(self.value)
        if self.unit:
            val_formatted = f"{Style().bold(True).foreground('#FAFAFA').render(val_str)} {Style().foreground('#00E5FF').render(self.unit)}"
        else:
            val_formatted = Style().bold(True).foreground("#FAFAFA").render(val_str)

        lines = [lbl_str, val_formatted]

        # 3. Delta + Trend indicator
        if self.delta:
            is_positive = (self.trend == MetricTrend.UP)
            if self.invert_trend:
                is_good = (self.trend == MetricTrend.DOWN)
            else:
                is_good = is_positive

            if self.trend == MetricTrend.UP:
                arrow = "▲"
            elif self.trend == MetricTrend.DOWN:
                arrow = "▼"
            else:
                arrow = "•"

            trend_color = "#00E676" if is_good else "#FF5252" if (self.trend != MetricTrend.NEUTRAL) else "#B0B0B0"
            delta_styled = Style().foreground(trend_color).render(f"{arrow} {self.delta}")
            lines.append(delta_styled)

        # 4. Optional description
        if self.description:
            lines.append(Style().foreground("#666688").render(truncate_ansi(self.description, inner_w)))

        card_content = "\n".join(lines)
        return (
            Style()
            .border(border)
            .border_foreground(border_fg)
            .padding(0, 1)
            .width(w - 2)
            .render(card_content)
        )

    def render_tag(self) -> str:
        """Render this metric as a compact pill badge."""
        val = f"{self.value}{self.unit}"
        delta_part = f" ({self.delta})" if self.delta else ""
        text = f" {self.label}: {val}{delta_part} "
        return Style().bold(True).foreground("#FFFFFF").background("#3F51B5").render(text)

    def render_list_item(self, total_width: int = 40) -> str:
        """Render this metric as a key-value row."""
        lbl = self.label
        val = f"{self.value} {self.unit}".strip()
        if self.delta:
            arrow = "▲" if self.trend == MetricTrend.UP else "▼" if self.trend == MetricTrend.DOWN else ""
            val += f" {arrow}{self.delta}"

        lbl_w = string_width(lbl)
        val_w = string_width(val)
        dots_w = max(2, total_width - lbl_w - val_w - 2)
        dots = " " + ("." * (dots_w - 2)) + " "

        return (
            Style().foreground("#E0E0E0").render(lbl)
            + Style().foreground("#555577").render(dots)
            + Style().bold(True).foreground("#00E5FF").render(val)
        )


class MetricGroup(Model):
    """Container managing multiple Metric items in a cohesive layout."""

    def __init__(
        self,
        metrics: Sequence[Metric] = (),
        layout: MetricLayout = MetricLayout.CARD,
        direction: LayoutDirection = LayoutDirection.HORIZONTAL,
        width: int | None = None,
    ) -> None:
        self.metrics = list(metrics)
        self.layout = layout
        self.direction = direction
        self.width = width

    def add_metric(self, metric: Metric) -> MetricGroup:
        self.metrics.append(metric)
        return self

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MetricGroup, Cmd | None]:
        return self, None

    def view(self) -> str:
        if not self.metrics:
            return ""

        if self.layout == MetricLayout.TAG:
            rendered = [m.render_tag() for m in self.metrics]
            return "  ".join(rendered) if self.direction == LayoutDirection.HORIZONTAL else "\n".join(rendered)

        elif self.layout == MetricLayout.LIST:
            w = self.width or 40
            rendered = [m.render_list_item(total_width=w) for m in self.metrics]
            return "\n".join(rendered)

        else:  # CARD
            rendered = [m.render_card() for m in self.metrics]
            if self.direction == LayoutDirection.HORIZONTAL:
                return join_horizontal(Align.TOP, *rendered)
            else:
                return join_vertical(Align.LEFT, *rendered)
