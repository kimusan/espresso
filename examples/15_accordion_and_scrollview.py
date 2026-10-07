#!/usr/bin/env python3
"""Example 15: Accordion & ScrollView Showcase.

Demonstrates:
1. Accordion bean wrapping diverse child components:
   - Section 1: User Profile (TextInput beans)
   - Section 2: Preferences (Switch bean)
   - Section 3: Performance Metrics (Table bean)
   - Section 4: Live Service Logs (Nested ScrollView bean with scrollbar)
2. Single-expand vs Multi-expand modes (toggle with 'm')
3. Keyboard navigation (j/k, Enter/Space, Tab to focus child, Esc to unfocus)
4. Mouse interaction (clicking headers, scrolling with wheel)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, MouseMsg, Msg, Program, batch, quit_app
from espresso.beans import (
    Accordion,
    AccordionItem,
    AccordionSelectMsg,
    AccordionToggleMsg,
    Column,
    ScrollView,
    Switch,
    Table,
    TextInput,
)
from espresso.crema import ROUNDED_BORDER, Style, join_vertical


SAMPLE_LOGS = "\n".join([
    "[2026-10-07 20:00:01] [INFO] System kernel booted successfully.",
    "[2026-10-07 20:00:02] [INFO] Loading network interfaces: eth0, lo, wg0.",
    "[2026-10-07 20:00:03] [DEBUG] Initializing cryptographic keystore (Ed25519).",
    "[2026-10-07 20:00:05] [INFO] Connected to primary Postgres replica (10.0.4.12:5432).",
    "[2026-10-07 20:00:08] [DEBUG] Cache warmed: 4,892 items indexed in 18ms.",
    "[2026-10-07 20:00:11] [INFO] REST API gateway listening on 0.0.0.0:8080.",
    "[2026-10-07 20:00:14] [WARN] Ingress queue latency spiked to 42ms (threshold 30ms).",
    "[2026-10-07 20:00:15] [INFO] Auto-scaler spun up 2 worker nodes in us-east-1.",
    "[2026-10-07 20:00:19] [DEBUG] GC pause duration: 1.2ms (Gen0: 42, Gen1: 3).",
    "[2026-10-07 20:00:22] [INFO] SSL certificate renewed for *.service.internal.",
    "[2026-10-07 20:00:25] [DEBUG] Synchronized clock with time.google.com (offset: 0.12ms).",
    "[2026-10-07 20:00:30] [INFO] Healthcheck probe status: 200 OK across all pods.",
    "[2026-10-07 20:00:35] [DEBUG] Routine snapshot saved: snap-20261007-001 (142 MB).",
    "[2026-10-07 20:00:41] [INFO] All services operating at nominal efficiency.",
])


class ProfilePanel(Model):
    """Simple form container wrapping two TextInput beans."""

    def __init__(self) -> None:
        self.username = TextInput(placeholder="e.g. kimschulz", prompt="Username: ")
        self.email = TextInput(placeholder="e.g. kim@schulz.dk", prompt="Email:    ")
        self.active_field = 0
        self.username.focus()

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        if self.active_field == 0:
            self.username.focus()
        else:
            self.email.focus()

    def blur(self) -> None:
        self.username.blur()
        self.email.blur()

    def update(self, msg: Msg) -> tuple[ProfilePanel, Cmd | None]:
        if isinstance(msg, KeyMsg):
            if msg.key in ("down", "tab"):
                self.active_field = 1
                self.username.blur()
                self.email.focus()
                return self, None
            elif msg.key in ("up", "shift+tab"):
                self.active_field = 0
                self.email.blur()
                self.username.focus()
                return self, None

        if self.active_field == 0:
            self.username, cmd = self.username.update(msg)
        else:
            self.email, cmd = self.email.update(msg)
        return self, cmd

    def view(self) -> str:
        return f"{self.username.view()}\n{self.email.view()}"


class PreferencesPanel(Model):
    """Preferences container wrapping a Switch bean."""

    def __init__(self) -> None:
        self.sw_telemetry = Switch(label="Anonymous Telemetry", value=True)
        self.sw_notifications = Switch(label="Email Alerts", value=False)
        self.active_idx = 0
        self.sw_telemetry.focus()

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        if self.active_idx == 0:
            self.sw_telemetry.focus()
        else:
            self.sw_notifications.focus()

    def blur(self) -> None:
        self.sw_telemetry.blur()
        self.sw_notifications.blur()

    def update(self, msg: Msg) -> tuple[PreferencesPanel, Cmd | None]:
        if isinstance(msg, KeyMsg):
            if msg.key in ("down", "tab"):
                self.active_idx = 1
                self.sw_telemetry.blur()
                self.sw_notifications.focus()
                return self, None
            elif msg.key in ("up", "shift+tab"):
                self.active_idx = 0
                self.sw_notifications.blur()
                self.sw_telemetry.focus()
                return self, None

        if self.active_idx == 0:
            self.sw_telemetry, cmd = self.sw_telemetry.update(msg)
        else:
            self.sw_notifications, cmd = self.sw_notifications.update(msg)
        return self, cmd

    def view(self) -> str:
        return f"{self.sw_telemetry.view()}\n{self.sw_notifications.view()}"


class AccordionShowcaseApp(Model):
    def __init__(self) -> None:
        # 1. Child bean for Section 1: User Profile
        self.profile = ProfilePanel()

        # 2. Child bean for Section 2: Preferences
        self.prefs = PreferencesPanel()

        # 3. Child bean for Section 3: Metrics Table
        table_cols = [
            Column("Cluster", 10),
            Column("Region", 12),
            Column("Load", 8),
            Column("Status", 10),
        ]
        table_rows = [
            ["kube-prod-1", "us-east-1", "68%", "Healthy"],
            ["kube-prod-2", "eu-west-1", "42%", "Healthy"],
            ["kube-prod-3", "ap-southeast", "89%", "Warning"],
            ["kube-backup", "us-west-2", "12%", "Idle"],
        ]
        self.metrics_table = Table(columns=table_cols, rows=table_rows)

        # 4. Child bean for Section 4: ScrollView with logs
        self.logs_scroll = ScrollView(child=SAMPLE_LOGS, width=62, height=6)

        # Build Accordion
        items = [
            AccordionItem(
                id="profile",
                title="Account Profile",
                content=self.profile,
                expanded=True,
                badge="Required",
            ),
            AccordionItem(
                id="prefs",
                title="System Preferences",
                content=self.prefs,
                badge="2 settings",
            ),
            AccordionItem(
                id="metrics",
                title="Infrastructure Clusters",
                content=self.metrics_table,
                badge="4 pods",
            ),
            AccordionItem(
                id="logs",
                title="Real-time Server Logs",
                content=self.logs_scroll,
                badge="14 lines",
            ),
        ]

        self.accordion = Accordion(items=items, width=66, allow_multiple=False)

        # Activity message
        self.status_msg = "Use ↑/↓ or j/k to navigate, Enter to toggle, Tab to focus child."

    def init(self) -> Cmd | None:
        return self.accordion.init()

    def update(self, msg: Msg) -> tuple[AccordionShowcaseApp, Cmd | None]:
        if isinstance(msg, KeyMsg):
            # Global quit
            if msg.key in ("q", "ctrl+c") and not self.accordion.focus_child:
                return self, quit_app()

            # Toggle allow_multiple mode
            if msg.key == "m" and not self.accordion.focus_child:
                self.accordion.allow_multiple = not self.accordion.allow_multiple
                mode_str = "Multi-Expand" if self.accordion.allow_multiple else "Single-Expand"
                self.status_msg = f"Toggled mode: {mode_str}"
                return self, None

        # Capture accordion status changes
        if isinstance(msg, AccordionToggleMsg):
            action = "Expanded" if msg.expanded else "Collapsed"
            self.status_msg = f"{action} section: {msg.item_id}"
        elif isinstance(msg, AccordionSelectMsg):
            self.status_msg = f"Selected header: {msg.item_id}"

        self.accordion, cmd = self.accordion.update(msg)
        return self, cmd

    def view(self) -> str:
        # Title banner
        title_style = (
            Style()
            .bold(True)
            .foreground("#FFFFFF")
            .background("#7D56F4")
            .padding(0, 2)
        )
        title = title_style.render("Espresso Beans: Accordion & ScrollView Showcase")

        # Mode tag
        mode_str = "Multi-Expand" if self.accordion.allow_multiple else "Single-Expand"
        focus_str = "● Child Focused" if self.accordion.focus_child else "○ Header Nav"
        meta_style = Style().foreground("#00E5FF").bold(True)
        meta = meta_style.render(f"Mode: [{mode_str}] | Focus: [{focus_str}]")

        # Status text
        status_style = Style().foreground("#AAAAAA").italic(True)
        status = status_style.render(f"Status: {self.status_msg}")

        # Hotkeys help footer
        help_style = Style().foreground("#888899").faint(True)
        help_text = help_style.render(
            "Keys: ↑/↓, j/k: Navigate | Enter/Space: Toggle | Tab: Focus Child | Esc: Back | m: Mode | q: Quit"
        )

        # Card container
        card_style = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .padding(1, 2)
            .width(72)
        )

        content = join_vertical(
            0,
            title,
            "",
            meta,
            "",
            self.accordion.view(),
            "",
            status,
            "",
            help_text,
        )

        return card_style.render(content)


def main() -> None:
    app = AccordionShowcaseApp()
    Program(app).run()


if __name__ == "__main__":
    main()
