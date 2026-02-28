"""Rozmísťování stránek — umístění rozložených dílů na A4/A3/Letter listy.

Používá jednoduchý shelf (police) algoritmus; pokročilejší verze (NFDH,
Guillotine apod.) lze zaměnit později.

Pokročilé funkce:
- Dlaždicový tisk (tiled print) — velké díly se rozdělí přes více listů
- Rotace dílů (0°/90°/180°/270°) pro lepší využití plochy
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class PaperSize(Enum):
    A4 = auto()
    A3 = auto()
    LETTER = auto()
    A2 = auto()    # pro plottery
    A1 = auto()
    CUSTOM = auto()


# Rozměry papíru v mm (šířka, výška) — orientace na výšku
PAPER_DIMS: dict[PaperSize, tuple[float, float]] = {
    PaperSize.A4: (210.0, 297.0),
    PaperSize.A3: (297.0, 420.0),
    PaperSize.LETTER: (215.9, 279.4),
    PaperSize.A2: (420.0, 594.0),
    PaperSize.A1: (594.0, 841.0),
    PaperSize.CUSTOM: (210.0, 297.0),  # výchozí = A4
}


class Orientation(Enum):
    PORTRAIT = auto()
    LANDSCAPE = auto()


class PartRotation(Enum):
    """Rotace dílu pro lepší fit."""
    DEG_0 = 0
    DEG_90 = 90
    DEG_180 = 180
    DEG_270 = 270


@dataclass
class PageSettings:
    paper: PaperSize = PaperSize.A4
    orientation: Orientation = Orientation.PORTRAIT
    margin_mm: float = 10.0
    bleed_mm: float = 0.0

    @property
    def printable_size(self) -> tuple[float, float]:
        w, h = PAPER_DIMS[self.paper]
        if self.orientation == Orientation.LANDSCAPE:
            w, h = h, w
        m = self.margin_mm * 2
        return (w - m, h - m)


@dataclass
class PlacedPart:
    """Díl umístěný na konkrétní stránce."""

    part_id: int
    page_index: int
    offset: NDArray[np.float64]       # (2,) — posunutí v mm
    rotation: PartRotation = PartRotation.DEG_0
    # bounding box po umístění
    bbox_min: NDArray[np.float64] = field(default_factory=lambda: np.zeros(2))
    bbox_max: NDArray[np.float64] = field(default_factory=lambda: np.zeros(2))
    is_tile: bool = False    # je to dlaždice velkého dílu?
    tile_row: int = 0        # řádek dlaždice
    tile_col: int = 0        # sloupec dlaždice
    source_part_id: int = -1  # ID původního dílu (pro dlaždice)


@dataclass
class LayoutResult:
    pages: int = 0
    placements: list[PlacedPart] = field(default_factory=list)


def _bounding_box(pts: NDArray[np.float64]) -> tuple[NDArray, NDArray]:
    return pts.min(axis=0), pts.max(axis=0)


def pack_parts(
    part_outlines: list[NDArray[np.float64]],
    settings: PageSettings | None = None,
    scale: float = 1.0,
    *,
    allow_rotation: bool = False,
    tiled: bool = False,
    tile_overlap_mm: float = 10.0,
) -> LayoutResult:
    """Rozmístí 2D obrysy dílů na stránky.

    Parameters
    ----------
    part_outlines
        Seznam (N_i, 2) polí — 2D pozice vrcholů každého dílu.
    settings
        Nastavení stránky.
    scale
        Měřítkový faktor model→papír (např. pro 1:100 zadejte 10).
    allow_rotation
        Pokud True, zkouší rotaci 90° pro lepší fit.
    tiled
        Pokud True, velké díly se rozdělí na dlaždice.
    tile_overlap_mm
        Přesah dlaždic pro slepení.

    Returns
    -------
    LayoutResult s počtem stránek a informacemi o umístění.
    """
    if settings is None:
        settings = PageSettings()

    pw, ph = settings.printable_size
    result = LayoutResult()

    # Shelf packing state
    current_page = 0
    shelf_x = 0.0
    shelf_y = 0.0
    shelf_height = 0.0

    # Sort parts by height descending for better packing
    indices = list(range(len(part_outlines)))
    bboxes = []
    for outline in part_outlines:
        pts = outline * scale
        bb_min, bb_max = _bounding_box(pts)
        bboxes.append((bb_min, bb_max, bb_max - bb_min))

    indices.sort(key=lambda i: -bboxes[i][2][1])  # sort by height desc

    for idx in indices:
        bb_min, bb_max, size = bboxes[idx]
        w, h = float(size[0]), float(size[1])

        # Zkusit rotaci 90° pokud je povolena a lépe sedí
        rotation = PartRotation.DEG_0
        if allow_rotation and h > w and w <= ph and h > pw:
            # Rotace 90° — prohodit rozměry
            w, h = h, w
            rotation = PartRotation.DEG_90

        # Dlaždicový tisk: díl je větší než stránka
        if tiled and (w > pw or h > ph):
            _place_tiled(result, idx, bb_min, w, h, pw, ph,
                         tile_overlap_mm, current_page, settings.margin_mm)
            current_page = result.pages  # posun na další stránku po dlaždicích
            continue

        # Try to place on current shelf
        if shelf_x + w > pw:
            # New shelf
            shelf_y += shelf_height
            shelf_x = 0.0
            shelf_height = 0.0

        if shelf_y + h > ph:
            # New page
            current_page += 1
            shelf_x = 0.0
            shelf_y = 0.0
            shelf_height = 0.0

        offset = np.array(
            [shelf_x - float(bb_min[0]), shelf_y - float(bb_min[1])],
            dtype=np.float64,
        )

        result.placements.append(
            PlacedPart(
                part_id=idx,
                page_index=current_page,
                offset=offset,
                rotation=rotation,
                bbox_min=np.array([shelf_x, shelf_y]),
                bbox_max=np.array([shelf_x + w, shelf_y + h]),
            )
        )

        shelf_x += w + 2.0  # 2 mm mezera
        shelf_height = max(shelf_height, h)

    result.pages = current_page + 1
    return result


def _place_tiled(
    result: LayoutResult,
    part_id: int,
    bb_min: NDArray[np.float64],
    w: float,
    h: float,
    pw: float,
    ph: float,
    overlap: float,
    start_page: int,
    margin: float,
) -> None:
    """Rozdělí velký díl na dlaždice a umístí je na samostatné stránky."""
    tile_w = pw - overlap
    tile_h = ph - overlap
    cols = max(1, math.ceil(w / tile_w))
    rows = max(1, math.ceil(h / tile_h))

    page = start_page
    for row in range(rows):
        for col in range(cols):
            ox = col * tile_w
            oy = row * tile_h

            offset = np.array(
                [ox - float(bb_min[0]), oy - float(bb_min[1])],
                dtype=np.float64,
            )

            result.placements.append(
                PlacedPart(
                    part_id=part_id,
                    page_index=page,
                    offset=-offset,  # záporné posun — ořez na dlaždici
                    bbox_min=np.array([0.0, 0.0]),
                    bbox_max=np.array([pw, ph]),
                    is_tile=True,
                    tile_row=row,
                    tile_col=col,
                    source_part_id=part_id,
                )
            )
            page += 1

    result.pages = page

    result.pages = current_page + 1
    return result
