"""Deterministické identifikátory pro hrany, díly a uzly.

Klíčový problém: když se mesh mírně změní (přidá se vertex, přečíslují
se faces), nesmí se rozbít všechny edge-match ID, part ID atd.

Řešení: hash-based ID odvozené z *topologie* (geometrické pozice),
nikoli z pořadí v poli.

Použití::

    from archpapercraft.core_geometry.stable_ids import (
        edge_hash, part_hash, node_stable_id,
    )
"""

from __future__ import annotations

import hashlib
import struct

import numpy as np
from numpy.typing import NDArray

from archpapercraft.core_geometry.primitives import MeshData

# Přesnost zaokrouhlení souřadnic pro hash (v mm) — menší odchylky
# pod tuto mez se považují za identické.
_PRECISION_MM = 0.01


def _quantize(val: float) -> int:
    """Zaokrouhlí float na stabilní celočíselnou reprezentaci."""
    return round(val / _PRECISION_MM)


def _hash_ints(*values: int) -> str:
    """Vytvoří krátký deterministický hash z celočíselných hodnot."""
    data = struct.pack(f">{len(values)}q", *values)
    return hashlib.sha1(data).hexdigest()[:12]


# ======================================================================
#  Edge hash
# ======================================================================


def edge_hash(
    mesh: MeshData,
    v0_idx: int,
    v1_idx: int,
) -> str:
    """Stabilní hash hrany odvozený z geometrických pozic koncových bodů.

    Vrací 12-znakový hex string, který zůstane stejný, i když se
    změní číslování vertexů (pokud se nezmění souřadnice).
    """
    p0 = mesh.vertices[v0_idx]
    p1 = mesh.vertices[v1_idx]

    # Seřadíme body kanonicky (menší x, pak y, pak z)
    pts = sorted([(p0[0], p0[1], p0[2]), (p1[0], p1[1], p1[2])])
    ints = []
    for pt in pts:
        ints.extend(_quantize(c) for c in pt)
    return _hash_ints(*ints)


def edge_midpoint_hash(
    mesh: MeshData,
    v0_idx: int,
    v1_idx: int,
) -> str:
    """Hash hrany založený na středovém bodě — ještě robustnější."""
    p0 = mesh.vertices[v0_idx]
    p1 = mesh.vertices[v1_idx]
    mid = (p0 + p1) / 2.0
    length = float(np.linalg.norm(p1 - p0))
    ints = [_quantize(mid[0]), _quantize(mid[1]), _quantize(mid[2]),
            _quantize(length)]
    return _hash_ints(*ints)


# ======================================================================
#  Part hash (pro díly / connected components)
# ======================================================================


def part_hash(
    mesh: MeshData,
    face_indices: list[int],
) -> str:
    """Stabilní hash dílu odvozený z centroidu a plochy.

    Centroid = průměr středů všech faces dílu.
    Plocha = součet ploch trojúhelníků dílu.
    """
    if not face_indices:
        return "empty_part"

    centroids = []
    total_area = 0.0
    for fi in face_indices:
        tri = mesh.faces[fi]
        p0 = mesh.vertices[tri[0]]
        p1 = mesh.vertices[tri[1]]
        p2 = mesh.vertices[tri[2]]
        centroids.append((p0 + p1 + p2) / 3.0)
        total_area += 0.5 * float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))

    centroid = np.mean(centroids, axis=0)
    ints = [
        _quantize(centroid[0]),
        _quantize(centroid[1]),
        _quantize(centroid[2]),
        _quantize(total_area),
        len(face_indices),
    ]
    return _hash_ints(*ints)


# ======================================================================
#  Node stable ID
# ======================================================================


def node_stable_id(
    node_type: str,
    name: str,
    position: tuple[float, float, float] | NDArray[np.float64],
) -> str:
    """Stabilní ID uzlu scény odvozené z typu, jména a pozice.

    Používá se jako fallback, když uživatel nezadá vlastní ``node_id``.
    """
    data = f"{node_type}:{name}:{_quantize(position[0])}:{_quantize(position[1])}:{_quantize(position[2])}"
    return hashlib.sha1(data.encode()).hexdigest()[:16]


# ======================================================================
#  Hromadné přiřazení stabilních edge-match IDs
# ======================================================================


def compute_stable_edge_match_ids(
    mesh: MeshData,
    seam_edges: set[tuple[int, int]],
) -> dict[tuple[int, int], str]:
    """Vrátí dict { edge → stabilní hash ID } pro všechny švové hrany.

    Na rozdíl od sekvenčního číslování (1, 2, 3…) je tento hash
    stabilní i při změně pořadí hran v meshy.
    """
    result: dict[tuple[int, int], str] = {}
    for edge in seam_edges:
        result[edge] = edge_hash(mesh, edge[0], edge[1])
    return result
