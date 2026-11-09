"""Independent analytic curves, global budgets and truthful loft-fit scopes."""

import copy
import json
import math
from fractions import Fraction

import pytest

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_curves import fit_native_loft_boundaries
from archpapercraft.authoring.loft_geometry import (
    LoftCorrespondence,
    LoftProfile,
    flatten_loft,
)


def circle_report(*, second_radius=30, depth=30, reverse=False):
    profiles = []
    for radius, z, identity in ((20, 0, "a"), (second_radius, depth, "b")):
        profiles.append(LoftProfile((Curve((radius, 0), (-radius, 0), "arc",
                                           {"center": (0, 0), "sweep_deg": 180}, identity),),
                                    origin=(0, 0, z), profile_id="profile-"+identity))
    interval = (1, 0) if reverse else (0, 1)
    return flatten_loft(*profiles, [LoftCorrespondence("a", "b", interval, interval)])


def point_on_native(boundary, u):
    for segment in boundary["segments"]:
        a, b = segment["source"]["loft_parameter_interval"]
        if a <= u <= b:
            t = (u-a)/(b-a)
            p, q = segment["start"], segment["end"]
            if segment["kind"] == "line":
                return [(1-t)*x+t*y for x, y in zip(p, q)]
            c1, c2 = segment["data"]["control1"], segment["data"]["control2"]
            return [(1-t)**3*x+3*(1-t)**2*t*y+3*(1-t)*t*t*z+t**3*w
                    for x, y, z, w in zip(p, c1, c2, q)]
    raise AssertionError("Test did not find the explicit source interval")


def native_length(boundary):
    """Independent composite Simpson integration, used only as a test oracle."""
    total = 0
    for segment in boundary["segments"]:
        a, b = segment["start"], segment["end"]
        if segment["kind"] == "line":
            total += math.dist(a, b)
            continue
        c1, c2 = segment["data"]["control1"], segment["data"]["control2"]
        values = []
        for i in range(9):
            t = i/8
            values.append(math.hypot(*(3*((1-t)**2*(y-x)+2*(1-t)*t*(z-y)+t*t*(w-z))
                                       for x, y, z, w in zip(a, c1, c2, b))))
        total += (values[0]+values[-1]+4*sum(values[1:-1:2])+2*sum(values[2:-1:2]))/24
    return total


def synthetic_report(*, patches=1, parameters=(0, 0.3, 0.7, 1)):
    """Trusted analytic input to isolate fitter math from the source solver.

    Every boundary is an offset of (u,u²)*.01. Linear interpolation error is
    <=.0004, and total chord-length deficit over these few arcs <.01 per chain.
    This fixture does not assert that a sampled arbitrary surface is a loft.
    """
    rows = []
    for index in range(patches):
        xs = [index*.02+t*.01 for t in parameters]
        first = [[x, t*t*.01] for x, t in zip(xs, parameters)]
        second = [[x, y+.02] for x, y in first]
        rows.append({"parameters": list(parameters),
                     "source_parameters": [[t, t] for t in parameters],
                     "first_profile_id": "first", "second_profile_id": "second",
                     "first_segment_id": "a-"+str(index), "second_segment_id": "b-"+str(index),
                     "first_parameter_interval": [0, 1], "second_parameter_interval": [0, 1],
                     "flat_first_paper_mm": first, "flat_second_paper_mm": second,
                     "join_before_kind": "EXPLICIT_SEAM" if index == 0 else "FOLD_CREASE"})
    return {"status": "EXACT", "family": "POSITIVE_HOMOTHETIC_CONE", "patches": rows,
            "representation_error_bound_paper_mm": .001,
            "boundary_length_error_bound_paper_mm": .01,
            "regularity_lower_bound_paper_mm2": 1,
            "proof_scope": "DECLARED_REGULAR_PARAMETRIC_FAMILY_AND_BOUNDED_REPRESENTATION",
            "feature_id": "authored-feature", "coverage": {"scope": "test-explicit-intervals"}}


def test_circular_cone_native_curves_match_analytic_development_and_lengths():
    report = circle_report()
    before = copy.deepcopy(report)
    fit = fit_native_loft_boundaries(report)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY", fit.get("message")
    patch = fit["patches"][0]
    radius = math.sqrt(20**2+60**2)
    for side, factor in (("first", 1), ("second", 1.5)):
        boundary = patch[side]
        assert boundary["representation"] == "NATIVE_HERMITE_CUBICS"
        for u in (0, .001, .137, .333, .501, .731, .999, 1):
            angle = math.pi*20/radius*u
            exact = [radius*factor*math.cos(angle), radius*factor*math.sin(angle)]
            assert math.dist(point_on_native(boundary, u), exact) <= (
                fit["position_error_bound_paper_mm"])
        assert abs(native_length(boundary)-20*factor*math.pi) <= (
            fit["boundary_length_error_bound_paper_mm"])
        assert any(abs((s["data"]["control1"][0]-s["start"][0]) *
                       (s["end"][1]-s["start"][1]) -
                       (s["data"]["control1"][1]-s["start"][1]) *
                       (s["end"][0]-s["start"][0])) > 1e-12 for s in boundary["segments"])
    assert fit["source_coverage"] == report["coverage"] and report == before
    assert fit["physical_build"] == "NOT_VERIFIED"
    assert fit["serialized_output"] == "NOT_VERIFIED"
    json.dumps(fit, allow_nan=False)


def test_planar_arc_band_native_length_bound_covers_both_actual_semicircles():
    fit = fit_native_loft_boundaries(circle_report(depth=0))
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    for side, radius in (("first", 20), ("second", 30)):
        measured = native_length(fit["patches"][0][side])
        assert abs(measured-math.pi*radius) <= fit["boundary_length_error_bound_paper_mm"]
    assert fit["length_scope"].endswith("EXCLUDES_CLOSING_RULINGS")
    assert fit["patches"][0]["closing_ruling_length_proof"] == "CALLER_VALIDATES_INDEPENDENTLY"


def test_normal_curved_extrusion_keeps_native_lines_and_analytic_arclength():
    report = circle_report(second_radius=20)
    fit = fit_native_loft_boundaries(report)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    patch = fit["patches"][0]
    for side, y in (("first", 0), ("second", 30)):
        assert patch[side]["representation"] == "NATIVE_LINES"
        assert {s["kind"] for s in patch[side]["segments"]} == {"line"}
        for u in (.017, .159, .371, .583, .971):
            assert math.dist(point_on_native(patch[side], u), [20*math.pi*u, y]) <= (
                fit["position_error_bound_paper_mm"])
    assert fit["line_interpolant_deviation_bound_paper_mm"] == 0


@pytest.mark.parametrize("reverse", [False, True])
def test_l01_straight_collinear_cubic_retains_nonlinear_same_u_mapping(reverse):
    curve = Curve((0, 0), (6, 0), "cubic", {"control1": (1, 0), "control2": (3, 0)}, "a")
    other = Curve(curve.start, curve.end, curve.kind, dict(curve.data), "b")
    a, b = LoftProfile((curve,), profile_id="first"), LoftProfile(
        (other,), origin=(0, 0, 10), profile_id="second")
    interval = (1, 0) if reverse else (0, 1)
    report = flatten_loft(a, b, [LoftCorrespondence("a", "b", interval, interval)])
    fit = fit_native_loft_boundaries(report)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    boundary = fit["patches"][0]["first"]
    assert len(boundary["segments"]) > 1 and boundary["representation"] == "NATIVE_LINES"
    for u in (.031, .173, .333, .5, .731, .997):
        source = 1-u if reverse else u
        x = 3*source+3*source**2
        exact = [6-x if reverse else x, 0]
        assert math.dist(point_on_native(boundary, u), exact) <= (
            fit["position_error_bound_paper_mm"])
    assert boundary["segments"][0]["source"]["parameter_interval"][0] == interval[0]


def test_returned_binary_controls_have_explicit_actual_derivative_jump_bound():
    fit = fit_native_loft_boundaries(synthetic_report(), position_budget_mm=.1, length_budget_mm=.1)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    boundary = fit["patches"][0]["first"]
    observed = []
    for before, after in zip(boundary["segments"], boundary["segments"][1:]):
        ta, tb = map(Fraction, before["source"]["loft_parameter_interval"])
        tc, td = map(Fraction, after["source"]["loft_parameter_interval"])
        differences = []
        for axis in range(2):
            left = 3*(Fraction(before["end"][axis]) -
                      Fraction(before["data"]["control2"][axis]))/(tb-ta)
            right = 3*(Fraction(after["data"]["control1"][axis]) -
                       Fraction(after["start"][axis]))/(td-tc)
            differences.append(left-right)
        observed.append(math.hypot(*differences))
    assert 0 < max(observed) <= boundary["binary_control_derivative_jump_bound_paper_mm_per_u"]
    assert boundary["exact_c1_of_binary_controls"] is False
    assert boundary["ideal_continuity"] == "C1_SHARED_QUADRATIC_DERIVATIVE_WITHIN_SOURCE_PATCH"


def test_global_length_budget_sums_all_intervals_and_patches_not_local_max():
    report = synthetic_report(patches=3)
    initial = fit_native_loft_boundaries(report, position_budget_mm=.1, length_budget_mm=.1)
    assert initial["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    source = report["boundary_length_error_bound_paper_mm"]
    global_extra = initial["native_boundary_length_excess_bound_paper_mm"]["first"]
    local_extra = max(s["length_excess_bound_paper_mm"] for p in initial["patches"]
                      for s in p["first"]["segments"])
    assert global_extra > 3*local_extra
    budget = source+(global_extra+local_extra)/2
    refused = fit_native_loft_boundaries(report, position_budget_mm=.1, length_budget_mm=budget)
    assert refused["status"] == "UNRESOLVED"
    assert refused["boundary_length_error_bound_paper_mm"] > budget
    assert refused["next_action"] == "REFINE_SOURCE_SOLVER_AND_REFIT_WITHOUT_HANDLE_CLAMPING"
    assert initial["both_profile_boundaries_length_error_bound_paper_mm"] >= 2*source+2*global_extra


def test_too_small_position_budget_does_not_clamp_or_rewrite_handles():
    report = synthetic_report()
    before = copy.deepcopy(report)
    fit = fit_native_loft_boundaries(report, position_budget_mm=.0011, length_budget_mm=.1)
    assert fit["status"] == "UNRESOLVED"
    assert fit["position_error_bound_paper_mm"] > .0011
    assert fit["line_interpolant_deviation_bound_paper_mm"] > .0001
    assert report == before


def test_reverse_loop_swaps_controls_and_source_intervals_and_keeps_closing_rulings():
    report = synthetic_report()
    report["patches"][0]["second_parameter_interval"] = [1, 0]
    for row in report["patches"][0]["source_parameters"]:
        row[1] = 1-row[1]
    fit = fit_native_loft_boundaries(report, position_budget_mm=.1, length_budget_mm=.1)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    patch = fit["patches"][0]
    n = len(patch["first"]["segments"])
    original = patch["second"]["segments"][-1]
    reversed_segment = patch["closed_boundary_segments"][n+1]
    assert reversed_segment["start"] == original["end"]
    assert reversed_segment["data"]["control1"] == original["data"]["control2"]
    assert reversed_segment["source"]["parameter_interval"] == list(reversed(
        original["source"]["parameter_interval"]))
    assert reversed_segment["source"]["direction"] == -original["source"]["direction"]
    assert reversed_segment["source"]["feature_id"] == "authored-feature"
    assert patch["closed_boundary_commands"][0][0] == "M"
    assert patch["closed_boundary_commands"][-1] == ["Z"]
    for a, b in zip(patch["closed_boundary_segments"], patch["closed_boundary_segments"][1:]):
        assert a["end"] == b["start"]
    assert patch["closed_boundary_segments"][-1]["end"] == (
        patch["closed_boundary_segments"][0]["start"])
    assert patch["closed_boundary_topology"] == "NOT_VERIFIED"
    ruling = patch["closed_boundary_segments"][n]
    assert ruling["source"]["first_source_parameter"] == 1
    assert ruling["source"]["second_source_parameter"] == 0
    assert ruling["source"]["feature_id"] == "authored-feature"


@pytest.mark.parametrize("budget", [0, -1, True, float("nan"), float("inf")])
@pytest.mark.parametrize("name", ["position_budget_mm", "length_budget_mm"])
def test_invalid_budgets_never_create_certified_empty_output(name, budget):
    assert fit_native_loft_boundaries(synthetic_report(), **{name: budget})["status"] == (
        "UNRESOLVED")


@pytest.mark.parametrize("damage", ["parameters", "source", "position", "status", "nodes",
                                    "regularity"])
def test_malformed_or_unproven_source_report_is_refused(damage):
    report = synthetic_report()
    if damage == "parameters":
        report["patches"][0]["parameters"][1] = 0
    elif damage == "source":
        report["patches"][0]["source_parameters"][1][0] = .4
    elif damage == "position":
        report["representation_error_bound_paper_mm"] = -1
    elif damage == "status":
        report["status"] = "UNRESOLVED"
    elif damage == "nodes":
        report["patches"][0]["flat_first_paper_mm"].pop()
    else:
        report["regularity_lower_bound_paper_mm2"] = 0
    assert fit_native_loft_boundaries(report)["status"] == "UNRESOLVED"


def test_source_corner_is_not_smoothed_between_patches():
    report = synthetic_report(patches=2)
    first_end = report["patches"][0]["flat_first_paper_mm"][-1]
    second_end = report["patches"][0]["flat_second_paper_mm"][-1]
    for side, start in (("first", first_end), ("second", second_end)):
        report["patches"][1]["flat_"+side+"_paper_mm"] = [
            [start[0]-t*t*.01, start[1]+t*.01] for t in report["patches"][1]["parameters"]]
    fit = fit_native_loft_boundaries(report, position_budget_mm=.1, length_budget_mm=.1)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    first, second = fit["patches"]
    a, b = first["first"]["segments"][-1], second["first"]["segments"][0]
    assert a["end"] == b["start"] == first_end
    left = [x-y for x, y in zip(a["end"], a["data"]["control2"])]
    right = [x-y for x, y in zip(b["data"]["control1"], b["start"])]
    assert abs(left[0]*right[1]-left[1]*right[0]) > 1e-9
    assert second["join_before_kind"] == "FOLD_CREASE"
    assert second["source_patch_boundary_policy"] == "NO_CROSS_PATCH_SMOOTHING"


def test_segment_and_reserve_budgets_are_explicit_not_silent_truncation():
    report = synthetic_report()
    assert fit_native_loft_boundaries(report, max_segments=2)["status"] == "UNRESOLVED"
    assert fit_native_loft_boundaries(report, rounding_reserve_mm=-1)["status"] == "UNRESOLVED"


def test_actual_gothic_cone_keeps_pointed_source_corner_and_native_straight_base():
    profiles = []
    for width, height, depth, name in ((20, 30, 0, "a"), (24, 36, 10, "b")):
        center = (height*height-width*width)/(2*width)
        angle = math.degrees(math.atan2(height, -center))-180
        curves = (
            Curve((-width, 0), (0, height), "arc",
                  {"center": (center, 0), "sweep_deg": angle}, name+"-left"),
            Curve((0, height), (width, 0), "arc",
                  {"center": (-center, 0), "sweep_deg": angle}, name+"-right"),
            Curve((width, 0), (-width, 0), segment_id=name+"-bottom"))
        profiles.append(LoftProfile(curves, origin=(0, 0, depth), profile_id=name, closed=True))
    refs = [LoftCorrespondence(a.segment_id, b.segment_id)
            for a, b in zip(profiles[0].curves, profiles[1].curves)]
    report = flatten_loft(*profiles, refs)
    fit = fit_native_loft_boundaries(report)
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY", fit.get("message")
    before, after, base = fit["patches"]
    assert after["join_before_kind"] == "FOLD_CREASE"
    for side in ("first", "second"):
        a = before[side]["segments"][-1]
        b = after[side]["segments"][0]
        assert math.dist(a["end"], b["start"]) < 1e-10
        assert a["end"] == report["patches"][0]["flat_"+side+"_paper_mm"][-1]
        incoming = [x-y for x, y in zip(a["end"], a["data"]["control2"])]
        outgoing = [x-y for x, y in zip(b["data"]["control1"], b["start"])]
        assert abs(incoming[0]*outgoing[1]-incoming[1]*outgoing[0]) > 1e-9
        assert base[side]["representation"] == "NATIVE_LINES"
        assert all(s["kind"] == "line" for s in base[side]["segments"])


def test_nonuniform_neighbor_quadratics_produce_real_quadratic_curve_not_chord_only_cubics():
    report = synthetic_report(parameters=(0, .1, .6, 1))
    fit = fit_native_loft_boundaries(report, position_budget_mm=.1, length_budget_mm=.1)
    boundary = fit["patches"][0]["first"]
    assert fit["status"] == "CERTIFIED_REPRESENTATION_ONLY"
    for u in (.013, .071, .173, .417, .731, .971):
        point = point_on_native(boundary, u)
        assert math.dist(point, [.01*u, .01*u*u]) < 1e-16
    for segment in boundary["segments"]:
        a, b = segment["source"]["loft_parameter_interval"]
        # The local quadratic sits strictly off its chord at the midpoint.
        midpoint = point_on_native(boundary, (a+b)/2)
        chord_midpoint = [(x+y)/2 for x, y in zip(segment["start"], segment["end"])]
        error = math.dist(midpoint, chord_midpoint)
        assert 0 < error <= segment["line_interpolant_deviation_bound_paper_mm"]


def test_source_endpoint_cannot_be_silently_rounded_before_the_control_error_proof():
    report = synthetic_report()
    report["patches"][0]["flat_first_paper_mm"][0][0] = Fraction(1, 3)
    assert fit_native_loft_boundaries(report)["status"] == "UNRESOLVED"
