"""Testy pro core_geometry/backend.py — geometrický backend."""

import pytest

from archpapercraft.core_geometry.backend import (
    get_backend,
    MeshBackend,
    GeometryBackend,
)
from archpapercraft.core_geometry.primitives import make_box_mesh


class TestMeshBackend:
    def test_get_default(self):
        be = get_backend("mesh")
        assert isinstance(be, MeshBackend)
        assert be.name == "mesh"
        assert not be.supports_csg

    def test_union_concatenates(self):
        a = make_box_mesh(1, 1, 1)
        b = make_box_mesh(1, 1, 1)
        result = get_backend("mesh").boolean_union(a, b)
        assert result.num_vertices == a.num_vertices + b.num_vertices

    def test_difference_placeholder(self):
        a = make_box_mesh(1, 1, 1)
        b = make_box_mesh(0.5, 0.5, 0.5)
        result = get_backend("mesh").boolean_difference(a, b)
        # Placeholder vrací a beze změny
        assert result.num_vertices == a.num_vertices

    def test_intersect_placeholder(self):
        a = make_box_mesh(1, 1, 1)
        b = make_box_mesh(0.5, 0.5, 0.5)
        result = get_backend("mesh").boolean_intersect(a, b)
        assert result.num_vertices == a.num_vertices


class TestAutoBackend:
    def test_auto_returns_backend(self):
        be = get_backend("auto")
        assert isinstance(be, GeometryBackend)

    def test_auto_is_mesh_without_occ(self):
        """Bez pythonocc-core by auto měl vrátit MeshBackend."""
        from archpapercraft.core_geometry.primitives import OCC_AVAILABLE
        if OCC_AVAILABLE:
            pytest.skip("OCC is installed — test only relevant without it")
        be = get_backend("auto")
        assert isinstance(be, MeshBackend)


class TestOCCBackend:
    def test_occ_unavailable_raises(self):
        from archpapercraft.core_geometry.primitives import OCC_AVAILABLE
        if OCC_AVAILABLE:
            pytest.skip("Test only relevant when OCC is NOT installed")
        with pytest.raises(RuntimeError, match="pythonocc-core"):
            get_backend("occ")
