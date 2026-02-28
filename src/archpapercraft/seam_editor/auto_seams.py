"""Automatické generování švů podle dihedrálních úhlů, velikostních limitů
a architektonických pravidel.

Pravidla pro architekturu:
- Střecha se dělí po hřebeni a úžlabí
- Zdi se dělí v rozích
- Okna/otvory se dělí po obrysu
"""

from __future__ import annotations

import math

import numpy as np

from archpapercraft.core_geometry.mesh import compute_face_normals
from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.seam_editor.seam_graph import Edge, SeamGraph


def auto_seams(
    mesh: MeshData,
    sharp_angle_deg: float = 60.0,
    max_part_extent_mm: float = 250.0,
    scale: float = 1.0,
    *,
    architecture_rules: bool = True,
    locked_edges: set[Edge] | None = None,
) -> SeamGraph:
    """Automatické generování švů.

    Strategie:
    1. Označí každou hranu, jejíž dihedrální úhel přesáhne *sharp_angle_deg*.
    2. Pokud je *architecture_rules* True, aplikuje architektonické švy
       (hřebeny, okapnice, svislé hrany zdí).
    3. Pokud jakýkoli díl přesáhne *max_part_extent_mm* (po aplikaci *scale*),
       iterativně dělí podél nejdelší hrany.

    Vrací naplněný :class:`SeamGraph`.
    """
    normals = compute_face_normals(mesh)

    # ── build edge → face adjacency ───────────────────────────────────
    edge_faces: dict[Edge, list[int]] = {}
    for fi in range(mesh.num_faces):
        tri = mesh.faces[fi]
        for j in range(3):
            e: Edge = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))  # type: ignore[assignment]
            edge_faces.setdefault(e, []).append(fi)

    sg = SeamGraph(mesh=mesh)

    # Převezmi zamknuté hrany
    if locked_edges:
        sg.locked_edges = set(locked_edges)

    # ── krok 1: ostré hrany → švy ─────────────────────────────────────
    for edge, faces in edge_faces.items():
        if len(faces) != 2:
            # okrajová hrana → vždy šev
            sg.add_seam(*edge)
            continue
        n0, n1 = normals[faces[0]], normals[faces[1]]
        dot = float(np.clip(np.dot(n0, n1), -1.0, 1.0))
        angle = math.degrees(math.acos(dot))
        if angle >= sharp_angle_deg:
            sg.add_seam(*edge)

    # ── krok 2: architektonické švy ───────────────────────────────────
    if architecture_rules:
        _apply_architecture_rules(sg, edge_faces, normals)

    # ── krok 3: dělení příliš velkých dílů ────────────────────────────
    _split_oversize_parts(sg, max_part_extent_mm, scale, edge_faces, normals)

    return sg


def _apply_architecture_rules(
    sg: SeamGraph,
    edge_faces: dict[Edge, list[int]],
    normals: np.ndarray,
) -> None:
    """Aplikuje architektonická pravidla pro umísťování švů.

    Pravidla:
    - Hřebenové hrany (ridge): normály stoupají ze dvou stran → šev
    - Okapnice (eave): normála jedné strany je ~horizontální, druhá ~vertikální
    - Svislé rohy zdí: obě normály horizontální, úhel > 45°
    """
    UP = np.array([0.0, 0.0, 1.0])
    RIDGE_DOT_THRESHOLD = 0.3     # normály musí mít Z-komponentu
    EAVE_VERTICAL_THRESHOLD = 0.7  # |dot(n, UP)| pro detekci svislé plochy
    WALL_CORNER_DEG = 45.0

    for edge, faces in edge_faces.items():
        if len(faces) != 2:
            continue
        if sg.is_seam(edge[0], edge[1]):
            continue

        n0, n1 = normals[faces[0]], normals[faces[1]]
        dz0 = abs(float(np.dot(n0, UP)))
        dz1 = abs(float(np.dot(n1, UP)))

        # Hřebenová hrana: obě normály mají nenulovou Z-komponentu
        # a směřují různým směrem (jedna nahoru-vlevo, druhá nahoru-vpravo)
        if dz0 > RIDGE_DOT_THRESHOLD and dz1 > RIDGE_DOT_THRESHOLD:
            cross = np.cross(n0, n1)
            if abs(float(cross[2])) > 0.5:
                # normály se kříží v Z → hřebenová hrana
                sg.add_seam(*edge)
                continue

        # Okapnice: jedna plocha je střecha (šikmá), druhá stěna (svislá)
        is_wall_0 = dz0 < 0.3
        is_wall_1 = dz1 < 0.3
        is_roof_0 = 0.3 < dz0 < EAVE_VERTICAL_THRESHOLD
        is_roof_1 = 0.3 < dz1 < EAVE_VERTICAL_THRESHOLD
        if (is_wall_0 and is_roof_1) or (is_wall_1 and is_roof_0):
            sg.add_seam(*edge)
            continue

        # Svislé rohy zdí: obě normals ~horizontální, úhel > 45°
        if is_wall_0 and is_wall_1:
            dot = float(np.clip(np.dot(n0, n1), -1.0, 1.0))
            angle = math.degrees(math.acos(dot))
            if angle >= WALL_CORNER_DEG:
                sg.add_seam(*edge)


def _split_oversize_parts(
    sg: SeamGraph,
    limit_mm: float,
    scale: float,
    edge_faces: dict[Edge, list[int]],
    normals: np.ndarray,
    max_iters: int = 50,
) -> None:
    """Rozdělí díly, které jsou příliš velké, přidáním švů na interních hranách."""
    for _ in range(max_iters):
        parts = sg.compute_parts()
        any_split = False
        for part_faces in parts:
            # bounding-box extent of the part
            face_verts = sg.mesh.vertices[sg.mesh.faces[part_faces].ravel()]
            extent = (face_verts.max(axis=0) - face_verts.min(axis=0)) * scale
            max_extent = float(extent.max())

            if max_extent <= limit_mm:
                continue

            # Find the longest non-seam internal edge and mark as seam
            best_edge: Edge | None = None
            best_len = 0.0
            part_set = set(part_faces)
            for fi in part_faces:
                tri = sg.mesh.faces[fi]
                for j in range(3):
                    e: Edge = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))  # type: ignore[assignment]
                    if sg.is_seam(e[0], e[1]):
                        continue
                    v0 = sg.mesh.vertices[e[0]]
                    v1 = sg.mesh.vertices[e[1]]
                    length = float(np.linalg.norm(v1 - v0))
                    if length > best_len:
                        best_len = length
                        best_edge = e

            if best_edge is not None:
                sg.add_seam(*best_edge)
                any_split = True

        if not any_split:
            break
