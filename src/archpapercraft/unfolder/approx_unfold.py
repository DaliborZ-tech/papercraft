"""Approximate unfolding via per-face unrolling (facet strategy) and
integration with gore/ring strategies for bodies of revolution.
"""

from __future__ import annotations

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.seam_editor.seam_graph import SeamGraph
from archpapercraft.unfolder.exact_unfold import UnfoldedPart, unfold_part
from archpapercraft.unfolder.strategies import (
    UnfoldStrategy,
    generate_gores,
    generate_rings,
)

import numpy as np


def unfold_all_parts(
    mesh: MeshData,
    seam_graph: SeamGraph,
) -> list[UnfoldedPart]:
    """Unfold every connected part of *seam_graph* and return 2-D results."""
    parts_faces = seam_graph.compute_parts()
    results: list[UnfoldedPart] = []

    for pid, face_list in enumerate(parts_faces):
        part = unfold_part(
            mesh=mesh,
            face_indices=face_list,
            seam_edges=seam_graph.seam_edges,
            part_id=pid,
        )
        results.append(part)

    return results


def unfold_revolution_body(
    profile_2d: np.ndarray,
    strategy: UnfoldStrategy = UnfoldStrategy.GORES,
    num_segments: int = 16,
) -> list[np.ndarray]:
    """Unfold a body-of-revolution using one of the approximate strategies.

    Returns a list of 2-D polygon outlines (one per gore / ring).
    """
    if strategy == UnfoldStrategy.GORES:
        return generate_gores(profile_2d, num_gores=num_segments)
    elif strategy == UnfoldStrategy.RINGS:
        return generate_rings(profile_2d, num_rings=num_segments)
    else:
        raise NotImplementedError(f"Strategy {strategy} not implemented for revolution bodies")
