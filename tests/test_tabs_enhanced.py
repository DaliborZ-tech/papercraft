"""Testy pro rozšířené chlopně, sestavovací návod a značení."""

import numpy as np
import pytest

from archpapercraft.tabs_generator.tabs import (
    TabSettings,
    TabShape,
    TabSide,
    generate_tab,
    generate_relief_cuts,
)
from archpapercraft.tabs_generator.markings import (
    classify_folds,
    FoldType,
    MarkerType,
    add_up_arrows,
    add_registration_marks,
)
from archpapercraft.tabs_generator.build_guide import (
    generate_build_guide,
    BuildGuide,
    PartInfo,
)


class TestToothTab:
    def test_tooth_shape(self):
        p0 = np.array([0.0, 0.0])
        p1 = np.array([10.0, 0.0])
        settings = TabSettings(shape=TabShape.TOOTH, tooth_count=4)
        tab = generate_tab(p0, p1, settings)
        assert tab is not None
        assert tab.polygon.shape[0] > 4  # více bodů než obdélník


class TestInnerTab:
    def test_inner_side(self):
        p0 = np.array([0.0, 0.0])
        p1 = np.array([10.0, 0.0])
        settings = TabSettings(shape=TabShape.STRAIGHT, side=TabSide.INNER)
        tab = generate_tab(p0, p1, settings)
        assert tab is not None
        assert tab.side == TabSide.INNER
        # Vnitřní chlopeň — normála opačným směrem
        assert tab.polygon[2][1] < 0  # pod základní linkou


class TestGlueMarginOnly:
    def test_thin_margin(self):
        p0 = np.array([0.0, 0.0])
        p1 = np.array([10.0, 0.0])
        settings = TabSettings(glue_margin_only=True, width_mm=5.0)
        tab = generate_tab(p0, p1, settings)
        assert tab is not None
        # Šířka by měla být max 1.5 mm
        max_y = tab.polygon[:, 1].max()
        assert max_y <= 1.6


class TestReliefCuts:
    def test_no_cuts_for_isolated(self):
        verts = np.array([[0, 0], [10, 0], [10, 10]], dtype=np.float64)
        cuts = generate_relief_cuts(verts, [(0, 1)], TabSettings())
        assert len(cuts) == 0  # žádný sdílený vrchol

    def test_cuts_at_shared_vertex(self):
        verts = np.array([[0, 0], [10, 0], [0, 10]], dtype=np.float64)
        # Dvě hrany sdílejí vrchol 0
        cuts = generate_relief_cuts(verts, [(0, 1), (0, 2)], TabSettings())
        assert len(cuts) > 0


class TestOrientationMarkers:
    def test_up_arrow(self):
        markings = classify_folds(
            np.array([[0, 0], [10, 0], [10, 10]], dtype=np.float64),
            [(0, 1)],
        )
        add_up_arrows(markings, np.array([[0, 0], [10, 0], [10, 10]], dtype=np.float64))
        assert len(markings.markers) == 1
        assert markings.markers[0].marker_type == MarkerType.UP_ARROW

    def test_registration(self):
        verts = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        markings = classify_folds(verts, [])
        add_registration_marks(markings, verts)
        assert len(markings.markers) == 4  # 4 rohy


class TestBuildGuide:
    def test_generate(self):
        m1 = classify_folds(
            np.array([[0, 0], [10, 0], [10, 10]], dtype=np.float64),
            [(0, 1)], part_id=1,
        )
        m1.edge_labels = {(0, 1): 10}
        m2 = classify_folds(
            np.array([[0, 0], [5, 0], [5, 5]], dtype=np.float64),
            [(0, 1)], part_id=2,
        )
        m2.edge_labels = {(0, 1): 10}

        guide = generate_build_guide([m1, m2], project_name="Test")
        assert len(guide.parts) == 2
        assert len(guide.edge_matches) == 1
        assert guide.edge_matches[0].match_id == 10

    def test_text_output(self):
        m1 = classify_folds(
            np.array([[0, 0], [10, 0]], dtype=np.float64),
            [], part_id=1,
        )
        guide = generate_build_guide([m1])
        text = guide.to_text()
        assert "SESTAVOVACÍ NÁVOD" in text
        assert "LEGENDA" in text

    def test_legend(self):
        guide = BuildGuide()
        assert len(guide.legend) > 0
        assert any("Horský" in item for item in guide.legend)
