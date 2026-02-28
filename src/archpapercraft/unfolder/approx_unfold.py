"""Approximate unfolding via per-face unrolling (facet strategy) and
integration with gore/ring strategies for bodies of revolution.
"""

from __future__ import annotations

import logging

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.seam_editor.seam_graph import SeamGraph
from archpapercraft.unfolder.exact_unfold import UnfoldedPart, unfold_part
from archpapercraft.unfolder.strategies import (
    UnfoldStrategy,
    extract_revolution_profile,
    generate_gores,
    generate_rings,
)

import numpy as np
from numpy.typing import NDArray

_log = logging.getLogger(__name__)


# ── core exact unfold ──────────────────────────────────────────────────


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


# ── revolution body helpers ───────────────────────────────────────────


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


def _outline_to_unfolded_part(outline: NDArray[np.float64], part_id: int) -> UnfoldedPart:
    """Convert a 2-D polygon outline to an :class:`UnfoldedPart`.

    Triangulation uses a simple fan from the first vertex.
    """
    n = len(outline)
    if n < 3:
        return UnfoldedPart(
            part_id=part_id,
            vertices_2d=outline,
            faces=np.empty((0, 3), dtype=np.int32),
            vert_map_3d=np.full(n, -1, dtype=np.int32),
        )

    faces = [[0, i, i + 1] for i in range(1, n - 1)]
    cut_edges = [(i, (i + 1) % n) for i in range(n)]

    return UnfoldedPart(
        part_id=part_id,
        vertices_2d=outline.astype(np.float64),
        faces=np.array(faces, dtype=np.int32),
        vert_map_3d=np.full(n, -1, dtype=np.int32),
        fold_edges=[],
        cut_edges=cut_edges,
    )


# ── unified strategy dispatcher (called by UI) ────────────────────────


def unfold_with_strategy(
    mesh: MeshData,
    seam_graph: SeamGraph,
    strategy: str = "Exact",
    segments: int = 16,
) -> list[UnfoldedPart]:
    """Unfold *mesh* using the chosen strategy name from the UI combo-box.

    Strategies
    ----------
    Exact / Facets
        Seam-based BFS edge-unfolding (always works).
    Gores
        Splits a rotationally symmetric body into vertical gore strips.
    Rings
        Splits a rotationally symmetric body into horizontal ring bands.

    If the mesh is not a revolution body, Gores/Rings fall back to Exact
    with a logged warning.
    """
    if strategy in ("Exact", "Facets"):
        return unfold_all_parts(mesh, seam_graph)

    if strategy in ("Gores", "Rings"):
        profile = extract_revolution_profile(mesh)
        if profile is not None:
            strat = UnfoldStrategy.GORES if strategy == "Gores" else UnfoldStrategy.RINGS
            outlines = unfold_revolution_body(profile, strat, segments)
            return [
                _outline_to_unfolded_part(ol, pid)
                for pid, ol in enumerate(outlines)
            ]
        _log.warning(
            "Mesh is not a revolution body — falling back to exact unfold."
        )
        return unfold_all_parts(mesh, seam_graph)

    # Unknown strategy — fallback
    _log.warning("Unknown strategy '%s', using Exact.", strategy)
    return unfold_all_parts(mesh, seam_graph)
