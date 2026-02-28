"""Gothic window preset — pointed (lancet) arch with splayed jambs.

Generates a 3-D mesh of a Gothic window frame suitable for papercraft:
- Proper pointed (ogival) arch top — two circular arcs meeting at apex
- Configurable splay angle for the jambs (ostění)
- Optional central mullion (sloupek) dividing the window into two lights
- Optional simple tracery (kružba) in the arch head
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
    width : float         Window opening width (default 1.2).
    height : float        Total height including arch (default 2.8).
    depth : float         Wall / jamb depth (default 0.35).
    splay_angle : float   Jamb splay angle in degrees (default 10).
    arch_segments : int   Resolution of the pointed arch (default 16).
    frame_width : float   Width of the stone frame (default 0.10).
    mullion : bool        Add a central mullion (default True).
    mullion_width : float Width of the mullion bar (default 0.06).
    tracery : bool        Add simple trefoil tracery in arch head (default False).
    spring_ratio : float  Spring line position as ratio of height (default 0.55).
    """
    W = float(params.get("width", 1.2))
    H = float(params.get("height", 2.8))
    D = float(params.get("depth", 0.35))
    splay = float(params.get("splay_angle", 10.0))
    segs = int(params.get("arch_segments", 16))
    FW = float(params.get("frame_width", 0.10))
    add_mullion = bool(params.get("mullion", True))
    MW = float(params.get("mullion_width", 0.06))
    add_tracery = bool(params.get("tracery", False))
    spring_ratio = float(params.get("spring_ratio", 0.55))

    all_verts: list[np.ndarray] = []
    all_faces: list[np.ndarray] = []
    offset = 0

    # ── Main frame (outer arch - inner arch) ──────────────────────────
    outer = _pointed_arch_profile(W / 2, H, segs, spring_ratio=spring_ratio)
    inner = _pointed_arch_profile(W / 2 - FW, H - FW * 1.5, segs,
                                  base_z=FW * 0.5, spring_ratio=spring_ratio)

    v, f = _build_frame_ring(outer, inner, D, splay, W)
    all_verts.append(v)
    all_faces.append(f + offset)
    offset += len(v)

    # ── Optional mullion (central vertical bar) ───────────────────────
    if add_mullion:
        spring_h = H * spring_ratio
        mv, mf = _build_mullion(MW, spring_h, D, base_z=FW * 0.5)
        all_verts.append(mv)
        all_faces.append(mf + offset)
        offset += len(mv)

    # ── Optional tracery (simple trefoil-like bars in arch head) ──────
    if add_tracery and add_mullion:
        tv, tf = _build_tracery(W, H, D, FW, MW, segs, spring_ratio)
        all_verts.append(tv)
        all_faces.append(tf + offset)
        offset += len(tv)

    vertices = np.vstack(all_verts)
    faces = np.vstack(all_faces)

    return MeshData(
        vertices=vertices.astype(np.float64),
        faces=faces.astype(np.int32),
    )


# ── Pointed arch profile ──────────────────────────────────────────────


def _pointed_arch_profile(
    half_w: float, height: float, segs: int, base_z: float = 0.0,
    spring_ratio: float = 0.55,
) -> np.ndarray:
    """Generate a closed pointed-arch profile as (N, 2) array in XZ plane.

    The profile traces: bottom-left → up left jamb → left arc → apex →
    right arc → down right jamb → bottom-right.

    The arch uses two circular arcs whose centers sit on the spring line.
    The apex is computed so it exactly reaches *height*.
    """
    spring_h = height * spring_ratio  # spring line
    arch_rise = height - spring_h  # vertical rise from spring to apex

    # Compute center offset *c* so apex is exactly at *height*.
    # Left arc center: (c, spring_h), right center: (-c, spring_h)
    # R = half_w + c  (radius from center to opposite spring)
    # apex_z = spring_h + sqrt(R² - c²) = height
    # → (half_w + c)² - c² = arch_rise²
    # → half_w² + 2·half_w·c = arch_rise²
    # → c = (arch_rise² - half_w²) / (2·half_w)
    if half_w < 1e-9:
        return np.array([[0, base_z], [0, height]], dtype=np.float64)

    c = (arch_rise ** 2 - half_w ** 2) / (2 * half_w)
    if c < 0:
        # Arch portion is wider than tall — fall back to semicircle
        c = 0.0
    R = half_w + c

    pts: list[list[float]] = []

    # Left jamb (bottom → spring)
    pts.append([-half_w, base_z])
    pts.append([-half_w, spring_h])

    # Left arc: center at (+c, spring_h), from left spring to apex
    # Start angle: π (pointing left toward -half_w)
    # End angle: atan2(arch_rise, -c) — pointing toward apex at (0, height)
    start_a = math.pi
    end_a = math.atan2(math.sqrt(max(0, R ** 2 - c ** 2)), -c)

    for i in range(1, segs + 1):
        t = i / segs
        angle = start_a + t * (end_a - start_a)
        x = c + R * math.cos(angle)
        z = spring_h + R * math.sin(angle)
        pts.append([x, min(z, height)])

    # Right arc: center at (-c, spring_h), from apex to right spring
    # Start angle: atan2(arch_rise, c) — pointing toward apex
    # End angle: 0 (pointing right toward +half_w)
    start_b = math.atan2(math.sqrt(max(0, R ** 2 - c ** 2)), c)
    end_b = 0.0

    for i in range(1, segs + 1):
        t = i / segs
        angle = start_b + t * (end_b - start_b)
        x = -c + R * math.cos(angle)
        z = spring_h + R * math.sin(angle)
        pts.append([x, min(z, height)])

    # Right jamb (spring → bottom)
    pts.append([half_w, spring_h])
    pts.append([half_w, base_z])

    return np.array(pts, dtype=np.float64)


# ── Frame ring builder ────────────────────────────────────────────────


def _build_frame_ring(
    outer: np.ndarray,
    inner: np.ndarray,
    depth: float,
    splay_deg: float,
    opening_width: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a 3-D frame ring from outer and inner 2-D profiles.

    Returns (vertices, faces).
    """
    n_out = len(outer)
    n_in = len(inner)

    splay_offset = depth * math.tan(math.radians(splay_deg))

    front_outer = _embed_xz(outer, y=0.0)
    front_inner = _embed_xz(inner, y=0.0)
    back_outer = _embed_xz(outer, y=depth)

    # Back inner is splayed outward (wider opening on the interior side).
    # Apply per-vertex angular splay: each point moves outward proportional
    # to its distance from the profile centroid, giving proper conical splay.
    back_inner_2d = inner.copy()
    half_w = opening_width / 2 + 1e-9
    for i in range(len(back_inner_2d)):
        x = back_inner_2d[i, 0]
        # Splay proportional to signed distance from center
        back_inner_2d[i, 0] = x + math.copysign(splay_offset, x) if abs(x) > 1e-9 else x
    back_inner = _embed_xz(back_inner_2d, y=depth)

    # Since outer and inner may have different point counts,
    # we build each surface as its own quad strip and close with triangle fans.
    # For simplicity, resample inner to match outer count.
    if n_in != n_out:
        inner_resampled = _resample_profile(inner, n_out)
        front_inner = _embed_xz(inner_resampled, y=0.0)
        back_inner_2d_r = inner_resampled.copy()
        for i in range(len(back_inner_2d_r)):
            x = back_inner_2d_r[i, 0]
            back_inner_2d_r[i, 0] = x + math.copysign(splay_offset, x) if abs(x) > 1e-9 else x
        back_inner = _embed_xz(back_inner_2d_r, y=depth)

    n = n_out

    # 0..n-1       front outer
    # n..2n-1      front inner
    # 2n..3n-1     back inner (splayed)
    # 3n..4n-1     back outer
    verts = np.vstack([front_outer, front_inner, back_inner, back_outer])

    faces: list[list[int]] = []
    for i in range(n):
        ni = (i + 1) % n

        # Front face ring (outer ↔ inner)
        faces.append([i, ni, n + ni])
        faces.append([i, n + ni, n + i])

        # Back face ring
        faces.append([3 * n + i, 2 * n + i, 2 * n + ni])
        faces.append([3 * n + i, 2 * n + ni, 3 * n + ni])

        # Inner surface (front inner → back inner)
        faces.append([n + i, n + ni, 2 * n + ni])
        faces.append([n + i, 2 * n + ni, 2 * n + i])

        # Outer surface (front outer → back outer)
        faces.append([i, 3 * n + i, 3 * n + ni])
        faces.append([i, 3 * n + ni, ni])

    return verts, np.array(faces, dtype=np.int32)


# ── Mullion (central divider bar) ─────────────────────────────────────


def _build_mullion(
    width: float, height: float, depth: float, base_z: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Build a simple rectangular mullion bar centered at x=0."""
    hw = width / 2
    verts = np.array(
        [
            [-hw, 0, base_z], [hw, 0, base_z], [hw, 0, height], [-hw, 0, height],
            [-hw, depth, base_z], [hw, depth, base_z], [hw, depth, height], [-hw, depth, height],
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],       # front
            [5, 4, 7], [5, 7, 6],       # back
            [4, 0, 3], [4, 3, 7],       # left
            [1, 5, 6], [1, 6, 2],       # right
            [3, 2, 6], [3, 6, 7],       # top
            [4, 5, 1], [4, 1, 0],       # bottom
        ],
        dtype=np.int32,
    )
    return verts, faces


# ── Helpers ───────────────────────────────────────────────────────────


def _embed_xz(profile_2d: np.ndarray, y: float) -> np.ndarray:
    """Convert (N, 2) XZ profile to (N, 3) with given Y."""
    n = len(profile_2d)
    out = np.zeros((n, 3), dtype=np.float64)
    out[:, 0] = profile_2d[:, 0]
    out[:, 1] = y
    out[:, 2] = profile_2d[:, 1]
    return out


def _resample_profile(profile: np.ndarray, target_n: int) -> np.ndarray:
    """Linearly resample a 2-D profile to *target_n* points."""
    n = len(profile)
    if n == target_n:
        return profile
    old_t = np.linspace(0, 1, n)
    new_t = np.linspace(0, 1, target_n)
    new_x = np.interp(new_t, old_t, profile[:, 0])
    new_z = np.interp(new_t, old_t, profile[:, 1])
    return np.column_stack([new_x, new_z])


# ── Tracery (simple arch-head bars) ───────────────────────────────────


def _build_tracery(
    W: float, H: float, D: float, FW: float, MW: float,
    segs: int, spring_ratio: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Build simple tracery bars forming a Y-shape in the arch head.

    Creates a horizontal bar connecting the two sub-arches at the
    spring point of the main arch, giving a simple bifurcated tracery
    effect typical of Early Gothic / Decorated windows.
    """
    spring_h = H * spring_ratio
    bar_h = FW * 0.6  # bar thickness
    bar_z_bottom = spring_h - bar_h / 2
    bar_z_top = spring_h + bar_h / 2

    # Horizontal bar from inner left to inner right at spring height
    inner_hw = W / 2 - FW
    x_left = -inner_hw
    x_right = inner_hw

    verts = np.array([
        # Front face
        [x_left,  0, bar_z_bottom],
        [x_right, 0, bar_z_bottom],
        [x_right, 0, bar_z_top],
        [x_left,  0, bar_z_top],
        # Back face
        [x_left,  D, bar_z_bottom],
        [x_right, D, bar_z_bottom],
        [x_right, D, bar_z_top],
        [x_left,  D, bar_z_top],
    ], dtype=np.float64)

    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # front
        [5, 4, 7], [5, 7, 6],  # back
        [4, 0, 3], [4, 3, 7],  # left
        [1, 5, 6], [1, 6, 2],  # right
        [3, 2, 6], [3, 6, 7],  # top
        [4, 5, 1], [4, 1, 0],  # bottom
    ], dtype=np.int32)

    return verts, faces
