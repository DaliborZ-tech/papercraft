"""Surface classifier — label triangle groups as flat / developable / non-developable.

Algorithm (mesh-based, no OCC dependency):
1. Compute per-face normals.
2. Build face-adjacency graph (shared edges).
3. Flood-fill connected faces whose dihedral angle is below a threshold → "patch".
4. For each patch decide:
   - All normals identical (within tolerance) → FLAT
   - Gaussian curvature ≈ 0 → DEVELOPABLE  (cylinder / cone segment)
   - Otherwise → NON_DEVELOPABLE
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np

from archpapercraft.core_geometry.mesh import compute_face_normals
from archpapercraft.core_geometry.primitives import MeshData


class SurfaceKind(Enum):
    FLAT = auto()
    DEVELOPABLE = auto()
    NON_DEVELOPABLE = auto()


@dataclass
class SurfacePatch:
    """A group of connected faces sharing similar surface properties."""

    patch_id: int
    kind: SurfaceKind
    face_indices: list[int] = field(default_factory=list)
    max_dihedral_deg: float = 0.0


@dataclass
class AnalysisResult:
    patches: list[SurfacePatch] = field(default_factory=list)

    @property
    def flat_patches(self) -> list[SurfacePatch]:
        return [p for p in self.patches if p.kind == SurfaceKind.FLAT]

    @property
    def developable_patches(self) -> list[SurfacePatch]:
        return [p for p in self.patches if p.kind == SurfaceKind.DEVELOPABLE]

    @property
    def non_developable_patches(self) -> list[SurfacePatch]:
        return [p for p in self.patches if p.kind == SurfaceKind.NON_DEVELOPABLE]


# ── helpers ────────────────────────────────────────────────────────────


def _build_adjacency(mesh: MeshData):
    """Return *edge_to_faces* dict and *face_neighbors* list-of-sets."""
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for fi in range(mesh.num_faces):
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            edge_faces.setdefault(e, []).append(fi)

    neighbors: list[set[int]] = [set() for _ in range(mesh.num_faces)]
    for faces in edge_faces.values():
        for i in range(len(faces)):
            for j in range(i + 1, len(faces)):
                neighbors[faces[i]].add(faces[j])
                neighbors[faces[j]].add(faces[i])
    return edge_faces, neighbors


def _dihedral_angle(n1, n2) -> float:
    """Angle between two unit-normal vectors (degrees)."""
    dot = np.clip(np.dot(n1, n2), -1.0, 1.0)
    return math.degrees(math.acos(dot))


# ── main entry-point ───────────────────────────────────────────────────


def classify_surfaces(
    mesh: MeshData,
    sharp_angle_deg: float = 30.0,
    flat_tolerance_deg: float = 2.0,
    developable_tolerance_deg: float = 15.0,
) -> AnalysisResult:
    """Classify the faces of *mesh* into surface patches.

    Parameters
    ----------
    sharp_angle_deg
        Dihedral angle above which an edge is considered "sharp" (patch boundary).
    flat_tolerance_deg
        If all normals within a patch deviate less than this → FLAT.
    developable_tolerance_deg
        If max dihedral within a patch is below this → DEVELOPABLE.
    """
    normals = compute_face_normals(mesh)
    _edge_faces, neighbors = _build_adjacency(mesh)

    visited = np.zeros(mesh.num_faces, dtype=bool)
    patches: list[SurfacePatch] = []
    pid = 0

    for start in range(mesh.num_faces):
        if visited[start]:
            continue
        # BFS flood-fill
        queue: deque[int] = deque([start])
        visited[start] = True
        face_ids: list[int] = []
        max_dihedral = 0.0

        while queue:
            fi = queue.popleft()
            face_ids.append(fi)
            for ni in neighbors[fi]:
                if visited[ni]:
                    continue
                angle = _dihedral_angle(normals[fi], normals[ni])
                if angle < sharp_angle_deg:
                    visited[ni] = True
                    queue.append(ni)
                    max_dihedral = max(max_dihedral, angle)

        # classify patch
        patch_normals = normals[face_ids]
        ref = patch_normals[0]
        deviations = np.array([_dihedral_angle(ref, n) for n in patch_normals])
        max_dev = float(deviations.max()) if len(deviations) else 0.0

        if max_dev < flat_tolerance_deg:
            kind = SurfaceKind.FLAT
        elif max_dihedral < developable_tolerance_deg:
            kind = SurfaceKind.DEVELOPABLE
        else:
            kind = SurfaceKind.NON_DEVELOPABLE

        patches.append(
            SurfacePatch(
                patch_id=pid,
                kind=kind,
                face_indices=face_ids,
                max_dihedral_deg=max_dihedral,
            )
        )
        pid += 1

    return AnalysisResult(patches=patches)
