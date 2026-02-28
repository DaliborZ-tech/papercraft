"""Generátor opěrného pilíře (Buttress) — typický gotický prvek.

Opěrný pilíř je zjednodušený jako klín (wedge) — kvádr se zúžením směrem nahoru.
"""

from __future__ import annotations

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


def generate_buttress(
    width: float = 1.0,
    depth_bottom: float = 2.0,
    depth_top: float = 0.5,
    height: float = 5.0,
) -> MeshData:
    """Vytvoří klínovitý opěrný pilíř.

    Parametry
    ---------
    width : float
        Šířka pilíře (Y).
    depth_bottom : float
        Hloubka u paty (X).
    depth_top : float
        Hloubka na vrchu (X) — menší = zúžení.
    height : float
        Výška pilíře (Z).
    """
    hw = width / 2

    # Spodní obdélník
    v0 = [0.0, -hw, 0.0]
    v1 = [depth_bottom, -hw, 0.0]
    v2 = [depth_bottom, +hw, 0.0]
    v3 = [0.0, +hw, 0.0]
    # Horní obdélník (zúžený v X)
    v4 = [0.0, -hw, height]
    v5 = [depth_top, -hw, height]
    v6 = [depth_top, +hw, height]
    v7 = [0.0, +hw, height]

    verts = np.array([v0, v1, v2, v3, v4, v5, v6, v7], dtype=np.float64)
    faces = np.array([
        # Spodek
        [0, 2, 1], [0, 3, 2],
        # Vršek
        [4, 5, 6], [4, 6, 7],
        # Přední stěna (X=0)
        [0, 4, 7], [0, 7, 3],
        # Zadní stěna (X=depth)
        [1, 2, 6], [1, 6, 5],
        # Levá stěna (Y=-hw)
        [0, 1, 5], [0, 5, 4],
        # Pravá stěna (Y=+hw)
        [2, 3, 7], [2, 7, 6],
    ], dtype=np.int32)

    return MeshData(vertices=verts, faces=faces)
