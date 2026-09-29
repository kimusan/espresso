"""Terminal I/O, raw mode management, signals, and ANSI escape sequences."""

from __future__ import annotations

import atexit
import os
import shutil
import signal
import sys
from types import FrameType
from typing import Callable

# ANSI Escape Codes
CSI = "\x1b["
HIDE_CURSOR = f"{CSI}?25l"
SHOW_CURSOR = f"{CSI}?25h"
ENTER_ALT_SCREEN = f"{CSI}?1049h"
EXIT_ALT_SCREEN = f"{CSI}?1049l"
CLEAR_SCREEN = f"{CSI}2J{CSI}H"
CLEAR_LINE = f"{CSI}2K"
CLEAR_TO_EOL = f"{CSI}K"
CURSOR_UP = lambda n=1: f"{CSI}{n}A"
CURSOR_DOWN = lambda n=1: f"{CSI}{n}B"
CURSOR_TO_COL = lambda col=1: f"{CSI}{col}G"
ENABLE_MOUSE_SGR = f"{CSI}?1000h{CSI}?1002h{CSI}?1006h"
DISABLE_MOUSE_SGR = f"{CSI}?1000l{CSI}?1002l{CSI}?1006l"



class TerminalDriver:
    """Manages low-level terminal mode (raw/canonical), signals, and ANSI controls."""

    def __init__(self, alt_screen: bool = False, mouse: bool = False) -> None:
        self.alt_screen = alt_screen
        self.mouse = mouse
        self._orig_termios: list[int | list[bytes | int]] | None = None
        self._is_raw = False
        self._is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        self._on_resize: Callable[[int, int], None] | None = None
        self._orig_sigwinch_handler: Callable[[int, FrameType | None], None] | int | None = None

    @property
    def is_tty(self) -> bool:
        return self._is_tty

    def get_size(self) -> tuple[int, int]:
        """Return (width, height) of the terminal."""
        size = shutil.get_terminal_size((80, 24))
        return size.columns, size.lines

    def set_resize_handler(self, handler: Callable[[int, int], None]) -> None:
        """Register a callback for terminal window resize events."""
        self._on_resize = handler
        if hasattr(signal, "SIGWINCH") and self._is_tty:
            def _handle_winch(signum: int, frame: FrameType | None) -> None:
                w, h = self.get_size()
                if self._on_resize:
                    self._on_resize(w, h)

            self._orig_sigwinch_handler = signal.signal(signal.SIGWINCH, _handle_winch)

    def enter(self) -> None:
        """Enter raw mode and configure the terminal for TUI execution."""
        if not self._is_tty:
            return

        # Unix termios raw mode
        try:
            import termios

            fd = sys.stdin.fileno()
            self._orig_termios = termios.tcgetattr(fd)

            # Ensure stdin and stdout are in standard blocking mode
            try:
                os.set_blocking(fd, True)
                os.set_blocking(sys.stdout.fileno(), True)
            except Exception:
                pass

            # Make a copy of attributes for raw mode
            mode = list(self._orig_termios)

            # iflag: Disable flow control (XON/XOFF) and CR-to-NL translation
            mode[0] = mode[0] & ~(termios.IXON | termios.ICRNL | termios.BRKINT | termios.INPCK | termios.ISTRIP)

            # oflag: CRITICAL: Keep OPOST and ONLCR enabled so \n translates to \r\n
            # This completely prevents terminal staircase/skewing
            mode[1] = mode[1] | (termios.OPOST | termios.ONLCR)

            # cflag: 8-bit characters
            mode[2] = (mode[2] & ~(termios.CSIZE | termios.PARENB)) | termios.CS8

            # lflag: Disable canonical mode, local echo, signals (Ctrl+C as key), and extended input
            mode[3] = mode[3] & ~(termios.ICANON | termios.ECHO | termios.ISIG | termios.IEXTEN)

            # vmin = 1, vtime = 0: read blocks until at least 1 byte is available
            mode[6][termios.VMIN] = 1
            mode[6][termios.VTIME] = 0

            termios.tcsetattr(fd, termios.TCSADRAIN, mode)
            self._is_raw = True
            atexit.register(self.exit)
        except Exception:
            # Fallback if termios isn't available or fails
            self._is_raw = False


        # Output escape sequences
        out = [HIDE_CURSOR]
        if self.alt_screen:
            out.append(ENTER_ALT_SCREEN)
            out.append(CLEAR_SCREEN)
        if self.mouse:
            out.append(ENABLE_MOUSE_SGR)

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def exit(self) -> None:
        """Restore canonical terminal mode and original screen buffer."""
        if not self._is_tty:
            return

        out = [SHOW_CURSOR]
        if self.mouse:
            out.append(DISABLE_MOUSE_SGR)
        if self.alt_screen:
            out.append(EXIT_ALT_SCREEN)

        sys.stdout.write("".join(out))
        sys.stdout.flush()

        # Restore termios
        if self._is_raw and self._orig_termios is not None:
            try:
                import termios

                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._orig_termios)
                self._is_raw = False
            except Exception:
                pass

        # Ensure standard blocking mode is restored
        try:
            os.set_blocking(sys.stdin.fileno(), True)
            os.set_blocking(sys.stdout.fileno(), True)
        except Exception:
            pass


        # Restore signal handler
        if hasattr(signal, "SIGWINCH") and self._orig_sigwinch_handler is not None:
            try:
                signal.signal(signal.SIGWINCH, self._orig_sigwinch_handler)
            except Exception:
                pass

    def __enter__(self) -> TerminalDriver:
        self.enter()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.exit()
