"""Keyboard and input event representation and ANSI escape sequence parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from espresso.core.tea import Msg


@dataclass(frozen=True)
class Key:
    """Represents a pressed key with modifiers and printable character."""

    name: str  # e.g., "a", "enter", "up", "ctrl+c", "esc", "backspace"
    char: str | None = None  # None for special non-printable keys
    alt: bool = False
    ctrl: bool = False
    shift: bool = False

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other or (self.char is not None and self.char == other)
        if isinstance(other, Key):
            return self.name == other.name
        return False


@dataclass(frozen=True)
class KeyMsg(Msg):
    """Message emitted whenever a keyboard key is pressed."""

    key: Key

    def __init__(self, key: Key | str, char: str | None = None, alt: bool = False, ctrl: bool = False, shift: bool = False) -> None:
        if isinstance(key, str):
            if char is None and len(key) == 1 and not (alt or ctrl):
                char = key
            object.__setattr__(self, "key", Key(name=key, char=char, alt=alt, ctrl=ctrl, shift=shift))
        else:
            object.__setattr__(self, "key", key)

    def __str__(self) -> str:
        return str(self.key)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return str(self.key) == other or (self.key.char is not None and self.key.char == other)
        if isinstance(other, Key):
            return self.key == other
        if isinstance(other, KeyMsg):
            return self.key == other.key
        return False


# Map common single control characters (0-31) to names
CTRL_KEY_MAP: dict[int, str] = {
    0: "ctrl+@",
    1: "ctrl+a",
    2: "ctrl+b",
    3: "ctrl+c",
    4: "ctrl+d",
    5: "ctrl+e",
    6: "ctrl+f",
    7: "ctrl+g",
    8: "ctrl+h",
    9: "tab",
    10: "enter",  # Line Feed \n
    11: "ctrl+k",
    12: "ctrl+l",
    13: "enter",  # Carriage Return \r
    14: "ctrl+n",
    15: "ctrl+o",
    16: "ctrl+p",
    17: "ctrl+q",
    18: "ctrl+r",
    19: "ctrl+s",
    20: "ctrl+t",
    21: "ctrl+u",
    22: "ctrl+v",
    23: "ctrl+w",
    24: "ctrl+x",
    25: "ctrl+y",
    26: "ctrl+z",
    27: "esc",
    127: "backspace",  # ASCII DEL (\x7f)
}

# Standard ANSI escape sequences mapped to friendly names
ANSI_KEY_MAP: dict[str, Key] = {
    # Arrow keys
    "\x1b[A": Key("up"),
    "\x1b[B": Key("down"),
    "\x1b[C": Key("right"),
    "\x1b[D": Key("left"),
    "\x1bOA": Key("up"),
    "\x1bOB": Key("down"),
    "\x1bOC": Key("right"),
    "\x1bOD": Key("left"),
    # Modified arrows
    "\x1b[1;2A": Key("shift+up", shift=True),
    "\x1b[1;2B": Key("shift+down", shift=True),
    "\x1b[1;2C": Key("shift+right", shift=True),
    "\x1b[1;2D": Key("shift+left", shift=True),
    "\x1b[1;5A": Key("ctrl+up", ctrl=True),
    "\x1b[1;5B": Key("ctrl+down", ctrl=True),
    "\x1b[1;5C": Key("ctrl+right", ctrl=True),
    "\x1b[1;5D": Key("ctrl+left", ctrl=True),
    # Navigation
    "\x1b[H": Key("home"),
    "\x1b[F": Key("end"),
    "\x1b[1~": Key("home"),
    "\x1b[4~": Key("end"),
    "\x1b[7~": Key("home"),
    "\x1b[8~": Key("end"),
    "\x1b[2~": Key("insert"),
    "\x1b[3~": Key("delete"),
    "\x1b[5~": Key("pageup"),
    "\x1b[6~": Key("pagedown"),
    "\x1b[Z": Key("shift+tab", shift=True),
    # Function keys F1-F4 (SS3 mode)
    "\x1bOP": Key("f1"),
    "\x1bOQ": Key("f2"),
    "\x1bOR": Key("f3"),
    "\x1bOS": Key("f4"),
    # Function keys F1-F12 (CSI mode)
    "\x1b[11~": Key("f1"),
    "\x1b[12~": Key("f2"),
    "\x1b[13~": Key("f3"),
    "\x1b[14~": Key("f4"),
    "\x1b[15~": Key("f5"),
    "\x1b[17~": Key("f6"),
    "\x1b[18~": Key("f7"),
    "\x1b[19~": Key("f8"),
    "\x1b[20~": Key("f9"),
    "\x1b[21~": Key("f10"),
    "\x1b[23~": Key("f11"),
    "\x1b[24~": Key("f12"),
}


def parse_keys(raw: str) -> Iterator[KeyMsg]:
    """Parse a stream of raw terminal characters into KeyMsg instances."""
    i = 0
    n = len(raw)
    while i < n:
        char = raw[i]

        # Check for escape sequence
        if char == "\x1b":
            # If escape is the last character or next isn't [ or O
            if i + 1 >= n:
                yield KeyMsg(Key("esc"))
                i += 1
                continue

            # Alt + key combination (e.g. \x1ba -> alt+a)
            if raw[i + 1] not in ("[", "O"):
                next_ch = raw[i + 1]
                yield KeyMsg(Key(name=f"alt+{next_ch}", char=next_ch, alt=True))
                i += 2
                continue

            # Check for SGR 1006 mouse event: \x1b[<...
            if raw[i : i + 3] == "\x1b[<":
                from espresso.core.mouse import parse_sgr_mouse

                mouse_msg, consumed = parse_sgr_mouse(raw[i:])
                if mouse_msg is not None:
                    yield mouse_msg
                    i += consumed
                    continue

            # Try longest matching ANSI sequence
            matched = False
            # Check substrings from longest possible (up to 8 chars) down to 2 chars
            max_len = min(n - i, 8)
            for length in range(max_len, 1, -1):
                seq = raw[i : i + length]
                if seq in ANSI_KEY_MAP:
                    yield KeyMsg(ANSI_KEY_MAP[seq])
                    i += length
                    matched = True
                    break


            if matched:
                continue

            # Check if this is an unknown escape sequence (consume up to terminating char)
            # Standard CSI sequence ends with character in 0x40-0x7E (@ through ~)
            if raw[i + 1] == "[":
                j = i + 2
                while j < n and not (0x40 <= ord(raw[j]) <= 0x7E):
                    j += 1
                if j < n:
                    # Consumed unknown CSI sequence
                    i = j + 1
                    continue

            # Fallback: emit solitary ESC
            yield KeyMsg(Key("esc"))
            i += 1
            continue

        # Check for control characters
        code = ord(char)
        if code in CTRL_KEY_MAP:
            name = CTRL_KEY_MAP[code]
            is_ctrl = name.startswith("ctrl+")
            yield KeyMsg(Key(name=name, char=None if is_ctrl or name in ("enter", "tab", "backspace") else char, ctrl=is_ctrl))
            i += 1
            continue

        # Regular printable character
        yield KeyMsg(Key(name=char, char=char))
        i += 1
