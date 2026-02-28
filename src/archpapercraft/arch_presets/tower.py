"""Generátor věže (Tower) — polygonální nebo válcový půdorys.

Věž se skládá z:
- tělesa (válec nebo N-úhelníkový hranol)
- volitelné římsy (lip) na vrchu
- opakovaných pater (segmentace výšky)
"""

from __future__ import annotations

import math

import numpy as np

from archpapercraft.core_geometry.primitives import (
    MeshData,
    make_box_mesh,
    make_cylinder_mesh,
    make_ngon_profile,
)
from archpapercraft.core_geometry.operations import (
    boolean_union_mesh,
    extrude_profile_mesh,
    translate_mesh,
)


def generate_tower(
    shape: str = "cylindrical",
    radius: float = 2.0,
    height: float = 10.0,
    sides: int = 8,
    segments: int = 32,
    floors: int = 3,
    cornice_height: float = 0.3,
    cornice_overhang: float = 0.2,
) -> MeshData:
    """Vytvoří mesh věže.

    Parametry
    ---------
    shape : str
        ``"cylindrical"`` nebo ``"polygonal"``.
    radius : float
        Poloměr (nebo opsaná kružnice u polygonu).
    height : float
        Celková výška věže.
    sides : int
        Počet stran (jen pro polygonal).
    segments : int
        Počet segmentů (jen pro cylindrical).
    floors : int
        Počet pater (vizuální segmentace).
    cornice_height : float
        Výška římsy na vrchu.
    cornice_overhang : float
        Přesah římsy.
    """
    # Hlavní těleso
    if shape == "cylindrical":
        body = make_cylinder_mesh(radius, height, segments)
    else:
        # Polygonální — extrude N-gon profilu
        profile = make_ngon_profile(radius, sides)
        direction = np.array([0.0, 0.0, 1.0])
        body = extrude_profile_mesh(profile, direction, height)

    # Římsa na vrchu
    if cornice_height > 0 and cornice_overhang > 0:
        r_cornice = radius + cornice_overhang
        if shape == "cylindrical":
            cornice = make_cylinder_mesh(r_cornice, cornice_height, segments)
        else:
            cp = make_ngon_profile(r_cornice, sides)
            cornice = extrude_profile_mesh(
                cp, np.array([0.0, 0.0, 1.0]), cornice_height
            )
        cornice = translate_mesh(cornice, np.array([0.0, 0.0, height]))
        body = boolean_union_mesh(body, cornice)

    return body
