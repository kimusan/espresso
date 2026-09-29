"""The Program runtime engine coordinating The Elm Architecture loop."""

from __future__ import annotations

import asyncio
import inspect
import os
import sys
from typing import TextIO

from espresso.core.keys import parse_keys
from espresso.core.tea import BatchMsg, Cmd, Model, Msg, QuitMsg, WindowSizeMsg
from espresso.core.terminal import (
    CLEAR_LINE,
    CURSOR_TO_COL,
    CURSOR_UP,
    TerminalDriver,
)


class Program:
    """The runtime coordinator that drives a TEA Model."""

    def __init__(
        self,
        model: Model,
        alt_screen: bool = False,
        mouse: bool = False,
        fps: int = 60,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ) -> None:
        self.model = model
        self.alt_screen = alt_screen
        self.mouse = mouse
        self.fps = fps
        self.input_stream = input_stream or sys.stdin
        self.output_stream = output_stream or sys.stdout

        self._queue: asyncio.Queue[Msg] | None = None
        self._running = False
        self._terminal = TerminalDriver(alt_screen=self.alt_screen, mouse=self.mouse)
        self._last_rendered_lines: list[str] = []
        self._bg_tasks: set[asyncio.Task[None]] = set()

    def run(self) -> Model:
        """Run the program synchronously to completion."""
        return asyncio.run(self.run_async())

    async def run_async(self) -> Model:
        """Run the program asynchronously in the current event loop."""
        self._queue = asyncio.Queue()
        self._running = True
        loop = asyncio.get_running_loop()

        # Handle window resizing
        def _on_resize(w: int, h: int) -> None:
            if self._queue is not None and self._running:
                loop.call_soon_threadsafe(self._queue.put_nowait, WindowSizeMsg(w, h))

        self._terminal.set_resize_handler(_on_resize)

        # Enter terminal raw mode
        self._terminal.enter()

        reader_task: asyncio.Task[None] | None = None
        try:
            # Emit initial window size
            w, h = self._terminal.get_size()
            await self._queue.put(WindowSizeMsg(w, h))

            # Trigger initial model command
            init_cmd = self.model.init()
            if init_cmd is not None:
                self._dispatch_cmd(init_cmd)

            # Initial render
            self._render(self.model.view())

            # Start stdin input listener task
            reader_task = asyncio.create_task(self._stdin_reader())

            # Main event loop
            while self._running:
                msg = await self._queue.get()
                should_quit = await self._handle_msg(msg)
                if should_quit:
                    break

        finally:
            self._running = False
            if reader_task is not None:
                reader_task.cancel()
                try:
                    await reader_task
                except (asyncio.CancelledError, Exception):
                    pass

            for task in list(self._bg_tasks):
                task.cancel()

            self._terminal.exit()

            # Ensure newline after inline mode
            if not self.alt_screen and self._last_rendered_lines:
                self.output_stream.write("\n")
                self.output_stream.flush()

        return self.model

    async def _handle_msg(self, msg: Msg) -> bool:
        """Process a single message. Return True if the application should quit."""
        if isinstance(msg, QuitMsg):
            return True

        if isinstance(msg, BatchMsg):
            for sub_msg in msg.messages:
                quit_req = await self._handle_msg(sub_msg)
                if quit_req:
                    return True
            return False

        # Dispatch message to model
        if inspect.iscoroutinefunction(self.model.update):
            updated_model, cmd = await self.model.update(msg)
        else:
            updated_model, cmd = self.model.update(msg)

        self.model = updated_model

        if cmd is not None:
            self._dispatch_cmd(cmd)

        # Re-render view
        self._render(self.model.view())
        return False

    def _dispatch_cmd(self, cmd: Cmd) -> None:
        """Execute a Cmd in the background and route its resulting Msg into the queue."""
        if cmd is None:
            return

        async def _cmd_wrapper() -> None:
            try:
                if inspect.iscoroutinefunction(cmd) or inspect.isawaitable(cmd):
                    res = await (cmd() if callable(cmd) else cmd)
                elif callable(cmd):
                    loop = asyncio.get_running_loop()
                    res = await loop.run_in_executor(None, cmd)
                else:
                    res = None

                if isinstance(res, Msg) and self._queue is not None and self._running:
                    await self._queue.put(res)
            except Exception as e:
                # Silently catch or handle command errors
                pass

        task = asyncio.create_task(_cmd_wrapper())
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _stdin_reader(self) -> None:
        """Read bytes from standard input and enqueue parsed KeyMsg objects."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        try:
            await loop.connect_read_pipe(lambda: protocol, self.input_stream)
        except Exception:
            # Fallback for environments where connect_read_pipe isn't supported
            return

        while self._running:
            try:
                data = await reader.read(1024)
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                for key_msg in parse_keys(text):
                    if self._queue is not None:
                        await self._queue.put(key_msg)
            except asyncio.CancelledError:
                break
            except Exception:
                break

    def _render(self, view_content: str) -> None:
        """Render view content to the terminal output stream."""
        new_lines = view_content.splitlines()
        buf = []

        if self.alt_screen:
            # Move cursor to home position
            buf.append("\x1b[H")
            for i, line in enumerate(new_lines):
                buf.append(f"{line}{CLEAR_LINE}\n")
            # Clear remaining lines below if old view was taller
            if len(new_lines) < len(self._last_rendered_lines):
                remaining = len(self._last_rendered_lines) - len(new_lines)
                for _ in range(remaining):
                    buf.append(f"{CLEAR_LINE}\n")
        else:
            # Inline mode: rewrite lines over the previously rendered block
            num_prev_lines = len(self._last_rendered_lines)
            if num_prev_lines > 1:
                buf.append(CURSOR_UP(num_prev_lines - 1))
            buf.append(CURSOR_TO_COL(1))

            for i, line in enumerate(new_lines):
                buf.append(f"{line}{CLEAR_LINE}")
                if i < len(new_lines) - 1:
                    buf.append("\n")

            # Clear trailing extra lines if view shrank
            if len(new_lines) < num_prev_lines:
                extra = num_prev_lines - len(new_lines)
                for _ in range(extra):
                    buf.append("\n" + CLEAR_LINE)
                buf.append(CURSOR_UP(extra))

        self._last_rendered_lines = new_lines
        self.output_stream.write("".join(buf))
        self.output_stream.flush()
