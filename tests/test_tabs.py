"""Tests for tabs_generator: tabs and markings."""

import numpy as np
import pytest

from archpapercraft.tabs_generator.tabs import (
    Tab,
    TabSettings,
    TabShape,
    generate_tab,
    generate_tabs_for_part,
)
from archpapercraft.tabs_generator.markings import classify_folds, FoldType


class TestTabGeneration:
    def test_straight_tab(self):
        p0 = np.array([0.0, 0.0])
        p1 = np.array([10.0, 0.0])
        settings = TabSettings(shape=TabShape.STRAIGHT, width_mm=5.0)
        tab = generate_tab(p0, p1, settings, match_id=1)
        assert tab is not None
        assert tab.polygon.shape == (4, 2)
        assert tab.match_id == 1

    def test_tapered_tab(self):
        p0 = np.array([0.0, 0.0])
        p1 = np.array([10.0, 0.0])
        settings = TabSettings(shape=TabShape.TAPERED, width_mm=6.0, taper_ratio=0.5)
        tab = generate_tab(p0, p1, settings)
        assert tab is not None
        assert tab.polygon.shape == (4, 2)

    def test_disabled(self):
        p0 = np.array([0.0, 0.0])
        p1 = np.array([10.0, 0.0])
        settings = TabSettings(enabled=False)
        assert generate_tab(p0, p1, settings) is None

    def test_zero_length_edge(self):
        p0 = np.array([5.0, 5.0])
        p1 = np.array([5.0, 5.0])
        settings = TabSettings()
        assert generate_tab(p0, p1, settings) is None

    def test_grammage_width(self):
        s160 = TabSettings(grammage=160)
        s250 = TabSettings(grammage=250)
        assert s250.width_mm > s160.width_mm


class TestMarkings:
    def test_classify_folds(self):
        verts = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        fold_edges = [(0, 1), (1, 2)]
        markings = classify_folds(verts, fold_edges, part_id=0)
        assert len(markings.fold_lines) == 2
        assert all(fl.fold_type == FoldType.MOUNTAIN for fl in markings.fold_lines)
