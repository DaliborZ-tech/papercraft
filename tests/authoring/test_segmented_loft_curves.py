"""Independent analytic and interval expectations for curved source subdivision."""

import json
import math
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_geometry import LoftCorrespondence, LoftProfile
from archpapercraft.authoring.segmented_loft import segment_ruled_loft


def _refs(a, b, *, reverse=False):
    pairs = list(zip(a.curves, b.curves))
    if reverse:
        pairs.reverse()
    interval = (1, 0) if reverse else (0, 1)
    return tuple(
        LoftCorrespondence(x.segment_id, y.segment_id, interval, interval) for x, y in pairs
    )


def _gothic(w, h, prefix, *, depth=0, size=1, xz=False):
    w, h, depth = w * size, h * size, depth * size
    center = (h * h - w * w) / (2 * w)
    sweep = math.degrees(math.atan2(h, -center)) - 180
    curves = (
        Curve((-w, 0), (0, h), "arc", {"center": (center, 0), "sweep_deg": sweep}, prefix + "L"),
        Curve((0, h), (w, 0), "arc", {"center": (-center, 0), "sweep_deg": sweep}, prefix + "R"),
        Curve((w, 0), (-w, 0), segment_id=prefix + "B"),
    )
    return LoftProfile(
        curves,
        origin=(0, depth, 0) if xz else (0, 0, depth),
        v=(0, 0, 1) if xz else (0, 1, 0),
        profile_id=prefix,
        closed=True,
    )


def _arc(radius, prefix, *, depth=0, endpoint_offset=0):
    curve = Curve(
        (radius, 0),
        (-radius, endpoint_offset),
        "arc",
        {"center": (0, 0), "sweep_deg": 180},
        prefix + "a",
    )
    return LoftProfile((curve,), origin=(0, 0, depth), profile_id=prefix)


def _parabola(prefix, *, depth=0):
    curve = Curve(
        (0, 0), (30, 30), "cubic", {"control1": (10, 0), "control2": (20, 10)}, prefix + "c"
    )
    return LoftProfile((curve,), origin=(0, 0, depth), profile_id=prefix)


def _certified(report):
    assert report["status"] == "CERTIFIED", report
    assert report["mode"] == "APPROXIMATE"
    assert report["family"] == "INTERVAL_CURVED_RULED_TRIANGLE_ISLANDS"
    assert report["physical_build"] == "NOT_VERIFIED"
    assert report["global_embedding"] == "NOT_CHECKED"
    assert report["regularity_lower_paper_mm2"] > 0
    assert report["max_surface_deviation_paper_mm"] <= report["requested_deviation_budget_paper_mm"]
    json.dumps(report, allow_nan=False)
    return report


def _local(curve, t, derivative=False):
    """Test-side analytic source evaluator; imports no production evaluator."""
    a, b = np.array(curve.start), np.array(curve.end)
    if curve.kind == "line":
        return b - a if derivative else a + (b - a) * t
    if curve.kind == "cubic":
        c, d = np.array(curve.data["control1"]), np.array(curve.data["control2"])
        if derivative:
            return 3 * ((1 - t) ** 2 * (c - a) + 2 * t * (1 - t) * (d - c) + t * t * (b - d))
        return (1 - t) ** 3 * a + 3 * t * (1 - t) ** 2 * c + 3 * t * t * (1 - t) * d + t**3 * b
    center = np.array(curve.data["center"])
    x, y = a - center
    omega = math.pi * curve.data["sweep_deg"] / 180
    sine, cosine = math.sin(omega * t), math.cos(omega * t)
    if derivative:
        return omega * np.array([-x * sine - y * cosine, x * cosine - y * sine])
    if t == 0:
        return a
    if t == 1:
        return b
    return center + np.array([x * cosine - y * sine, x * sine + y * cosine])


def _source(a, b, provenance, u, v):
    curves = []
    for profile, label in ((a, "first"), (b, "second")):
        curve = next(c for c in profile.curves if c.segment_id == provenance[label + "_segment_id"])
        start, end = provenance[label + "_parameter_interval"]
        point = _local(curve, start + (end - start) * u)
        tangent = _local(curve, start + (end - start) * u, derivative=True) * (end - start)
        axes = np.column_stack([profile.u, profile.v])
        curves.append((np.array(profile.origin) + axes @ point, axes @ tangent))
    (p, dp), (q, dq) = curves
    return (1 - v) * p + v * q, np.cross((1 - v) * dp + v * dq, q - p)


def _interior_oracle(report, a, b, *, sample_stride=1):
    for triangle in report["triangles"][::sample_stride]:
        provenance = report["patches"][triangle["patch_index"]]["source"]
        uv = np.array(
            [[float(Fraction(x)) for x in p] for p in triangle["parameter_vertices_exact"]]
        )
        points = np.array(triangle["world_vertices_model_mm"])
        plane = np.cross(points[1] - points[0], points[2] - points[0])
        bound = float(Fraction(triangle["position_error_bound_paper_mm_exact"]))
        angle_bound = float(Fraction(triangle["normal_angle_bound_deg_exact"]))
        for weights in ((0.2, 0.3, 0.5), (0.7, 0.2, 0.1), (0.5, 0, 0.5)):
            u, v = np.array(weights) @ uv
            expected, normal = _source(a, b, provenance, u, v)
            delivered = np.array(weights) @ points
            assert np.linalg.norm(expected - delivered) * report["scale"] <= bound + 1e-11
            angle = math.degrees(
                math.atan2(np.linalg.norm(np.cross(normal, plane)), np.dot(normal, plane))
            )
            assert angle <= angle_bound + 1e-10


@pytest.mark.parametrize("reverse", [False, True])
def test_nonhomothetic_gothic_b3_has_bounded_actual_interior_and_sharp_corners(reverse):
    a, b = _gothic(20, 30, "a"), _gothic(18, 25, "b", depth=10)
    result = _certified(segment_ruled_loft(a, b, _refs(a, b, reverse=reverse), scale=1))
    assert result["counts"]["patches"] == 3
    assert result["counts"]["triangles"] <= 256
    assert result["max_surface_deviation_paper_mm"] < 0.25
    _interior_oracle(result, a, b)
    # An independent triple product at u=.5 on the left arc is nonzero.
    ref = next(p["source"] for p in result["patches"] if p["source"]["first_segment_id"] == "aL")
    c0, c1 = a.curves[0], b.curves[0]
    p, q = _local(c0, 0.5), _local(c1, 0.5)
    dp, dq = _local(c0, 0.5, True), _local(c1, 0.5, True)
    determinant = np.dot([*dp, 0], np.cross([*(q - p), 10], [*(dq - dp), 0]))
    assert abs(determinant) > 100
    assert ref["first_parameter_interval"] == ([1, 0] if reverse else [0, 1])
    # All patch parameter areas remain exactly one, including the pointed join.
    for patch in result["patches"]:
        total = Fraction(0)
        for index in patch["triangle_indices"]:
            p, q, r = [
                [Fraction(x) for x in uv]
                for uv in result["triangles"][index]["parameter_vertices_exact"]
            ]
            total += ((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])) / 2
        assert total == 1
        assert "bilinear_coefficients_model_mm_exact" not in patch


def test_twisted_homothetic_gothic_does_not_become_an_exact_plane_by_float_epsilon():
    a, b = _gothic(20, 30, "a"), _gothic(24, 36, "b", depth=10)
    angle = math.radians(25)
    b = replace(
        b, u=(math.cos(angle), math.sin(angle), 0), v=(-math.sin(angle), math.cos(angle), 0)
    )
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    _interior_oracle(result, a, b, sample_stride=3)
    assert result["max_surface_deviation_paper_mm"] > 0
    assert result["source"]["first_profile_id"] == "a"
    assert result["source"]["second_profile_id"] == "b"


def test_arc_extrusion_true_sagitta_and_intrinsic_boundary_length_enclosure():
    a, b = _arc(10, "a"), _arc(10, "b", depth=30)
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    nu = result["subdivisions"]["u"]
    sagitta = 10 * (1 - math.cos(math.pi / (2 * nu)))
    assert 0 < sagitta <= result["max_surface_deviation_paper_mm"]
    for triangle in result["triangles"]:
        values = [Fraction(point[0]) for point in triangle["parameter_vertices_exact"]]
        hu = max(values) - min(values)
        # Independently, |C''|=10*pi² over the entire source half-circle.
        reserved = float(Fraction(triangle["source_interpolation_bound_model_mm_exact"]))
        assert reserved >= 10 * math.pi**2 * float(hu) ** 2 / 8 - 1e-15
    with localcontext() as context:
        context.prec = 80
        pi = Decimal(
            "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998"
        )
        expected = Fraction(20 * pi + 60)
    lower = Fraction(result["lengths"]["source_boundary_lower_paper_mm_exact"])
    upper = Fraction(result["lengths"]["source_boundary_upper_paper_mm_exact"])
    assert lower <= expected <= upper
    assert float(upper - lower) < 1e-18
    _interior_oracle(result, a, b)


def test_cubic_parabola_has_analytic_interior_normals_and_true_source_edge_lengths():
    a, b = _parabola("a"), _parabola("b", depth=30)
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    assert Fraction(result["regularity_lower_paper_mm2_exact"]) <= 900
    _interior_oracle(result, a, b)
    for triangle in result["triangles"]:
        values = [Fraction(point[0]) for point in triangle["parameter_vertices_exact"]]
        hu = max(values) - min(values)
        # C''=(0,60,0) on the whole interval, not a sampled/chord bound.
        assert (
            Fraction(triangle["source_interpolation_bound_model_mm_exact"])
            == Fraction(15, 2) * hu**2
        )
    for edge in result["edges"]:
        uv = [[float(Fraction(x)) for x in p] for p in edge["uses"][0]["parameter_endpoints_exact"]]
        (u0, v0), (u1, v1) = uv
        du, dv = u1 - u0, v1 - v0
        expected, error = quad(
            lambda t: math.sqrt((30 * du) ** 2 + (60 * (u0 + du * t) * du) ** 2 + (30 * dv) ** 2),
            0,
            1,
            epsabs=1e-11,
        )
        assert error < 1e-9
        low = float(Fraction(edge["source_length_lower_paper_mm_exact"]))
        high = float(Fraction(edge["source_length_upper_paper_mm_exact"]))
        assert low - 1e-12 <= expected <= high + 1e-12


@pytest.mark.parametrize(
    "first_kind,second_kind",
    [
        (a, b)
        for a in ("line", "arc", "cubic")
        for b in ("line", "arc", "cubic")
        if (a, b) != ("line", "line")
    ],
)
def test_all_curved_line_arc_cubic_source_kind_pairs(first_kind, second_kind):
    def curve(kind, identity):
        if kind == "line":
            return Curve((-10, 0), (0, 10), segment_id=identity)
        if kind == "arc":
            return Curve((-10, 0), (0, 10), "arc", {"center": (0, 0), "sweep_deg": -90}, identity)
        return Curve(
            (-10, 0), (0, 10), "cubic", {"control1": (-10, 5), "control2": (-5, 10)}, identity
        )

    a = LoftProfile((curve(first_kind, "a0"),), profile_id="a")
    b = LoftProfile((curve(second_kind, "b0"),), origin=(0, 0, 30), profile_id="b")
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    _interior_oracle(result, a, b)


def test_same_parameter_bound_detects_nonlinear_collinear_cubic_not_just_chord_geometry():
    a = LoftProfile(
        (Curve((0, 0), (6, 0), "cubic", {"control1": (1, 0), "control2": (3, 0)}, "a0"),),
        profile_id="a",
    )
    b = LoftProfile(
        (Curve((0, 0), (6, 0), "cubic", {"control1": (1, 0), "control2": (3, 0)}, "b0"),),
        origin=(0, 0, 10),
        profile_id="b",
    )
    rejected = segment_ruled_loft(a, b, _refs(a, b), scale=1, max_cells=1)
    assert rejected["status"] == "UNRESOLVED"
    report = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    assert report["max_surface_deviation_paper_mm"] > 0
    assert report["subdivisions"]["u"] > 1
    triangle = report["triangles"][0]
    uv = np.array([[float(Fraction(x)) for x in p] for p in triangle["parameter_vertices_exact"]])
    u, v = (uv[0] + uv[1]) / 2
    delivered = (
        np.array(triangle["world_vertices_model_mm"][0]) + triangle["world_vertices_model_mm"][1]
    ) / 2
    actual = np.array([3 * u + 3 * u * u, 0, 10 * v])
    assert np.linalg.norm(actual - delivered) > 0
    assert np.linalg.norm(actual - delivered) <= report["max_surface_deviation_paper_mm"]


def test_nondyadic_cubic_stationary_ruling_never_gets_a_regular_certificate():
    # Cx=9u³-9u²+3u, Cx'=3(3u-1)²: the exact collapse u=1/3
    # is never a dyadic mesh vertex, though the endpoint controls are integers.
    curve = Curve((0, 0), (3, 0), "cubic", {"control1": (1, 0), "control2": (-1, 0)}, "a0")
    other = Curve(curve.start, curve.end, "cubic", dict(curve.data), "b0")
    a, b = (
        LoftProfile((curve,), profile_id="a"),
        LoftProfile((other,), origin=(0, 0, 10), profile_id="b"),
    )
    result = segment_ruled_loft(
        a, b, _refs(a, b), scale=1, max_deviation_mm=100, max_cells=256, max_depth=8
    )
    assert result["status"] == "UNRESOLVED"
    assert "triangles" not in result and "edges" not in result


def test_two_genuine_independent_cubic_profiles_have_bounded_nondevelopable_variant():
    ca = Curve((0, 0), (30, 30), "cubic", {"control1": (10, 0), "control2": (20, 15)}, "a0")
    cb = Curve((0, 0), (25, 32), "cubic", {"control1": (7, 3), "control2": (18, 12)}, "b0")
    a = LoftProfile((ca,), profile_id="a")
    b = LoftProfile((cb,), origin=(0, 0, 20), profile_id="b")
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    _interior_oracle(result, a, b)
    p, q = _local(ca, 0.5), _local(cb, 0.5)
    dp, dq = _local(ca, 0.5, True), _local(cb, 0.5, True)
    determinant = np.dot([*dp, 0], np.cross([*(q - p), 20], [*(dq - dp), 0]))
    assert abs(determinant) > 100


def test_arc_halfturn_has_true_nondyadic_collapse_despite_nonzero_vertex_normals():
    a, b = _arc(20, "a"), _arc(28, "b")
    b = replace(b, u=(-1, 0, 0), v=(0, -1, 0))
    result = segment_ruled_loft(
        a, b, _refs(a, b), scale=1, max_deviation_mm=100, max_cells=256, max_depth=8
    )
    assert result["status"] == "UNRESOLVED"
    assert "triangles" not in result
    for j in range(257):
        assert 1 - Fraction(12, 5) * Fraction(j, 256) != 0


def test_original_arc_with_rounded_endpoint_and_common_reverse_preserves_source_radius():
    a, b = _arc(20, "a", endpoint_offset=1e-8), _arc(20, "b", depth=30, endpoint_offset=1e-8)
    result = _certified(segment_ruled_loft(a, b, _refs(a, b, reverse=True), scale=1))
    assert result["numerical_vertex_error_bound_model_mm"] >= 1e-8
    first = result["triangles"][0]
    assert first["world_vertices_model_mm"][0] == [-20, 1e-8, 0]
    _interior_oracle(result, a, b)


@pytest.mark.parametrize("xz", [False, True])
def test_world_basis_and_model100_paper_scale_keep_hard_bounds_in_separate_units(xz):
    a = _gothic(20, 30, "a", size=100, xz=xz)
    b = _gothic(18, 25, "b", depth=10, size=100, xz=xz)
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=0.01))
    assert result["max_surface_deviation_model_mm"] > 1
    assert result["max_surface_deviation_paper_mm"] < 0.25
    assert result["max_surface_deviation_model_mm"] * 0.01 == pytest.approx(
        result["max_surface_deviation_paper_mm"], rel=1e-14
    )
    _interior_oracle(result, a, b, sample_stride=3)


def test_actual_float_world_basis_and_translation_are_not_replaced_by_ideal_axes():
    a, b = _gothic(20, 30, "a"), _gothic(18, 25, "b", depth=10)
    axes = {"u": (0.8, 0.6, 0), "v": (-0.6, 0.8, 0)}
    a = replace(a, origin=(2100, -330, 1200), **axes)
    b = replace(b, origin=(2100, -330, 1210), **axes)
    result = _certified(segment_ruled_loft(a, b, _refs(a, b), scale=1))
    _interior_oracle(result, a, b, sample_stride=2)
    assert result["numerical_vertex_error_bound_model_mm"] > 0


def test_limit_edit_budget_exhaustion_colliding_source_and_immutable_inputs():
    a, b = _gothic(20, 30, "a"), _gothic(18, 25, "b", depth=10)
    refs = _refs(a, b)
    before = (a.curves, a.origin, a.u, a.v, b.curves, b.origin, b.u, b.v)
    loose = _certified(segment_ruled_loft(a, b, refs, scale=1))
    tighter = _certified(segment_ruled_loft(a, b, refs, scale=1, max_deviation_mm=0.1))
    assert tighter["counts"]["triangles"] > loose["counts"]["triangles"]
    for other, references, settings in (
        (b, refs, {"max_cells": 3}),
        (b, refs, {"max_depth": 0}),
        (b, refs[:-1], {}),
        (b, refs + refs[:1], {}),
        (replace(b, profile_id="a"), refs, {}),
    ):
        result = segment_ruled_loft(a, other, references, scale=1, **settings)
        assert result["status"] == "UNRESOLVED"
        assert "triangles" not in result and "edges" not in result
    assert before == (a.curves, a.origin, a.u, a.v, b.curves, b.origin, b.u, b.v)


def test_historical_approved_line_payload_remains_identical():
    raw = (
        Path(__file__).resolve().parents[2]
        / "docs/p2/implementation/evidence/pc008-segmentation-review-ad0cfa3-fixture.json"
    )
    expected = json.loads(raw.read_text(encoding="utf8"))
    a = LoftProfile((Curve((0, 0), (40, 0), segment_id="a"),), profile_id="front")
    b = LoftProfile(
        (Curve((0, 0), (40, 20), segment_id="b"),), origin=(0, 0, 30), profile_id="back"
    )
    actual = segment_ruled_loft(a, b, _refs(a, b), scale=1)
    assert actual == expected


def test_curved_source_world_precision_and_partial_refs_cannot_publish_partial_mesh():
    a, b = _arc(20, "a"), _arc(20, "b", depth=30)
    refs = _refs(a, b)
    shifted_a = replace(a, origin=(1e20, 0, 0))
    shifted_b = replace(b, origin=(1e20, 0, 30))
    result = segment_ruled_loft(
        shifted_a, shifted_b, refs, scale=1, max_deviation_mm=100, max_cells=16, max_depth=4
    )
    assert result["status"] == "UNRESOLVED"
    assert "triangles" not in result
    partial = (replace(refs[0], first_interval=(0.2, 0.8)),)
    result = segment_ruled_loft(a, b, partial, scale=1)
    assert result["status"] == "UNRESOLVED" and result["examined_cells"] == 0


def test_exact_rational_full_interval_provenance_is_detached_json_not_fraction_objects():
    a, b = _arc(10, "a"), _arc(10, "b", depth=30)
    refs = (LoftCorrespondence("aa", "ba", (Fraction(0), Fraction(1)), (Fraction(0), Fraction(1))),)
    report = _certified(segment_ruled_loft(a, b, refs, scale=1))
    assert report["source"]["correspondences"][0]["first_parameter_interval"] == [0, 1]
    assert all(
        type(x) is int for x in report["source"]["correspondences"][0]["first_parameter_interval"]
    )
