"""Accordion component for collapsible multi-panel containers wrapping child beans or text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg, batch
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class AccordionToggleMsg(Msg):
    """Message emitted whenever an accordion section is expanded or collapsed."""

    index: int
    item_id: str
    expanded: bool


@dataclass(frozen=True)
class AccordionSelectMsg(Msg):
    """Message emitted whenever the active accordion header changes."""

    index: int
    item_id: str


@dataclass
class AccordionItem:
    """A single collapsible section inside an Accordion.

    Can wrap any Model bean or plain string content.
    """

    id: str
    title: str
    content: Model | str
    expanded: bool = False
    badge: str | None = None
    icon_collapsed: str = "▶"
    icon_expanded: str = "▼"
    disabled: bool = False
    description: str | None = None


class Accordion(Model):
    """Collapsible accordion container bean that wraps child beans within expandable panels.

    Features:
    - Wraps any Model bean (e.g. Table, Form, List, ScrollView, TextInput) or text inside each level.
    - Single-expand mode (`allow_multiple=False`) or multi-expand mode (`allow_multiple=True`).
    - Full keyboard navigation:
      - Header navigation mode: `up`/`down`/`j`/`k` to navigate headers, `enter`/`space` to toggle.
      - Tab / Shift+Tab / Esc to focus into and out of interactive child beans.
    - Full mouse support: clicking headers toggles expansion; clicking into child beans dispatches with local coordinates.
    - Visual indicators (customizable `▼` / `▶` icons, badges, borders, and active highlights).
    - Lifecycle forwarding: automatically invokes `init()` on child Model beans.
    """

    def __init__(
        self,
        items: Sequence[AccordionItem] | None = None,
        width: int = 60,
        allow_multiple: bool = False,
        active_index: int = 0,
        bordered: bool = True,
        style: Style | None = None,
        header_active_style: Style | None = None,
        header_inactive_style: Style | None = None,
        header_disabled_style: Style | None = None,
        badge_style: Style | None = None,
        border_style: Style | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        self.items: list[AccordionItem] = list(items or [])
        self.width = max(20, width)
        self.allow_multiple = allow_multiple
        self.active_index = max(0, min(active_index, max(0, len(self.items) - 1)))
        self.bordered = bordered
        self.focus_child = False
        self.offset_x = offset_x
        self.offset_y = offset_y

        # Crema Styles
        self.style = style or Style()
        self.header_active_style = (
            header_active_style
            or Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        )
        self.header_inactive_style = (
            header_inactive_style
            or Style().foreground("#D0D0E0").background("#252535").padding(0, 1)
        )
        self.header_disabled_style = (
            header_disabled_style
            or Style().foreground("#666677").faint(True).padding(0, 1)
        )
        self.badge_style = badge_style or Style().foreground("#00E5FF").bold(True)
        self.border_style = border_style or Style().foreground("#444455")

        self._sync_child_focus()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen coordinate offsets for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y

    def init(self) -> Cmd | None:
        """Initialize all wrapped child beans."""
        cmds: list[Cmd] = []
        for item in self.items:
            if isinstance(item.content, Model):
                c = item.content.init()
                if c:
                    cmds.append(c)
        return batch(*cmds) if cmds else None

    def _sync_child_focus(self) -> None:
        """Propagate focus or blur to the active item's child bean."""
        for idx, item in enumerate(self.items):
            if isinstance(item.content, Model):
                should_focus = (idx == self.active_index and self.focus_child and item.expanded)
                if should_focus:
                    if hasattr(item.content, "focus") and callable(item.content.focus):
                        item.content.focus()
                    elif hasattr(item.content, "focused"):
                        item.content.focused = True
                else:
                    if hasattr(item.content, "blur") and callable(item.content.blur):
                        item.content.blur()
                    elif hasattr(item.content, "focused"):
                        item.content.focused = False

    def add_item(self, item: AccordionItem) -> None:
        """Add a new section to the accordion."""
        self.items.append(item)

    def remove_item(self, item_id: str) -> None:
        """Remove a section by its ID."""
        self.items = [it for it in self.items if it.id != item_id]
        if self.active_index >= len(self.items):
            self.active_index = max(0, len(self.items) - 1)
        self._sync_child_focus()

    def get_item(self, item_id: str) -> AccordionItem | None:
        """Find an item by its ID."""
        for it in self.items:
            if it.id == item_id:
                return it
        return None

    def _find_index(self, index_or_id: int | str) -> int | None:
        """Resolve an index or item_id to an integer index."""
        if isinstance(index_or_id, int):
            if 0 <= index_or_id < len(self.items):
                return index_or_id
            return None
        for i, it in enumerate(self.items):
            if it.id == index_or_id:
                return i
        return None

    def set_active(self, index_or_id: int | str) -> Cmd | None:
        """Change the active highlighted accordion header."""
        idx = self._find_index(index_or_id)
        if idx is not None and idx != self.active_index:
            self.active_index = idx
            item = self.items[idx]
            self._sync_child_focus()

            def _emit() -> Msg:
                return AccordionSelectMsg(index=idx, item_id=item.id)

            return _emit
        return None

    def toggle(self, index_or_id: int | str) -> Cmd | None:
        """Toggle expansion of an accordion section."""
        idx = self._find_index(index_or_id)
        if idx is None:
            return None

        item = self.items[idx]
        if item.disabled:
            return None

        if item.expanded:
            return self.collapse(idx)
        else:
            return self.expand(idx)

    def expand(self, index_or_id: int | str) -> Cmd | None:
        """Expand an accordion section."""
        idx = self._find_index(index_or_id)
        if idx is None:
            return None

        item = self.items[idx]
        if item.disabled or item.expanded:
            return None

        cmds: list[Cmd] = []
        # If single-expand mode, collapse all other sections
        if not self.allow_multiple:
            for i, other in enumerate(self.items):
                if i != idx and other.expanded:
                    other.expanded = False
                    other_id = other.id
                    other_idx = i

                    def _make_collapse_emit(i_idx: int, i_id: str) -> Cmd:
                        def _emit() -> Msg:
                            return AccordionToggleMsg(index=i_idx, item_id=i_id, expanded=False)
                        return _emit

                    cmds.append(_make_collapse_emit(other_idx, other_id))

        item.expanded = True
        self.active_index = idx
        self._sync_child_focus()

        def _make_expand_emit(i_idx: int, i_id: str) -> Cmd:
            def _emit() -> Msg:
                return AccordionToggleMsg(index=i_idx, item_id=i_id, expanded=True)
            return _emit

        cmds.append(_make_expand_emit(idx, item.id))
        return batch(*cmds) if cmds else None

    def collapse(self, index_or_id: int | str) -> Cmd | None:
        """Collapse an accordion section."""
        idx = self._find_index(index_or_id)
        if idx is None:
            return None

        item = self.items[idx]
        if not item.expanded:
            return None

        item.expanded = False
        if self.focus_child:
            self.focus_child = False
        self._sync_child_focus()

        def _emit() -> Msg:
            return AccordionToggleMsg(index=idx, item_id=item.id, expanded=False)

        return _emit

    def expand_all(self) -> Cmd | None:
        """Expand all sections (only applicable when allow_multiple is True)."""
        if not self.allow_multiple:
            return None
        cmds: list[Cmd] = []
        for i, it in enumerate(self.items):
            if not it.disabled and not it.expanded:
                c = self.expand(i)
                if c:
                    cmds.append(c)
        return batch(*cmds) if cmds else None

    def collapse_all(self) -> Cmd | None:
        """Collapse all sections."""
        cmds: list[Cmd] = []
        for i, it in enumerate(self.items):
            if it.expanded:
                c = self.collapse(i)
                if c:
                    cmds.append(c)
        return batch(*cmds) if cmds else None

    def _next_enabled_index(self, start: int, step: int) -> int:
        """Find the next non-disabled index in direction step."""
        if not self.items:
            return 0
        curr = start
        for _ in range(len(self.items)):
            curr = (curr + step) % len(self.items)
            if not self.items[curr].disabled:
                return curr
        return start

    def update(self, msg: Msg) -> tuple[Accordion, Cmd | None]:
        """Handle keyboard navigation, mouse interactions, and delegate to active child bean."""
        # 1. Child focus mode: delegate keyboard input directly to child Model
        if self.focus_child and 0 <= self.active_index < len(self.items):
            active_item = self.items[self.active_index]
            if isinstance(active_item.content, Model):
                if isinstance(msg, KeyMsg) and msg.key in ("esc", "shift+tab"):
                    self.focus_child = False
                    self._sync_child_focus()
                    return self, None

                # Forward event to child
                active_item.content, child_cmd = active_item.content.update(msg)
                return self, child_cmd

        # 2. Header navigation mode
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "up" | "k":
                    new_idx = self._next_enabled_index(self.active_index, -1)
                    cmd = self.set_active(new_idx)
                    return self, cmd

                case "down" | "j":
                    new_idx = self._next_enabled_index(self.active_index, 1)
                    cmd = self.set_active(new_idx)
                    return self, cmd

                case "home" | "g":
                    for i, it in enumerate(self.items):
                        if not it.disabled:
                            return self, self.set_active(i)

                case "end" | "G":
                    for i in reversed(range(len(self.items))):
                        if not self.items[i].disabled:
                            return self, self.set_active(i)

                case "enter" | " ":
                    cmd = self.toggle(self.active_index)
                    return self, cmd

                case "right" | "e":
                    cmd = self.expand(self.active_index)
                    return self, cmd

                case "left" | "c":
                    cmd = self.collapse(self.active_index)
                    return self, cmd

                case "tab":
                    # If active section is expanded and content is a Model, enter child focus
                    if 0 <= self.active_index < len(self.items):
                        it = self.items[self.active_index]
                        if it.expanded and isinstance(it.content, Model):
                            self.focus_child = True
                            self._sync_child_focus()
                            return self, None

        # 3. Mouse interactions
        if isinstance(msg, MouseMsg):
            local_x = msg.x - self.offset_x
            local_y = msg.y - self.offset_y

            # Calculate vertical slice intervals for each header and content area
            curr_y = 0
            for idx, item in enumerate(self.items):
                # Header row occupies 1 line (plus top border if bordered)
                header_start = curr_y
                header_h = 1
                header_end = header_start + header_h

                if (
                    msg.button == MouseButton.LEFT
                    and msg.action == MouseAction.PRESS
                    and header_start <= local_y < header_end
                    and 0 <= local_x < self.width
                ):
                    self.active_index = idx
                    self.focus_child = False
                    cmd = self.toggle(idx)
                    return self, cmd

                curr_y = header_end

                # Expanded content area
                if item.expanded:
                    rendered_lines = self._get_item_content_lines(item)
                    content_h = len(rendered_lines)
                    content_start = curr_y
                    content_end = content_start + content_h

                    if content_start <= local_y < content_end and 0 <= local_x < self.width:
                        # Clicked inside content area
                        self.active_index = idx
                        if isinstance(item.content, Model):
                            self.focus_child = True
                            self._sync_child_focus()
                            # Translate mouse coordinates for child
                            child_y = local_y - content_start
                            # 2 characters indent
                            child_x = max(0, local_x - 2)
                            child_msg = MouseMsg(
                                x=child_x,
                                y=child_y,
                                button=msg.button,
                                action=msg.action,
                                shift=msg.shift,
                                alt=msg.alt,
                                ctrl=msg.ctrl,
                            )
                            item.content, child_cmd = item.content.update(child_msg)
                            return self, child_cmd
                        return self, None

                    curr_y = content_end

                # Spacing row between sections
                curr_y += 1

        return self, None

    def _get_item_content_lines(self, item: AccordionItem) -> list[str]:
        """Obtain rendered content lines for an item."""
        if isinstance(item.content, Model):
            raw = item.content.view()
        else:
            raw = str(item.content)
        if not raw:
            return []
        return raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    def view(self) -> str:
        """Render the complete accordion layout with styled headers, indicators, and content."""
        if not self.items:
            empty_style = Style().foreground("#777788").italic(True)
            return empty_style.render("No accordion sections.")

        lines: list[str] = []
        inner_w = self.width

        for idx, item in enumerate(self.items):
            is_active = (idx == self.active_index)
            is_expanded = item.expanded

            # 1. Prepare Header text components
            icon = item.icon_expanded if is_expanded else item.icon_collapsed
            icon_str = f"{icon} "

            badge_str = ""
            if item.badge:
                badge_rendered = self.badge_style.render(f"[{item.badge}]")
                badge_str = f" {badge_rendered}"

            focus_marker = "● " if (is_active and self.focus_child) else ""

            # Header style selection
            if item.disabled:
                h_style = self.header_disabled_style
            elif is_active:
                h_style = self.header_active_style
            else:
                h_style = self.header_inactive_style

            # Compute available title width
            prefix = f"{focus_marker}{icon_str}"
            prefix_w = string_width(prefix)
            badge_w = string_width(f" [{item.badge}]") if item.badge else 0
            avail_title_w = max(1, inner_w - prefix_w - badge_w - 2)
            title_truncated = truncate_ansi(item.title, avail_title_w, tail="…")

            # Combine header content
            left_part = f"{prefix}{title_truncated}"
            used_w = string_width(left_part) + badge_w
            spacing = " " * max(1, inner_w - used_w - 2)
            header_raw = f"{left_part}{spacing}{badge_str}"

            rendered_header = h_style.width(inner_w).render(header_raw)
            lines.append(rendered_header)

            # 2. Render expanded content
            if is_expanded:
                content_lines = self._get_item_content_lines(item)
                content_avail_w = max(1, inner_w - 2)

                indent_char = self.border_style.render("│ ")
                for c_line in content_lines:
                    truncated_c = truncate_ansi(c_line, content_avail_w, tail="")
                    pad = " " * max(0, content_avail_w - string_width(truncated_c))
                    lines.append(f"{indent_char}{truncated_c}{pad}")

            # Blank separator line between sections
            if idx < len(self.items) - 1:
                lines.append(self.border_style.render("─" * inner_w))

        result = "\n".join(lines)
        if self.style._width is None and self.width > 0:
            return self.style.width(self.width).render(result)
        return self.style.render(result)
