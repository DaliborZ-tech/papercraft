"""Testy pro scene_graph/snap.py — systém přichytávání."""

import numpy as np
import pytest

from archpapercraft.scene_graph.snap import (
    SnapMode,
    SnapSettings,
    SnapResult,
    snap_to_grid,
    snap_to_vertex,
    snap_to_axis,
    snap_angle,
    snap_point,
)


class TestSnapToGrid:
    def test_basic(self):
        pt = np.array([1.3, 2.7, 0.1])
        settings = SnapSettings(enabled=True, modes=SnapMode.GRID, grid_size=1.0)
        result = snap_to_grid(pt, settings)
        np.testing.assert_allclose(result.position, [1.0, 3.0, 0.0])
        assert result.snapped

    def test_fine_grid(self):
        pt = np.array([0.26, 0.0, 0.0])
        settings = SnapSettings(enabled=True, modes=SnapMode.GRID, grid_size=0.5)
        result = snap_to_grid(pt, settings)
        np.testing.assert_allclose(result.position, [0.5, 0.0, 0.0])


class TestSnapToVertex:
    def test_within_radius(self):
        pt = np.array([1.01, 0.0, 0.0])
        vertices = np.array([[1.0, 0.0, 0.0], [5.0, 5.0, 5.0]])
        settings = SnapSettings(enabled=True, modes=SnapMode.VERTEX, vertex_radius=0.05)
        result = snap_to_vertex(pt, vertices, settings)
        assert result.snapped
        np.testing.assert_allclose(result.position, [1.0, 0.0, 0.0])

    def test_outside_radius(self):
        pt = np.array([1.1, 0.0, 0.0])
        vertices = np.array([[1.0, 0.0, 0.0]])
        settings = SnapSettings(enabled=True, modes=SnapMode.VERTEX, vertex_radius=0.05)
        result = snap_to_vertex(pt, vertices, settings)
        assert not result.snapped


class TestSnapToAxis:
    def test_x_axis(self):
        pt = np.array([5.0, 0.1, 3.0])
        origin = np.array([0.0, 0.0, 0.0])
        settings = SnapSettings(enabled=True, modes=SnapMode.AXIS)
        result = snap_to_axis(pt, origin, settings)
        assert result.snapped
        # Y deviation (0.1) is smallest → Y snapped to origin
        np.testing.assert_allclose(result.position, [5.0, 0.0, 3.0])

    def test_snap_smallest_axis(self):
        """Snap zarovná osu s nejmenší odchylkou od origin."""
        pt = np.array([5.0, 5.0, 0.2])
        origin = np.array([0.0, 0.0, 0.0])
        settings = SnapSettings(enabled=True, modes=SnapMode.AXIS)
        result = snap_to_axis(pt, origin, settings)
        assert result.snapped
        np.testing.assert_allclose(result.position, [5.0, 5.0, 0.0])


class TestSnapAngle:
    def test_45_deg(self):
        """snap_angle vrací float zaokrouhlený na nejbližší násobek step_deg."""
        settings = SnapSettings(enabled=True, modes=SnapMode.ANGLE, angle_step_deg=45.0)
        result = snap_angle(43.0, settings)
        assert result == pytest.approx(45.0)

    def test_no_snap_disabled(self):
        """Když je ANGLE mód vypnutý, vrátí původní úhel."""
        settings = SnapSettings(enabled=True, modes=SnapMode.GRID, angle_step_deg=45.0)
        result = snap_angle(20.0, settings)
        assert result == pytest.approx(20.0)

    def test_snap_15_deg_step(self):
        settings = SnapSettings(enabled=True, modes=SnapMode.ANGLE, angle_step_deg=15.0)
        result = snap_angle(22.0, settings)
        assert result == pytest.approx(15.0)


class TestSnapPoint:
    def test_vertex_priority(self):
        """Vertex snap má přednost před grid snapem."""
        pt = np.array([1.02, 0.0, 0.0])
        vertices = np.array([[1.0, 0.0, 0.0]])
        settings = SnapSettings(
            enabled=True,
            modes=SnapMode.GRID | SnapMode.VERTEX,
            grid_size=0.5,
            vertex_radius=0.05,
        )
        result = snap_point(pt, settings, scene_vertices=vertices)
        assert result.snapped
        assert result.snap_type == SnapMode.VERTEX
        np.testing.assert_allclose(result.position, [1.0, 0.0, 0.0])

    def test_grid_only(self):
        pt = np.array([1.3, 2.7, 0.0])
        settings = SnapSettings(enabled=True, modes=SnapMode.GRID, grid_size=1.0)
        result = snap_point(pt, settings)
        assert result.snapped
        np.testing.assert_allclose(result.position, [1.0, 3.0, 0.0])

    def test_disabled(self):
        pt = np.array([1.3, 2.7, 0.0])
        settings = SnapSettings(enabled=False, grid_size=1.0)
        result = snap_point(pt, settings)
        assert not result.snapped


class TestSnapMode:
    def test_combine(self):
        mode = SnapMode.GRID | SnapMode.VERTEX
        assert SnapMode.GRID in mode
        assert SnapMode.VERTEX in mode
        assert SnapMode.EDGE not in mode
