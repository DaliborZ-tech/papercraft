"""Opening preset — rectangular or arched hole to subtract from a wall.

The opening is a solid volume (like a "cookie cutter") that can be
boolean-subtracted from a wall.  For the mesh fallback we simply generate
the opening box/arch as its own mesh for visualisation.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


def generate_opening(params: dict[str, Any]) -> MeshData:
    """Generate a rectangular or arched opening solid.

    Parameters
    ----------
    width : float       Opening width (default 1.2).
    height : float      Opening height (default 2.0).
    depth : float       Wall thickness / depth of the opening (default 0.35).
    arch_type : str     "rect" | "round" | "pointed" (default "rect").
    arch_segments : int  Resolution for arched tops (default 12).
    """
    W = float(params.get("width", 1.2))
    H = float(params.get("height", 2.0))
    D = float(params.get("depth", 0.35))
    arch = str(params.get("arch_type", "rect"))
    segs = int(params.get("arch_segments", 12))

    if arch == "rect":
        return _rect_opening(W, H, D)
    elif arch == "round":
        return _round_arch_opening(W, H, D, segs)
    elif arch == "pointed":
        return _pointed_arch_opening(W, H, D, segs)
    else:
        return _rect_opening(W, H, D)


def _rect_opening(w: float, h: float, d: float) -> MeshData:
    """Simple rectangular opening (a box)."""
    verts = np.array(
        [
            [0, 0, 0], [w, 0, 0], [w, 0, h], [0, 0, h],
            [0, d, 0], [w, d, 0], [w, d, h], [0, d, h],
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],
            [5, 4, 7], [5, 7, 6],
            [4, 0, 3], [4, 3, 7],
            [1, 5, 6], [1, 6, 2],
            [3, 2, 6], [3, 6, 7],
            [4, 5, 1], [4, 1, 0],
        ],
        dtype=np.int32,
    )
    return MeshData(vertices=verts, faces=faces)


def _round_arch_opening(w: float, h: float, d: float, segs: int) -> MeshData:
    """Opening with a semicircular arch on top."""
    # Bottom rectangle up to the spring line, then semicircle
    radius = w / 2.0
    spring_h = h - radius  # height of the straight part

    front_profile = _arch_profile(w, spring_h, radius, segs, y=0.0)
    back_profile = _arch_profile(w, spring_h, radius, segs, y=d)

    n = len(front_profile)
    verts = np.vstack([front_profile, back_profile])
    faces = _extrude_faces(n)
    return MeshData(vertices=verts, faces=np.array(faces, dtype=np.int32))


def _pointed_arch_opening(w: float, h: float, d: float, segs: int) -> MeshData:
    """Opening with a Gothic pointed arch (two arcs meeting at the top)."""
    spring_h = h * 0.5
    radius = w * 0.7  # larger than half-width → pointed

    cx_left = w * 0.3
    cx_right = w * 0.7
    top_x = w / 2

    # left arc
    pts: list[list[float]] = [[0.0, 0.0, 0.0], [w, 0.0, 0.0]]
    pts.append([w, 0.0, spring_h])

    half = segs // 2
    for i in range(half + 1):
        frac = i / half
        angle = frac * (math.pi / 2)
        x = cx_right - radius * math.cos(angle) + (top_x - cx_right + radius) * frac
        z = spring_h + radius * math.sin(angle) * ((h - spring_h) / radius)
        x = min(max(x, 0), w)
        pts.append([x, 0.0, z])

    for i in range(half, -1, -1):
        frac = i / half
        angle = frac * (math.pi / 2)
        x = cx_left + radius * math.cos(angle) - (cx_left - radius + top_x) * frac
        z = spring_h + radius * math.sin(angle) * ((h - spring_h) / radius)
        x = min(max(x, 0), w)
        pts.append([x, 0.0, z])

    pts.append([0.0, 0.0, spring_h])

    front = np.array(pts, dtype=np.float64)
    back = front.copy()
    back[:, 1] = d

    n = len(front)
    verts = np.vstack([front, back])
    faces = _extrude_faces(n)
    return MeshData(vertices=verts, faces=np.array(faces, dtype=np.int32))


def _arch_profile(w: float, spring_h: float, radius: float, segs: int, y: float) -> np.ndarray:
    """Generate a 2-D profile (Nx3) for a round-arch opening at depth *y*."""
    cx = w / 2.0
    pts: list[list[float]] = [
        [0.0, y, 0.0],
        [w, y, 0.0],
        [w, y, spring_h],
    ]
    for i in range(segs + 1):
        angle = math.pi * i / segs
        x = cx + radius * math.cos(math.pi - angle)
        z = spring_h + radius * math.sin(angle)
        pts.append([x, y, z])
    pts.append([0.0, y, spring_h])
    return np.array(pts, dtype=np.float64)


def _extrude_faces(n: int) -> list[list[int]]:
    """Create triangle faces connecting front (0..n-1) and back (n..2n-1) profiles."""
    faces: list[list[int]] = []
    for i in range(n):
        ni = (i + 1) % n
        # quad as 2 triangles
        faces.append([i, ni, ni + n])
        faces.append([i, ni + n, i + n])
    return faces
