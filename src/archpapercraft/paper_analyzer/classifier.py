"""Klasifikátor povrchů — označení skupin trojúhelníků jako flat / developable / non-developable.

Navíc poskytuje:
- Detekce non-manifold hran
- Detekce příliš krátkých hran
- Kontroly měřítka (scale sanity checks)
- Výpočet metriky „papercraft readiness"

Algoritmus (mesh-based, bez závislosti na OCC):
1. Vypočítá per-face normály.
2. Sestaví graf sousednosti ploch (sdílené hrany).
3. Flood-fill propojených ploch s dihedrálním úhlem pod prahem → „záplata".
4. Pro každou záplatu rozhodne:
   - Všechny normály identické → FLAT
   - Gaussova křivost ≈ 0 → DEVELOPABLE (segment válce/kužele)
   - Jinak → NON_DEVELOPABLE
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


# ── Non-manifold a validační kontroly ──────────────────────────────────


@dataclass
class ManifoldReport:
    """Výsledek kontroly manifoldnosti."""

    non_manifold_edges: list[tuple[int, int]] = field(default_factory=list)
    boundary_edges: list[tuple[int, int]] = field(default_factory=list)
    short_edges: list[tuple[int, int]] = field(default_factory=list)
    is_manifold: bool = True
    is_watertight: bool = True


def check_manifold(
    mesh: MeshData,
    min_edge_length: float = 0.5,
) -> ManifoldReport:
    """Zkontroluje non-manifold hrany, okrajové hrany a příliš krátké hrany.

    Parametry
    ---------
    mesh : MeshData
        Vstupní mesh.
    min_edge_length : float
        Minimální délka hrany v jednotkách modelu (kratší = varování).
    """
    edge_faces, _ = _build_adjacency(mesh)
    report = ManifoldReport()

    for edge, faces in edge_faces.items():
        if len(faces) > 2:
            report.non_manifold_edges.append(edge)
        elif len(faces) == 1:
            report.boundary_edges.append(edge)

        # Kontrola délky hrany
        v0 = mesh.vertices[edge[0]]
        v1 = mesh.vertices[edge[1]]
        length = float(np.linalg.norm(v1 - v0))
        if length < min_edge_length:
            report.short_edges.append(edge)

    report.is_manifold = len(report.non_manifold_edges) == 0
    report.is_watertight = len(report.boundary_edges) == 0
    return report


# ── Kontroly měřítka (Scale Sanity Checks) ────────────────────────────


@dataclass
class ScaleWarning:
    """Jedno varování o měřítku."""

    message: str
    severity: str = "warning"  # "warning" | "error"
    face_indices: list[int] = field(default_factory=list)


@dataclass
class ScaleReport:
    """Výsledek kontrol měřítka."""

    warnings: list[ScaleWarning] = field(default_factory=list)
    min_detail_mm: float = 0.0
    max_part_extent_mm: float = 0.0
    is_ok: bool = True


def check_scale_readiness(
    mesh: MeshData,
    scale_factor: float = 0.01,
    min_detail_mm: float = 3.0,
    max_part_extent_mm: float = 250.0,
    min_tab_width_mm: float = 3.0,
) -> ScaleReport:
    """Zkontroluje, zda je model v daném měřítku vyrobitelný z papíru.

    Parametry
    ---------
    mesh : MeshData
        Vstupní mesh.
    scale_factor : float
        Faktor měřítka (např. 0.01 pro 1:100).
    min_detail_mm : float
        Minimální rozměr detailu po zmenšení (mm).
    max_part_extent_mm : float
        Maximální rozměr dílu (mm) — přesáhne-li, varování.
    min_tab_width_mm : float
        Minimální šířka pro chlopni (mm).
    """
    report = ScaleReport()

    # Celkový rozsah modelu po aplikaci měřítka
    if mesh.num_vertices == 0:
        return report
    bbox_min = mesh.vertices.min(axis=0)
    bbox_max = mesh.vertices.max(axis=0)
    extent = (bbox_max - bbox_min) * scale_factor * 1000  # převod na mm
    report.max_part_extent_mm = float(extent.max())

    if report.max_part_extent_mm > max_part_extent_mm:
        report.warnings.append(ScaleWarning(
            message=f"Model přesahuje {max_part_extent_mm} mm "
                    f"(aktuální: {report.max_part_extent_mm:.1f} mm). "
                    f"Bude nutné rozdělit na více dílů.",
            severity="error",
        ))

    # Kontrola krátkých hran v měřítku
    short_count = 0
    for fi in range(mesh.num_faces):
        tri = mesh.faces[fi]
        for j in range(3):
            v0 = mesh.vertices[tri[j]]
            v1 = mesh.vertices[tri[(j + 1) % 3]]
            length_mm = float(np.linalg.norm(v1 - v0)) * scale_factor * 1000
            if length_mm < min_detail_mm:
                short_count += 1
                if length_mm < report.min_detail_mm or report.min_detail_mm == 0:
                    report.min_detail_mm = length_mm

    if short_count > 0:
        report.warnings.append(ScaleWarning(
            message=f"{short_count} hran je kratších než {min_detail_mm} mm "
                    f"v daném měřítku. Zvažte zjednodušení geometrie.",
            severity="warning",
        ))

    if report.min_detail_mm < min_tab_width_mm and report.min_detail_mm > 0:
        report.warnings.append(ScaleWarning(
            message=f"Nejkratší hrana ({report.min_detail_mm:.1f} mm) je kratší "
                    f"než minimální šířka chlopně ({min_tab_width_mm} mm).",
            severity="error",
        ))

    report.is_ok = all(w.severity != "error" for w in report.warnings)
    return report


# ── Papercraft Readiness Indikátor ─────────────────────────────────────


def papercraft_readiness_score(
    mesh: MeshData,
    scale_factor: float = 0.01,
) -> float:
    """Vrátí skóre 0.0–1.0 udávající připravenost modelu pro papercraft.

    1.0 = plně připraveno (pouze rovinné plochy, žádné problémy)
    0.0 = nepřipraveno (non-manifold, vše nevyvinutelné)
    """
    if mesh.num_faces == 0:
        return 0.0

    # Analýza povrchů
    result = classify_surfaces(mesh)
    n_total = sum(len(p.face_indices) for p in result.patches)
    n_flat = sum(len(p.face_indices) for p in result.flat_patches)
    n_dev = sum(len(p.face_indices) for p in result.developable_patches)

    surface_score = (n_flat + 0.7 * n_dev) / max(n_total, 1)

    # Manifoldnost
    mf = check_manifold(mesh)
    manifold_score = 1.0 if mf.is_manifold else 0.3

    # Měřítko
    sr = check_scale_readiness(mesh, scale_factor)
    scale_score = 1.0 if sr.is_ok else 0.5

    return min(1.0, surface_score * 0.5 + manifold_score * 0.3 + scale_score * 0.2)
