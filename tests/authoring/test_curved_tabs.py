"""Independent source, map, contact, and whole-phase expectations for C tabs."""

import math
from dataclasses import replace
from fractions import Fraction

import pytest

from archpapercraft.authoring.curve_area import native_region_area_bounds
from archpapercraft.authoring.curved_tabs import (
    Cap,
    CircularHole,
    Limits,
    Rim,
    _rotation,
    certify_tabs,
    evaluate_tab,
    periodic_tabs,
)


def fixture(radius=10, slope=0, base=2, depth=2, relief=Fraction(1, 2)):
    rim = Rim(radius, slope, "rim", "body")
    cap = Cap(radius, "cap")
    tabs = periodic_tabs(rim, cap.part_id, count=12, nominal_base_mm=base,
                         depth_mm=depth, relief_mm=relief)
    limits = Limits(Fraction(8, 100), Fraction(1, 4), 1, Fraction(1, 5), Fraction(1, 100))
    return rim, tabs, cap, limits


def slot_zero_hole(radius):
    angle = math.pi/12
    return CircularHole(9*math.cos(angle), 9*math.sin(angle), radius)


@pytest.mark.parametrize("radius,slope", [(10, 0), (10, Fraction(-1, 3)), (20, Fraction(1, 3)),
                                           (10, Fraction(1, 10**12)), (10, Fraction(-1, 10**12))])
def test_positive_twelve_tabs_cylinder_cone_and_both_limits(radius, slope):
    report = certify_tabs(*fixture(radius, slope))
    assert report["status"] == "CERTIFIED_APPROXIMATE", report["problems"]
    assert len(report["checked_ids"]) == 12
    assert len(report["pairs"]) == 66
    assert report["fold_scope"] == "ALL_INDEPENDENT_TAB_PHASES_FROM_GENERATOR_TO_INWARD_CAP"
    assert report["physical_status"] == "P3_NOT_RUN_NO_ELASTICITY_OR_ADHESIVE_CLAIM"
    for tab in report["tabs"]:
        assert tab["actual_glue_area_bounds_mm2"][0] >= 1
        assert tab["actual_glue_area_bounds_mm2"][0] == tab["actual_glue_area_bounds_mm2"][1]
        assert tab["body_distance_lower_mm"] > Fraction(21, 100)


def test_cylinder_analytic_oracles_and_one_percent_narrow_option():
    report = certify_tabs(*fixture())
    row = report["tabs"][0]
    assert row["actual_glue_area_bounds_mm2"] == (Fraction(9, 8), Fraction(9, 8))
    assert row["source_arc_length_bounds_mm"] == (2, 2)
    assert row["flat_native_loop"] == (("M", -1, 0), ("L", 1, 0), ("L", 0, 2), ("Z",))
    args = fixture(base=Fraction(1, 4), depth=9)
    strict = replace(args[-1], max_differential_deformation=Fraction(1, 100))
    narrow = certify_tabs(*args[:-1], strict)
    assert narrow["status"] == "CERTIFIED_APPROXIMATE", narrow["problems"]
    row = narrow["tabs"][0]
    assert row["actual_glue_area_bounds_mm2"] == (Fraction(289, 288), Fraction(289, 288))
    assert row["differential_deformation_bound"] < Fraction(1, 100)
    assert row["jacobian_perturbation_bound"] > Fraction(1, 100)


@pytest.mark.parametrize("radius,slope", [(10, 0), (10, Fraction(-1, 3)), (20, Fraction(1, 3)),
                                           (10, Fraction(1, 10**20)), (10, Fraction(-1, 10**20))])
def test_one_percent_principal_strain_option_with_one_square_mm_minimum(radius, slope):
    rim, tabs, cap, limits = fixture(radius, slope, base=Fraction(6, 25), depth=Fraction(19, 2),
                                    relief=Fraction(3, 5))
    limits = replace(limits, max_differential_deformation=Fraction(1, 100),
                     max_position_mm=Fraction(1, 100))
    result = certify_tabs(rim, tabs, cap, limits)
    assert result["status"] == "CERTIFIED_APPROXIMATE", result["problems"]
    for row in result["tabs"]:
        assert row["differential_deformation_bound"] < Fraction(1, 100)
        assert row["actual_glue_area_bounds_mm2"][0] >= 1
        assert row["collar_injectivity_margin"] > 0
    assert len(result["pairs"]) == result["expected_active_pair_count"] == 66
    assert all(p["whole_phase_distance_lower_mm"] > Fraction(21, 100) for p in result["pairs"])


@pytest.mark.parametrize("slope", [Fraction(1, 3), Fraction(-1, 3),
                                    Fraction(1, 10**20), Fraction(-1, 10**20)])
def test_cone_native_arc_has_exact_source_circle_and_no_fake_chord(slope):
    rim, tabs, cap, limits = fixture(slope=slope)
    row = certify_tabs(rim, tabs[:1], cap, limits)["tabs"][0]
    x, y = row["xe"], row["fe"]
    signed_radius = Fraction(10)/slope
    assert x*x+(y+signed_radius)**2 == signed_radius**2
    assert row["shared_base_commands"][1][0] == "A"
    assert all(command[0] != "A" for command in row["cut_side_commands"])
    assert row["shared_base_commands"][1][5] == int(slope < 0)
    lo, hi = row["source_arc_length_bounds_mm"]
    # atan(q)<q for q>0: actual base differs honestly from the nominal2mm.
    assert 0 < lo <= hi <= 2
    assert lo < 2  # outward rounding may include2 in the near-cylinder limit.
    area = native_region_area_bounds([row["flat_native_loop"]])
    assert area[0] > 0


@pytest.mark.parametrize("slope", [0, Fraction(1, 3), Fraction(-1, 3)])
def test_true_base_contiguity_and_relief_continuity_in_arbitrary_phases(slope):
    rim, tabs, cap, limits = fixture(slope=slope)
    tab = tabs[0]
    row = certify_tabs(rim, tabs[:1], cap, limits)["tabs"][0]
    k = float(slope)
    theta0 = math.pi/12
    for fraction in (-1, -.4, 0, .6, 1):
        x = fraction*float(row["xe"])
        base_y = -k*x*x/10/(1+math.sqrt(1-(k*x/10)**2)) if k else 0
        theta = math.asin(k*x/10)/k if k else x/10
        for phase in (0, .137, .499, .871, 1):
            actual = evaluate_tab(rim, tab, x, base_y, phase)
            assert actual == pytest.approx((10*math.cos(theta+theta0),
                                            10*math.sin(theta+theta0), 0), abs=1e-12)
            actual = evaluate_tab(rim, tab, x, Fraction(1, 2), phase)
            h = math.sqrt(1-k*k)
            phi = phase*math.atan2(h, -k)
            radial = 10+.5*(k*math.cos(phi)-h*math.sin(phi))
            assert actual == pytest.approx((radial*math.cos(theta0)-x*math.sin(theta0),
                                            radial*math.sin(theta0)+x*math.cos(theta0),
                                            .5*(h*math.cos(phi)+k*math.sin(phi))), abs=1e-12)


def test_off_custom_tip_and_ids_preserve_provenance_and_periodic_boundary():
    rim, tabs, cap, limits = fixture()
    changed = list(tabs)
    changed[0] = replace(changed[0], enabled=False)
    changed[5] = replace(changed[5], tip_offset_mm=Fraction(1, 4))
    report = certify_tabs(rim, changed, cap, limits)
    assert report["status"] == "CERTIFIED_APPROXIMATE", report["problems"]
    assert report["expected_ids"] == tuple(t.tab_id for t in tabs)
    assert tabs[0].tab_id not in report["checked_ids"]
    assert len(report["pairs"]) == 55
    assert report["tabs"][5]["glue_triangle_local"][-1] == (8, Fraction(1, 4))
    regenerated = periodic_tabs(rim, "cap", count=12, nominal_base_mm=1, depth_mm=3, relief_mm=1)
    assert tuple(t.tab_id for t in regenerated) == tuple(t.tab_id for t in tabs)
    wrapped = [replace(t, center_turn=Fraction(t.center_turn)+2) for t in changed]
    assert certify_tabs(rim, wrapped, cap, limits)["status"] == report["status"]


def test_actual_receiver_hole_cannot_be_replaced_by_full_nominal_disk():
    rim, tabs, cap, limits = fixture()
    # Entire slot0 glue triangle lies inside this local cap hole.
    cap = replace(cap, holes=(slot_zero_hole(2),))
    report = certify_tabs(rim, tabs[:1], cap, limits)
    assert report["status"] == "INVALID"
    assert report["tabs"][0]["actual_glue_area_bounds_mm2"] == (0, 0)
    assert report["tabs"][0]["proven_uncovered_glue_area_mm2"] == Fraction(9, 8)


def test_partial_hole_contact_bounds_and_min_area_do_not_invent_coverage():
    rim, tabs, cap, limits = fixture()
    cap = replace(cap, holes=(slot_zero_hole(Fraction(1, 4)),))
    report = certify_tabs(rim, tabs[:1], cap, limits, max_cells=20000)
    assert report["status"] == "INVALID"
    low, high = report["tabs"][0]["actual_glue_area_bounds_mm2"]
    # At least a small central hole is absent; it is not all1.125mm² glue.
    assert 0 < low <= high < Fraction(9, 8)
    assert report["tabs"][0]["proven_uncovered_glue_area_mm2"] > 0


def test_cap_hole_far_from_glue_and_inside_void_has_no_false_loss():
    rim, tabs, cap, limits = fixture()
    cap = replace(cap, holes=(CircularHole(0, 0, 5),))
    assert certify_tabs(rim, tabs, cap, limits)["status"] == "CERTIFIED_APPROXIMATE"
    shifted = replace(cap, plane_offset_mm=Fraction(1, 1000))
    assert certify_tabs(rim, tabs, shifted, limits)["status"] == "INVALID"


def test_budget_exhaustion_and_strict_budgets_never_claim_clear():
    args = fixture()
    assert certify_tabs(*args, max_cells=0)["status"] == "UNRESOLVED"
    assert certify_tabs(*args, max_pairs=0)["status"] == "UNRESOLVED"
    strict = replace(args[-1], max_position_mm=Fraction(1, 100000))
    assert certify_tabs(*args[:-1], strict)["status"] == "UNRESOLVED"
    strict = replace(args[-1], max_differential_deformation=Fraction(1, 100000))
    assert certify_tabs(*args[:-1], strict)["status"] == "UNRESOLVED"
    minimum = replace(args[-1], min_glue_area_mm2=2)
    assert certify_tabs(*args[:-1], minimum)["status"] == "INVALID"


def test_certain_overlap_survives_unknown_material_and_other_uncertainty():
    rim, tabs, cap, limits = fixture()
    tabs = (tabs[0], replace(tabs[1], center_turn=tabs[0].center_turn),
            replace(tabs[2], depth_mm=9, relief_mm=Fraction(1, 1000)))
    report = certify_tabs(rim, tabs, cap, replace(limits, thickness_mm=None))
    assert report["status"] == "INVALID"
    assert any("positive-area" in p[2] for p in report["problems"])
    assert any(p[0] == "UNVERIFIED" for p in report["problems"])


@pytest.mark.parametrize("change", [{"owner_id": "wrong"}, {"receiver_id": "wrong"},
                                     {"contact_side": "front"}, {"depth_mm": 11},
                                     {"relief_mm": 0}, {"nominal_base_mm": -1},
                                     {"tip_offset_mm": 2}])
def test_invalid_geometry_owner_receiver_and_contact_side_are_concrete_negatives(change):
    rim, tabs, cap, limits = fixture()
    assert certify_tabs(rim, (replace(tabs[0], **change),), cap, limits)["status"] == "INVALID"


def test_unknown_thickness_and_failed_whole_angle_bounds_are_not_clear():
    rim, tabs, cap, limits = fixture()
    report = certify_tabs(rim, tabs, cap, replace(limits, thickness_mm=None))
    assert report["status"] == "UNVERIFIED"
    assert certify_tabs(rim, tabs, cap, replace(limits, clearance_mm=1))["status"] == "UNRESOLVED"


def test_source_gap_generation_validation_and_paper_seam_crossing():
    rim, tabs, cap, limits = fixture()
    generated = periodic_tabs(rim, "cap", count=12, gap_mm=Fraction(16, 5), depth_mm=2,
                              relief_mm=Fraction(1, 2))
    result = certify_tabs(rim, generated, cap, limits)
    assert result["status"] == "CERTIFIED_APPROXIMATE", result["problems"]
    assert all(p["source_gap_bounds_mm"][0] >= Fraction(16, 5) for p in result["pairs"])
    changed = (replace(tabs[0], center_turn=0),)
    result = certify_tabs(rim, changed, cap, limits)
    assert result["status"] == "INVALID"
    assert any("paper seam" in p[2] for p in result["problems"])


def test_unknown_barrier_does_not_turn_into_clear_or_erase_certain_hole_failure():
    rim, tabs, cap, limits = fixture()
    result = certify_tabs(rim, tabs, cap, limits, unresolved_obstacle_ids=("beam",))
    assert result["status"] == "UNRESOLVED"
    assert result["unresolved_obstacle_ids"] == ("beam",)
    cap = replace(cap, holes=(slot_zero_hole(2),))
    result = certify_tabs(rim, tabs[:1], cap, limits, unresolved_obstacle_ids=("beam",))
    assert result["status"] == "INVALID"


@pytest.mark.parametrize("turn,sine,cosine", [(Fraction(0), 0, 1), (Fraction(1, 4), 1, 0),
                                               (Fraction(1, 2), 0, -1), (Fraction(3, 4), -1, 0)])
def test_outward_rotations_enclose_exact_quadrant_oracles(turn, sine, cosine):
    s, c = _rotation(turn)
    assert s[0] <= sine <= s[1]
    assert c[0] <= cosine <= c[1]


def test_independent_cylinder_metric_oracle_is_inside_principal_strain_bound():
    # Analytic derivatives of the cylinder collar, independently of the helper's
    # general cone inequalities. These checks exercise interior φ, x, and y;
    # the certificate itself remains the whole-domain rational inequalities.
    rim, tabs, cap, limits = fixture(base=Fraction(6, 25), depth=Fraction(19, 2),
                                    relief=Fraction(3, 5))
    row = certify_tabs(rim, tabs[:1], cap, limits)["tabs"][0]
    bound = float(row["differential_deformation_bound"])
    for x in (-.119, -.05, .01, .119):
        theta = x/10
        defect = (10*(math.cos(theta)-1), 10*math.sin(theta)-x, 0)
        derivative = (-math.sin(theta), math.cos(theta)-1, 0)
        for y in (.001, .2, .599):
            alpha = 1-y/.6
            jx = (alpha*derivative[0], 1+alpha*derivative[1], 0)
            for phi in (.001, .271, .783, 1.397, math.pi/2):
                jy = (-math.sin(phi)-defect[0]/.6,
                      -defect[1]/.6, math.cos(phi))
                aa = sum(v*v for v in jx)
                cc = sum(v*v for v in jy)
                bb = sum(a*b for a, b in zip(jx, jy))
                discriminant = math.hypot(aa-cc, 2*bb)
                minimum = math.sqrt((aa+cc-discriminant)/2)
                maximum = math.sqrt((aa+cc+discriminant)/2)
                assert max(1-minimum, maximum-1) <= bound


def test_fold_body_bound_has_independent_mid_motion_oracles():
    rim, tabs, cap, limits = fixture()
    row = certify_tabs(rim, tabs[:1], cap, limits)["tabs"][0]
    lower = float(row["body_distance_lower_mm"])
    # Exact distance to the open cylinder at z<=0: for z>=0 it is the
    # Euclidean distance to its rim circle. Endpoints alone cannot establish it.
    for phase in (.071, .211, .521, .873):
        for x in (-.7, 0, .7):
            point = evaluate_tab(rim, tabs[0], x, .51, phase)
            distance = math.hypot(math.hypot(point[0], point[1])-10, point[2])
            assert distance >= lower


def test_partial_hole_budget_never_returns_full_coverage():
    rim, tabs, cap, limits = fixture()
    cap = replace(cap, holes=(slot_zero_hole(Fraction(1, 4)),))
    result = certify_tabs(rim, tabs[:1], cap, limits, max_cells=1)
    assert result["status"] == "UNRESOLVED"
    assert result["tabs"][0]["actual_glue_area_bounds_mm2"] == (0, Fraction(9, 8))


def test_actual_source_overlap_and_requested_gap_fail_independently_of_endpoint_tests():
    rim, tabs, cap, limits = fixture()
    first = tabs[0]
    second = replace(tabs[1], center_turn=Fraction(first.center_turn)+Fraction(1, 1000))
    result = certify_tabs(rim, (first, second), cap, limits)
    assert result["status"] == "INVALID"
    assert any("Source gap" in problem[2] for problem in result["problems"])


def test_binary_float_slope_has_exact_native_base_and_compact_public_bounds():
    rim, tabs, cap, limits = fixture(slope=-1/3)
    result = certify_tabs(rim, tabs[:1], cap, limits)
    assert result["status"] == "CERTIFIED_APPROXIMATE"
    row = result["tabs"][0]
    assert row["slope"] == Fraction(-1/3)
    signed_radius = Fraction(10)/Fraction(-1/3)
    assert row["xe"]**2+(row["fe"]+signed_radius)**2 == signed_radius**2
    for key in ("position_bound_mm", "differential_deformation_bound",
                "body_distance_lower_mm", "angular_sector_half_bound"):
        assert len(str(row[key])) < 200


@pytest.mark.parametrize("change", [{"radius_mm": 0}, {"radial_slope": 1},
                                     {"radial_slope": float("nan")}])
def test_invalid_rim_is_rejected_without_float_nan_pass(change):
    rim, tabs, cap, limits = fixture()
    assert certify_tabs(replace(rim, **change), tabs[:1], cap, limits)["status"] == "INVALID"
