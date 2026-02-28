"""Modelling operations: extrude, revolve, boolean, transform.

OCC-backed when pythonocc-core is available; lightweight mesh fallback otherwise.

Pro výběr backendu viz ``archpapercraft.core_geometry.backend``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData, OCC_AVAILABLE
from archpapercraft.core_geometry.backend import get_backend, GeometryBackend

if TYPE_CHECKING:
    from numpy.typing import NDArray

# ── OCC imports (optional) ─────────────────────────────────────────────

if OCC_AVAILABLE:
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
    from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Vec
    from OCP.TopoDS import TopoDS_Shape

# ======================================================================
# Boolean operations — delegují na aktivní backend
# ======================================================================


def boolean_union_occ(shape_a, shape_b):
    """OCC boolean union (low-level — pro přímé volání s OCC shapes)."""
    return BRepAlgoAPI_Fuse(shape_a, shape_b).Shape()


def boolean_difference_occ(shape_a, shape_b):
    """OCC boolean difference (low-level — A − B)."""
    return BRepAlgoAPI_Cut(shape_a, shape_b).Shape()


def boolean_union_mesh(a: MeshData, b: MeshData) -> MeshData:
    """Boolean union přes aktivní backend."""
    return get_backend().boolean_union(a, b)


def boolean_difference_mesh(a: MeshData, b: MeshData) -> MeshData:
    """Boolean difference přes aktivní backend.

    S MeshBackend: vrací *a* beze změny (placeholder).
    S OCCBackend:  plné CSG odečtení.
    """
    return get_backend().boolean_difference(a, b)


def boolean_intersect_mesh(a: MeshData, b: MeshData) -> MeshData:
    """Boolean intersection přes aktivní backend.

    S MeshBackend: vrací *a* beze změny (placeholder).
    S OCCBackend:  plný CSG průnik.
    """
    return get_backend().boolean_intersect(a, b)


# ======================================================================
# Extrude (linear sweep of a 2-D profile along a direction)
# ======================================================================


def extrude_occ(face, direction: tuple[float, float, float], distance: float):
    """Extrude an OCC face along *direction* by *distance*."""
    vec = gp_Vec(*direction)
    vec.Normalize()
    vec.Scale(distance)
    return BRepPrimAPI_MakePrism(face, vec).Shape()


def extrude_profile_mesh(
    profile_2d: NDArray[np.float64],
    direction: NDArray[np.float64],
    distance: float,
) -> MeshData:
    """Extrude a closed 2-D polygon (Nx2) along *direction* (3-vec).

    Returns a MeshData tube with open caps.
    """
    n = len(profile_2d)
    # Embed 2-D profile into 3-D (XY plane)
    bottom = np.zeros((n, 3), dtype=np.float64)
    bottom[:, :2] = profile_2d
    d = direction / np.linalg.norm(direction) * distance
    top = bottom + d

    verts = np.vstack([bottom, top])
    faces_list: list[list[int]] = []
    for i in range(n):
        ni = (i + 1) % n
        faces_list.append([i, ni, ni + n])
        faces_list.append([i, ni + n, i + n])
    return MeshData(vertices=verts, faces=np.array(faces_list, dtype=np.int32))


# ======================================================================
# Revolve (rotation of a profile around an axis)
# ======================================================================


def revolve_occ(face, axis_origin, axis_dir, angle_deg: float = 360.0):
    """Revolve an OCC face around an axis."""
    ax = gp_Ax1(gp_Pnt(*axis_origin), gp_Dir(*axis_dir))
    return BRepPrimAPI_MakeRevol(face, ax, math.radians(angle_deg)).Shape()


def revolve_profile_mesh(
    profile_2d: NDArray[np.float64],
    segments: int = 32,
    angle_deg: float = 360.0,
) -> MeshData:
    """Revolve a 2-D profile (Nx2, in XZ plane) around the Z-axis.

    *profile_2d[:, 0]* is the radius (distance from Z), *[:, 1]* is Z.

    Returns a closed-surface MeshData suitable for papercraft.
    """
    n_pts = len(profile_2d)
    angle_rad = math.radians(angle_deg)
    thetas = np.linspace(0, angle_rad, segments, endpoint=False)
    closed = abs(angle_deg - 360.0) < 1e-6

    all_verts: list[NDArray] = []
    for theta in thetas:
        ring = np.zeros((n_pts, 3), dtype=np.float64)
        ring[:, 0] = profile_2d[:, 0] * math.cos(theta)
        ring[:, 1] = profile_2d[:, 0] * math.sin(theta)
        ring[:, 2] = profile_2d[:, 1]
        all_verts.append(ring)

    verts = np.vstack(all_verts)  # (segments * n_pts, 3)

    faces_list: list[list[int]] = []
    for s in range(segments):
        ns = (s + 1) % segments if closed else s + 1
        if ns >= segments and not closed:
            break
        for p in range(n_pts - 1):
            i0 = s * n_pts + p
            i1 = s * n_pts + p + 1
            i2 = ns * n_pts + p + 1
            i3 = ns * n_pts + p
            faces_list.append([i0, i1, i2])
            faces_list.append([i0, i2, i3])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )


# ======================================================================
# Merge helpers
# ======================================================================


def merge_meshes(meshes: list[MeshData]) -> MeshData:
    """Merge multiple meshes into one by concatenating vertices/faces.

    Face indices are offset so that they reference the correct vertices
    in the combined array.  Returns an empty mesh if *meshes* is empty.
    """
    if not meshes:
        return MeshData(
            vertices=np.empty((0, 3), dtype=np.float64),
            faces=np.empty((0, 3), dtype=np.int32),
        )
    if len(meshes) == 1:
        return meshes[0]

    all_verts: list[NDArray] = []
    all_faces: list[NDArray] = []
    offset = 0
    for m in meshes:
        all_verts.append(m.vertices)
        all_faces.append(m.faces + offset)
        offset += len(m.vertices)

    return MeshData(
        vertices=np.vstack(all_verts),
        faces=np.vstack(all_faces).astype(np.int32),
    )


# ======================================================================
# Transform helpers
# ======================================================================


def translate_mesh(mesh: MeshData, offset: NDArray[np.float64]) -> MeshData:
    """Return a translated copy of *mesh*."""
    return MeshData(
        vertices=mesh.vertices + offset,
        faces=mesh.faces.copy(),
        normals=mesh.normals.copy() if mesh.normals is not None else None,
    )


def scale_mesh(mesh: MeshData, factors: NDArray[np.float64]) -> MeshData:
    """Return a scaled copy of *mesh*. *factors* is (sx, sy, sz)."""
    return MeshData(
        vertices=mesh.vertices * factors,
        faces=mesh.faces.copy(),
        normals=None,
    )


def mirror_mesh(mesh: MeshData, axis: int = 0) -> MeshData:
    """Mirror *mesh* along *axis* (0=X, 1=Y, 2=Z)."""
    new_verts = mesh.vertices.copy()
    new_verts[:, axis] *= -1
    new_faces = mesh.faces[:, ::-1].copy()  # flip winding
    return MeshData(vertices=new_verts, faces=new_faces)
