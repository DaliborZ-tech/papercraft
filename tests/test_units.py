"""Testy pro core_geometry/units.py — jednotkový systém."""

import pytest

from archpapercraft.core_geometry.units import (
    to_mm,
    from_mm,
    convert,
    scale_factor_for_display,
    model_to_paper_mm,
    paper_mm_to_model,
    SUPPORTED_UNITS,
)


class TestToMm:
    def test_mm_identity(self):
        assert to_mm(100.0, "mm") == pytest.approx(100.0)

    def test_cm(self):
        assert to_mm(1.0, "cm") == pytest.approx(10.0)

    def test_m(self):
        assert to_mm(1.0, "m") == pytest.approx(1000.0)

    def test_inch(self):
        assert to_mm(1.0, "in") == pytest.approx(25.4)

    def test_ft(self):
        assert to_mm(1.0, "ft") == pytest.approx(304.8)

    def test_invalid_unit(self):
        with pytest.raises(ValueError, match="Neznámá jednotka"):
            to_mm(1.0, "parsec")


class TestFromMm:
    def test_to_cm(self):
        assert from_mm(100.0, "cm") == pytest.approx(10.0)

    def test_to_m(self):
        assert from_mm(1000.0, "m") == pytest.approx(1.0)


class TestConvert:
    def test_m_to_cm(self):
        assert convert(1.0, "m", "cm") == pytest.approx(100.0)

    def test_in_to_mm(self):
        assert convert(1.0, "in", "mm") == pytest.approx(25.4)


class TestScaleFactor:
    def test_1_100(self):
        assert scale_factor_for_display("1:100") == pytest.approx(0.01)

    def test_1_50(self):
        assert scale_factor_for_display("1:50") == pytest.approx(0.02)

    def test_1_1(self):
        assert scale_factor_for_display("1:1") == pytest.approx(1.0)

    def test_invalid(self):
        assert scale_factor_for_display("invalid") == pytest.approx(1.0)


class TestModelToPaper:
    def test_wall_10m_at_1_100(self):
        """Zeď 10 m v 1:100 → 100 mm na papíře."""
        result = model_to_paper_mm(10.0, "m", "1:100")
        assert result == pytest.approx(100.0)

    def test_roundtrip(self):
        paper = model_to_paper_mm(5.0, "m", "1:50")
        model = paper_mm_to_model(paper, "m", "1:50")
        assert model == pytest.approx(5.0)
