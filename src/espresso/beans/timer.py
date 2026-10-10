"""High-precision countdown Timer and elapsed Stopwatch components."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

from espresso.core.tea import Cmd, Model, Msg, tick
from espresso.crema.style import Style


@dataclass(frozen=True)
class TimerTickMsg(Msg):
    """Message emitted on each tick of a countdown Timer."""

    tag: str
    id: int


@dataclass(frozen=True)
class TimerTimeoutMsg(Msg):
    """Message emitted when a countdown Timer reaches zero."""

    tag: str


@dataclass(frozen=True)
class StopwatchTickMsg(Msg):
    """Message emitted on each tick of a Stopwatch."""

    tag: str
    id: int


class Timer(Model):
    """High-precision countdown timer driven by tea tick commands."""

    def __init__(
        self,
        timeout: float,
        interval: float = 1.0,
        tag: str = "timer",
        auto_start: bool = True,
        style: Style | None = None,
        format_fn: Callable[[float], str] | None = None,
    ) -> None:
        t = 0.0 if math.isnan(timeout) else timeout
        self.initial_timeout = max(0.0, float(t))
        self.timeout = self.initial_timeout
        self.remaining = self.initial_timeout
        inv = 1.0 if math.isnan(interval) else interval
        self.interval = max(0.001, float(inv))
        self.tag = tag
        self.auto_start = auto_start
        self.style = style
        self.format_fn = format_fn

        self.running: bool = False
        self.timedout: bool = False
        self._tick_id: int = 0
        self._start_time: float = 0.0
        self._target_time: float = 0.0

    def init(self) -> Cmd | None:
        """Initialize timer lifecycle, automatically starting countdown if configured."""
        if self.auto_start:
            return self.start()
        return None

    def start(self) -> Cmd | None:
        """Start or resume countdown."""
        if self.running or self.timedout or self.remaining <= 0.0:
            return None
        self.running = True
        self._tick_id += 1
        self._start_time = time.monotonic()
        self._target_time = self._start_time + self.remaining
        delay = min(self.interval, self.remaining)
        return tick(delay, TimerTickMsg(tag=self.tag, id=self._tick_id))

    def stop(self) -> None:
        """Pause the countdown."""
        if not self.running:
            return
        self.running = False
        self.remaining = max(0.0, self._target_time - time.monotonic())
        self._tick_id += 1

    def toggle(self) -> Cmd | None:
        """Toggle between running and paused states."""
        if self.running:
            self.stop()
            return None
        return self.start()

    def reset(self, timeout: float | None = None, start: bool = False) -> Cmd | None:
        """Reset the timer to initial or new timeout duration."""
        self.stop()
        if timeout is not None:
            self.initial_timeout = max(0.0, float(timeout))
        self.timeout = self.initial_timeout
        self.remaining = self.initial_timeout
        self.timedout = False
        self._tick_id += 1
        if start:
            return self.start()
        return None

    @property
    def elapsed(self) -> float:
        """Elapsed time in seconds since timer started."""
        return max(0.0, self.initial_timeout - self.remaining)

    @property
    def percent(self) -> float:
        """Progress ratio from 0.0 (start) to 1.0 (completed)."""
        if self.initial_timeout <= 0:
            return 1.0
        return max(0.0, min(1.0, self.elapsed / self.initial_timeout))

    def set_remaining(self, val: float) -> None:
        """Directly adjust remaining time, primarily for testing or sync."""
        self.remaining = max(0.0, float(val))
        if self.running:
            self._target_time = time.monotonic() + self.remaining
        if self.remaining <= 0.0:
            self.timedout = True

    def update(self, msg: Msg) -> tuple[Timer, Cmd | None]:
        """Advance remaining time on timer tick, scheduling next tick or emitting timeout message."""
        if isinstance(msg, TimerTickMsg) and msg.tag == self.tag and msg.id == self._tick_id:
            if not self.running:
                return self, None
            now = time.monotonic()
            self.remaining = max(0.0, self._target_time - now)
            if self.remaining <= 0.0:
                self.remaining = 0.0
                self.running = False
                self.timedout = True
                tag = self.tag
                return self, (lambda: TimerTimeoutMsg(tag=tag))

            next_delay = min(self.interval, self.remaining)
            return self, tick(next_delay, TimerTickMsg(tag=self.tag, id=self._tick_id))

        return self, None

    def view(self) -> str:
        """Render the countdown timer formatted as HH:MM:SS or MM:SS."""
        if self.format_fn is not None:
            formatted = self.format_fn(self.remaining)
        else:
            total_sec = max(0.0, self.remaining)
            if self.interval < 1.0:
                total_tenths = int(round(total_sec * 10))
                tenths = total_tenths % 10
                total_seconds = total_tenths // 10
                seconds = total_seconds % 60
                minutes = (total_seconds // 60) % 60
                hours = total_seconds // 3600
                if hours > 0:
                    base = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{tenths:1d}"
                else:
                    base = f"{minutes:02d}:{seconds:02d}.{tenths:1d}"
            else:
                total_seconds = int(round(total_sec))
                seconds = total_seconds % 60
                minutes = (total_seconds // 60) % 60
                hours = total_seconds // 3600
                if hours > 0:
                    base = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    base = f"{minutes:02d}:{seconds:02d}"
            formatted = base

        if self.style is not None:
            return self.style.render(formatted)
        return formatted


class Stopwatch(Model):
    """High-precision elapsed time stopwatch driven by tea tick commands."""

    def __init__(
        self,
        interval: float = 0.1,
        tag: str = "stopwatch",
        auto_start: bool = False,
        style: Style | None = None,
        format_fn: Callable[[float], str] | None = None,
    ) -> None:
        inv = 0.1 if math.isnan(interval) else interval
        self.interval = max(0.001, float(inv))
        self.tag = tag
        self.auto_start = auto_start
        self.style = style
        self.format_fn = format_fn

        self.running: bool = False
        self._accumulated_time: float = 0.0
        self._start_time: float = 0.0
        self._tick_id: int = 0

    def init(self) -> Cmd | None:
        """Initialize stopwatch lifecycle, starting elapsed time tracking if configured."""
        if self.auto_start:
            return self.start()
        return None

    def start(self) -> Cmd | None:
        """Start or resume stopwatch."""
        if self.running:
            return None
        self.running = True
        self._tick_id += 1
        self._start_time = time.monotonic() - self._accumulated_time
        return tick(self.interval, StopwatchTickMsg(tag=self.tag, id=self._tick_id))

    def stop(self) -> None:
        """Pause stopwatch."""
        if not self.running:
            return
        self.running = False
        self._accumulated_time = max(0.0, time.monotonic() - self._start_time)
        self._tick_id += 1

    def toggle(self) -> Cmd | None:
        """Toggle between running and paused states."""
        if self.running:
            self.stop()
            return None
        return self.start()

    def reset(self, start: bool = False) -> Cmd | None:
        """Reset elapsed time to zero."""
        self.stop()
        self._accumulated_time = 0.0
        self._tick_id += 1
        if start:
            return self.start()
        return None

    @property
    def elapsed(self) -> float:
        """Return current elapsed time in seconds."""
        if self.running:
            return max(0.0, time.monotonic() - self._start_time)
        return self._accumulated_time

    def set_elapsed(self, val: float) -> None:
        """Directly set elapsed time, primarily for testing or sync."""
        v = 0.0 if math.isnan(val) else val
        self._accumulated_time = max(0.0, float(v))
        if self.running:
            self._start_time = time.monotonic() - self._accumulated_time

    def update(self, msg: Msg) -> tuple[Stopwatch, Cmd | None]:
        """Update elapsed duration on matching tick message and schedule next tick."""
        if isinstance(msg, StopwatchTickMsg) and msg.tag == self.tag and msg.id == self._tick_id:
            if not self.running:
                return self, None
            self._accumulated_time = time.monotonic() - self._start_time
            return self, tick(self.interval, StopwatchTickMsg(tag=self.tag, id=self._tick_id))

        return self, None

    def view(self) -> str:
        """Render elapsed time formatted as MM:SS.hh or HH:MM:SS.hh."""
        if self.format_fn is not None:
            formatted = self.format_fn(self.elapsed)
        else:
            total_sec = max(0.0, self.elapsed)
            total_hundredths = int(round(total_sec * 100))
            hundredths = total_hundredths % 100
            total_seconds = total_hundredths // 100
            seconds = total_seconds % 60
            minutes = (total_seconds // 60) % 60
            hours = total_seconds // 3600
            if hours > 0:
                base = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"
            else:
                base = f"{minutes:02d}:{seconds:02d}.{hundredths:02d}"
            formatted = base

        if self.style is not None:
            return self.style.render(formatted)
        return formatted
