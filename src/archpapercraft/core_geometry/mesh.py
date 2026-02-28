"""Triangulace a síťování OCC solidů a pomocné nástroje pro mesh."""

from __future__ import annotations

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData, OCC_AVAILABLE

if OCC_AVAILABLE:
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRep import BRep_Tool


def triangulate_occ_shape(shape, linear_deflection: float = 0.1) -> MeshData:
    """Triangulate an OCC TopoDS_Shape and return a :class:`MeshData`.

    Parameters
    ----------
    shape
        A TopoDS_Shape solid.
    linear_deflection
        Mesh density control — smaller = finer mesh.
    """
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core není nainstalován")

    BRepMesh_IncrementalMesh(shape, linear_deflection)

    all_verts: list[list[float]] = []
    all_faces: list[list[int]] = []
    vert_offset = 0

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = explorer.Current()
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, loc)
        if triangulation is None:
            explorer.Next()
            continue

        n_nodes = triangulation.NbNodes()
        n_tris = triangulation.NbTriangles()

        for i in range(1, n_nodes + 1):
            pnt = triangulation.Node(i)
            all_verts.append([pnt.X(), pnt.Y(), pnt.Z()])

        for i in range(1, n_tris + 1):
            tri = triangulation.Triangle(i)
            n1, n2, n3 = tri.Get()
            all_faces.append([
                n1 - 1 + vert_offset,
                n2 - 1 + vert_offset,
                n3 - 1 + vert_offset,
            ])

        vert_offset += n_nodes
        explorer.Next()

    return MeshData(
        vertices=np.array(all_verts, dtype=np.float64),
        faces=np.array(all_faces, dtype=np.int32),
    )


# ── Pure-numpy mesh utilities ─────────────────────────────────────────


def compute_face_normals(mesh: MeshData) -> np.ndarray:
    """Compute per-face normals for *mesh*."""
    v0 = mesh.vertices[mesh.faces[:, 0]]
    v1 = mesh.vertices[mesh.faces[:, 1]]
    v2 = mesh.vertices[mesh.faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths < 1e-12] = 1.0
    return normals / lengths


def compute_face_areas(mesh: MeshData) -> np.ndarray:
    """Return an array of face areas."""
    v0 = mesh.vertices[mesh.faces[:, 0]]
    v1 = mesh.vertices[mesh.faces[:, 1]]
    v2 = mesh.vertices[mesh.faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)


def merge_close_vertices(mesh: MeshData, tolerance: float = 1e-6) -> MeshData:
    """Merge vertices that are closer than *tolerance*."""
    from scipy.spatial import cKDTree

    tree = cKDTree(mesh.vertices)
    groups = tree.query_ball_tree(tree, tolerance)

    mapping = np.arange(mesh.num_vertices)
    for group in groups:
        canonical = min(group)
        for idx in group:
            mapping[idx] = canonical

    # re-index
    unique, inverse = np.unique(mapping, return_inverse=True)
    new_verts = mesh.vertices[unique]
    new_faces = inverse[mesh.faces]
    return MeshData(vertices=new_verts, faces=new_faces)
