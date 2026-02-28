"""3-D transform utilities for scene-graph nodes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass
class Transform:
    """Position + rotation (Euler XYZ in degrees) + uniform / per-axis scale."""

    position: NDArray[np.float64] = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )
    rotation: NDArray[np.float64] = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )
    scale: NDArray[np.float64] = field(
        default_factory=lambda: np.ones(3, dtype=np.float64)
    )

    # ── helpers ────────────────────────────────────────────────────────

    def to_matrix(self) -> NDArray[np.float64]:
        """Return a 4×4 affine matrix (TRS order)."""
        T = np.eye(4, dtype=np.float64)
        T[:3, 3] = self.position

        rx, ry, rz = np.radians(self.rotation)
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)

        R = np.array(
            [
                [cy * cz, -cy * sz, sy],
                [sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy],
                [-cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy],
            ],
            dtype=np.float64,
        )

        S = np.diag(self.scale)

        mat = T.copy()
        mat[:3, :3] = R @ S
        return mat

    def copy(self) -> Transform:
        return Transform(
            position=self.position.copy(),
            rotation=self.rotation.copy(),
            scale=self.scale.copy(),
        )
