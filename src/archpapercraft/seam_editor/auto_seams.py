"""Automatické generování švů podle dihedrálních úhlů, velikostních limitů
a architektonických pravidel.

Algoritmus:
  1. Ohodnotí každou vnitřní hranu váhou (ostrý úhel → vysoká váha, "architektonická"
     hrana → střední váha, hladká hrana → nízká váha).
  2. Najde **minimální kostru** (Prim) grafu sousednosti ploch — hrany v kostře
     zůstanou přehyby (folds), ostatní se stanou švy (seams).
     Minimum‐cost preferuje hladké hrany jako přehyby a ostré hrany jako švy.
  3. Okrajové hrany (jen 1 sousedící plocha) jsou vždy švy.
  4. Po-kostrovém kroku se ještě iterativně dělí příliš velké díly.

Pravidla pro architekturu:
- Střecha se dělí po hřebeni a úžlabí
- Zdi se dělí v rozích
- Okna/otvory se dělí po obrysu
"""

from __future__ import annotations

import heapq
import math

import numpy as np

from archpapercraft.core_geometry.mesh import compute_face_normals
from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.seam_editor.seam_graph import Edge, SeamGraph


# Váhy pro priority hran ve spanning tree
_WEIGHT_SMOOTH = 0     # hladká hrana → preferujeme jako přehyb
_WEIGHT_ARCH = 50      # architektonická hrana → preferujeme jako šev
_WEIGHT_SHARP = 100    # ostrá hrana → silně preferujeme jako šev


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

    Strategie (spanning-tree):
    1. Ohodnotí hrany (ostrá → vysoká váha, hladká → nízká váha).
    2. Najde minimální kostru grafu ploch — hrany kostry = přehyby,
       zbylé = švy.  To garantuje, že každý díl je *spojitý*.
    3. Pokud jakýkoli díl přesáhne *max_part_extent_mm* (po *scale*),
       iterativně dělí podél nejdelší fold-hrany.

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

    # ── krok 1: ohodnotit hrany ──────────────────────────────────────
    edge_weight: dict[Edge, int] = {}
    boundary_edges: set[Edge] = set()

    for edge, faces in edge_faces.items():
        if len(faces) != 2:
            # Okrajová hrana → vždy šev (nemůže být v kostře)
            boundary_edges.add(edge)
            continue

        # Dihedrální úhel
        n0, n1 = normals[faces[0]], normals[faces[1]]
        dot = float(np.clip(np.dot(n0, n1), -1.0, 1.0))
        angle = math.degrees(math.acos(dot))

        if angle >= sharp_angle_deg:
            edge_weight[edge] = _WEIGHT_SHARP
        else:
            edge_weight[edge] = _WEIGHT_SMOOTH

    # ── krok 2: architektonické váhy ──────────────────────────────────
    if architecture_rules:
        _apply_architecture_weights(edge_weight, edge_faces, normals)

    # ── krok 3: minimální kostra (Prim) → fold hrany ─────────────────
    # Stavíme graf sousednosti ploch. Hrana mezi plochami má váhu z edge_weight.
    # Kostra určí, které hrany zůstanou přehyby (fold).
    # Hrany MIMO kostru = švy (seams).

    face_adj: dict[int, list[tuple[int, Edge]]] = {}
    for edge, faces in edge_faces.items():
        if len(faces) == 2 and edge not in boundary_edges:
            f0, f1 = faces
            face_adj.setdefault(f0, []).append((f1, edge))
            face_adj.setdefault(f1, []).append((f0, edge))

    num_faces = mesh.num_faces
    in_tree = [False] * num_faces
    tree_edges: set[Edge] = set()

    # Spustíme Prim z každé dosud nenavštívené plochy
    # (mesh může mít více komponent)
    for start in range(num_faces):
        if in_tree[start]:
            continue
        in_tree[start] = True
        heap: list[tuple[int, int, int, Edge]] = []  # (weight, tiebreak, face, edge)
        for neighbor, edge in face_adj.get(start, []):
            w = edge_weight.get(edge, _WEIGHT_SMOOTH)
            heapq.heappush(heap, (w, id(edge), neighbor, edge))

        while heap:
            w, _, face, edge = heapq.heappop(heap)
            if in_tree[face]:
                continue
            in_tree[face] = True
            tree_edges.add(edge)
            for neighbor, e in face_adj.get(face, []):
                if not in_tree[neighbor]:
                    we = edge_weight.get(e, _WEIGHT_SMOOTH)
                    heapq.heappush(heap, (we, id(e), neighbor, e))

    # Hrany mimo kostru + okrajové → švy
    for edge in boundary_edges:
        sg.add_seam(*edge)
    for edge in edge_faces:
        if edge not in tree_edges and edge not in boundary_edges:
            sg.add_seam(*edge)

    # ── krok 4: dělení příliš velkých dílů ────────────────────────────
    _split_oversize_parts(sg, max_part_extent_mm, scale, edge_faces, normals)

    return sg


def _apply_architecture_weights(
    edge_weight: dict[Edge, int],
    edge_faces: dict[Edge, list[int]],
    normals: np.ndarray,
) -> None:
    """Zvýší váhu architektonicky významných hran (hřebeny, okapnice, rohy zdí).

    Hrany s vyšší váhou budou preferovány jako švy ve spanning-tree algoritmu.
    """
    UP = np.array([0.0, 0.0, 1.0])
    RIDGE_DOT_THRESHOLD = 0.3
    EAVE_VERTICAL_THRESHOLD = 0.7
    WALL_CORNER_DEG = 45.0

    for edge, faces in edge_faces.items():
        if len(faces) != 2:
            continue

        n0, n1 = normals[faces[0]], normals[faces[1]]
        dz0 = abs(float(np.dot(n0, UP)))
        dz1 = abs(float(np.dot(n1, UP)))

        # Hřebenová hrana
        if dz0 > RIDGE_DOT_THRESHOLD and dz1 > RIDGE_DOT_THRESHOLD:
            cross = np.cross(n0, n1)
            if abs(float(cross[2])) > 0.5:
                edge_weight[edge] = max(edge_weight.get(edge, 0), _WEIGHT_ARCH)
                continue

        # Okapnice
        is_wall_0 = dz0 < 0.3
        is_wall_1 = dz1 < 0.3
        is_roof_0 = 0.3 < dz0 < EAVE_VERTICAL_THRESHOLD
        is_roof_1 = 0.3 < dz1 < EAVE_VERTICAL_THRESHOLD
        if (is_wall_0 and is_roof_1) or (is_wall_1 and is_roof_0):
            edge_weight[edge] = max(edge_weight.get(edge, 0), _WEIGHT_ARCH)
            continue

        # Svislé rohy zdí
        if is_wall_0 and is_wall_1:
            dot = float(np.clip(np.dot(n0, n1), -1.0, 1.0))
            angle = math.degrees(math.acos(dot))
            if angle >= WALL_CORNER_DEG:
                edge_weight[edge] = max(edge_weight.get(edge, 0), _WEIGHT_ARCH)


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
