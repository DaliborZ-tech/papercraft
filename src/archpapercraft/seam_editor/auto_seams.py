"""Automatic seam generation based on dihedral angles and page-size limits."""

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
) -> SeamGraph:
    """Generate seams automatically.

    Strategy:
    1. Mark every edge whose dihedral angle exceeds *sharp_angle_deg*.
    2. If any resulting part exceeds *max_part_extent_mm* (after applying
       *scale*), iteratively split along the longest edge until it fits.

    Returns a populated :class:`SeamGraph`.
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

    # ── step 1: sharp-angle seams ─────────────────────────────────────
    for edge, faces in edge_faces.items():
        if len(faces) != 2:
            # boundary edge → always a seam
            sg.add_seam(*edge)
            continue
        n0, n1 = normals[faces[0]], normals[faces[1]]
        dot = float(np.clip(np.dot(n0, n1), -1.0, 1.0))
        angle = math.degrees(math.acos(dot))
        if angle >= sharp_angle_deg:
            sg.add_seam(*edge)

    # ── step 2: size-limit splitting (simple heuristic) ──────────────
    _split_oversize_parts(sg, max_part_extent_mm, scale, edge_faces, normals)

    return sg


def _split_oversize_parts(
    sg: SeamGraph,
    limit_mm: float,
    scale: float,
    edge_faces: dict[Edge, list[int]],
    normals: np.ndarray,
    max_iters: int = 50,
) -> None:
    """Split parts that are too large by adding seams on internal edges."""
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
