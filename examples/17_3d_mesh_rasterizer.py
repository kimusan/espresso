#!/usr/bin/env python3
"""Example 17: 3D Software Rasterizer for OBJ, STL, PLY, and GLB.

Demonstrates:
1. Pure Python software 3D rasterization in terminal cells:
   - 4x4 matrix pipeline: Model, View (LookAt), Perspective Projection, Viewport.
   - Backface culling and sub-pixel Z-buffering (depth buffer).
2. Shading modes:
   - Flat / Lambertian diffuse shading per triangle facet.
   - Gouraud smooth shading via barycentric vertex normal interpolation.
   - Wireframe vector rasterization.
3. Dual-canvas architectures:
   - 24-bit Truecolor Half-block (▀) rendering at 1x2 sub-pixels per character cell.
   - Ultra-high-resolution Unicode Braille (U+2800..U+28FF) at 2x4 sub-pixels per cell.
4. Multi-format model ingestion:
   - OBJ (Wavefront), STL (binary & ASCII), PLY (binary & ASCII), and GLB (glTF 2.0 binary).
   - Procedural primitives: Torus, UV Sphere, Cube, Pyramid, Cylinder.
5. Interactive controls:
   - Mouse click-and-drag to orbit, mouse wheel to zoom.
   - Arrows / H,J,K,L: Orbit camera (yaw and pitch).
   - [/]: Roll camera.
   - +/- or W/S: Zoom in / out.
   - Space: Toggle auto-rotation.
   - M: Cycle shading (Flat -> Gouraud -> Wireframe).
   - C: Toggle canvas (Half-block <-> Braille).
   - 1-6: Switch models.
   - Q: Quit.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, WindowSizeMsg, batch, quit_app
from espresso.beans import (
    CanvasMode,
    MeshData,
    MeshViewer,
    MeshViewerTickMsg,
    ShadingMode,
    Tabs,
    create_cube,
    create_cylinder,
    create_pyramid,
    create_torus,
    create_uv_sphere,
    parse_glb,
    parse_obj,
    parse_ply,
    parse_stl,
)
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.crema import (
    BLOCK_BORDER,
    DOUBLE_BORDER,
    NORMAL_BORDER,
    ROUNDED_BORDER,
    THICK_BORDER,
    Align,
    Border,
    Style,
    join_horizontal,
    join_vertical,
    string_width,
    strip_ansi,
)

# Sample Wavefront OBJ: Low-poly Diamond / Gem
SAMPLE_DIAMOND_OBJ = """
# Low-Poly Diamond
v 0.0 0.8 0.0
v -0.6 0.2 -0.6
v  0.6 0.2 -0.6
v  0.6 0.2  0.6
v -0.6 0.2  0.6
v 0.0 -0.8 0.0
# Top Cap
f 1 2 3
f 1 3 4
f 1 4 5
f 1 5 2
# Bottom Point
f 6 3 2
f 6 4 3
f 6 5 4
f 6 2 5
"""

# Sample ASCII STL: Triangular Prism
SAMPLE_PRISM_STL = """
solid prism
  facet normal 0.0 0.0 1.0
    outer loop
      vertex -0.8 -0.8 0.5
      vertex  0.8 -0.8 0.5
      vertex  0.0  0.8 0.5
    endloop
  endfacet
  facet normal 0.0 0.0 -1.0
    outer loop
      vertex -0.8 -0.8 -0.5
      vertex  0.0  0.8 -0.5
      vertex  0.8 -0.8 -0.5
    endloop
  endfacet
  facet normal 0.0 -1.0 0.0
    outer loop
      vertex -0.8 -0.8 -0.5
      vertex  0.8 -0.8 -0.5
      vertex  0.8 -0.8  0.5
    endloop
  endfacet
  facet normal 0.0 -1.0 0.0
    outer loop
      vertex -0.8 -0.8 -0.5
      vertex  0.8 -0.8  0.5
      vertex -0.8 -0.8  0.5
    endloop
  endfacet
  facet normal -0.89 0.44 0.0
    outer loop
      vertex -0.8 -0.8 -0.5
      vertex -0.8 -0.8  0.5
      vertex  0.0  0.8  0.5
    endloop
  endfacet
  facet normal -0.89 0.44 0.0
    outer loop
      vertex -0.8 -0.8 -0.5
      vertex  0.0  0.8  0.5
      vertex  0.0  0.8 -0.5
    endloop
  endfacet
  facet normal 0.89 0.44 0.0
    outer loop
      vertex  0.8 -0.8 -0.5
      vertex  0.0  0.8 -0.5
      vertex  0.0  0.8  0.5
    endloop
  endfacet
  facet normal 0.89 0.44 0.0
    outer loop
      vertex  0.8 -0.8 -0.5
      vertex  0.0  0.8  0.5
      vertex  0.8 -0.8  0.5
    endloop
  endfacet
endsolid prism
"""


class App3DModel(Model):
    """Interactive application model demonstrating the 3D software rasterizer."""

    def __init__(self, width: int = 84, height: int = 28) -> None:
        self.width = max(60, width)
        self.height = max(20, height)

        # 3D Viewer Bean
        self.viewer = MeshViewer(
            mesh=create_torus(r_major=1.0, r_minor=0.38, seg_major=24, seg_minor=14),
            width=self.width - 28,
            height=self.height - 4,
            shading=ShadingMode.GOURAUD,
            canvas_mode=CanvasMode.HALF_BLOCK,
            auto_spin=True,
            spin_speed=2.2,
            title="3D Rasterizer",
            border=ROUNDED_BORDER,
        )

        # Model Library
        diamond = parse_obj(SAMPLE_DIAMOND_OBJ)
        diamond.name = "Diamond (OBJ)"
        prism = parse_stl(SAMPLE_PRISM_STL)
        prism.name = "Prism (STL)"

        self.models: list[tuple[str, MeshData]] = [
            ("Torus", create_torus(r_major=1.0, r_minor=0.38, seg_major=24, seg_minor=14)),
            ("Sphere", create_uv_sphere(radius=1.0, slices=20, stacks=14)),
            ("Cube", create_cube(1.0)),
            ("Diamond (OBJ)", diamond),
            ("Prism (STL)", prism),
            ("Pyramid", create_pyramid(1.0, 1.2)),
        ]
        self.active_model_idx = 0

        # Tabs
        self.tabs = Tabs(
            titles=[m[0] for m in self.models],
            active_tab=0,
        )

        # Border Cycle
        self.borders = [ROUNDED_BORDER, DOUBLE_BORDER, NORMAL_BORDER, THICK_BORDER, BLOCK_BORDER]
        self.border_idx = 0

    def init(self) -> Cmd | None:
        return self.viewer.init()

    def set_model(self, idx: int) -> None:
        idx = max(0, min(idx, len(self.models) - 1))
        self.active_model_idx = idx
        self.tabs.set_active(idx)
        name, mesh = self.models[idx]
        mesh.name = name
        self.viewer.load_mesh(mesh)

    def update(self, msg: Msg) -> tuple[App3DModel, Cmd | None]:
        if isinstance(msg, WindowSizeMsg):
            self.width = max(60, msg.width)
            self.height = max(20, msg.height)
            self.viewer.width = self.width - 28
            self.viewer.height = self.height - 4
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app
                case "1" | "2" | "3" | "4" | "5" | "6":
                    idx = int(msg.key) - 1
                    if idx < len(self.models):
                        self.set_model(idx)
                    return self, None
                case "tab":
                    next_idx = (self.active_model_idx + 1) % len(self.models)
                    self.set_model(next_idx)
                    return self, None
                case "b":
                    self.border_idx = (self.border_idx + 1) % len(self.borders)
                    self.viewer.border = self.borders[self.border_idx]
                    return self, None

        # Route mouse and keys to the viewer
        self.viewer, cmd = self.viewer.update(msg)
        return self, cmd

    def view(self) -> str:
        # 1. Header with title and model tabs
        title_style = Style().bold(True).foreground("#FF007F")
        header_text = f"☕ {title_style.render('ESPRESSO 3D')} - Pure-Python Software Rasterizer (Half-block & Braille)"
        tab_row = self.tabs.view()

        # 2. Left side: 3D Rasterizer Canvas View
        viewer_view = self.viewer.view()

        # 3. Right side: Info and Control Inspector Panel
        sidebar_w = 26
        sidebar_h = self.viewer.height
        b = ROUNDED_BORDER

        key_col = Style().bold(True).foreground("#00E5FF")
        val_col = Style().bold(True).foreground("#FFD54F")
        dim_col = Style().foreground("#888899")

        shading_name = self.viewer.shading.value.upper()
        canvas_name = self.viewer.canvas_mode.value.upper()
        if self.viewer.canvas_mode == CanvasMode.HALF_BLOCK:
            res_info = "1x2 sub-pixels"
        elif self.viewer.dither:
            res_info = "2x4 Bayer dither"
        else:
            res_info = "2x4 solid ⣿"

        info_lines = [
            f"\x1b[1m\x1b[35m◆ SHADING & CAMERA\x1b[0m",
            f"Mode:    {val_col.render(shading_name)}",
            f"Canvas:  {val_col.render(canvas_name)}",
            f"Grid:    {dim_col.render(res_info)}",
            f"Yaw:     {dim_col.render(f'{int(math.degrees(self.viewer.yaw)) % 360}°')}",
            f"Pitch:   {dim_col.render(f'{int(math.degrees(self.viewer.pitch))}°')}",
            f"Zoom:    {dim_col.render(f'{self.viewer.distance:.1f}x')}",
            f"Triangles: {val_col.render(str(len(self.viewer.mesh.triangles)))}",
            f"Spin:    {'ON ⚡' if self.viewer.auto_spin else 'OFF ⏸'}",
            "",
            f"\x1b[1m\x1b[35m◆ CONTROLS\x1b[0m",
            f"{key_col.render('Space')}  Toggle auto-spin",
            f"{key_col.render('M')}      Cycle shading",
            f"{key_col.render('C')}      Toggle canvas",
            f"{key_col.render('D')}      Toggle dither",
            f"{key_col.render('Arrows')} Orbit camera",
            f"{key_col.render('+ / -')}  Zoom in / out",
            f"{key_col.render('[ / ]')}  Roll view",
            f"{key_col.render('R')}      Reset camera",
            f"{key_col.render('1 - 6')}  Switch model",
            f"{key_col.render('B')}      Cycle border",
            f"{key_col.render('Q')}      Quit",
            "",
            dim_col.render("Drag mouse to orbit"),
            dim_col.render("Scroll wheel to zoom"),
        ]

        # Pad sidebar lines inside border
        inner_sw = sidebar_w - 2
        framed_sidebar = [
            f"{b.top_left}{b.top * 2}\x1b[1m\x1b[36m Inspector \x1b[0m{b.top * (inner_sw - 13)}{b.top_right}"
        ]
        for r in range(sidebar_h - 2):
            if r < len(info_lines):
                l = info_lines[r]
                pad = max(0, inner_sw - string_width(l))
                framed_sidebar.append(f"{b.left}{l}{' ' * pad}{b.right}")
            else:
                framed_sidebar.append(f"{b.left}{' ' * inner_sw}{b.right}")
        framed_sidebar.append(f"{b.bottom_left}{b.bottom * inner_sw}{b.bottom_right}")
        sidebar_view = "\n".join(framed_sidebar)

        # 4. Join horizontal: 3D Rasterizer on left, Inspector on right
        body = join_horizontal(Align.TOP, viewer_view, sidebar_view)

        return join_vertical(Align.LEFT, header_text, tab_row, body)


def main() -> None:
    """Entry point for Example 17: 3D Software Rasterizer."""
    app = App3DModel()
    Program(app, alt_screen=True, mouse=True).run()


if __name__ == "__main__":
    main()
