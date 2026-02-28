"""Onion dome (cibulka) preset — body of revolution from a parametric profile.

The classic onion dome shape is defined by:
- A "neck" (narrow cylinder at the base)
- A bulge that widens then narrows
- A pointed tip

The profile is revolved around the vertical axis using the core_geometry
revolve function.  The preset also stores the 2-D profile so the unfolder
can use the gore / ring strategies directly without triangulating first.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from archpapercraft.core_geometry.operations import revolve_profile_mesh
from archpapercraft.core_geometry.primitives import MeshData


# ── Built-in profile presets ───────────────────────────────────────────

def _default_onion_profile(
    height: float = 5.0,
    max_radius: float = 2.0,
    neck_radius: float = 0.8,
    neck_height_frac: float = 0.15,
    bulge_height_frac: float = 0.55,
    tip_height_frac: float = 0.30,
    n_points: int = 40,
) -> np.ndarray:
    """Generate the 2-D profile curve for a classic onion dome.

    Returns (N, 2) array where column 0 = radius, column 1 = Z height.
    """
    pts: list[list[float]] = []
    total_pts = n_points

    neck_h = height * neck_height_frac
    bulge_h = height * bulge_height_frac
    tip_h = height * tip_height_frac

    # Neck section (straight / slight taper)
    neck_pts = max(3, int(total_pts * neck_height_frac))
    for i in range(neck_pts):
        t = i / max(neck_pts - 1, 1)
        z = t * neck_h
        r = neck_radius
        pts.append([r, z])

    # Bulge section (sine-like swell)
    bulge_pts = max(5, int(total_pts * bulge_height_frac))
    for i in range(bulge_pts):
        t = i / max(bulge_pts - 1, 1)
        z = neck_h + t * bulge_h
        # smooth swell from neck_radius to max_radius and back
        r = neck_radius + (max_radius - neck_radius) * math.sin(t * math.pi)
        pts.append([r, z])

    # Tip section (tapering to zero)
    tip_pts = max(3, int(total_pts * tip_height_frac))
    # start radius = last radius of bulge section
    start_r = pts[-1][0] if pts else neck_radius
    for i in range(1, tip_pts + 1):
        t = i / tip_pts
        z = neck_h + bulge_h + t * tip_h
        r = start_r * (1 - t) ** 1.5  # power curve for pointed tip
        pts.append([max(r, 0.0), z])

    return np.array(pts, dtype=np.float64)


# ── Main generator ─────────────────────────────────────────────────────

def generate_onion_dome(params: dict[str, Any]) -> MeshData:
    """Generate an onion-dome mesh by revolving a profile curve.

    Parameters
    ----------
    height : float          Total dome height (default 5.0).
    max_radius : float      Maximum bulge radius (default 2.0).
    neck_radius : float     Neck cylinder radius (default 0.8).
    neck_frac : float       Fraction of height for neck (default 0.15).
    bulge_frac : float      Fraction of height for bulge (default 0.55).
    segments : int          Number of revolution segments (default 24).
    profile_points : int    Number of profile curve points (default 40).
    """
    height = float(params.get("height", 5.0))
    max_r = float(params.get("max_radius", 2.0))
    neck_r = float(params.get("neck_radius", 0.8))
    neck_frac = float(params.get("neck_frac", 0.15))
    bulge_frac = float(params.get("bulge_frac", 0.55))
    segments = int(params.get("segments", 24))
    prof_pts = int(params.get("profile_points", 40))

    profile = _default_onion_profile(
        height=height,
        max_radius=max_r,
        neck_radius=neck_r,
        neck_height_frac=neck_frac,
        bulge_height_frac=bulge_frac,
        n_points=prof_pts,
    )

    mesh = revolve_profile_mesh(profile, segments=segments, angle_deg=360.0)
    return mesh


def get_onion_profile(params: dict[str, Any]) -> np.ndarray:
    """Return the 2-D profile curve for gore/ring unfolding strategies.

    Same parameters as :func:`generate_onion_dome`.
    """
    return _default_onion_profile(
        height=float(params.get("height", 5.0)),
        max_radius=float(params.get("max_radius", 2.0)),
        neck_radius=float(params.get("neck_radius", 0.8)),
        neck_height_frac=float(params.get("neck_frac", 0.15)),
        bulge_height_frac=float(params.get("bulge_frac", 0.55)),
        n_points=int(params.get("profile_points", 40)),
    )
