"""Analytic expectations for the independent vector-file audit tool."""

import importlib.util
import math
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "vector_curve_oracle", Path(__file__).resolve().parents[2]
    / "tools/authoring/vector_curve_oracle.py",
)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def test_native_circle_and_reversed_hole_green_integrals():
    assert oracle.svg_signed_area("M 20 0 A 20 20 0 0 1 0 20 "
                                  "A 20 20 0 0 1 -20 0 A 20 20 0 0 1 0 -20 "
                                  "A 20 20 0 0 1 20 0 Z") == pytest.approx(400 * math.pi)
    assert oracle.svg_signed_area("M 20 0 A 20 20 0 0 0 -20 0 "
                                  "A 20 20 0 0 0 20 0 Z") == pytest.approx(-400 * math.pi)


def test_cubic_arch_area_has_independent_polynomial_integral():
    # x'=60+120t-120t², y=90t-90t²; integral y dx =1260.
    # A rectangular base adds80*10=800, total2060, clockwise traversal.
    assert oracle.svg_signed_area(
        "M 0 0 C 20 30 60 30 80 0 L 80 -10 L 0 -10 Z"
    ) == pytest.approx(-2060)


def test_oracle_refuses_unhandled_elliptical_geometry():
    with pytest.raises(AssertionError):
        oracle.svg_signed_area("M 20 0 A 20 10 0 0 1 0 10 Z")
