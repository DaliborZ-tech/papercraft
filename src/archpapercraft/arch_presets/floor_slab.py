"""Generátor desky podlahy / stropu (Floor/Slab).

Jednoduchý kvádr se zadanou délkou, šířkou a tloušťkou.
"""

from __future__ import annotations

from archpapercraft.core_geometry.primitives import MeshData, make_box_mesh
from archpapercraft.core_geometry.operations import translate_mesh

import numpy as np


def generate_floor_slab(
    length: float = 10.0,
    width: float = 8.0,
    thickness: float = 0.2,
) -> MeshData:
    """Vytvoří desku podlahy/stropu.

    Parametry
    ---------
    length : float
        Délka desky (X).
    width : float
        Šířka desky (Y).
    thickness : float
        Tloušťka desky (Z).
    """
    mesh = make_box_mesh(length, width, thickness)
    # Posunout tak, aby spodek desky ležel na Z=0
    return translate_mesh(mesh, np.array([0.0, 0.0, thickness / 2]))
