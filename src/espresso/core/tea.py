"""The Elm Architecture (TEA) core protocols, messages, and command primitives.

In TEA:
- Model: Pure state data structure.
- Msg: An event or notification (keypress, timer tick, network response).
- Cmd: An asynchronous task producer that generates a Msg when finished.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Iterable,
    Protocol,
    Sequence,
    TypeAlias,
    Union,
    runtime_checkable,
)


class Msg:
    """Base class for all messages dispatched in Espresso."""


@dataclass(frozen=True)
class QuitMsg(Msg):
    """Message instructing the Program event loop to cleanly terminate."""

    def __call__(self) -> QuitMsg:
        return self


@dataclass(frozen=True)
class WindowSizeMsg(Msg):
    """Message emitted when the terminal window size changes."""

    width: int
    height: int


@dataclass(frozen=True)
class BatchMsg(Msg):
    """Container message for multiple messages produced together."""

    messages: tuple[Msg, ...]


@dataclass(frozen=True)
class TickMsg(Msg):
    """Message produced by a timed tick command."""

    tag: str = ""


# A Cmd is either:
# 1. A synchronous callable returning Msg or None: Callable[[], Msg | None]
# 2. An asynchronous callable returning an awaitable of Msg or None: Callable[[], Awaitable[Msg | None]]
# 3. None (representing no command)
SyncCmd: TypeAlias = Callable[[], Union[Msg, None]]
AsyncCmd: TypeAlias = Callable[[], Awaitable[Union[Msg, None]]]
Cmd: TypeAlias = Union[SyncCmd, AsyncCmd, None]


@runtime_checkable
class Model(Protocol):
    """Protocol representing a TEA component in Espresso."""

    def init(self) -> Cmd | None:
        """Return the initial command to run when the program starts."""
        ...

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        """Process a message and return the updated model and an optional command."""
        ...

    def view(self) -> str:
        """Render the model state to a formatted terminal string."""
        ...


def quit_app() -> QuitMsg:
    """Convenience command that returns a QuitMsg to shut down the application."""
    return QuitMsg()


def batch(*cmds: Cmd | None) -> Cmd:
    """Combine multiple commands into a single command that executes concurrently.

    Each non-None command runs in the background and its resulting Msg is sent
    to the program's update loop as soon as it completes.
    """
    valid_cmds = [c for c in cmds if c is not None]
    if not valid_cmds:
        return None

    async def _batch_runner() -> Msg | None:
        # Instead of returning a single message, Program's command dispatcher
        # detects BatchCommand or runs them concurrently. We return a BatchMsg
        # if executed together.
        tasks = []
        for cmd in valid_cmds:
            if asyncio.iscoroutinefunction(cmd):
                tasks.append(cmd())
            else:
                loop = asyncio.get_running_loop()
                tasks.append(loop.run_in_executor(None, cmd))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        msgs: list[Msg] = []
        for res in results:
            if isinstance(res, Msg):
                msgs.append(res)
        if msgs:
            return BatchMsg(messages=tuple(msgs))
        return None

    return _batch_runner


def sequence(*cmds: Cmd | None) -> Cmd:
    """Execute commands sequentially in order.

    Each command runs to completion before the next command begins.
    """
    valid_cmds = [c for c in cmds if c is not None]
    if not valid_cmds:
        return None

    async def _seq_runner() -> Msg | None:
        msgs: list[Msg] = []
        for cmd in valid_cmds:
            if asyncio.iscoroutinefunction(cmd):
                res = await cmd()
            else:
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, cmd)
            if isinstance(res, Msg):
                msgs.append(res)
        if msgs:
            return BatchMsg(messages=tuple(msgs))
        return None

    return _seq_runner


def tick(duration_seconds: float, msg_factory: Callable[[], Msg] | Msg) -> Cmd:
    """Create a command that waits for a duration and then produces a message."""

    async def _tick_cmd() -> Msg:
        await asyncio.sleep(duration_seconds)
        if callable(msg_factory):
            return msg_factory()
        return msg_factory

    return _tick_cmd
