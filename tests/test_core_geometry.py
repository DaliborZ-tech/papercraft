"""Tests for core_geometry: primitives, operations, mesh, validation."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import (
    MeshData,
    make_box_mesh,
    make_cone_mesh,
    make_cylinder_mesh,
)
from archpapercraft.core_geometry.mesh import compute_face_normals, compute_face_areas
from archpapercraft.core_geometry.validation import validate_mesh, fix_normals_consistent
from archpapercraft.core_geometry.operations import (
    boolean_union_mesh,
    extrude_profile_mesh,
    revolve_profile_mesh,
    translate_mesh,
    scale_mesh,
    mirror_mesh,
)


class TestBoxMesh:
    def test_vertex_count(self):
        mesh = make_box_mesh(2, 3, 4)
        assert mesh.num_vertices == 8

    def test_face_count(self):
        mesh = make_box_mesh(2, 3, 4)
        assert mesh.num_faces == 12  # 6 sides × 2 triangles

    def test_dimensions(self):
        mesh = make_box_mesh(2, 3, 4)
        extent = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
        np.testing.assert_allclose(extent, [2, 3, 4])


class TestCylinderMesh:
    def test_segments(self):
        mesh = make_cylinder_mesh(1.0, 2.0, segments=16)
        # 16 bottom + 16 top + 2 center = 34
        assert mesh.num_vertices == 34

    def test_height(self):
        mesh = make_cylinder_mesh(1.0, 5.0, segments=8)
        assert mesh.vertices[:, 2].max() == pytest.approx(5.0)


class TestConeMesh:
    def test_sharp_cone(self):
        mesh = make_cone_mesh(1.0, 0.0, 3.0, segments=8)
        assert mesh.num_vertices > 0
        assert mesh.num_faces > 0

    def test_truncated_cone(self):
        mesh = make_cone_mesh(2.0, 1.0, 4.0, segments=16)
        assert mesh.num_faces > 0


class TestMeshUtilities:
    def test_face_normals_shape(self):
        mesh = make_box_mesh(1, 1, 1)
        normals = compute_face_normals(mesh)
        assert normals.shape == (12, 3)

    def test_face_areas_positive(self):
        mesh = make_box_mesh(1, 1, 1)
        areas = compute_face_areas(mesh)
        assert all(a > 0 for a in areas)


class TestValidation:
    def test_box_is_valid(self):
        mesh = make_box_mesh(1, 1, 1)
        report = validate_mesh(mesh)
        assert len(report.degenerate_faces) == 0

    def test_empty_mesh(self):
        mesh = MeshData(
            vertices=np.empty((0, 3), dtype=np.float64),
            faces=np.empty((0, 3), dtype=np.int32),
        )
        report = validate_mesh(mesh)
        assert not report.is_valid


class TestOperations:
    def test_translate(self):
        mesh = make_box_mesh(1, 1, 1)
        moved = translate_mesh(mesh, np.array([10, 20, 30]))
        center = moved.vertices.mean(axis=0)
        np.testing.assert_allclose(center, [10, 20, 30], atol=1e-9)

    def test_scale(self):
        mesh = make_box_mesh(1, 1, 1)
        scaled = scale_mesh(mesh, np.array([2, 3, 4]))
        extent = scaled.vertices.max(axis=0) - scaled.vertices.min(axis=0)
        np.testing.assert_allclose(extent, [2, 3, 4])

    def test_mirror(self):
        mesh = make_box_mesh(2, 2, 2)
        mirrored = mirror_mesh(mesh, axis=0)
        # X coords flipped
        assert mirrored.vertices[:, 0].min() == pytest.approx(-1.0)

    def test_union(self):
        a = make_box_mesh(1, 1, 1)
        b = make_box_mesh(1, 1, 1)
        combined = boolean_union_mesh(a, b)
        assert combined.num_vertices == a.num_vertices + b.num_vertices

    def test_extrude(self):
        profile = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)
        mesh = extrude_profile_mesh(profile, np.array([0, 0, 1.0]), 5.0)
        assert mesh.num_faces == 8  # 4 sides × 2 tris

    def test_revolve(self):
        profile = np.array([[1.0, 0.0], [1.5, 1.0], [1.0, 2.0]], dtype=np.float64)
        mesh = revolve_profile_mesh(profile, segments=16, angle_deg=360)
        assert mesh.num_faces > 0
        assert mesh.num_vertices == 16 * 3
