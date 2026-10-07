"""TextArea component for interactive multi-line text editing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from espresso.core.keys import Key, KeyMsg
from espresso.core.mouse import MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import char_width, string_width


@dataclass
class _VisualRow:
    logical_row: int
    seg_idx: int
    is_first_segment: bool
    is_last_segment: bool
    start_col: int
    end_col: int
    text: str


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
        word_wrap: bool = False,
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
        self.word_wrap = word_wrap
        self.focused: bool = True

        self.style = style or Style().foreground("#FAFAFA")
        self.line_number_style = line_number_style or Style().foreground("#555555")
        self.cursor_line_number_style = cursor_line_number_style or Style().bold(True).foreground("#7D56F4")
        self.placeholder_style = placeholder_style or Style().foreground("#666666")

    def init(self) -> Cmd | None:
        """Initialize component lifecycle (no-op for TextArea)."""
        return None

    def focus(self) -> None:
        """Enable keyboard focus and show the cursor."""
        self.focused = True

    def blur(self) -> None:
        """Remove keyboard focus and hide the cursor."""
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

    @cursor.setter
    def cursor(self, pos: tuple[int, int]) -> None:
        self.set_cursor(pos[0], pos[1])

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

    def _get_content_width(self) -> int | None:
        """Calculate available text content width inside the textarea."""
        if self.width is None:
            return None
        total_lines = len(self.lines)
        gutter_w = max(2, len(str(total_lines)))
        sep = " │ "
        gutter_total_w = gutter_w + len(sep) if self.show_line_numbers else 0
        return max(1, self.width - gutter_total_w)

    def _get_visual_rows(self, content_w: int) -> list[_VisualRow]:
        """Split logical lines into wrapped visual rows for display without adding newlines."""
        vis_rows: list[_VisualRow] = []
        for r_idx, line in enumerate(self.lines):
            if not line:
                vis_rows.append(
                    _VisualRow(
                        logical_row=r_idx,
                        seg_idx=0,
                        is_first_segment=True,
                        is_last_segment=True,
                        start_col=0,
                        end_col=0,
                        text="",
                    )
                )
                continue

            segs = self._get_visual_segments(line, content_w)
            for seg_idx, (s, e, t) in enumerate(segs):
                vis_rows.append(
                    _VisualRow(
                        logical_row=r_idx,
                        seg_idx=seg_idx,
                        is_first_segment=(seg_idx == 0),
                        is_last_segment=(seg_idx == len(segs) - 1),
                        start_col=s,
                        end_col=e,
                        text=t,
                    )
                )
        return vis_rows

    def _get_visual_segments(self, line: str, max_w: int) -> list[tuple[int, int, str]]:
        """Wrap a single string into (start_col, end_col, text) slices based on cell width."""
        if not line:
            return [(0, 0, "")]
        if string_width(line) <= max_w:
            return [(0, len(line), line)]

        segs: list[tuple[int, int, str]] = []
        cur = 0
        n = len(line)
        while cur < n:
            fit_len = 0
            w = 0
            while cur + fit_len < n:
                ch_w = char_width(line[cur + fit_len])
                if w + ch_w > max_w and fit_len > 0:
                    break
                w += ch_w
                fit_len += 1

            if cur + fit_len >= n:
                segs.append((cur, n, line[cur:]))
                break

            chunk = line[cur : cur + fit_len]
            last_space = chunk.rfind(" ")
            if last_space != -1 and last_space > 0:
                break_len = last_space + 1
            else:
                break_len = max(1, fit_len)

            end = cur + break_len
            segs.append((cur, end, line[cur:end]))
            cur = end

        return segs

    def _find_cursor_visual_pos(self, vis_rows: list[_VisualRow]) -> tuple[int, int]:
        """Find the visual row index and visual column for (self.cursor_row, self.cursor_col)."""
        target_v_row = 0
        target_v_col = 0
        found = False

        for v_idx, v in enumerate(vis_rows):
            if v.logical_row == self.cursor_row:
                if v.start_col <= self.cursor_col < v.end_col:
                    target_v_row = v_idx
                    target_v_col = self.cursor_col - v.start_col
                    found = True
                    break
                elif self.cursor_col == v.end_col:
                    if v.is_last_segment:
                        target_v_row = v_idx
                        target_v_col = v.end_col - v.start_col
                        found = True
                        break

        if not found:
            for v_idx in reversed(range(len(vis_rows))):
                if vis_rows[v_idx].logical_row == self.cursor_row:
                    target_v_row = v_idx
                    target_v_col = max(0, self.cursor_col - vis_rows[v_idx].start_col)
                    break

        return target_v_row, target_v_col

    def _adjust_scroll(self) -> None:
        """Keep the cursor within the visible viewport bounds."""
        self.cursor_row = max(0, min(self.cursor_row, len(self.lines) - 1))
        self.cursor_col = max(0, min(self.cursor_col, len(self.lines[self.cursor_row])))

        content_w = self._get_content_width()

        if self.word_wrap and content_w is not None:
            self.col_offset = 0
            vis_rows = self._get_visual_rows(content_w)
            v_row_idx, _ = self._find_cursor_visual_pos(vis_rows)
            if self.height is not None:
                if v_row_idx < self.row_offset:
                    self.row_offset = v_row_idx
                elif v_row_idx >= self.row_offset + self.height:
                    self.row_offset = v_row_idx - self.height + 1
                max_offset = max(0, len(vis_rows) - self.height)
                self.row_offset = max(0, min(self.row_offset, max_offset))
            else:
                self.row_offset = 0
            return

        # Default unwrapped vertical scrolling
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
        if content_w is not None:
            if self.cursor_col < self.col_offset:
                self.col_offset = self.cursor_col
            elif self.cursor_col >= self.col_offset + content_w:
                self.col_offset = self.cursor_col - content_w + 1
            self.col_offset = max(0, self.col_offset)
        else:
            self.col_offset = 0

    def update(self, msg: Msg) -> tuple[TextArea, Cmd | None]:
        """Process keyboard navigation, character edits, tab indentation, and scroll wheel."""
        if not self.focused:
            return self, None

        content_w = self._get_content_width()

        match msg:
            case KeyMsg(key="up"):
                if self.word_wrap and content_w is not None:
                    vis_rows = self._get_visual_rows(content_w)
                    v_row, v_col = self._find_cursor_visual_pos(vis_rows)
                    if v_row > 0:
                        prev_v = vis_rows[v_row - 1]
                        self.cursor_row = prev_v.logical_row
                        self.cursor_col = min(prev_v.end_col, prev_v.start_col + v_col)
                        self._adjust_scroll()
                    return self, None

                if self.cursor_row > 0:
                    self.cursor_row -= 1
                    self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
                    self._adjust_scroll()
                return self, None

            case KeyMsg(key="down"):
                if self.word_wrap and content_w is not None:
                    vis_rows = self._get_visual_rows(content_w)
                    v_row, v_col = self._find_cursor_visual_pos(vis_rows)
                    if v_row < len(vis_rows) - 1:
                        next_v = vis_rows[v_row + 1]
                        self.cursor_row = next_v.logical_row
                        self.cursor_col = min(next_v.end_col, next_v.start_col + v_col)
                        self._adjust_scroll()
                    return self, None

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
                if self.word_wrap and content_w is not None:
                    vis_rows = self._get_visual_rows(content_w)
                    v_row, _ = self._find_cursor_visual_pos(vis_rows)
                    self.cursor_col = vis_rows[v_row].start_col
                    self._adjust_scroll()
                    return self, None
                self.cursor_col = 0
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="end" | "ctrl+e"):
                if self.word_wrap and content_w is not None:
                    vis_rows = self._get_visual_rows(content_w)
                    v_row, _ = self._find_cursor_visual_pos(vis_rows)
                    v = vis_rows[v_row]
                    self.cursor_col = v.end_col if v.is_last_segment else max(v.start_col, v.end_col - 1)
                    self._adjust_scroll()
                    return self, None
                self.cursor_col = len(self.lines[self.cursor_row])
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="pageup"):
                jump = self.height if self.height is not None else 10
                if self.word_wrap and content_w is not None:
                    vis_rows = self._get_visual_rows(content_w)
                    v_row, v_col = self._find_cursor_visual_pos(vis_rows)
                    target_v_row = max(0, v_row - jump)
                    target = vis_rows[target_v_row]
                    self.cursor_row = target.logical_row
                    self.cursor_col = min(target.end_col, target.start_col + v_col)
                    self._adjust_scroll()
                    return self, None

                self.cursor_row = max(0, self.cursor_row - jump)
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
                self._adjust_scroll()
                return self, None

            case KeyMsg(key="pagedown"):
                jump = self.height if self.height is not None else 10
                if self.word_wrap and content_w is not None:
                    vis_rows = self._get_visual_rows(content_w)
                    v_row, v_col = self._find_cursor_visual_pos(vis_rows)
                    target_v_row = min(len(vis_rows) - 1, v_row + jump)
                    target = vis_rows[target_v_row]
                    self.cursor_row = target.logical_row
                    self.cursor_col = min(target.end_col, target.start_col + v_col)
                    self._adjust_scroll()
                    return self, None

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
                    if self.word_wrap and content_w is not None:
                        total_rows = len(self._get_visual_rows(content_w))
                    else:
                        total_rows = len(self.lines)
                    max_offset = max(0, total_rows - self.height)
                    if self.row_offset < max_offset:
                        self.row_offset += 1
                return self, None

            case KeyMsg(key=k) if k.char is not None and not (k.ctrl or k.alt):
                self.insert_text(k.char)
                return self, None

        return self, None

    def view(self) -> str:
        """Render visible text lines, line number gutter, and cursor within the viewport."""
        if self.width is not None and self.width <= 0:
            return ""
        if self.height is not None and self.height <= 0:
            return ""

        total_lines = len(self.lines)
        gutter_w = max(2, len(str(total_lines)))
        sep = " │ "
        gutter_total_w = gutter_w + len(sep) if self.show_line_numbers else 0
        content_w = self._get_content_width()

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

                line_str = line_rendered
                if self.width is not None:
                    diff = self.width - string_width(line_str)
                    if diff > 0:
                        line_str = f"{line_str}{' ' * diff}"
                output.append(line_str)

            if self.height is not None:
                pad_w = self.width if self.width is not None else (gutter_total_w if self.show_line_numbers else 0)
                while len(output) < self.height:
                    output.append(" " * pad_w)

            return "\n".join(output)

        # Word-wrapped rendering
        if self.word_wrap and content_w is not None:
            vis_rows = self._get_visual_rows(content_w)
            v_cursor_idx, v_cursor_col = self._find_cursor_visual_pos(vis_rows)

            if self.height is not None:
                end_idx = min(len(vis_rows), self.row_offset + self.height)
                visible_rows = vis_rows[self.row_offset : end_idx]
            else:
                visible_rows = vis_rows

            output_lines: list[str] = []
            for v_idx_rel, v in enumerate(visible_rows):
                actual_v_idx = self.row_offset + v_idx_rel
                num_prefix = ""
                if self.show_line_numbers:
                    if v.is_first_segment:
                        num_str = f"{v.logical_row + 1:>{gutter_w}}{sep}"
                        num_prefix = (
                            self.cursor_line_number_style.render(num_str)
                            if self.focused and v.logical_row == self.cursor_row
                            else self.line_number_style.render(num_str)
                        )
                    else:
                        num_str = f"{' ':>{gutter_w}}{sep}"
                        num_prefix = self.line_number_style.render(num_str)

                text = v.text
                if self.focused and actual_v_idx == v_cursor_idx:
                    c_col = v_cursor_col
                    left = text[:c_col]
                    c_char = text[c_col] if c_col < len(text) else " "
                    right = text[c_col + 1 :] if c_col < len(text) else ""
                    c_rendered = f"\033[7m{c_char}\033[0m"
                    text_rendered = f"{self.style.render(left)}{c_rendered}{self.style.render(right)}"
                else:
                    text_rendered = self.style.render(text)

                line_str = f"{num_prefix}{text_rendered}"
                if self.width is not None:
                    diff = self.width - string_width(line_str)
                    if diff > 0:
                        line_str = f"{line_str}{' ' * diff}"
                output_lines.append(line_str)

            if self.height is not None:
                pad_w = self.width if self.width is not None else (gutter_total_w if self.show_line_numbers else 0)
                while len(output_lines) < self.height:
                    output_lines.append(" " * pad_w)

            return "\n".join(output_lines)

        # Standard non-wrapped row rendering
        if self.height is not None:
            end_row = min(total_lines, self.row_offset + self.height)
            visible_indices = range(self.row_offset, end_row)
        else:
            visible_indices = range(0, total_lines)

        output_lines = []
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

            line_str = f"{num_prefix}{text_rendered}"
            if self.width is not None:
                diff = self.width - string_width(line_str)
                if diff > 0:
                    line_str = f"{line_str}{' ' * diff}"
            output_lines.append(line_str)

        if self.height is not None:
            pad_w = self.width if self.width is not None else (gutter_total_w if self.show_line_numbers else 0)
            while len(output_lines) < self.height:
                output_lines.append(" " * pad_w)

        return "\n".join(output_lines)
