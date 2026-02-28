"""Gabled (sedlová) roof preset."""

from __future__ import annotations

from typing import Any

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


def generate_gabled_roof(params: dict[str, Any]) -> MeshData:
    """Generate a gabled roof mesh.

    Parameters
    ----------
    width : float     Roof span (default 10.0).
    depth : float     Roof depth / length (default 8.0).
    height : float    Ridge height above the eaves (default 3.0).
    overhang : float  Eave overhang (default 0.5).
    thickness : float Roof panel thickness (default 0.1).
    """
    W = float(params.get("width", 10.0))
    D = float(params.get("depth", 8.0))
    H = float(params.get("height", 3.0))
    OH = float(params.get("overhang", 0.5))
    T = float(params.get("thickness", 0.1))

    hw = W / 2.0 + OH

    # Outer shell (6 vertices for gable prism)
    v = np.array(
        [
            # bottom left→right, front
            [-hw, 0, 0],            # 0
            [hw, 0, 0],             # 1
            [0, 0, H],              # 2 ridge front
            # back
            [-hw, D, 0],            # 3
            [hw, D, 0],             # 4
            [0, D, H],              # 5 ridge back
        ],
        dtype=np.float64,
    )

    faces = np.array(
        [
            # left slope
            [0, 3, 5], [0, 5, 2],
            # right slope
            [1, 2, 5], [1, 5, 4],
            # front gable
            [0, 2, 1],
            # back gable
            [3, 4, 5],
            # bottom (optional — for closed mesh)
            [0, 1, 4], [0, 4, 3],
        ],
        dtype=np.int32,
    )

    return MeshData(vertices=v, faces=faces)
