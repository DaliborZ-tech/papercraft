"""Native source topology proofs and regressions against chord-only validity."""

import math
from decimal import Decimal
from fractions import Fraction

import pytest

from archpapercraft.authoring.curve_topology import (
    certify_native_region_separation,
    certify_native_region_topology,
    certify_region_topology,
)
from archpapercraft.authoring.curves import Curve


def polygon(points, prefix="line"):
    return tuple(Curve(a, b, segment_id=f"{prefix}-{i}")
                 for i, (a, b) in enumerate(zip(points, (*points[1:], points[0]))))


def circle(center=(0, 0), radius=1, prefix="circle"):
    x, y = center
    a, b = (x+radius, y), (x-radius, y)
    return (Curve(a, b, "arc", {"center": center, "sweep_deg": 180}, prefix+"-upper"),
            Curve(b, a, "arc", {"center": center, "sweep_deg": 180}, prefix+"-lower"))


def test_p01_shallow_cubic_crossing_behind_valid_chord_rectangle_has_real_witness():
    a, b = (0, 0.0005), (10, 0.0005)
    curve = Curve(a, b, "cubic", {"control1": (3, -0.001), "control2": (7, -0.001)}, "P01")
    outer = (curve, Curve(b, (10, 0)), Curve((10, 0), (0, 0)), Curve((0, 0), a))
    result = certify_region_topology(outer)
    assert result.status == "INVALID", result
    assert result.witness["method"] == "BERNSTEIN_SIGN_CHANGE_WITHIN_LINE_INTERVAL"
    assert "P01" in result.witness["segments"]
    lo, hi = result.witness["line_side_values"]
    assert lo*hi < 0
    assert result.witness["point"] is None  # No fake exact midpoint intersection.


def test_shallow_crossing_remains_invalid_after_large_translation_and_tiny_scale():
    def transform(point):
        return 100+point[0]*1e-4, -200+point[1]*1e-4
    a, b = transform((0, 0.0005)), transform((10, 0.0005))
    curve = Curve(a, b, "cubic", {"control1": transform((3, -0.001)),
                                   "control2": transform((7, -0.001))})
    p, q = transform((10, 0)), transform((0, 0))
    loop = (curve, Curve(b, p), Curve(p, q), Curve(q, a))
    assert certify_region_topology(loop).status == "INVALID"


def test_two_semicircles_are_a_simple_closed_circle_not_a_two_edge_zero_area_chord():
    result = certify_region_topology(circle())
    assert result.status == "VALID", result
    assert result.examined_nodes < 30


def test_quarter_disk_with_native_two_arc_hole_is_proved_inside():
    outer = (Curve((10, 0), (0, 10), "arc", {"center": (0, 0), "sweep_deg": 90}),
             Curve((0, 10), (0, 0)), Curve((0, 0), (10, 0)))
    result = certify_region_topology(outer, (circle((3, 3), 1),))
    assert result.status == "VALID", result


def test_monotone_bezier_arch_and_three_lines_form_valid_material():
    arch = Curve((0, 0), (10, 0), "cubic",
                 {"control1": (0, 8), "control2": (10, 8)}, "arch")
    outer = (arch, Curve((10, 0), (10, -5)), Curve((10, -5), (0, -5)), Curve((0, -5), (0, 0)))
    assert certify_region_topology(outer).status == "VALID"


def test_nonconvex_s_shaped_monotone_cubic_is_not_restricted_to_arch_presets():
    curve = Curve((0, 0), (10, 0), "cubic",
                  {"control1": (3, 8), "control2": (7, -8)})
    outer = (curve, Curve((10, 0), (10, -10)), Curve((10, -10), (0, -10)),
             Curve((0, -10), (0, 0)))
    assert certify_region_topology(outer).status == "VALID"


def test_sharp_gothic_apex_uses_two_distinct_centers_without_smoothing():
    apex = (4, math.sqrt(48))
    left = Curve((0, 0), apex, "arc", {"center": (8, 0), "sweep_deg": -60}, "left")
    right = Curve(apex, (8, 0), "arc", {"center": (0, 0), "sweep_deg": -60}, "right")
    outer = (left, right, Curve((8, 0), (8, -3)), Curve((8, -3), (0, -3)),
             Curve((0, -3), (0, 0)))
    result = certify_region_topology(outer)
    assert result.status == "VALID", result


def test_adjacent_curve_is_not_blanket_ignored_when_it_crosses_near_shared_endpoint():
    # First x=0 line and final cubic share A but cubic crosses x=0 again.
    a, b, c = (0, 0), (0, 10), (10, 10)
    curve = Curve(c, a, "cubic", {"control1": (-2, 8), "control2": (-0.1, 1)}, "near-end")
    result = certify_region_topology((Curve(a, b), Curve(b, c), curve))
    assert result.status == "INVALID", result


@pytest.mark.parametrize("hole,reason", [
    (circle((20, 0), 1), "outside"),
    (circle((9.5, 0), 1), "intersect"),
])
def test_hole_outside_or_intersecting_outer_circle_is_rejected(hole, reason):
    result = certify_region_topology(circle(radius=10), (hole,))
    assert result.status == "INVALID", (reason, result)


def test_tangent_hole_is_never_silently_accepted_as_strictly_inside():
    result = certify_region_topology(circle(radius=10), (circle((9, 0), 1),), max_nodes=2000)
    assert result.status in ("INVALID", "UNRESOLVED"), result


def test_near_touching_holes_with_uncertified_gap_remain_unresolved():
    holes = (circle((-1, 0), 1), circle((1+1e-14, 0), 1))
    result = certify_region_topology(circle(radius=10), holes, max_nodes=2000)
    assert result.status in ("INVALID", "UNRESOLVED"), result


def test_separate_holes_are_valid_but_nested_holes_are_invalid():
    outer = circle(radius=10)
    assert certify_region_topology(outer, (circle((-3, 0), 1), circle((3, 0), 1))).status == "VALID"
    nested = certify_region_topology(outer, (circle(radius=3), circle(radius=1)))
    assert nested.status == "INVALID" and "nested" in nested.reason


def test_tangent_arc_and_nonadjacent_line_reports_analytic_contact_or_unresolved():
    # Circle hole tangent to the top of the rectangle, rather than crossing it.
    outer = polygon(((-3, -3), (3, -3), (3, 1), (-3, 1)))
    result = certify_region_topology(outer, (circle(),))
    assert result.status in ("INVALID", "UNRESOLVED")


def test_nonadjacent_repeated_authored_vertex_is_not_permitted_as_a_shared_endpoint():
    outer = polygon(((0, 0), (2, 2), (0, 2), (2, 0), (2, 2)))
    assert certify_region_topology(outer).status == "INVALID"


def test_coincident_reversed_lines_and_overlapping_arcs_are_not_valid_loops():
    lines = (Curve((0, 0), (1, 0)), Curve((1, 0), (0, 0)))
    assert certify_region_topology(lines).status == "INVALID"
    quarter = Curve((1, 0), (0, 1), "arc", {"center": (0, 0), "sweep_deg": 90})
    reverse = Curve((0, 1), (1, 0), "arc", {"center": (0, 0), "sweep_deg": -90})
    assert certify_region_topology((quarter, reverse)).status == "INVALID"


def test_opposite_semicircles_with_differently_rounded_native_midpoints_are_unresolved():
    # Their raw source circles coincide, but positive/negative trig evaluation
    # yields different fixed native midpoint X coordinates. Do not claim an
    # exact manufactured intersection from those nominal source circles.
    upper = circle()[0]
    reverse = Curve((-1, 0), (1, 0), "arc", {"center": (0, 0), "sweep_deg": -180})
    assert certify_region_topology((upper, reverse)).status == "UNRESOLVED"


def test_t01_nominal_source_circle_cannot_invent_a_native_svg_intersection():
    delta = 1e-14
    arc = Curve((0, 1), (1, 0), "arc",
                {"center": (delta, 0), "sweep_deg": -90}, "T01")
    # SVG's fixed endpoints and radius1 choose the unit circle; its x<=1.
    # The nominal center delta would falsely hit the next vertical line.
    outer = (arc, Curve((1, 0), (1+delta/2, 0)),
             Curve((1+delta/2, 0), (1+delta/2, 2)),
             Curve((1+delta/2, 2), (0, 2)), Curve((0, 2), (0, 1)))
    result = certify_region_topology(outer)
    assert result.status == "UNRESOLVED", result
    assert result.witness is None
    assert result.geometry_scope.startswith("MANUFACTURING_NATIVE_SVG")


def test_retracing_cubic_without_proved_self_monotonicity_never_passes_on_chords():
    curve = Curve((0, 0), (1, 0), "cubic", {"control1": (3, 0), "control2": (-2, 0)})
    result = certify_region_topology((curve, Curve((1, 0), (0, 0))), max_depth=8, max_nodes=500)
    assert result.status in ("INVALID", "UNRESOLVED")


def test_large_source_arc_endpoint_mismatch_does_not_get_endpoint_only_topology_pass():
    sweep = 360-math.degrees(1e-8)
    curve = Curve((1, 0), (1, 1e-8), "arc", {"center": (0, 0), "sweep_deg": sweep})
    result = certify_region_topology((curve, Curve(curve.end, curve.start)))
    assert result.status == "UNRESOLVED" and "endpoint mismatch" in result.reason


@pytest.mark.parametrize("limits", [{"max_nodes": 0}, {"max_nodes": 1}, {"max_depth": 0}])
def test_budget_exhaustion_never_becomes_sampling_validity(limits):
    outer = circle(radius=10)
    result = certify_region_topology(outer, (circle((3, 3), 1),), **limits)
    assert result.status == "UNRESOLVED", result


def test_open_boundary_is_invalid_without_mutation():
    curves = (Curve((0, 0), (1, 0)), Curve((1, 0), (1, 1)))
    result = certify_region_topology(curves)
    assert result.status == "INVALID" and "closed" in result.reason
    assert curves[1].end == (1, 1)


def test_winding_and_topology_are_orientation_independent():
    outer = polygon(((0, 0), (10, 0), (10, 10), (0, 10)))
    reverse = tuple(Curve(c.end, c.start, segment_id=c.segment_id) for c in reversed(outer))
    hole = circle((5, 5), 1)
    assert certify_region_topology(outer, (hole,)).status == "VALID"
    assert certify_region_topology(reverse, (hole,)).status == "VALID"


def native_rectangle(left, bottom, right, top):
    return (("M", left, bottom), ("L", right, bottom), ("L", right, top),
            ("L", left, top), ("Z",))


@pytest.mark.parametrize("gap,expected", [(Fraction(1, 10), "VALID"),
                                         (Fraction(1, 10**14), "UNRESOLVED")])
def test_raw_native_quarter_uses_exact_endpoint_circle_without_nominal_center(gap, expected):
    path = (("M", 0, 1), ("A", 1, 1, 0, 0, 0, 1, 0), ("L", 1+gap, 0),
            ("L", 1+gap, 2), ("L", 0, 2), ("Z",))
    result = certify_native_region_topology(path)
    assert result.status == expected, result
    assert result.geometry_scope == "EXACTLY_SUPPLIED_NATIVE_PATH_GEOMETRY"
    assert result.entry_scope.startswith("SUPPLIED_ABSOLUTE_NATIVE_PATH")


@pytest.mark.parametrize("denominator", [10**20, 10**400])
def test_exact_native_cubic_crossing_survives_decimal_gaps_that_float_would_erase(denominator):
    delta = Fraction(1, denominator)
    # Every y coordinate rounds to1 in binary float. The serialized/rational
    # values instead prove two genuine crossings of the horizontal bottom.
    path = (("M", 0, 1+delta/2),
            ("C", 3, 1-delta, 7, 1-delta, 10, 1+delta/2),
            ("L", 10, 1), ("L", 0, 1), ("Z",))
    result = certify_native_region_topology(path)
    assert result.status == "INVALID", result
    assert result.witness["method"] == "BERNSTEIN_SIGN_CHANGE_WITHIN_LINE_INTERVAL"
    sides = [Fraction(value) for value in result.witness["line_side_values_exact"]]
    assert sides[0]*sides[1] < 0


def test_raw_decimal_fraction_and_string_coordinates_remain_exact_through_hole_winding():
    outer = native_rectangle(Decimal("0"), "0", Fraction(10), "10.000000")
    clockwise_hole = (("M", "2", "2"), ("L", "2", "8"), ("L", "8", "8"),
                      ("L", "8", "2"), ("Z",))
    result = certify_native_region_topology(outer, (clockwise_hole,))
    assert result.status == "VALID", result


def test_actual_six_decimal_native_cubic_path_is_checked_after_serialization():
    path = (("M", "0.000000", "0.000500"),
            ("C", "3.000000", "-0.001000", "7.000000", "-0.001000", "10", "0.000500"),
            ("L", "10.000000", "0.000000"), ("L", "0.000000", "0.000000"), ("Z",))
    assert certify_native_region_topology(path).status == "INVALID"


def test_native_z_adds_the_actual_implicit_closing_edge_and_zero_lines_are_noops():
    triangle = (("M", 0, 0), ("L", 0, 0), ("L", 2, 0), ("L", 1, 1), ("Z",))
    assert certify_native_region_topology(triangle).status == "VALID"
    explicit = triangle[:-1]+(("L", 0, 0), ("Z",))
    assert certify_native_region_topology(explicit).status == "VALID"


@pytest.mark.parametrize("commands", [
    (("M", 1, 0), ("A", 1, 2, 0, 0, 1, 0, 1), ("Z",)),
    (("M", 1, 0), ("A", 1, 1, 0, 1, 1, 0, 1), ("Z",)),
    (("M", 0, 0), ("l", 1, 0), ("Z",)),
    (("M", 0, 0), ("L", 1, 0)),
    (("M", 0, 0), ("M", 1, 1), ("Z",)),
    (("M", 0, 0), ("L", "NaN", 1), ("Z",)),
])
def test_unsupported_or_unclosed_native_path_is_explicitly_unresolved(commands):
    assert certify_native_region_topology(commands).status == "UNRESOLVED"


def test_raw_native_budget_is_explicit_and_never_falls_back_to_source_geometry():
    path = native_rectangle(0, 0, 10, 10)
    result = certify_native_region_topology(path, max_nodes=0)
    assert result.status == "UNRESOLVED" and "budget" in result.reason


def separation(first, second, first_holes=(), second_holes=(), **limits):
    return certify_native_region_separation(first, first_holes, second, second_holes, **limits)


def test_native_material_regions_disjoint_and_strict_containment_are_distinguished():
    outer = native_rectangle(0, 0, 10, 10)
    apart = native_rectangle(20, 20, 25, 25)
    inside = native_rectangle(2, 2, 4, 4)
    assert separation(outer, apart).status == "DISJOINT"
    result = separation(outer, inside)
    assert result.status == "OVERLAP"
    assert result.witness["method"] == "STRICT_MATERIAL_CONTAINMENT_WITH_DISJOINT_BOUNDARIES"
    assert separation(inside, outer).status == "OVERLAP"


def test_material_inside_other_regions_hole_is_disjoint_in_both_directions():
    outer = native_rectangle(0, 0, 10, 10)
    hole = native_rectangle(2, 2, 8, 8)
    floating = native_rectangle(3, 3, 7, 7)
    assert separation(outer, floating, first_holes=(hole,)).status == "DISJOINT"
    assert separation(floating, outer, second_holes=(hole,)).status == "DISJOINT"
    spanning_hole = native_rectangle(1, 1, 9, 9)
    assert separation(outer, spanning_hole, first_holes=(hole,)).status == "OVERLAP"


def test_transverse_crossing_proves_positive_material_area_not_only_boundary_intersection():
    horizontal = native_rectangle(-3, -1, 3, 1)
    vertical = native_rectangle(-1, -3, 1, 3)
    result = separation(horizontal, vertical)
    assert result.status == "OVERLAP"
    assert (result.witness.get("proper_interior_crossing")
            or result.witness["method"] == "CERTIFIED_STRICT_COMMON_INTERIOR_POINT")


@pytest.mark.parametrize("second", [native_rectangle(10, 0, 20, 10),
                                     native_rectangle(10, 10, 20, 20)])
def test_native_boundary_edge_or_corner_touch_is_not_called_positive_area_overlap(second):
    result = separation(native_rectangle(0, 0, 10, 10), second)
    assert result.status == "UNRESOLVED", result
    assert "positive area" in result.reason


def test_coincident_boundaries_need_an_actual_common_interior_witness_for_positive_area():
    outer = native_rectangle(0, 0, 10, 10)
    result = separation(outer, outer)
    assert result.status == "OVERLAP"
    assert result.witness["method"] == "CERTIFIED_STRICT_COMMON_INTERIOR_POINT"


def native_circle(x=0, y=0, radius=1):
    return (("M", x+radius, y),
            ("A", radius, radius, 0, 0, 1, x, y+radius),
            ("A", radius, radius, 0, 0, 1, x-radius, y),
            ("A", radius, radius, 0, 0, 1, x, y-radius),
            ("A", radius, radius, 0, 0, 1, x+radius, y), ("Z",))


def test_native_circle_region_separation_uses_interval_circle_geometry_and_hole_material():
    first, separate, crossing = native_circle(), native_circle(3, 0), native_circle(1, 0)
    assert separation(first, separate).status == "DISJOINT"
    assert separation(first, crossing).status == "OVERLAP"
    outer, hole = native_circle(radius=10), native_circle(radius=5)
    floating = native_circle(radius=1)
    assert separation(outer, floating, first_holes=(hole,)).status == "DISJOINT"


def test_native_separation_budget_and_invalid_input_block_without_area_claim():
    outer = native_rectangle(0, 0, 10, 10)
    assert separation(outer, outer, max_nodes=0).status == "UNRESOLVED"
    invalid = (("M", 0, 0), ("L", 10, 10), ("L", 0, 10), ("L", 10, 0), ("Z",))
    result = separation(outer, invalid)
    assert result.status == "UNRESOLVED" and "input material region" in result.reason


def test_exact_fraction_separation_does_not_turn_tiny_positive_gap_into_overlap():
    delta = Fraction(1, 10**40)
    first = native_rectangle(0, 0, 1, 1)
    apart = native_rectangle(1+delta, 0, 2, 1)
    result = separation(first, apart, max_nodes=2000)
    assert result.status in ("DISJOINT", "UNRESOLVED"), result


def test_actual_native_cubic_material_crossing_uses_area_proof_not_chord_rectangles():
    arch = (("M", 0, 0), ("C", 0, 8, 10, 8, 10, 0),
            ("L", 10, -5), ("L", 0, -5), ("Z",))
    across_top = native_rectangle(4, 4, 6, 8)
    result = separation(arch, across_top)
    assert result.status == "OVERLAP", result
