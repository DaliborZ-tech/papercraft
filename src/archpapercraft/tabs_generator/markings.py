"""Fold-line and numbering markings for papercraft parts.

Fold types:
- **Mountain fold** — folded away from viewer (dashed line ── ── ──)
- **Valley fold** — folded toward viewer (dash-dot ─·─·─)

Each part gets a sequential Part ID, and each cut edge gets a Match ID so the
builder knows what glues to what.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class FoldType(Enum):
    MOUNTAIN = auto()
    VALLEY = auto()


@dataclass
class FoldLine:
    p0: NDArray[np.float64]
    p1: NDArray[np.float64]
    fold_type: FoldType = FoldType.MOUNTAIN


@dataclass
class PartMarkings:
    """All markings for one unfolded part."""

    part_id: int
    fold_lines: list[FoldLine] = field(default_factory=list)
    edge_labels: dict[tuple[int, int], int] = field(default_factory=dict)  # edge → match ID

    def add_fold(
        self,
        p0: NDArray[np.float64],
        p1: NDArray[np.float64],
        dihedral_deg: float = 0.0,
    ) -> None:
        """Add a fold line; classify as mountain or valley by dihedral angle."""
        ft = FoldType.MOUNTAIN if dihedral_deg >= 0 else FoldType.VALLEY
        self.fold_lines.append(FoldLine(p0=p0, p1=p1, fold_type=ft))


def classify_folds(
    vertices_2d: NDArray[np.float64],
    fold_edges: list[tuple[int, int]],
    part_id: int = 0,
) -> PartMarkings:
    """Create markings for fold edges.  Default to mountain for now."""
    markings = PartMarkings(part_id=part_id)
    for v0, v1 in fold_edges:
        markings.add_fold(vertices_2d[v0], vertices_2d[v1], dihedral_deg=1.0)
    return markings
