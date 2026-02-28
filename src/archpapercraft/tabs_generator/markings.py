"""Značení přehybů, číslování a orientační značky pro papírové díly.

Typy přehybů:
- **Horský přehyb** (mountain fold) — přehnuto od pozorovatele (čárkovaně ── ── ──)
- **Údolní přehyb** (valley fold) — přehnuto k pozorovateli (čerchovaně ─·─·─)

Každý díl dostane sekvenční ID dílu a každá řezná hrana dostane Match ID,
aby stavitel věděl, co se lepí k čemu.

Pokročilé funkce:
- Orientační značky (šipky nahoru, osy, registrační křížky)
- Generátor sestavovacího návodu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class FoldType(Enum):
    MOUNTAIN = auto()
    VALLEY = auto()


class MarkerType(Enum):
    """Typ orientační značky."""
    UP_ARROW = auto()       # šipka nahoru (orientace dílu)
    AXIS_INDICATOR = auto()  # osa X/Y
    REGISTRATION = auto()    # registrační křížek pro zarovnání
    GRAIN_ARROW = auto()     # směr vlákna papíru


@dataclass
class FoldLine:
    p0: NDArray[np.float64]
    p1: NDArray[np.float64]
    fold_type: FoldType = FoldType.MOUNTAIN
    angle_deg: float = 0.0  # dihedrální úhel pro vizualizaci


@dataclass
class OrientationMarker:
    """Orientační značka na dílu."""
    position: NDArray[np.float64]
    direction: NDArray[np.float64]  # jednotkový vektor směru
    marker_type: MarkerType = MarkerType.UP_ARROW
    label: str = ""


@dataclass
class PartMarkings:
    """Veškerá značení pro jeden rozložený díl."""

    part_id: int
    fold_lines: list[FoldLine] = field(default_factory=list)
    edge_labels: dict[tuple[int, int], int] = field(default_factory=dict)
    markers: list[OrientationMarker] = field(default_factory=list)
    part_label: str = ""  # volitelný textový popisek dílu

    def add_fold(
        self,
        p0: NDArray[np.float64],
        p1: NDArray[np.float64],
        dihedral_deg: float = 0.0,
    ) -> None:
        """Přidá přehybovou linku; klasifikuje jako horský/údolní přehyb."""
        ft = FoldType.MOUNTAIN if dihedral_deg >= 0 else FoldType.VALLEY
        self.fold_lines.append(FoldLine(p0=p0, p1=p1, fold_type=ft,
                                         angle_deg=dihedral_deg))

    def add_orientation_marker(
        self,
        position: NDArray[np.float64],
        direction: NDArray[np.float64],
        marker_type: MarkerType = MarkerType.UP_ARROW,
        label: str = "",
    ) -> None:
        """Přidá orientační značku na díl."""
        self.markers.append(OrientationMarker(
            position=position, direction=direction,
            marker_type=marker_type, label=label,
        ))


def classify_folds(
    vertices_2d: NDArray[np.float64],
    fold_edges: list[tuple[int, int]],
    part_id: int = 0,
    *,
    dihedral_angles: dict[tuple[int, int], float] | None = None,
) -> PartMarkings:
    """Vytvoří značení pro přehybové hrany.

    Pokud je *dihedral_angles* zadán, klasifikuje přehyby správně.
    Jinak výchozí horský přehyb.
    """
    markings = PartMarkings(part_id=part_id)
    for v0, v1 in fold_edges:
        angle = 1.0  # výchozí horský
        if dihedral_angles:
            e = tuple(sorted((v0, v1)))
            angle = dihedral_angles.get(e, 1.0)
        markings.add_fold(vertices_2d[v0], vertices_2d[v1], dihedral_deg=angle)
    return markings


def add_up_arrows(
    markings: PartMarkings,
    vertices_2d: NDArray[np.float64],
) -> None:
    """Přidá šipku nahoru do těžiště dílu."""
    if len(vertices_2d) == 0:
        return
    centroid = vertices_2d.mean(axis=0)
    direction = np.array([0.0, -1.0])  # nahoru v souřadnicích stránky
    markings.add_orientation_marker(centroid, direction, MarkerType.UP_ARROW)


def add_registration_marks(
    markings: PartMarkings,
    vertices_2d: NDArray[np.float64],
) -> None:
    """Přidá registrační křížky do rohů bounding boxu dílu."""
    if len(vertices_2d) == 0:
        return
    bbox_min = vertices_2d.min(axis=0)
    bbox_max = vertices_2d.max(axis=0)
    corners = [
        bbox_min,
        np.array([bbox_max[0], bbox_min[1]]),
        bbox_max,
        np.array([bbox_min[0], bbox_max[1]]),
    ]
    for corner in corners:
        markings.add_orientation_marker(
            corner, np.array([1.0, 0.0]),
            MarkerType.REGISTRATION, label="+",
        )
