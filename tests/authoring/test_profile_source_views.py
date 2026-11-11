"""Source identities/polynomials and historical coverage, independent of UI."""

import copy
import json
import math
from fractions import Fraction as Q

import pytest

from archpapercraft.authoring.curve_subdivision import (
    CurveSource,
    CurveSubdivisionHistory,
    SourcePointReference,
    TrimReference,
)
from archpapercraft.authoring.curves import (
    Curve,
    _control,
    certify_curve,
    derivative,
    evaluate,
    svg_commands,
)
from archpapercraft.authoring.loft_geometry import LoftCorrespondence, LoftProfile, flatten_loft
from archpapercraft.authoring.model import CurveSegment, Profile, SketchPlane, Vertex
from archpapercraft.authoring.profile_curves import _reversed_curve, source_curve
from archpapercraft.authoring.profile_source_views import (
    SourceCurveView,
    SourceViewError,
    canonical_projection,
    historical_point,
    history_chord,
    native_projection_certificate,
    semantic_reference_curves,
    source_reference,
    source_region_area_bounds,
    validate_projection,
)


def arc(gap=0):
    return CurveSource("arc", (20, 0), (-20, Q(gap)), center=(0, 0), sweep_deg=180)


def cubic():
    # Exact independent power: x=12t²-8t³, y=12t-12t².
    return CurveSource("cubic", (0, 0), (4, 0), controls=((0, 4), (4, 4)))


def history(kind="arc"):
    source = (
        arc()
        if kind == "arc"
        else cubic()
        if kind == "cubic"
        else CurveSource("line", (0, 0), (12, 4))
    )
    return CurveSubdivisionHistory("profile", "root", source)


def profile_for(h, *, depth=0):
    vertices, segments = [], []
    for i, piece in enumerate(h.pieces):
        reference = source_reference(h, piece.id)
        cache = canonical_projection(reference)
        if not vertices:
            vertices.append(Vertex("vertex-0", cache["start"]))
        vertices.append(Vertex(f"vertex-{i + 1}", cache["end"]))
        segment = CurveSegment(
            piece.id, cache["kind"], vertices[-2].id, vertices[-1].id, cache["data"]
        )
        # Root app owner adds this known persisted field in schema8. This math
        # fixture exercises the same self-contained field without modifying7.
        segment.source_reference = reference
        segments.append(segment)
    return Profile(
        h.profile_id,
        "Curve",
        vertices,
        segments,
        closed=False,
        plane=SketchPlane(origin=[0, 0, depth]),
    )


def view(h, piece="root"):
    return SourceCurveView.from_reference(source_reference(h, piece))


@pytest.mark.parametrize("a,b", [(Q(0), Q(1, 3)), (Q(1, 3), Q(7, 8)), (Q(7, 8), Q(1, 3))])
def test_restricted_cubic_matches_entire_independent_power_polynomial(a, b):
    v = view(history("cubic")).restricted(a, b)
    controls = _control(v)
    power = tuple(
        (p0, 3 * (p1 - p0), 3 * (p0 - 2 * p1 + p2), -p0 + 3 * p1 - 3 * p2 + p3)
        for p0, p1, p2, p3 in zip(*controls)
    )
    d = b - a
    expected = (
        (12 * a * a - 8 * a**3, (24 * a - 24 * a * a) * d, (12 - 24 * a) * d * d, -8 * d**3),
        (12 * a - 12 * a * a, (12 - 24 * a) * d, -12 * d * d, Q(0)),
    )
    assert power == expected
    assert derivative(v, Q(1, 3)) == pytest.approx(
        ((24 * (a + d / 3) - 24 * (a + d / 3) ** 2) * d, (12 - 24 * (a + d / 3)) * d)
    )
    assert v.reversed().reversed().to_reference() == v.to_reference()


def test_half_circle_original_radius_survives_irrational_child_cache():
    h = history().split("root", Q(1, 3), "left", "right")
    v = view(h, "right")
    assert sum(Q(x) ** 2 for x in v.start) != 400  # rounded child is not the circle definition
    low, high = v.radius_bounds()
    assert low <= 20 <= high and high - low < Q(1, 10**70)
    cert = certify_curve(v, chord_tolerance=0.01, length_tolerance=0.01)
    expected = 40 * math.pi / 3
    assert cert.status == "CERTIFIED" and cert.length_lower <= expected <= cert.length_upper
    assert evaluate(v, Q(1, 4)) == (0.0, 20.0)
    assert derivative(v, Q(1, 4)) == pytest.approx((-40 * math.pi / 3, 0))
    assert _reversed_curve(v).root_source == v.root_source


@pytest.mark.parametrize("kind", ["line", "arc", "cubic"])
def test_repeated_split_merge_restrictions_preserve_signed_source_area(kind):
    original = history(kind)
    h = original.split("root", Q(1, 3), "left", "right").split("right", Q(3, 5), "middle", "end")
    whole = view(original)
    areas = [view(h, p.id).green_integral_bounds() for p in h.pieces]
    lower, upper = sum(a for a, _ in areas), sum(b for _, b in areas)
    source_low, source_high = whole.green_integral_bounds()
    assert lower <= source_high and source_low <= upper
    if kind != "arc":
        assert lower == upper == source_low == source_high
    merged = h.merge([p.id for p in h.pieces], "merged")
    assert (
        view(merged, "merged").controls_exact() == whole.controls_exact()
        if kind != "arc"
        else (view(merged, "merged").root_source == whole.root_source)
    )
    restored = CurveSubdivisionHistory.from_dict(json.loads(json.dumps(merged.to_dict())))
    assert source_reference(restored, "merged") == source_reference(merged, "merged")


@pytest.mark.parametrize("kind", ["line", "arc", "cubic"])
def test_exact_source_to_native_projection_has_direct_green_integral_guard(kind):
    v = view(history(kind)).restricted(Q(1, 3), Q(7, 8))
    result = native_projection_certificate(
        v, position_budget=0.01, length_budget=0.01, area_budget=0.01
    )
    assert result["status"] == "CERTIFIED"
    assert Q(result["area_error_bound_exact"]) <= Q(result["area_budget_exact"])
    impossible = native_projection_certificate(
        v, position_budget=1e-30, length_budget=1e-30, area_budget=1e-30, max_segments=2
    )
    assert impossible["status"] == "UNRESOLVED"


def test_independent_cubic_area_and_length_bound_and_reverse_sign():
    v = view(history("cubic"))
    # ∫(xdy-ydx)/2 = -48/5 from the stated two source polynomials.
    assert v.green_integral_bounds() == (Q(-48, 5), Q(-48, 5))
    assert v.reversed().green_integral_bounds() == (Q(48, 5), Q(48, 5))
    # Speed=12*(2t²-2t+1), so the whole curve has length8 exactly.
    cert = certify_curve(v, chord_tolerance=0.01, length_tolerance=0.001)
    assert cert.length_lower <= 8 <= cert.length_upper
    assert cert.length_upper - cert.length_lower <= 0.001


@pytest.mark.parametrize(
    "mutation", ["schema", "future", "source_future", "profile", "piece", "bool"]
)
def test_descriptor_is_strict_qualified_and_detached(mutation):
    reference = source_reference(history(), "root")
    changed = copy.deepcopy(reference)
    if mutation == "schema":
        changed["schema"] = 2
    elif mutation == "future":
        changed["external_factory"] = "execute"
    elif mutation == "source_future":
        changed["source"]["future"] = 1
    elif mutation in ("profile", "piece"):
        changed[mutation + "_id"] = "different"
    else:
        changed["generation"] = True
    with pytest.raises(ValueError):
        SourceCurveView.from_reference(
            changed, expected_profile_id="profile", expected_piece_id="root"
        )
    v = SourceCurveView.from_reference(reference)
    reference["source"]["start"][0] = "0"
    assert v.start == (20, 0)
    with pytest.raises((AttributeError, TypeError)):
        v.data["center"] = (1, 2)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_source_curve_reader_and_projection_poison_are_checked_without_project_lookup(kind):
    h = history(kind).split("root", Q(1, 3), "left", "right")
    profile = profile_for(h)
    actual = source_curve(profile, profile.segments[1])
    assert actual.root_source == h.pieces[1].source
    assert (
        _control(actual) == h.pieces[1].controls_exact()
        if kind == "cubic"
        else actual.kind == "arc"
    )
    profile.vertices[-1].point[0] += 1e-8
    with pytest.raises(SourceViewError, match="cache"):
        source_curve(profile, profile.segments[1])


def test_authored_arc_endpoint_gap_is_retained_bounded_and_not_called_exact():
    source = arc(Q(1, 20000000))
    h = CurveSubdivisionHistory("profile", "root", source).split("root", Q(1, 3), "a", "b")
    v = view(h, "b")
    assert v.end == source.end and v.evaluate(1) == (-20.0, 5e-8)
    assert v.point_bounds(1) == ((Q(-20), Q(-20)), (Q(0), Q(0)))
    assert v.endpoint_gap_bound() >= Q(1, 20000000)
    assert certify_curve(v, chord_tolerance=1e-9, length_tolerance=1e-9).status == "UNRESOLVED"
    assert (
        native_projection_certificate(
            v, position_budget=0.01, length_budget=0.01, area_budget=0.01
        )["status"]
        == "CERTIFIED"
    )


@pytest.mark.parametrize("kind", ["arc", "cubic", "line"])
def test_semantic_whole_source_loft_does_not_repartition_phi_when_one_profile_is_split(kind):
    root = history(kind)
    split = root.split("root", Q(1, 3), "left", "right")
    first = profile_for(split)
    second_history = CurveSubdivisionHistory("other", "other-edge", root.pieces[0].source)
    second = profile_for(second_history, depth=10)
    semantic = semantic_reference_curves(first, {"root": split}, ["root"])
    assert semantic["status"] == "RESOLVED" and semantic["full_profile_coverage"]
    assert type(semantic["curves"][0]) is Curve
    assert [use["piece_id"] for use in semantic["coverage"][0]["uses"]] == ["left", "right"]
    a = LoftProfile.from_profile(first, histories={"root": split}, references=["root"])
    b = LoftProfile.from_profile(
        second, histories={"other-edge": second_history}, references=["other-edge"]
    )
    result = flatten_loft(a, b, [LoftCorrespondence("root", "other-edge")])
    before = flatten_loft(
        LoftProfile.from_profile(profile_for(root), histories={"root": root}, references=["root"]),
        b,
        [LoftCorrespondence("root", "other-edge")],
    )
    assert result == before and result["status"] == "EXACT"
    assert len(result["patches"]) == 1


def test_partial_reference_coverage_and_edited_child_are_truthfully_unresolved_for_whole_loft():
    h = history().split("root", Q(1, 3), "left", "right")
    profile = profile_for(h)
    partial = TrimReference("trim", "profile", "root", Q(1, 4), Q(3, 4))
    result = semantic_reference_curves(profile, {"root": h}, [partial])
    assert result["status"] == "RESOLVED" and not result["full_profile_coverage"]
    assert result["curves"][0].parameter_interval == (Q(1, 4), Q(3, 4))
    a = LoftProfile.from_profile(profile, histories={"root": h}, references=[partial])
    assert flatten_loft(a, a, [LoftCorrespondence("root", "root")])["status"] == "UNRESOLVED"
    h = h.edit("left", CurveSource("line", (20, 0), (10, 17)))
    profile = profile_for(h)
    result = semantic_reference_curves(profile, {"root": h}, ["root"])
    assert result["status"] == "UNRESOLVED" and "GENERATION" in result["why"]
    assert profile.segment("left") is not None and profile.segment("right") is not None


def test_semantic_chord_and_retired_point_are_source_positions_not_first_child():
    h = history().split("root", Q(1, 4), "left", "right")
    chord = history_chord(h, "root")
    assert chord["points"] == ((20.0, 0.0), (-20.0, 0.0))
    assert "NOT_AN_EXACT_STRAIGHT_HINGE" in chord["scope"]
    assert view(h, "left").end != chord["points"][1]
    ref = SourcePointReference("retired-vertex", "profile", "root", Q(1, 4))
    point = historical_point(h, ref)
    assert point["status"] == "SHARED_POINT" and len(point["uses"]) == 2
    assert point["point"] == pytest.approx((math.sqrt(200), math.sqrt(200)))


def test_legacy_none_reader_retains_identical_curve_and_svg_bytes():
    profile = profile_for(history("cubic"))
    segment = profile.segments[0]
    segment.source_reference = None
    curve = source_curve(profile, segment)
    expected = Curve((0, 0), (4, 0), "cubic", {"control1": (0, 4), "control2": (4, 4)}, "root")
    assert type(curve) is Curve and svg_commands(curve) == svg_commands(expected)


def test_partial_arc_native_topology_does_not_certify_the_different_analytic_source():
    from archpapercraft.authoring.curve_topology import (
        certify_native_region_topology,
        certify_region_topology,
    )

    h = history().split("root", Q(1, 3), "left", "right")
    a, b = view(h, "left"), view(h, "right")
    # Exact rational counterexample: the stored 60° endpoint is NOT on the
    # source circle even though a minor native endpoint-A can pass through it.
    assert sum(Q(x) ** 2 for x in a.end) != 400
    source_result = certify_region_topology((a, b, Curve(b.end, a.start)))
    assert source_result.status == "UNRESOLVED"
    assert "SOURCE_VIEW_TOPOLOGY_UNRESOLVED" in source_result.reason
    commands = []
    for curve in (a, b):
        packet = native_projection_certificate(
            curve, position_budget=0.01, length_budget=0.01, area_budget=0.01
        )
        commands.extend(packet["commands"] if not commands else packet["commands"][1:])
    commands.append(["Z"])
    assert certify_native_region_topology(commands).status == "VALID"
    # The checked whole semantic partition can use the original curve instead.
    whole = semantic_reference_curves(profile_for(h), {"root": h}, ["root"])
    original = whole["curves"][0]
    assert (
        certify_region_topology((original, Curve(original.end, original.start))).status == "VALID"
    )


def test_a_restricted_view_cannot_silently_become_a_rounded_new_curve_source():
    v = view(history()).restricted(Q(1, 3), 1)
    with pytest.raises(ValueError, match="EXPLICIT_ROOT_SOURCE_AND_PARAMETER_INTERVAL"):
        CurveSource.from_curve(v)
    assert v.root_source == arc() and v.parameter_interval == (Q(1, 3), Q(1))


@pytest.mark.parametrize("field", ["start", "end", "data"])
def test_float_cache_boolean_is_rejected_even_when_equal_to_a_coordinate(field):
    reference = source_reference(history("cubic"), "root")
    cache = canonical_projection(reference)
    if field == "data":
        cache["data"]["control1"][0] = False
    else:
        cache[field][1] = False
    with pytest.raises(SourceViewError):
        validate_projection(reference, **cache)


def test_original_net_body_area_keeps_holes_and_one_scale_without_float_cache():
    def rectangle(x, y, w, h):
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        return tuple(Curve(a, b) for a, b in zip(points, points[1:] + points[:1]))

    body = rectangle(0, 0, 100, 80)
    hole = rectangle(20, 20, 20, 30)
    result = source_region_area_bounds(body, [hole], scale=Q(1, 10))
    assert result["area_lower_exact"] == result["area_upper_exact"] == "74"
    assert result["area_basis"] == "ORIGINAL_NET_BODY_MINUS_HOLES_WITHOUT_TABS"
    with pytest.raises(SourceViewError, match="budget"):
        source_region_area_bounds(body, [hole], max_curves=4)


def test_retired_cubic_split_vertex_remains_the_exact_interior_source_point_after_merge():
    h = history("cubic").split("root", Q(1, 3), "left", "right")
    reference = SourcePointReference("retired-cubic-vertex", "profile", "root", Q(1, 3))
    shared = historical_point(h, reference)
    assert shared["status"] == "SHARED_POINT"
    expected = ((Q(28, 27), Q(28, 27)), (Q(8, 3), Q(8, 3)))
    assert shared["nominal_bounds_exact"] == expected
    merged = h.merge(["left", "right"], "merged")
    retired = historical_point(merged, reference)
    assert retired["status"] == "SINGLE" and retired["nominal_bounds_exact"] == expected
