"""Gothic window preset — pointed arch with splayed jambs (ostění).

Generates a 3-D mesh of a Gothic window frame suitable for papercraft:
- Pointed (lancet) arch top
- Configurable splay angle for the jambs
- Flat panels ideal for exact unfolding
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


def generate_gothic_window(params: dict[str, Any]) -> MeshData:
    """Generate a Gothic window mesh.

    Parameters
    ----------
    width : float         Window opening width (default 1.0).
    height : float        Total height including arch (default 2.5).
    depth : float         Wall / jamb depth (default 0.4).
    splay_angle : float   Jamb splay angle in degrees (default 15).
    arch_segments : int   Resolution of the pointed arch (default 12).
    frame_width : float   Width of the "stone" frame (default 0.08).
    """
    W = float(params.get("width", 1.0))
    H = float(params.get("height", 2.5))
    D = float(params.get("depth", 0.4))
    splay = float(params.get("splay_angle", 15.0))
    segs = int(params.get("arch_segments", 12))
    FW = float(params.get("frame_width", 0.08))

    # Outer profile (front face)
    outer = _pointed_arch_profile(W / 2, H, segs)
    # Inner profile (slightly smaller)
    inner = _pointed_arch_profile(W / 2 - FW, H - FW, segs)

    # Splay: the inner opening at the back is wider
    splay_offset = D * math.tan(math.radians(splay))

    # Front face ring (outer - inner as flat)
    # Build as strips extruded to depth D with splay
    n = len(outer)

    front_outer = _embed_xz(outer, y=0.0)
    front_inner = _embed_xz(inner, y=0.0)
    # back inner is splayed outward
    back_inner = _embed_xz(
        inner * np.array([[1.0 + splay_offset / (W / 2 + 1e-9), 1.0]]),
        y=D,
    )
    back_outer = _embed_xz(outer, y=D)

    # Concatenate all vertices:
    # 0..n-1   front outer
    # n..2n-1  front inner
    # 2n..3n-1 back inner (splayed)
    # 3n..4n-1 back outer
    verts = np.vstack([front_outer, front_inner, back_inner, back_outer])

    faces: list[list[int]] = []

    for i in range(n):
        ni = (i + 1) % n
        # Front face ring (outer → inner)
        faces.append([i, ni, n + ni])
        faces.append([i, n + ni, n + i])

        # Back face ring (outer → inner)
        faces.append([3 * n + i, 2 * n + i, 2 * n + ni])
        faces.append([3 * n + i, 2 * n + ni, 3 * n + ni])

        # Jamb inner surface (front inner → back inner)
        faces.append([n + i, n + ni, 2 * n + ni])
        faces.append([n + i, 2 * n + ni, 2 * n + i])

        # Outer surface (front outer → back outer)
        faces.append([i, 3 * n + i, 3 * n + ni])
        faces.append([i, 3 * n + ni, ni])

    return MeshData(
        vertices=verts,
        faces=np.array(faces, dtype=np.int32),
    )


def _pointed_arch_profile(half_w: float, height: float, segs: int) -> np.ndarray:
    """Generate pointed-arch profile as (N, 2) array in XZ plane.

    Returns a closed polyline: bottom-left → up left jamb → arch → down right jamb → bottom-right.
    """
    spring_h = height * 0.55  # spring line at ~55% of total height
    radius = half_w * 1.3  # > half-width gives the pointed shape

    pts: list[list[float]] = []

    # left jamb (bottom to spring)
    pts.append([-half_w, 0.0])
    pts.append([-half_w, spring_h])

    # left arc → apex
    cx = half_w  # center of left arc is on the *right* side
    for i in range(segs + 1):
        t = i / segs
        angle = math.pi / 2 + t * (math.pi / 2)
        x = -cx + radius * math.cos(angle)
        z = spring_h + radius * math.sin(angle)
        if z > height:
            z = height
        pts.append([x, z])

    # right arc ← apex
    cx_r = -half_w
    for i in range(segs + 1):
        t = i / segs
        angle = math.pi - t * (math.pi / 2)
        x = -cx_r + radius * math.cos(angle)
        z = spring_h + radius * math.sin(angle)
        if z > height:
            z = height
        pts.append([x, z])

    # right jamb (spring to bottom)
    pts.append([half_w, spring_h])
    pts.append([half_w, 0.0])

    return np.array(pts, dtype=np.float64)


def _embed_xz(profile_2d: np.ndarray, y: float) -> np.ndarray:
    """Convert (N, 2) XZ profile to (N, 3) with given Y."""
    n = len(profile_2d)
    out = np.zeros((n, 3), dtype=np.float64)
    out[:, 0] = profile_2d[:, 0]
    out[:, 1] = y
    out[:, 2] = profile_2d[:, 1]
    return out
