"""Independent bilinear target, interior, length, regularity and coverage oracles."""

import json
import math
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_geometry import LoftCorrespondence, LoftProfile
from archpapercraft.authoring.segmented_loft import segment_ruled_loft


def _fixture(*, scale_size=1, origin=(0, 0, 0)):
    first = LoftProfile(
        (Curve((0, 0), (40 * scale_size, 0), segment_id="front-line"),),
        origin=origin,
        profile_id="front-profile",
    )
    second = LoftProfile(
        (Curve((0, 0), (40 * scale_size, 20 * scale_size), segment_id="back-line"),),
        origin=(origin[0], origin[1], origin[2] + 30 * scale_size),
        profile_id="back-profile",
    )
    return first, second, (LoftCorrespondence("front-line", "back-line"),)


def _report(**options):
    first, second, references = _fixture()
    return segment_ruled_loft(first, second, references, scale=1, **options)


def _certified(report):
    assert report["status"] == "CERTIFIED", report
    assert report["mode"] == "APPROXIMATE"
    assert report["segmentation_only"] is True
    assert report["physical_build"] == "NOT_VERIFIED"
    assert report["global_embedding"] == "NOT_CHECKED"
    assert report["max_surface_deviation_paper_mm"] <= report["requested_deviation_budget_paper_mm"]
    assert Fraction(report["max_surface_deviation_paper_mm"]) >= Fraction(
        report["max_surface_deviation_paper_mm_exact"]
    )
    assert report["regularity_lower_paper_mm2"] > 0
    assert 0 <= report["max_normal_angle_bound_deg"] <= 90
    json.dumps(report, allow_nan=False)
    return report


def _target(u, v):
    # Direct author fixture, independent of production coefficients and evaluator.
    return np.array([40 * u, 20 * u * v, 30 * v], dtype=float)


def _normal(u, v):
    # (40,20v,0) x (0,20u,30); min norm over the entire square is 1200.
    return np.array([600 * v, -1200, 800 * u], dtype=float)


def test_hand_determinant_and_true_whole_face_error_not_only_vertices():
    # C0'=(40,0,0), d=(0,20u,30), d'=(0,20,0): determinant=-24000.
    report = _certified(_report(max_deviation_mm=5, max_cells=1))
    assert report["patches"][0]["developability_determinant_exact"] == "-24000"
    assert report["patches"][0]["nondevelopable_witness"] is True
    assert report["counts"]["triangles"] == 2
    triangle = report["triangles"][0]
    vertices = np.array(triangle["world_vertices_model_mm"])
    # At the shared parameter diagonal midpoint, P1=(20,10,15), S=(20,5,15).
    delivered_midpoint = (vertices[0] + vertices[2]) / 2
    actual_error = np.linalg.norm(_target(0.5, 0.5) - delivered_midpoint)
    assert actual_error == 5
    assert Fraction(triangle["position_error_bound_paper_mm_exact"]) == 5
    assert report["max_surface_deviation_paper_mm"] == 5
    # All mesh vertices lie on the target, which alone would falsely report zero.
    for point, uv in zip(vertices, triangle["parameter_vertices_exact"]):
        assert np.array_equal(point, _target(*(float(Fraction(x)) for x in uv)))


def test_required_quarter_millimeter_budget_is_conservative_and_complete():
    report = _certified(_report())
    assert report["subdivisions"] == {"u": 8, "v": 4, "refinement_rounds": 5}
    assert report["max_surface_deviation_paper_mm"] == 0.15625
    assert report["counts"] == {
        "patches": 1,
        "cells": 32,
        "triangles": 64,
        "triangle_island_parts": 64,
        "paired_cut_seams": 84,
        "source_boundary_cut_segments": 24,
        "manufactured_triangle_cut_segments": 192,
    }
    assert report["examined_cells"] == 63
    assert Fraction(report["regularity_lower_paper_mm2_exact"]) <= 1200
    source = report["source"]
    assert source["first_profile_id"] == "front-profile"
    assert source["second_profile_id"] == "back-profile"
    assert source["expected_first_segment_ids"] == ["front-line"]
    assert source["expected_second_segment_ids"] == ["back-line"]


def test_independent_interior_points_and_normal_angles_fit_each_regional_bound():
    report = _certified(_report())
    for triangle in report["triangles"]:
        uv = np.array(
            [[float(Fraction(x)) for x in p] for p in triangle["parameter_vertices_exact"]]
        )
        vertices = np.array(triangle["world_vertices_model_mm"])
        plane = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
        position_bound = float(Fraction(triangle["position_error_bound_paper_mm_exact"]))
        normal_bound = float(Fraction(triangle["normal_angle_bound_deg_exact"]))
        for weights in ((0.2, 0.3, 0.5), (0.6, 0.1, 0.3), (0.5, 0, 0.5)):
            u, v = np.array(weights) @ uv
            delivered = np.array(weights) @ vertices
            assert np.linalg.norm(_target(u, v) - delivered) <= position_bound + 1e-12
            normal = _normal(u, v)
            angle = math.degrees(
                math.atan2(np.linalg.norm(np.cross(normal, plane)), np.dot(normal, plane))
            )
            assert angle <= normal_bound + 1e-12


def test_exact_parameter_triangles_cover_square_once_without_gaps_or_overlap():
    report = _certified(_report())
    from shapely import Polygon
    from shapely.ops import unary_union

    total_area = Fraction(0)
    triangles = []
    for record in report["triangles"]:
        a, b, c = [[Fraction(x) for x in uv] for uv in record["parameter_vertices_exact"]]
        area = ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
        assert area > 0
        total_area += area
        triangles.append(Polygon([[float(x) for x in uv] for uv in (a, b, c)]))
    assert total_area == 1
    assert sum(p.area for p in triangles) == 1
    assert unary_union(triangles).area == 1
    # Every triangle edge belongs to one boundary cut or a two-sided cut pair.
    uses = [use["triangle_index"] for edge in report["edges"] for use in edge["uses"]]
    assert sorted(uses) == sorted([i for i in range(64) for _ in range(3)])
    assert all(len(edge["uses"]) in (1, 2) for edge in report["edges"])


def test_source_boundary_length_is_preserved_and_diagonal_shortening_has_own_bound():
    report = _certified(_report(max_deviation_mm=5, max_cells=1))
    boundary = 40 + math.sqrt(2000) + 30 + math.sqrt(1300)
    low = float(Fraction(report["lengths"]["source_boundary_lower_paper_mm_exact"]))
    high = float(Fraction(report["lengths"]["source_boundary_upper_paper_mm_exact"]))
    assert low <= boundary <= high
    diagonal = next(edge for edge in report["edges"] if edge["role"] == "PAIRED_ISLAND_CUT")
    # On u=v=t: S=(40t,20t²,30t), speed=sqrt(2500+1600t²).
    intrinsic, error = quad(lambda t: math.sqrt(2500 + 1600 * t * t), 0, 1, epsabs=1e-12)
    assert error < 1e-10
    chord = math.sqrt(40**2 + 20**2 + 30**2)
    assert intrinsic - chord > 1
    source_low = float(Fraction(diagonal["source_length_lower_paper_mm_exact"]))
    source_high = float(Fraction(diagonal["source_length_upper_paper_mm_exact"]))
    assert source_low <= intrinsic <= source_high
    assert intrinsic - chord <= float(
        Fraction(diagonal["absolute_length_difference_bound_paper_mm_exact"])
    )
    assert report["lengths"]["boundary_absolute_difference_bound_paper_mm"] < 1e-20


def test_editing_budget_refines_or_returns_unresolved_without_partial_geometry():
    loose, tighter = _certified(_report()), _certified(_report(max_deviation_mm=0.1))
    assert tighter["counts"]["triangles"] > loose["counts"]["triangles"]
    assert tighter["max_surface_deviation_paper_mm"] < loose["max_surface_deviation_paper_mm"]
    rejected = _report(max_deviation_mm=0.0001, max_cells=16)
    assert rejected["status"] == "UNRESOLVED"
    assert "cell budget" in rejected["message"]
    assert "triangles" not in rejected
    assert rejected["examined_cells"] < 2 * 16


def test_hard_budget_can_fail_even_though_vertex_samples_all_have_zero_error():
    report = _report(max_deviation_mm=0.25, max_cells=1)
    assert report["status"] == "UNRESOLVED"
    assert "triangles" not in report


def test_depth_exhaustion_is_explicit_and_does_not_relax_requested_limit():
    report = _report(max_deviation_mm=0.25, max_depth=4)
    assert report["status"] == "UNRESOLVED"
    assert "depth budget" in report["message"]


def test_regularity_proof_refines_without_using_zero_samples_as_a_certificate():
    first = LoftProfile((Curve((0, 0), (1, 0), segment_id="a"),), profile_id="first")
    second = LoftProfile(
        (Curve((0, 0), (-1, 1), segment_id="b"),), origin=(0, 0, 1), profile_id="second"
    )
    refs = (LoftCorrespondence("a", "b"),)
    coarse = segment_ruled_loft(first, second, refs, scale=1, max_deviation_mm=10, max_depth=0)
    assert coarse["status"] == "UNRESOLVED"
    assert "regularity" in coarse["message"]
    refined = _certified(segment_ruled_loft(first, second, refs, scale=1, max_deviation_mm=10))
    assert refined["subdivisions"]["refinement_rounds"] > 0
    # N=(v,2v-1,u) never vanishes, but one coarse triangle's normal points
    # more than 90 degrees from a remote corner. Refinement proves its region.
    assert refined["regularity_lower_paper_mm2"] > 0


def test_crossing_rulings_with_true_jacobian_collapse_remain_unresolved():
    first = LoftProfile((Curve((0, 0), (40, 0), segment_id="a"),), profile_id="first")
    second = LoftProfile(
        (Curve((40, 0), (0, 0), segment_id="b"),), origin=(0, 0, 30), profile_id="second"
    )
    refs = (LoftCorrespondence("a", "b"),)
    result = segment_ruled_loft(first, second, refs, scale=1, max_deviation_mm=100, max_depth=6)
    assert result["status"] == "UNRESOLVED"
    assert "triangles" not in result


@pytest.mark.parametrize("reverse", [False, True])
def test_multipatch_explicit_corner_adjacency_and_common_reversed_source_intervals(reverse):
    curves_a = (Curve((0, 0), (20, 0), segment_id="a0"), Curve((20, 0), (40, 0), segment_id="a1"))
    curves_b = (
        Curve((0, 0), (20, 10), segment_id="b0"),
        Curve((20, 10), (40, 20), segment_id="b1"),
    )
    first = LoftProfile(curves_a, profile_id="first")
    second = LoftProfile(curves_b, origin=(0, 0, 30), profile_id="second")
    order = [1, 0] if reverse else [0, 1]
    interval = (1, 0) if reverse else (0, 1)
    refs = tuple(LoftCorrespondence(f"a{i}", f"b{i}", interval, interval) for i in order)
    report = _certified(segment_ruled_loft(first, second, refs, scale=1))
    assert len(report["patches"]) == 2
    assert sum(Fraction(p["parameter_area_exact"]) for p in report["patches"]) == 2
    assert all(p["source"]["first_parameter_interval"] == list(interval) for p in report["patches"])
    corner_edges = [
        edge for edge in report["edges"] if len({u["patch_index"] for u in edge["uses"]}) == 2
    ]
    assert len(corner_edges) == report["subdivisions"]["v"]
    assert all(len(edge["uses"]) == 2 for edge in corner_edges)


def test_closed_profile_declared_seam_has_semantic_adjacency_without_coordinate_dedup():
    points = [(0, 0), (40, 0), (40, 20), (0, 20)]
    a = tuple(Curve(p, points[(i + 1) % 4], segment_id=f"a{i}") for i, p in enumerate(points))
    b = tuple(Curve(p, points[(i + 1) % 4], segment_id=f"b{i}") for i, p in enumerate(points))
    first, second = (
        LoftProfile(a, profile_id="first", closed=True),
        LoftProfile(b, origin=(0, 0, 30), profile_id="second", closed=True),
    )
    refs = tuple(LoftCorrespondence(f"a{i}", f"b{i}") for i in range(4))
    report = _certified(segment_ruled_loft(first, second, refs, scale=1))
    assert report["counts"]["triangles"] == 8
    assert report["counts"]["source_boundary_cut_segments"] == 8
    assert report["counts"]["paired_cut_seams"] == 8
    assert report["max_surface_deviation_paper_mm"] == 0
    assert report["max_normal_angle_bound_deg"] == 0
    # Even a zero-error planar target is not upgraded by this approximation API.
    assert report["mode"] == "APPROXIMATE"


def test_model_scale_conversion_and_rigid_world_translation_preserve_paper_error():
    first, second, refs = _fixture(scale_size=100, origin=(1024, -512, 64))
    result = _certified(segment_ruled_loft(first, second, refs, scale=0.01))
    reference = _certified(_report())
    assert result["subdivisions"] == reference["subdivisions"]
    assert result["max_surface_deviation_paper_mm"] == pytest.approx(
        reference["max_surface_deviation_paper_mm"], rel=1e-14
    )
    assert result["max_normal_angle_bound_deg"] == pytest.approx(
        reference["max_normal_angle_bound_deg"], abs=1e-12
    )


def test_unrepresentable_world_coordinates_cannot_pass_as_exact_source_vertices():
    first, second, refs = _fixture(origin=(1e20, 0, 0))
    report = segment_ruled_loft(first, second, refs, scale=1, max_depth=3)
    assert report["status"] == "UNRESOLVED"
    assert "triangles" not in report


def test_actual_vertex_rounding_is_measured_and_reserved_in_the_hard_position_bound():
    first, second, refs = _fixture(origin=(0.1, 0.2, 0.3))
    report = _certified(
        segment_ruled_loft(first, second, refs, scale=1, max_deviation_mm=5 + 1e-12, max_cells=1)
    )
    assert report["numerical_vertex_error_bound_paper_mm"] > 0
    assert Fraction(report["max_surface_deviation_paper_mm_exact"]) > 5
    triangle = report["triangles"][0]
    for floats, exact in zip(
        triangle["world_vertices_model_mm"], triangle["delivered_vertices_model_mm_exact"]
    ):
        assert [Fraction(x) for x in floats] == [Fraction(x) for x in exact]
    blocked = segment_ruled_loft(first, second, refs, scale=1, max_deviation_mm=5, max_cells=1)
    assert blocked["status"] == "UNRESOLVED"


def test_rigidly_rotated_source_planes_preserve_bounds_and_triangle_counts():
    first, second, refs = _fixture()
    # Ninety degrees about X: (x,y,z)->(x,-z,y), an exact rigid basis.
    first = replace(first, v=(0, 0, 1))
    second = replace(second, v=(0, 0, 1), origin=(0, -30, 0))
    rotated = _certified(segment_ruled_loft(first, second, refs, scale=1))
    reference = _certified(_report())
    assert rotated["counts"] == reference["counts"]
    assert (
        rotated["max_surface_deviation_paper_mm_exact"]
        == reference["max_surface_deviation_paper_mm_exact"]
    )
    assert (
        rotated["max_normal_angle_bound_deg_exact"] == reference["max_normal_angle_bound_deg_exact"]
    )


def test_sources_are_immutable_and_returned_geometry_is_detached():
    first, second, refs = _fixture()

    def state(profile):
        return (
            profile.origin,
            profile.u,
            profile.v,
            [(c.start, c.end, dict(c.data), c.segment_id) for c in profile.curves],
        )

    before = state(first), state(second)
    result = _certified(segment_ruled_loft(first, second, refs, scale=1))
    result["triangles"][0]["world_vertices_model_mm"][0][0] = 123456
    again = _certified(segment_ruled_loft(first, second, refs, scale=1))
    assert again["triangles"][0]["world_vertices_model_mm"][0][0] == 0
    assert before == (state(first), state(second))


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_unproved_curved_source_families_are_explicitly_unsupported(kind):
    if kind == "arc":
        a = Curve((20, 0), (-20, 0), "arc", {"center": (0, 0), "sweep_deg": 180}, "a")
        b = Curve((20, 0), (-20, 0), "arc", {"center": (0, 0), "sweep_deg": 180}, "b")
    else:
        a = Curve((0, 0), (30, 30), "cubic", {"control1": (10, 0), "control2": (20, 10)}, "a")
        b = Curve(a.start, a.end, "cubic", dict(a.data), "b")
    first, second = (
        LoftProfile((a,), profile_id="first"),
        LoftProfile((b,), origin=(0, 0, 30), profile_id="second"),
    )
    result = segment_ruled_loft(first, second, (LoftCorrespondence("a", "b"),), scale=1)
    assert result["status"] == "UNRESOLVED"
    assert result["supported_source_kinds"] == ["line"]
    assert "curved target" in result["next_action"]
    assert "triangles" not in result


@pytest.mark.parametrize(
    "settings",
    [
        {"scale": 0},
        {"scale": -1},
        {"scale": True},
        {"scale": math.nan},
        {"scale": math.inf},
        {"max_deviation_mm": 0},
        {"max_deviation_mm": -0.25},
        {"max_deviation_mm": True},
        {"max_deviation_mm": math.inf},
        {"max_cells": 0},
        {"max_cells": True},
        {"max_depth": -1},
        {"max_depth": True},
    ],
)
def test_invalid_numerical_inputs_cannot_mutate_or_produce_candidate_geometry(settings):
    first, second, refs = _fixture()
    result = segment_ruled_loft(first, second, refs, **{"scale": 1, **settings})
    assert result["status"] == "UNRESOLVED"
    assert result["examined_cells"] == 0
    assert "triangles" not in result


def test_incomplete_duplicate_partial_and_boolean_correspondences_fail_before_sampling():
    first, second, refs = _fixture()
    cases = [
        (),
        refs + refs,
        (replace(refs[0], first_interval=(0, 0.5)),),
        (replace(refs[0], first_interval=(False, True)),),
    ]
    for references in cases:
        result = segment_ruled_loft(first, second, references, scale=1)
        assert result["status"] == "UNRESOLVED", result
        assert result["examined_cells"] == 0


def test_inconsistent_source_topology_is_not_silently_closed():
    first, second, refs = _fixture()
    for a, b in (
        (replace(first, closed=True), second),
        (replace(first, closed=True), replace(second, closed=True)),
    ):
        result = segment_ruled_loft(a, b, refs, scale=1)
        assert result["status"] == "UNRESOLVED"
        assert result["examined_cells"] == 0
