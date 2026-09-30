"""Terminal image viewer component using 24-bit ANSI half-block rendering.

Inspired by mistakenelf/teacup/image.
Renders graphics, photos, pixel art, and charts in the terminal using
truecolor 24-bit upper-half blocks (▀) with pure Python standard library
support for Netpbm PPM, uncompressed BMP, and raw RGB matrices, plus an
optional Pillow bridge for PNG/JPEG when available.
"""

from __future__ import annotations

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


class RenderMode(Enum):
    """Terminal pixel rendering strategy."""

    HALF_BLOCK = "half_block"  # 24-bit RGB upper-half blocks (▀)
    ASCII = "ascii"            # Grayscale ASCII density characters (@%#*+=-:. )


ASCII_RAMP = " .:-=+*#%@"


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


def parse_ppm(data: bytes | str) -> list[list[tuple[int, int, int]]]:
    """Parse a Netpbm PPM (P3 text or P6 binary) image into an RGB matrix."""
    if isinstance(data, str):
        data = data.encode("latin1")

    # Strip comments and tokenize tokens
    tokens: list[bytes] = []
    idx = 0
    length = len(data)

    while idx < length and len(tokens) < 4:
        # Skip whitespace
        while idx < length and data[idx] in b" \t\r\n":
            idx += 1
        if idx >= length:
            break
        # Skip comment
        if data[idx] == ord(b"#"):
            while idx < length and data[idx] != ord(b"\n"):
                idx += 1
            continue

        # Extract token
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

    # Skip single whitespace after max_val header
    if idx < length and data[idx] in b" \t\r\n":
        idx += 1

    matrix: list[list[tuple[int, int, int]]] = []

    if magic == "P6":
        # Binary RGB
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
        # Text ASCII RGB
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
    row_stride = ((w * 3 + 3) // 4) * 4  # rows are 4-byte aligned

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
    mode: RenderMode = RenderMode.HALF_BLOCK,
) -> list[str]:
    """Convert an RGB pixel matrix to a list of terminal text lines."""
    if not matrix or not matrix[0]:
        return []

    h = len(matrix)
    w = len(matrix[0])
    lines: list[str] = []

    if mode == RenderMode.HALF_BLOCK:
        # Step 2 rows per character cell
        for y in range(0, h, 2):
            row_chars: list[str] = []
            for x in range(w):
                top_pixel = matrix[y][x]
                bot_pixel = matrix[y + 1][x] if y + 1 < h else None
                row_chars.append(rgb_to_ansi_half_block(top_pixel, bot_pixel))
            lines.append("".join(row_chars))
    else:
        # ASCII mode
        for y in range(h):
            row_chars = [rgb_to_ascii(matrix[y][x]) for x in range(w)]
            lines.append("".join(row_chars))

    return lines


class ImageViewer(Model):
    """Terminal image previewer supporting 24-bit half-block rendering."""

    def __init__(
        self,
        pixels: list[list[tuple[int, int, int]]] | None = None,
        width: int = 40,
        height: int = 20,
        mode: RenderMode = RenderMode.HALF_BLOCK,
        title: str = "Image Preview",
        show_border: bool = True,
    ) -> None:
        self.raw_matrix = pixels or []
        self.width = max(10, width)
        self.height = max(4, height)
        self.mode = mode
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
    def from_file(cls, path: str | Path, **kwargs) -> ImageViewer:
        """Load an image file (PPM, BMP, or PNG/JPG if Pillow is installed)."""
        p = Path(path)
        data = p.read_bytes()
        suffix = p.suffix.lower()

        if suffix in (".ppm", ".pgm"):
            return cls.from_ppm(data, title=p.name, **kwargs)
        elif suffix == ".bmp":
            return cls.from_bmp(data, title=p.name, **kwargs)
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
                    f"Native standard library supports .ppm and .bmp images."
                )

    def _rebuild_rendered(self) -> None:
        if not self.raw_matrix:
            self.viewport.set_content("No image loaded")
            return

        # Target dimensions for half-block: 2 pixels per character height
        target_w = self.width
        target_h = self.height * 2 if self.mode == RenderMode.HALF_BLOCK else self.height

        scaled = scale_rgb_matrix(self.raw_matrix, target_w, target_h)
        lines = render_image_to_lines(scaled, self.mode)
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
