"""TextArea component for interactive multi-line text editing."""

from __future__ import annotations

from typing import Sequence

from espresso.core.keys import Key, KeyMsg
from espresso.core.mouse import MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width


class TextArea(Model):
    """Multi-line text editor supporting navigation, editing, scrolling, and line numbers."""

    def __init__(
        self,
        placeholder: str = "",
        width: int | None = None,
        height: int | None = None,
        show_line_numbers: bool = True,
        tab_size: int = 4,
        char_limit: int | None = None,
        max_lines: int | None = None,
        style: Style | None = None,
        line_number_style: Style | None = None,
        cursor_line_number_style: Style | None = None,
        placeholder_style: Style | None = None,
    ) -> None:
        self.lines: list[str] = [""]
        self.cursor_row: int = 0
        self.cursor_col: int = 0
        self.row_offset: int = 0
        self.col_offset: int = 0

        self.placeholder = placeholder
        self.width = width
        self.height = height
        self.show_line_numbers = show_line_numbers
        self.tab_size = tab_size
        self.char_limit = char_limit
        self.max_lines = max_lines
        self.focused: bool = True

        self.style = style or Style().foreground("#FAFAFA")
        self.line_number_style = line_number_style or Style().foreground("#555555")
        self.cursor_line_number_style = cursor_line_number_style or Style().bold(True).foreground("#7D56F4")
        self.placeholder_style = placeholder_style or Style().foreground("#666666")

    def init(self) -> Cmd | None:
        return None

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False

    @property
    def value(self) -> str:
        """Get the full text content as a single string."""
        return "\n".join(self.lines)

    @value.setter
    def value(self, val: str) -> None:
        self.set_value(val)

    def set_value(self, val: str) -> None:
        """Set the text content and position the cursor at the end."""
        if not val:
            self.lines = [""]
        else:
            normalized = val.replace("\r\n", "\n").replace("\r", "\n")
            self.lines = normalized.split("\n")
            if self.max_lines is not None:
                self.lines = self.lines[: self.max_lines]

        self.cursor_row = len(self.lines) - 1
        self.cursor_col = len(self.lines[-1])
        self._adjust_scroll()

    @property
    def line_count(self) -> int:
        """Return the number of lines."""
        return len(self.lines)

    @property
    def cursor(self) -> tuple[int, int]:
        """Return the cursor position as (row, col)."""
        return self.cursor_row, self.cursor_col

    def set_cursor(self, row: int, col: int) -> None:
        """Set cursor position with clamping."""
        self.cursor_row = max(0, min(row, len(self.lines) - 1))
        self.cursor_col = max(0, min(col, len(self.lines[self.cursor_row])))
        self._adjust_scroll()

    def toggle_line_numbers(self) -> None:
        """Toggle line numbering display."""
        self.show_line_numbers = not self.show_line_numbers

    def clear(self) -> None:
        """Clear all content and reset cursor."""
        self.lines = [""]
        self.cursor_row = 0
        self.cursor_col = 0
        self.row_offset = 0
        self.col_offset = 0

    def insert_text(self, text: str) -> None:
        """Insert text at the current cursor position."""
        if not text:
            return

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        insert_lines = normalized.split("\n")

        # Check char limit if set
        if self.char_limit is not None:
            current_len = sum(len(l) for l in self.lines) + len(self.lines) - 1
            if current_len >= self.char_limit:
                return
            allowed = self.char_limit - current_len
            if len(normalized) > allowed:
                normalized = normalized[:allowed]
                insert_lines = normalized.split("\n")

        cur_line = self.lines[self.cursor_row]
        left = cur_line[: self.cursor_col]
        right = cur_line[self.cursor_col :]

        if len(insert_lines) == 1:
            self.lines[self.cursor_row] = left + insert_lines[0] + right
            self.cursor_col += len(insert_lines[0])
        else:
            # Check max lines constraint
            if self.max_lines is not None:
                available_lines = self.max_lines - len(self.lines)
                if available_lines < len(insert_lines) - 1:
                    insert_lines = insert_lines[: available_lines + 1]

            first = left + insert_lines[0]
            last = insert_lines[-1] + right
            middle = insert_lines[1:-1]

            new_lines = [first] + middle + [last]
            self.lines[self.cursor_row : self.cursor_row + 1] = new_lines
            self.cursor_row += len(insert_lines) - 1
            self.cursor_col = len(insert_lines[-1])

        self._adjust_scroll()

    def _adjust_scroll(self) -> None:
        """Keep the cursor within the visible viewport bounds."""
        self.cursor_row = max(0, min(self.cursor_row, len(self.lines) - 1))
        self.cursor_col = max(0, min(self.cursor_col, len(self.lines[self.cursor_row])))

        # Vertical scrolling
        if self.height is not None:
            if self.cursor_row < self.row_offset:
                self.row_offset = self.cursor_row
            elif self.cursor_row >= self.row_offset + self.height:
                self.row_offset = self.cursor_row - self.height + 1
            max_row_offset = max(0, len(self.lines) - self.height)
            self.row_offset = max(0, min(self.row_offset, max_row_offset))
        else:
            self.row_offset = 0

        # Horizontal scrolling
        if self.width is not None:
            gutter_w = 0
            if self.show_line_numbers:
                gutter_w = max(2, len(str(len(self.lines)))) + 3  # " N │ "
            content_w = max(1, self.width - gutter_w)
            if self.cursor_col < self.col_offset:
                self.col_offset = self.cursor_col
            elif self.cursor_col >= self.col_offset + content_w:
                self.col_offset = self.cursor_col - content_w + 1
            self.col_offset = max(0, self.col_offset)
        else:
            self.col_offset = 0

    def update(self, msg: Msg) -> tuple[TextArea, Cmd | None]:
        if not self.focused:
            return self, None

        match msg:
            case KeyMsg(key="up"):
                if self.cursor_row > 0:
                    self.cursor_row -= 1
                    self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="down"):
                if self.cursor_row < len(self.lines) - 1:
                    self.cursor_row += 1
                    self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="left"):
                if self.cursor_col > 0:
                    self.cursor_col -= 1
                    self._adjust_scroll()
                elif self.cursor_row > 0:
                    self.cursor_row -= 1
                    self.cursor_col = len(self.lines[self.cursor_row])
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="right"):
                if self.cursor_col < len(self.lines[self.cursor_row]):
                    self.cursor_col += 1
                    self._adjust_scroll()
                elif self.cursor_row < len(self.lines) - 1:
                    self.cursor_row += 1
                    self.cursor_col = 0
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="home" | "ctrl+a"):
                self.cursor_col = 0
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="end" | "ctrl+e"):
                self.cursor_col = len(self.lines[self.cursor_row])
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="pageup"):
                jump = self.height if self.height is not None else 10
                self.cursor_row = max(0, self.cursor_row - jump)
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="pagedown"):
                jump = self.height if self.height is not None else 10
                self.cursor_row = min(len(self.lines) - 1, self.cursor_row + jump)
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="enter"):
                if self.max_lines is not None and len(self.lines) >= self.max_lines:
                    return self, None

                cur = self.lines[self.cursor_row]
                left = cur[: self.cursor_col]
                right = cur[self.cursor_col :]

                self.lines[self.cursor_row] = left
                self.lines.insert(self.cursor_row + 1, right)
                self.cursor_row += 1
                self.cursor_col = 0
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="backspace"):
                if self.cursor_col > 0:
                    cur = self.lines[self.cursor_row]
                    self.lines[self.cursor_row] = cur[: self.cursor_col - 1] + cur[self.cursor_col :]
                    self.cursor_col -= 1
                    self._adjust_scroll()
                elif self.cursor_row > 0:
                    prev = self.lines[self.cursor_row - 1]
                    prev_len = len(prev)
                    self.lines[self.cursor_row - 1] = prev + self.lines[self.cursor_row]
                    del self.lines[self.cursor_row]
                    self.cursor_row -= 1
                    self.cursor_col = prev_len
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="delete"):
                cur = self.lines[self.cursor_row]
                if self.cursor_col < len(cur):
                    self.lines[self.cursor_row] = cur[: self.cursor_col] + cur[self.cursor_col + 1 :]
                    self._adjust_scroll()
                elif self.cursor_row < len(self.lines) - 1:
                    self.lines[self.cursor_row] = cur + self.lines[self.cursor_row + 1]
                    del self.lines[self.cursor_row + 1]
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="tab"):
                self.insert_text(" " * self.tab_size)
                return self, None

            case MouseMsg(button=MouseButton.WHEEL_UP):
                if self.row_offset > 0:
                    self.row_offset -= 1
                return self, None

            case MouseMsg(button=MouseButton.WHEEL_DOWN):
                if self.height is not None:
                    max_offset = max(0, len(self.lines) - self.height)
                    if self.row_offset < max_offset:
                        self.row_offset += 1
                return self, None

            case KeyMsg(key=k) if k.char is not None and not (k.ctrl or k.alt):
                self.insert_text(k.char)
                return self, None

        return self, None

    def view(self) -> str:
        total_lines = len(self.lines)
        gutter_w = max(2, len(str(total_lines)))
        sep = " │ "
        gutter_total_w = gutter_w + len(sep) if self.show_line_numbers else 0

        content_w: int | None = None
        if self.width is not None:
            content_w = max(1, self.width - gutter_total_w)

        # Empty content with placeholder
        if self.value == "" and self.placeholder:
            placeholder_lines = self.placeholder.splitlines() or [""]
            output: list[str] = []
            for i, p_line in enumerate(placeholder_lines):
                if self.height is not None and i >= self.height:
                    break

                num_prefix = ""
                if self.show_line_numbers:
                    num_str = f"{i + 1:>{gutter_w}}{sep}"
                    num_prefix = (
                        self.cursor_line_number_style.render(num_str)
                        if self.focused and i == 0
                        else self.line_number_style.render(num_str)
                    )

                if self.focused and i == 0:
                    c_char = p_line[0] if p_line else " "
                    rest = p_line[1:] if len(p_line) > 1 else ""
                    c_rendered = f"\033[7m{c_char}\033[0m"
                    line_rendered = f"{num_prefix}{c_rendered}{self.placeholder_style.render(rest)}"
                else:
                    line_rendered = f"{num_prefix}{self.placeholder_style.render(p_line)}"

                output.append(line_rendered)

            if self.height is not None:
                while len(output) < self.height:
                    output.append(" " * gutter_total_w if self.show_line_numbers else "")

            return "\n".join(output)

        # Render visible rows
        if self.height is not None:
            end_row = min(total_lines, self.row_offset + self.height)
            visible_indices = range(self.row_offset, end_row)
        else:
            visible_indices = range(0, total_lines)

        output_lines: list[str] = []
        for r in visible_indices:
            line = self.lines[r]

            # Line number gutter
            num_prefix = ""
            if self.show_line_numbers:
                num_str = f"{r + 1:>{gutter_w}}{sep}"
                if self.focused and r == self.cursor_row:
                    num_prefix = self.cursor_line_number_style.render(num_str)
                else:
                    num_prefix = self.line_number_style.render(num_str)

            # Horizontal slice of text
            if content_w is not None:
                visible_text = line[self.col_offset : self.col_offset + content_w]
            else:
                visible_text = line[self.col_offset :]

            if self.focused and r == self.cursor_row:
                rel_c = self.cursor_col - self.col_offset
                if 0 <= rel_c <= len(visible_text):
                    left = visible_text[:rel_c]
                    c_char = visible_text[rel_c] if rel_c < len(visible_text) else " "
                    right = visible_text[rel_c + 1 :] if rel_c < len(visible_text) else ""
                    c_rendered = f"\033[7m{c_char}\033[0m"
                    text_rendered = f"{self.style.render(left)}{c_rendered}{self.style.render(right)}"
                else:
                    text_rendered = self.style.render(visible_text)
            else:
                text_rendered = self.style.render(visible_text)

            output_lines.append(f"{num_prefix}{text_rendered}")

        if self.height is not None:
            while len(output_lines) < self.height:
                output_lines.append(" " * gutter_total_w if self.show_line_numbers else "")

        return "\n".join(output_lines)
