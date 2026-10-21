"""Unit tests for ImageViewer and terminal graphics rendering."""

from __future__ import annotations

import struct
import unittest

from espresso.beans.image import (
    ImageViewer,
    RenderMode,
    TerminalGraphicsProtocol,
    decode_kitty,
    decode_sixel,
    detect_terminal_graphics,
    encode_kitty,
    encode_sixel,
    is_inside_tmux,
    parse_bmp,
    parse_ppm,
    render_image_to_braille,
    rgb_to_ansi_half_block,
    rgb_to_ascii,
    scale_rgb_matrix,
    wrap_tmux_passthrough,
)


class TestImageViewer(unittest.TestCase):
    def test_half_block_ansi_packing(self) -> None:
        top = (255, 0, 0)      # Red
        bot = (0, 255, 0)      # Green
        block = rgb_to_ansi_half_block(top, bot)

        # Foreground 255,0,0 and Background 0,255,0 with '▀'
        self.assertIn("38;2;255;0;0", block)
        self.assertIn("48;2;0;255;0", block)
        self.assertIn("▀", block)

        # Top only
        top_only = rgb_to_ansi_half_block(top, None)
        self.assertIn("38;2;255;0;0", top_only)
        self.assertIn("▀", top_only)
        self.assertNotIn("48;2", top_only)

        # Bottom only should use lower half block '▄' with foreground color
        bot_only = rgb_to_ansi_half_block(None, bot)
        self.assertIn("38;2;0;255;0", bot_only)
        self.assertIn("▄", bot_only)
        self.assertNotIn("48;2", bot_only)

    def test_ascii_luminance_ramp(self) -> None:
        white = (255, 255, 255)
        black = (0, 0, 0)
        self.assertEqual(rgb_to_ascii(white), "@")
        self.assertEqual(rgb_to_ascii(black), " ")

    def test_matrix_scaling(self) -> None:
        matrix = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        scaled = scale_rgb_matrix(matrix, target_width=4, target_height=4)
        self.assertEqual(len(scaled), 4)
        self.assertEqual(len(scaled[0]), 4)
        self.assertEqual(scaled[0][0], (255, 0, 0))
        self.assertEqual(scaled[3][3], (255, 255, 255))

    def test_parse_ppm_p3_text(self) -> None:
        ppm_p3 = b"""P3
# Test 2x2 image
2 2
255
255 0 0    0 255 0
0 0 255    255 255 255
"""
        matrix = parse_ppm(ppm_p3)
        self.assertEqual(len(matrix), 2)
        self.assertEqual(len(matrix[0]), 2)
        self.assertEqual(matrix[0][0], (255, 0, 0))
        self.assertEqual(matrix[0][1], (0, 255, 0))
        self.assertEqual(matrix[1][0], (0, 0, 255))
        self.assertEqual(matrix[1][1], (255, 255, 255))

    def test_parse_ppm_p6_binary(self) -> None:
        header = b"P6\n2 2\n255\n"
        pixels = bytes([
            255, 0, 0,     0, 255, 0,
            0, 0, 255,     255, 255, 255,
        ])
        matrix = parse_ppm(header + pixels)
        self.assertEqual(matrix[0][0], (255, 0, 0))
        self.assertEqual(matrix[1][1], (255, 255, 255))

    def test_parse_bmp_uncompressed(self) -> None:
        # Create minimal 2x2 24-bit uncompressed BMP in memory
        w, h = 2, 2
        row_stride = ((w * 3 + 3) // 4) * 4  # 8 bytes per row
        pixel_data_size = row_stride * h
        file_size = 54 + pixel_data_size

        # BMP Header (14 bytes)
        bmp_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
        # DIB Header (40 bytes)
        dib_header = struct.pack("<IIIHHIIIIII", 40, w, h, 1, 24, 0, pixel_data_size, 2835, 2835, 0, 0)

        # BMP stores bottom-up in BGR format
        # Row 0 (bottom row): (0, 0, 255) -> BGR: (255, 0, 0), (255, 255, 255) -> (255, 255, 255) + 2 padding
        row0 = bytes([255, 0, 0, 255, 255, 255, 0, 0])
        # Row 1 (top row): (255, 0, 0) -> BGR: (0, 0, 255), (0, 255, 0) -> (0, 255, 0) + 2 padding
        row1 = bytes([0, 0, 255, 0, 255, 0, 0, 0])

        bmp_bytes = bmp_header + dib_header + row0 + row1
        matrix = parse_bmp(bmp_bytes)
        self.assertEqual(len(matrix), 2)
        self.assertEqual(matrix[0][0], (255, 0, 0))  # Top-left is red

    def test_image_viewer_model(self) -> None:
        pixels = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        viewer = ImageViewer(pixels=pixels, width=2, height=1, mode=RenderMode.HALF_BLOCK)
        v = viewer.view()
        self.assertIn("▀", v)

        # ASCII mode
        viewer_ascii = ImageViewer(pixels=pixels, width=2, height=2, mode=RenderMode.ASCII)
        v_ascii = viewer_ascii.view()
        self.assertIn("@", v_ascii)

    def test_decode_sixel_basic(self) -> None:
        # Minimal Sixel string: DCS q #0;2;100;0;0 #0@ ST
        # '@' is ord 64 -> 64 - 63 = 1 -> pixel (0, 0)
        sixel = "\x1bPq\"1;1;1;1#0;2;100;0;0#0@\x1b\\"
        matrix = decode_sixel(sixel)
        self.assertGreaterEqual(len(matrix), 1)
        self.assertGreaterEqual(len(matrix[0]), 1)
        self.assertEqual(matrix[0][0], (255, 0, 0))

    def test_decode_sixel_palette_and_rle(self) -> None:
        # Sixel with run-length encoding: !4~
        # '~' is ord 126 -> 63 bits (all 6 bits set: 1+2+4+8+16+32)
        sixel = "\x1bPq#1;2;0;100;0#1!4~\x1b\\"
        matrix = decode_sixel(sixel)
        self.assertEqual(len(matrix), 6)      # 6 vertical bits
        self.assertEqual(len(matrix[0]), 4)   # repeated 4 times
        for y in range(6):
            for x in range(4):
                self.assertEqual(matrix[y][x], (0, 255, 0))

    def test_decode_sixel_hls_palette(self) -> None:
        # Sixel with DEC HLS palette: mode 1
        # DEC Hue 0 is blue (0, 0, 255 in standard wheel)
        sixel = "\x1bPq#2;1;0;50;100#2@\x1b\\"
        matrix = decode_sixel(sixel)
        self.assertGreaterEqual(len(matrix), 1)
        b = matrix[0][0][2]
        self.assertGreater(b, 200)

    def test_encode_and_decode_sixel_roundtrip(self) -> None:
        original = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        sixel = encode_sixel(original)
        self.assertTrue(sixel.startswith("\x1bPq"))
        self.assertTrue(sixel.endswith("\x1b\\"))

        decoded = decode_sixel(sixel)
        self.assertEqual(len(decoded), 2)
        self.assertEqual(len(decoded[0]), 2)
        self.assertEqual(decoded[0][0], (255, 0, 0))
        self.assertEqual(decoded[0][1], (0, 255, 0))
        self.assertEqual(decoded[1][0], (0, 0, 255))
        self.assertEqual(decoded[1][1], (255, 255, 255))

    def test_encode_sixel_quantization(self) -> None:
        # Generate image with 300 unique colors (exceeding 256)
        pixels = [[(i % 256, (i * 2) % 256, (i * 3) % 256) for i in range(20)] for _ in range(15)]
        sixel = encode_sixel(pixels, max_colors=256)
        # Should cleanly encode without error
        self.assertTrue(sixel.startswith("\x1bPq"))
        decoded = decode_sixel(sixel)
        self.assertEqual(len(decoded), 15)
        self.assertEqual(len(decoded[0]), 20)

    def test_decode_and_encode_kitty(self) -> None:
        original = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        encoded = encode_kitty(original, cols=4, rows=2)
        self.assertTrue(encoded.startswith("\x1b_G"))
        self.assertIn("a=T", encoded)
        self.assertIn("f=24", encoded)
        self.assertIn("s=2,v=2", encoded)

        decoded = decode_kitty(encoded)
        self.assertEqual(decoded, original)

    def test_tmux_passthrough_wrapping(self) -> None:
        seq = "\x1b_Ga=T,f=24;payload\x1b\\"
        wrapped = wrap_tmux_passthrough(seq)
        # Verify that all inner ESC are doubled and wrapped in DCS passthrough
        self.assertTrue(wrapped.startswith("\x1bPtmux;\x1b\x1b_G"))
        self.assertTrue(wrapped.endswith("\x1b\x1b\\\x1b\\"))

    def test_tmux_detection_and_safe_fallback(self) -> None:
        import os
        from unittest.mock import patch

        # In tmux, default AUTO should safely fallback to HALF_BLOCK
        with patch.dict(os.environ, {"TMUX": "/tmp/tmux-1000/default,1234,0", "TERM_PROGRAM": "ghostty"}):
            self.assertTrue(is_inside_tmux())
            proto = detect_terminal_graphics(allow_tmux_passthrough=False)
            self.assertEqual(proto, TerminalGraphicsProtocol.HALF_BLOCK)

            # If user explicitly enables tmux passthrough, native is permitted
            proto_allowed = detect_terminal_graphics(allow_tmux_passthrough=True)
            self.assertEqual(proto_allowed, TerminalGraphicsProtocol.KITTY)

    def test_detect_terminal_graphics_kitty_and_sixel(self) -> None:
        import os
        from unittest.mock import patch

        # Ghostty or Kitty
        with patch.dict(os.environ, {"TERM_PROGRAM": "ghostty", "TMUX": ""}):
            proto = detect_terminal_graphics()
            self.assertEqual(proto, TerminalGraphicsProtocol.KITTY)

        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "TMUX": ""}):
            proto = detect_terminal_graphics()
            self.assertEqual(proto, TerminalGraphicsProtocol.KITTY)

        # Foot or Sixel
        with patch.dict(os.environ, {"TERM_PROGRAM": "foot", "TMUX": ""}):
            proto = detect_terminal_graphics()
            self.assertEqual(proto, TerminalGraphicsProtocol.SIXEL)

        # Unknown terminal
        with patch.dict(os.environ, {"TERM_PROGRAM": "unknown", "TERM": "vt100", "TMUX": ""}):
            proto = detect_terminal_graphics()
            self.assertEqual(proto, TerminalGraphicsProtocol.HALF_BLOCK)

    def test_braille_rendering(self) -> None:
        # 2x4 dots (1 cell) with high brightness
        pixels = [[(255, 255, 255), (255, 255, 255)] for _ in range(4)]
        lines = render_image_to_braille(pixels, width=1, height=1)
        self.assertEqual(len(lines), 1)
        # All 8 dots active produces chr(0x28FF) = '⣿'
        self.assertIn("⣿", lines[0])

    def test_image_viewer_from_sixel_and_kitty(self) -> None:
        original = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        sixel_data = encode_sixel(original)
        viewer_sixel = ImageViewer.from_sixel(sixel_data, width=10, height=5, mode=RenderMode.HALF_BLOCK)
        self.assertEqual(viewer_sixel.raw_matrix, original)
        v = viewer_sixel.view()
        self.assertIn("▀", v)

        kitty_data = encode_kitty(original)
        viewer_kitty = ImageViewer.from_kitty(kitty_data, width=10, height=5, mode=RenderMode.HALF_BLOCK)
        self.assertEqual(viewer_kitty.raw_matrix, original)

    def test_image_viewer_native_deselection(self) -> None:
        pixels = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        # Forced KITTY protocol, but enable_native=False deselects it
        viewer = ImageViewer(
            pixels=pixels,
            width=10,
            height=5,
            protocol=TerminalGraphicsProtocol.KITTY,
            enable_native=False,
        )
        self.assertEqual(viewer._resolve_protocol(), TerminalGraphicsProtocol.HALF_BLOCK)
        v = viewer.view()
        self.assertIn("▀", v)

        # Toggle native back on
        viewer.toggle_native()
        self.assertTrue(viewer.enable_native)
        self.assertEqual(viewer._resolve_protocol(), TerminalGraphicsProtocol.KITTY)
        v_native = viewer.view()
        self.assertIn("\x1b_G", v_native)

    def test_image_viewer_protocol_switching(self) -> None:
        pixels = [
            [(255, 255, 255), (255, 255, 255)],
            [(255, 255, 255), (255, 255, 255)],
        ]
        viewer = ImageViewer(pixels=pixels, width=10, height=5, protocol=TerminalGraphicsProtocol.HALF_BLOCK)
        self.assertIn("▀", viewer.view())

        # Switch to Braille
        viewer.set_protocol(TerminalGraphicsProtocol.BRAILLE)
        self.assertIn("⣿", viewer.view())

        # Switch to ASCII
        viewer.set_protocol(TerminalGraphicsProtocol.ASCII)
        self.assertIn("@", viewer.view())

    def test_image_viewer_tmux_passthrough_toggle(self) -> None:
        pixels = [[(255, 0, 0), (0, 255, 0)]]
        viewer = ImageViewer(pixels=pixels, width=10, height=5, allow_tmux_passthrough=False)
        self.assertFalse(viewer.allow_tmux_passthrough)

        state = viewer.toggle_tmux_passthrough()
        self.assertTrue(state)
        self.assertTrue(viewer.allow_tmux_passthrough)

        viewer.set_tmux_passthrough(False)
        self.assertFalse(viewer.allow_tmux_passthrough)

    def test_graphics_ansi_width_and_stripping(self) -> None:
        from espresso.crema.width import string_width, strip_ansi, truncate_ansi

        # Kitty graphics escape sequence
        kitty_seq = "\x1b_Ga=T,f=24,s=2,v=1;QUJDREVGR0g=\x1b\\"
        self.assertEqual(strip_ansi(kitty_seq), "")
        self.assertEqual(string_width(kitty_seq), 0)

        # Tmux wrapped Kitty sequence
        tmux_kitty = wrap_tmux_passthrough(kitty_seq)
        self.assertEqual(strip_ansi(tmux_kitty), "")
        self.assertEqual(string_width(tmux_kitty), 0)

        # Sixel graphics escape sequence
        sixel_seq = '\x1bPq"1;1;10;10#0;2;0;0;0#0~-~-\x1b\\'
        self.assertEqual(strip_ansi(sixel_seq), "")
        self.assertEqual(string_width(sixel_seq), 0)

        # Tmux wrapped Sixel sequence
        tmux_sixel = wrap_tmux_passthrough(sixel_seq)
        self.assertEqual(strip_ansi(tmux_sixel), "")
        self.assertEqual(string_width(tmux_sixel), 0)

        # Truncation must not damage preceding text or append spurious text
        line = f"Start: {tmux_kitty} End"
        self.assertEqual(string_width(line), 11)  # "Start: " (7) + "" (0) + " End" (4)
        truncated = truncate_ansi(line, 15)
        self.assertIn("\x1bPtmux;", truncated)
        self.assertTrue(truncated.endswith("End"))

    def test_image_viewer_kitty_placement_clearing(self) -> None:
        pixels = [[(255, 0, 0), (0, 255, 0)]]
        viewer = ImageViewer(pixels=pixels, width=10, height=5, protocol=TerminalGraphicsProtocol.KITTY, enable_native=True)

        # In Kitty mode, initial lines have Kitty transmission and clear sequence
        self.assertIn("a=T", viewer.viewport.lines[0])
        self.assertIn("a=d", viewer.viewport.lines[0])
        self.assertTrue(viewer._has_kitty_placement)

        # Switch to Braille: should emit clear sequence on the transition frame
        viewer.set_protocol(TerminalGraphicsProtocol.BRAILLE)
        self.assertIn("a=d", viewer.viewport.lines[0])
        self.assertFalse(viewer._has_kitty_placement)

        # Next rebuild in Braille should not re-emit clear sequence
        viewer._rebuild_rendered()
        self.assertNotIn("a=d", viewer.viewport.lines[0])


if __name__ == "__main__":
    unittest.main()

