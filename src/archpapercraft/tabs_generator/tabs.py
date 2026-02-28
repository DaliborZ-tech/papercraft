"""Tab geometry generation for papercraft edges.

A "tab" (chlopně) is a trapezoidal flap added along a cut edge so the user
can glue the piece to its neighbour.

Settings influenced by paper thickness / grammage:
- 160 g → tab_width ~5 mm
- 200 g → ~6 mm
- 250 g → ~7 mm
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class TabShape(Enum):
    STRAIGHT = auto()  # rectangular tab
    TAPERED = auto()  # trapezoidal (narrower at tip)
    ROUNDED = auto()  # placeholder for future


# Paper grammage → default tab width (mm)
GRAMMAGE_TAB_WIDTH: dict[int, float] = {
    160: 5.0,
    200: 6.0,
    250: 7.0,
}


@dataclass
class TabSettings:
    enabled: bool = True
    width_mm: float = 5.0
    shape: TabShape = TabShape.TAPERED
    taper_ratio: float = 0.6  # tip width as fraction of base (for TAPERED)
    grammage: int = 160  # paper weight g/m²

    def __post_init__(self) -> None:
        if self.grammage in GRAMMAGE_TAB_WIDTH:
            self.width_mm = GRAMMAGE_TAB_WIDTH[self.grammage]


@dataclass
class Tab:
    """A single generated tab polygon."""

    edge_2d: tuple[NDArray[np.float64], NDArray[np.float64]]  # (p0, p1) on the cut edge
    polygon: NDArray[np.float64]  # (4, 2) or (N, 2) outline
    match_id: int = 0  # edge-match ID for assembly guide


def generate_tab(
    p0: NDArray[np.float64],
    p1: NDArray[np.float64],
    settings: TabSettings,
    match_id: int = 0,
) -> Tab | None:
    """Create a tab polygon on the *outside* of the cut edge p0→p1.

    Returns None if tabs are disabled.
    """
    if not settings.enabled:
        return None

    edge_vec = p1 - p0
    edge_len = float(np.linalg.norm(edge_vec))
    if edge_len < 1e-6:
        return None

    # unit vectors
    tangent = edge_vec / edge_len
    normal = np.array([-tangent[1], tangent[0]])  # outward normal (left side)

    w = settings.width_mm

    if settings.shape == TabShape.STRAIGHT:
        poly = np.array([
            p0,
            p1,
            p1 + normal * w,
            p0 + normal * w,
        ], dtype=np.float64)

    elif settings.shape == TabShape.TAPERED:
        inset = edge_len * (1 - settings.taper_ratio) / 2
        poly = np.array([
            p0,
            p1,
            p1 - tangent * inset + normal * w,
            p0 + tangent * inset + normal * w,
        ], dtype=np.float64)

    else:
        # fallback to straight
        poly = np.array([
            p0,
            p1,
            p1 + normal * w,
            p0 + normal * w,
        ], dtype=np.float64)

    return Tab(edge_2d=(p0.copy(), p1.copy()), polygon=poly, match_id=match_id)


def generate_tabs_for_part(
    vertices_2d: NDArray[np.float64],
    cut_edges: list[tuple[int, int]],
    edge_match_ids: dict[tuple[int, int], int] | None,
    settings: TabSettings | None = None,
) -> list[Tab]:
    """Generate tabs for all cut-edges of one unfolded part.

    Only every second occurrence of a matched edge gets a tab (the other side
    stays flat), so each seam is glued from one side.
    """
    if settings is None:
        settings = TabSettings()

    if not settings.enabled:
        return []

    tabs: list[Tab] = []
    seen_match: set[int] = set()

    for v0_idx, v1_idx in cut_edges:
        p0 = vertices_2d[v0_idx]
        p1 = vertices_2d[v1_idx]

        # determine match id
        e_sorted = tuple(sorted((v0_idx, v1_idx)))
        mid = 0
        if edge_match_ids:
            mid = edge_match_ids.get(e_sorted, 0)

        # only first side gets a tab
        if mid in seen_match and mid != 0:
            continue
        seen_match.add(mid)

        tab = generate_tab(p0, p1, settings, match_id=mid)
        if tab:
            tabs.append(tab)

    return tabs
