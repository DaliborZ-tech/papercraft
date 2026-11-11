"""Independent whole-triangle and provenance checks for new segmentation only."""

import hashlib
import json
import math
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import pytest

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_geometry import LoftCorrespondence, LoftProfile
from archpapercraft.authoring.segmented_loft import segment_ruled_loft


def fixture(origin=(0, 0, 0)):
    a = LoftProfile((Curve((0, 0), (40, 0), segment_id="a"),), origin=origin, profile_id="front")
    b = LoftProfile(
        (Curve((0, 0), (40, 20), segment_id="b"),),
        origin=(origin[0], origin[1], origin[2] + 30),
        profile_id="back",
    )
    return a, b, (LoftCorrespondence("a", "b"),)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def test_actual_module_pin_hash():
    import archpapercraft.authoring.segmented_loft as actual

    root = Path(__file__).resolve().parents[4]
    path = root / "src/archpapercraft/authoring/segmented_loft.py"
    assert Path(actual.__file__).resolve() == path
    (Path(__file__).parent / "pc008-segmentation-review-ad0cfa3-binding.json").write_text(
        json.dumps(
            {
                "source_pin": "ad0cfa36559cc7c475e617c94dd04613d96d55f5",
                "actual_module": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            },
            indent=2,
        ),
        encoding="utf8",
    )


def test_whole_triangle_identity_normals_lengths_and_complete_exact_uv():
    a, b, refs = fixture()
    r = segment_ruled_loft(a, b, refs, scale=1)
    assert r["status"] == "CERTIFIED" and r["mode"] == "APPROXIMATE"
    assert r["subdivisions"]["u"] == 8 and r["subdivisions"]["v"] == 4
    assert r["counts"]["triangles"] == 64 and r["counts"]["paired_cut_seams"] == 84
    assert r["patches"][0]["developability_determinant_exact"] == "-24000"
    assert r["max_surface_deviation_paper_mm"] == 0.15625
    assert r["max_normal_angle_bound_deg"] == pytest.approx(8.56567, abs=0.00001)
    assert r["regularity_lower_paper_mm2"] == pytest.approx(1190.733, abs=0.001)
    area = Q(0)
    intervals = {}
    for index, triangle in enumerate(r["triangles"]):
        uv = [[Q(x) for x in p] for p in triangle["parameter_vertices_exact"]]
        xyz = [[Q(x) for x in p] for p in triangle["delivered_vertices_model_mm_exact"]]
        u0, u1 = min(p[0] for p in uv), max(p[0] for p in uv)
        v0, v1 = min(p[1] for p in uv), max(p[1] for p in uv)
        assert (u1 - u0, v1 - v0) == (Q(1, 8), Q(1, 4))
        # On normalized lower triangle y<=x, uv-I(uv)=y(x-1);
        # on upper triangle x<=y, uv-I(uv)=x(y-1). Both magnitudes <=1/4
        # by t(1-t)<=1/4 on the ENTIRE domain, not vertex/interior samples.
        analytic_whole_bound = 20 * (u1 - u0) * (v1 - v0) / 4
        assert Q(triangle["position_error_bound_paper_mm_exact"]) >= analytic_whole_bound
        signed_area = (
            (uv[1][0] - uv[0][0]) * (uv[2][1] - uv[0][1])
            - (uv[1][1] - uv[0][1]) * (uv[2][0] - uv[0][0])
        ) / 2
        assert signed_area == Q(1, 64)
        area += signed_area
        intervals.setdefault((u0, v0), []).append(uv)
        for (u, v), actual in zip(uv, xyz):
            assert actual == [40 * u, 20 * u * v, 30 * v]
        plane = cross(sub(xyz[1], xyz[0]), sub(xyz[2], xyz[0]))
        assert plane == tuple(Q(x) for x in triangle["delivered_plane_normal_exact"])
        normals = [
            (600 * v, Q(-1200), 800 * u) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        ]
        minimum_dot = min(dot(n, plane) for n in normals)
        assert minimum_dot > 0
        regularity = Q(triangle["regularity_lower_paper_mm2_exact"])
        assert regularity**2 * dot(plane, plane) <= minimum_dot**2
        # Affine normal: dot minima and convex cross-norm maxima are bounded
        # by the rectangle corners, independently of the production evaluator.
        ratio = max(
            math.sqrt(float(dot(cross(n, plane), cross(n, plane)))) for n in normals
        ) / float(minimum_dot)
        assert (
            math.degrees(math.atan(ratio))
            <= float(Q(triangle["normal_angle_bound_deg_exact"])) + 1e-12
        )
    assert area == 1 and len(intervals) == 32
    assert all(len(pair) == 2 for pair in intervals.values())
    assert set(intervals) == {(Q(i, 8), Q(j, 4)) for i in range(8) for j in range(4)}
    for (u0, v0), pair in intervals.items():
        u1, v1 = u0 + Q(1, 8), v0 + Q(1, 4)
        assert {frozenset(map(tuple, t)) for t in pair} == {
            frozenset(((u0, v0), (u1, v0), (u1, v1))),
            frozenset(((u0, v0), (u1, v1), (u0, v1))),
        }
    uses = [(u["triangle_index"], u) for edge in r["edges"] for u in edge["uses"]]
    assert sorted(i for i, _ in uses) == sorted([i for i in range(64) for _ in range(3)])
    with localcontext() as ctx:
        ctx.prec = 70
        diagonal = (
            Decimal(4100).sqrt() / 2
            + Decimal("31.25") * (Decimal(".8") + Decimal("1.64").sqrt()).ln()
        )
        full = segment_ruled_loft(a, b, refs, scale=1, max_deviation_mm=5, max_cells=1)
        edge = next(e for e in full["edges"] if e["role"] == "PAIRED_ISLAND_CUT")

        def q(value):
            return Decimal(Q(value).numerator) / Decimal(Q(value).denominator)

        assert q(edge["source_length_lower_paper_mm_exact"]) <= diagonal
        assert diagonal <= q(edge["source_length_upper_paper_mm_exact"])
        shortening = diagonal - Decimal(2900).sqrt()
        assert shortening > 1
        assert shortening <= q(edge["absolute_length_difference_bound_paper_mm_exact"])
    (Path(__file__).parent / "pc008-segmentation-review-ad0cfa3-fixture.json").write_text(
        json.dumps(r, indent=2), encoding="utf8"
    )


def test_actual_rounded_vertices_add_whole_face_error_and_plane_certificate():
    a, b, refs = fixture((0.1, 0.2, 0.3))
    r = segment_ruled_loft(a, b, refs, scale=1, max_deviation_mm=5 + 1e-10, max_cells=1)
    assert r["status"] == "CERTIFIED"
    for triangle in r["triangles"]:
        bound = Q(triangle["position_error_bound_paper_mm_exact"])
        reserve = bound - 5
        assert reserve > 0
        exact = [[Q(x) for x in p] for p in triangle["ideal_vertices_model_mm_exact"]]
        actual = [[Q(x) for x in p] for p in triangle["world_vertices_model_mm"]]
        uv = [[Q(x) for x in p] for p in triangle["parameter_vertices_exact"]]
        for ideal, (u, v) in zip(exact, uv):
            assert ideal == [
                Q(0.1) + 40 * u,
                Q(0.2) + 20 * u * v,
                Q(0.3) + (Q(0.3 + 30) - Q(0.3)) * v,
            ]
        for ideal, delivered in zip(exact, actual):
            assert dot(sub(ideal, delivered), sub(ideal, delivered)) <= reserve**2
        plane = cross(sub(actual[1], actual[0]), sub(actual[2], actual[0]))
        assert plane == tuple(Q(x) for x in triangle["delivered_plane_normal_exact"])
    blocked = segment_ruled_loft(a, b, refs, scale=1, max_deviation_mm=5, max_cells=1)
    assert blocked["status"] == "UNRESOLVED" and "triangles" not in blocked


def test_colliding_profile_references_cannot_certify_different_source_geometries():
    a, b, refs = fixture()
    b = replace(b, profile_id=a.profile_id)
    r = segment_ruled_loft(a, b, refs, scale=1)
    assert r["status"] == "UNRESOLVED"
    assert "triangles" not in r


@pytest.mark.parametrize(
    "case", ["missing", "duplicate", "partial", "inverse_one", "depth", "cells", "singular"]
)
def test_failures_preserve_sources_and_never_publish_partial_mesh(case):
    a, b, refs = fixture()
    kwargs = {"scale": 1}
    if case == "missing":
        refs = (replace(refs[0], second_segment_id="absent"),)
    elif case == "duplicate":
        refs += refs
    elif case == "partial":
        refs = (replace(refs[0], first_interval=(0.25, 1)),)
    elif case == "inverse_one" or case == "singular":
        b = replace(b, curves=(Curve((40, 0), (0, 0), segment_id="b"),))
        kwargs.update(max_depth=3, max_deviation_mm=100)
    elif case == "depth":
        kwargs["max_depth"] = 1
    else:
        kwargs.update(max_deviation_mm=0.0001, max_cells=4)
    before = repr((a, b, refs))
    r = segment_ruled_loft(a, b, refs, **kwargs)
    assert r["status"] == "UNRESOLVED", r
    assert "triangles" not in r and "edges" not in r
    assert repr((a, b, refs)) == before


@pytest.mark.parametrize("reverse", [False, True])
def test_multipatch_oriented_complete_source_coverage_and_weld_direction(reverse):
    a = LoftProfile(
        (Curve((0, 0), (20, 0), segment_id="a0"), Curve((20, 0), (40, 0), segment_id="a1")),
        profile_id="first",
    )
    b = LoftProfile(
        (Curve((0, 0), (20, 10), segment_id="b0"), Curve((20, 10), (40, 20), segment_id="b1")),
        origin=(0, 0, 30),
        profile_id="second",
    )
    order, interval = ([1, 0], (1, 0)) if reverse else ([0, 1], (0, 1))
    refs = tuple(LoftCorrespondence(f"a{i}", f"b{i}", interval, interval) for i in order)
    r = segment_ruled_loft(a, b, refs, scale=1)
    assert r["status"] == "CERTIFIED"
    assert [p["source"]["first_segment_id"] for p in r["patches"]] == [f"a{i}" for i in order]
    for patch in r["patches"]:
        assert patch["source"]["first_parameter_interval"] == list(interval)
        area = Q(0)
        for i in patch["triangle_indices"]:
            t = r["triangles"][i]
            assert t["patch_index"] == r["patches"].index(patch)
            p, q, s = [[Q(x) for x in uv] for uv in t["parameter_vertices_exact"]]
            area += ((q[0] - p[0]) * (s[1] - p[1]) - (q[1] - p[1]) * (s[0] - p[0])) / 2
        assert area == 1
    for edge in r["edges"]:
        if len(edge["uses"]) != 2:
            continue
        xyz = []
        for use in edge["uses"]:
            t = r["triangles"][use["triangle_index"]]
            lookup = dict(
                zip(map(tuple, t["parameter_vertices_exact"]), t["world_vertices_model_mm"])
            )
            xyz.append([lookup[tuple(p)] for p in use["parameter_endpoints_exact"]])
        assert xyz[0] == list(reversed(xyz[1]))


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_curved_sources_are_explicitly_unresolved_not_exact(kind):
    if kind == "arc":
        c = Curve((2, 0), (-2, 0), kind, {"center": (0, 0), "sweep_deg": 180}, "curved")
    else:
        c = Curve((0, 0), (3, 3), kind, {"control1": (1, 0), "control2": (2, 3)}, "curved")
    a = LoftProfile((c,), profile_id="first")
    b = replace(a, profile_id="second", origin=(0, 0, 30))
    r = segment_ruled_loft(a, b, (LoftCorrespondence("curved", "curved"),), scale=1)
    assert r["status"] == "UNRESOLVED" and "triangles" not in r


def test_jacobian_collapse_between_every_dyadic_vertex_is_never_certified():
    a = LoftProfile((Curve((0, 0), (40, 0), segment_id="a"),), profile_id="first")
    b = LoftProfile(
        (Curve((0, 0), (-80, 0), segment_id="b"),), origin=(0, 0, 30), profile_id="second"
    )
    # S=(40u(1-3v),0,30v); N=(0,-1200(1-3v),0). The collapse v=1/3
    # is NEVER a dyadic grid vertex. Every sampled vertex normal is nonzero.
    r = segment_ruled_loft(
        a,
        b,
        (LoftCorrespondence("a", "b"),),
        scale=1,
        max_deviation_mm=100,
        max_depth=8,
        max_cells=256,
    )
    assert r["status"] == "UNRESOLVED" and "triangles" not in r
