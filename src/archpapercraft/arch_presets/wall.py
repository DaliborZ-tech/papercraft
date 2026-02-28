"""Wall preset — a rectangular solid described by length, height, thickness."""

from __future__ import annotations

from typing import Any

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


def generate_wall(params: dict[str, Any]) -> MeshData:
    """Generate mesh for a wall.

    Parameters (from ``params`` dict):
    - ``length``    (float, default 10.0)
    - ``height``    (float, default 3.0)
    - ``thickness`` (float, default 0.3)
    """
    L = float(params.get("length", 10.0))
    H = float(params.get("height", 3.0))
    T = float(params.get("thickness", 0.3))

    # 8 corners of the wall box
    verts = np.array(
        [
            [0, 0, 0],      # 0 — front bottom left
            [L, 0, 0],      # 1 — front bottom right
            [L, 0, H],      # 2 — front top right
            [0, 0, H],      # 3 — front top left
            [0, T, 0],      # 4 — back bottom left
            [L, T, 0],      # 5 — back bottom right
            [L, T, H],      # 6 — back top right
            [0, T, H],      # 7 — back top left
        ],
        dtype=np.float64,
    )

    faces = np.array(
        [
            # front
            [0, 1, 2], [0, 2, 3],
            # back
            [5, 4, 7], [5, 7, 6],
            # left
            [4, 0, 3], [4, 3, 7],
            # right
            [1, 5, 6], [1, 6, 2],
            # top
            [3, 2, 6], [3, 6, 7],
            # bottom
            [4, 5, 1], [4, 1, 0],
        ],
        dtype=np.int32,
    )

    return MeshData(vertices=verts, faces=faces)
