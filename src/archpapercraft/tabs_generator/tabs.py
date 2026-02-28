"""Generátor geometrie chlopní pro papírové vystřihováníky.

"Chlopeň" (tab) je lichoběžníkový/obdélníkový/zubatý pásek přidaný podél
řezné hrany, aby uživatel mohl díl přilepit k sousednímu dílu.

Nastavení ovlivněná gramáží papíru:
- 160 g → šířka chlopně ~5 mm
- 200 g → ~6 mm
- 250 g → ~7 mm

Pokročilé funkce:
- TOOTH (zubaté) — pilovitý profil lepidla
- Vnitřní/vnější chlopně
- Úlevové řezy (relief cuts) v ostrých rozích
- Režim „pouze lepicí okraj"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class TabShape(Enum):
    STRAIGHT = auto()   # obdélníková chlopeň
    TAPERED = auto()    # lichoběžníková (zúžená na konci)
    ROUNDED = auto()    # zaoblená (budoucí)
    TOOTH = auto()      # zubatá (pilovitý profil)


class TabSide(Enum):
    """Na které straně hrany se generuje chlopeň."""
    OUTER = auto()      # vnější strana (výchozí)
    INNER = auto()      # vnitřní strana


# Gramáž papíru → výchozí šířka chlopně (mm)
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
    taper_ratio: float = 0.6       # šířka hrotu jako podíl základny (TAPERED)
    grammage: int = 160             # gramáž papíru g/m²
    side: TabSide = TabSide.OUTER   # vnitřní/vnější
    tooth_count: int = 4            # počet zubů pro TOOTH tvar
    relief_cut_mm: float = 0.5     # délka úlevového řezu v rozích
    glue_margin_only: bool = False  # jen lepicí okraj (bez plné chlopně)

    def __post_init__(self) -> None:
        if self.grammage in GRAMMAGE_TAB_WIDTH:
            self.width_mm = GRAMMAGE_TAB_WIDTH[self.grammage]


@dataclass
class Tab:
    """Jeden vygenerovaný polygon chlopně."""

    edge_2d: tuple[NDArray[np.float64], NDArray[np.float64]]  # (p0, p1) řezná hrana
    polygon: NDArray[np.float64]  # (4, 2) nebo (N, 2) obrys
    match_id: int = 0  # ID páru hrany pro sestavovací návod
    side: TabSide = TabSide.OUTER


@dataclass
class ReliefCut:
    """Úlevový řez v ostrém rohu."""

    p0: NDArray[np.float64]
    p1: NDArray[np.float64]


def generate_tab(
    p0: NDArray[np.float64],
    p1: NDArray[np.float64],
    settings: TabSettings,
    match_id: int = 0,
) -> Tab | None:
    """Vytvoří polygon chlopně na vnější/vnitřní straně řezné hrany p0→p1.

    Vrátí None pokud jsou chlopně zakázány.
    """
    if not settings.enabled:
        return None

    edge_vec = p1 - p0
    edge_len = float(np.linalg.norm(edge_vec))
    if edge_len < 1e-6:
        return None

    # jednotkové vektory
    tangent = edge_vec / edge_len
    normal = np.array([-tangent[1], tangent[0]])  # normála (levá strana)

    # Obrátit normálu pro vnitřní chlopně
    if settings.side == TabSide.INNER:
        normal = -normal

    w = settings.width_mm

    if settings.glue_margin_only:
        # Jen tenký lepicí okraj (1 mm)
        w = min(w, 1.5)
        poly = np.array([
            p0,
            p1,
            p1 + normal * w,
            p0 + normal * w,
        ], dtype=np.float64)

    elif settings.shape == TabShape.STRAIGHT:
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

    elif settings.shape == TabShape.TOOTH:
        poly = _generate_tooth_tab(p0, p1, tangent, normal, w,
                                   settings.tooth_count, edge_len)

    else:
        # fallback na rovnou
        poly = np.array([
            p0,
            p1,
            p1 + normal * w,
            p0 + normal * w,
        ], dtype=np.float64)

    return Tab(edge_2d=(p0.copy(), p1.copy()), polygon=poly,
               match_id=match_id, side=settings.side)


def _generate_tooth_tab(
    p0: NDArray[np.float64],
    p1: NDArray[np.float64],
    tangent: NDArray[np.float64],
    normal: NDArray[np.float64],
    width: float,
    tooth_count: int,
    edge_len: float,
) -> NDArray[np.float64]:
    """Vygeneruje zubatý (pilovitý) polygon chlopně."""
    tooth_count = max(1, tooth_count)
    step = edge_len / tooth_count
    points: list[NDArray[np.float64]] = [p0.copy()]

    for i in range(tooth_count):
        base_start = p0 + tangent * (i * step)
        base_mid = p0 + tangent * ((i + 0.5) * step)
        base_end = p0 + tangent * ((i + 1) * step)
        # nahoru
        points.append(base_start + normal * width)
        points.append(base_mid + normal * width)
        # dolů zpět k základně
        points.append(base_end.copy())

    return np.array(points, dtype=np.float64)


def generate_relief_cuts(
    vertices_2d: NDArray[np.float64],
    cut_edges: list[tuple[int, int]],
    settings: TabSettings,
) -> list[ReliefCut]:
    """Vygeneruje úlevové řezy v ostrých rozích mezi řeznými hranami.

    Úlevový řez je krátký zářez, který usnadní ohýbání papíru
    v místech, kde se setkávají chlopně.
    """
    if settings.relief_cut_mm <= 0:
        return []

    # Najdi vrcholy sdílené více řeznými hranami
    vertex_edges: dict[int, list[tuple[int, int]]] = {}
    for v0, v1 in cut_edges:
        vertex_edges.setdefault(v0, []).append((v0, v1))
        vertex_edges.setdefault(v1, []).append((v0, v1))

    cuts: list[ReliefCut] = []
    for vid, edges in vertex_edges.items():
        if len(edges) < 2:
            continue
        # Reliéfový řez ve směru normály
        p = vertices_2d[vid]
        for v0, v1 in edges:
            other = v1 if v0 == vid else v0
            direction = vertices_2d[other] - p
            length = float(np.linalg.norm(direction))
            if length < 1e-6:
                continue
            direction = direction / length
            cut_end = p + direction * settings.relief_cut_mm
            cuts.append(ReliefCut(p0=p.copy(), p1=cut_end))

    return cuts


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
