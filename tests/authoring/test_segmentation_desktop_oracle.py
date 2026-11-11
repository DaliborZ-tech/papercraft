"""Check the proof's independent hand-specified witness, without a desktop run."""

import importlib.util
import math
from fractions import Fraction
from pathlib import Path


def oracle_module():
    path = Path(__file__).resolve().parents[2] / "tools/authoring/segmentation_desktop_steps.py"
    spec = importlib.util.spec_from_file_location("segmentation_desktop_oracle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_target_and_flat_triangle_have_independent_analytic_values():
    oracle = oracle_module()
    assert oracle.source_point(Fraction(1, 2), Fraction(1, 4)) == [
        20,
        Fraction(5, 2),
        Fraction(15, 2),
    ]
    # First cell's lower triangle. A=(0,0,0), B=(5,0,0),
    # C=(5,5/8,15/2); its cross product is (0,-75/2,25/8).
    points = [
        oracle.source_point(*uv)
        for uv in ((0, 0), (Fraction(1, 8), 0), (Fraction(1, 8), Fraction(1, 4)))
    ]
    expected = math.sqrt((75 / 2) ** 2 + (25 / 8) ** 2) / 2
    assert math.isclose(oracle.triangle_area(points), expected, abs_tol=1e-12, rel_tol=0)


def test_reversing_triangle_does_not_change_cut_material_area():
    oracle = oracle_module()
    points = [[3, 2, 1], [3, 6, 1], [3, 2, 7]]
    assert oracle.triangle_area(points) == oracle.triangle_area(list(reversed(points))) == 12
