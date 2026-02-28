"""Testy pro rozšířený classifier (manifold, scale, readiness score)."""

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import make_box_mesh, make_cylinder_mesh
from archpapercraft.paper_analyzer.classifier import (
    classify_surfaces,
    check_manifold,
    check_scale_readiness,
    papercraft_readiness_score,
    ManifoldReport,
    ScaleReport,
)


class TestManifoldCheck:
    def test_box_is_manifold(self):
        mesh = make_box_mesh(1, 1, 1)
        report = check_manifold(mesh)
        assert report.is_manifold
        assert len(report.non_manifold_edges) == 0

    def test_box_is_watertight(self):
        mesh = make_box_mesh(1, 1, 1)
        report = check_manifold(mesh)
        assert report.is_watertight

    def test_short_edge_detection(self):
        mesh = make_box_mesh(0.001, 0.001, 0.001)
        report = check_manifold(mesh, min_edge_length=0.01)
        assert len(report.short_edges) > 0


class TestScaleReadiness:
    def test_box_at_good_scale(self):
        mesh = make_box_mesh(10, 10, 10)  # 10×10×10 model units (metry)
        report = check_scale_readiness(mesh, scale_factor=0.01)  # 1:100 → 100 mm
        assert report.is_ok

    def test_box_too_large(self):
        mesh = make_box_mesh(100, 100, 100)
        report = check_scale_readiness(
            mesh, scale_factor=10.0,
            max_part_extent_mm=200.0,
        )
        assert not report.is_ok
        assert any("přesahuje" in w.message.lower() or "rozdělit" in w.message.lower()
                    for w in report.warnings)


class TestReadinessScore:
    def test_box_score(self):
        mesh = make_box_mesh(5, 5, 5)
        score = papercraft_readiness_score(mesh, scale_factor=10.0)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # kvádr by měl mít slušné skóre

    def test_cylinder_score(self):
        mesh = make_cylinder_mesh(1.0, 3.0, segments=16)
        score = papercraft_readiness_score(mesh, scale_factor=10.0)
        assert 0.0 <= score <= 1.0
