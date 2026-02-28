"""Systém přichytávání (Snap) pro 3D viewport.

Podporované režimy:
- Mřížka (Grid snap)
- Body / vrcholy (Vertex snap)
- Hrany (Edge snap)
- Osy (Axis snap)
- Úhlový snap (Angle snap) — např. 5°, 15°, 45°, 90°
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Flag, auto

import numpy as np
from numpy.typing import NDArray


class SnapMode(Flag):
    """Příznak režimů přichytávání — lze kombinovat."""

    NONE = 0
    GRID = auto()       # Na mřížku
    VERTEX = auto()     # Na vrcholy meshe
    EDGE = auto()       # Na nejbližší bod hrany
    AXIS = auto()       # Na hlavní osy (X, Y, Z)
    ANGLE = auto()      # Úhlový snap při rotaci

    @classmethod
    def all(cls) -> SnapMode:
        return cls.GRID | cls.VERTEX | cls.EDGE | cls.AXIS | cls.ANGLE


@dataclass
class SnapSettings:
    """Nastavení přichytávání."""

    enabled: bool = True
    modes: SnapMode = SnapMode.GRID
    grid_size: float = 10.0        # mm — velikost mřížky
    vertex_radius: float = 5.0     # mm — poloměr zachycení vrcholu
    edge_radius: float = 5.0       # mm — poloměr zachycení hrany
    angle_step_deg: float = 15.0   # ° — krok úhlového snapu


@dataclass
class SnapResult:
    """Výsledek přichytávání — upravená pozice + informace o typu."""

    position: NDArray[np.float64]   # (3,) — výsledná pozice
    snapped: bool = False           # Zda došlo k přichytnutí
    snap_type: SnapMode = SnapMode.NONE
    snap_target: str = ""           # Popis cíle (pro zobrazení v UI)


def snap_to_grid(
    point: NDArray[np.float64],
    settings: SnapSettings,
) -> SnapResult:
    """Přichytí bod na nejbližší bod mřížky."""
    if not settings.enabled or SnapMode.GRID not in settings.modes:
        return SnapResult(position=point.copy())

    gs = settings.grid_size
    snapped = np.round(point / gs) * gs
    return SnapResult(
        position=snapped,
        snapped=True,
        snap_type=SnapMode.GRID,
        snap_target=f"Mřížka [{gs} mm]",
    )


def snap_to_vertex(
    point: NDArray[np.float64],
    vertices: NDArray[np.float64],
    settings: SnapSettings,
) -> SnapResult:
    """Přichytí na nejbližší vrchol, pokud je v dosahu."""
    if not settings.enabled or SnapMode.VERTEX not in settings.modes:
        return SnapResult(position=point.copy())
    if len(vertices) == 0:
        return SnapResult(position=point.copy())

    dists = np.linalg.norm(vertices - point, axis=1)
    idx = int(np.argmin(dists))
    if dists[idx] <= settings.vertex_radius:
        return SnapResult(
            position=vertices[idx].copy(),
            snapped=True,
            snap_type=SnapMode.VERTEX,
            snap_target=f"Vrchol #{idx}",
        )
    return SnapResult(position=point.copy())


def snap_to_axis(
    point: NDArray[np.float64],
    origin: NDArray[np.float64],
    settings: SnapSettings,
) -> SnapResult:
    """Přichytí bod na nejbližší hlavní osu procházející *origin*."""
    if not settings.enabled or SnapMode.AXIS not in settings.modes:
        return SnapResult(position=point.copy())

    diff = point - origin
    abs_diff = np.abs(diff)
    # Najdi osu s nejmenší odchylkou (tu zaokrouhlíme na nulu)
    min_axis = int(np.argmin(abs_diff))
    snapped = point.copy()
    snapped[min_axis] = origin[min_axis]
    axis_names = ["X", "Y", "Z"]
    return SnapResult(
        position=snapped,
        snapped=True,
        snap_type=SnapMode.AXIS,
        snap_target=f"Osa {axis_names[min_axis]}",
    )


def snap_angle(
    angle_deg: float,
    settings: SnapSettings,
) -> float:
    """Zaokrouhlí úhel na nejbližší násobek ``angle_step_deg``."""
    if not settings.enabled or SnapMode.ANGLE not in settings.modes:
        return angle_deg
    step = settings.angle_step_deg
    return round(angle_deg / step) * step


def snap_point(
    point: NDArray[np.float64],
    settings: SnapSettings,
    scene_vertices: NDArray[np.float64] | None = None,
    origin: NDArray[np.float64] | None = None,
) -> SnapResult:
    """Hlavní snap funkce — zkusí všechny aktivní režimy (vertex → axis → grid).

    Priorita: Vertex > Axis > Grid.
    """
    if not settings.enabled:
        return SnapResult(position=point.copy())

    # 1) Vertex snap — nejvyšší priorita
    if scene_vertices is not None and SnapMode.VERTEX in settings.modes:
        result = snap_to_vertex(point, scene_vertices, settings)
        if result.snapped:
            return result

    # 2) Axis snap
    if origin is not None and SnapMode.AXIS in settings.modes:
        diff = point - origin
        abs_diff = np.abs(diff)
        min_val = float(abs_diff.min())
        if min_val < settings.edge_radius:
            return snap_to_axis(point, origin, settings)

    # 3) Grid snap — nejnižší priorita
    if SnapMode.GRID in settings.modes:
        return snap_to_grid(point, settings)

    return SnapResult(position=point.copy())
