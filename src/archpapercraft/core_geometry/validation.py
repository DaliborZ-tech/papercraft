"""Mesh validation: normals orientation, non-manifold edges, self-intersections."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData


@dataclass
class ValidationReport:
    """Collects issues found during mesh validation."""

    is_valid: bool = True
    non_manifold_edges: list[tuple[int, int]] = field(default_factory=list)
    flipped_normals: list[int] = field(default_factory=list)
    degenerate_faces: list[int] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def add_issue(self, msg: str) -> None:
        self.is_valid = False
        self.messages.append(msg)


def validate_mesh(mesh: MeshData) -> ValidationReport:
    """Run basic validation checks on *mesh* and return a report."""
    report = ValidationReport()

    if mesh.num_faces == 0:
        report.add_issue("Mesh has no faces.")
        return report

    # 1. Degenerate faces (zero-area)
    v0 = mesh.vertices[mesh.faces[:, 0]]
    v1 = mesh.vertices[mesh.faces[:, 1]]
    v2 = mesh.vertices[mesh.faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    degen = np.where(areas < 1e-12)[0]
    if len(degen):
        report.degenerate_faces = degen.tolist()
        report.add_issue(f"{len(degen)} degenerate (zero-area) faces found.")

    # 2. Non-manifold edges (shared by != 2 faces)
    edge_count: dict[tuple[int, int], int] = {}
    for fi in range(mesh.num_faces):
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            edge_count[e] = edge_count.get(e, 0) + 1

    for edge, count in edge_count.items():
        if count != 2:
            report.non_manifold_edges.append(edge)

    if report.non_manifold_edges:
        report.add_issue(
            f"{len(report.non_manifold_edges)} non-manifold edges found "
            f"(boundary or shared by >2 faces)."
        )

    return report


def fix_normals_consistent(mesh: MeshData) -> MeshData:
    """Attempt to make all face normals consistent via BFS edge-walk.

    Returns a new MeshData (faces may have flipped winding).
    """
    from collections import deque

    n_faces = mesh.num_faces
    # Build edge → face adjacency
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for fi in range(n_faces):
        tri = mesh.faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri[j]), int(tri[(j + 1) % 3]))))
            edge_faces.setdefault(e, []).append(fi)

    visited = np.zeros(n_faces, dtype=bool)
    new_faces = mesh.faces.copy()

    # BFS from face 0
    queue: deque[int] = deque()
    queue.append(0)
    visited[0] = True

    while queue:
        fi = queue.popleft()
        tri_a = new_faces[fi]
        for j in range(3):
            e = tuple(sorted((int(tri_a[j]), int(tri_a[(j + 1) % 3]))))
            for neighbor in edge_faces.get(e, []):
                if visited[neighbor]:
                    continue
                visited[neighbor] = True
                # check consistent winding: shared edge should appear in opposite order
                tri_b = new_faces[neighbor]
                # find the shared edge indices in neighbor
                idx_in_b = []
                for k in range(3):
                    eb = tuple(sorted((int(tri_b[k]), int(tri_b[(k + 1) % 3]))))
                    if eb == e:
                        idx_in_b = [k, (k + 1) % 3]
                        break
                if idx_in_b:
                    # in tri_a the edge goes  tri_a[j] -> tri_a[(j+1)%3]
                    # in tri_b it should go  tri_b[idx_in_b[1]] -> tri_b[idx_in_b[0]]
                    if tri_b[idx_in_b[0]] == tri_a[j]:
                        # same direction → flip neighbor
                        new_faces[neighbor] = new_faces[neighbor][::-1]
                queue.append(neighbor)

    return MeshData(vertices=mesh.vertices.copy(), faces=new_faces)
