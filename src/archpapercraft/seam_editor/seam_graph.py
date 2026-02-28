"""Seam graph data-structure.

A *SeamGraph* lives on top of a triangle mesh and marks certain edges as "seams"
(where the paper will be cut).  Edges that are NOT seams become fold-lines.

The graph also tracks:
- which connected components (unfold "islands" / parts) exist,
- part IDs for numbering,
- edge-match IDs so the user knows which edge sticks to which.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


Edge = tuple[int, int]  # always sorted (lo, hi)


@dataclass
class SeamGraph:
    """Holds the set of seam-edges for a given mesh."""

    mesh: MeshData
    seam_edges: set[Edge] = field(default_factory=set)

    # lazy caches
    _edge_faces: dict[Edge, list[int]] | None = field(default=None, repr=False)
    _face_neighbors: list[set[int]] | None = field(default=None, repr=False)
    _parts: list[list[int]] | None = field(default=None, repr=False)

    # ── edge / adjacency helpers ───────────────────────────────────────

    def _ensure_adjacency(self) -> None:
        if self._edge_faces is not None:
            return
        ef: dict[Edge, list[int]] = {}
        for fi in range(self.mesh.num_faces):
            tri = self.mesh.faces[fi]
            for j in range(3):
                e: Edge = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))  # type: ignore[assignment]
                ef.setdefault(e, []).append(fi)
        self._edge_faces = ef

        fn: list[set[int]] = [set() for _ in range(self.mesh.num_faces)]
        for edge, faces in ef.items():
            if edge in self.seam_edges:
                continue  # seam → don't connect
            for i in range(len(faces)):
                for j in range(i + 1, len(faces)):
                    fn[faces[i]].add(faces[j])
                    fn[faces[j]].add(faces[i])
        self._face_neighbors = fn

    def invalidate_caches(self) -> None:
        self._edge_faces = None
        self._face_neighbors = None
        self._parts = None

    # ── seam manipulation ──────────────────────────────────────────────

    def add_seam(self, v0: int, v1: int) -> None:
        self.seam_edges.add(tuple(sorted((v0, v1))))  # type: ignore[arg-type]
        self.invalidate_caches()

    def remove_seam(self, v0: int, v1: int) -> None:
        self.seam_edges.discard(tuple(sorted((v0, v1))))  # type: ignore[arg-type]
        self.invalidate_caches()

    def toggle_seam(self, v0: int, v1: int) -> bool:
        """Toggle seam state; return True if the edge is now a seam."""
        e: Edge = tuple(sorted((v0, v1)))  # type: ignore[assignment]
        if e in self.seam_edges:
            self.seam_edges.discard(e)
            self.invalidate_caches()
            return False
        self.seam_edges.add(e)
        self.invalidate_caches()
        return True

    def is_seam(self, v0: int, v1: int) -> bool:
        return tuple(sorted((v0, v1))) in self.seam_edges

    # ── connected components (parts) ───────────────────────────────────

    def compute_parts(self) -> list[list[int]]:
        """Return list of face-index lists, one per connected component
        (respecting seam cuts)."""
        self._ensure_adjacency()
        assert self._face_neighbors is not None

        visited = np.zeros(self.mesh.num_faces, dtype=bool)
        parts: list[list[int]] = []

        for start in range(self.mesh.num_faces):
            if visited[start]:
                continue
            queue: deque[int] = deque([start])
            visited[start] = True
            component: list[int] = []
            while queue:
                fi = queue.popleft()
                component.append(fi)
                for ni in self._face_neighbors[fi]:
                    if not visited[ni]:
                        visited[ni] = True
                        queue.append(ni)
            parts.append(component)

        self._parts = parts
        return parts

    @property
    def num_parts(self) -> int:
        if self._parts is None:
            self.compute_parts()
        assert self._parts is not None
        return len(self._parts)

    # ── edge-match numbering ───────────────────────────────────────────

    def compute_edge_match_ids(self) -> dict[Edge, int]:
        """Assign a unique match-ID to each seam edge so the user can pair
        cut edges during assembly."""
        self._ensure_adjacency()
        match_id = 1
        result: dict[Edge, int] = {}
        for edge in sorted(self.seam_edges):
            result[edge] = match_id
            match_id += 1
        return result

    # ── all edges of the mesh ──────────────────────────────────────────

    def all_edges(self) -> set[Edge]:
        self._ensure_adjacency()
        assert self._edge_faces is not None
        return set(self._edge_faces.keys())
