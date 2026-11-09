"""Independent expectations for proved families, bounds and truthful rejection."""

import copy
import json
import math

import numpy as np
import pytest

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_geometry import (
    LoftCorrespondence,
    LoftProfile,
    flatten_loft,
    sample_loft,
)


def correspondence(a, b):
    return tuple(LoftCorrespondence(x.segment_id, y.segment_id) for x, y in zip(a.curves, b.curves))


def arc_profile(radius, *, height=0, prefix="a"):
    return LoftProfile(
        (
            Curve(
                (radius, 0),
                (-radius, 0),
                "arc",
                {"center": (0, 0), "sweep_deg": 180},
                prefix + "-arc",
            ),
        ),
        origin=(0, 0, height),
        profile_id=prefix,
    )


def gothic(width, height, *, depth=0, prefix="a"):
    center = (height * height - width * width) / (2 * width)
    angle = math.degrees(math.atan2(height, -center)) - 180
    curves = (
        Curve(
            (-width, 0),
            (0, height),
            "arc",
            {"center": (center, 0), "sweep_deg": angle},
            prefix + "-left",
        ),
        Curve(
            (0, height),
            (width, 0),
            "arc",
            {"center": (-center, 0), "sweep_deg": angle},
            prefix + "-right",
        ),
        Curve((width, 0), (-width, 0), segment_id=prefix + "-bottom"),
    )
    return LoftProfile(curves, origin=(0, 0, depth), profile_id=prefix)


def polygon_area(points):
    return abs(sum(x[0] * y[1] - y[0] * x[1] for x, y in zip(points, points[1:] + points[:1]))) / 2


def test_planar_semicircular_annulus_has_real_unfilled_inner_region_and_source_lineage():
    a, b = arc_profile(20), arc_profile(30, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT", result
    assert result["family"] == "CONCENTRIC_PLANAR_ARC_BAND"
    patch = result["patches"][0]
    assert patch["first_segment_id"] == "a-arc" and patch["second_segment_id"] == "b-arc"
    assert patch["first_parameter_interval"] == [0, 1]
    assert patch["source_parameters"][0] == [0, 0]
    assert patch["source_parameters"][-1] == [1, 1]
    expected = math.pi * (30**2 - 20**2) / 2
    # Area error <= perimeter * max boundary displacement plus its squared term.
    epsilon = result["representation_error_bound_paper_mm"]
    assert abs(polygon_area(patch["flat_boundary_paper_mm"]) - expected) < 200 * epsilon
    from shapely import Point, Polygon

    assert not Polygon(patch["flat_boundary_paper_mm"]).contains(Point(0, 5))
    assert Polygon(patch["flat_boundary_paper_mm"]).contains(Point(0, 25))


def test_normal_arc_extrusion_length_and_exact_rectangular_metric():
    a, b = arc_profile(10), arc_profile(10, height=30, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT", result
    assert result["family"] == "NORMAL_EXTRUSION"
    patch = result["patches"][0]
    width = patch["flat_first_paper_mm"][-1][0]
    assert abs(width - 10 * math.pi) <= result["boundary_length_error_bound_paper_mm"]
    assert patch["flat_second_paper_mm"][-1][1] == 30
    assert result["regularity_lower_bound_paper_mm2"] > 0
    assert result["physical_build"] == "NOT_VERIFIED"


def test_planar_arc_polyline_boundary_length_deficit_is_in_the_reported_bound():
    a, b = arc_profile(20), arc_profile(30, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT"
    patch = result["patches"][0]
    for points, radius in ((patch["flat_first_paper_mm"], 20), (patch["flat_second_paper_mm"], 30)):
        measured = math.fsum(math.dist(x, y) for x, y in zip(points, points[1:]))
        assert abs(math.pi * radius - measured) <= (result["boundary_length_error_bound_paper_mm"])


def test_cubic_extrusion_proves_regularity_and_total_arclength_enclosure():
    # C(t)=(30t,30t^2); exact length is 15sqrt(5)+7.5 asinh(2).
    curve = Curve((0, 0), (30, 30), "cubic", {"control1": (10, 0), "control2": (20, 10)}, "first")
    other = Curve(curve.start, curve.end, curve.kind, dict(curve.data), "second")
    a = LoftProfile((curve,), profile_id="a")
    b = LoftProfile((other,), origin=(0, 0, 12), profile_id="b")
    before = (curve.start, curve.end, dict(curve.data))
    result = flatten_loft(a, b, correspondence(a, b), tolerance_mm=0.005)
    assert result["status"] == "EXACT", result
    width = result["patches"][0]["flat_first_paper_mm"][-1][0]
    exact = 15 * math.sqrt(5) + 7.5 * math.asinh(2)
    assert abs(width - exact) <= result["boundary_length_error_bound_paper_mm"] < 0.005
    assert result["representation_error_bound_paper_mm"] < 0.005
    assert (curve.start, curve.end, dict(curve.data)) == before
    json.dumps(result, allow_nan=False)


def test_circular_cone_radials_and_developed_angle_are_analytic():
    a, b = arc_profile(20), arc_profile(30, height=30, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT", result
    # Apex is z=-60; r0=sqrt(20^2+60^2), r1=1.5*r0; sector angle=pi*20/r0.
    radius = math.hypot(20, 60)
    patch = result["patches"][0]
    assert np.allclose(np.linalg.norm(patch["flat_first_paper_mm"], axis=1), radius)
    assert np.allclose(np.linalg.norm(patch["flat_second_paper_mm"], axis=1), 1.5 * radius)
    assert (
        abs(result["total_developed_angle_rad"] - math.pi * 20 / radius)
        <= (result["angular_error_bound_rad"])
    )
    assert 0 < result["representation_error_bound_paper_mm"] <= 0.005
    assert result["boundary_length_error_bound_paper_mm"] <= 0.005


def test_gothic_b1_positive_independent_profiles_keep_pointed_corner_and_shared_ruling():
    a, b = gothic(20, 30), gothic(24, 36, depth=10, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT", result
    assert result["family"] == "POSITIVE_HOMOTHETIC_CONE"
    assert result["homothety_factor"] == pytest.approx(1.2)
    assert len(result["patches"]) == 3
    for before, after in zip(result["patches"], result["patches"][1:]):
        assert np.allclose(before["flat_first_paper_mm"][-1], after["flat_first_paper_mm"][0])
        assert np.allclose(before["flat_second_paper_mm"][-1], after["flat_second_paper_mm"][0])
        assert after["join_before_kind"] == "FOLD_CREASE"
    assert all(
        p["interior_tessellation_role"] == "DISPLAY_ONLY_NOT_FOLD" for p in result["patches"]
    )
    assert result["regularity_lower_bound_paper_mm2"] > 0


def test_gothic_metric_of_reported_map_matches_separate_world_chords_as_resolution_refines():
    a, b = gothic(20, 30), gothic(24, 36, depth=10, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b), scale=0.5)
    assert result["status"] == "EXACT", result
    for patch in result["patches"]:
        wa = np.asarray(patch["world_first_model_mm"]) * 0.5
        wb = np.asarray(patch["world_second_model_mm"]) * 0.5
        fa = np.asarray(patch["flat_first_paper_mm"])
        fb = np.asarray(patch["flat_second_paper_mm"])
        assert np.max(abs(np.linalg.norm(wa - wb, axis=1) - np.linalg.norm(fa - fb, axis=1))) < 1e-8
        world = (wa + wb) / 2
        flat = (fa + fb) / 2
        length_world = np.linalg.norm(np.diff(world, axis=0), axis=1).sum()
        length_flat = np.linalg.norm(np.diff(flat, axis=0), axis=1).sum()
        assert abs(length_world - length_flat) < result["boundary_length_error_bound_paper_mm"]


def test_nonhomothetic_independent_gothic_profile_does_not_gain_exact_by_sampling_zeros():
    a, b = gothic(20, 30), gothic(18, 25, depth=10, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "REJECTED", result
    assert result["family"] == "NONDEVELOPABLE"
    assert abs(result["witness"]["determinant"]) > result["witness"]["numerical_reserve"]


def test_180_degree_correspondence_singularity_is_analytic_not_a_missed_v_sample():
    a = LoftProfile((Curve((20, 0), (-20, 0), segment_id="a"),))
    b = LoftProfile((Curve((-28, 0), (28, 0), segment_id="b"),))
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "REJECTED"
    assert result["family"] == "SINGULAR_HOMOTHETY"
    assert result["witness"]["v"] == pytest.approx(5 / 12)


def test_cubic_stationary_tangent_and_insufficient_budget_remain_unresolved():
    curve = Curve((0, 0), (10, 10), "cubic", {"control1": (0, 0), "control2": (5, 5)}, "a")
    a = LoftProfile((curve,))
    b = LoftProfile(
        (Curve(curve.start, curve.end, curve.kind, dict(curve.data), "b"),), origin=(0, 0, 10)
    )
    assert flatten_loft(a, b, correspondence(a, b))["status"] == "UNRESOLVED"
    a, b = gothic(20, 30), gothic(24, 36, depth=10, prefix="b")
    assert flatten_loft(a, b, correspondence(a, b), max_segments=2)["status"] == "UNRESOLVED"


@pytest.mark.parametrize("value", [0, -1, True, float("nan")])
def test_bad_scale_is_not_an_exact_empty_surface(value):
    a, b = arc_profile(20), arc_profile(30, height=10, prefix="b")
    assert flatten_loft(a, b, correspondence(a, b), scale=value)["status"] == "UNRESOLVED"


def test_partial_correspondence_is_explicitly_preserved_as_unsupported_not_silently_extended():
    a, b = arc_profile(20), arc_profile(30, height=10, prefix="b")
    refs = [LoftCorrespondence("a-arc", "b-arc", (0.2, 0.8), (0.2, 0.8))]
    before = copy.deepcopy(refs)
    assert flatten_loft(a, b, refs)["status"] == "UNRESOLVED"
    assert refs == before


def test_forward_parameter_mapping_stays_within_bound_for_a_short_curved_extrusion():
    sweep = 0.1
    end = (10 * math.cos(sweep), 10 * math.sin(sweep))
    a = LoftProfile(
        (Curve((10, 0), end, "arc", {"center": (0, 0), "sweep_deg": math.degrees(sweep)}, "a"),)
    )
    b = LoftProfile(
        (Curve((10, 0), end, "arc", {"center": (0, 0), "sweep_deg": math.degrees(sweep)}, "b"),),
        origin=(0, 0, 15),
    )
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT"
    for u in (0.001, 0.137, 0.501, 0.917, 1):
        point = sample_loft(result, 0, u, 0.7)
        world = [10 * math.cos(sweep * u), 10 * math.sin(sweep * u), 15 * 0.7]
        assert (
            math.dist(point["world_model_mm"], world)
            <= (result["representation_error_bound_paper_mm"])
        )
        assert (
            math.dist(point["flat_paper_mm"], [10 * sweep * u, 15 * 0.7])
            <= (result["representation_error_bound_paper_mm"])
        )
    assert result["coverage"]["expected_first_segment_ids"] == ["a"]


def test_model_profile_adapter_keeps_source_curve_identity_and_closed_intent():
    from archpapercraft.authoring.model import CurveSegment, Profile, Vertex

    source = Profile(
        "profile",
        "own",
        [Vertex("v1", [0, 0]), Vertex("v2", [20, 0])],
        [CurveSegment("source-edge", "line", "v1", "v2")],
        closed=False,
    )
    converted = LoftProfile.from_profile(source)
    assert converted.profile_id == "profile" and converted.curves[0].segment_id == "source-edge"
    assert not converted.closed


def test_cone_forward_map_and_boundary_lengths_have_a_global_not_per_leaf_budget():
    a, b = gothic(20, 30), gothic(24, 36, depth=10, prefix="b")
    result = flatten_loft(a, b, correspondence(a, b))
    assert result["status"] == "EXACT"
    assert result["boundary_length_error_bound_paper_mm"] <= 0.005
    point = sample_loft(result, 1, 0.173, 0.61)
    assert point["first_segment_id"] == "a-right"
    assert point["second_segment_id"] == "b-right"
    assert point["mode"] == "BOUNDED_PARAMETER_INTERPOLATION"
    with pytest.raises(ValueError):
        sample_loft(result, 0, 1.01, 0)
