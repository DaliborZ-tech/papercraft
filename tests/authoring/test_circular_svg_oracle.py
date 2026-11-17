"""Independent manufacturing oracle qualification, including radius cancellation."""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[2]/"tools/authoring/circular_svg_oracle.py"
spec = importlib.util.spec_from_file_location("circular_svg_oracle", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
area = module.svg_signed_area


def test_large_radius_short_arc_segment_has_independently_bounded_area():
    actual = area("M 0 0 A 30000000 30000000 0 0 1 10 0 Z")
    # c³/(12R) is the leading term; c²/R² bounds this tiny remainder loosely.
    lower = Decimal(1000)/Decimal(360000000)
    assert lower < actual < lower*(1+Decimal(100)/Decimal(900000000000000))


@pytest.mark.parametrize("shift", ["0", "100000000000000000000"])
def test_parallel_translated_arcs_enclose_exact_three_hundred_mm2(shift):
    x = Decimal(shift)
    value = f"M {x} 0 A 30000000 30000000 0 0 1 {x+10} 0 "
    value += f"L {x+10} 30 A 30000000 30000000 0 0 0 {x} 30 Z"
    assert abs(area(value)-300) < Decimal("1e-50")


def test_compound_circular_hole_has_original_net_area():
    value = "M 10 0 A 10 10 0 0 1 -10 0 A 10 10 0 0 1 10 0 Z "
    value += "M 2 0 A 2 2 0 0 0 -2 0 A 2 2 0 0 0 2 0 Z"
    assert abs(area(value)-Decimal(96)*module.PI) < Decimal("1e-24")


def test_major_arc_sector_and_reversal_keep_oriented_area():
    positive = area("M 0 0 L 1 0 A 1 1 0 1 1 0 -1 L 0 0 Z")
    negative = area("M 0 0 L 0 -1 A 1 1 0 1 0 1 0 L 0 0 Z")
    assert abs(positive-Decimal(3)*module.PI/4) < Decimal("1e-25")
    assert abs(positive+negative) < Decimal("1e-100")


@pytest.mark.parametrize("value", [
    "M 0 0 L 1 1", "M 0 0 A 1 1 0 0 1 3 0 Z",
    "M 0 0 A 1 2 0 0 1 1 0 Z", "M 0 0 A 1 1 0 2 1 1 0 Z",
    "M 0 0 A 1 1 1 0 1 1 0 Z", "M 0 0 A 1 1 0 0 1 0 0 Z",
    "M 0 0 L 1e31 0 Z", "M 0 0 ; L 1 1 Z", "M 0 0 M 1 1 Z", "Z", "",
])
def test_unsupported_or_malformed_input_is_refused(value):
    with pytest.raises(ValueError):
        area(value)
