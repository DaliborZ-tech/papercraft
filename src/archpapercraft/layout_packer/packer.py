"""Page packing — place unfolded parts onto A4/A3/Letter sheets.

Uses a simple bottom-left shelf algorithm.  A more advanced approach (NFDH,
Guillotine, etc.) can be swapped in later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class PaperSize(Enum):
    A4 = auto()
    A3 = auto()
    LETTER = auto()


# Real paper dimensions in mm (width, height) — portrait orientation
PAPER_DIMS: dict[PaperSize, tuple[float, float]] = {
    PaperSize.A4: (210.0, 297.0),
    PaperSize.A3: (297.0, 420.0),
    PaperSize.LETTER: (215.9, 279.4),
}


class Orientation(Enum):
    PORTRAIT = auto()
    LANDSCAPE = auto()


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
    """A part positioned on a specific page."""

    part_id: int
    page_index: int
    offset: NDArray[np.float64]  # (2,) — translation in mm
    # bounding box after placement (for debugging)
    bbox_min: NDArray[np.float64] = field(default_factory=lambda: np.zeros(2))
    bbox_max: NDArray[np.float64] = field(default_factory=lambda: np.zeros(2))


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
) -> LayoutResult:
    """Pack 2-D part outlines onto pages.

    Parameters
    ----------
    part_outlines
        List of (N_i, 2) arrays — 2-D vertex positions of each part (in model units).
    settings
        Page settings.
    scale
        Model→paper scale factor (e.g., for 1:100 pass 10 to convert m→mm).

    Returns
    -------
    LayoutResult with page count and per-part placement info.
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
                bbox_min=np.array([shelf_x, shelf_y]),
                bbox_max=np.array([shelf_x + w, shelf_y + h]),
            )
        )

        shelf_x += w + 2.0  # 2 mm gap
        shelf_height = max(shelf_height, h)

    result.pages = current_page + 1
    return result
