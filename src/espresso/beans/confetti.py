"""2D terminal particle physics engine and celebratory confetti emitter."""

from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.overlay import place_overlay, slice_ansi
from espresso.crema.style import Style
from espresso.crema.width import string_width


class ConfettiMode(Enum):
    """Emission pattern for confetti particles."""

    BURST = "burst"    # Radial explosion from a center point
    CANNON = "cannon"  # Twin angled cannons launched from bottom corners
    RAIN = "rain"      # Celebratory cascade drifting from the top


class ConfettiTickMsg(Msg):
    """Timer message advancing confetti particle physics."""

    def __init__(self, tag: str, active_particles: int) -> None:
        self.tag = tag
        self.active_particles = active_particles

    def __str__(self) -> str:
        return f"ConfettiTickMsg(tag={self.tag!r}, active={self.active_particles})"


@dataclass
class Particle:
    """A single particle in 2D terminal space."""

    x: float
    y: float
    vx: float
    vy: float
    char: str
    color: str
    life: int
    max_life: int


# Guaranteed 1-column single-cell glyphs (no double-width emojis that displace box borders)
DEFAULT_CONFETTI_CHARS: list[str] = [
    "✦", "★", "•", "▲", "▼", "◆", "■", "♦", "●", "▪", "*", "+", "x"
]
DEFAULT_PALETTE: list[str] = [
    "#FF007F",  # Neon Pink
    "#00E5FF",  # Cyan
    "#FFD54F",  # Gold
    "#7D56F4",  # Purple
    "#00E676",  # Lime Green
    "#FF9100",  # Bright Orange
    "#FFFFFF",  # Pure White
]


class Confetti(Model):
    """A 2D particle physics emitter for celebrations and visual effects."""

    def __init__(
        self,
        width: int = 80,
        height: int = 24,
        gravity: float = 14.0,
        drag: float = 0.45,
        fps: float = 30.0,
        characters: Sequence[str] | None = None,
        colors: Sequence[str] | None = None,
        tag: str = "confetti",
    ) -> None:
        self.width = max(10, width)
        self.height = max(4, height)
        self.gravity = gravity
        self.drag = drag
        self.fps = max(10.0, fps)
        self.dt = 1.0 / self.fps
        self.characters = list(characters or DEFAULT_CONFETTI_CHARS)
        self.colors = list(colors or DEFAULT_PALETTE)
        self.tag = tag

        self.particles: list[Particle] = []

    @property
    def is_active(self) -> bool:
        """True if any particles are currently alive."""
        return len(self.particles) > 0

    def set_size(self, width: int, height: int) -> None:
        """Update emission canvas bounds."""
        self.width = max(10, width)
        self.height = max(4, height)

    def fire(
        self,
        count: int = 50,
        mode: ConfettiMode = ConfettiMode.BURST,
        origin: tuple[int, int] | None = None,
    ) -> Cmd | None:
        """Spawn particles and return animation tick command if not already running."""
        w, h = self.width, self.height
        was_active = self.is_active

        if mode == ConfettiMode.BURST:
            cx = float(origin[0]) if origin is not None else w / 2.0
            cy = float(origin[1]) if origin is not None else h / 2.0

            for _ in range(count):
                angle = random.uniform(0, 2 * math.pi)
                # Aspect ratio compensation for taller terminal cells (2:1 ratio)
                speed = random.uniform(24.0, 56.0)
                vx = math.cos(angle) * speed * 1.6
                vy = math.sin(angle) * speed * 0.8 - 4.0  # slight upward bias
                life = random.randint(14, 26)
                char = random.choice(self.characters)
                color = random.choice(self.colors)
                # Disperse initial coordinates slightly when origin is automatic
                r0 = 0.0 if origin is not None else random.uniform(0.5, 3.5)
                px = cx + math.cos(angle) * r0 * 1.5
                py = cy + math.sin(angle) * r0 * 0.7
                self.particles.append(Particle(px, py, vx, vy, char, color, life, life))

        elif mode == ConfettiMode.CANNON:
            # Left and right corner cannons firing high inward arcs across canvas
            for i in range(count):
                from_left = (i % 2 == 0)
                cx = 2.0 if from_left else float(w - 3)
                cy = float(h - 2)

                # Angle pointed inward and upward
                if from_left:
                    angle = random.uniform(math.radians(25), math.radians(65))
                    speed = random.uniform(32.0, 56.0)
                else:
                    angle = random.uniform(math.radians(115), math.radians(155))
                    speed = random.uniform(32.0, 56.0)

                vx = math.cos(angle) * speed
                vy = -math.sin(angle) * speed * 0.88
                life = random.randint(28, 48)
                char = random.choice(self.characters)
                color = random.choice(self.colors)
                self.particles.append(Particle(cx, cy, vx, vy, char, color, life, life))

        elif mode == ConfettiMode.RAIN:
            for _ in range(count):
                cx = random.uniform(2.0, float(w - 3))
                cy = random.uniform(0.0, 3.0)
                vx = random.uniform(-4.0, 4.0)
                vy = random.uniform(3.0, 9.0)
                life = random.randint(25, 45)
                char = random.choice(self.characters)
                color = random.choice(self.colors)
                self.particles.append(Particle(cx, cy, vx, vy, char, color, life, life))

        # Only schedule a new ticker if one was not already running
        if not was_active:
            return self.tick()
        return None

    def clear(self) -> None:
        """Remove all active particles immediately."""
        self.particles.clear()

    def tick(self) -> Cmd:
        """Create a command that schedules the next particle update."""
        tag = self.tag
        dt = self.dt
        count = len(self.particles)

        async def _tick_async() -> Msg:
            await asyncio.sleep(dt)
            return ConfettiTickMsg(tag=tag, active_particles=count)

        return _tick_async

    def init(self) -> Cmd | None:
        if self.is_active:
            return self.tick()
        return None

    def update(self, msg: Msg) -> tuple[Confetti, Cmd | None]:
        """Update particle physics on tick and continue until all particles expire."""
        if isinstance(msg, ConfettiTickMsg) and msg.tag == self.tag:
            self._step_physics()
            if self.is_active:
                return self, self.tick()
            return self, None
        return self, None

    def _step_physics(self) -> None:
        """Advance all particles by one physics step."""
        dt = self.dt
        alive: list[Particle] = []

        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += self.gravity * dt
            # Air drag
            p.vx *= (1.0 - self.drag * dt)
            p.vy *= (1.0 - self.drag * dt)
            p.life -= 1

            # Keep if inside reasonable bounds and alive
            if p.life > 0 and -2 <= p.x <= self.width + 2 and -2 <= p.y <= self.height + 2:
                alive.append(p)

        self.particles = alive

    def overlay(self, background: str) -> str:
        """Overlay active particles on top of a rendered background view string."""
        if not self.particles:
            return background

        bg_lines = background.split("\n")
        # Build particle grid: (col, row) -> styled_char
        particle_grid: dict[tuple[int, int], str] = {}
        for p in self.particles:
            col = int(round(p.x))
            row = int(round(p.y))
            if 0 <= col < self.width and 0 <= row < len(bg_lines):
                styled_char = Style().foreground(p.color).bold(True).render(p.char)
                particle_grid[(col, row)] = styled_char

        if not particle_grid:
            return background

        out_lines: list[str] = []
        for row_idx, line in enumerate(bg_lines):
            row_particles = {col: s for (col, r), s in particle_grid.items() if r == row_idx}
            if not row_particles:
                out_lines.append(line)
                continue

            current_line = line
            # Sort columns descending to slice from right to left
            for col in sorted(row_particles.keys(), reverse=True):
                char_str = row_particles[col]
                cw = string_width(current_line)
                if col >= cw:
                    pad_spaces = " " * (col - cw)
                    current_line = f"{current_line}{pad_spaces}{char_str}"
                else:
                    left_part = slice_ansi(current_line, 0, col, pad=True)
                    right_part = slice_ansi(current_line, col + 1)
                    current_line = f"{left_part}{char_str}{right_part}"

            out_lines.append(current_line)

        return "\n".join(out_lines)

    def view(self) -> str:
        """Render standalone transparent particle frame padded to bounds."""
        lines = [[" "] * self.width for _ in range(self.height)]

        for p in self.particles:
            col = int(round(p.x))
            row = int(round(p.y))
            if 0 <= col < self.width and 0 <= row < self.height:
                styled_char = Style().foreground(p.color).bold(True).render(p.char)
                lines[row][col] = styled_char

        return "\n".join("".join(row) for row in lines)
