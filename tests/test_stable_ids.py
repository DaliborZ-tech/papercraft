"""Testy pro core_geometry/stable_ids.py — deterministické ID."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import MeshData, make_box_mesh
from archpapercraft.core_geometry.stable_ids import (
    edge_hash,
    edge_midpoint_hash,
    part_hash,
    node_stable_id,
    compute_stable_edge_match_ids,
)


class TestEdgeHash:
    def test_same_edge_same_hash(self):
        mesh = make_box_mesh(1, 1, 1)
        h1 = edge_hash(mesh, 0, 1)
        h2 = edge_hash(mesh, 0, 1)
        assert h1 == h2

    def test_reversed_vertices_same_hash(self):
        """Hash by měl být symetrický — edge(0,1) == edge(1,0)."""
        mesh = make_box_mesh(1, 1, 1)
        h1 = edge_hash(mesh, 0, 1)
        h2 = edge_hash(mesh, 1, 0)
        assert h1 == h2

    def test_different_edge_different_hash(self):
        mesh = make_box_mesh(1, 1, 1)
        h1 = edge_hash(mesh, 0, 1)
        h2 = edge_hash(mesh, 2, 3)
        assert h1 != h2

    def test_hash_is_12_chars(self):
        mesh = make_box_mesh(1, 1, 1)
        h = edge_hash(mesh, 0, 1)
        assert len(h) == 12


class TestMidpointHash:
    def test_deterministic(self):
        mesh = make_box_mesh(2, 2, 2)
        h1 = edge_midpoint_hash(mesh, 0, 1)
        h2 = edge_midpoint_hash(mesh, 0, 1)
        assert h1 == h2


class TestPartHash:
    def test_nonempty(self):
        mesh = make_box_mesh(1, 1, 1)
        h = part_hash(mesh, [0, 1, 2, 3])
        assert len(h) == 12

    def test_empty(self):
        mesh = make_box_mesh(1, 1, 1)
        h = part_hash(mesh, [])
        assert h == "empty_part"

    def test_different_parts(self):
        mesh = make_box_mesh(1, 1, 1)
        h1 = part_hash(mesh, [0, 1])
        h2 = part_hash(mesh, [2, 3])
        assert h1 != h2


class TestNodeStableId:
    def test_deterministic(self):
        id1 = node_stable_id("WALL", "Front Wall", (0, 0, 0))
        id2 = node_stable_id("WALL", "Front Wall", (0, 0, 0))
        assert id1 == id2

    def test_different_position(self):
        id1 = node_stable_id("WALL", "W1", (0, 0, 0))
        id2 = node_stable_id("WALL", "W1", (100, 0, 0))
        assert id1 != id2

    def test_16_chars(self):
        sid = node_stable_id("ROOF", "R1", (0, 0, 0))
        assert len(sid) == 16


class TestStableEdgeMatchIds:
    def test_compute(self):
        mesh = make_box_mesh(1, 1, 1)
        seams = {(0, 1), (2, 3)}
        ids = compute_stable_edge_match_ids(mesh, seams)
        assert len(ids) == 2
        # Všechna ID jsou neprázdné stringy
        for edge, eid in ids.items():
            assert isinstance(eid, str)
            assert len(eid) > 0
