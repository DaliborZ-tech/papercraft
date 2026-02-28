"""Tests for the unfolder (exact + approximate)."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import make_box_mesh
from archpapercraft.seam_editor.auto_seams import auto_seams
from archpapercraft.unfolder.exact_unfold import unfold_part
from archpapercraft.unfolder.approx_unfold import unfold_all_parts
from archpapercraft.unfolder.strategies import generate_gores, generate_rings


class TestExactUnfold:
    def test_single_triangle(self):
        """Unfold a single triangle — should produce 3 vertices in 2-D."""
        verts = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=np.float64)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        from archpapercraft.core_geometry.primitives import MeshData

        mesh = MeshData(vertices=verts, faces=faces)
        result = unfold_part(mesh, [0])
        assert result.vertices_2d.shape[0] == 3
        assert result.vertices_2d.shape[1] == 2

    def test_box_unfold(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = auto_seams(mesh, sharp_angle_deg=60)
        parts = unfold_all_parts(mesh, sg)
        assert len(parts) > 0
        for p in parts:
            assert p.vertices_2d.shape[1] == 2


class TestGores:
    def test_gore_count(self):
        profile = np.array(
            [[1.0, 0.0], [1.5, 1.0], [2.0, 2.0], [1.5, 3.0], [0.5, 4.0], [0.0, 5.0]],
            dtype=np.float64,
        )
        gores = generate_gores(profile, num_gores=12)
        assert len(gores) == 12

    def test_gore_shape(self):
        profile = np.array([[1.0, 0.0], [2.0, 2.0], [0.0, 4.0]], dtype=np.float64)
        gores = generate_gores(profile, num_gores=8)
        for g in gores:
            assert g.shape[1] == 2  # 2-D polygon
            assert g.shape[0] == len(profile) * 2  # left + right sides


class TestRings:
    def test_ring_count(self):
        profile = np.array(
            [[1.0, 0.0], [1.5, 1.0], [2.0, 2.0], [1.5, 3.0], [0.5, 4.0]],
            dtype=np.float64,
        )
        rings = generate_rings(profile, num_rings=4)
        assert len(rings) > 0
        for r in rings:
            assert r.shape == (4, 2)  # trapezoid
