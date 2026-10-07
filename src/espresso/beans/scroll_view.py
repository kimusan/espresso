"""ScrollView component for scrollable containers wrapping child beans or text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class ScrollChangeMsg(Msg):
    """Message emitted whenever the scroll offset changes."""

    offset_y: int
    max_offset: int
    percent: float


class ScrollView(Model):
    """Scrollable container bean that wraps any child Model or text content.

    Features:
    - Wraps any Model bean (e.g. Table, Form, Accordion, List) or plain string.
    - Dynamically calculates content dimensions and clamps scroll offset.
    - Renders an integrated vertical scrollbar with customizable thumb and track styles.
    - Full keyboard navigation (arrow keys, page up/down, home/end).
    - Full mouse support (wheel up/down, clicking on scrollbar to jump, coordinate translation for child).
    - Forwards TEA lifecycle (`init`, `update`) to the child Model.
    """

    def __init__(
        self,
        child: Model | str = "",
        width: int = 80,
        height: int = 20,
        show_scrollbar: bool = True,
        scroll_step: int = 1,
        page_step: int | None = None,
        style: Style | None = None,
        scrollbar_thumb_style: Style | None = None,
        scrollbar_track_style: Style | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
        auto_forward_keys: bool = True,
    ) -> None:
        self.child = child
        self.width = max(5, width)
        self.height = max(1, height)
        self.show_scrollbar = show_scrollbar
        self.scroll_step = max(1, scroll_step)
        self.page_step = page_step
        self.style = style or Style()
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.auto_forward_keys = auto_forward_keys

        # Scroll state
        self.y_offset = 0
        self.x_offset = 0

        # Styles
        self.scrollbar_thumb_style = scrollbar_thumb_style or Style().foreground("#7D56F4").bold(True)
        self.scrollbar_track_style = scrollbar_track_style or Style().foreground("#333344")

    def init(self) -> Cmd | None:
        """Initialize the wrapped child if it is a TEA Model or has init()."""
        if hasattr(self.child, "init") and callable(self.child.init):
            return self.child.init()
        return None

    def set_child(self, child: Model | str) -> None:
        """Replace the wrapped child component or text content."""
        self.child = child
        self._clamp_offset()

    def set_content(self, text: str) -> None:
        """Set raw text content (backwards-compatible with Viewport API)."""
        self.child = text
        self._clamp_offset()

    def set_dimensions(self, width: int, height: int) -> None:
        """Resize the scroll view container."""
        self.width = max(5, width)
        self.height = max(1, height)
        self._clamp_offset()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen coordinate offsets for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    def _get_raw_lines(self) -> list[str]:
        """Extract lines of rendered child content."""
        if hasattr(self.child, "view") and callable(self.child.view):
            rendered = self.child.view()
        else:
            rendered = str(self.child)

        if not rendered:
            return []
        return rendered.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    @property
    def total_lines(self) -> int:
        """Total number of rendered lines in child content."""
        return len(self._get_raw_lines())

    @property
    def max_offset(self) -> int:
        """Maximum allowable vertical scroll offset."""
        return max(0, self.total_lines - self.height)

    @property
    def scroll_percent(self) -> float:
        """Current vertical scroll position ratio from 0.0 (top) to 1.0 (bottom)."""
        m = self.max_offset
        if m == 0:
            return 1.0
        return self.y_offset / m

    def _clamp_offset(self) -> None:
        """Ensure y_offset stays within [0, max_offset]."""
        self.y_offset = max(0, min(self.y_offset, self.max_offset))

    def scroll_to(self, target_y: int) -> Cmd | None:
        """Scroll to a specific vertical line offset."""
        new_y = max(0, min(target_y, self.max_offset))
        if new_y != self.y_offset:
            self.y_offset = new_y
            cur_y = self.y_offset
            max_y = self.max_offset
            pct = self.scroll_percent

            def _emit() -> Msg:
                return ScrollChangeMsg(offset_y=cur_y, max_offset=max_y, percent=pct)

            return _emit
        return None

    def scroll_by(self, delta_y: int) -> Cmd | None:
        """Scroll vertically by delta lines."""
        return self.scroll_to(self.y_offset + delta_y)

    def scroll_to_top(self) -> Cmd | None:
        """Scroll to the very beginning of the content."""
        return self.scroll_to(0)

    def scroll_to_bottom(self) -> Cmd | None:
        """Scroll to the very end of the content."""
        return self.scroll_to(self.max_offset)

    def update(self, msg: Msg) -> tuple[ScrollView, Cmd | None]:
        """Handle keyboard scrolling, mouse events, and delegate to child."""
        cmd: Cmd | None = None
        consumed_by_scroll = False

        if isinstance(msg, KeyMsg):
            p_step = self.page_step or self.height
            match msg.key:
                case "pageup" | "ctrl+u":
                    cmd = self.scroll_by(-p_step)
                    consumed_by_scroll = True
                case "pagedown" | "ctrl+d":
                    cmd = self.scroll_by(p_step)
                    consumed_by_scroll = True
                case "home" if not hasattr(self.child, "update"):
                    cmd = self.scroll_to_top()
                    consumed_by_scroll = True
                case "end" if not hasattr(self.child, "update"):
                    cmd = self.scroll_to_bottom()
                    consumed_by_scroll = True
                case "up" | "k" if not hasattr(self.child, "update"):
                    cmd = self.scroll_by(-self.scroll_step)
                    consumed_by_scroll = True
                case "down" | "j" if not hasattr(self.child, "update"):
                    cmd = self.scroll_by(self.scroll_step)
                    consumed_by_scroll = True

        elif isinstance(msg, MouseMsg):
            # Mouse wheel always scrolls the viewport
            if msg.button == MouseButton.WHEEL_UP:
                cmd = self.scroll_by(-self.scroll_step)
                return self, cmd
            elif msg.button == MouseButton.WHEEL_DOWN:
                cmd = self.scroll_by(self.scroll_step)
                return self, cmd

            # Check if clicked on the vertical scrollbar track
            content_w = self.width - (1 if self.show_scrollbar else 0)
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            if self.show_scrollbar and local_x == content_w and 0 <= local_y < self.height:
                if msg.action == MouseAction.PRESS and self.max_offset > 0:
                    ratio = local_y / max(1, self.height - 1)
                    target = int(round(ratio * self.max_offset))
                    cmd = self.scroll_to(target)
                    return self, cmd

        # If not consumed by container scrolling, forward to child Model
        child_cmd: Cmd | None = None
        if not consumed_by_scroll and hasattr(self.child, "update") and callable(self.child.update):
            # Translate mouse coordinates for child relative to current scroll offset
            child_msg = msg
            if isinstance(msg, MouseMsg):
                translated_x = msg.x - self.offset_x + self.x_offset
                translated_y = msg.y - self.offset_y + self.y_offset
                child_msg = MouseMsg(
                    x=translated_x,
                    y=translated_y,
                    button=msg.button,
                    action=msg.action,
                    shift=msg.shift,
                    alt=msg.alt,
                    ctrl=msg.ctrl,
                )

            self.child, child_cmd = self.child.update(child_msg)
            self._clamp_offset()

        final_cmd = cmd or child_cmd
        return self, final_cmd

    def view(self) -> str:
        """Render the visible window of lines truncated to width and padded to height."""
        if self.width <= 0 or self.height <= 0:
            return ""

        raw_lines = self._get_raw_lines()
        self._clamp_offset()

        content_w = self.width - (1 if self.show_scrollbar else 0)
        visible = raw_lines[self.y_offset : self.y_offset + self.height]

        # Truncate lines to content width and pad trailing whitespace
        formatted_lines: list[str] = []
        for line in visible:
            truncated = truncate_ansi(line, content_w, tail="")
            pad = max(0, content_w - string_width(truncated))
            formatted_lines.append(f"{truncated}{' ' * pad}")

        # Fill remaining height with blank rows if content is short
        while len(formatted_lines) < self.height:
            formatted_lines.append(" " * content_w)

        # Composite vertical scrollbar
        if self.show_scrollbar and self.height > 0:
            total = len(raw_lines)
            if total <= self.height or total == 0:
                # Content completely fits
                for r in range(self.height):
                    formatted_lines[r] = f"{formatted_lines[r]}{self.scrollbar_track_style.render('│')}"
            else:
                thumb_size = max(1, int(round((self.height / total) * self.height)))
                max_scroll = max(1, total - self.height)
                thumb_pos = int((self.y_offset / max_scroll) * (self.height - thumb_size))
                thumb_pos = max(0, min(self.height - thumb_size, thumb_pos))

                for r in range(self.height):
                    if thumb_pos <= r < thumb_pos + thumb_size:
                        bar_char = self.scrollbar_thumb_style.render("█")
                    else:
                        bar_char = self.scrollbar_track_style.render("│")
                    formatted_lines[r] = f"{formatted_lines[r]}{bar_char}"

        result = "\n".join(formatted_lines)
        vp_style = self.style
        if vp_style._width is None and self.width > 0:
            vp_style = vp_style.width(self.width)

        return vp_style.render(result)
