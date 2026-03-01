"""Tests for seam_graph and auto_seams."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import make_box_mesh
from archpapercraft.seam_editor.seam_graph import SeamGraph
from archpapercraft.seam_editor.auto_seams import auto_seams


class TestSeamGraph:
    def test_add_remove_seam(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        assert sg.is_seam(0, 1)
        assert sg.is_seam(1, 0)  # order invariant
        sg.remove_seam(1, 0)
        assert not sg.is_seam(0, 1)

    def test_toggle(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        assert sg.toggle_seam(2, 3) is True
        assert sg.toggle_seam(2, 3) is False

    def test_parts_no_seams(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        parts = sg.compute_parts()
        assert len(parts) == 1  # all connected

    def test_edge_match_ids(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.add_seam(2, 3)
        ids = sg.compute_edge_match_ids()
        assert len(ids) == 2
        assert all(v > 0 for v in ids.values())


class TestAutoSeams:
    def test_box_auto_seams(self):
        mesh = make_box_mesh(2, 2, 2)
        sg = auto_seams(mesh, sharp_angle_deg=60.0)
        # Spanning-tree algorithm keeps connectivity: seams exist but mesh
        # unfolds into a single connected part (cross pattern).
        assert len(sg.seam_edges) > 0
        parts = sg.compute_parts()
        assert len(parts) == 1

    def test_all_edges_present(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = auto_seams(mesh)
        all_e = sg.all_edges()
        assert len(all_e) > 0
