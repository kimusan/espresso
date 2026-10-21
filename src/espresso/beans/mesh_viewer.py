"""Software 3D mesh rasterizer bean supporting OBJ, STL, PLY, and GLB formats.

Renders 3D geometry directly inside terminal cells with:
- Shading: Flat (Lambertian diffuse) and Gouraud (smooth barycentric normal interpolation)
- Canvas Modes:
  * Half-block (▀): 24-bit RGB truecolor at 1x2 sub-pixels per cell
  * Braille (U+2800..U+28FF): 2x4 sub-pixels per cell for ultra-high-definition wireframes and dithered surfaces
- Pure Python parsers for Wavefront OBJ, Stereolithography STL (binary & ASCII),
  Stanford PLY (binary & ASCII), and glTF 2.0 Binary (GLB) with zero external dependencies
- Procedural primitives: Cube, UV Sphere, Torus, Pyramid, Cylinder
- 4x4 matrix pipeline: Model, View (LookAt), Perspective Projection, Viewport,
  Backface Culling, and Z-buffering (depth buffer)
- TEA Model integration: Key/Mouse camera orbit, zoom, roll, auto-spin ticker, and Crema framing
"""

from __future__ import annotations

import asyncio
import json
import math
import struct
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Sequence, Union

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER, Border
from espresso.crema.color import Color
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, strip_ansi


# =============================================================================
# 3D Vector & Matrix Mathematics
# =============================================================================

@dataclass
class Vec3:
    """3D floating point vector."""

    x: float
    y: float
    z: float

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vec3:
        return self.__mul__(scalar)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> Vec3:
        mag = self.length()
        if mag > 1e-9:
            inv = 1.0 / mag
            return Vec3(self.x * inv, self.y * inv, self.z * inv)
        return Vec3(0.0, 1.0, 0.0)

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


class Mat4:
    """4x4 row-major transformation matrix."""

    def __init__(self, data: Sequence[float] | None = None) -> None:
        if data is not None and len(data) == 16:
            self.m = list(data)
        else:
            # Identity matrix
            self.m = [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ]

    @classmethod
    def identity(cls) -> Mat4:
        return cls()

    def __mul__(self, other: Mat4) -> Mat4:
        a = self.m
        b = other.m
        res = [0.0] * 16
        for row in range(4):
            r_idx = row * 4
            for col in range(4):
                res[r_idx + col] = (
                    a[r_idx + 0] * b[0 * 4 + col]
                    + a[r_idx + 1] * b[1 * 4 + col]
                    + a[r_idx + 2] * b[2 * 4 + col]
                    + a[r_idx + 3] * b[3 * 4 + col]
                )
        return Mat4(res)

    @classmethod
    def translation(cls, tx: float, ty: float, tz: float) -> Mat4:
        return cls([
            1.0, 0.0, 0.0, tx,
            0.0, 1.0, 0.0, ty,
            0.0, 0.0, 1.0, tz,
            0.0, 0.0, 0.0, 1.0,
        ])

    @classmethod
    def scale(cls, sx: float, sy: float, sz: float) -> Mat4:
        return cls([
            sx,  0.0, 0.0, 0.0,
            0.0, sy,  0.0, 0.0,
            0.0, 0.0, sz,  0.0,
            0.0, 0.0, 0.0, 1.0,
        ])

    @classmethod
    def rotation_x(cls, rad: float) -> Mat4:
        c = math.cos(rad)
        s = math.sin(rad)
        return cls([
            1.0, 0.0,  0.0, 0.0,
            0.0,   c,   -s, 0.0,
            0.0,   s,    c, 0.0,
            0.0, 0.0,  0.0, 1.0,
        ])

    @classmethod
    def rotation_y(cls, rad: float) -> Mat4:
        c = math.cos(rad)
        s = math.sin(rad)
        return cls([
              c, 0.0,   s, 0.0,
            0.0, 1.0, 0.0, 0.0,
             -s, 0.0,   c, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ])

    @classmethod
    def rotation_z(cls, rad: float) -> Mat4:
        c = math.cos(rad)
        s = math.sin(rad)
        return cls([
              c,  -s, 0.0, 0.0,
              s,   c, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ])

    @classmethod
    def look_at(cls, eye: Vec3, target: Vec3, up: Vec3) -> Mat4:
        """Create a right-handed LookAt view matrix."""
        z_axis = (eye - target).normalize()
        x_axis = up.cross(z_axis).normalize()
        y_axis = z_axis.cross(x_axis).normalize()

        return cls([
            x_axis.x, x_axis.y, x_axis.z, -x_axis.dot(eye),
            y_axis.x, y_axis.y, y_axis.z, -y_axis.dot(eye),
            z_axis.x, z_axis.y, z_axis.z, -z_axis.dot(eye),
            0.0,      0.0,      0.0,      1.0,
        ])

    @classmethod
    def perspective(cls, fov_deg: float, aspect: float, near: float, far: float) -> Mat4:
        """Create a perspective projection matrix mapping into NDC [-1, 1]."""
        f = 1.0 / math.tan(math.radians(fov_deg) * 0.5)
        range_inv = 1.0 / (near - far)

        return cls([
            f / aspect, 0.0, 0.0,                       0.0,
            0.0,        f,   0.0,                       0.0,
            0.0,        0.0, (near + far) * range_inv, 2.0 * near * far * range_inv,
            0.0,        0.0, -1.0,                      0.0,
        ])

    def transform_vec4(self, x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
        m = self.m
        ox = m[0] * x + m[1] * y + m[2] * z + m[3] * w
        oy = m[4] * x + m[5] * y + m[6] * z + m[7] * w
        oz = m[8] * x + m[9] * y + m[10] * z + m[11] * w
        ow = m[12] * x + m[13] * y + m[14] * z + m[15] * w
        return (ox, oy, oz, ow)

    def transform_point(self, v: Vec3) -> Vec3:
        ox, oy, oz, ow = self.transform_vec4(v.x, v.y, v.z, 1.0)
        if abs(ow) > 1e-9 and abs(ow - 1.0) > 1e-9:
            inv = 1.0 / ow
            return Vec3(ox * inv, oy * inv, oz * inv)
        return Vec3(ox, oy, oz)

    def transform_direction(self, v: Vec3) -> Vec3:
        m = self.m
        return Vec3(
            m[0] * v.x + m[1] * v.y + m[2] * v.z,
            m[4] * v.x + m[5] * v.y + m[6] * v.z,
            m[8] * v.x + m[9] * v.y + m[10] * v.z,
        )


# =============================================================================
# Mesh Representation & Normal Calculations
# =============================================================================

@dataclass
class Triangle:
    """A triangle face with 3 vertex indices and optional normal indices."""

    v0: int
    v1: int
    v2: int
    n0: int = -1
    n1: int = -1
    n2: int = -1
    face_normal: Vec3 = field(default_factory=lambda: Vec3(0.0, 1.0, 0.0))


@dataclass
class MeshData:
    """Parsed or procedurally generated 3D polygonal mesh."""

    name: str = "Mesh"
    vertices: list[Vec3] = field(default_factory=list)
    normals: list[Vec3] = field(default_factory=list)
    triangles: list[Triangle] = field(default_factory=list)

    def compute_normals(self) -> None:
        """Compute face normals and smooth vertex normals if omitted in source data."""
        # Compute face normals
        for tri in self.triangles:
            if 0 <= tri.v0 < len(self.vertices) and 0 <= tri.v1 < len(self.vertices) and 0 <= tri.v2 < len(self.vertices):
                v0 = self.vertices[tri.v0]
                v1 = self.vertices[tri.v1]
                v2 = self.vertices[tri.v2]
                fn = (v1 - v0).cross(v2 - v0).normalize()
                tri.face_normal = fn

        # If vertex normals are missing, accumulate face normals to vertices
        if not self.normals or len(self.normals) < len(self.vertices):
            accum = [Vec3(0.0, 0.0, 0.0) for _ in self.vertices]
            for tri in self.triangles:
                fn = tri.face_normal
                accum[tri.v0] = accum[tri.v0] + fn
                accum[tri.v1] = accum[tri.v1] + fn
                accum[tri.v2] = accum[tri.v2] + fn

            self.normals = [n.normalize() for n in accum]
            for tri in self.triangles:
                tri.n0 = tri.v0
                tri.n1 = tri.v1
                tri.n2 = tri.v2

    def center_and_scale(self, target_radius: float = 1.0) -> None:
        """Center the mesh around (0, 0, 0) and uniformly scale it into a normalized bounding sphere."""
        if not self.vertices:
            return

        min_x = min(v.x for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        max_y = max(v.y for v in self.vertices)
        min_z = min(v.z for v in self.vertices)
        max_z = max(v.z for v in self.vertices)

        cx = (min_x + max_x) * 0.5
        cy = (min_y + max_y) * 0.5
        cz = (min_z + max_z) * 0.5

        max_span = max(max_x - min_x, max_y - min_y, max_z - min_z)
        scale = (target_radius * 2.0 / max_span) if max_span > 1e-9 else 1.0

        scaled_vertices: list[Vec3] = []
        for v in self.vertices:
            scaled_vertices.append(Vec3(
                (v.x - cx) * scale,
                (v.y - cy) * scale,
                (v.z - cz) * scale,
            ))
        self.vertices = scaled_vertices


# =============================================================================
# Procedural Primitive Generators
# =============================================================================

def create_cube(size: float = 1.0) -> MeshData:
    """Generate a 6-sided, 12-triangle cube centered at the origin."""
    s = size * 0.5
    verts = [
        Vec3(-s, -s,  s),  # 0
        Vec3( s, -s,  s),  # 1
        Vec3( s,  s,  s),  # 2
        Vec3(-s,  s,  s),  # 3
        Vec3(-s, -s, -s),  # 4
        Vec3( s, -s, -s),  # 5
        Vec3( s,  s, -s),  # 6
        Vec3(-s,  s, -s),  # 7
    ]

    # Front, Back, Left, Right, Top, Bottom
    face_indices = [
        (0, 1, 2), (0, 2, 3),  # Front (+Z)
        (5, 4, 7), (5, 7, 6),  # Back (-Z)
        (4, 0, 3), (4, 3, 7),  # Left (-X)
        (1, 5, 6), (1, 6, 2),  # Right (+X)
        (3, 2, 6), (3, 6, 7),  # Top (+Y)
        (4, 5, 1), (4, 1, 0),  # Bottom (-Y)
    ]

    triangles = [Triangle(v0=f[0], v1=f[1], v2=f[2]) for f in face_indices]
    mesh = MeshData(name="Cube", vertices=verts, triangles=triangles)
    mesh.compute_normals()
    return mesh


def create_pyramid(base_size: float = 1.0, height: float = 1.2) -> MeshData:
    """Generate a 4-sided pyramid with a square base centered at the origin."""
    b = base_size * 0.5
    h = height * 0.5
    verts = [
        Vec3(-b, -h, -b),  # 0: base bottom-left
        Vec3( b, -h, -b),  # 1: base bottom-right
        Vec3( b, -h,  b),  # 2: base top-right
        Vec3(-b, -h,  b),  # 3: base top-left
        Vec3(0.0, h, 0.0), # 4: apex
    ]

    face_indices = [
        (0, 2, 1), (0, 3, 2),  # Base
        (0, 1, 4),             # Front
        (1, 2, 4),             # Right
        (2, 3, 4),             # Back
        (3, 0, 4),             # Left
    ]

    triangles = [Triangle(v0=f[0], v1=f[1], v2=f[2]) for f in face_indices]
    mesh = MeshData(name="Pyramid", vertices=verts, triangles=triangles)
    mesh.compute_normals()
    return mesh


def create_uv_sphere(radius: float = 1.0, slices: int = 16, stacks: int = 12) -> MeshData:
    """Generate a smooth UV sphere with slices (longitude) and stacks (latitude)."""
    verts: list[Vec3] = []
    triangles: list[Triangle] = []

    for i in range(stacks + 1):
        phi = math.pi * i / stacks
        y = radius * math.cos(phi)
        r = radius * math.sin(phi)

        for j in range(slices):
            theta = 2.0 * math.pi * j / slices
            x = r * math.sin(theta)
            z = r * math.cos(theta)
            verts.append(Vec3(x, y, z))

    for i in range(stacks):
        for j in range(slices):
            next_j = (j + 1) % slices
            p0 = i * slices + j
            p1 = i * slices + next_j
            p2 = (i + 1) * slices + j
            p3 = (i + 1) * slices + next_j

            if i > 0:
                triangles.append(Triangle(v0=p0, v1=p2, v2=p1))
            if i < stacks - 1:
                triangles.append(Triangle(v0=p1, v1=p2, v2=p3))

    mesh = MeshData(name="Sphere", vertices=verts, triangles=triangles)
    mesh.compute_normals()
    return mesh


def create_torus(
    r_major: float = 1.0,
    r_minor: float = 0.35,
    seg_major: int = 18,
    seg_minor: int = 12,
) -> MeshData:
    """Generate a donut-shaped 3D torus with major and minor radii."""
    verts: list[Vec3] = []
    triangles: list[Triangle] = []

    for i in range(seg_major):
        u = 2.0 * math.pi * i / seg_major
        cos_u = math.cos(u)
        sin_u = math.sin(u)

        for j in range(seg_minor):
            v = 2.0 * math.pi * j / seg_minor
            cos_v = math.cos(v)
            sin_v = math.sin(v)

            x = (r_major + r_minor * cos_v) * cos_u
            y = r_minor * sin_v
            z = (r_major + r_minor * cos_v) * sin_u
            verts.append(Vec3(x, y, z))

    for i in range(seg_major):
        next_i = (i + 1) % seg_major
        for j in range(seg_minor):
            next_j = (j + 1) % seg_minor
            p0 = i * seg_minor + j
            p1 = next_i * seg_minor + j
            p2 = next_i * seg_minor + next_j
            p3 = i * seg_minor + next_j

            triangles.append(Triangle(v0=p0, v1=p1, v2=p2))
            triangles.append(Triangle(v0=p0, v1=p2, v2=p3))

    mesh = MeshData(name="Torus", vertices=verts, triangles=triangles)
    mesh.compute_normals()
    return mesh


def create_cylinder(radius: float = 1.0, height: float = 1.6, segments: int = 16) -> MeshData:
    """Generate a closed 3D cylinder with top and bottom caps."""
    verts: list[Vec3] = []
    triangles: list[Triangle] = []
    h = height * 0.5

    # Top center (0) and bottom center (1)
    verts.append(Vec3(0.0,  h, 0.0))
    verts.append(Vec3(0.0, -h, 0.0))

    # Top ring: indices 2 to 2 + segments - 1
    # Bottom ring: indices 2 + segments to 2 + 2*segments - 1
    for i in range(segments):
        th = 2.0 * math.pi * i / segments
        x = radius * math.cos(th)
        z = radius * math.sin(th)
        verts.append(Vec3(x,  h, z))
        verts.append(Vec3(x, -h, z))

    for i in range(segments):
        next_i = (i + 1) % segments
        top_curr = 2 + i * 2
        bot_curr = 3 + i * 2
        top_next = 2 + next_i * 2
        bot_next = 3 + next_i * 2

        # Side quad
        triangles.append(Triangle(v0=top_curr, v1=bot_curr, v2=bot_next))
        triangles.append(Triangle(v0=top_curr, v1=bot_next, v2=top_next))

        # Top cap
        triangles.append(Triangle(v0=0, v1=top_curr, v2=top_next))
        # Bottom cap
        triangles.append(Triangle(v0=1, v1=bot_next, v2=bot_curr))

    mesh = MeshData(name="Cylinder", vertices=verts, triangles=triangles)
    mesh.compute_normals()
    return mesh


# =============================================================================
# Pure Python Mesh Loaders (OBJ, STL, PLY, GLB)
# =============================================================================

def parse_obj(content_or_path: str | Path) -> MeshData:
    """Parse Wavefront OBJ data into a MeshData structure."""
    if isinstance(content_or_path, Path) or (isinstance(content_or_path, str) and "\n" not in content_or_path and Path(content_or_path).is_file()):
        raw_text = Path(content_or_path).read_text(encoding="utf-8", errors="replace")
    else:
        raw_text = str(content_or_path)

    vertices: list[Vec3] = []
    normals: list[Vec3] = []
    triangles: list[Triangle] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        tag = parts[0]

        if tag == "v" and len(parts) >= 4:
            vertices.append(Vec3(float(parts[1]), float(parts[2]), float(parts[3])))

        elif tag == "vn" and len(parts) >= 4:
            normals.append(Vec3(float(parts[1]), float(parts[2]), float(parts[3])).normalize())

        elif tag == "f" and len(parts) >= 4:
            # Face vertices can be formatted as v, v/vt, v//vn, or v/vt/vn
            face_verts: list[tuple[int, int]] = []
            for token in parts[1:]:
                sub = token.split("/")
                # OBJ indices are 1-based, can be negative
                v_idx = int(sub[0])
                v_idx = v_idx - 1 if v_idx > 0 else len(vertices) + v_idx

                n_idx = -1
                if len(sub) >= 3 and sub[2]:
                    n_idx = int(sub[2])
                    n_idx = n_idx - 1 if n_idx > 0 else len(normals) + n_idx

                face_verts.append((v_idx, n_idx))

            # Fan triangulation for quads and n-gons
            for i in range(1, len(face_verts) - 1):
                v0, n0 = face_verts[0]
                v1, n1 = face_verts[i]
                v2, n2 = face_verts[i + 1]
                triangles.append(Triangle(v0=v0, v1=v1, v2=v2, n0=n0, n1=n1, n2=n2))

    mesh = MeshData(name="OBJ Model", vertices=vertices, normals=normals, triangles=triangles)
    mesh.compute_normals()
    return mesh


def parse_stl(content_or_path: bytes | str | Path) -> MeshData:
    """Parse Stereolithography STL (binary or ASCII) data into MeshData."""
    raw_bytes: bytes
    if isinstance(content_or_path, Path) or (isinstance(content_or_path, str) and "\n" not in content_or_path and Path(content_or_path).is_file()):
        raw_bytes = Path(content_or_path).read_bytes()
    elif isinstance(content_or_path, str):
        raw_bytes = content_or_path.encode("utf-8")
    else:
        raw_bytes = content_or_path

    # Check for ASCII STL
    is_ascii = False
    if raw_bytes.strip().startswith(b"solid"):
        # Could still be binary if 80-byte header starts with 'solid'
        # Check if contains b"facet normal"
        if b"facet" in raw_bytes[:1000]:
            is_ascii = True

    if is_ascii:
        return _parse_stl_ascii(raw_bytes.decode("utf-8", errors="replace"))
    else:
        return _parse_stl_binary(raw_bytes)


def _parse_stl_ascii(text: str) -> MeshData:
    vertices: list[Vec3] = []
    triangles: list[Triangle] = []
    current_tri_verts: list[int] = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            parts = line.split()
            if len(parts) >= 4:
                idx = len(vertices)
                vertices.append(Vec3(float(parts[1]), float(parts[2]), float(parts[3])))
                current_tri_verts.append(idx)
                if len(current_tri_verts) == 3:
                    triangles.append(Triangle(v0=current_tri_verts[0], v1=current_tri_verts[1], v2=current_tri_verts[2]))
                    current_tri_verts = []

    mesh = MeshData(name="STL ASCII", vertices=vertices, triangles=triangles)
    mesh.compute_normals()
    return mesh


def _parse_stl_binary(data: bytes) -> MeshData:
    if len(data) < 84:
        return MeshData(name="Empty STL")

    tri_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + tri_count * 50
    if len(data) < expected_size:
        # File might be truncated, parse available triangles
        tri_count = (len(data) - 84) // 50

    vertices: list[Vec3] = []
    triangles: list[Triangle] = []
    offset = 84

    for _ in range(tri_count):
        # 12 floats: nx, ny, nz, x1, y1, z1, x2, y2, z2, x3, y3, z3, uint16 attr
        vals = struct.unpack_from("<12f", data, offset)
        offset += 50

        fn = Vec3(vals[0], vals[1], vals[2]).normalize()
        v0 = Vec3(vals[3], vals[4], vals[5])
        v1 = Vec3(vals[6], vals[7], vals[8])
        v2 = Vec3(vals[9], vals[10], vals[11])

        base_idx = len(vertices)
        vertices.extend([v0, v1, v2])
        triangles.append(Triangle(v0=base_idx, v1=base_idx + 1, v2=base_idx + 2, face_normal=fn))

    mesh = MeshData(name="STL Binary", vertices=vertices, triangles=triangles)
    mesh.compute_normals()
    return mesh


def parse_ply(content_or_path: bytes | str | Path) -> MeshData:
    """Parse Stanford Triangle PLY (binary little-endian or ASCII) into MeshData."""
    raw_bytes: bytes
    if isinstance(content_or_path, Path) or (isinstance(content_or_path, str) and "\n" not in content_or_path and Path(content_or_path).is_file()):
        raw_bytes = Path(content_or_path).read_bytes()
    elif isinstance(content_or_path, str):
        raw_bytes = content_or_path.encode("utf-8")
    else:
        raw_bytes = content_or_path

    # Extract header up to "end_header\n"
    end_header_marker = b"end_header"
    header_end = raw_bytes.find(end_header_marker)
    if header_end == -1:
        return MeshData(name="Invalid PLY")

    header_text = raw_bytes[:header_end].decode("ascii", errors="replace")
    body_offset = header_end + len(end_header_marker)
    while body_offset < len(raw_bytes) and raw_bytes[body_offset] in (10, 13, 32):
        body_offset += 1

    is_binary = "format binary_little_endian" in header_text
    vertex_count = 0
    face_count = 0

    for line in header_text.splitlines():
        line = line.strip()
        if line.startswith("element vertex"):
            vertex_count = int(line.split()[2])
        elif line.startswith("element face"):
            face_count = int(line.split()[2])

    vertices: list[Vec3] = []
    triangles: list[Triangle] = []

    if not is_binary:
        # ASCII PLY parsing
        body_lines = raw_bytes[body_offset:].decode("utf-8", errors="replace").splitlines()
        line_idx = 0
        for _ in range(vertex_count):
            if line_idx >= len(body_lines):
                break
            parts = body_lines[line_idx].split()
            if len(parts) >= 3:
                vertices.append(Vec3(float(parts[0]), float(parts[1]), float(parts[2])))
            line_idx += 1

        for _ in range(face_count):
            if line_idx >= len(body_lines):
                break
            parts = body_lines[line_idx].split()
            if len(parts) >= 4:
                nv = int(parts[0])
                idx_list = [int(p) for p in parts[1:nv + 1]]
                for i in range(1, len(idx_list) - 1):
                    triangles.append(Triangle(v0=idx_list[0], v1=idx_list[i], v2=idx_list[i + 1]))
            line_idx += 1
    else:
        # Binary Little Endian PLY
        curr_offset = body_offset
        # Standard vertex with 3x float32
        v_struct_size = 12
        for _ in range(vertex_count):
            if curr_offset + v_struct_size > len(raw_bytes):
                break
            x, y, z = struct.unpack_from("<3f", raw_bytes, curr_offset)
            vertices.append(Vec3(x, y, z))
            curr_offset += v_struct_size

        for _ in range(face_count):
            if curr_offset >= len(raw_bytes):
                break
            # Typically 1 byte count followed by int32 indices
            nv = raw_bytes[curr_offset]
            curr_offset += 1
            if curr_offset + nv * 4 > len(raw_bytes):
                break
            indices = struct.unpack_from(f"<{nv}i", raw_bytes, curr_offset)
            curr_offset += nv * 4
            for i in range(1, len(indices) - 1):
                triangles.append(Triangle(v0=indices[0], v1=indices[i], v2=indices[i + 1]))

    mesh = MeshData(name="PLY Model", vertices=vertices, triangles=triangles)
    mesh.compute_normals()
    return mesh


def parse_glb(content_or_path: bytes | Path) -> MeshData:
    """Parse glTF 2.0 Binary container (GLB) extracting mesh positions and indices."""
    raw_bytes: bytes
    if isinstance(content_or_path, Path) or (isinstance(content_or_path, str) and Path(content_or_path).is_file()):
        raw_bytes = Path(content_or_path).read_bytes()
    else:
        raw_bytes = content_or_path

    if len(raw_bytes) < 12:
        return MeshData(name="Invalid GLB")

    magic, version, length = struct.unpack_from("<4sII", raw_bytes, 0)
    if magic != b"glTF" or version != 2:
        return MeshData(name="Unsupported GLB")

    # Read Chunk 0 (JSON) and Chunk 1 (BIN)
    offset = 12
    json_data: dict[str, Any] = {}
    bin_buffer = b""

    while offset < len(raw_bytes):
        chunk_len, chunk_type = struct.unpack_from("<I4s", raw_bytes, offset)
        offset += 8
        chunk_bytes = raw_bytes[offset:offset + chunk_len]
        offset += chunk_len

        if chunk_type == b"JSON":
            try:
                json_data = json.loads(chunk_bytes.decode("utf-8"))
            except Exception:
                pass
        elif chunk_type == b"BIN\x00":
            bin_buffer = chunk_bytes

    if not json_data or not bin_buffer:
        return MeshData(name="Empty GLB")

    accessors = json_data.get("accessors", [])
    buffer_views = json_data.get("bufferViews", [])
    meshes = json_data.get("meshes", [])

    if not meshes:
        return MeshData(name="No Mesh in GLB")

    vertices: list[Vec3] = []
    normals: list[Vec3] = []
    triangles: list[Triangle] = []

    for primitive in meshes[0].get("primitives", []):
        attrs = primitive.get("attributes", {})
        pos_acc_idx = attrs.get("POSITION")
        if pos_acc_idx is None or pos_acc_idx >= len(accessors):
            continue

        pos_acc = accessors[pos_acc_idx]
        pos_bv = buffer_views[pos_acc.get("bufferView", 0)]
        pos_offset = pos_bv.get("byteOffset", 0) + pos_acc.get("byteOffset", 0)
        pos_count = pos_acc.get("count", 0)

        vert_start = len(vertices)
        for i in range(pos_count):
            p_off = pos_offset + i * 12
            if p_off + 12 <= len(bin_buffer):
                x, y, z = struct.unpack_from("<3f", bin_buffer, p_off)
                vertices.append(Vec3(x, y, z))

        # Check for normals
        norm_acc_idx = attrs.get("NORMAL")
        if norm_acc_idx is not None and norm_acc_idx < len(accessors):
            norm_acc = accessors[norm_acc_idx]
            norm_bv = buffer_views[norm_acc.get("bufferView", 0)]
            norm_offset = norm_bv.get("byteOffset", 0) + norm_acc.get("byteOffset", 0)
            norm_count = norm_acc.get("count", 0)
            for i in range(norm_count):
                n_off = norm_offset + i * 12
                if n_off + 12 <= len(bin_buffer):
                    nx, ny, nz = struct.unpack_from("<3f", bin_buffer, n_off)
                    normals.append(Vec3(nx, ny, nz).normalize())

        # Check for indices
        indices_acc_idx = primitive.get("indices")
        if indices_acc_idx is not None and indices_acc_idx < len(accessors):
            idx_acc = accessors[indices_acc_idx]
            idx_bv = buffer_views[idx_acc.get("bufferView", 0)]
            idx_offset = idx_bv.get("byteOffset", 0) + idx_acc.get("byteOffset", 0)
            idx_count = idx_acc.get("count", 0)
            comp_type = idx_acc.get("componentType", 5123)  # 5123 = unsigned short, 5125 = unsigned int

            raw_indices: list[int] = []
            if comp_type == 5123:  # uint16
                for i in range(idx_count):
                    raw_indices.append(struct.unpack_from("<H", bin_buffer, idx_offset + i * 2)[0])
            elif comp_type == 5125:  # uint32
                for i in range(idx_count):
                    raw_indices.append(struct.unpack_from("<I", bin_buffer, idx_offset + i * 4)[0])
            elif comp_type == 5121:  # uint8
                for i in range(idx_count):
                    raw_indices.append(bin_buffer[idx_offset + i])

            for i in range(0, len(raw_indices) - 2, 3):
                triangles.append(Triangle(
                    v0=vert_start + raw_indices[i],
                    v1=vert_start + raw_indices[i + 1],
                    v2=vert_start + raw_indices[i + 2],
                ))
        else:
            # Non-indexed geometry
            for i in range(0, pos_count - 2, 3):
                triangles.append(Triangle(
                    v0=vert_start + i,
                    v1=vert_start + i + 1,
                    v2=vert_start + i + 2,
                ))

    mesh = MeshData(name="GLB Model", vertices=vertices, normals=normals, triangles=triangles)
    mesh.compute_normals()
    return mesh


# =============================================================================
# Shading and Canvas Enums
# =============================================================================

class ShadingMode(Enum):
    """3D lighting and rendering style."""

    FLAT = "flat"            # Lambertian diffuse lighting per triangle facet
    GOURAUD = "gouraud"      # Smooth barycentric lighting interpolation across vertices
    WIREFRAME = "wireframe"  # Edge rasterization


class CanvasMode(Enum):
    """Terminal cell drawing strategy."""

    HALF_BLOCK = "half_block"  # 1x2 sub-pixels per cell via 24-bit ANSI ▀
    BRAILLE = "braille"        # 2x4 sub-pixels per cell via Unicode Braille patterns


# Braille bit offsets: dot (dx, dy) where dx in [0, 1] and dy in [0, 1, 2, 3]
BRAILLE_DOT_MAP: tuple[tuple[int, int], ...] = (
    (0, 0),  # Dot 1: bit 0
    (0, 1),  # Dot 2: bit 1
    (0, 2),  # Dot 3: bit 2
    (1, 0),  # Dot 4: bit 3
    (1, 1),  # Dot 5: bit 4
    (1, 2),  # Dot 6: bit 5
    (0, 3),  # Dot 7: bit 6
    (1, 3),  # Dot 8: bit 7
)

# Bayer 4x4 threshold matrix for ordered dithering in Braille shaded mode
BAYER_4X4 = [
    [ 0/16,  8/16,  2/16, 10/16],
    [12/16,  4/16, 14/16,  6/16],
    [ 3/16, 11/16,  1/16,  9/16],
    [15/16,  7/16, 13/16,  5/16],
]


# =============================================================================
# Software 3D Rasterizer Engine
# =============================================================================

@dataclass
class TransformedVertex:
    """Screen-space coordinates and associated lighting intensity."""

    sx: float
    sy: float
    sz: float
    intensity: float


class Rasterizer3D:
    """Pure-Python depth-buffered software triangle rasterizer."""

    def __init__(
        self,
        pixel_width: int,
        pixel_height: int,
        ambient: float = 0.22,
        light_dir: Vec3 | None = None,
        base_color: tuple[int, int, int] = (125, 86, 244),  # Signature Purple
    ) -> None:
        self.width = max(8, pixel_width)
        self.height = max(8, pixel_height)
        self.ambient = ambient
        self.light_dir = (light_dir or Vec3(0.577, 0.707, -0.408)).normalize()
        self.base_color = base_color

        self.z_buffer = [float("inf")] * (self.width * self.height)
        self.color_buffer: list[tuple[int, int, int] | None] = [None] * (self.width * self.height)

    def clear(self) -> None:
        """Reset depth and color buffers."""
        self.z_buffer = [float("inf")] * (self.width * self.height)
        self.color_buffer = [None] * (self.width * self.height)

    def render_mesh(
        self,
        mesh: MeshData,
        mvp: Mat4,
        shading: ShadingMode,
    ) -> None:
        """Transform, cull, and rasterize all mesh triangles into the framebuffer."""
        self.clear()
        w = self.width
        h = self.height

        # 1. Transform all vertices into homogeneous clip space and viewport space
        transformed: list[TransformedVertex] = []
        light = self.light_dir

        for i, v in enumerate(mesh.vertices):
            cx, cy, cz, cw = mvp.transform_vec4(v.x, v.y, v.z, 1.0)
            if cw <= 1e-4:
                # Behind near clipping plane
                transformed.append(TransformedVertex(-1000.0, -1000.0, 1000.0, 0.0))
                continue

            inv_w = 1.0 / cw
            ndc_x = cx * inv_w
            ndc_y = cy * inv_w
            ndc_z = cz * inv_w

            # Map NDC [-1, 1] to screen space [0, w-1] x [0, h-1]
            sx = (ndc_x + 1.0) * 0.5 * (w - 1)
            sy = (1.0 - ndc_y) * 0.5 * (h - 1)  # Invert Y for screen row orientation
            sz = (ndc_z + 1.0) * 0.5

            # Evaluate vertex lighting for Gouraud shading
            intensity = self.ambient
            if i < len(mesh.normals):
                n = mesh.normals[i]
                diff = max(0.0, n.dot(light))
                intensity = min(1.0, self.ambient + (1.0 - self.ambient) * diff)

            transformed.append(TransformedVertex(sx, sy, sz, intensity))

        # 2. Rasterize triangles
        for tri in mesh.triangles:
            if not (0 <= tri.v0 < len(transformed) and 0 <= tri.v1 < len(transformed) and 0 <= tri.v2 < len(transformed)):
                continue

            tv0 = transformed[tri.v0]
            tv1 = transformed[tri.v1]
            tv2 = transformed[tri.v2]

            # Near-plane guard
            if tv0.sz >= 900.0 or tv1.sz >= 900.0 or tv2.sz >= 900.0:
                continue

            # Backface culling via 2D signed cross-product
            det = (tv1.sx - tv0.sx) * (tv2.sy - tv0.sy) - (tv1.sy - tv0.sy) * (tv2.sx - tv0.sx)
            if det <= 0.0:
                # Cull triangles winding clockwise / facing away
                continue

            if shading == ShadingMode.WIREFRAME:
                self._draw_wireframe_triangle(tv0, tv1, tv2)
            elif shading == ShadingMode.FLAT:
                # Face normal lighting
                diff = max(0.0, tri.face_normal.dot(light))
                facet_intensity = min(1.0, self.ambient + (1.0 - self.ambient) * diff)
                r = int(min(255, self.base_color[0] * facet_intensity))
                g = int(min(255, self.base_color[1] * facet_intensity))
                b = int(min(255, self.base_color[2] * facet_intensity))
                self._rasterize_triangle(tv0, tv1, tv2, det, (r, g, b), is_gouraud=False)
            elif shading == ShadingMode.GOURAUD:
                self._rasterize_triangle(tv0, tv1, tv2, det, self.base_color, is_gouraud=True)

    def _rasterize_triangle(
        self,
        tv0: TransformedVertex,
        tv1: TransformedVertex,
        tv2: TransformedVertex,
        det: float,
        base_color: tuple[int, int, int],
        is_gouraud: bool,
    ) -> None:
        """Rasterize a filled 2D triangle using barycentric coordinates."""
        min_x = max(0, int(math.floor(min(tv0.sx, tv1.sx, tv2.sx))))
        max_x = min(self.width - 1, int(math.ceil(max(tv0.sx, tv1.sx, tv2.sx))))
        min_y = max(0, int(math.floor(min(tv0.sy, tv1.sy, tv2.sy))))
        max_y = min(self.height - 1, int(math.ceil(max(tv0.sy, tv1.sy, tv2.sy))))

        if min_x > max_x or min_y > max_y:
            return

        inv_det = 1.0 / det
        w = self.width
        z_buf = self.z_buffer
        c_buf = self.color_buffer

        for y in range(min_y, max_y + 1):
            row_offset = y * w
            py = float(y) + 0.5

            for x in range(min_x, max_x + 1):
                px = float(x) + 0.5

                # Barycentric coordinates
                w0 = ((tv1.sx - px) * (tv2.sy - py) - (tv1.sy - py) * (tv2.sx - px)) * inv_det
                w1 = ((tv2.sx - px) * (tv0.sy - py) - (tv2.sy - py) * (tv0.sx - px)) * inv_det
                w2 = 1.0 - w0 - w1

                if w0 >= -1e-4 and w1 >= -1e-4 and w2 >= -1e-4:
                    z = w0 * tv0.sz + w1 * tv1.sz + w2 * tv2.sz
                    idx = row_offset + x

                    if z < z_buf[idx]:
                        z_buf[idx] = z
                        if not is_gouraud:
                            c_buf[idx] = base_color
                        else:
                            intensity = w0 * tv0.intensity + w1 * tv1.intensity + w2 * tv2.intensity
                            r = int(min(255, max(0, base_color[0] * intensity)))
                            g = int(min(255, max(0, base_color[1] * intensity)))
                            b = int(min(255, max(0, base_color[2] * intensity)))
                            c_buf[idx] = (r, g, b)

    def _draw_wireframe_triangle(
        self,
        tv0: TransformedVertex,
        tv1: TransformedVertex,
        tv2: TransformedVertex,
    ) -> None:
        """Rasterize triangle outline edges via Bresenham line algorithm."""
        edge_col = (0, 229, 255)  # Cyan wireframe
        self._draw_line(int(tv0.sx), int(tv0.sy), tv0.sz, int(tv1.sx), int(tv1.sy), tv1.sz, edge_col)
        self._draw_line(int(tv1.sx), int(tv1.sy), tv1.sz, int(tv2.sx), int(tv2.sy), tv2.sz, edge_col)
        self._draw_line(int(tv2.sx), int(tv2.sy), tv2.sz, int(tv0.sx), int(tv0.sy), tv0.sz, edge_col)

    def _draw_line(
        self,
        x0: int,
        y0: int,
        z0: float,
        x1: int,
        y1: int,
        z1: float,
        color: tuple[int, int, int],
    ) -> None:
        """Bresenham 3D line drawing with depth buffer testing."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        steps = max(dx, dy)
        inv_steps = 1.0 / steps if steps > 0 else 1.0
        step_idx = 0

        w = self.width
        h = self.height
        z_buf = self.z_buffer
        c_buf = self.color_buffer

        while True:
            t = step_idx * inv_steps
            z = z0 + (z1 - z0) * t

            if 0 <= x0 < w and 0 <= y0 < h:
                idx = y0 * w + x0
                if z <= z_buf[idx] + 1e-3:
                    z_buf[idx] = z
                    c_buf[idx] = color

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
            step_idx += 1


# =============================================================================
# Canvas Emitters (Half-block & Braille)
# =============================================================================

def emit_half_block_canvas(
    color_buffer: list[tuple[int, int, int] | None],
    pixel_width: int,
    pixel_height: int,
) -> list[str]:
    """Convert RGB color buffer into ANSI 24-bit half-block lines (▀ and ▄)."""
    lines: list[str] = []
    term_rows = pixel_height // 2

    for row in range(term_rows):
        top_y = row * 2
        bot_y = row * 2 + 1
        line_parts: list[str] = []

        cur_fg: tuple[int, int, int] | None = None
        cur_bg: tuple[int, int, int] | None = None

        for x in range(pixel_width):
            top_c = color_buffer[top_y * pixel_width + x]
            bot_c = color_buffer[bot_y * pixel_width + x] if bot_y < pixel_height else None

            if top_c is None and bot_c is None:
                if cur_fg is not None or cur_bg is not None:
                    line_parts.append("\x1b[0m")
                    cur_fg = None
                    cur_bg = None
                line_parts.append(" ")
                continue

            if top_c is not None and bot_c is not None:
                char = "▀"
                target_fg = top_c
                target_bg = bot_c
            elif top_c is not None:
                char = "▀"
                target_fg = top_c
                target_bg = None
            else:
                char = "▄"
                target_fg = bot_c
                target_bg = None

            frag: list[str] = []
            if target_fg != cur_fg:
                frag.append(f"\x1b[38;2;{target_fg[0]};{target_fg[1]};{target_fg[2]}m")
                cur_fg = target_fg

            if target_bg != cur_bg:
                if target_bg is not None:
                    frag.append(f"\x1b[48;2;{target_bg[0]};{target_bg[1]};{target_bg[2]}m")
                else:
                    frag.append("\x1b[49m")
                cur_bg = target_bg

            frag.append(char)
            line_parts.append("".join(frag))

        if cur_fg is not None or cur_bg is not None:
            line_parts.append("\x1b[0m")

        lines.append("".join(line_parts))

    return lines


def emit_braille_canvas(
    color_buffer: list[tuple[int, int, int] | None],
    pixel_width: int,
    pixel_height: int,
    is_wireframe: bool = False,
    dither: bool = False,
) -> list[str]:
    """Convert sub-pixel color buffer into Unicode Braille patterns (U+2800..U+28FF).

    In solid mode (default dither=False), each occupied sub-pixel activates its
    corresponding Braille dot, creating solid surfaces with fully dotted characters (⣿)
    and sub-pixel edge contours, colored using 24-bit Truecolor.
    When dither=True, Bayer ordered dithering is applied based on luminance.
    """
    lines: list[str] = []
    term_cols = pixel_width // 2
    term_rows = pixel_height // 4

    # Map subpixel (dx, dy) to bit index in Unicode Braille
    dot_bits = [
        (0, 0, 0x01),  # Dot 1: top-left
        (0, 1, 0x02),  # Dot 2: mid-upper-left
        (0, 2, 0x04),  # Dot 3: mid-lower-left
        (1, 0, 0x08),  # Dot 4: top-right
        (1, 1, 0x10),  # Dot 5: mid-upper-right
        (1, 2, 0x20),  # Dot 6: mid-lower-right
        (0, 3, 0x40),  # Dot 7: bottom-left
        (1, 3, 0x80),  # Dot 8: bottom-right
    ]

    for ty in range(term_rows):
        line_parts: list[str] = []
        cur_fg: tuple[int, int, int] | None = None

        for tx in range(term_cols):
            base_x = tx * 2
            base_y = ty * 4

            mask = 0
            accum_r = 0
            accum_g = 0
            accum_b = 0
            active_dots = 0

            for dx, dy, bit in dot_bits:
                px = base_x + dx
                py = base_y + dy
                if px < pixel_width and py < pixel_height:
                    c = color_buffer[py * pixel_width + px]
                    if c is not None:
                        if not dither or is_wireframe:
                            # Solid surface or wireframe: activate dot for each occupied subpixel
                            mask |= bit
                            accum_r += c[0]
                            accum_g += c[1]
                            accum_b += c[2]
                            active_dots += 1
                        else:
                            # Bayer dithered shading (optional monochrome/dither mode)
                            lum = (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0
                            thresh = BAYER_4X4[py % 4][px % 4]
                            if lum > thresh:
                                mask |= bit
                                accum_r += c[0]
                                accum_g += c[1]
                                accum_b += c[2]
                                active_dots += 1

            if mask == 0:
                if cur_fg is not None:
                    line_parts.append("\x1b[0m")
                    cur_fg = None
                line_parts.append(" ")
                continue

            avg_r = int(accum_r / active_dots) if active_dots > 0 else 255
            avg_g = int(accum_g / active_dots) if active_dots > 0 else 255
            avg_b = int(accum_b / active_dots) if active_dots > 0 else 255
            avg_color = (avg_r, avg_g, avg_b)

            if avg_color != cur_fg:
                line_parts.append(f"\x1b[38;2;{avg_r};{avg_g};{avg_b}m")
                cur_fg = avg_color

            line_parts.append(chr(0x2800 + mask))

        if cur_fg is not None:
            line_parts.append("\x1b[0m")

        lines.append("".join(line_parts))

    return lines


# =============================================================================
# Tea Component: MeshViewer Bean
# =============================================================================

class MeshViewerTickMsg(Msg):
    """Timer message driving interactive 3D auto-spin."""

    def __init__(self, tag: str) -> None:
        self.tag = tag


class MeshViewer(Model):
    """A full-featured software 3D rasterizer bean for terminal applications."""

    def __init__(
        self,
        mesh: MeshData | None = None,
        width: int = 60,
        height: int = 24,
        shading: ShadingMode = ShadingMode.GOURAUD,
        canvas_mode: CanvasMode = CanvasMode.HALF_BLOCK,
        base_color: tuple[int, int, int] = (125, 86, 244),  # Signature Purple
        auto_spin: bool = True,
        spin_speed: float = 2.5,
        title: str = "3D Mesh Viewer",
        border: Border | None = ROUNDED_BORDER,
        dither: bool = False,
        tag: str = "mesh_viewer",
    ) -> None:
        self.width = max(20, width)
        self.height = max(8, height)
        self.shading = shading
        self.canvas_mode = canvas_mode
        self.base_color = base_color
        self.auto_spin = auto_spin
        self.spin_speed = spin_speed
        self.title = title
        self.border = border
        self.dither = dither
        self.tag = tag

        # Camera & Transform state
        self.yaw = 0.65       # Orbit angle around Y axis
        self.pitch = 0.35     # Orbit angle around X axis
        self.roll = 0.0       # Orbit angle around Z axis
        self.distance = 2.6   # Camera zoom distance
        self.fov = 50.0       # Field of view in degrees

        # Interaction state
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.show_stats = True

        # Current active mesh
        self.mesh = mesh or create_torus()
        self.mesh.center_and_scale(target_radius=1.0)

        # Built-in primitive cycle list for quick demos
        self.primitives: list[Callable[[], MeshData]] = [
            create_torus,
            create_uv_sphere,
            create_cube,
            create_pyramid,
            create_cylinder,
        ]
        self.primitive_idx = 0

    def load_mesh(self, mesh: MeshData) -> None:
        """Assign a new mesh to the viewer and normalize its scale."""
        self.mesh = mesh
        self.mesh.center_and_scale(target_radius=1.0)

    def load_file(self, file_path: str | Path) -> None:
        """Autodetect file extension and load OBJ, STL, PLY, or GLB models."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".obj":
            self.load_mesh(parse_obj(path))
        elif ext == ".stl":
            self.load_mesh(parse_stl(path))
        elif ext == ".ply":
            self.load_mesh(parse_ply(path))
        elif ext in (".glb", ".gltf"):
            self.load_mesh(parse_glb(path))
        else:
            # Fallback to OBJ
            self.load_mesh(parse_obj(path))

    def init(self) -> Cmd | None:
        """Initialize auto-spin ticker if enabled."""
        if self.auto_spin:
            return self.tick()
        return None

    def tick(self) -> Cmd:
        """Schedule the next animation frame tick."""
        tag = self.tag

        async def _tick_async() -> Msg:
            await asyncio.sleep(0.04)  # ~25 FPS
            return MeshViewerTickMsg(tag=tag)

        return _tick_async

    def update(self, msg: Msg) -> tuple[MeshViewer, Cmd | None]:
        """Handle keyboard navigation, mouse orbit controls, and animation ticks."""
        if isinstance(msg, MeshViewerTickMsg) and msg.tag == self.tag:
            if self.auto_spin:
                self.yaw += math.radians(self.spin_speed)
                return self, self.tick()
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                # Shading Mode Toggle
                case "m":
                    modes = [ShadingMode.FLAT, ShadingMode.GOURAUD, ShadingMode.WIREFRAME]
                    cur_idx = modes.index(self.shading)
                    self.shading = modes[(cur_idx + 1) % len(modes)]
                    return self, None

                # Canvas Mode Toggle (Half-block <-> Braille)
                case "c":
                    if self.canvas_mode == CanvasMode.HALF_BLOCK:
                        self.canvas_mode = CanvasMode.BRAILLE
                    else:
                        self.canvas_mode = CanvasMode.HALF_BLOCK
                    return self, None

                # Toggle Bayer dithering in Braille mode
                case "d":
                    self.dither = not self.dither
                    return self, None

                # Auto-spin toggle
                case " " | "space":
                    self.auto_spin = not self.auto_spin
                    if self.auto_spin:
                        return self, self.tick()
                    return self, None

                # Orbit Camera (Arrow keys & Vim keys)
                case "left" | "h":
                    self.yaw -= 0.1
                    return self, None
                case "right" | "l":
                    self.yaw += 0.1
                    return self, None
                case "up" | "k":
                    self.pitch = max(-1.4, min(1.4, self.pitch + 0.1))
                    return self, None
                case "down" | "j":
                    self.pitch = max(-1.4, min(1.4, self.pitch - 0.1))
                    return self, None

                # Roll Camera
                case "[":
                    self.roll -= 0.1
                    return self, None
                case "]":
                    self.roll += 0.1
                    return self, None

                # Zoom in / out
                case "+" | "=" | "w":
                    self.distance = max(1.2, self.distance - 0.2)
                    return self, None
                case "-" | "_" | "s":
                    self.distance = min(6.0, self.distance + 0.2)
                    return self, None

                # Reset Camera View
                case "r":
                    self.yaw = 0.65
                    self.pitch = 0.35
                    self.roll = 0.0
                    self.distance = 2.6
                    return self, None

                # Toggle stats overlay
                case "i":
                    self.show_stats = not self.show_stats
                    return self, None

                # Switch built-in procedural primitives (1 through 5)
                case "1" | "2" | "3" | "4" | "5":
                    idx = int(msg.key) - 1
                    if 0 <= idx < len(self.primitives):
                        self.primitive_idx = idx
                        self.load_mesh(self.primitives[idx]())
                    return self, None

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.WHEEL_UP:
                self.distance = max(1.2, self.distance - 0.2)
                return self, None
            if msg.button == MouseButton.WHEEL_DOWN:
                self.distance = min(6.0, self.distance + 0.2)
                return self, None

            if msg.button == MouseButton.LEFT:
                if msg.action == MouseAction.PRESS:
                    self.is_dragging = True
                    self.last_mouse_x = msg.x
                    self.last_mouse_y = msg.y
                elif msg.action == MouseAction.RELEASE:
                    self.is_dragging = False

            if self.is_dragging:
                dx = msg.x - self.last_mouse_x
                dy = msg.y - self.last_mouse_y
                self.yaw += dx * 0.05
                self.pitch = max(-1.4, min(1.4, self.pitch + dy * 0.05))
                self.last_mouse_x = msg.x
                self.last_mouse_y = msg.y
                return self, None

        return self, None

    def view(self) -> str:
        """Render the 3D scene into terminal character cells."""
        # Calculate viewport dimensions inside border
        has_border = self.border is not None
        inner_w = max(10, self.width - (2 if has_border else 0))
        inner_h = max(4, self.height - (2 if has_border else 0))

        # Resolution based on Canvas Mode
        if self.canvas_mode == CanvasMode.HALF_BLOCK:
            pixel_w = inner_w
            pixel_h = inner_h * 2
        else:
            # Braille: 2x4 sub-pixels
            pixel_w = inner_w * 2
            pixel_h = inner_h * 4

        # Build View Matrix via orbital camera
        cam_x = self.distance * math.cos(self.pitch) * math.sin(self.yaw)
        cam_y = self.distance * math.sin(self.pitch)
        cam_z = self.distance * math.cos(self.pitch) * math.cos(self.yaw)
        eye = Vec3(cam_x, cam_y, cam_z)
        target = Vec3(0.0, 0.0, 0.0)
        up = Vec3(0.0, 1.0, 0.0)

        view_mat = Mat4.look_at(eye, target, up)
        if abs(self.roll) > 1e-4:
            view_mat = Mat4.rotation_z(self.roll) * view_mat

        # Build Projection Matrix
        aspect = float(pixel_w) / float(pixel_h) if pixel_h > 0 else 1.0
        # Terminal characters typically have an aspect ratio of ~1:2 (width:height).
        # In Half-block, vertical resolution is doubled, giving square pixels (aspect ~ 1.0).
        # In Braille, 2 cols x 4 rows gives square pixels (aspect ~ 1.0).
        proj_mat = Mat4.perspective(self.fov, aspect, near=0.1, far=100.0)
        mvp = proj_mat * view_mat

        # Execute software rasterizer
        rasterizer = Rasterizer3D(
            pixel_width=pixel_w,
            pixel_height=pixel_h,
            ambient=0.22,
            base_color=self.base_color,
        )
        rasterizer.render_mesh(self.mesh, mvp, self.shading)

        # Emit canvas lines
        if self.canvas_mode == CanvasMode.HALF_BLOCK:
            raw_lines = emit_half_block_canvas(rasterizer.color_buffer, pixel_w, pixel_h)
        else:
            raw_lines = emit_braille_canvas(
                rasterizer.color_buffer,
                pixel_w,
                pixel_h,
                is_wireframe=(self.shading == ShadingMode.WIREFRAME),
                dither=self.dither,
            )

        # Pad or clip lines to inner_h
        lines: list[str] = []
        for r in range(inner_h):
            if r < len(raw_lines):
                line = raw_lines[r]
                # Pad to inner_w
                cw = string_width(line)
                if cw < inner_w:
                    line = f"{line}{' ' * (inner_w - cw)}"
                lines.append(line)
            else:
                lines.append(" " * inner_w)

        # Stats and help overlay at the bottom
        if self.show_stats and len(lines) >= 2:
            mode_badge = f"{self.shading.value.upper()} | {self.canvas_mode.value.upper()}"
            if self.canvas_mode == CanvasMode.BRAILLE and self.dither:
                mode_badge += " (DITHER)"
            poly_badge = f"▲ {len(self.mesh.triangles)} tris"
            info_left = f" {mode_badge} ({poly_badge})"
            info_right = f"yaw:{int(math.degrees(self.yaw)) % 360}° zoom:{self.distance:.1f}x [m:shading c:canvas d:dither space:spin] "

            w_left = string_width(info_left)
            w_right = string_width(info_right)
            if w_left + w_right <= inner_w:
                gap = " " * (inner_w - w_left - w_right)
                stat_line = f"\x1b[2m\x1b[36m{info_left}\x1b[0m{gap}\x1b[2m{info_right}\x1b[0m"
                lines[-1] = stat_line
            elif w_left <= inner_w:
                gap = " " * (inner_w - w_left)
                stat_line = f"\x1b[2m\x1b[36m{info_left}\x1b[0m{gap}"
                lines[-1] = stat_line

        # Optional Crema box border framing
        if not has_border or not self.border:
            return "\n".join(lines)

        b = self.border
        title_text = f" {self.title}: {self.mesh.name} "
        title_w = string_width(title_text)

        top_bar_len = max(0, inner_w - title_w)
        top_left = top_bar_len // 2
        top_right = top_bar_len - top_left

        header = f"{b.top_left}{b.top * top_left}\x1b[1m\x1b[35m{title_text}\x1b[0m{b.top * top_right}{b.top_right}"
        footer = f"{b.bottom_left}{b.bottom * inner_w}{b.bottom_right}"

        boxed_lines = [header]
        for l in lines:
            boxed_lines.append(f"{b.left}{l}{b.right}")
        boxed_lines.append(footer)

        return "\n".join(boxed_lines)
