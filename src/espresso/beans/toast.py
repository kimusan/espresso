"""Transient toast notifications component."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style


class ToastLevel(Enum):
    """Severity level of a Toast notification."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ToastItem:
    """An individual active toast notification."""

    id: str
    message: str
    level: ToastLevel
    duration_seconds: float = 3.0


@dataclass(frozen=True)
class ToastDismissMsg(Msg):
    """Message emitted when a toast's duration expires and it should be removed."""

    toast_id: str


class ToastManager(Model):
    """Manages active toast notifications, auto-dismiss timers, and rendering.

    Modeled after daltonsw/bubbleup.
    """

    def __init__(self) -> None:
        self.toasts: list[ToastItem] = []

    @property
    def has_toasts(self) -> bool:
        """Return True if there are currently any active toasts."""
        return len(self.toasts) > 0

    def add(
        self,
        message: str,
        level: ToastLevel = ToastLevel.INFO,
        duration: float = 3.0,
    ) -> tuple[ToastItem, Cmd]:
        """Add a new toast and return an asynchronous auto-dismiss TEA command."""
        t_id = str(uuid.uuid4())[:8]
        item = ToastItem(id=t_id, message=message, level=level, duration_seconds=duration)
        self.toasts.append(item)

        async def _dismiss_timer() -> Msg:
            await asyncio.sleep(duration)
            return ToastDismissMsg(toast_id=t_id)

        return item, _dismiss_timer

    def dismiss(self, toast_id: str) -> None:
        """Remove a toast by ID."""
        self.toasts = [t for t in self.toasts if t.id != toast_id]

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[ToastManager, Cmd | None]:
        """Process toast dismiss notifications."""
        if isinstance(msg, ToastDismissMsg):
            self.dismiss(msg.toast_id)
            return self, None
        return self, None

    def view(self) -> str:
        """Render all active toast cards stacked vertically."""
        if not self.toasts:
            return ""

        rendered_toasts: list[str] = []
        for t in self.toasts:
            if t.level == ToastLevel.SUCCESS:
                icon = "✔ "
                accent = "#00E676"
            elif t.level == ToastLevel.WARNING:
                icon = "⚠ "
                accent = "#FFD700"
            elif t.level == ToastLevel.ERROR:
                icon = "✖ "
                accent = "#FF5252"
            else:  # INFO
                icon = "ℹ "
                accent = "#00E5FF"

            toast_card = (
                Style()
                .border(ROUNDED_BORDER)
                .border_foreground(accent)
                .background("#181824")
                .foreground("#FAFAFA")
                .bold(True)
                .padding(0, 1)
                .render(f"{icon}{t.message}")
            )
            rendered_toasts.append(toast_card)

        return "\n".join(rendered_toasts)
