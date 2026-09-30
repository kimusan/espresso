"""Unit tests for ImageViewer and terminal graphics rendering."""

from __future__ import annotations

import struct
import unittest

from espresso.beans.image import (
    ImageViewer,
    RenderMode,
    parse_bmp,
    parse_ppm,
    rgb_to_ansi_half_block,
    rgb_to_ascii,
    scale_rgb_matrix,
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


if __name__ == "__main__":
    unittest.main()
