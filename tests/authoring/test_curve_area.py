"""Independent analytic area oracles for actual serialized native paths."""

import math
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction

import pytest

from archpapercraft.authoring.curve_area import native_region_area_bounds


def rectangle(x=0, y=0, width=100, height=100):
    return [("M", x, y), ("L", x+width, y), ("L", x+width, y+height),
            ("L", x, y+height), ("Z",)]


def circle(radius=20, sweep=1):
    return [("M", radius, 0), ("A", radius, radius, 0, 0, sweep, -radius, 0),
            ("A", radius, radius, 0, 0, sweep, radius, 0), ("Z",)]


def assert_pi_multiple(bounds, multiple):
    # Published decimal digits, independent of the implementation's Machin series.
    pi_low = Fraction(
        "3.141592653589793238462643383279502884197169399375105820974944592307816406286")
    pi_high = pi_low + Fraction(1, 10**75)
    low, high = bounds
    assert low <= multiple*pi_low <= multiple*pi_high <= high
    assert high-low < Fraction(1, 10**20)


@pytest.mark.parametrize("sweep", [0, 1])
def test_circle_uses_analytic_pi_and_winding_does_not_fill_hole(sweep):
    assert_pi_multiple(native_region_area_bounds([circle(sweep=sweep)]), 400)
    low, high = native_region_area_bounds([circle(sweep=sweep), rectangle()])
    pi = math.pi
    assert abs(float((low+high)/2) - (10000-400*pi)) < 1e-10
    assert high-low < Fraction(1, 10**20)


def test_exact_cubic_green_integral_not_control_polygon_or_samples():
    # x=12t²-8t³, y=12t-12t²; ∫y dx = 48/5.
    arch = [("M", 0, 0), ("C", 0, 4, 4, 4, 4, 0), ("L", 0, 0), ("Z",)]
    assert native_region_area_bounds([arch]) == (Fraction(48, 5), Fraction(48, 5))
    reverse = [("M", 0, 0), ("L", 4, 0), ("C", 4, 4, 0, 4, 0, 0), ("Z",)]
    assert native_region_area_bounds([reverse]) == native_region_area_bounds([arch])


def test_cubic_area_and_line_tab_are_additive():
    # Same arch, rectangle below it contributes another 8 square mm.
    with_tab = [("M", 0, 0), ("C", 0, 4, 4, 4, 4, 0),
                ("L", 4, -2), ("L", 0, -2), ("Z",)]
    assert native_region_area_bounds([with_tab]) == (Fraction(88, 5), Fraction(88, 5))


def test_decimal_and_fraction_coordinates_are_never_binary_rounded():
    epsilon = Fraction(1, 10**17)
    loop = [("M", Decimal("0.1"), "0.2"), ("L", Fraction(11, 10)+epsilon, "0.2"),
            ("L", Fraction(11, 10)+epsilon, "1.2"), ("L", "0.1", "1.2"), ("Z",)]
    assert native_region_area_bounds([loop]) == (1+epsilon, 1+epsilon)


def test_exact_binary_float_semantics_and_outward_public_quantization():
    loop = rectangle(width=0.1, height=0.1)
    expected = Fraction(0.1)**2
    low, high = native_region_area_bounds([loop])
    assert low <= expected <= high
    assert low.denominator <= 10**24 and high.denominator <= 10**24


@pytest.mark.parametrize("large,sweep,expected", [(0, 1, "minor"), (1, 1, "major"),
                                                   (0, 0, "minor"), (1, 0, "major")])
def test_quarter_and_large_arc_actual_endpoint_centers(large, sweep, expected):
    loop = [("M", 1, 0), ("A", 1, 1, 37, large, sweep, 0, 1), ("Z",)]
    low, high = native_region_area_bounds([loop])
    # Circular segment areas: minor π/4-1/2, major 3π/4+1/2.
    oracle = math.pi/4-0.5 if expected == "minor" else 3*math.pi/4+0.5
    assert abs(float((low+high)/2)-oracle) < 1e-14
    assert high-low < Fraction(1, 10**20)


def test_quarter_disk_and_negative_translated_coordinates():
    loop = [("M", -3, -4), ("L", -1, -4), ("A", 2, 2, 0, 0, 1, -3, -2), ("Z",)]
    assert_pi_multiple(native_region_area_bounds([loop]), 1)


def test_svg_radius_correction_is_applied_to_actual_arc():
    loop = [("M", -2, 0), ("A", 1, 1, 0, 0, 1, 2, 0), ("Z",)]
    assert_pi_multiple(native_region_area_bounds([loop]), 2)


def test_actual_serialized_cubic_circle_area_not_nominal_circle_area():
    # Four common PDF cubic quarter-circles, with actual serialized decimal
    # handles. Analytic unit area is 2 + 12k/5 - 3k²/5, not π.
    k = Fraction("0.552285")
    h = 20*k
    loop = [("M", 20, 0), ("C", 20, h, h, 20, 0, 20),
            ("C", -h, 20, -20, h, -20, 0),
            ("C", -20, -h, -h, -20, 0, -20),
            ("C", h, -20, 20, -h, 20, 0), ("Z",)]
    expected = 400*(2+Fraction(12, 5)*k-Fraction(3, 5)*k*k)
    low, high = native_region_area_bounds([loop])
    assert low == high == expected
    assert abs(float(low)-400*math.pi) > 0.01


def test_cubic_translation_and_scale_preserve_exact_integral():
    loop = [("M", 0, 0), ("C", 0, 4, 4, 4, 4, 0), ("Z",)]
    shifted = []
    for operation, *coordinates in loop:
        values = [Fraction(value)*3 + (1000000 if i % 2 == 0 else -2000000)
                  for i, value in enumerate(coordinates)]
        shifted.append((operation, *values))
    assert native_region_area_bounds([shifted]) == (Fraction(432, 5), Fraction(432, 5))


def test_holes_are_subtracted_regardless_of_order_and_winding():
    loops = [rectangle(2, 2, 2, 3), rectangle(0, 0, 10, 10),
             [("M", 5, 5), ("L", 5, 7), ("L", 7, 7), ("L", 7, 5), ("Z",)]]
    assert native_region_area_bounds(loops) == (90, 90)
    original = deepcopy(loops)
    native_region_area_bounds(loops)
    assert loops == original


@pytest.mark.parametrize("loop", [
    [], [("M", 0, 0), ("L", 1, 0)],
    [("M", 0, 0), ("M", 1, 0), ("Z",)],
    [("M", 0, 0), ("A", 1, 2, 0, 0, 1, 1, 0), ("Z",)],
    [("M", 0, 0), ("A", -1, -1, 0, 0, 1, 1, 0), ("Z",)],
    [("M", 0, 0), ("A", 0, 0, 0, 0, 1, 1, 0), ("Z",)],
    [("M", 0, 0), ("A", 1, 1, 0, 0, 1, 0, 0), ("Z",)],
    [("M", 0, 0), ("L", float("inf"), 1), ("Z",)],
    [("M", 0, False), ("Z",)],
    [("M", 0, 0), ("L", 1, 0), ("Z",)],
    [("M", 0, 0), ("l", 1, 1), ("Z",)],
    [("M", 0, 0), ("Z",), ("L", 1, 1)],
])
def test_unsupported_or_degenerate_paths_are_explicit_errors(loop):
    with pytest.raises(ValueError):
        native_region_area_bounds([loop])


def test_missing_outer_ambiguous_outer_and_budget_are_explicit_errors():
    with pytest.raises(ValueError):
        native_region_area_bounds([])
    with pytest.raises(ValueError):
        native_region_area_bounds([rectangle(), rectangle()])
    with pytest.raises(ValueError, match="budget"):
        native_region_area_bounds([rectangle()], max_commands=4)
    with pytest.raises(ValueError, match="budget"):
        native_region_area_bounds([rectangle()], max_commands=False)
