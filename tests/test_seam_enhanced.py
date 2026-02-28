"""Testy pro rozšířený seam editor (lock, paint mode, arch rules)."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import make_box_mesh
from archpapercraft.seam_editor.seam_graph import SeamGraph
from archpapercraft.seam_editor.auto_seams import auto_seams


class TestLockedSeams:
    def test_lock_prevents_remove(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.lock_seam(0, 1)
        assert sg.is_locked(0, 1)
        sg.remove_seam(0, 1)
        assert sg.is_seam(0, 1)  # stále šev — zamčeno

    def test_lock_prevents_toggle(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.lock_seam(0, 1)
        result = sg.toggle_seam(0, 1)
        assert result is True  # stále šev
        assert sg.is_seam(0, 1)

    def test_unlock(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.lock_seam(0, 1)
        sg.unlock_seam(0, 1)
        assert not sg.is_locked(0, 1)
        sg.remove_seam(0, 1)
        assert not sg.is_seam(0, 1)

    def test_lock_all_seams(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.add_seam(2, 3)
        sg.lock_all_seams()
        assert len(sg.locked_edges) == 2

    def test_unlock_all(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.lock_all_seams()
        sg.unlock_all()
        assert len(sg.locked_edges) == 0


class TestPaintMode:
    def test_paint_add(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.paint_seam(0, 1, add=True)
        assert sg.is_seam(0, 1)

    def test_paint_remove(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.paint_seam(0, 1, add=False)
        assert not sg.is_seam(0, 1)

    def test_paint_locked(self):
        mesh = make_box_mesh(1, 1, 1)
        sg = SeamGraph(mesh=mesh)
        sg.add_seam(0, 1)
        sg.lock_seam(0, 1)
        sg.paint_seam(0, 1, add=False)
        assert sg.is_seam(0, 1)  # zamčeno — nelze smazat


class TestArchitectureRules:
    def test_auto_seams_with_rules(self):
        mesh = make_box_mesh(2, 2, 2)
        sg = auto_seams(mesh, sharp_angle_deg=60.0, architecture_rules=True)
        assert len(sg.seam_edges) > 0

    def test_auto_seams_without_rules(self):
        mesh = make_box_mesh(2, 2, 2)
        sg = auto_seams(mesh, sharp_angle_deg=60.0, architecture_rules=False)
        assert len(sg.seam_edges) > 0

    def test_locked_edges_preserved(self):
        mesh = make_box_mesh(2, 2, 2)
        locked = {(0, 1)}
        sg = auto_seams(mesh, locked_edges=locked)
        assert sg.is_locked(0, 1)
