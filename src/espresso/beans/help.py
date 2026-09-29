"""Help component for keybinding documentation and hotkey hints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from espresso.core.keys import Key, KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.layout import join_horizontal
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width


@dataclass
class KeyBinding:
    """Represents a key combination and its descriptive help entry."""

    keys: list[str]
    help_desc: str
    help_key: str
    enabled: bool = True

    def __init__(
        self,
        keys: str | Sequence[str],
        help_desc: str,
        help_key: str | None = None,
        enabled: bool = True,
    ) -> None:
        if isinstance(keys, str):
            self.keys = [keys]
        else:
            self.keys = list(keys)
        self.help_desc = help_desc
        self.help_key = help_key if help_key is not None else "/".join(self.keys)
        self.enabled = enabled

    def matches(self, msg: KeyMsg | Key | str) -> bool:
        """Check if a key message or key string matches this binding."""
        if not self.enabled:
            return False
        if isinstance(msg, KeyMsg):
            return msg.key.name in self.keys or (msg.key.char is not None and msg.key.char in self.keys)
        if isinstance(msg, Key):
            return msg.name in self.keys or (msg.char is not None and msg.char in self.keys)
        if isinstance(msg, str):
            return msg in self.keys
        return False


@runtime_checkable
class KeyMap(Protocol):
    """Protocol for models or containers that expose keybinding lists."""

    def short_help(self) -> list[KeyBinding]:
        """Return bindings shown in single-line compact help."""
        ...

    def full_help(self) -> list[list[KeyBinding]]:
        """Return column groups of bindings shown in multi-column full help."""
        ...


class Help(Model):
    """Keybinding helper rendering compact single-line or multi-column full help."""

    def __init__(
        self,
        key_map: KeyMap | Sequence[KeyBinding] | Sequence[Sequence[KeyBinding]] | None = None,
        width: int | None = None,
        show_all: bool = False,
        short_separator: str = " • ",
        column_gap: int = 4,
        key_style: Style | None = None,
        desc_style: Style | None = None,
        sep_style: Style | None = None,
    ) -> None:
        self.key_map = key_map
        self.width = width
        self.show_all = show_all
        self.short_separator = short_separator
        self.column_gap = column_gap

        self.key_style = key_style or Style().bold(True).foreground("#7D56F4")
        self.desc_style = desc_style or Style().foreground("#888888")
        self.sep_style = sep_style or Style().foreground("#444444")

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Help, Cmd | None]:
        return self, None

    def toggle(self) -> None:
        """Toggle between compact single-line help and full multi-column help."""
        self.show_all = not self.show_all

    def _resolve(
        self,
        target: KeyMap | Sequence[KeyBinding] | Sequence[Sequence[KeyBinding]] | None,
    ) -> tuple[list[KeyBinding], list[list[KeyBinding]]]:
        km = target if target is not None else self.key_map
        if km is None:
            return [], []

        # If it conforms to KeyMap protocol
        if hasattr(km, "short_help") and callable(km.short_help):
            short = km.short_help()
            full = km.full_help() if hasattr(km, "full_help") and callable(km.full_help) else [short]
            return list(short), [list(col) for col in full]

        # If it's a sequence of sequences of KeyBinding
        if isinstance(km, (list, tuple)) and len(km) > 0 and isinstance(km[0], (list, tuple)):
            groups = [list(col) for col in km]  # type: ignore[arg-type]
            flattened = [b for col in groups for b in col]
            return flattened, groups

        # If it's a flat sequence of KeyBinding
        if isinstance(km, (list, tuple)):
            flat = [b for b in km if isinstance(b, KeyBinding)]
            # Auto-group into columns of 4 for full help
            chunk_size = 4
            groups = [flat[i : i + chunk_size] for i in range(0, len(flat), chunk_size)] or [flat]
            return flat, groups

        # Fallback: check object attributes for KeyBinding
        attrs = [getattr(km, k) for k in dir(km) if isinstance(getattr(km, k), KeyBinding)]
        groups = [attrs[i : i + 4] for i in range(0, len(attrs), 4)] or [attrs]
        return attrs, groups

    def short_help_view(self, bindings: Sequence[KeyBinding]) -> str:
        """Render single-line compact keybinding help."""
        enabled = [b for b in bindings if b.enabled]
        if not enabled:
            return ""

        rendered_items: list[str] = []
        cur_w = 0
        sep_w = string_width(self.short_separator)

        for b in enabled:
            item_w = string_width(b.help_key) + 1 + string_width(b.help_desc)
            needed = item_w if not rendered_items else item_w + sep_w
            if self.width is not None and cur_w + needed > self.width and rendered_items:
                break

            k_rendered = self.key_style.render(b.help_key)
            d_rendered = self.desc_style.render(b.help_desc)
            rendered_items.append(f"{k_rendered} {d_rendered}")
            cur_w += needed

        sep_rendered = self.sep_style.render(self.short_separator)
        return sep_rendered.join(rendered_items)

    def full_help_view(self, groups: Sequence[Sequence[KeyBinding]]) -> str:
        """Render multi-column full keybinding help."""
        col_blocks: list[str] = []
        valid_groups = [[b for b in col if b.enabled] for col in groups]
        valid_groups = [col for col in valid_groups if col]

        if not valid_groups:
            return ""

        for idx, col in enumerate(valid_groups):
            max_k_w = max(string_width(b.help_key) for b in col)
            lines: list[str] = []
            for b in col:
                pad_key = b.help_key.ljust(max_k_w)
                k_rendered = self.key_style.render(pad_key)
                d_rendered = self.desc_style.render(b.help_desc)
                lines.append(f"{k_rendered}  {d_rendered}")

            col_text = "\n".join(lines)
            if idx < len(valid_groups) - 1:
                # Add gap padding to all rows except last column
                gap_spaces = " " * self.column_gap
                col_text = "\n".join(l + gap_spaces for l in lines)

            col_blocks.append(col_text)

        return join_horizontal(Align.TOP, *col_blocks)

    def view(
        self,
        key_map: KeyMap | Sequence[KeyBinding] | Sequence[Sequence[KeyBinding]] | None = None,
    ) -> str:
        """Render the keybindings based on compact or full mode."""
        short_bindings, full_groups = self._resolve(key_map)
        if self.show_all:
            return self.full_help_view(full_groups)
        return self.short_help_view(short_bindings)
