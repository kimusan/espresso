"""The Program runtime engine coordinating The Elm Architecture loop."""

from __future__ import annotations

import asyncio
import inspect
import os
import sys
import threading
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
            # Determine initial window size and notify model so initial view has correct dimensions
            w, h = self._terminal.get_size()
            if inspect.iscoroutinefunction(self.model.update):
                self.model, size_cmd = await self.model.update(WindowSizeMsg(w, h))
            else:
                self.model, size_cmd = self.model.update(WindowSizeMsg(w, h))
            if size_cmd is not None:
                self._dispatch_cmd(size_cmd)

            # Trigger initial model command
            init_cmd = self.model.init()
            if init_cmd is not None:
                self._dispatch_cmd(init_cmd)

            # Initial render
            self._render(self.model.view())

            # Start stdin input listener thread (runs in blocking mode, no O_NONBLOCK side-effects)
            self._start_stdin_reader(loop)

            # Main event loop
            while self._running:
                msg = await self._queue.get()
                should_quit = await self._handle_msg(msg)
                if should_quit:
                    break

        finally:
            self._running = False
            for task in list(self._bg_tasks):
                task.cancel()

            self._terminal.exit()

            # Ensure clean carriage return and newline after inline mode
            if not self.alt_screen and self._last_rendered_lines:
                try:
                    self.output_stream.write("\r\n")
                    self.output_stream.flush()
                except Exception:
                    pass

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

        if isinstance(msg, WindowSizeMsg) and self.alt_screen:
            # On window resize in alt_screen, clear screen and reset diff buffer for a clean reflow
            self._last_rendered_lines = []
            try:
                self.output_stream.write("\x1b[2J\x1b[H")
                self.output_stream.flush()
            except Exception:
                pass

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

    def _start_stdin_reader(self, loop: asyncio.AbstractEventLoop) -> threading.Thread:
        """Start a daemon thread to read stdin in blocking mode without touching tty blocking flags."""
        def _worker() -> None:
            fd = None
            try:
                fd = self.input_stream.fileno()
            except Exception:
                pass

            while self._running:
                try:
                    if fd is not None:
                        # Blocking read in background thread
                        data = os.read(fd, 1024)
                    else:
                        chunk = self.input_stream.read(1)
                        if isinstance(chunk, str):
                            data = chunk.encode("utf-8")
                        else:
                            data = chunk or b""

                    if not data:
                        break

                    text = data.decode("utf-8", errors="replace")
                    for key_msg in parse_keys(text):
                        if self._queue is not None and self._running:
                            loop.call_soon_threadsafe(self._queue.put_nowait, key_msg)
                except Exception:
                    break

        thread = threading.Thread(target=_worker, name="Espresso-StdinReader", daemon=True)
        thread.start()
        return thread

    def _render(self, view_content: str) -> None:
        """Render view content to the terminal output stream."""
        new_lines = view_content.splitlines()
        buf = []

        if self.alt_screen:
            # Clamp rendered lines to terminal height to prevent terminal scrolling
            term_w, term_h = self._terminal.get_size()
            if term_h > 0 and len(new_lines) > term_h:
                new_lines = new_lines[:term_h]

            # Line-diffing alt-screen renderer
            if not self._last_rendered_lines:
                # Initial frame render
                buf.append("\x1b[H")
                for i, line in enumerate(new_lines):
                    buf.append(f"\x1b[{i + 1};1H\x1b[2K{line}")
            else:
                max_lines = max(len(new_lines), len(self._last_rendered_lines))
                for row_idx in range(max_lines):
                    old_line = self._last_rendered_lines[row_idx] if row_idx < len(self._last_rendered_lines) else None
                    new_line = new_lines[row_idx] if row_idx < len(new_lines) else None

                    if old_line == new_line:
                        continue

                    # Direct cursor jump to row (1-indexed), clear line, and write new_line
                    buf.append(f"\x1b[{row_idx + 1};1H\x1b[2K")
                    if new_line is not None:
                        buf.append(new_line)
        else:
            # Inline mode: rewrite lines over the previously rendered block
            num_prev_lines = len(self._last_rendered_lines)
            if num_prev_lines > 1:
                buf.append(CURSOR_UP(num_prev_lines - 1))
            buf.append("\r")

            for i, line in enumerate(new_lines):
                buf.append(f"\r\x1b[2K{line}")
                if i < len(new_lines) - 1:
                    buf.append("\r\n")

            # Clear trailing extra lines if view shrank
            if len(new_lines) < num_prev_lines:
                extra = num_prev_lines - len(new_lines)
                for _ in range(extra):
                    buf.append("\r\n\x1b[2K")
                buf.append(CURSOR_UP(extra))
                buf.append("\r")


        self._last_rendered_lines = new_lines
        payload = "".join(buf)

        try:
            self.output_stream.write(payload)
            self.output_stream.flush()
        except BlockingIOError:
            # If stdout fd was marked non-blocking externally, restore blocking and retry
            fd = getattr(self.output_stream, "fileno", None)
            if fd is not None:
                try:
                    os.set_blocking(fd(), True)
                except Exception:
                    pass
            try:
                self.output_stream.write(payload)
                self.output_stream.flush()
            except Exception:
                pass


