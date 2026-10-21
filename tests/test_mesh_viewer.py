"""Unit tests for MeshViewer 3D software rasterizer and mesh loaders."""

from __future__ import annotations

import json
import math
import struct
import unittest

from espresso.beans.mesh_viewer import (
    DEFAULT_MESH_PALETTES,
    CanvasMode,
    Mat4,
    MeshData,
    MeshViewer,
    MeshViewerTickMsg,
    Rasterizer3D,
    ShadingMode,
    Triangle,
    Vec3,
    create_cube,
    create_cylinder,
    create_pyramid,
    create_torus,
    create_uv_sphere,
    emit_braille_canvas,
    emit_half_block_canvas,
    parse_glb,
    parse_obj,
    parse_ply,
    parse_stl,
)
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema.width import string_width, strip_ansi


class TestVectorAndMatrixMath(unittest.TestCase):
    def test_vec3_operations(self) -> None:
        v1 = Vec3(1.0, 2.0, 3.0)
        v2 = Vec3(4.0, 5.0, 6.0)

        # Addition & Subtraction
        self.assertEqual(v1 + v2, Vec3(5.0, 7.0, 9.0))
        self.assertEqual(v2 - v1, Vec3(3.0, 3.0, 3.0))

        # Scalar multiplication & Negation
        self.assertEqual(v1 * 2.0, Vec3(2.0, 4.0, 6.0))
        self.assertEqual(2.0 * v1, Vec3(2.0, 4.0, 6.0))
        self.assertEqual(-v1, Vec3(-1.0, -2.0, -3.0))

        # Dot product
        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        self.assertAlmostEqual(v1.dot(v2), 32.0)

        # Cross product: (2*6 - 3*5, 3*4 - 1*6, 1*5 - 2*4) = (-3, 6, -3)
        cross = v1.cross(v2)
        self.assertAlmostEqual(cross.x, -3.0)
        self.assertAlmostEqual(cross.y, 6.0)
        self.assertAlmostEqual(cross.z, -3.0)

        # Length & Normalization
        v_unit = Vec3(0.0, 3.0, 4.0)
        self.assertAlmostEqual(v_unit.length(), 5.0)
        norm = v_unit.normalize()
        self.assertAlmostEqual(norm.length(), 1.0)
        self.assertAlmostEqual(norm.y, 0.6)
        self.assertAlmostEqual(norm.z, 0.8)

    def test_mat4_transforms(self) -> None:
        # Identity
        ident = Mat4.identity()
        p = Vec3(1.0, 2.0, 3.0)
        self.assertEqual(ident.transform_point(p), p)

        # Translation
        trans = Mat4.translation(5.0, -2.0, 10.0)
        p_trans = trans.transform_point(p)
        self.assertAlmostEqual(p_trans.x, 6.0)
        self.assertAlmostEqual(p_trans.y, 0.0)
        self.assertAlmostEqual(p_trans.z, 13.0)

        # Scale
        sc = Mat4.scale(2.0, 3.0, 4.0)
        p_sc = sc.transform_point(p)
        self.assertAlmostEqual(p_sc.x, 2.0)
        self.assertAlmostEqual(p_sc.y, 6.0)
        self.assertAlmostEqual(p_sc.z, 12.0)

        # Rotation 90 degrees around Z axis (maps (1, 0, 0) to (0, 1, 0))
        rot_z = Mat4.rotation_z(math.pi * 0.5)
        p_x = Vec3(1.0, 0.0, 0.0)
        p_rot = rot_z.transform_point(p_x)
        self.assertAlmostEqual(p_rot.x, 0.0, places=5)
        self.assertAlmostEqual(p_rot.y, 1.0, places=5)
        self.assertAlmostEqual(p_rot.z, 0.0, places=5)

        # Perspective & LookAt
        view = Mat4.look_at(Vec3(0.0, 0.0, 5.0), Vec3(0.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0))
        proj = Mat4.perspective(60.0, 1.0, 0.1, 100.0)
        mvp = proj * view
        p_clip = mvp.transform_vec4(0.0, 0.0, 0.0, 1.0)
        # Point at origin should project into screen center (x=0, y=0)
        self.assertAlmostEqual(p_clip[0], 0.0)
        self.assertAlmostEqual(p_clip[1], 0.0)


class TestProceduralPrimitives(unittest.TestCase):
    def test_primitives_generation(self) -> None:
        cube = create_cube(1.0)
        self.assertEqual(len(cube.vertices), 8)
        self.assertEqual(len(cube.triangles), 12)
        self.assertEqual(len(cube.normals), 8)

        sphere = create_uv_sphere(radius=1.0, slices=8, stacks=6)
        self.assertGreater(len(sphere.vertices), 20)
        self.assertGreater(len(sphere.triangles), 30)

        torus = create_torus(r_major=1.0, r_minor=0.3, seg_major=8, seg_minor=6)
        self.assertEqual(len(torus.vertices), 8 * 6)
        self.assertEqual(len(torus.triangles), 8 * 6 * 2)

        pyramid = create_pyramid(1.0, 1.0)
        self.assertEqual(len(pyramid.vertices), 5)
        self.assertEqual(len(pyramid.triangles), 6)  # 2 base + 4 sides

        cylinder = create_cylinder(1.0, 1.0, segments=8)
        self.assertGreater(len(cylinder.vertices), 16)
        self.assertGreater(len(cylinder.triangles), 16)


class TestMeshLoaders(unittest.TestCase):
    def test_parse_obj(self) -> None:
        obj_text = """
        # Simple Triangle OBJ
        v 0.0 0.0 0.0
        v 1.0 0.0 0.0
        v 0.0 1.0 0.0
        vn 0.0 0.0 1.0
        f 1//1 2//1 3//1
        """
        mesh = parse_obj(obj_text)
        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(len(mesh.triangles), 1)
        self.assertEqual(mesh.triangles[0].v0, 0)
        self.assertEqual(mesh.triangles[0].v1, 1)
        self.assertEqual(mesh.triangles[0].v2, 2)

        # Quad with fan triangulation
        quad_text = """
        v -1 -1 0
        v  1 -1 0
        v  1  1 0
        v -1  1 0
        f 1 2 3 4
        """
        mesh_quad = parse_obj(quad_text)
        self.assertEqual(len(mesh_quad.vertices), 4)
        self.assertEqual(len(mesh_quad.triangles), 2)

        # Negative indexing support
        neg_text = """
        v 0 0 0
        v 1 0 0
        v 0 1 0
        f -3 -2 -1
        """
        mesh_neg = parse_obj(neg_text)
        self.assertEqual(len(mesh_neg.triangles), 1)
        self.assertEqual(mesh_neg.triangles[0].v0, 0)

    def test_parse_stl_ascii(self) -> None:
        stl_ascii = """
        solid test_triangle
          facet normal 0.0 0.0 1.0
            outer loop
              vertex 0.0 0.0 0.0
              vertex 1.0 0.0 0.0
              vertex 0.0 1.0 0.0
            endloop
          endfacet
        endsolid test_triangle
        """
        mesh = parse_stl(stl_ascii)
        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(len(mesh.triangles), 1)

    def test_parse_stl_binary(self) -> None:
        # Binary STL: 80 bytes header + uint32 tri_count + 50 bytes per triangle
        header = b"\x00" * 80
        tri_count = 1
        tri_data = struct.pack(
            "<12fH",
            0.0, 0.0, 1.0,  # normal
            0.0, 0.0, 0.0,  # v0
            1.0, 0.0, 0.0,  # v1
            0.0, 1.0, 0.0,  # v2
            0,              # attr byte count
        )
        stl_bytes = header + struct.pack("<I", tri_count) + tri_data
        mesh = parse_stl(stl_bytes)
        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(len(mesh.triangles), 1)

    def test_parse_ply_ascii(self) -> None:
        ply_ascii = """ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
element face 1
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
0 1 0
3 0 1 2
"""
        mesh = parse_ply(ply_ascii)
        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(len(mesh.triangles), 1)
        self.assertEqual(mesh.triangles[0].v0, 0)
        self.assertEqual(mesh.triangles[0].v1, 1)
        self.assertEqual(mesh.triangles[0].v2, 2)

    def test_parse_ply_binary(self) -> None:
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            "element vertex 3\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "element face 1\n"
            "property list uchar int vertex_indices\n"
            "end_header\n"
        ).encode("ascii")

        verts_data = struct.pack(
            "<9f",
            0.0, 0.0, 0.0,
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
        )
        face_data = struct.pack("<B3i", 3, 0, 1, 2)
        ply_bytes = header + verts_data + face_data

        mesh = parse_ply(ply_bytes)
        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(len(mesh.triangles), 1)

    def test_parse_glb(self) -> None:
        # Construct a minimal valid glTF 2.0 binary container with 1 triangle
        pos_bytes = struct.pack(
            "<9f",
            -0.5, -0.5, 0.0,
             0.5, -0.5, 0.0,
             0.0,  0.5, 0.0,
        )
        idx_bytes = struct.pack("<3H", 0, 1, 2)
        bin_payload = pos_bytes + idx_bytes

        json_meta = {
            "asset": {"version": "2.0"},
            "buffers": [{"byteLength": len(bin_payload)}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes)},
                {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(idx_bytes)},
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "byteOffset": 0,
                    "componentType": 5126,  # FLOAT
                    "count": 3,
                    "type": "VEC3",
                },
                {
                    "bufferView": 1,
                    "byteOffset": 0,
                    "componentType": 5123,  # UNSIGNED_SHORT
                    "count": 3,
                    "type": "SCALAR",
                },
            ],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {"POSITION": 0},
                            "indices": 1,
                        }
                    ]
                }
            ],
        }
        json_bytes = json.dumps(json_meta).encode("utf-8")
        # Pad JSON to 4-byte boundary
        pad_len = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b" " * pad_len

        chunk0_header = struct.pack("<I4s", len(json_bytes), b"JSON")
        chunk1_header = struct.pack("<I4s", len(bin_payload), b"BIN\x00")
        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_payload)
        glb_header = struct.pack("<4sII", b"glTF", 2, total_len)

        glb_data = glb_header + chunk0_header + json_bytes + chunk1_header + bin_payload
        mesh = parse_glb(glb_data)

        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(len(mesh.triangles), 1)
        self.assertEqual(mesh.triangles[0].v0, 0)
        self.assertEqual(mesh.triangles[0].v1, 1)
        self.assertEqual(mesh.triangles[0].v2, 2)


class TestRasterizerAndCanvas(unittest.TestCase):
    def test_rasterizer_flat_and_gouraud(self) -> None:
        cube = create_cube(1.0)
        view = Mat4.look_at(Vec3(0.0, 0.0, 3.0), Vec3(0.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0))
        proj = Mat4.perspective(50.0, 1.0, 0.1, 10.0)
        mvp = proj * view

        # Flat Shading
        r_flat = Rasterizer3D(pixel_width=40, pixel_height=40)
        r_flat.render_mesh(cube, mvp, ShadingMode.FLAT)
        # Should have rasterized colored pixels in the center
        active_pixels = sum(1 for c in r_flat.color_buffer if c is not None)
        self.assertGreater(active_pixels, 50)

        # Gouraud Shading
        r_gouraud = Rasterizer3D(pixel_width=40, pixel_height=40)
        r_gouraud.render_mesh(cube, mvp, ShadingMode.GOURAUD)
        active_gouraud = sum(1 for c in r_gouraud.color_buffer if c is not None)
        self.assertGreater(active_gouraud, 50)

        # Wireframe
        r_wire = Rasterizer3D(pixel_width=40, pixel_height=40)
        r_wire.render_mesh(cube, mvp, ShadingMode.WIREFRAME)
        active_wire = sum(1 for c in r_wire.color_buffer if c is not None)
        self.assertGreater(active_wire, 10)

    def test_canvas_emitters(self) -> None:
        colors = [(255, 0, 0) if i % 2 == 0 else None for i in range(16 * 16)]
        half_block_lines = emit_half_block_canvas(colors, 16, 16)
        self.assertEqual(len(half_block_lines), 8)
        self.assertTrue(any("▀" in l for l in half_block_lines))

        braille_lines = emit_braille_canvas(colors, 16, 16, is_wireframe=False)
        self.assertEqual(len(braille_lines), 4)
        # Check that Braille characters (>= 0x2800) are emitted
        has_braille = any(any(ord(ch) >= 0x2800 for ch in l) for l in braille_lines)
        self.assertTrue(has_braille)

    def test_braille_solid_surface_rendering(self) -> None:
        """Verify that solid surfaces emit fully-dotted Braille ⣿ characters in default mode."""
        # 2x4 subpixels = 1 terminal character cell, all filled with red
        red = (255, 0, 0)
        solid_cell = [red] * 8
        lines = emit_braille_canvas(solid_cell, pixel_width=2, pixel_height=4, is_wireframe=False, dither=False)
        self.assertEqual(len(lines), 1)
        # Should contain fully dotted character ⣿ (U+28FF)
        self.assertIn("⣿", lines[0])

        # Dither mode test: dark color with Bayer dither drops dots
        dark_purple = (27, 18, 53)
        dark_cell = [dark_purple] * 8
        dithered_lines = emit_braille_canvas(dark_cell, pixel_width=2, pixel_height=4, is_wireframe=False, dither=True)
        self.assertEqual(len(dithered_lines), 1)
        # In dither mode with dark color, ⣿ should NOT be emitted
        self.assertNotIn("⣿", dithered_lines[0])

    def test_half_block_silhouette_rendering(self) -> None:
        """Verify that bottom-pixel-only cells emit ▄ without default foreground white blocks."""
        # 4 pixels width, 2 pixels height (1 terminal row)
        # Pixel 0: top colored, bot empty -> ▀ with FG
        # Pixel 1: top empty, bot colored -> ▄ with FG (not default FG ▀)
        # Pixel 2: both colored -> ▀ with FG and BG
        # Pixel 3: both empty -> space
        red = (255, 0, 0)
        green = (0, 255, 0)
        color_buf: list[tuple[int, int, int] | None] = [
            red,  None, red,   None,  # top row (y=0)
            None, green, green, None,  # bot row (y=1)
        ]
        lines = emit_half_block_canvas(color_buf, pixel_width=4, pixel_height=2)
        self.assertEqual(len(lines), 1)
        row_str = lines[0]

        # Must not contain default FG reset immediately followed by ▀ (\x1b[39m▀)
        self.assertNotIn("\x1b[39m▀", row_str)
        # Must contain ▀ for top-only and both-colored
        self.assertIn("▀", row_str)
        # Must contain ▄ for bottom-only
        self.assertIn("▄", row_str)
        # The green color (0, 255, 0) should be applied as foreground for ▄
        self.assertIn("38;2;0;255;0m▄", row_str)


class TestMeshViewerComponent(unittest.TestCase):
    def test_initial_state_and_view(self) -> None:
        viewer = MeshViewer(width=50, height=18)
        self.assertTrue(viewer.auto_spin)
        self.assertIsNotNone(viewer.init())

        rendered = viewer.view()
        self.assertIn("3D Mesh Viewer", rendered)
        self.assertIn("tris", rendered)
        # Width should match framed terminal width
        lines = rendered.splitlines()
        self.assertEqual(len(lines), 18)
        self.assertEqual(string_width(lines[0]), 50)

    def test_keyboard_controls(self) -> None:
        viewer = MeshViewer(width=40, height=14)

        # Toggle shading mode ('m')
        self.assertEqual(viewer.shading, ShadingMode.GOURAUD)
        viewer, _ = viewer.update(KeyMsg("m"))
        self.assertEqual(viewer.shading, ShadingMode.WIREFRAME)
        viewer, _ = viewer.update(KeyMsg("m"))
        self.assertEqual(viewer.shading, ShadingMode.FLAT)

        # Toggle canvas mode ('c')
        self.assertEqual(viewer.canvas_mode, CanvasMode.HALF_BLOCK)
        viewer, _ = viewer.update(KeyMsg("c"))
        self.assertEqual(viewer.canvas_mode, CanvasMode.BRAILLE)
        viewer, _ = viewer.update(KeyMsg("c"))
        self.assertEqual(viewer.canvas_mode, CanvasMode.HALF_BLOCK)

        # Toggle auto-spin ('space')
        self.assertTrue(viewer.auto_spin)
        viewer, _ = viewer.update(KeyMsg("space"))
        self.assertFalse(viewer.auto_spin)

        # Toggle dither mode ('d')
        self.assertFalse(viewer.dither)
        viewer, _ = viewer.update(KeyMsg("d"))
        self.assertTrue(viewer.dither)
        viewer, _ = viewer.update(KeyMsg("d"))
        self.assertFalse(viewer.dither)

        # Toggle color palette ('p')
        self.assertEqual(viewer.color_name, "Purple")
        viewer, _ = viewer.update(KeyMsg("p"))
        self.assertEqual(viewer.color_name, "Cyan")
        viewer, _ = viewer.update(KeyMsg("p"))
        self.assertEqual(viewer.color_name, "Emerald")

        # Orbit and Zoom keys
        old_yaw = viewer.yaw
        viewer, _ = viewer.update(KeyMsg("right"))
        self.assertGreater(viewer.yaw, old_yaw)

        old_dist = viewer.distance
        viewer, _ = viewer.update(KeyMsg("-"))
        self.assertGreater(viewer.distance, old_dist)

        viewer, _ = viewer.update(KeyMsg("r"))
        self.assertEqual(viewer.distance, 2.6)

        # Switch primitives ('1'-'5')
        viewer, _ = viewer.update(KeyMsg("3"))
        self.assertEqual(viewer.mesh.name, "Cube")

    def test_mouse_controls(self) -> None:
        viewer = MeshViewer(width=40, height=14)
        old_dist = viewer.distance

        # Mouse wheel zoom
        viewer, _ = viewer.update(MouseMsg(x=10, y=5, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
        self.assertLess(viewer.distance, old_dist)

        # Mouse drag orbit
        viewer, _ = viewer.update(MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertTrue(viewer.is_dragging)
        viewer, _ = viewer.update(MouseMsg(x=15, y=8, button=MouseButton.LEFT, action=MouseAction.MOTION))
        self.assertNotEqual(viewer.yaw, 0.65)
        viewer, _ = viewer.update(MouseMsg(x=15, y=8, button=MouseButton.LEFT, action=MouseAction.RELEASE))
        self.assertFalse(viewer.is_dragging)

    def test_auto_spin_ticker(self) -> None:
        viewer = MeshViewer(width=40, height=14, auto_spin=True)
        old_yaw = viewer.yaw
        viewer, cmd = viewer.update(MeshViewerTickMsg(tag=viewer.tag))
        self.assertGreater(viewer.yaw, old_yaw)
        self.assertIsNotNone(cmd)

    def test_color_palettes_and_custom_color(self) -> None:
        # Default palette initialization
        viewer = MeshViewer(width=40, height=14)
        self.assertEqual(viewer.color_name, "Purple")
        self.assertEqual(viewer.base_color, (145, 105, 255))

        # Cycle through all default palettes and verify wrap-around
        total_presets = len(DEFAULT_MESH_PALETTES)
        for i in range(1, total_presets):
            expected_name, expected_rgb = DEFAULT_MESH_PALETTES[i]
            col = viewer.cycle_color()
            self.assertEqual(col, expected_rgb)
            self.assertEqual(viewer.color_name, expected_name)
            self.assertEqual(viewer.base_color, expected_rgb)

        # One more cycle should wrap back to Purple (index 0)
        viewer.cycle_color()
        self.assertEqual(viewer.color_name, "Purple")
        self.assertEqual(viewer.base_color, (145, 105, 255))

        # Test set_color with an existing preset color
        viewer.set_color((0, 235, 255))  # Cyan
        self.assertEqual(viewer.color_name, "Cyan")
        self.assertEqual(viewer.base_color, (0, 235, 255))

        # Test set_color with a custom RGB color
        viewer.set_color((250, 120, 20), name="Tangerine")
        self.assertEqual(viewer.color_name, "Tangerine")
        self.assertEqual(viewer.base_color, (250, 120, 20))

        # Test custom base_color in __init__
        custom_viewer = MeshViewer(width=40, height=14, base_color=(10, 20, 30))
        self.assertEqual(custom_viewer.color_name, "Custom")
        self.assertEqual(custom_viewer.base_color, (10, 20, 30))
        self.assertEqual(custom_viewer.palette_idx, 0)
        # Cycling should move to the first built-in palette (Purple)
        custom_viewer.cycle_color()
        self.assertEqual(custom_viewer.color_name, "Purple")


if __name__ == "__main__":
    unittest.main()
