"""Vytváření primitivních těles (kvádr, válec, kužel, koule, torus) a 2D profilů.

Když je dostupný pythonocc-core (OpenCascade), funkce vrací reálná
TopoDS_Shape tělesa. Jinak se použije odlehčená numpy-mesh reprezentace,
aby zbytek pipeline mohl fungovat (s nižší přesností).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Lightweight mesh fallback (always available)
# ---------------------------------------------------------------------------


@dataclass
class MeshData:
    """Jednoduchý indexovaný trojúhelníkový mesh — interní výměnný formát."""

    vertices: NDArray[np.float64]  # (N, 3)
    faces: NDArray[np.int32]  # (M, 3) — indexy trojúhelníků
    normals: NDArray[np.float64] | None = None  # per-face nebo per-vertex

    @property
    def num_vertices(self) -> int:
        return self.vertices.shape[0]

    @property
    def num_faces(self) -> int:
        return self.faces.shape[0]


# ---------------------------------------------------------------------------
# Try to import OCC — flag available at runtime
# ---------------------------------------------------------------------------

try:
    from OCP.BRepPrimAPI import (
        BRepPrimAPI_MakeBox,
        BRepPrimAPI_MakeCone,
        BRepPrimAPI_MakeCylinder,
    )
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

    OCC_AVAILABLE = True
except ImportError:
    OCC_AVAILABLE = False


# ---------------------------------------------------------------------------
# OCC-backed primitives
# ---------------------------------------------------------------------------


def make_box_occ(dx: float, dy: float, dz: float):
    """Vrátí TopoDS_Shape kvádr *dx × dy × dz*."""
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core není nainstalován")
    return BRepPrimAPI_MakeBox(dx, dy, dz).Shape()


def make_cylinder_occ(radius: float, height: float):
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core není nainstalován")
    return BRepPrimAPI_MakeCylinder(radius, height).Shape()


def make_cone_occ(radius1: float, radius2: float, height: float):
    if not OCC_AVAILABLE:
        raise RuntimeError("pythonocc-core není nainstalován")
    return BRepPrimAPI_MakeCone(radius1, radius2, height).Shape()


# ---------------------------------------------------------------------------
# Pure-numpy mesh primitives (fallback)
# ---------------------------------------------------------------------------


def make_box_mesh(dx: float, dy: float, dz: float) -> MeshData:
    """Vytvoří mesh kvádru zarovnaného s osami se středem v počátku."""
    hx, hy, hz = dx / 2, dy / 2, dz / 2
    verts = np.array(
        [
            [-hx, -hy, -hz],
            [+hx, -hy, -hz],
            [+hx, +hy, -hz],
            [-hx, +hy, -hz],
            [-hx, -hy, +hz],
            [+hx, -hy, +hz],
            [+hx, +hy, +hz],
            [-hx, +hy, +hz],
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            # bottom
            [0, 2, 1],
            [0, 3, 2],
            # top
            [4, 5, 6],
            [4, 6, 7],
            # front
            [0, 1, 5],
            [0, 5, 4],
            # back
            [2, 3, 7],
            [2, 7, 6],
            # left
            [0, 4, 7],
            [0, 7, 3],
            # right
            [1, 2, 6],
            [1, 6, 5],
        ],
        dtype=np.int32,
    )
    return MeshData(vertices=verts, faces=faces)


def make_cylinder_mesh(
    radius: float, height: float, segments: int = 32
) -> MeshData:
    """Create a cylinder mesh (open ends) along the Z axis."""
    angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    bottom = np.column_stack([radius * np.cos(angles), radius * np.sin(angles),
                              np.zeros(segments)])
    top = bottom.copy()
    top[:, 2] = height
    # center vertices for caps
    center_bot = np.array([[0.0, 0.0, 0.0]])
    center_top = np.array([[0.0, 0.0, height]])
    verts = np.vstack([bottom, top, center_bot, center_top])

    faces_list: list[list[int]] = []
    n = segments
    cb = 2 * n  # center bottom index
    ct = 2 * n + 1  # center top index
    for i in range(n):
        ni = (i + 1) % n
        # side quads as two triangles
        faces_list.append([i, ni, ni + n])
        faces_list.append([i, ni + n, i + n])
        # bottom cap
        faces_list.append([cb, ni, i])
        # top cap
        faces_list.append([ct, i + n, ni + n])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )


def make_cone_mesh(
    radius_bottom: float, radius_top: float, height: float, segments: int = 32
) -> MeshData:
    """Truncated cone (set *radius_top=0* for a sharp cone)."""
    angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    bottom = np.column_stack([radius_bottom * np.cos(angles),
                              radius_bottom * np.sin(angles),
                              np.zeros(segments)])
    top = np.column_stack([radius_top * np.cos(angles),
                           radius_top * np.sin(angles),
                           np.full(segments, height)])
    center_bot = np.array([[0.0, 0.0, 0.0]])
    center_top = np.array([[0.0, 0.0, height]])
    verts = np.vstack([bottom, top, center_bot, center_top])

    faces_list: list[list[int]] = []
    n = segments
    cb = 2 * n
    ct = 2 * n + 1
    for i in range(n):
        ni = (i + 1) % n
        if radius_top > 1e-9:
            faces_list.append([i, ni, ni + n])
            faces_list.append([i, ni + n, i + n])
        else:
            faces_list.append([i, ni, ct])
        faces_list.append([cb, ni, i])
        if radius_top > 1e-9:
            faces_list.append([ct, i + n, ni + n])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )


# ---------------------------------------------------------------------------
# Koule (Sphere)
# ---------------------------------------------------------------------------


def make_sphere_mesh(
    radius: float, segments: int = 32, rings: int = 16
) -> MeshData:
    """Vytvoří mesh koule se středem v počátku.

    Parametry
    ---------
    radius : float
        Poloměr koule.
    segments : int
        Počet segmentů (podélné dělení).
    rings : int
        Počet prstenců (příčné dělení).
    """
    verts_list: list[list[float]] = []
    faces_list: list[list[int]] = []

    # Severní pól
    verts_list.append([0.0, 0.0, radius])

    for i in range(1, rings):
        phi = math.pi * i / rings
        z = radius * math.cos(phi)
        r = radius * math.sin(phi)
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            verts_list.append([r * math.cos(theta), r * math.sin(theta), z])

    # Jižní pól
    verts_list.append([0.0, 0.0, -radius])

    verts = np.array(verts_list, dtype=np.float64)

    # Trojúhelníky k severnímu pólu
    for j in range(segments):
        nj = (j + 1) % segments
        faces_list.append([0, 1 + j, 1 + nj])

    # Střední pásy
    for i in range(rings - 2):
        for j in range(segments):
            nj = (j + 1) % segments
            r1 = 1 + i * segments
            r2 = 1 + (i + 1) * segments
            faces_list.append([r1 + j, r2 + j, r2 + nj])
            faces_list.append([r1 + j, r2 + nj, r1 + nj])

    # Trojúhelníky k jižnímu pólu
    south = len(verts) - 1
    last_ring = 1 + (rings - 2) * segments
    for j in range(segments):
        nj = (j + 1) % segments
        faces_list.append([south, last_ring + nj, last_ring + j])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )


# ---------------------------------------------------------------------------
# Torus
# ---------------------------------------------------------------------------


def make_torus_mesh(
    major_radius: float,
    minor_radius: float,
    major_segments: int = 32,
    minor_segments: int = 16,
) -> MeshData:
    """Vytvoří mesh torusu (prstence) se středem v počátku, v rovině XY.

    Parametry
    ---------
    major_radius : float
        Hlavní poloměr (vzdálenost středu trubice od středu torusu).
    minor_radius : float
        Vedlejší poloměr (poloměr trubice).
    major_segments : int
        Počet dělení hlavního kruhu.
    minor_segments : int
        Počet dělení trubice.
    """
    verts_list: list[list[float]] = []
    for i in range(major_segments):
        theta = 2 * math.pi * i / major_segments
        ct, st = math.cos(theta), math.sin(theta)
        for j in range(minor_segments):
            phi = 2 * math.pi * j / minor_segments
            cp, sp = math.cos(phi), math.sin(phi)
            r = major_radius + minor_radius * cp
            verts_list.append([r * ct, r * st, minor_radius * sp])

    verts = np.array(verts_list, dtype=np.float64)
    faces_list: list[list[int]] = []
    for i in range(major_segments):
        ni = (i + 1) % major_segments
        for j in range(minor_segments):
            nj = (j + 1) % minor_segments
            v0 = i * minor_segments + j
            v1 = i * minor_segments + nj
            v2 = ni * minor_segments + nj
            v3 = ni * minor_segments + j
            faces_list.append([v0, v1, v2])
            faces_list.append([v0, v2, v3])

    return MeshData(
        vertices=verts,
        faces=np.array(faces_list, dtype=np.int32),
    )


# ---------------------------------------------------------------------------
# 2D profily (pro extrude / revolve / půdorysy)
# ---------------------------------------------------------------------------


def make_rectangle_profile(width: float, height: float) -> NDArray[np.float64]:
    """Vrátí uzavřený obdélníkový profil (4 body, Nx2) se středem v počátku."""
    hw, hh = width / 2, height / 2
    return np.array([
        [-hw, -hh],
        [+hw, -hh],
        [+hw, +hh],
        [-hw, +hh],
    ], dtype=np.float64)


def make_circle_profile(radius: float, segments: int = 32) -> NDArray[np.float64]:
    """Vrátí uzavřený kruhový profil (Nx2) se středem v počátku."""
    angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])


def make_polyline_profile(points: list[tuple[float, float]]) -> NDArray[np.float64]:
    """Vrátí profil z libovolné lomené čáry (Nx2).

    Parametry
    ---------
    points : list[tuple[float, float]]
        Seznam bodů [(x, y), ...] — uzavření se provede automaticky.
    """
    return np.array(points, dtype=np.float64)


def make_ngon_profile(radius: float, sides: int) -> NDArray[np.float64]:
    """Vrátí pravidelný N-úhelník (Nx2) — pro věže s polygonálním půdorysem."""
    angles = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])
