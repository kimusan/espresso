"""Spring physics animation engine based on damped harmonic oscillators."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Callable

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width


class SpringTickMsg(Msg):
    """Message emitted on spring simulation tick."""

    def __init__(self, tag: str, value: float, velocity: float, is_settled: bool) -> None:
        self.tag = tag
        self.value = value
        self.velocity = velocity
        self.is_settled = is_settled

    def __str__(self) -> str:
        return f"SpringTickMsg(tag={self.tag!r}, value={self.value:.3f}, vel={self.velocity:.3f}, settled={self.is_settled})"


class SpringValue:
    """A single numeric value animated via damped harmonic oscillator physics.

    Uses the exact analytical closed-form solution of the second-order differential equation:
        m * x''(t) + c * x'(t) + k * (x(t) - target) = 0
    guaranteeing 100% mathematical stability across any variable time step dt.
    """

    def __init__(
        self,
        value: float = 0.0,
        target: float | None = None,
        stiffness: float = 120.0,
        damping: float = 0.75,
        mass: float = 1.0,
        epsilon: float = 0.005,
    ) -> None:
        self.value = float(value)
        self.target = float(value if target is None else target)
        self.velocity: float = 0.0

        # Physical properties
        self.stiffness = max(0.1, float(stiffness))
        self.damping = max(0.0, float(damping))  # damping ratio (zeta)
        self.mass = max(0.01, float(mass))
        self.epsilon = max(0.0001, float(epsilon))

    @property
    def is_settled(self) -> bool:
        """True if the value is within epsilon of target and velocity is near zero."""
        return abs(self.value - self.target) < self.epsilon and abs(self.velocity) < (self.epsilon * 20.0)

    def set_target(self, target: float) -> None:
        """Update destination target while preserving current position and momentum."""
        self.target = float(target)

    def snap_to(self, value: float) -> None:
        """Instantly jump value and target to value and zero out velocity."""
        self.value = float(value)
        self.target = float(value)
        self.velocity = 0.0

    def update(self, dt: float) -> tuple[float, float]:
        """Advance the physics simulation by dt seconds.

        Returns (new_value, new_velocity).
        """
        if self.is_settled:
            self.value = self.target
            self.velocity = 0.0
            return self.value, self.velocity

        if dt <= 0.0:
            return self.value, self.velocity

        m = self.mass
        k = self.stiffness
        zeta = self.damping

        omega0 = math.sqrt(k / m)
        x0 = self.value - self.target
        v0 = self.velocity

        # 1. Underdamped (zeta < 1.0): oscillatory bounce around target
        if zeta < 1.0:
            omega_d = omega0 * math.sqrt(1.0 - zeta * zeta)
            decay = math.exp(-zeta * omega0 * dt)
            cos_term = math.cos(omega_d * dt)
            sin_term = math.sin(omega_d * dt)

            c1 = x0
            c2 = (v0 + zeta * omega0 * x0) / omega_d

            new_x = (c1 * cos_term + c2 * sin_term) * decay
            new_v = decay * (
                -zeta * omega0 * (c1 * cos_term + c2 * sin_term)
                + (-c1 * omega_d * sin_term + c2 * omega_d * cos_term)
            )

        # 2. Critically damped (zeta == 1.0): quickest approach with no overshoot
        elif abs(zeta - 1.0) < 1e-5:
            decay = math.exp(-omega0 * dt)
            c1 = x0
            c2 = v0 + omega0 * x0

            new_x = (c1 + c2 * dt) * decay
            new_v = (c2 - omega0 * (c1 + c2 * dt)) * decay

        # 3. Overdamped (zeta > 1.0): exponential decay with no bounce
        else:
            omega_d = omega0 * math.sqrt(zeta * zeta - 1.0)
            r1 = -omega0 * zeta + omega_d
            r2 = -omega0 * zeta - omega_d

            c2 = (v0 - r1 * x0) / (r2 - r1)
            c1 = x0 - c2

            exp1 = math.exp(r1 * dt)
            exp2 = math.exp(r2 * dt)

            new_x = c1 * exp1 + c2 * exp2
            new_v = c1 * r1 * exp1 + c2 * r2 * exp2

        self.value = self.target + new_x
        self.velocity = new_v

        # Check if settled after step
        if self.is_settled:
            self.value = self.target
            self.velocity = 0.0

        return self.value, self.velocity


class Spring(Model):
    """An interactive spring animation widget and controller for Tea applications."""

    def __init__(
        self,
        value: float = 0.0,
        target: float | None = None,
        min_val: float = 0.0,
        max_val: float = 100.0,
        stiffness: float = 120.0,
        damping: float = 0.75,
        mass: float = 1.0,
        fps: float = 60.0,
        width: int = 40,
        label: str = "Spring Gauge:",
        tag: str = "spring",
        track_char: str = "─",
        filled_char: str = "━",
        thumb_char: str = "●",
        target_char: str = "▼",
        style: Style | None = None,
        thumb_style: Style | None = None,
        target_style: Style | None = None,
        label_style: Style | None = None,
    ) -> None:
        self.spring = SpringValue(
            value=value,
            target=target,
            stiffness=stiffness,
            damping=damping,
            mass=mass,
        )
        self.min_val = min_val
        self.max_val = max(min_val + 0.001, max_val)
        self.fps = max(10.0, fps)
        self.dt = 1.0 / self.fps
        self.width = max(10, width)
        self.label = label
        self.tag = tag

        self.track_char = track_char
        self.filled_char = filled_char
        self.thumb_char = thumb_char
        self.target_char = target_char

        self.style = style or Style().foreground("#444466")
        self.thumb_style = thumb_style or Style().bold(True).foreground("#00E5FF")
        self.target_style = target_style or Style().bold(True).foreground("#FF007F")
        self.label_style = label_style or Style().bold(True).foreground("#FFFFFF")

    @property
    def value(self) -> float:
        return self.spring.value

    @property
    def target(self) -> float:
        return self.spring.target

    @property
    def velocity(self) -> float:
        return self.spring.velocity

    @property
    def is_settled(self) -> bool:
        return self.spring.is_settled

    def set_target(self, target: float) -> Cmd:
        """Change destination target and return animation tick command if needed."""
        self.spring.set_target(target)
        return self.tick()

    def snap_to(self, value: float) -> None:
        """Instantly set position without animation."""
        self.spring.snap_to(value)

    def tick(self) -> Cmd:
        """Create a Tea command that waits for frame interval and emits SpringTickMsg."""
        tag = self.tag
        dt = self.dt
        val = self.value
        vel = self.velocity
        settled = self.is_settled

        async def _tick_async() -> Msg:
            await asyncio.sleep(dt)
            return SpringTickMsg(tag=tag, value=val, velocity=vel, is_settled=settled)

        return _tick_async

    def init(self) -> Cmd | None:
        """Emit initial frame tick if not yet settled."""
        if not self.is_settled:
            return self.tick()
        return None

    def update(self, msg: Msg) -> tuple[Spring, Cmd | None]:
        """Process SpringTickMsg, advance physics, and schedule next tick until settled."""
        if isinstance(msg, SpringTickMsg) and msg.tag == self.tag:
            self.spring.update(self.dt)
            if not self.spring.is_settled:
                return self, self.tick()
            return self, None
        return self, None

    def view(self) -> str:
        """Render a spring physics track with moving thumb and target indicator."""
        label_part = f"{self.label_style.render(self.label)} " if self.label else ""
        label_w = string_width(label_part)

        # Telemetry badge: Value, Target, Velocity
        status = " settled" if self.is_settled else f" v:{self.velocity:+5.1f}"
        badge = f" [{self.value:5.1f} → {self.target:5.1f}{status}]"
        badge_styled = Style().foreground("#8888AA").render(badge)
        badge_w = string_width(badge)

        track_w = max(5, self.width - label_w - badge_w)
        span = self.max_val - self.min_val

        # Normalized coordinates along track
        pct_val = (self.value - self.min_val) / max(0.001, span)
        pct_tgt = (self.target - self.min_val) / max(0.001, span)

        # Allow visual overshoot beyond 0..1 bounds
        idx_val = int(round(pct_val * (track_w - 1)))
        idx_tgt = int(round(pct_tgt * (track_w - 1)))
        clamped_idx_tgt = max(0, min(track_w - 1, idx_tgt))

        # Build track cells
        cells: list[str] = [self.track_char] * track_w

        # Target marker
        cells[clamped_idx_tgt] = self.target_style.render(self.target_char)

        # Render thumb or overshoot indicators
        if 0 <= idx_val < track_w:
            cells[idx_val] = self.thumb_style.render(self.thumb_char)
        elif idx_val < 0:
            cells[0] = self.thumb_style.render("◀")
        else:
            cells[track_w - 1] = self.thumb_style.render("▶")

        track_rendered = "".join(cells)
        return f"{label_part}{track_rendered}{badge_styled}"
