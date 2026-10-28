"""Desktop application menu bar with drop-down menus, keyboard mnemonics, and mouse interaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import NORMAL_BORDER
from espresso.crema.overlay import place_overlay
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass
class MenuItem:
    """An individual command or separator inside a drop-down menu."""

    id: str
    label: str
    shortcut: str = ""       # e.g., "Ctrl+N", "F5", "Ctrl+S"
    enabled: bool = True
    is_separator: bool = False
    action: Callable[[], Any] | None = None


@dataclass
class MenuCategory:
    """A top-level category on the menu bar holding a list of drop-down items."""

    id: str
    label: str              # e.g., "File", "Edit", "View", "Help"
    mnemonic: str = ""       # e.g., "f" for Alt+F access
    items: list[MenuItem] = field(default_factory=list)


@dataclass(frozen=True)
class MenuSelectMsg(Msg):
    """Message emitted when an item in the drop-down menu is chosen."""

    category_id: str
    item_id: str


@dataclass(frozen=True)
class MenuOpenMsg(Msg):
    """Message emitted when a menu category is opened."""

    category_id: str


@dataclass(frozen=True)
class MenuCloseMsg(Msg):
    """Message emitted when the active menu is closed without selection."""

    pass


class MenuBar(Model):
    """Desktop-style top application menu bar with cascading drop-down menus.

    Supports keyboard shortcuts (F10, Alt+Mnemonic, arrow keys, Enter, Esc),
    mouse click and hover navigation, separators, disabled items, and overlay rendering.
    """

    def __init__(
        self,
        categories: list[MenuCategory] | None = None,
        width: int = 80,
        brand: str = "",
        right_status: str = "",
        offset_x: int = 0,
        offset_y: int = 0,
        bar_style: Style | None = None,
        category_style: Style | None = None,
        active_category_style: Style | None = None,
        dropdown_border_style: Style | None = None,
        item_style: Style | None = None,
        selected_item_style: Style | None = None,
        disabled_item_style: Style | None = None,
        shortcut_style: Style | None = None,
        separator_style: Style | None = None,
    ) -> None:
        self.categories: list[MenuCategory] = categories or []
        self.width: int = max(20, width)
        self.brand: str = brand
        self.right_status: str = right_status
        self.offset_x: int = offset_x
        self.offset_y: int = offset_y

        self.is_open: bool = False
        self.active_cat_idx: int = 0
        self.active_item_idx: int = 0

        # Styles with attractive default dark theme palette
        self.bar_style = bar_style or Style().background("#1E1E2E").foreground("#CDD6F4")
        self.category_style = category_style or Style().background("#1E1E2E").foreground("#CDD6F4")
        self.active_category_style = active_category_style or Style().bold(True).background("#89B4FA").foreground("#11111B")
        self.dropdown_border_style = dropdown_border_style or Style().foreground("#89B4FA").background("#181825")
        self.item_style = item_style or Style().foreground("#CDD6F4").background("#181825")
        self.selected_item_style = selected_item_style or Style().bold(True).background("#89B4FA").foreground("#11111B")
        self.disabled_item_style = disabled_item_style or Style().foreground("#585B70").background("#181825")
        self.shortcut_style = shortcut_style or Style().foreground("#A6ADC8")
        self.separator_style = separator_style or Style().foreground("#45475A").background("#181825")

        self._cat_bounds: list[tuple[int, int]] = []
        self._compute_bounds()

    def set_size(self, width: int, height: int | None = None) -> None:
        """Update the menu bar width."""
        self.width = max(20, width)
        self._compute_bounds()

    def set_offset(self, x: int, y: int) -> None:
        """Set screen offset coordinates for mouse hit-testing."""
        self.offset_x = x
        self.offset_y = y
        self._compute_bounds()

    def _compute_bounds(self) -> None:
        """Calculate start and end column bounds for each category header."""
        self._cat_bounds = []
        x = self.offset_x
        if self.brand:
            x += string_width(self.brand) + 1

        for cat in self.categories:
            label = f" {cat.label} ▾ "
            w = string_width(label)
            self._cat_bounds.append((x, x + w))
            x += w + 1

    def _find_next_selectable_item(self, items: list[MenuItem], start_idx: int, direction: int) -> int:
        """Find the next enabled, non-separator item index wrapping around."""
        if not items:
            return 0
        n = len(items)
        idx = start_idx
        for _ in range(n):
            idx = (idx + direction) % n
            item = items[idx]
            if not item.is_separator and item.enabled:
                return idx
        return start_idx

    def open_category(self, index: int) -> Cmd | None:
        """Open a menu category by index."""
        if not self.categories:
            return None
        self.active_cat_idx = index % len(self.categories)
        cat = self.categories[self.active_cat_idx]
        self.active_item_idx = self._find_next_selectable_item(cat.items, -1, 1)
        self.is_open = True
        return lambda: MenuOpenMsg(cat.id)

    def close(self) -> Cmd | None:
        """Close the active menu."""
        if not self.is_open:
            return None
        self.is_open = False
        return lambda: MenuCloseMsg()

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MenuBar, Cmd | None]:
        """Process keyboard shortcuts and mouse clicks for menu navigation."""
        if isinstance(msg, KeyMsg):
            k = str(msg.key).lower()

            # Check mnemonic shortcuts (e.g., 'alt+f' or 'alt+e')
            for idx, cat in enumerate(self.categories):
                if cat.mnemonic and k == f"alt+{cat.mnemonic.lower()}":
                    cmd = self.open_category(idx)
                    return self, cmd

            # F10 or standalone 'm' to activate menu bar
            if k in ("f10", "menu"):
                if self.is_open:
                    cmd = self.close()
                else:
                    cmd = self.open_category(0)
                return self, cmd

            if not self.is_open:
                return self, None

            cat = self.categories[self.active_cat_idx]

            if k in ("esc", "q"):
                cmd = self.close()
                return self, cmd

            if k in ("left", "h"):
                new_idx = (self.active_cat_idx - 1) % len(self.categories)
                cmd = self.open_category(new_idx)
                return self, cmd

            if k in ("right", "l", "tab"):
                new_idx = (self.active_cat_idx + 1) % len(self.categories)
                cmd = self.open_category(new_idx)
                return self, cmd

            if k in ("up", "k"):
                self.active_item_idx = self._find_next_selectable_item(cat.items, self.active_item_idx, -1)
                return self, None

            if k in ("down", "j"):
                self.active_item_idx = self._find_next_selectable_item(cat.items, self.active_item_idx, 1)
                return self, None

            if k in ("enter", " ", "space"):
                if 0 <= self.active_item_idx < len(cat.items):
                    chosen = cat.items[self.active_item_idx]
                    if chosen.enabled and not chosen.is_separator:
                        self.is_open = False
                        if chosen.action:
                            try:
                                chosen.action()
                            except Exception:
                                pass
                        cat_id, item_id = cat.id, chosen.id
                        return self, lambda: MenuSelectMsg(cat_id, item_id)
                return self, None

        elif isinstance(msg, MouseMsg):
            # 1. Mouse Wheel Scrolling
            if msg.button in (MouseButton.WHEEL_UP, MouseButton.WHEEL_DOWN):
                step = -1 if msg.button == MouseButton.WHEEL_UP else 1
                if self.is_open:
                    drop_info = self.dropdown_bounds()
                    if drop_info:
                        drop_x, drop_y, drop_w, drop_h = drop_info
                        if drop_x <= msg.x < drop_x + drop_w and drop_y <= msg.y < drop_y + drop_h:
                            cat = self.categories[self.active_cat_idx]
                            self.active_item_idx = self._find_next_selectable_item(cat.items, self.active_item_idx, step)
                            return self, None
                    # Wheel on header cycles category
                    if msg.y == self.offset_y and self.categories:
                        new_cat_idx = (self.active_cat_idx + step) % len(self.categories)
                        return self, self.open_category(new_cat_idx)
                elif msg.y == self.offset_y and self.categories:
                    # Wheel on header when closed opens and cycles category
                    new_cat_idx = (self.active_cat_idx + step) % len(self.categories)
                    return self, self.open_category(new_cat_idx)
                return self, None

            # 2. Mouse Press or Double Click
            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                # Click on Top Bar
                if msg.y == self.offset_y:
                    if msg.button == MouseButton.LEFT:
                        for idx, (x0, x1) in enumerate(self._cat_bounds):
                            if x0 <= msg.x < x1:
                                if self.is_open and self.active_cat_idx == idx:
                                    cmd = self.close()
                                else:
                                    cmd = self.open_category(idx)
                                return self, cmd
                    # Clicked on top bar outside category headers
                    if self.is_open:
                        cmd = self.close()
                        return self, cmd

                # Click inside open Dropdown or outside
                if self.is_open:
                    if msg.button == MouseButton.LEFT:
                        cat = self.categories[self.active_cat_idx]
                        drop_info = self.dropdown_bounds()
                        if drop_info:
                            drop_x, drop_y, drop_w, drop_h = drop_info
                            item_row = msg.y - (drop_y + 1)
                            if drop_x <= msg.x < drop_x + drop_w and 0 <= item_row < len(cat.items):
                                chosen = cat.items[item_row]
                                if chosen.enabled and not chosen.is_separator:
                                    self.is_open = False
                                    if chosen.action:
                                        try:
                                            chosen.action()
                                        except Exception:
                                            pass
                                    cat_id, item_id = cat.id, chosen.id
                                    return self, lambda: MenuSelectMsg(cat_id, item_id)
                    # Clicked outside dropdown
                    cmd = self.close()
                    return self, cmd

            # 3. Mouse Release (Press-drag-release desktop paradigm)
            elif msg.action == MouseAction.RELEASE and self.is_open and msg.button == MouseButton.LEFT:
                drop_info = self.dropdown_bounds()
                if drop_info:
                    drop_x, drop_y, drop_w, drop_h = drop_info
                    item_row = msg.y - (drop_y + 1)
                    cat = self.categories[self.active_cat_idx]
                    if drop_x <= msg.x < drop_x + drop_w and 0 <= item_row < len(cat.items):
                        chosen = cat.items[item_row]
                        if chosen.enabled and not chosen.is_separator:
                            self.is_open = False
                            if chosen.action:
                                try:
                                    chosen.action()
                                except Exception:
                                    pass
                            cat_id, item_id = cat.id, chosen.id
                            return self, lambda: MenuSelectMsg(cat_id, item_id)

            # 4. Mouse Motion (Hover navigation while open)
            elif msg.action == MouseAction.MOTION and self.is_open:
                if msg.y == self.offset_y:
                    for idx, (x0, x1) in enumerate(self._cat_bounds):
                        if x0 <= msg.x < x1 and idx != self.active_cat_idx:
                            cmd = self.open_category(idx)
                            return self, cmd
                else:
                    drop_info = self.dropdown_bounds()
                    if drop_info:
                        drop_x, drop_y, drop_w, drop_h = drop_info
                        item_row = msg.y - (drop_y + 1)
                        cat = self.categories[self.active_cat_idx]
                        if drop_x <= msg.x < drop_x + drop_w and 0 <= item_row < len(cat.items):
                            target = cat.items[item_row]
                            if target.enabled and not target.is_separator:
                                self.active_item_idx = item_row

        return self, None

    def dropdown_bounds(self) -> tuple[int, int, int, int] | None:
        """Calculate (x, y, width, height) of the open drop-down menu."""
        if not self.is_open or not self.categories:
            return None
        cat = self.categories[self.active_cat_idx]
        x = self._cat_bounds[self.active_cat_idx][0] if self.active_cat_idx < len(self._cat_bounds) else self.offset_x
        y = self.offset_y + 1

        # Determine drop-down width based on longest item + shortcut
        inner_w = 24
        for it in cat.items:
            sc_len = len(it.shortcut) + 2 if it.shortcut else 0
            w = string_width(it.label) + sc_len + 4
            inner_w = max(inner_w, w)

        # Border adds 2 cells horizontally, 2 cells vertically
        total_w = inner_w + 2
        total_h = len(cat.items) + 2

        # Clamp right edge so it doesn't overflow screen width
        if x + total_w > self.offset_x + self.width:
            x = max(self.offset_x, self.offset_x + self.width - total_w)

        return (x, y, total_w, total_h)

    def get_open_dropdown(self) -> tuple[str, int, int] | None:
        """Render the open drop-down menu box and return (rendered_str, x, y)."""
        bounds = self.dropdown_bounds()
        if not bounds:
            return None
        drop_x, drop_y, total_w, _ = bounds
        inner_w = total_w - 2
        cat = self.categories[self.active_cat_idx]

        content_rows: list[str] = []
        for idx, item in enumerate(cat.items):
            if item.is_separator:
                sep_line = "─" * inner_w
                content_rows.append(self.separator_style.render(sep_line))
                continue

            sc_txt = f"[{item.shortcut}]" if item.shortcut else ""
            sc_len = string_width(sc_txt)
            lbl_w = string_width(item.label)

            pad_len = max(1, inner_w - lbl_w - sc_len - 2)
            row_text = f" {item.label}{' ' * pad_len}{sc_txt} "

            if not item.enabled:
                row_str = self.disabled_item_style.render(row_text)
            elif idx == self.active_item_idx:
                row_str = self.selected_item_style.render(row_text)
            else:
                row_str = self.item_style.render(row_text)
            content_rows.append(row_str)

        # Build bordered dropdown box
        b_tl = NORMAL_BORDER.top_left
        b_tr = NORMAL_BORDER.top_right
        b_bl = NORMAL_BORDER.bottom_left
        b_br = NORMAL_BORDER.bottom_right
        b_h = NORMAL_BORDER.top
        b_v = NORMAL_BORDER.left

        top_line = self.dropdown_border_style.render(b_tl + (b_h * inner_w) + b_tr)
        bottom_line = self.dropdown_border_style.render(b_bl + (b_h * inner_w) + b_br)

        box_lines = [top_line]
        for row in content_rows:
            v_edge = self.dropdown_border_style.render(b_v)
            box_lines.append(f"{v_edge}{row}{v_edge}")
        box_lines.append(bottom_line)

        return ("\n".join(box_lines), drop_x, drop_y)

    def render_overlay(self, base_view: str) -> str:
        """Composite the active drop-down menu on top of base_view if open."""
        drop_info = self.get_open_dropdown()
        if not drop_info:
            return base_view
        drop_str, drop_x, drop_y = drop_info

        base_lines = base_view.replace("\r\n", "\n").replace("\r", "\n").split("\n") if base_view else [""]
        drop_lines = drop_str.split("\n")
        target_w = max(self.width, max((string_width(l) for l in base_lines), default=self.width))
        target_h = max(len(base_lines), drop_y + len(drop_lines))

        padded_base: list[str] = []
        for i in range(target_h):
            if i < len(base_lines):
                line = base_lines[i]
                w = string_width(line)
                padded_base.append(line + (" " * max(0, target_w - w)))
            else:
                padded_base.append(" " * target_w)
        full_base = "\n".join(padded_base)

        return place_overlay(full_base, drop_str, x=drop_x, y=drop_y)

    def view(self) -> str:
        """Render the single-line top application menu bar."""
        parts: list[str] = []

        if self.brand:
            parts.append(self.bar_style.bold(True).render(self.brand))

        for idx, cat in enumerate(self.categories):
            lbl = f" {cat.label} ▾ "
            if self.is_open and idx == self.active_cat_idx:
                parts.append(self.active_category_style.render(lbl))
            else:
                # Underline mnemonic character if present
                if cat.mnemonic and cat.mnemonic.lower() in cat.label.lower():
                    pos = cat.label.lower().index(cat.mnemonic.lower())
                    pre = cat.label[:pos]
                    ch = cat.label[pos]
                    post = cat.label[pos + 1 :]
                    rendered_cat = (
                        self.category_style.render(f" {pre}")
                        + self.category_style.underline(True).render(ch)
                        + self.category_style.underline(False).render(f"{post} ▾ ")
                    )
                    parts.append(rendered_cat)
                else:
                    parts.append(self.category_style.render(lbl))

        left_cluster = " ".join(parts)
        left_w = string_width(left_cluster)

        right_rendered = ""
        right_w = 0
        if self.right_status:
            right_rendered = self.bar_style.foreground("#A6ADC8").render(f" {self.right_status} ")
            right_w = string_width(right_rendered)

        spacer_len = max(0, self.width - left_w - right_w)
        spacer = self.bar_style.render(" " * spacer_len)

        return left_cluster + spacer + right_rendered
