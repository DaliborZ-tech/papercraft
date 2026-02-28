"""Primitive solid creation (box, cylinder, cone).

When pythonocc-core (OpenCascade) is available the functions return real
TopoDS_Shape solids.  When it is **not** installed the module falls back to a
lightweight numpy-mesh representation so the rest of the pipeline can still
run (with reduced accuracy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Lightweight mesh fallback (always available)
# ---------------------------------------------------------------------------


@dataclass
class MeshData:
    """Simple indexed-triangle mesh used as fallback and as internal exchange format."""

    vertices: NDArray[np.float64]  # (N, 3)
    faces: NDArray[np.int32]  # (M, 3) — triangle indices
    normals: NDArray[np.float64] | None = None  # per-face or per-vertex

    @property
    def num_vertices(self) -> int:
        return self.vertices.shape[0]

    @property
    def num_faces(self) -> int:
        return self.faces.shape[0]


# ---------------------------------------------------------------------------
# Try to import OCC — flag available at runtime
# ---------------------------------------------------------------------------

try:
    from OCP.BRepPrimAPI import (
        BRepPrimAPI_MakeBox,
        BRepPrimAPI_MakeCone,
        BRepPrimAPI_MakeCylinder,
    )
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

    OCC_AVAILABLE = True
except ImportError:
    OCC_AVAILABLE = False


# ---------------------------------------------------------------------------
# OCC-backed primitives
# ---------------------------------------------------------------------------


def make_box_occ(dx: float, dy: float, dz: float):
    """Return a TopoDS_Shape box *dx × dy × dz*."""
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core is not installed")
    return BRepPrimAPI_MakeBox(dx, dy, dz).Shape()


def make_cylinder_occ(radius: float, height: float):
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core is not installed")
    return BRepPrimAPI_MakeCylinder(radius, height).Shape()


def make_cone_occ(radius1: float, radius2: float, height: float):
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core is not installed")
    return BRepPrimAPI_MakeCone(radius1, radius2, height).Shape()


# ---------------------------------------------------------------------------
# Pure-numpy mesh primitives (fallback)
# ---------------------------------------------------------------------------


def make_box_mesh(dx: float, dy: float, dz: float) -> MeshData:
    """Create an axis-aligned box mesh centered at the origin."""
    hx, hy, hz = dx / 2, dy / 2, dz / 2
    verts = np.array(
        [
            [-hx, -hy, -hz],
            [+hx, -hy, -hz],
            [+hx, +hy, -hz],
            [-hx, +hy, -hz],
            [-hx, -hy, +hz],
            [+hx, -hy, +hz],
            [+hx, +hy, +hz],
            [-hx, +hy, +hz],
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            # bottom
            [0, 2, 1],
            [0, 3, 2],
            # top
            [4, 5, 6],
            [4, 6, 7],
            # front
            [0, 1, 5],
            [0, 5, 4],
            # back
            [2, 3, 7],
            [2, 7, 6],
            # left
            [0, 4, 7],
            [0, 7, 3],
            # right
            [1, 2, 6],
            [1, 6, 5],
        ],
        dtype=np.int32,
    )
    return MeshData(vertices=verts, faces=faces)


def make_cylinder_mesh(
    radius: float, height: float, segments: int = 32
) -> MeshData:
    """Create a cylinder mesh (open ends) along the Z axis."""
    angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    bottom = np.column_stack([radius * np.cos(angles), radius * np.sin(angles),
                              np.zeros(segments)])
    top = bottom.copy()
    top[:, 2] = height
    # center vertices for caps
    center_bot = np.array([[0.0, 0.0, 0.0]])
    center_top = np.array([[0.0, 0.0, height]])
    verts = np.vstack([bottom, top, center_bot, center_top])

    faces_list: list[list[int]] = []
    n = segments
    cb = 2 * n  # center bottom index
    ct = 2 * n + 1  # center top index
    for i in range(n):
        ni = (i + 1) % n
        # side quads as two triangles
        faces_list.append([i, ni, ni + n])
        faces_list.append([i, ni + n, i + n])
        # bottom cap
        faces_list.append([cb, ni, i])
        # top cap
        faces_list.append([ct, i + n, ni + n])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )


def make_cone_mesh(
    radius_bottom: float, radius_top: float, height: float, segments: int = 32
) -> MeshData:
    """Truncated cone (set *radius_top=0* for a sharp cone)."""
    angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    bottom = np.column_stack([radius_bottom * np.cos(angles),
                              radius_bottom * np.sin(angles),
                              np.zeros(segments)])
    top = np.column_stack([radius_top * np.cos(angles),
                           radius_top * np.sin(angles),
                           np.full(segments, height)])
    center_bot = np.array([[0.0, 0.0, 0.0]])
    center_top = np.array([[0.0, 0.0, height]])
    verts = np.vstack([bottom, top, center_bot, center_top])

    faces_list: list[list[int]] = []
    n = segments
    cb = 2 * n
    ct = 2 * n + 1
    for i in range(n):
        ni = (i + 1) % n
        if radius_top > 1e-9:
            faces_list.append([i, ni, ni + n])
            faces_list.append([i, ni + n, i + n])
        else:
            faces_list.append([i, ni, ct])
        faces_list.append([cb, ni, i])
        if radius_top > 1e-9:
            faces_list.append([ct, i + n, ni + n])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )
