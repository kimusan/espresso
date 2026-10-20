"""Terminal image viewer component with native hardware and cell-based rendering.

Inspired by mistakenelf/teacup/image, Limoni, and modern terminal graphics protocols.
Supports DEC Sixel and Kitty Graphics Protocol hardware rasterization with automatic
terminal capability detection, intelligent tmux multiplexer protection, and graceful
fallback to 24-bit ANSI upper-half blocks (▀), Braille 2x4 dot matrices, or ASCII ramps.
Includes pure Python standard library decoders and encoders for Sixel, Kitty APC,
Netpbm PPM, uncompressed BMP, and raw RGB matrices, with an optional Pillow bridge
for PNG/JPEG when installed.
"""

from __future__ import annotations

import base64
import colorsys
import os
import struct
from enum import Enum
from pathlib import Path
from typing import Sequence

from espresso.beans.viewport import Viewport
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.style import Style
from espresso.crema.width import string_width


class TerminalGraphicsProtocol(Enum):
    """Terminal graphics protocol and rendering strategy."""

    AUTO = "auto"              # Auto-detect best supported protocol (Kitty, Sixel, or Half-block)
    KITTY = "kitty"            # Native Kitty graphics protocol (APC ESC _ G ... ESC \)
    SIXEL = "sixel"            # Native DEC Sixel graphics protocol (DCS ESC P q ... ESC \)
    HALF_BLOCK = "half_block"  # 24-bit RGB upper-half blocks (▀)
    BRAILLE = "braille"        # Braille 2x4 dot matrix (U+2800..U+28FF)
    ASCII = "ascii"            # Grayscale ASCII density characters (@%#*+=-:. )


class RenderMode(Enum):
    """Terminal pixel rendering strategy (backward-compatible alias for protocols)."""

    HALF_BLOCK = "half_block"
    BRAILLE = "braille"
    ASCII = "ascii"
    KITTY = "kitty"
    SIXEL = "sixel"
    AUTO = "auto"


ASCII_RAMP = " .:-=+*#%@"

# Default DEC VT340 16-color Sixel palette in RGB values
DEFAULT_VT340_PALETTE: list[tuple[int, int, int]] = [
    (0, 0, 0),        # 0: 0% 0% 0%
    (51, 51, 204),    # 1: 20% 20% 80%
    (204, 33, 33),    # 2: 80% 13% 13%
    (51, 204, 51),    # 3: 20% 80% 20%
    (204, 51, 204),   # 4: 80% 20% 80%
    (51, 204, 204),   # 5: 20% 80% 80%
    (204, 204, 51),   # 6: 80% 80% 20%
    (135, 135, 135),  # 7: 53% 53% 53%
    (66, 66, 66),     # 8: 26% 26% 26%
    (84, 84, 153),    # 9: 33% 33% 60%
    (153, 66, 66),    # 10: 60% 26% 26%
    (84, 153, 84),    # 11: 33% 60% 33%
    (153, 84, 153),   # 12: 60% 33% 60%
    (84, 153, 153),   # 13: 33% 60% 60%
    (153, 153, 84),   # 14: 60% 60% 33%
    (204, 204, 204),  # 15: 80% 80% 80%
]


def is_inside_tmux() -> bool:
    """Return True if executing inside a tmux or screen session."""
    return bool(os.environ.get("TMUX") or os.environ.get("TERM", "").startswith(("tmux", "screen")))


def wrap_tmux_passthrough(seq: str) -> str:
    """Wrap an escape sequence in tmux DCS passthrough with doubled ESC characters.

    In tmux, pass-through sequences require: ESC P tmux ; <escaped_body> ESC \\
    where all ESC characters inside <escaped_body> are doubled to ESC ESC.
    """
    escaped = seq.replace("\x1b", "\x1b\x1b")
    return f"\x1bPtmux;{escaped}\x1b\\"


def detect_terminal_graphics(
    allow_tmux_passthrough: bool = False,
    allow_query: bool = False,
) -> TerminalGraphicsProtocol:
    """Detect the graphics protocol supported by the current terminal environment.

    When running inside tmux or screen, returns HALF_BLOCK unless allow_tmux_passthrough
    is explicitly True, avoiding tmux split-pane clobbering and unhandled passthrough errors.
    """
    if is_inside_tmux() and not allow_tmux_passthrough:
        return TerminalGraphicsProtocol.HALF_BLOCK

    # Check for Kitty graphics support
    # Supported by Kitty, Ghostty, WezTerm
    if (
        os.environ.get("KITTY_WINDOW_ID")
        or os.environ.get("KITTY_PID")
        or os.environ.get("GHOSTTY_RESOURCES_DIR")
        or os.environ.get("TERM_PROGRAM") in ("ghostty", "kitty", "WezTerm")
        or os.environ.get("TERM") == "xterm-kitty"
    ):
        return TerminalGraphicsProtocol.KITTY

    # Check for Sixel graphics support
    # Supported by Foot, WezTerm, Contour, Mintty, mlterm, XTerm with sixel
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    term = os.environ.get("TERM", "").lower()

    if term_program in ("foot", "contour", "mlterm", "mintty") or term.startswith(
        ("foot", "mlterm", "xterm-sixel", "vt340")
    ):
        return TerminalGraphicsProtocol.SIXEL

    # Fallback to universally supported half-block truecolor
    return TerminalGraphicsProtocol.HALF_BLOCK


def rgb_to_ansi_half_block(
    top_rgb: tuple[int, int, int] | None,
    bot_rgb: tuple[int, int, int] | None,
) -> str:
    """Pack two vertical RGB pixels into a single ▀ character."""
    if top_rgb is None and bot_rgb is None:
        return " "

    fg_part = f"\x1b[38;2;{top_rgb[0]};{top_rgb[1]};{top_rgb[2]}m" if top_rgb else ""
    bg_part = f"\x1b[48;2;{bot_rgb[0]};{bot_rgb[1]};{bot_rgb[2]}m" if bot_rgb else ""

    if top_rgb and bot_rgb:
        return f"{fg_part}{bg_part}▀\x1b[0m"
    elif top_rgb and not bot_rgb:
        return f"{fg_part}▀\x1b[0m"
    else:
        # Only bottom pixel present
        return f"{bg_part} \x1b[0m"


def rgb_to_ascii(rgb: tuple[int, int, int]) -> str:
    """Map an RGB pixel to an ASCII density character."""
    r, g, b = rgb
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    idx = int(luminance * (len(ASCII_RAMP) - 1))
    idx = max(0, min(idx, len(ASCII_RAMP) - 1))
    return ASCII_RAMP[idx]


def scale_rgb_matrix(
    matrix: list[list[tuple[int, int, int]]],
    target_width: int,
    target_height: int,
) -> list[list[tuple[int, int, int]]]:
    """Resize an RGB pixel matrix using nearest-neighbor scaling."""
    orig_h = len(matrix)
    if orig_h == 0:
        return []
    orig_w = len(matrix[0])
    if orig_w == 0 or target_width <= 0 or target_height <= 0:
        return []

    if orig_w == target_width and orig_h == target_height:
        return matrix

    scaled: list[list[tuple[int, int, int]]] = []
    for y in range(target_height):
        src_y = min(orig_h - 1, int(y * orig_h / target_height))
        row: list[tuple[int, int, int]] = []
        for x in range(target_width):
            src_x = min(orig_w - 1, int(x * orig_w / target_width))
            row.append(matrix[src_y][src_x])
        scaled.append(row)

    return scaled


def decode_sixel(
    data: bytes | str,
    default_bg: tuple[int, int, int] = (0, 0, 0),
) -> list[list[tuple[int, int, int]]]:
    """Decode DEC Sixel graphics data into an RGB pixel matrix in pure Python.

    Supports DCS envelope stripping, raster attributes, color palette registers,
    RGB percentage and DEC HLS color specifications, run-length compression,
    and carriage return/line feed band stepping.
    """
    if isinstance(data, str):
        data = data.encode("latin1", errors="replace")

    # Locate Sixel payload start (after 'q' if a DCS envelope is present)
    idx = 0
    q_pos = data.find(b"q")
    if q_pos != -1 and q_pos < 50:
        idx = q_pos + 1

    palette = list(DEFAULT_VT340_PALETTE) + [default_bg] * (256 - len(DEFAULT_VT340_PALETTE))
    current_color = 0
    canvas: dict[tuple[int, int], tuple[int, int, int]] = {}
    x = 0
    y = 0
    max_w = 0
    max_h = 0
    n = len(data)

    def parse_nums(p: int) -> tuple[list[int], int]:
        vals: list[int] = []
        num = 0
        has_num = False
        while p < n:
            b = data[p]
            if 48 <= b <= 57:  # '0' through '9'
                num = num * 10 + (b - 48)
                has_num = True
                p += 1
            elif b == ord(";"):
                vals.append(num)
                num = 0
                has_num = False
                p += 1
            else:
                break
        if has_num:
            vals.append(num)
        return vals, p

    while idx < n:
        b = data[idx]
        if b in (ord(" "), ord("\t")):
            idx += 1
            continue
        elif b in (ord("\r"), ord("$")):
            x = 0
            idx += 1
        elif b in (ord("\n"), ord("-")):
            x = 0
            y += 6
            idx += 1
        elif b == ord('"'):
            # Raster attributes: "pan;pad;ph;pv
            nums, idx = parse_nums(idx + 1)
            if len(nums) >= 4:
                max_w = max(max_w, nums[2])
                max_h = max(max_h, nums[3])
        elif b == ord("#"):
            # Color selector or definition: #id or #id;type;c1;c2;c3
            nums, idx = parse_nums(idx + 1)
            if nums:
                reg = nums[0] & 255
                current_color = reg
                if len(nums) >= 5:
                    mode = nums[1]
                    if mode == 2:
                        # RGB percentage
                        r = int(min(100, nums[2]) * 255 / 100)
                        g = int(min(100, nums[3]) * 255 / 100)
                        bl = int(min(100, nums[4]) * 255 / 100)
                        palette[reg] = (r, g, bl)
                    elif mode == 1:
                        # DEC HLS (Hue 0 is blue, 120 is red)
                        hue = ((nums[2] + 240) % 360) / 360.0
                        light = min(100, nums[3]) / 100.0
                        sat = min(100, nums[4]) / 100.0
                        rf, gf, bf = colorsys.hls_to_rgb(hue, light, sat)
                        palette[reg] = (int(rf * 255 + 0.5), int(gf * 255 + 0.5), int(bf * 255 + 0.5))
        elif b == ord("!"):
            # Run-length compression: !<count><char>
            nums, idx = parse_nums(idx + 1)
            if nums and idx < n:
                count = nums[0]
                char_byte = data[idx]
                idx += 1
                if 63 <= char_byte <= 126:
                    bits = char_byte - 63
                    for k in range(6):
                        if bits & (1 << k):
                            for r_step in range(count):
                                canvas[(x + r_step, y + k)] = palette[current_color]
                            max_h = max(max_h, y + k + 1)
                    x += count
                    max_w = max(max_w, x)
        elif 63 <= b <= 126:
            # 6-pixel vertical slice
            bits = b - 63
            for k in range(6):
                if bits & (1 << k):
                    canvas[(x, y + k)] = palette[current_color]
                    max_h = max(max_h, y + k + 1)
            x += 1
            max_w = max(max_w, x)
            idx += 1
        elif b == 0x1B:  # ESC string terminator
            break
        else:
            idx += 1

    if max_w == 0 or max_h == 0:
        return []

    matrix: list[list[tuple[int, int, int]]] = []
    for r in range(max_h):
        row: list[tuple[int, int, int]] = []
        for c in range(max_w):
            row.append(canvas.get((c, r), default_bg))
        matrix.append(row)

    return matrix


def encode_sixel(
    pixels: list[list[tuple[int, int, int]]],
    max_colors: int = 256,
) -> str:
    """Encode an RGB pixel matrix into a DEC Sixel DCS byte stream in pure Python."""
    if not pixels or not pixels[0]:
        return ""

    h = len(pixels)
    w = len(pixels[0])

    # Quantize colors to max_colors (using 8-bit 3-3-2 quantization if needed)
    unique_colors = set(c for row in pixels for c in row)
    use_quant = len(unique_colors) > max_colors

    def get_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        if not use_quant:
            return rgb
        r, g, b = rgb
        return ((r >> 5) << 5, (g >> 5) << 5, (b >> 6) << 6)

    color_map: dict[tuple[int, int, int], int] = {}
    palette: list[tuple[int, int, int]] = []

    for row in pixels:
        for raw_c in row:
            c = get_color(raw_c)
            if c not in color_map and len(palette) < max_colors:
                color_map[c] = len(palette)
                palette.append(c)

    parts: list[str] = [f'\x1bPq"1;1;{w};{h}']
    for idx, (r, g, b) in enumerate(palette):
        parts.append(f"#{idx};2;{r * 100 // 255};{g * 100 // 255};{b * 100 // 255}")

    for band_y in range(0, h, 6):
        band_colors: set[int] = set()
        for dy in range(min(6, h - band_y)):
            for x in range(w):
                c = get_color(pixels[band_y + dy][x])
                band_colors.add(color_map.get(c, 0))

        first = True
        for col_idx in sorted(band_colors):
            if not first:
                parts.append("$")
            first = False
            parts.append(f"#{col_idx}")

            band_chars: list[str] = []
            for x in range(w):
                bits = 0
                for dy in range(min(6, h - band_y)):
                    c = get_color(pixels[band_y + dy][x])
                    if color_map.get(c, 0) == col_idx:
                        bits |= (1 << dy)
                band_chars.append(chr(63 + bits))

            # Run-length compression
            i = 0
            while i < len(band_chars):
                char = band_chars[i]
                run = 1
                while i + run < len(band_chars) and band_chars[i + run] == char:
                    run += 1
                if run > 3:
                    parts.append(f"!{run}{char}")
                else:
                    parts.append(char * run)
                i += run

        if band_y + 6 < h:
            parts.append("-")

    parts.append("\x1b\\")
    return "".join(parts)


def decode_kitty(data: bytes | str) -> list[list[tuple[int, int, int]]]:
    """Decode a Kitty Graphics Protocol APC sequence or base64 payload into an RGB matrix."""
    if isinstance(data, bytes):
        data = data.decode("latin1", errors="replace")

    # Strip APC introducer if present: \x1b_G ... \x1b\
    if "\x1b_G" in data:
        start = data.index("\x1b_G") + 3
        end = data.find("\x1b\\", start)
        if end == -1:
            end = len(data)
        data = data[start:end]

    if ";" not in data:
        return []

    ctrl_str, b64_payload = data.split(";", 1)
    keys: dict[str, str] = {}
    for kv in ctrl_str.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            keys[k.strip()] = v.strip()

    w = int(keys.get("s", "0"))
    h = int(keys.get("v", "0"))
    fmt = keys.get("f", "24")

    raw = base64.b64decode(b64_payload)
    bpp = 3 if fmt == "24" else 4
    if w <= 0 or h <= 0 or len(raw) < w * h * bpp:
        return []

    matrix: list[list[tuple[int, int, int]]] = []
    idx = 0
    for r in range(h):
        row: list[tuple[int, int, int]] = []
        for c in range(w):
            r_val, g_val, b_val = raw[idx], raw[idx + 1], raw[idx + 2]
            row.append((r_val, g_val, b_val))
            idx += bpp
        matrix.append(row)

    return matrix


def encode_kitty(
    pixels: list[list[tuple[int, int, int]]],
    cols: int | None = None,
    rows: int | None = None,
    image_id: int = 1,
) -> str:
    """Encode an RGB pixel matrix into Kitty Graphics Protocol APC escape sequences."""
    if not pixels or not pixels[0]:
        return ""

    h = len(pixels)
    w = len(pixels[0])
    raw_bytes = bytes([c for row in pixels for px in row for c in px[:3]])
    b64 = base64.b64encode(raw_bytes).decode("ascii")

    chunk_size = 4096
    chunks = [b64[i : i + chunk_size] for i in range(0, len(b64), chunk_size)]
    parts: list[str] = []

    for idx, chunk in enumerate(chunks):
        m = 1 if idx < len(chunks) - 1 else 0
        if idx == 0:
            ctrl = f"a=T,f=24,s={w},v={h},i={image_id},m={m}"
            if cols is not None and rows is not None:
                ctrl += f",c={cols},r={rows}"
            parts.append(f"\x1b_G{ctrl};{chunk}\x1b\\")
        else:
            parts.append(f"\x1b_Gm={m};{chunk}\x1b\\")

    return "".join(parts)


def parse_ppm(data: bytes | str) -> list[list[tuple[int, int, int]]]:
    """Parse a Netpbm PPM (P3 text or P6 binary) image into an RGB matrix."""
    if isinstance(data, str):
        data = data.encode("latin1")

    tokens: list[bytes] = []
    idx = 0
    length = len(data)

    while idx < length and len(tokens) < 4:
        while idx < length and data[idx] in b" \t\r\n":
            idx += 1
        if idx >= length:
            break
        if data[idx] == ord(b"#"):
            while idx < length and data[idx] != ord(b"\n"):
                idx += 1
            continue

        start = idx
        while idx < length and data[idx] not in b" \t\r\n#":
            idx += 1
        tokens.append(data[start:idx])

    if len(tokens) < 4:
        raise ValueError("Invalid PPM header")

    magic = tokens[0].decode("ascii")
    width = int(tokens[1].decode("ascii"))
    height = int(tokens[2].decode("ascii"))
    max_val = int(tokens[3].decode("ascii"))

    if idx < length and data[idx] in b" \t\r\n":
        idx += 1

    matrix: list[list[tuple[int, int, int]]] = []

    if magic == "P6":
        bytes_per_sample = 1 if max_val < 256 else 2
        for _ in range(height):
            row: list[tuple[int, int, int]] = []
            for _ in range(width):
                if bytes_per_sample == 1:
                    r = data[idx]
                    g = data[idx + 1]
                    b = data[idx + 2]
                    idx += 3
                else:
                    r = data[idx]
                    g = data[idx + 2]
                    b = data[idx + 4]
                    idx += 6
                row.append((r, g, b))
            matrix.append(row)
    elif magic == "P3":
        rest_tokens = data[idx:].split()
        tok_idx = 0
        for _ in range(height):
            row = []
            for _ in range(width):
                r = int(rest_tokens[tok_idx])
                g = int(rest_tokens[tok_idx + 1])
                b = int(rest_tokens[tok_idx + 2])
                tok_idx += 3
                row.append((r, g, b))
            matrix.append(row)
    else:
        raise ValueError(f"Unsupported PPM format: {magic}")

    return matrix


def parse_bmp(data: bytes) -> list[list[tuple[int, int, int]]]:
    """Parse uncompressed 24-bit Windows BMP image into an RGB matrix."""
    if len(data) < 54 or data[:2] != b"BM":
        raise ValueError("Invalid BMP header")

    offset = struct.unpack_from("<I", data, 10)[0]
    header_size = struct.unpack_from("<I", data, 14)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    planes, bpp = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]

    if bpp != 24 or compression != 0:
        raise ValueError(f"Only uncompressed 24-bit BMP is supported (got {bpp}bpp, compression {compression})")

    is_top_down = height < 0
    h = abs(height)
    w = width
    row_stride = ((w * 3 + 3) // 4) * 4

    matrix: list[list[tuple[int, int, int]]] = []
    for r in range(h):
        row_idx = (r if is_top_down else (h - 1 - r))
        row_offset = offset + row_idx * row_stride
        row: list[tuple[int, int, int]] = []
        for c in range(w):
            b, g, r_val = data[row_offset + c * 3 : row_offset + c * 3 + 3]
            row.append((r_val, g, b))
        matrix.append(row)

    return matrix


def render_image_to_lines(
    matrix: list[list[tuple[int, int, int]]],
    mode: RenderMode | TerminalGraphicsProtocol = RenderMode.HALF_BLOCK,
) -> list[str]:
    """Convert an RGB pixel matrix to a list of terminal text lines using half-blocks or ASCII."""
    if not matrix or not matrix[0]:
        return []

    h = len(matrix)
    w = len(matrix[0])
    lines: list[str] = []

    mode_val = mode.value if isinstance(mode, (RenderMode, TerminalGraphicsProtocol)) else str(mode)

    if mode_val == "ascii":
        for y in range(h):
            row_chars = [rgb_to_ascii(matrix[y][x]) for x in range(w)]
            lines.append("".join(row_chars))
    else:
        # Half-block mode (2 rows per character cell)
        for y in range(0, h, 2):
            row_chars = []
            for x in range(w):
                top_pixel = matrix[y][x]
                bot_pixel = matrix[y + 1][x] if y + 1 < h else None
                row_chars.append(rgb_to_ansi_half_block(top_pixel, bot_pixel))
            lines.append("".join(row_chars))

    return lines


def render_image_to_braille(
    matrix: list[list[tuple[int, int, int]]],
    width: int,
    height: int,
    threshold: float = 0.35,
) -> list[str]:
    """Render an RGB pixel matrix into Braille 2x4 dot matrix characters with 24-bit truecolor."""
    if not matrix or not matrix[0] or width <= 0 or height <= 0:
        return []

    # Target dot grid: 2 dots horizontally, 4 dots vertically per cell
    dot_w = width * 2
    dot_h = height * 4
    scaled = scale_rgb_matrix(matrix, dot_w, dot_h)

    lines: list[str] = []
    for cy in range(height):
        cell_chars: list[str] = []
        for cx in range(width):
            mask = 0
            active_colors: list[tuple[int, int, int]] = []
            all_colors: list[tuple[int, int, int]] = []

            # 2 columns x 4 rows
            coords = [
                ((0, 0), 0x01), ((0, 1), 0x02), ((0, 2), 0x04), ((0, 3), 0x40),
                ((1, 0), 0x08), ((1, 1), 0x10), ((1, 2), 0x20), ((1, 3), 0x80),
            ]

            for (dx, dy), bit in coords:
                px = cx * 2 + dx
                py = cy * 4 + dy
                if py < len(scaled) and px < len(scaled[py]):
                    rgb = scaled[py][px]
                    all_colors.append(rgb)
                    lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0
                    if lum >= threshold:
                        mask |= bit
                        active_colors.append(rgb)

            colors_to_avg = active_colors if active_colors else all_colors
            if colors_to_avg:
                avg_r = sum(c[0] for c in colors_to_avg) // len(colors_to_avg)
                avg_g = sum(c[1] for c in colors_to_avg) // len(colors_to_avg)
                avg_b = sum(c[2] for c in colors_to_avg) // len(colors_to_avg)
            else:
                avg_r, avg_g, avg_b = 0, 0, 0

            ch = chr(0x2800 + mask)
            if mask == 0:
                cell_chars.append(" ")
            else:
                cell_chars.append(f"\x1b[38;2;{avg_r};{avg_g};{avg_b}m{ch}\x1b[0m")

        lines.append("".join(cell_chars))

    return lines


class ImageViewer(Model):
    """Terminal image previewer supporting native Sixel, Kitty, half-block, and braille rendering."""

    def __init__(
        self,
        pixels: list[list[tuple[int, int, int]]] | None = None,
        width: int = 40,
        height: int = 20,
        mode: RenderMode | TerminalGraphicsProtocol | str = TerminalGraphicsProtocol.AUTO,
        protocol: TerminalGraphicsProtocol | RenderMode | str | None = None,
        enable_native: bool = True,
        allow_tmux_passthrough: bool = False,
        title: str = "Image Preview",
        show_border: bool = True,
    ) -> None:
        self.raw_matrix = pixels or []
        self.width = max(10, width)
        self.height = max(4, height)

        # Allow mode or protocol argument interchangeably
        chosen_proto = protocol if protocol is not None else mode
        if isinstance(chosen_proto, str):
            try:
                self.protocol = TerminalGraphicsProtocol(chosen_proto)
            except ValueError:
                self.protocol = TerminalGraphicsProtocol.AUTO
        elif isinstance(chosen_proto, RenderMode):
            self.protocol = TerminalGraphicsProtocol(chosen_proto.value)
        else:
            self.protocol = chosen_proto

        self.mode = self.protocol
        self.enable_native = enable_native
        self.allow_tmux_passthrough = allow_tmux_passthrough
        self.title = title
        self.show_border = show_border

        self.viewport = Viewport(width=self.width, height=self.height)
        self._rebuild_rendered()

    @classmethod
    def from_ppm(cls, ppm_data: bytes | str, **kwargs) -> ImageViewer:
        """Create an ImageViewer from Netpbm PPM data."""
        matrix = parse_ppm(ppm_data)
        return cls(pixels=matrix, **kwargs)

    @classmethod
    def from_bmp(cls, bmp_bytes: bytes, **kwargs) -> ImageViewer:
        """Create an ImageViewer from uncompressed 24-bit BMP bytes."""
        matrix = parse_bmp(bmp_bytes)
        return cls(pixels=matrix, **kwargs)

    @classmethod
    def from_sixel(cls, sixel_data: bytes | str, **kwargs) -> ImageViewer:
        """Create an ImageViewer from DEC Sixel graphics data."""
        matrix = decode_sixel(sixel_data)
        return cls(pixels=matrix, **kwargs)

    @classmethod
    def from_kitty(cls, kitty_data: bytes | str, **kwargs) -> ImageViewer:
        """Create an ImageViewer from Kitty Graphics Protocol APC data."""
        matrix = decode_kitty(kitty_data)
        return cls(pixels=matrix, **kwargs)

    @classmethod
    def from_file(cls, path: str | Path, **kwargs) -> ImageViewer:
        """Load an image file (PPM, BMP, Sixel, or PNG/JPG if Pillow is installed)."""
        p = Path(path)
        data = p.read_bytes()
        suffix = p.suffix.lower()

        if suffix in (".ppm", ".pgm"):
            return cls.from_ppm(data, title=p.name, **kwargs)
        elif suffix == ".bmp":
            return cls.from_bmp(data, title=p.name, **kwargs)
        elif suffix in (".sixel", ".six"):
            return cls.from_sixel(data, title=p.name, **kwargs)
        elif suffix == ".kitty":
            return cls.from_kitty(data, title=p.name, **kwargs)
        else:
            # Try Pillow if available
            try:
                from PIL import Image as PILImage
                import io
                img = PILImage.open(io.BytesIO(data)).convert("RGB")
                w, h = img.size
                rgb_bytes = img.tobytes()
                matrix = []
                idx = 0
                for _ in range(h):
                    row = []
                    for _ in range(w):
                        row.append((rgb_bytes[idx], rgb_bytes[idx + 1], rgb_bytes[idx + 2]))
                        idx += 3
                    matrix.append(row)
                return cls(pixels=matrix, title=p.name, **kwargs)
            except ImportError:
                raise ValueError(
                    f"Unsupported image format '{suffix}' without Pillow. "
                    f"Native standard library supports .ppm, .bmp, .sixel, and .kitty images."
                )

    def set_protocol(
        self,
        protocol: TerminalGraphicsProtocol | RenderMode | str,
        enable_native: bool | None = None,
    ) -> None:
        """Update graphics protocol and rebuild rendering."""
        if isinstance(protocol, str):
            try:
                self.protocol = TerminalGraphicsProtocol(protocol)
            except ValueError:
                self.protocol = TerminalGraphicsProtocol.AUTO
        elif isinstance(protocol, RenderMode):
            self.protocol = TerminalGraphicsProtocol(protocol.value)
        else:
            self.protocol = protocol

        self.mode = self.protocol
        if enable_native is not None:
            self.enable_native = enable_native
        self._rebuild_rendered()

    def toggle_native(self) -> None:
        """Toggle between hardware native protocols and cell-based fallbacks."""
        self.enable_native = not self.enable_native
        self._rebuild_rendered()

    def set_size(self, width: int, height: int) -> None:
        """Update display dimensions and re-render."""
        self.width = max(10, width)
        self.height = max(4, height)
        self.viewport.width = self.width
        self.viewport.height = self.height
        self._rebuild_rendered()

    def _resolve_protocol(self) -> TerminalGraphicsProtocol:
        """Determine effective rendering strategy based on configuration and environment."""
        proto = self.protocol
        if proto == TerminalGraphicsProtocol.AUTO:
            if not self.enable_native:
                return TerminalGraphicsProtocol.HALF_BLOCK
            return detect_terminal_graphics(allow_tmux_passthrough=self.allow_tmux_passthrough)

        if proto in (TerminalGraphicsProtocol.KITTY, TerminalGraphicsProtocol.SIXEL):
            if not self.enable_native:
                return TerminalGraphicsProtocol.HALF_BLOCK
            if is_inside_tmux() and not self.allow_tmux_passthrough:
                return TerminalGraphicsProtocol.HALF_BLOCK

        return proto

    def _rebuild_rendered(self) -> None:
        """Re-render pixel matrix into terminal viewport."""
        if not self.raw_matrix:
            self.viewport.set_content("No image loaded")
            return

        effective = self._resolve_protocol()

        if effective == TerminalGraphicsProtocol.KITTY:
            seq = encode_kitty(self.raw_matrix, cols=self.width, rows=self.height)
            if is_inside_tmux() and self.allow_tmux_passthrough:
                seq = wrap_tmux_passthrough(seq)
            # Pad rectangular lines so surrounding layout geometry and borders remain stable
            lines = [seq + (" " * self.width)] + [(" " * self.width) for _ in range(self.height - 1)]
            self.viewport.set_content("\n".join(lines))

        elif effective == TerminalGraphicsProtocol.SIXEL:
            # Scale to terminal pixel dimensions (approx 8x16 pixels per character cell)
            target_w = self.width * 8
            target_h = self.height * 16
            scaled = scale_rgb_matrix(self.raw_matrix, target_w, target_h)
            seq = encode_sixel(scaled)
            if is_inside_tmux() and self.allow_tmux_passthrough:
                seq = wrap_tmux_passthrough(seq)
            lines = [seq + (" " * self.width)] + [(" " * self.width) for _ in range(self.height - 1)]
            self.viewport.set_content("\n".join(lines))

        elif effective == TerminalGraphicsProtocol.BRAILLE:
            lines = render_image_to_braille(self.raw_matrix, width=self.width, height=self.height)
            self.viewport.set_content("\n".join(lines))

        elif effective == TerminalGraphicsProtocol.ASCII:
            scaled = scale_rgb_matrix(self.raw_matrix, self.width, self.height)
            lines = render_image_to_lines(scaled, RenderMode.ASCII)
            self.viewport.set_content("\n".join(lines))

        else:
            # Default HALF_BLOCK
            target_w = self.width
            target_h = self.height * 2
            scaled = scale_rgb_matrix(self.raw_matrix, target_w, target_h)
            lines = render_image_to_lines(scaled, RenderMode.HALF_BLOCK)
            self.viewport.set_content("\n".join(lines))

    def set_pixels(self, matrix: list[list[tuple[int, int, int]]]) -> None:
        """Set a new pixel matrix and re-render."""
        self.raw_matrix = matrix
        self._rebuild_rendered()

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[ImageViewer, Cmd | None]:
        """Handle panning / scrolling keys."""
        self.viewport, cmd = self.viewport.update(msg)
        return self, cmd

    def view(self) -> str:
        """Render the image viewport."""
        return self.viewport.view()
