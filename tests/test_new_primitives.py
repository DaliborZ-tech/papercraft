"""Testy pro nové primitivy a architektonické presety."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import (
    make_sphere_mesh,
    make_torus_mesh,
    make_rectangle_profile,
    make_circle_profile,
    make_polyline_profile,
    make_ngon_profile,
)
from archpapercraft.arch_presets.floor_slab import generate_floor_slab
from archpapercraft.arch_presets.tower import generate_tower
from archpapercraft.arch_presets.buttress import generate_buttress


class TestSphereMesh:
    def test_basic(self):
        mesh = make_sphere_mesh(1.0, segments=8, rings=6)
        assert mesh.num_vertices > 0
        assert mesh.num_faces > 0

    def test_radius(self):
        mesh = make_sphere_mesh(5.0, segments=16, rings=8)
        max_dist = np.linalg.norm(mesh.vertices, axis=1).max()
        assert max_dist == pytest.approx(5.0, abs=0.1)


class TestTorusMesh:
    def test_basic(self):
        mesh = make_torus_mesh(3.0, 1.0, major_segments=16, minor_segments=8)
        assert mesh.num_vertices == 16 * 8
        assert mesh.num_faces > 0

    def test_extent(self):
        mesh = make_torus_mesh(3.0, 1.0)
        max_r = np.sqrt(mesh.vertices[:, 0]**2 + mesh.vertices[:, 1]**2).max()
        assert max_r == pytest.approx(4.0, abs=0.1)  # major + minor


class TestProfiles:
    def test_rectangle(self):
        profile = make_rectangle_profile(10.0, 5.0)
        assert profile.shape == (4, 2)
        extent = profile.max(axis=0) - profile.min(axis=0)
        np.testing.assert_allclose(extent, [10.0, 5.0])

    def test_circle(self):
        profile = make_circle_profile(1.0, segments=32)
        assert profile.shape == (32, 2)
        # Všechny body na poloměru 1
        radii = np.linalg.norm(profile, axis=1)
        np.testing.assert_allclose(radii, 1.0, atol=1e-10)

    def test_polyline(self):
        points = [[0, 0], [1, 0], [1, 1], [0, 1]]
        profile = make_polyline_profile(points)
        assert profile.shape == (4, 2)

    def test_ngon(self):
        profile = make_ngon_profile(1.0, sides=6)
        assert profile.shape == (6, 2)


class TestFloorSlab:
    def test_basic(self):
        mesh = generate_floor_slab(length=10.0, width=8.0, thickness=0.3)
        assert mesh.num_vertices == 8
        assert mesh.num_faces == 12  # kvádr = 6 stran × 2 trojúhelníky

    def test_dimensions(self):
        mesh = generate_floor_slab(5.0, 4.0, 0.2)
        extent = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
        np.testing.assert_allclose(extent, [5.0, 4.0, 0.2])


class TestTower:
    def test_cylindrical(self):
        mesh = generate_tower(shape="cylindrical", radius=2.0, height=10.0, sides=16)
        assert mesh.num_vertices > 0
        assert mesh.num_faces > 0

    def test_polygonal(self):
        mesh = generate_tower(shape="polygonal", radius=2.0, height=8.0, sides=6)
        assert mesh.num_vertices > 0

    def test_with_cornice(self):
        mesh = generate_tower(
            shape="cylindrical", radius=2.0, height=10.0,
            sides=16, cornice_height=0.5, cornice_overhang=0.3,
        )
        max_r = np.sqrt(mesh.vertices[:, 0]**2 + mesh.vertices[:, 1]**2).max()
        assert max_r >= 2.3 - 0.01  # radius + overhang


class TestButtress:
    def test_basic(self):
        mesh = generate_buttress(width=1.0, depth_bottom=2.0, depth_top=0.5, height=5.0)
        assert mesh.num_vertices == 8
        assert mesh.num_faces > 0

    def test_wedge_shape(self):
        mesh = generate_buttress(1.0, 3.0, 0.5, 4.0)
        # Horní hloubka musí být menší než spodní — hloubka je podél osy X (sloupec 0)
        z_top = mesh.vertices[:, 2].max()
        verts_top = mesh.vertices[mesh.vertices[:, 2] > z_top - 0.01]
        verts_bot = mesh.vertices[mesh.vertices[:, 2] < 0.01]
        top_depth = verts_top[:, 0].max() - verts_top[:, 0].min()
        bot_depth = verts_bot[:, 0].max() - verts_bot[:, 0].min()
        assert bot_depth > top_depth
