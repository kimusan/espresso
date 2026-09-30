"""Interactive terminal filesystem browser and file picker component."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


def format_file_size(size_bytes: int) -> str:
    """Format byte count into human-readable size string (e.g., 4.2 KB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ("KB", "MB", "GB", "TB"):
        size_bytes /= 1024.0
        if size_bytes < 1024.0 or unit == "TB":
            return f"{size_bytes:.1f} {unit}"
    return f"{size_bytes:.1f} B"


@dataclass
class FileEntry:
    """Representation of a filesystem directory entry."""

    name: str
    path: Path
    is_dir: bool
    size: int = 0

    @property
    def icon(self) -> str:
        if self.is_dir:
            return "📁"
        return "📄"


@dataclass(frozen=True)
class FileSelectMsg(Msg):
    """Message emitted when a file or directory is selected with Enter."""

    path: Path
    is_dir: bool
    entry: FileEntry | None = None


class FilePicker(Model):
    """An interactive directory browser and file selector.

    Modeled after charmbracelet/bubbles/filepicker.
    """

    def __init__(
        self,
        current_path: Path | str | None = None,
        directory: Path | str | None = None,
        allowed_extensions: Sequence[str] = (),
        show_hidden: bool = False,
        dir_allowed: bool = False,
        file_allowed: bool = True,
        height: int = 12,
        width: int = 50,
    ) -> None:
        target_path = directory or current_path or Path.cwd()
        self.current_path = Path(target_path).resolve()
        self.allowed_extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in allowed_extensions]
        self.show_hidden = show_hidden
        self.dir_allowed = dir_allowed
        self.file_allowed = file_allowed
        self.height = max(5, height)
        self.width = max(30, width)

        self.cursor = 0
        self.scroll_offset = 0
        self.entries: list[FileEntry] = []
        self._refresh_entries()

        # Styles
        self.header_style = Style().bold(True).foreground("#FAFAFA").background("#7D56F4").padding(0, 1)
        self.cursor_style = Style().bold(True).foreground("#00E676")
        self.selected_style = Style().bold(True).foreground("#00E676")
        self.dir_style = Style().bold(True).foreground("#00E5FF")
        self.file_style = Style().foreground("#E0E0E0")
        self.dim_style = Style().faint(True)

    @property
    def current_dir(self) -> Path:
        """Alias for current_path."""
        return self.current_path

    def _refresh_entries(self) -> None:
        """Scan current directory and update entry list."""
        entries: list[FileEntry] = []

        # Parent directory navigation entry
        if self.current_path.parent != self.current_path:
            entries.append(FileEntry(name="..", path=self.current_path.parent, is_dir=True))

        try:
            with os.scandir(self.current_path) as it:
                dir_entries: list[FileEntry] = []
                file_entries: list[FileEntry] = []

                for entry in it:
                    name = entry.name
                    if not self.show_hidden and name.startswith("."):
                        continue

                    try:
                        is_directory = entry.is_dir(follow_symlinks=True)
                    except OSError:
                        is_directory = False

                    if is_directory:
                        dir_entries.append(FileEntry(name=name, path=Path(entry.path), is_dir=True))
                    else:
                        ext = Path(name).suffix.lower()
                        if self.allowed_extensions and ext not in self.allowed_extensions:
                            continue
                        try:
                            size = entry.stat().st_size
                        except OSError:
                            size = 0
                        file_entries.append(FileEntry(name=name, path=Path(entry.path), is_dir=False, size=size))

                # Sort directories first, then files alphabetically
                dir_entries.sort(key=lambda e: e.name.lower())
                file_entries.sort(key=lambda e: e.name.lower())
                entries.extend(dir_entries)
                entries.extend(file_entries)
        except PermissionError:
            pass

        self.entries = entries
        self.cursor = max(0, min(self.cursor, max(0, len(self.entries) - 1)))
        self._sync_scroll()

    def _sync_scroll(self) -> None:
        """Keep the active cursor inside the visible window."""
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.height:
            self.scroll_offset = self.cursor - self.height + 1

    @property
    def selected_entry(self) -> FileEntry | None:
        if 0 <= self.cursor < len(self.entries):
            return self.entries[self.cursor]
        return None

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[FilePicker, Cmd | None]:
        """Handle navigation, directory transitions, and file selection."""
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "down" | "j":
                    if self.cursor < len(self.entries) - 1:
                        self.cursor += 1
                        self._sync_scroll()
                    return self, None
                case "up" | "k":
                    if self.cursor > 0:
                        self.cursor -= 1
                        self._sync_scroll()
                    return self, None
                case "pgdown":
                    self.cursor = min(len(self.entries) - 1, self.cursor + self.height)
                    self._sync_scroll()
                    return self, None
                case "pgup":
                    self.cursor = max(0, self.cursor - self.height)
                    self._sync_scroll()
                    return self, None
                case "backspace" | "left" | "h":
                    # Go up to parent directory
                    if self.current_path.parent != self.current_path:
                        self.current_path = self.current_path.parent
                        self.cursor = 0
                        self.scroll_offset = 0
                        self._refresh_entries()
                    return self, None
                case ".":
                    # Toggle hidden files
                    self.show_hidden = not self.show_hidden
                    self._refresh_entries()
                    return self, None
                case "enter" | "right" | "l":
                    entry = self.selected_entry
                    if entry is not None:
                        if entry.is_dir:
                            self.current_path = entry.path.resolve()
                            self.cursor = 0
                            self.scroll_offset = 0
                            self._refresh_entries()
                            if self.dir_allowed and entry.name != "..":
                                def _emit_dir() -> Msg:
                                    return FileSelectMsg(path=entry.path, is_dir=True, entry=entry)
                                return self, _emit_dir
                            return self, None
                        elif self.file_allowed:
                            def _emit_file() -> Msg:
                                return FileSelectMsg(path=entry.path, is_dir=False, entry=entry)
                            return self, _emit_file

        return self, None

    def view(self) -> str:
        """Render the directory browser view."""
        lines: list[str] = []

        # 1. Path Breadcrumb Header
        trunc_path = truncate_ansi(str(self.current_path), self.width - 4)
        header = f"📂 {trunc_path}"
        lines.append(self.header_style.render(header))
        lines.append("")

        # 2. Entries listing within scroll window
        visible_entries = self.entries[self.scroll_offset : self.scroll_offset + self.height]

        if not self.entries:
            lines.append(self.dim_style.render("  (Empty directory)"))
        else:
            for idx, entry in enumerate(visible_entries):
                actual_idx = self.scroll_offset + idx
                is_selected = (actual_idx == self.cursor)

                cursor = "▶ " if is_selected else "  "
                icon = entry.icon

                if entry.name == "..":
                    name_str = ".."
                    style = self.dir_style
                elif entry.is_dir:
                    name_str = f"{entry.name}/"
                    style = self.dir_style
                else:
                    name_str = entry.name
                    style = self.file_style

                if is_selected:
                    name_str = self.selected_style.render(name_str)
                    cursor = self.cursor_style.render(cursor)
                else:
                    name_str = style.render(name_str)

                avail_w = self.width - 16
                name_trunc = truncate_ansi(name_str, avail_w)

                size_str = ""
                if not entry.is_dir:
                    size_str = self.dim_style.render(f"{format_file_size(entry.size):>9}")
                else:
                    size_str = " " * 9

                lines.append(f"{cursor}{icon} {name_trunc}  {size_str}")

        # Fill empty rows to maintain stable height
        rendered_entries_count = len(visible_entries)
        for _ in range(self.height - rendered_entries_count):
            lines.append("")

        # 3. Footer
        lines.append("")
        hidden_toggle_str = "hide .files" if self.show_hidden else "show .files"
        footer_help = f"↑/↓ nav • enter select/open • backspace up • . {hidden_toggle_str}"
        lines.append(self.dim_style.render(footer_help))

        return "\n".join(lines)
