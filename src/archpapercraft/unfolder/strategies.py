"""Approximate unfolding strategies for non-developable surfaces.

Three strategies:
- **Gores** (vertical strips): split the revolved surface into N meridian strips.
- **Rings** (horizontal bands): split into latitude rings.
- **Facets** (polygonization): just unfold the triangulated mesh facet-by-facet.
"""

from __future__ import annotations

import math
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

from archpapercraft.core_geometry.primitives import MeshData


class UnfoldStrategy(Enum):
    EXACT = auto()
    GORES = auto()
    RINGS = auto()
    FACETS = auto()


def extract_revolution_profile(
    mesh: MeshData,
    n_bins: int = 32,
) -> NDArray[np.float64] | None:
    """Try to extract a 2-D revolution profile ``(radius, z)`` from *mesh*.

    Works for cylinders, cones, spheres, domes, towers, etc.
    Returns *None* if the mesh does not appear rotationally symmetric.
    """
    verts = mesh.vertices
    if len(verts) < 3:
        return None

    radii = np.sqrt(verts[:, 0] ** 2 + verts[:, 1] ** 2)
    z = verts[:, 2]

    z_min, z_max = float(z.min()), float(z.max())
    if z_max - z_min < 1e-6:
        return None  # flat — not a revolution body

    # Angular distribution check: revolution bodies have many unique angles.
    # A box has only 4; a cylinder with 32 segments has 32.
    angles = np.arctan2(verts[:, 1], verts[:, 0])
    unique_angles = len(np.unique(np.round(angles, decimals=2)))
    if unique_angles < 8:
        return None  # too few angular positions → likely a prism, not revolution

    n_bins = min(n_bins, max(4, len(verts) // 4))
    z_edges = np.linspace(z_min, z_max, n_bins + 1)

    profile_r: list[float] = []
    profile_z: list[float] = []

    for i in range(n_bins):
        mask = (z >= z_edges[i]) & (z < z_edges[i + 1] + 1e-9)
        if not mask.any():
            continue
        bin_radii = radii[mask]
        mean_r = float(bin_radii.mean())
        std_r = float(bin_radii.std())
        # Coefficient of variation > 25 % ⇒ not rotationally symmetric
        if mean_r > 1e-6 and std_r / mean_r > 0.25:
            return None
        profile_r.append(mean_r)
        profile_z.append(float((z_edges[i] + z_edges[i + 1]) / 2))

    if len(profile_r) < 2:
        return None

    return np.column_stack([profile_r, profile_z]).astype(np.float64)


def generate_gores(
    profile_2d: NDArray[np.float64],
    num_gores: int = 16,
    angle_deg: float = 360.0,
) -> list[NDArray[np.float64]]:
    """Generate 2-D gore outlines for a surface-of-revolution.

    Parameters
    ----------
    profile_2d : (N, 2)
        Profile curve in the XZ plane [radius, z].
    num_gores : int
        Number of equal gores.
    angle_deg : float
        Total sweep angle (default 360).

    Returns
    -------
    list of (M, 2) arrays
        Each array is a closed 2-D polygon outline of one gore.
    """
    n_pts = len(profile_2d)
    gore_angle = math.radians(angle_deg) / num_gores

    gores: list[NDArray[np.float64]] = []

    for g in range(num_gores):
        # For each gore: compute the arc-length at each latitude as the flat width
        # and accumulate height along the profile
        left_pts: list[list[float]] = []
        right_pts: list[list[float]] = []
        cumulative_h = 0.0

        for i in range(n_pts):
            r = float(profile_2d[i, 0])
            if i > 0:
                dr = profile_2d[i, 0] - profile_2d[i - 1, 0]
                dz = profile_2d[i, 1] - profile_2d[i - 1, 1]
                cumulative_h += math.sqrt(float(dr**2 + dz**2))

            arc_half = r * gore_angle / 2.0
            left_pts.append([-arc_half, cumulative_h])
            right_pts.append([arc_half, cumulative_h])

        # close the gore polygon (right side reversed)
        outline = np.array(left_pts + right_pts[::-1], dtype=np.float64)
        gores.append(outline)

    return gores


def generate_rings(
    profile_2d: NDArray[np.float64],
    num_rings: int = 8,
    segments: int = 32,
) -> list[NDArray[np.float64]]:
    """Generate 2-D ring (band) outlines for a surface-of-revolution.

    Each ring is a rectangular strip that wraps around.  When cut open it
    becomes a trapezoid / strip.

    Returns list of (4, 2) arrays (trapezoid corners).
    """
    n_pts = len(profile_2d)
    ring_size = max(1, (n_pts - 1) // num_rings)

    rings: list[NDArray[np.float64]] = []
    for i in range(0, n_pts - 1, ring_size):
        j = min(i + ring_size, n_pts - 1)
        r_top = float(profile_2d[i, 0])
        r_bot = float(profile_2d[j, 0])
        h_segment = 0.0
        for k in range(i, j):
            dr = profile_2d[k + 1, 0] - profile_2d[k, 0]
            dz = profile_2d[k + 1, 1] - profile_2d[k, 1]
            h_segment += math.sqrt(float(dr**2 + dz**2))

        circ_top = 2 * math.pi * r_top
        circ_bot = 2 * math.pi * r_bot
        # trapezoid: bottom-left, bottom-right, top-right, top-left
        trap = np.array(
            [
                [0.0, 0.0],
                [circ_bot, 0.0],
                [circ_top + (circ_bot - circ_top) / 2, h_segment],  # offset centering
                [(circ_bot - circ_top) / 2, h_segment],
            ],
            dtype=np.float64,
        )
        rings.append(trap)

    return rings
