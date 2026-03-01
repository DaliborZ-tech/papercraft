"""Přesné rozložení pro rovinné a rozvinutelné (válcové / kuželové) plochy.

Základní algoritmus (BFS hranové rozložení):
  1. Zvol počáteční trojúhelník, polož ho na 2D rovinu.
  2. BFS přes graf sousednosti ploch (v rámci stejného dílu).
  3. Pro každý nový trojúhelník sdílející hranu s již položeným
     zrcadlí nový vrchol přes sdílenou hranu na opačnou stranu
     od rodičovského trojúhelníku.

Klíčové invarianty:
  - Každý 3D vertex může mít v rozložení VÍCE 2D kopií (duplikace
    na hranicích švů i při rozbalování kolem vrcholů).
  - Pozice sdílené hrany se bere z rodičovského trojúhelníku
    (face_2d_map), ne z globální mapy.
  - Nový vertex se vždy klade na OPAČNOU stranu sdílené hrany
    od třetího vrcholu rodiče (správné zrcadlení).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from archpapercraft.core_geometry.primitives import MeshData


def _face_normal(mesh: MeshData, fi: int) -> NDArray[np.float64]:
    """Compute face normal for triangle *fi*."""
    tri = mesh.faces[fi]
    v0, v1, v2 = mesh.vertices[tri[0]], mesh.vertices[tri[1]], mesh.vertices[tri[2]]
    n = np.cross(v1 - v0, v2 - v0)
    length = float(np.linalg.norm(n))
    return n / length if length > 1e-15 else np.array([0.0, 0.0, 1.0])


def _compute_dihedral(
    mesh: MeshData,
    fi_a: int,
    fi_b: int,
    shared_edge: tuple[int, int],
) -> float:
    """Compute signed dihedral angle in degrees between two adjacent faces.

    Positive → mountain (convex), negative → valley (concave).
    """
    n_a = _face_normal(mesh, fi_a)
    n_b = _face_normal(mesh, fi_b)

    # Edge direction vector
    e0, e1 = shared_edge
    edge_dir = mesh.vertices[e1] - mesh.vertices[e0]
    edge_len = float(np.linalg.norm(edge_dir))
    if edge_len < 1e-15:
        return 0.0
    edge_dir = edge_dir / edge_len

    # Signed angle: use cross product projected onto edge direction
    cross = np.cross(n_a, n_b)
    sin_val = float(np.dot(cross, edge_dir))
    cos_val = float(np.dot(n_a, n_b))

    angle_rad = float(np.arctan2(sin_val, cos_val))
    return float(np.degrees(angle_rad))


@dataclass
class UnfoldedPart:
    """Výsledek rozložení jednoho spojeného dílu."""

    part_id: int
    # 2-D vertex positions  (K, 2)
    vertices_2d: NDArray[np.float64]
    # triangle indices into vertices_2d  (T, 3)
    faces: NDArray[np.int32]
    # mapping from 2-D vertex index → original 3-D vertex index
    vert_map_3d: NDArray[np.int32]
    # edges classified as fold (mountain/valley) or cut
    fold_edges: list[tuple[int, int]] = field(default_factory=list)
    cut_edges: list[tuple[int, int]] = field(default_factory=list)
    # mapping: 2D cut edge (i,j) → 3D edge (a,b) for tab match IDs
    cut_edge_3d_map: dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)
    # dihedral angle (radians→degrees) for each fold edge (sorted 2D key)
    fold_dihedral_angles: dict[tuple[int, int], float] = field(default_factory=dict)


def unfold_part(
    mesh: MeshData,
    face_indices: list[int],
    seam_edges: set[tuple[int, int]] | None = None,
    part_id: int = 0,
) -> UnfoldedPart:
    """Rozloží spojený díl do 2D roviny BFS hranovým rozložením.

    Každý trojúhelník se zrcadlí přes sdílenou hranu na opačnou
    stranu od rodičovského trojúhelníku.  Každý face si pamatuje
    vlastní mapování 3D→2D vertexů (``face_2d_map``), čímž se
    správně řeší duplikace vrcholů.

    Parameters
    ----------
    mesh
        Celý mesh (vertexy sdíleny přes díly).
    face_indices
        Indexy faces patřící tomuto dílu (spojená komponenta).
    seam_edges
        Set švových hran (setříděné tuple); hrany MIMO tuto množinu
        jsou přehybové čáry.
    part_id
        Identifikátor dílu.
    """
    if seam_edges is None:
        seam_edges = set()

    face_set = set(face_indices)

    # ── lokální sousednost (v rámci dílu) ─────────────────────────
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for fi in face_indices:
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            edge_faces.setdefault(e, []).append(fi)

    # ── výstupní seznamy ──────────────────────────────────────────
    verts_2d_list: list[NDArray[np.float64]] = []   # (2,) pole
    vert_map_3d_list: list[int] = []
    fold_edges: list[tuple[int, int]] = []
    cut_edges: list[tuple[int, int]] = []
    cut_edge_3d_map: dict[tuple[int, int], tuple[int, int]] = {}
    fold_dihedral_angles: dict[tuple[int, int], float] = {}

    # face_2d_map[fi] = {3d_vidx: 2d_vidx}  — pro každý face
    face_2d_map: dict[int, dict[int, int]] = {}

    def _alloc_vertex(pos_2d: NDArray[np.float64], v3d: int) -> int:
        idx = len(verts_2d_list)
        verts_2d_list.append(pos_2d)
        vert_map_3d_list.append(v3d)
        return idx

    # ── položení prvního trojúhelníku ─────────────────────────────
    start = face_indices[0]
    tri0 = mesh.faces[start]
    v3 = [int(tri0[0]), int(tri0[1]), int(tri0[2])]
    p0, p1, p2 = mesh.vertices[v3[0]], mesh.vertices[v3[1]], mesh.vertices[v3[2]]

    d01 = float(np.linalg.norm(p1 - p0))
    d02 = float(np.linalg.norm(p2 - p0))
    d12 = float(np.linalg.norm(p2 - p1))

    pos_a = np.array([0.0, 0.0])
    pos_b = np.array([d01, 0.0])
    cos_a = np.clip((d01**2 + d02**2 - d12**2) / (2.0 * d01 * d02 + 1e-15), -1.0, 1.0)
    sin_a = float(np.sqrt(max(0.0, 1.0 - float(cos_a) ** 2)))
    pos_c = np.array([d02 * float(cos_a), d02 * sin_a])

    i_a = _alloc_vertex(pos_a, v3[0])
    i_b = _alloc_vertex(pos_b, v3[1])
    i_c = _alloc_vertex(pos_c, v3[2])
    face_2d_map[start] = {v3[0]: i_a, v3[1]: i_b, v3[2]: i_c}

    # ── BFS fronta: (face_to_visit, parent_face, shared_edge_3d) ──
    visited: set[int] = {start}
    queue: deque[tuple[int, int, tuple[int, int]]] = deque()

    def _enqueue_neighbors(fi: int) -> None:
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            if e in seam_edges:
                # šev → cut edge
                local = face_2d_map[fi]
                if e[0] in local and e[1] in local:
                    ce = (local[e[0]], local[e[1]])
                    cut_edges.append(ce)
                    cut_edge_3d_map[ce] = e
                continue
            for nb in edge_faces.get(e, []):
                if nb in visited or nb not in face_set:
                    continue
                visited.add(nb)
                queue.append((nb, fi, e))

    _enqueue_neighbors(start)

    # ── BFS ───────────────────────────────────────────────────────
    while queue:
        fi, parent_fi, shared_3d = queue.popleft()
        tri = mesh.faces[fi]
        tri_list = [int(tri[0]), int(tri[1]), int(tri[2])]

        a_3d, b_3d = shared_3d
        new_3d = [v for v in tri_list if v not in shared_3d][0]

        # 2D pozice sdílené hrany Z RODIČE
        parent_map = face_2d_map[parent_fi]
        a_2d_idx = parent_map[a_3d]
        b_2d_idx = parent_map[b_3d]
        a_2d = verts_2d_list[a_2d_idx]
        b_2d = verts_2d_list[b_2d_idx]

        # 3D vzdálenosti
        p_new = mesh.vertices[new_3d]
        p_a = mesh.vertices[a_3d]
        p_b = mesh.vertices[b_3d]
        da = float(np.linalg.norm(p_new - p_a))
        db = float(np.linalg.norm(p_new - p_b))
        d_ab = float(np.linalg.norm(b_2d - a_2d))

        # úhel u A mezi AB a A→new  (kosinová věta)
        cos_ang = np.clip(
            (d_ab**2 + da**2 - db**2) / (2.0 * d_ab * da + 1e-15),
            -1.0, 1.0,
        )
        sin_ang = float(np.sqrt(max(0.0, 1.0 - float(cos_ang) ** 2)))

        # jednotkový vektor A→B a kolmice
        ab = b_2d - a_2d
        ab_norm = ab / (np.linalg.norm(ab) + 1e-15)
        perp = np.array([-ab_norm[1], ab_norm[0]])

        # Třetí vertex RODIČE — ten leží na jedné straně sdílené hrany.
        # Nový vertex musí být na OPAČNÉ straně.
        parent_third_3d = [
            v for v in [int(mesh.faces[parent_fi][k]) for k in range(3)]
            if v not in shared_3d
        ][0]
        parent_third_2d = verts_2d_list[parent_map[parent_third_3d]]
        side_parent = float(np.dot(parent_third_2d - a_2d, perp))

        if side_parent >= 0:
            new_2d = a_2d + da * (float(cos_ang) * ab_norm - sin_ang * perp)
        else:
            new_2d = a_2d + da * (float(cos_ang) * ab_norm + sin_ang * perp)

        new_2d_idx = _alloc_vertex(new_2d, new_3d)

        # Mapování pro tento face
        face_2d_map[fi] = {a_3d: a_2d_idx, b_3d: b_2d_idx, new_3d: new_2d_idx}

        # Fold edge = sdílená hrana (přehyb)
        fold_edges.append((a_2d_idx, b_2d_idx))

        # Compute dihedral angle between parent face and this face
        _dihedral = _compute_dihedral(mesh, parent_fi, fi, shared_3d)
        fold_dihedral_angles[tuple(sorted((a_2d_idx, b_2d_idx)))] = _dihedral

        # Pokračuj BFS
        _enqueue_neighbors(fi)

    # ── Sestavení výstupních polí ─────────────────────────────────
    faces_2d: list[list[int]] = []
    for fi in face_indices:
        if fi not in face_2d_map:
            continue
        tri = mesh.faces[fi]
        local = face_2d_map[fi]
        faces_2d.append([local[int(tri[0])], local[int(tri[1])], local[int(tri[2])]])

    verts_2d = np.array(verts_2d_list, dtype=np.float64) if verts_2d_list else np.empty((0, 2), dtype=np.float64)
    vert_map = np.array(vert_map_3d_list, dtype=np.int32) if vert_map_3d_list else np.empty(0, dtype=np.int32)

    return UnfoldedPart(
        part_id=part_id,
        vertices_2d=verts_2d,
        faces=np.array(faces_2d, dtype=np.int32) if faces_2d else np.empty((0, 3), dtype=np.int32),
        vert_map_3d=vert_map,
        fold_edges=fold_edges,
        cut_edges=cut_edges,
        cut_edge_3d_map=cut_edge_3d_map,
        fold_dihedral_angles=fold_dihedral_angles,
    )
