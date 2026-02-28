"""Exact unfolding for planar and developable (cylindrical / conical) patches.

Core algorithm (BFS edge-unfolding):
  1. Pick a seed triangle, lay it flat on the 2-D plane.
  2. BFS over the face-adjacency graph (within the same part).
  3. For each new triangle sharing an edge with an already-placed triangle,
     compute the 2-D position by reflecting across the shared edge.

This works without distortion for all planar patches and gives an acceptable
result for low-curvature developable patches.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from archpapercraft.core_geometry.primitives import MeshData


@dataclass
class UnfoldedPart:
    """Result of unfolding one connected part."""

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


def _lay_first_triangle(
    mesh: MeshData, face_idx: int
) -> tuple[NDArray[np.float64], dict[int, int]]:
    """Place the first triangle at the origin.  Returns (verts_2d, 3d→2d map)."""
    tri = mesh.faces[face_idx]
    p0 = mesh.vertices[tri[0]]
    p1 = mesh.vertices[tri[1]]
    p2 = mesh.vertices[tri[2]]

    # edge lengths
    d01 = float(np.linalg.norm(p1 - p0))
    d02 = float(np.linalg.norm(p2 - p0))
    d12 = float(np.linalg.norm(p2 - p1))

    # place v0 at origin, v1 on +X
    v0 = np.array([0.0, 0.0])
    v1 = np.array([d01, 0.0])

    # v2 by cosine rule
    cos_a = (d01**2 + d02**2 - d12**2) / (2 * d01 * d02 + 1e-15)
    cos_a = float(np.clip(cos_a, -1.0, 1.0))
    sin_a = float(np.sqrt(max(0.0, 1.0 - cos_a**2)))
    v2 = np.array([d02 * cos_a, d02 * sin_a])

    verts_2d = np.array([v0, v1, v2], dtype=np.float64)
    idx_map = {int(tri[0]): 0, int(tri[1]): 1, int(tri[2]): 2}
    return verts_2d, idx_map


def _place_triangle(
    mesh: MeshData,
    face_idx: int,
    shared_3d: tuple[int, int],
    verts_2d: NDArray[np.float64],
    idx_map: dict[int, int],
) -> tuple[NDArray[np.float64], dict[int, int]]:
    """Place a new triangle adjacent to one whose shared edge is already laid out."""
    tri = mesh.faces[face_idx]
    tri_list = [int(tri[0]), int(tri[1]), int(tri[2])]

    # identify the "new" vertex (not on the shared edge)
    new_3d = [v for v in tri_list if v not in shared_3d][0]

    a_3d, b_3d = shared_3d
    a_2d = verts_2d[idx_map[a_3d]]
    b_2d = verts_2d[idx_map[b_3d]]

    p_new = mesh.vertices[new_3d]
    p_a = mesh.vertices[a_3d]
    p_b = mesh.vertices[b_3d]

    da = float(np.linalg.norm(p_new - p_a))
    db = float(np.linalg.norm(p_new - p_b))
    d_ab = float(np.linalg.norm(b_2d - a_2d))

    # angle at A between edge AB and edge A→new
    cos_a = (d_ab**2 + da**2 - db**2) / (2 * d_ab * da + 1e-15)
    cos_a = float(np.clip(cos_a, -1.0, 1.0))
    sin_a = float(np.sqrt(max(0.0, 1.0 - cos_a**2)))

    # direction A→B in 2-D
    ab = b_2d - a_2d
    ab_norm = ab / (np.linalg.norm(ab) + 1e-15)
    perp = np.array([-ab_norm[1], ab_norm[0]])

    # place on the side opposite to any already-placed vertex (prefer left)
    new_2d = a_2d + da * (cos_a * ab_norm + sin_a * perp)

    new_idx = len(verts_2d)
    verts_2d = np.vstack([verts_2d, new_2d.reshape(1, 2)])
    idx_map[new_3d] = new_idx

    return verts_2d, idx_map


def unfold_part(
    mesh: MeshData,
    face_indices: list[int],
    seam_edges: set[tuple[int, int]] | None = None,
    part_id: int = 0,
) -> UnfoldedPart:
    """Unfold a connected set of faces onto a 2-D plane (BFS edge-unfolding).

    Parameters
    ----------
    mesh
        The full mesh (vertices shared across parts).
    face_indices
        Indices of faces belonging to this part (connected component).
    seam_edges
        Set of seam edges (sorted tuples); edges NOT in this set are fold-lines.
    part_id
        Identifier for this part.
    """
    if seam_edges is None:
        seam_edges = set()

    face_set = set(face_indices)

    # build local adjacency (within this part, non-seam edges)
    edge_local: dict[tuple[int, int], list[int]] = {}
    for fi in face_indices:
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            edge_local.setdefault(e, []).append(fi)

    # start with first face
    start = face_indices[0]
    verts_2d, idx_map = _lay_first_triangle(mesh, start)

    visited = {start}
    queue: deque[int] = deque([start])

    fold_edges: list[tuple[int, int]] = []
    cut_edges: list[tuple[int, int]] = []

    while queue:
        fi = queue.popleft()
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            if e in seam_edges:
                # this is a cut edge
                if e[0] in idx_map and e[1] in idx_map:
                    cut_edges.append((idx_map[e[0]], idx_map[e[1]]))
                continue
            for neighbor in edge_local.get(e, []):
                if neighbor in visited or neighbor not in face_set:
                    continue
                visited.add(neighbor)
                # place the neighbor
                verts_2d, idx_map = _place_triangle(
                    mesh, neighbor, (e[0], e[1]), verts_2d, idx_map
                )
                fold_edges.append((idx_map[e[0]], idx_map[e[1]]))
                queue.append(neighbor)

    # build face array in 2-D indices
    faces_2d: list[list[int]] = []
    for fi in face_indices:
        tri = mesh.faces[fi]
        if all(int(v) in idx_map for v in tri):
            faces_2d.append([idx_map[int(tri[0])], idx_map[int(tri[1])], idx_map[int(tri[2])]])

    vert_map = np.full(len(verts_2d), -1, dtype=np.int32)
    for v3, v2 in idx_map.items():
        if v2 < len(vert_map):
            vert_map[v2] = v3

    return UnfoldedPart(
        part_id=part_id,
        vertices_2d=verts_2d,
        faces=np.array(faces_2d, dtype=np.int32) if faces_2d else np.empty((0, 3), dtype=np.int32),
        vert_map_3d=vert_map,
        fold_edges=fold_edges,
        cut_edges=cut_edges,
    )
