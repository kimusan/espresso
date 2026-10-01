#!/usr/bin/env python3
"""Example 13: Physics & Developer Tools Showcase.

Demonstrates:
1. Spring: Damped harmonic oscillator physics simulator with live trajectory and presets.
2. Confetti: 2D terminal particle physics emitter with gravity, drag, and Crema overlay.
3. DiffViewer: High-fidelity Git diff visualizer with Unified/Split views and intra-line word diffs.
4. Form & FormBuilder: Multi-field composite form with live validation and confetti celebration.
"""

from __future__ import annotations

import collections
import math
import random
import sys
from pathlib import Path
from typing import Any

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import (
    Cmd,
    KeyMsg,
    Model,
    MouseButton,
    MouseMsg,
    Msg,
    Program,
    WindowSizeMsg,
    batch,
    quit_app,
)
from espresso.beans import (
    Confetti,
    ConfettiMode,
    ConfettiTickMsg,
    DiffMode,
    DiffViewer,
    Form,
    FormField,
    FormSubmitMsg,
    Slider,
    Spring,
    SpringTickMsg,
    Tabs,
    TabStyle,
    TextInput,
)
from espresso.crema import (
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
    string_width,
    strip_ansi,
)

# Sample Git diff comparison
OLD_HANDLER_CODE = '''# Core connection handler
def process_request(request):
    # Synchronous blocking call
    payload = json.loads(request.raw_body)
    user_id = payload.get("user_id")
    user = database.query_user(user_id)
    if user is None:
        return {"status": 404, "error": "User not found"}
    
    # Legacy metric tracking
    metrics.increment("request_count")
    return {"status": 200, "user": user.name}
'''

NEW_HANDLER_CODE = '''# Core connection handler (Async TEA architecture)
async def process_request(request: Request) -> Response:
    # Asynchronous non-blocking coroutine
    payload = await request.json()
    user_id = payload.get("user_id")
    user = await database.fetch_user(user_id)
    if user is None:
        return Response(status=404, error="User not found")
    
    # Modern telemetry streaming
    telemetry.record_event("user_resolved", user_id=user_id)
    return Response(status=200, user=user.display_name, verified=True)
'''


class PhysicsAndToolsApp(Model):
    """Flagship interactive application showcasing Wave 2 Beans."""

    def __init__(self) -> None:
        self.width = 92
        self.height = 28
        self.active_tab = 0

        # Tabs navigation
        self.tab_titles = ["1 Spring Physics", "2 Confetti", "3 Git Diff", "4 Form Builder"]
        self.tabs = Tabs(
            titles=self.tab_titles,
            active_tab=0,
            tab_style=TabStyle.PILL,
            show_numbers=False,
        )

        # ---------------- Tab 1: Spring Physics ----------------
        self.spring = Spring(
            value=10.0,
            target=80.0,
            min_val=0.0,
            max_val=100.0,
            stiffness=120.0,
            damping=0.35,
            width=55,
            label="Oscillator:",
            tag="spring_demo",
        )
        self.spring_preset_name = "Bouncy (ζ=0.35)"
        self.spring_history: collections.deque[float] = collections.deque(maxlen=48)
        self.spring_history.append(10.0)

        # ---------------- Tab 2: Confetti Celebration ----------------
        self.confetti = Confetti(
            width=self.width - 6,
            height=self.height - 8,
            gravity=18.0,
            drag=0.85,
            fps=30.0,
            tag="confetti_tab",
        )

        # ---------------- Tab 3: Git DiffViewer ----------------
        self.diff_viewer = DiffViewer(
            old_text=OLD_HANDLER_CODE,
            new_text=NEW_HANDLER_CODE,
            fromfile="a/src/handler.py",
            tofile="b/src/handler.py",
            mode=DiffMode.UNIFIED,
            width=self.width - 4,
            height=self.height - 7,
        )

        # ---------------- Tab 4: Form Builder ----------------
        self.name_input = TextInput(placeholder="e.g. Ada Lovelace", char_limit=40)
        self.email_input = TextInput(placeholder="e.g. ada@example.org", char_limit=50)
        self.exp_slider = Slider(
            min_val=0,
            max_val=25,
            value=6,
            step=1,
            width=32,
            label="Python Experience:",
            value_format="{value:.0f} years",
        )
        self.role_input = TextInput(placeholder="e.g. Core Maintainer, TUI Dev", char_limit=40)

        def _validate_email(val: Any) -> str | None:
            s = str(val or "").strip()
            if not s:
                return "Email is required"
            if "@" not in s or "." not in s.split("@")[-1]:
                return "Enter a valid email (e.g. user@domain.com)"
            return None

        self.form = Form(
            fields=[
                FormField(id="name", label="Full Name", bean=self.name_input, required=True, hint="Your developer moniker"),
                FormField(id="email", label="Email Address", bean=self.email_input, validator=_validate_email, required=True, hint="Used for release announcements"),
                FormField(id="exp", label="Python Experience", bean=self.exp_slider, hint="Years designing Python systems"),
                FormField(id="role", label="Primary Focus Area", bean=self.role_input, hint="Optional area of specialization"),
            ],
            title="Developer Registration & Survey",
            submit_label="🚀 Submit Profile",
            width=self.width - 6,
        )
        self.submitted_profile: dict[str, Any] | None = None
        self.form_confetti = Confetti(
            width=self.width - 6,
            height=self.height - 8,
            gravity=19.0,
            drag=0.88,
            fps=30.0,
            tag="form_confetti",
        )

        # Styles
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.border_style = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4")
        self.footer_style = Style().foreground("#8888AA")
        self.badge_style = Style().bold(True).foreground("#000000").background("#00E5FF").padding(0, 1)

        self._sync_sizes()

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        c_spring = self.spring.init()
        if c_spring:
            cmds.append(c_spring)
        c_conf = self.confetti.init()
        if c_conf:
            cmds.append(c_conf)
        return batch(*cmds) if cmds else None

    def _sync_sizes(self) -> None:
        inner_w = max(40, self.width - 4)
        inner_h = max(10, self.height - 6)

        self.spring.width = max(35, inner_w - 6)
        self.confetti.set_size(inner_w - 2, inner_h)
        self.diff_viewer.set_size(inner_w, inner_h)
        self.form.width = inner_w - 2
        self.form_confetti.set_size(inner_w - 2, inner_h)

        # Set screen offsets for mouse click detection
        self.diff_viewer.set_offset(1, 3)
        self.form.set_offset(2, 4)

    def _apply_spring_preset(self, name: str, damping: float, stiffness: float) -> Cmd:
        self.spring_preset_name = name
        self.spring.spring.damping = damping
        self.spring.spring.stiffness = stiffness
        return self.spring.tick()

    def update(self, msg: Msg) -> tuple[PhysicsAndToolsApp, Cmd | None]:
        cmds: list[Cmd] = []

        if isinstance(msg, WindowSizeMsg):
            self.width = max(60, msg.width)
            self.height = max(20, msg.height)
            self._sync_sizes()
            return self, None

        # Confetti particle tick updates
        if isinstance(msg, ConfettiTickMsg):
            if msg.tag == self.confetti.tag:
                self.confetti, c = self.confetti.update(msg)
                if c:
                    cmds.append(c)
            elif msg.tag == self.form_confetti.tag:
                self.form_confetti, c = self.form_confetti.update(msg)
                if c:
                    cmds.append(c)
            return self, batch(*cmds) if cmds else None

        # Spring tick updates
        if isinstance(msg, SpringTickMsg) and msg.tag == self.spring.tag:
            self.spring, c = self.spring.update(msg)
            self.spring_history.append(self.spring.value)
            if c:
                cmds.append(c)
            return self, batch(*cmds) if cmds else None

        # Form submission message
        if isinstance(msg, FormSubmitMsg):
            self.submitted_profile = msg.values
            c_fire = self.form_confetti.fire(count=65, mode=ConfettiMode.BURST)
            if c_fire:
                cmds.append(c_fire)
            return self, batch(*cmds) if cmds else None

        # Keyboard global navigation
        if isinstance(msg, KeyMsg):
            # Global quit
            if msg.key in ("ctrl+c", "ctrl+q") or (msg.key == "q" and self.active_tab != 3):
                return self, quit_app

            # Quick Tab Switch via F1-F4 or Alt+1..4
            match msg.key:
                case "f1" | "alt+1":
                    self.active_tab = 0
                    self.tabs.set_active(0)
                    return self, None
                case "f2" | "alt+2":
                    self.active_tab = 1
                    self.tabs.set_active(1)
                    return self, None
                case "f3" | "alt+3":
                    self.active_tab = 2
                    self.tabs.set_active(2)
                    return self, None
                case "f4" | "alt+4":
                    self.active_tab = 3
                    self.tabs.set_active(3)
                    return self, None

            # Number keys when not in text input (Tabs 0, 1, 2)
            if self.active_tab in (0, 1, 2) and msg.key in ("1", "2", "3", "4"):
                idx = int(msg.key) - 1
                self.active_tab = idx
                self.tabs.set_active(idx)
                return self, None

            # Tab cycling when not in Form (Tab 3 uses Tab for field focus)
            if self.active_tab != 3:
                if msg.key == "tab":
                    self.active_tab = (self.active_tab + 1) % len(self.tab_titles)
                    self.tabs.set_active(self.active_tab)
                    return self, None
                elif msg.key == "shift+tab":
                    self.active_tab = (self.active_tab - 1) % len(self.tab_titles)
                    self.tabs.set_active(self.active_tab)
                    return self, None

        # Mouse clicks on header tab bar
        if isinstance(msg, MouseMsg) and msg.button == MouseButton.LEFT and msg.y == 0:
            header_w = string_width(self.title_style.render("⚡ ESPRESSO PHYSICS & TOOLS")) + 3
            if msg.x >= header_w:
                cur_x = header_w
                for idx, title in enumerate(self.tab_titles):
                    t_len = string_width(title) + 2
                    if cur_x <= msg.x < cur_x + t_len:
                        self.active_tab = idx
                        self.tabs.set_active(idx)
                        return self, None
                    cur_x += t_len + 2

        # ---------------- Active Tab Event Handling ----------------
        if self.active_tab == 0:
            # Spring Controls
            if isinstance(msg, KeyMsg):
                match msg.key:
                    case "left" | "h":
                        c = self.spring.set_target(max(0.0, self.spring.target - 5.0))
                        cmds.append(c)
                    case "right" | "l":
                        c = self.spring.set_target(min(100.0, self.spring.target + 5.0))
                        cmds.append(c)
                    case "z":
                        cmds.append(self.spring.set_target(0.0))
                    case "x":
                        cmds.append(self.spring.set_target(25.0))
                    case "c":
                        cmds.append(self.spring.set_target(50.0))
                    case "v":
                        cmds.append(self.spring.set_target(75.0))
                    case "b":
                        cmds.append(self.spring.set_target(100.0))
                    case "p" | "P":
                        # Cycle presets
                        presets = [
                            ("Bouncy (ζ=0.35)", 0.35, 120.0),
                            ("Snappy (ζ=0.70)", 0.70, 220.0),
                            ("Critically Damped (ζ=1.0)", 1.0, 140.0),
                            ("Overdamped (ζ=1.85)", 1.85, 90.0),
                        ]
                        curr_idx = 0
                        for i, (p_name, _, _) in enumerate(presets):
                            if p_name == self.spring_preset_name:
                                curr_idx = (i + 1) % len(presets)
                                break
                        new_p = presets[curr_idx]
                        cmds.append(self._apply_spring_preset(new_p[0], new_p[1], new_p[2]))

            elif isinstance(msg, MouseMsg) and msg.button == MouseButton.LEFT:
                # Click along Spring gauge row to set target
                gauge_y = 6
                if msg.y == gauge_y:
                    gauge_x_start = 14
                    gauge_w = 40
                    if gauge_x_start <= msg.x <= gauge_x_start + gauge_w:
                        pct = (msg.x - gauge_x_start) / float(gauge_w)
                        new_tgt = max(0.0, min(100.0, pct * 100.0))
                        cmds.append(self.spring.set_target(new_tgt))

        elif self.active_tab == 1:
            # Confetti Controls
            if isinstance(msg, KeyMsg):
                match msg.key:
                    case "b" | "space":
                        cmds.append(self.confetti.fire(count=60, mode=ConfettiMode.BURST))
                    case "c":
                        cmds.append(self.confetti.fire(count=70, mode=ConfettiMode.CANNON))
                    case "r":
                        cmds.append(self.confetti.fire(count=60, mode=ConfettiMode.RAIN))
                    case "x":
                        self.confetti.clear()

            elif isinstance(msg, MouseMsg) and msg.button == MouseButton.LEFT and msg.y >= 3:
                # Spawn burst centered exactly at click coordinate
                cx = msg.x - 2
                cy = msg.y - 3
                cmds.append(self.confetti.fire(count=55, mode=ConfettiMode.BURST, origin=(cx, cy)))

        elif self.active_tab == 2:
            # DiffViewer Controls
            self.diff_viewer, c = self.diff_viewer.update(msg)
            if c:
                cmds.append(c)

        elif self.active_tab == 3:
            # Form Controls
            if isinstance(msg, KeyMsg) and msg.key == "r" and self.submitted_profile is not None:
                # Reset submitted profile to allow filling again
                self.submitted_profile = None
                return self, None

            self.form, c = self.form.update(msg)
            if c:
                cmds.append(c)

        return self, batch(*cmds) if cmds else None

    def _render_trajectory(self) -> str:
        """Render mini 2D trajectory curve of the spring's historical motion."""
        history = list(self.spring_history)
        if not history:
            return ""

        rows = 4
        cols = min(48, max(20, self.width - 24))
        grid = [[" "] * cols for _ in range(rows)]

        recent = history[-cols:]
        # Pad with initial value if fewer points
        if len(recent) < cols:
            recent = [recent[0]] * (cols - len(recent)) + recent

        for c_idx, val in enumerate(recent):
            pct = max(0.0, min(1.0, val / 100.0))
            r_idx = int(round((1.0 - pct) * (rows - 1)))
            r_idx = max(0, min(rows - 1, r_idx))
            grid[r_idx][c_idx] = "●" if c_idx == cols - 1 else "·"

        rendered_rows: list[str] = []
        for r_idx, row_chars in enumerate(grid):
            pct_level = int(round((1.0 - r_idx / (rows - 1)) * 100))
            prefix = Style().faint(True).render(f"{pct_level:3d}% ┤")
            curve_str = "".join(row_chars)
            curve_styled = Style().foreground("#00E5FF").render(curve_str)
            rendered_rows.append(f"{prefix}{curve_styled}")

        axis = Style().faint(True).render("     └" + "─" * cols + " t →")
        rendered_rows.append(axis)
        return "\n".join(rendered_rows)

    def view(self) -> str:
        # Header bar
        header_title = self.title_style.render("⚡ ESPRESSO PHYSICS & TOOLS")
        tabs_bar = self.tabs.view()
        header = f"{header_title}   {tabs_bar}"

        # Card content based on active tab
        content_view = ""
        card_h = self.height - 2

        if self.active_tab == 0:
            # ---------------- TAB 1: Spring Physics ----------------
            title = Style().bold(True).foreground("#00E5FF").render("🪀 Analytical Damped Harmonic Oscillator Simulation:")
            formula = Style().faint(True).render("Equation of Motion: m·x''(t) + c·x'(t) + k·(x(t) - target) = 0 (Unconditionally Stable Closed-Form)")

            gauge_view = self.spring.view()

            preset_badge = Style().bold(True).foreground("#000000").background("#FFD54F").render(f" Preset: {self.spring_preset_name} ")
            hints = Style().faint(True).render(
                "• Target Controls: Left/Right (±5%) • z=0% • x=25% • c=50% • v=75% • b=100% • Click Gauge\n"
                "• Preset Cycle: Press 'p' to switch between Bouncy, Snappy, Critical, Overdamped"
            )

            traj_title = Style().bold(True).foreground("#A5D6A7").render("Oscillation Trajectory Curve x(t):")
            traj_graph = self._render_trajectory()

            zeta = self.spring.spring.damping
            stiff = self.spring.spring.stiffness
            omega0 = math.sqrt(stiff / self.spring.spring.mass)
            status_text = "✨ Settled at Equilibrium" if self.spring.is_settled else "🌊 Oscillating dynamically"
            telemetry = (
                f"Position: {self.spring.value:5.1f}%  │  Target: {self.spring.target:5.1f}%  │  "
                f"Velocity: {self.spring.velocity:+6.1f} u/s  │  Damping ζ: {zeta:.2f}  │  ω₀: {omega0:.1f} rad/s\n"
                f"Status: {Style().foreground('#00E676' if self.spring.is_settled else '#FF007F').render(status_text)}"
            )

            content_view = f"{title}\n{formula}\n\n{preset_badge}\n\n{gauge_view}\n\n{hints}\n\n{traj_title}\n{traj_graph}\n\n{telemetry}"

        elif self.active_tab == 1:
            # ---------------- TAB 2: Confetti Celebration ----------------
            title = Style().bold(True).foreground("#FF007F").render("🎉 2D Terminal Particle Physics & Celebratory Emitter:")
            controls = Style().faint(True).render(
                "• Keys: [b] or [Space] Radial Burst • [c] Twin Cannons • [r] Rain Shower • [x] Clear Particles\n"
                "• Mouse: Click anywhere in the card below to launch an instant localized particle explosion!"
            )

            banner_box = (
                "┌────────────────────────────────────────────────────────────────────────┐\n"
                "│  🏆  ESPRESSO 2.0 PRODUCTION MILESTONE                                 │\n"
                "│  The High-Performance Reactive Terminal UI Framework for Python 3.10+  │\n"
                "├────────────────────────────────────────────────────────────────────────┤\n"
                "│  • 36 Standard Beans Components (Bubbles & Teacup Supercharged)        │\n"
                "│  • Analytical Harmonic Oscillator Physics & 2D Particle Engine         │\n"
                "│  • SGR 1006 Direct Mouse Manipulation & ANSI Sub-Cell Braille Curves   │\n"
                "│  • 100% Pure Python Standard Library — Zero External C Dependencies    │\n"
                "└────────────────────────────────────────────────────────────────────────┘"
            )
            banner_styled = Style().foreground("#FAFAFA").render(banner_box)

            telemetry = (
                f"Active Particles: {len(self.confetti.particles):3d}  │  "
                f"Gravity: {self.confetti.gravity:.1f} cells/s²  │  "
                f"Air Drag: {self.confetti.drag:.2f}  │  FPS: {self.confetti.fps:.0f}\n"
                f"Glyphs: ✦ ★ • ✨ 🎉 ☕ ▲ ◆ ■ ♦  │  Palette: 7 Vivid 24-bit TrueColor Hues"
            )

            underlying = f"{title}\n{controls}\n\n{banner_styled}\n\n{telemetry}"
            # Overlay active particles directly on top of the text without layout deformation!
            content_view = self.confetti.overlay(underlying)

        elif self.active_tab == 2:
            # ---------------- TAB 3: Git DiffViewer ----------------
            diff_ui = self.diff_viewer.view()
            content_view = diff_ui

        elif self.active_tab == 3:
            # ---------------- TAB 4: Form Builder ----------------
            if self.submitted_profile is not None:
                # Show celebration results card
                res_title = Style().bold(True).foreground("#00E676").render("🎉 Profile Successfully Registered!")
                p = self.submitted_profile
                card_lines = [
                    "┌────────────────────────────────────────────────────────────┐",
                    f"│  Full Name:       {p.get('name', ''):<40} │",
                    f"│  Email Address:   {p.get('email', ''):<40} │",
                    f"│  Experience:      {str(p.get('exp', 0)) + ' years':<40} │",
                    f"│  Focus Area:      {p.get('role', 'General'):<40} │",
                    "└────────────────────────────────────────────────────────────┘",
                ]
                card_str = "\n".join(card_lines)
                reset_hint = Style().faint(True).render("Press 'r' to reset form and submit another response.")
                underlying = f"{res_title}\n\n{card_str}\n\n{reset_hint}"
                content_view = self.form_confetti.overlay(underlying)
            else:
                form_view = self.form.view()
                shortcuts = Style().faint(True).render(
                    "• Tab / Shift+Tab or Up/Down: Navigate fields • Left/Right: Adjust slider • Click field\n"
                    "• Enter on Submit or Ctrl+S: Submit form (Live validation highlights missing/invalid entries)"
                )
                content_view = f"{form_view}\n\n{shortcuts}"

        card = self.border_style.width(self.width - 2).height(card_h).render(content_view)

        # Footer
        if self.active_tab == 3:
            footer_text = "F1-F4: Switch Tab • Tab/Shift+Tab: Focus Fields • Ctrl+S: Submit • Ctrl+C: Quit"
        elif self.active_tab == 2:
            footer_text = "1-4 / Tab: Switch View • m: Toggle Unified/Split • Wheel/Arrows: Scroll • q: Quit"
        else:
            footer_text = "1-4 / Tab: Switch View • Mouse Click & Wheel Enabled • q: Quit"

        footer = self.footer_style.render(footer_text)
        return f"{header}\n{card}\n{footer}"


def main() -> None:
    Program(PhysicsAndToolsApp(), alt_screen=True, mouse=True).run()


if __name__ == "__main__":
    main()
