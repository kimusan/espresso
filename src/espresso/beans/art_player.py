"""Terminal art and animation player supporting .3a and classic .ans formats.

Supports:
- .3a Animated ASCII Art format (modern standard by asciimoth/3a):
  Header metadata, variable per-frame delays, colors, @color-pin, @text-pin,
  and body frame parsing.
- .ans ANSI art and BBS ANSImations:
  IBM-PC Code Page 437 decoding, SAUCE metadata parsing (Title, Author, Group),
  clear-screen frame boundary splitting (\\x1b[2J), and progressive BBS reveals.
- TEA Model integration:
  Tick-based timer playback, frame controls (Play/Pause, Step, Speed, Loop),
  customizable Crema box framing (borders, title, auto-centering), and lifecycle
  messages (AnimationDoneMsg, AnimationLoopMsg).
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence, Union

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg, batch, tick
from espresso.crema.border import ROUNDED_BORDER, Border
from espresso.crema.color import Color, parse_color
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, strip_ansi


# Regular expressions for ANSI sequence scanning
ANSI_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
CURSOR_FORWARD_RE = re.compile(r"\x1b\[([0-9]*)C")
CURSOR_CLEANUP_RE = re.compile(r"\x1b\[[0-9;]*[Ksu]")
FRAME_HOME_RE = re.compile(r"^\x1b\[(?:[0-9;]*)?[Hhf]")


@dataclass
class ArtFrame:
    """A single frame of rendered terminal art."""

    lines: list[str]
    duration_ms: int = 50
    width: int = 0
    height: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.width:
            self.width = max((string_width(l) for l in self.lines), default=0)
        if not self.height:
            self.height = len(self.lines)


@dataclass
class ArtAnimation:
    """A parsed terminal art animation comprising one or more frames."""

    frames: list[ArtFrame] = field(default_factory=list)
    title: str = ""
    author: str = ""
    orig_author: str = ""
    tags: list[str] = field(default_factory=list)
    default_delay_ms: int = 50
    loop: bool = True
    format: str = "custom"  # "3a", "ans", or "custom"

    @property
    def total_frames(self) -> int:
        return len(self.frames)

    @property
    def width(self) -> int:
        return max((f.width for f in self.frames), default=0)

    @property
    def height(self) -> int:
        return max((f.height for f in self.frames), default=0)

    @property
    def total_duration_ms(self) -> int:
        return sum(f.duration_ms for f in self.frames)

    def as_progressive(
        self,
        lines_per_frame: int = 1,
        delay_ms: int = 30,
    ) -> ArtAnimation:
        """Convert a static or single-frame art into a progressive BBS line reveal animation."""
        if not self.frames:
            return self

        base_frame = self.frames[0]
        total_lines = len(base_frame.lines)
        progressive_frames: list[ArtFrame] = []

        step = max(1, lines_per_frame)
        for i in range(step, total_lines + step, step):
            visible_lines = base_frame.lines[: min(i, total_lines)]
            progressive_frames.append(
                ArtFrame(lines=visible_lines, duration_ms=delay_ms)
            )

        return ArtAnimation(
            frames=progressive_frames,
            title=self.title,
            author=self.author,
            orig_author=self.orig_author,
            tags=list(self.tags),
            default_delay_ms=delay_ms,
            loop=False,
            format=self.format,
        )


# --- TEA Messages ---


@dataclass(frozen=True)
class ArtPlayerTickMsg(Msg):
    """Timer message instructing ArtPlayer to advance to the next animation frame."""

    tag: str = "art_player"
    frame_index: int = 0


@dataclass(frozen=True)
class AnimationDoneMsg(Msg):
    """Lifecycle message emitted when a non-looping animation completes playback."""

    tag: str = "art_player"
    title: str = ""


@dataclass(frozen=True)
class AnimationLoopMsg(Msg):
    """Lifecycle message emitted each time a looping animation cycles back to frame 0."""

    tag: str = "art_player"
    loop_count: int = 0


# --- ANSI & Parsing Helpers ---


def _color_to_fg_ansi(val: str) -> str:
    """Convert a .3a color token into an ANSI SGR foreground code."""
    val = val.strip().lower()
    if val in ("_", "none", "default"):
        return "39"
    if val.startswith("#"):
        h = val[1:]
        if len(h) == 3:
            r = int(h[0] * 2, 16)
            g = int(h[1] * 2, 16)
            b = int(h[2] * 2, 16)
            return f"38;2;{r};{g};{b}"
        elif len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return f"38;2;{r};{g};{b}"
        return "39"
    if len(val) == 1:
        if "0" <= val <= "7":
            return str(30 + int(val))
        elif "8" <= val <= "9":
            return str(90 + int(val) - 8)
        elif "a" <= val <= "f":
            return str(90 + ord(val) - ord("a") + 2)
    if val.isdigit():
        num = int(val)
        if 0 <= num <= 255:
            return f"38;5;{num}"
    return "39"


def _color_to_bg_ansi(val: str) -> str:
    """Convert a .3a color token into an ANSI SGR background code."""
    val = val.strip().lower()
    if val in ("_", "none", "default"):
        return "49"
    if val.startswith("#"):
        h = val[1:]
        if len(h) == 3:
            r = int(h[0] * 2, 16)
            g = int(h[1] * 2, 16)
            b = int(h[2] * 2, 16)
            return f"48;2;{r};{g};{b}"
        elif len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return f"48;2;{r};{g};{b}"
        return "49"
    if len(val) == 1:
        if "0" <= val <= "7":
            return str(40 + int(val))
        elif "8" <= val <= "9":
            return str(100 + int(val) - 8)
        elif "a" <= val <= "f":
            return str(100 + ord(val) - ord("a") + 2)
    if val.isdigit():
        num = int(val)
        if 0 <= num <= 255:
            return f"48;5;{num}"
    return "49"


def format_colored_line(
    chars: Sequence[str],
    color_keys: Sequence[str],
    color_map: dict[str, str],
) -> str:
    """Combine text glyphs with a color key mapping into an ANSI formatted string."""
    out: list[str] = []
    current_ansi: str | None = None
    char_len = len(chars)

    for i in range(char_len):
        ch = chars[i]
        key = color_keys[i] if i < len(color_keys) else "_"
        ansi = color_map.get(key, "")

        if ansi != current_ansi:
            out.append(ansi)
            current_ansi = ansi
        out.append(ch)

    if current_ansi:
        out.append("\x1b[0m")
    return "".join(out)


def normalize_ansi_lines(text: str) -> list[str]:
    """Split ANSI text into lines while preserving active styles and preventing border bleed."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    active_sgr = ""

    for line in lines:
        prefix = active_sgr if active_sgr else ""
        for match in ANSI_SGR_RE.finditer(line):
            code = match.group(1)
            full = match.group(0)
            if code in ("", "0"):
                active_sgr = ""
            else:
                active_sgr = full

        suffix = "\x1b[0m" if active_sgr else ""
        out.append(f"{prefix}{line}{suffix}")

    return out


def expand_ansi_cursor_forward(text: str) -> str:
    """Expand ANSI cursor forward commands (\\x1b[<n>C) into spaces for column alignment."""
    def _repl(m: re.Match[str]) -> str:
        count = int(m.group(1)) if m.group(1) else 1
        return " " * count

    return CURSOR_FORWARD_RE.sub(_repl, text)


# --- Parsers ---


def parse_3a(content: str) -> ArtAnimation:
    """Parse a .3a Animated ASCII Art format string into an ArtAnimation.

    Conforms to the 3A specification:
    - @3a header metadata: title, author, orig-author, tags, delay, loop, colors, col.
    - Pinned sections: @color-pin, @text-pin.
    - Multi-frame @body with blank line delimiters.
    """
    raw_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Locate @3a header
    idx = 0
    while idx < len(raw_lines):
        line_clean = raw_lines[idx].strip()
        if line_clean.lower() == "@3a":
            idx += 1
            break
        idx += 1

    title = ""
    author = ""
    orig_author = ""
    tags: list[str] = []
    default_delay_ms = 50
    frame_delays: dict[int, int] = {}
    loop = True
    colors_enabled = False
    custom_colors: dict[str, str] = {}
    color_pin_lines: list[str] = []
    text_pin_lines: list[str] = []

    # Parse @3a header keys
    while idx < len(raw_lines):
        line = raw_lines[idx]
        stripped = line.strip()
        if stripped.lower().startswith("@"):
            break

        if ";;" in line:
            line = line.split(";;", 1)[0]
        line = line.strip()
        idx += 1

        if not line:
            continue

        lower = line.lower()
        if lower.startswith("title:"):
            title = line[6:].strip()
        elif lower.startswith("author:"):
            author = line[7:].strip()
        elif lower.startswith("orig-author:"):
            orig_author = line[12:].strip()
        elif lower.startswith("tags:"):
            tags.extend([t.strip() for t in line[5:].split(",") if t.strip()])
        elif line.startswith("#"):
            tags.extend([t.lstrip("#").strip() for t in line.split() if t.strip()])
        elif lower.startswith("loop:"):
            loop = line[5:].strip().lower() in ("yes", "true", "1")
        elif lower.startswith("colors:"):
            colors_enabled = line[7:].strip().lower() in ("yes", "true", "1")
        elif lower.startswith("delay:"):
            parts = [p.strip() for p in line[6:].split(",") if p.strip()]
            for p_i, part in enumerate(parts):
                if ":" in part:
                    f_str, ms_str = part.split(":", 1)
                    try:
                        frame_delays[int(f_str.strip())] = int(ms_str.strip())
                    except ValueError:
                        pass
                elif p_i == 0 and part.isdigit():
                    default_delay_ms = int(part)
        elif lower.startswith("col "):
            tokens = line[4:].strip().split()
            if tokens:
                char = tokens[0]
                fg_val = None
                bg_val = None
                for token in tokens[1:]:
                    if token.lower().startswith("fg:"):
                        fg_val = token[3:]
                    elif token.lower().startswith("bg:"):
                        bg_val = token[3:]

                codes: list[str] = []
                if fg_val is not None:
                    codes.append(_color_to_fg_ansi(fg_val))
                if bg_val is not None:
                    codes.append(_color_to_bg_ansi(bg_val))

                custom_colors[char] = f"\x1b[{';'.join(codes)}m" if codes else ""
                colors_enabled = True

    # Parse optional pinned sections (@color-pin, @text-pin) and @body
    body_lines: list[str] = []
    while idx < len(raw_lines):
        line = raw_lines[idx]
        stripped = line.strip().lower()

        if stripped == "@color-pin":
            idx += 1
            while idx < len(raw_lines) and not raw_lines[idx].strip().lower().startswith("@"):
                c_line = raw_lines[idx]
                if not c_line.strip().startswith(";;"):
                    color_pin_lines.append(c_line)
                idx += 1
            colors_enabled = True
        elif stripped == "@text-pin":
            idx += 1
            while idx < len(raw_lines) and not raw_lines[idx].strip().lower().startswith("@"):
                t_line = raw_lines[idx]
                if not t_line.strip().startswith(";;"):
                    text_pin_lines.append(t_line)
                idx += 1
            colors_enabled = True
        elif stripped == "@body":
            idx += 1
            body_lines = raw_lines[idx:]
            break
        else:
            # Lines before @body or without explicit @body tag
            if not line.strip().startswith(";;"):
                body_lines.append(line)
            idx += 1

    # Build active color lookup map (defaults + custom col overrides)
    color_map: dict[str, str] = {
        "_": "\x1b[0m",
        " ": "",
    }
    # Built-in 0-7 standard colors
    for i in range(8):
        color_map[str(i)] = f"\x1b[{30 + i}m"
    # Built-in 8-f bright colors
    for i, ch in enumerate("89abcdef"):
        color_map[ch] = f"\x1b[{90 + i}m"
        color_map[ch.upper()] = f"\x1b[{90 + i}m"
    # User-defined colors take precedence
    color_map.update(custom_colors)

    # Chunk body lines into frames separated by blank lines
    raw_frames: list[list[str]] = []
    current_chunk: list[str] = []
    for bline in body_lines:
        if bline.strip().startswith(";;"):
            continue
        if bline.strip() == "":
            if current_chunk:
                raw_frames.append(current_chunk)
                current_chunk = []
        else:
            current_chunk.append(bline)
    if current_chunk:
        raw_frames.append(current_chunk)

    if not raw_frames:
        raw_frames = [[""]]

    # Assemble ArtFrames
    frames: list[ArtFrame] = []
    for f_idx, f_lines in enumerate(raw_frames):
        frame_rendered_lines: list[str] = []

        if color_pin_lines:
            # @color-pin mode: body lines are text, color_pin_lines are colors
            for r, row_text in enumerate(f_lines):
                c_row = color_pin_lines[r] if r < len(color_pin_lines) else ""
                frame_rendered_lines.append(
                    format_colored_line(list(row_text), list(c_row), color_map)
                )

        elif text_pin_lines:
            # @text-pin mode: body lines are colors, text_pin_lines are text
            for r, row_color in enumerate(f_lines):
                t_row = text_pin_lines[r] if r < len(text_pin_lines) else " " * len(row_color)
                frame_rendered_lines.append(
                    format_colored_line(list(t_row), list(row_color), color_map)
                )

        elif colors_enabled:
            # Standard two-column 3A mode: left half is text, right half is color keys
            for row in f_lines:
                w = len(row) // 2
                text_part = row[:w]
                color_part = row[w:]
                frame_rendered_lines.append(
                    format_colored_line(list(text_part), list(color_part), color_map)
                )

        else:
            # Plain monochrome ASCII
            frame_rendered_lines.extend(f_lines)

        dur = frame_delays.get(f_idx, default_delay_ms)
        frames.append(ArtFrame(lines=frame_rendered_lines, duration_ms=dur))

    return ArtAnimation(
        frames=frames,
        title=title,
        author=author,
        orig_author=orig_author,
        tags=tags,
        default_delay_ms=default_delay_ms,
        loop=loop,
        format="3a",
    )


def parse_ans(
    data: bytes | str,
    default_delay_ms: int = 50,
    progressive_lines: bool = False,
    lines_per_frame: int = 1,
) -> ArtAnimation:
    """Parse classic ANSI art (.ans) or BBS ANSImations into an ArtAnimation.

    Decodes IBM-PC Code Page 437, extracts 128-byte SAUCE metadata records,
    splits animations across screen clear sequences (\\x1b[2J), and normalizes
    ANSI escape sequences.
    """
    title = ""
    author = ""
    group = ""
    raw_text = ""

    if isinstance(data, bytes):
        raw_bytes = data
        # Check for 128-byte SAUCE metadata record at end of file
        if len(raw_bytes) >= 128 and raw_bytes[-128:-123] == b"SAUCE":
            sauce_record = raw_bytes[-128:]
            title = sauce_record[7:42].decode("cp437", errors="replace").strip()
            author = sauce_record[42:62].decode("cp437", errors="replace").strip()
            group = sauce_record[62:82].decode("cp437", errors="replace").strip()
            comments_count = sauce_record[104]  # 1 byte at offset -24 from end or 104 in SAUCE

            strip_len = 128
            if comments_count > 0:
                comnt_len = 5 + comments_count * 64
                if len(raw_bytes) >= 128 + comnt_len and raw_bytes[-128 - comnt_len : -128 - comnt_len + 5] == b"COMNT":
                    strip_len += comnt_len

            raw_bytes = raw_bytes[:-strip_len].rstrip(b"\x1a")

        try:
            raw_text = raw_bytes.decode("cp437")
        except UnicodeDecodeError:
            raw_text = raw_bytes.decode("utf-8", errors="replace")
    else:
        raw_text = data

    # Expand cursor movements and strip non-rendering codes
    raw_text = expand_ansi_cursor_forward(raw_text)
    raw_text = CURSOR_CLEANUP_RE.sub("", raw_text)

    # Frame splitting for ANSImations
    raw_frame_texts: list[str] = []
    if "\x1b[2J" in raw_text:
        chunks = raw_text.split("\x1b[2J")
        for chunk in chunks:
            cleaned = FRAME_HOME_RE.sub("", chunk.lstrip("\r\n"))
            if cleaned.strip():
                raw_frame_texts.append(cleaned)
    else:
        # Check for cursor home sequences indicating multi-frame redraws
        home_chunks = re.split(r"\x1b\[(?:1;1|0;0|)[Hhf]", raw_text)
        non_empty = [c for c in home_chunks if c.strip()]
        if len(non_empty) > 1:
            raw_frame_texts = non_empty

    if not raw_frame_texts:
        raw_frame_texts = [raw_text]

    frames: list[ArtFrame] = []
    for chunk in raw_frame_texts:
        lines = normalize_ansi_lines(chunk)
        # Trim excessive trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()
        frames.append(ArtFrame(lines=lines, duration_ms=default_delay_ms))

    anim = ArtAnimation(
        frames=frames,
        title=title,
        author=author,
        orig_author=group,
        default_delay_ms=default_delay_ms,
        loop=len(frames) > 1,
        format="ans",
    )

    if progressive_lines and len(frames) == 1:
        return anim.as_progressive(lines_per_frame=lines_per_frame, delay_ms=default_delay_ms)

    return anim


# --- ArtPlayer Model ---


class ArtPlayer(Model):
    """Interactive TEA component for rendering and playing terminal animations.

    Supports .3a Animated ASCII Art and .ans ANSI art, with playback controls,
    customizable Crema box framing (borders, title, auto-centering), and lifecycle
    messages (AnimationDoneMsg, AnimationLoopMsg).
    """

    def __init__(
        self,
        animation: ArtAnimation | None = None,
        fps: float | None = None,
        speed: float = 1.0,
        auto_play: bool = True,
        loop: bool | None = None,
        tag: str = "art_player",
        border: Border | None = ROUNDED_BORDER,
        border_fg: Union[Color, str, None] = None,
        show_border: bool = True,
        show_controls: bool = False,
        show_title: bool = True,
        title: str | None = None,
        center_horizontally: bool = True,
        center_vertically: bool = False,
        width: int | None = None,
        height: int | None = None,
        interactive: bool = True,
    ) -> None:
        self.animation: ArtAnimation = animation or ArtAnimation(frames=[ArtFrame(lines=[""])])
        self.fps = fps
        self.speed = max(0.05, speed)
        self.auto_play = auto_play
        self.loop = loop if loop is not None else self.animation.loop
        self.tag = tag
        self.border = border
        self.border_fg = border_fg
        self.show_border = show_border
        self.show_controls = show_controls
        self.show_title = show_title
        self.title = title
        self.center_horizontally = center_horizontally
        self.center_vertically = center_vertically
        self.width = width
        self.height = height
        self.interactive = interactive

        self.current_frame_idx: int = 0
        self.is_playing: bool = auto_play and self.total_frames > 1
        self.loop_count: int = 0

    # --- Constructors ---

    @classmethod
    def from_3a(cls, text: str, **kwargs: Any) -> ArtPlayer:
        """Create an ArtPlayer by parsing a .3a Animated ASCII Art string."""
        anim = parse_3a(text)
        return cls(animation=anim, **kwargs)

    @classmethod
    def from_ans(
        cls,
        data: bytes | str,
        default_delay_ms: int = 50,
        progressive_lines: bool = False,
        lines_per_frame: int = 1,
        **kwargs: Any,
    ) -> ArtPlayer:
        """Create an ArtPlayer by parsing an ANSI art (.ans) byte stream or string."""
        anim = parse_ans(
            data,
            default_delay_ms=default_delay_ms,
            progressive_lines=progressive_lines,
            lines_per_frame=lines_per_frame,
        )
        return cls(animation=anim, **kwargs)

    @classmethod
    def from_frames(
        cls,
        frames: Sequence[Union[str, ArtFrame, Sequence[str]]],
        default_delay_ms: int = 50,
        **kwargs: Any,
    ) -> ArtPlayer:
        """Create an ArtPlayer from a sequence of raw multiline strings or ArtFrames."""
        parsed: list[ArtFrame] = []
        for f in frames:
            if isinstance(f, ArtFrame):
                parsed.append(f)
            elif isinstance(f, str):
                lines = f.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                parsed.append(ArtFrame(lines=lines, duration_ms=default_delay_ms))
            elif isinstance(f, Sequence):
                parsed.append(ArtFrame(lines=list(f), duration_ms=default_delay_ms))
        anim = ArtAnimation(frames=parsed, default_delay_ms=default_delay_ms)
        return cls(animation=anim, **kwargs)

    @classmethod
    def from_file(cls, path: Union[str, Path], **kwargs: Any) -> ArtPlayer:
        """Create an ArtPlayer from a .3a or .ans file on disk."""
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".3a":
            text = p.read_text(encoding="utf-8", errors="replace")
            return cls.from_3a(text, **kwargs)
        elif ext in (".ans", ".asc"):
            raw = p.read_bytes()
            return cls.from_ans(raw, **kwargs)
        else:
            raw = p.read_bytes()
            if b"@3a" in raw[:200]:
                return cls.from_3a(raw.decode("utf-8", errors="replace"), **kwargs)
            return cls.from_ans(raw, **kwargs)

    # --- Properties ---

    @property
    def current_frame(self) -> ArtFrame | None:
        """Return the active ArtFrame."""
        if not self.animation.frames:
            return None
        idx = max(0, min(self.current_frame_idx, len(self.animation.frames) - 1))
        return self.animation.frames[idx]

    @property
    def total_frames(self) -> int:
        return len(self.animation.frames)

    @property
    def progress(self) -> float:
        """Return playback completion ratio from 0.0 to 1.0."""
        if self.total_frames <= 1:
            return 1.0
        return self.current_frame_idx / (self.total_frames - 1)

    @property
    def is_finished(self) -> bool:
        """Whether a non-looping animation has reached its final frame and stopped."""
        return (
            not self.loop
            and self.current_frame_idx >= self.total_frames - 1
            and not self.is_playing
        )

    def get_title(self) -> str:
        """Return the display title for the player."""
        if self.title is not None:
            return self.title
        return self.animation.title

    # --- Playback Controls ---

    def _get_frame_duration_seconds(self) -> float:
        """Calculate the duration in seconds for the active frame."""
        if self.fps is not None and self.fps > 0:
            base_s = 1.0 / self.fps
        elif self.current_frame:
            base_s = self.current_frame.duration_ms / 1000.0
        else:
            base_s = self.animation.default_delay_ms / 1000.0

        return max(0.001, base_s / max(0.01, self.speed))

    def _schedule_tick(self) -> Cmd:
        """Create a tea tick command for the next frame."""
        dur_s = self._get_frame_duration_seconds()
        tag = self.tag
        next_idx = self.current_frame_idx + 1
        return tick(dur_s, lambda: ArtPlayerTickMsg(tag=tag, frame_index=next_idx))

    def play(self) -> Cmd | None:
        """Start or resume animation playback."""
        if self.total_frames <= 1:
            return None
        self.is_playing = True
        return self._schedule_tick()

    def pause(self) -> None:
        """Pause animation playback."""
        self.is_playing = False

    def toggle_play(self) -> Cmd | None:
        """Toggle between playing and paused states."""
        if self.is_playing:
            self.pause()
            return None
        return self.play()

    def restart(self) -> Cmd | None:
        """Rewind animation to frame 0 and resume playback."""
        self.current_frame_idx = 0
        self.is_playing = True
        if self.total_frames > 1:
            return self._schedule_tick()
        return None

    def seek(self, index: int) -> None:
        """Jump directly to a specific frame index."""
        if self.total_frames > 0:
            self.current_frame_idx = max(0, min(index, self.total_frames - 1))

    def step_forward(self) -> None:
        """Step one frame forward and pause playback."""
        self.pause()
        if self.total_frames > 0:
            self.current_frame_idx = (self.current_frame_idx + 1) % self.total_frames

    def step_backward(self) -> None:
        """Step one frame backward and pause playback."""
        self.pause()
        if self.total_frames > 0:
            self.current_frame_idx = (self.current_frame_idx - 1 + self.total_frames) % self.total_frames

    def set_speed(self, speed: float) -> None:
        """Update playback speed multiplier (e.g. 1.0, 1.5, 2.0)."""
        self.speed = max(0.1, min(10.0, speed))

    def set_fps(self, fps: float | None) -> None:
        """Override per-frame delays with a fixed frames-per-second rate."""
        self.fps = fps

    def set_loop(self, loop: bool) -> None:
        """Enable or disable looping."""
        self.loop = loop

    def set_border(self, border: Border | None) -> None:
        """Set or remove framing border characters."""
        self.border = border

    def set_border_fg(self, color: Union[Color, str, None]) -> None:
        """Set the border foreground color."""
        self.border_fg = color

    def set_animation(self, animation: ArtAnimation) -> Cmd | None:
        """Swap the current animation with a new one."""
        self.animation = animation
        self.current_frame_idx = 0
        self.loop_count = 0
        if self.auto_play and self.total_frames > 1:
            self.is_playing = True
            return self._schedule_tick()
        self.is_playing = False
        return None

    # --- TEA Lifecycle ---

    def init(self) -> Cmd | None:
        """Emit initial playback tick if auto_play is enabled."""
        if self.auto_play and self.total_frames > 1:
            self.is_playing = True
            return self._schedule_tick()
        return None

    def update(self, msg: Msg) -> tuple[ArtPlayer, Cmd | None]:
        """Handle timer ticks, keyboard controls, and lifecycle events."""
        if isinstance(msg, ArtPlayerTickMsg) and msg.tag == self.tag:
            if not self.is_playing or self.total_frames <= 1:
                return self, None

            next_idx = self.current_frame_idx + 1
            if next_idx >= self.total_frames:
                if self.loop:
                    self.current_frame_idx = 0
                    self.loop_count += 1
                    # Schedule next tick and emit loop message
                    cmd = batch(
                        self._schedule_tick(),
                        lambda: AnimationLoopMsg(tag=self.tag, loop_count=self.loop_count),
                    )
                    return self, cmd
                else:
                    self.current_frame_idx = self.total_frames - 1
                    self.is_playing = False
                    return self, lambda: AnimationDoneMsg(tag=self.tag, title=self.get_title())
            else:
                self.current_frame_idx = next_idx
                return self, self._schedule_tick()

        if self.interactive and isinstance(msg, KeyMsg):
            match msg.key:
                case " " | "k":
                    return self, self.toggle_play()
                case "r" | "R":
                    return self, self.restart()
                case "right" | "l":
                    self.step_forward()
                    return self, None
                case "left" | "h":
                    self.step_backward()
                    return self, None
                case "]" | "+" | "=":
                    self.set_speed(self.speed + 0.25)
                    return self, None
                case "[" | "-":
                    self.set_speed(self.speed - 0.25)
                    return self, None

        return self, None

    # --- Rendering ---

    def view(self) -> str:
        """Render the active animation frame inside an optional styled border box."""
        frame = self.current_frame
        lines = list(frame.lines) if frame else [""]

        # Determine target content width
        content_w = self.width or self.animation.width or max((string_width(l) for l in lines), default=0)

        # Center lines horizontally if enabled
        if self.center_horizontally and content_w > 0:
            centered_lines: list[str] = []
            for line in lines:
                lw = string_width(line)
                pad = max(0, (content_w - lw) // 2)
                rpad = max(0, content_w - lw - pad)
                centered_lines.append(f"{' ' * pad}{line}{' ' * rpad}")
            lines = centered_lines

        # Center lines vertically if height is specified
        if self.center_vertically and self.height is not None and self.height > len(lines):
            diff = self.height - len(lines)
            top_pad = diff // 2
            bot_pad = diff - top_pad
            empty_row = " " * max(content_w, 1)
            lines = ([empty_row] * top_pad) + lines + ([empty_row] * bot_pad)

        # Add optional playback controls bar
        if self.show_controls:
            icon = "▶" if self.is_playing else "⏸"
            idx_str = f"[{self.current_frame_idx + 1}/{max(1, self.total_frames)}]"
            speed_str = f"[{self.speed:.2f}x]"
            hints = "[Space] Play/Pause  [R] Restart  [←/→] Step"
            ctrl_text = f"{icon} {idx_str}  {hints}  {speed_str}"
            ctrl_line = f"\x1b[2m{ctrl_text}\x1b[0m"

            sep_w = max(content_w, string_width(ctrl_text))
            sep = f"\x1b[2m{'─' * sep_w}\x1b[0m"
            lines.append(sep)
            lines.append(ctrl_line)

        body = "\n".join(lines)

        # Apply Crema border framing if configured
        if self.show_border and self.border is not None:
            style = Style().border(self.border)
            if self.border_fg:
                style = style.border_foreground(self.border_fg)

            title_text = self.get_title()
            if self.show_title and title_text:
                style = style.border_title(f" {title_text} ", align=Align.LEFT)

            return style.render(body)

        return body
