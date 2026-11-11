"""Independent geometry/algebra and source-reference oracles for AU13 math."""

import json
import math
from copy import deepcopy
from fractions import Fraction as Q

import pytest

from archpapercraft.authoring.curve_subdivision import (
    CurveSource,
    CurveSubdivisionHistory,
    SourcePointReference,
    TrimReference,
)
from archpapercraft.authoring.curves import Curve


def line():
    return CurveSource("line", (0, 0), (120, 40))


def cubic():
    # Independent power oracle: x=12t^2-8t^3, y=12t-12t^2.
    return CurveSource("cubic", (0, 0), (4, 0), ((0, 4), (4, 4)))


def arc(sweep=180):
    return CurveSource("arc", (20, 0), (-20, 0), center=(0, 0), sweep_deg=sweep)


def history(source=None):
    return CurveSubdivisionHistory("profile", "original", source or line())


def trim(segment_id="original", start=0, end=1, profile_id="profile"):
    return TrimReference("stable-trim-id", profile_id, segment_id, start, end)


def uses(result):
    return [(use.piece_id, use.start, use.end) for use in result.uses]


def power_coefficients(points):
    # Direct Bernstein -> power identity, independent of de Casteljau code.
    return tuple(
        (p0, 3 * (p1 - p0), 3 * (p0 - 2 * p1 + p2), -p0 + 3 * p1 - 3 * p2 + p3)
        for p0, p1, p2, p3 in zip(*points)
    )


@pytest.mark.parametrize(
    "a,b", [(Q(0), Q(1, 3)), (Q(1, 3), Q(7, 8)), (Q(7, 8), Q(1)), (Q(7, 8), Q(1, 3))]
)
def test_cubic_restriction_is_whole_polynomial_identity(a, b):
    # Expanding the known source polynomial at a+(b-a)t proves all t,
    # rather than accepting an agreement at display tessellation samples.
    d = b - a
    expected = (
        (12 * a**2 - 8 * a**3, (24 * a - 24 * a**2) * d, (12 - 24 * a) * d**2, -8 * d**3),
        (12 * a - 12 * a**2, (12 - 24 * a) * d, -12 * d**2, Q(0)),
    )
    assert power_coefficients(cubic().controls_on(a, b)) == expected


@pytest.mark.parametrize("split", [Q(1, 2), Q(1, 3), Q(999, 1000)])
def test_line_restrictions_exact_and_source_input_unchanged(split):
    old = history()
    child = old.split("original", split, "left", "right")
    p = (120 * split, 40 * split)
    assert child.pieces[0].controls_exact() == ((Q(0), Q(0)), p)
    assert child.pieces[1].controls_exact() == (p, (Q(120), Q(40)))
    assert old.pieces[0].controls_exact() == ((Q(0), Q(0)), (Q(120), Q(40)))
    assert old.to_dict()["events"] == []


def test_nested_split_maps_original_and_child_intervals_without_index_fallback():
    state = history().split("original", Q(1, 3), "left", "right")
    state = state.split("right", Q(1, 4), "middle", "end")
    result = state.resolve(trim(start=Q(1, 6), end=Q(3, 4)))
    assert result.status == "CHAIN"
    assert uses(result) == [("left", Q(1, 2), Q(1)), ("middle", Q(0), Q(1)), ("end", Q(0), Q(1, 2))]
    assert uses(state.resolve(trim("right", 0, Q(1, 2)))) == [
        ("middle", Q(0), Q(1)),
        ("end", Q(0), Q(1, 3)),
    ]


def test_oriented_trim_reverse_preserves_every_child_and_exact_local_direction():
    state = history().split("original", Q(1, 3), "left", "right")
    result = state.resolve(trim(start=Q(5, 6), end=Q(1, 6)))
    assert result.status == "CHAIN"
    assert uses(result) == [("right", Q(3, 4), Q(0)), ("left", Q(1), Q(1, 2))]
    assert result.reference.id == "stable-trim-id"


def test_trim_at_split_boundary_is_nonzero_interval_not_ambiguous_point_choice():
    state = history().split("original", Q(1, 3), "left", "right")
    assert uses(state.resolve(trim(start=Q(1, 3), end=1))) == [("right", Q(0), Q(1))]
    with pytest.raises(ValueError, match="nonempty"):
        trim(start=Q(1, 3), end=Q(1, 3))


def test_one_to_many_legacy_joint_is_explicit_unresolved_and_keeps_all_candidates():
    state = history().split("original", Q(1, 3), "left", "right")
    result = state.resolve(trim(), require_single=True)
    assert result.status == "UNRESOLVED"
    assert result.reason == "ONE_TO_MANY_NOT_SUPPORTED"
    assert uses(result) == [("left", Q(0), Q(1)), ("right", Q(0), Q(1))]
    assert result.reference == trim()


@pytest.mark.parametrize(
    "reference,reason",
    [
        (trim("unrelated"), "SOURCE_NOT_COVERED"),
        (trim(profile_id="another-profile"), "PROFILE_ID_MISMATCH"),
    ],
)
def test_unknown_qualified_source_never_aliases_same_name_or_nearest(reference, reason):
    result = history().split("original", Q(1, 2), "left", "right").resolve(reference)
    assert result.status == "UNRESOLVED"
    assert result.reason == reason


@pytest.mark.parametrize("source", [line(), cubic(), arc(), arc(-180)])
def test_inverse_merge_recovers_exact_source_and_historical_descendant_references(source):
    state = history(source).split("original", Q(2, 7), "left", "right")
    merged = state.merge(("left", "right"), "merged")
    assert merged.pieces[0].source == source
    assert merged.pieces[0].source_start == 0
    assert merged.pieces[0].source_end == 1
    assert uses(merged.resolve(trim())) == [("merged", Q(0), Q(1))]
    assert uses(merged.resolve(trim("left"))) == [("merged", Q(0), Q(2, 7))]
    assert uses(merged.resolve(trim("right", Q(1), Q(0)))) == [("merged", Q(1), Q(2, 7))]


def test_partial_merge_retains_subspan_lineage_then_second_split_composes_exactly():
    state = history().split("original", Q(1, 3), "left", "rest")
    state = state.split("rest", Q(1, 2), "middle", "right")
    state = state.merge(("left", "middle"), "two-thirds")
    assert uses(state.resolve(trim("middle"))) == [("two-thirds", Q(1, 2), Q(1))]
    state = state.split("two-thirds", Q(3, 4), "new-a", "new-b")
    assert uses(state.resolve(trim("middle"))) == [("new-a", Q(2, 3), Q(1)), ("new-b", Q(0), Q(1))]
    assert state.resolve(trim()).status == "CHAIN"


def test_edit_blocks_old_inverse_merge_even_if_new_shape_is_collinear():
    state = history().split("original", Q(1, 2), "left", "right")
    # Same geometric line but a new source generation: no unverified merge.
    changed = state.edit("left", CurveSource("line", (0, 0), (60, 20)))
    with pytest.raises(ValueError, match="same unedited"):
        changed.merge(("left", "right"), "forbidden")
    assert uses(changed.resolve(trim(start=0, end=Q(1, 2)))) == [("left", Q(0), Q(1))]
    new = changed.split("left", Q(1, 5), "new-a", "new-b")
    restored_edit = new.merge(("new-a", "new-b"), "edited-merged")
    assert restored_edit.pieces[0].source == changed.pieces[0].source
    assert restored_edit.resolve(trim()).status == "CHAIN"


@pytest.mark.parametrize(
    "ids", [("right", "left"), ("left", "left"), ("left", "unknown"), ("original", "right")]
)
def test_unordered_duplicate_missing_and_retired_merge_inputs_rejected(ids):
    state = history().split("original", Q(1, 2), "left", "right")
    with pytest.raises(ValueError):
        state.merge(ids, "merged")


@pytest.mark.parametrize("left,right", [("same", "same"), ("original", "new"), ("", "right")])
def test_id_collision_never_creates_alias(left, right):
    state = history()
    with pytest.raises(ValueError):
        state.split("original", Q(1, 2), left, right)
    assert len(state.pieces) == 1


def test_retired_id_reuse_rejected_after_merge():
    state = history().split("original", Q(1, 2), "left", "right")
    state = state.merge(("left", "right"), "merged")
    with pytest.raises(ValueError, match="retired"):
        state.split("merged", Q(1, 2), "left", "fresh")


@pytest.mark.parametrize("sweep", [180, -180])
def test_arc_exact_sweep_restriction_and_analytic_quarter_endpoint(sweep):
    state = history(arc(sweep)).split("original", Q(1, 2), "left", "right")
    assert [piece.sweep_deg_exact for piece in state.pieces] == [sweep / 2, sweep / 2]
    x, y = state.pieces[0].point_bounds(1)
    assert x[0] <= 0 <= x[1]
    assert y[0] <= (20 if sweep > 0 else -20) <= y[1]
    # The reused certified trigonometric helper has a global |angle|<7
    # Taylor remainder, rather than a quarter-circle-specific exact shortcut.
    assert max(x[1] - x[0], y[1] - y[0]) < Q(1, 10**40)
    assert state.pieces[1].point_bounds(0) == (x, y)
    # Retaining the parent analytic source avoids cumulative radius drift.
    assert state.pieces[0].source is state.pieces[1].source


def test_arc_chord_axis_counterexample_requires_original_trim_span():
    state = history(arc()).split("original", Q(1, 2), "left", "right")
    original_axis = math.atan2(0, -40)
    child_axis = math.atan2(20, -20)
    assert math.degrees(original_axis - child_axis) == pytest.approx(45)
    # Semantic axis endpoints remain the ORIGINAL full-span chord even after
    # topology split. The application must evaluate both ends of this chain.
    result = state.resolve(trim())
    first, last = state.pieces[0].point_bounds(0), state.pieces[-1].point_bounds(1)
    assert result.status == "CHAIN"
    assert first[0][0] <= 20 <= first[0][1]
    assert last[0][0] <= -20 <= last[0][1]


def test_arc_authored_endpoint_roundoff_is_retained_not_claimed_exact_analytic_end():
    source = CurveSource("arc", (20, 0), (-20, Q(1, 10**8)), center=(0, 0), sweep_deg=180)
    state = history(source).split("original", Q(1, 3), "left", "right")
    assert state.pieces[-1].source.end[1] == Q(1, 10**8)
    nominal_y = state.pieces[-1].point_bounds(1)[1]
    assert nominal_y[0] <= 0 <= nominal_y[1]
    assert not nominal_y[0] <= source.end[1] <= nominal_y[1]
    assert state.merge(("left", "right"), "merged").pieces[0].source == source


def test_planar_wall_frame_all_points_survive_split_chain_page_transform():
    # Independent fixed-root metric: page 2, [60,60], 30deg, .01 model->paper.
    # Keeping a full-span trim gives exactly the same mathematical frame.
    state = history().split("original", Q(1, 3), "left", "right")
    state = state.split("right", Q(1, 2), "middle", "end")
    mapping = state.resolve(trim())
    assert mapping.status == "CHAIN"
    start = state.pieces[0].point_bounds(0)
    end = state.pieces[-1].point_bounds(1)
    assert tuple(v[0] for v in start) == (0, 0)
    assert tuple(v[0] for v in end) == (120, 40)

    def page(points, origin, axis):
        theta = math.radians(30) - math.atan2(axis[1], axis[0])
        return [
            (
                60 + 0.01 * ((x - origin[0]) * math.cos(theta) - (y - origin[1]) * math.sin(theta)),
                60 + 0.01 * ((x - origin[0]) * math.sin(theta) + (y - origin[1]) * math.cos(theta)),
            )
            for x, y in points
        ]

    wall_points = [(0, 0), (120, 40), (100, 100), (-20, 60)]
    assert page(wall_points, (0, 0), (120, 40)) == page(
        wall_points, tuple(v[0] for v in start), tuple(v[0] for v in end)
    )


def test_json_roundtrip_replays_ancestry_edit_and_trim_identity_without_caches():
    state = history(cubic()).split("original", Q(1, 3), "left", "right")
    state = state.edit("left", cubic()).split("left", Q(2, 7), "a", "b")
    state = state.merge(("a", "b"), "edited-merged")
    raw = json.loads(json.dumps(state.to_dict()))
    restored = CurveSubdivisionHistory.from_dict(raw)
    assert restored.pieces == state.pieces
    assert restored.to_dict() == raw
    reference = TrimReference.from_dict(json.loads(json.dumps(trim().to_dict())))
    assert restored.resolve(reference) == state.resolve(trim())
    raw["source"]["start"][0] = "100"
    assert restored.pieces == state.pieces


@pytest.mark.parametrize("mutation", ["future", "unknown", "event", "cache", "duplicate"])
def test_replay_rejects_future_unknown_forged_or_aliased_history(mutation):
    raw = history().split("original", Q(1, 2), "left", "right").to_dict()
    if mutation == "future":
        raw["schema"] = 2
    elif mutation == "unknown":
        raw["extra"] = 1
    elif mutation == "event":
        raw["events"].append(["pretend_merge", "left", "right"])
    elif mutation == "cache":
        raw["pieces"] = [{"id": "forged", "parent": "original"}]
    else:
        raw["events"].append(["split", "left", "1/2", "right", "fresh"])
    with pytest.raises(ValueError):
        CurveSubdivisionHistory.from_dict(raw)


def test_detached_curve_input_and_nested_outputs_are_immutable():
    data = {"control1": [0, 4], "control2": [4, 4]}
    curve = Curve((0, 0), (4, 0), "cubic", data)
    source = CurveSource.from_curve(curve)
    state = history(source)
    before = deepcopy(state.to_dict())
    data["control1"][0] = 999
    output = state.to_dict()
    output["source"]["controls"][0][0] = "999"
    assert state.to_dict() == before
    with pytest.raises(AttributeError):
        state._pieces = ()
    with pytest.raises(AttributeError):
        del state._pieces
    with pytest.raises(AttributeError):
        source.start = (1, 2)


@pytest.mark.parametrize("parameter", [0, 1, -1, 2, True, float("nan"), float("inf")])
def test_invalid_split_parameter_rejected_without_mutation(parameter):
    state = history()
    with pytest.raises(ValueError):
        state.split("original", parameter, "left", "right")
    assert state.to_dict()["events"] == []


@pytest.mark.parametrize("source", [line(), arc(), cubic()])
def test_anchor_at_split_is_proven_shared_material_point_not_arbitrary_owner(source):
    state = history(source).split("original", Q(1, 3), "left", "right")
    reference = SourcePointReference("anchor-id", "profile", "original", Q(1, 3))
    result = state.resolve_point(reference)
    assert result.status == "SHARED_POINT"
    assert [(use.piece_id, use.parameter) for use in result.uses] == [
        ("left", Q(1)),
        ("right", Q(0)),
    ]
    reference = SourcePointReference.from_dict(json.loads(json.dumps(reference.to_dict())))
    merged = state.merge(("left", "right"), "merged")
    result = merged.resolve_point(reference)
    assert result.status == "SINGLE"
    assert [(use.piece_id, use.parameter) for use in result.uses] == [("merged", Q(1, 3))]


def test_edited_boundary_remains_unresolved_despite_coincident_float_endpoints():
    state = history().split("original", Q(1, 2), "left", "right")
    state = state.edit("left", CurveSource("line", (0, 0), (60, 20)))
    reference = SourcePointReference("anchor-id", "profile", "original", Q(1, 2))
    result = state.resolve_point(reference)
    assert result.status == "UNRESOLVED"
    assert result.reason == "AMBIGUOUS_MATERIAL_POINT"
    assert len(result.uses) == 2


@pytest.mark.parametrize(
    "reference,reason",
    [
        (SourcePointReference("anchor", "different", "original", 0), "PROFILE_ID_MISMATCH"),
        (SourcePointReference("anchor", "profile", "missing", 0), "SOURCE_NOT_COVERED"),
    ],
)
def test_point_reference_requires_qualified_actual_source(reference, reason):
    result = history().resolve_point(reference)
    assert result.status == "UNRESOLVED"
    assert result.reason == reason


def test_replay_work_budget_is_explicit_and_keeps_prior_history(monkeypatch):
    import archpapercraft.authoring.curve_subdivision as module

    monkeypatch.setattr(module, "_MAX_EVENTS", 1)
    state = history().split("original", Q(1, 2), "left", "right")
    with pytest.raises(ValueError, match="work budget"):
        state.merge(("left", "right"), "merged")
    assert [piece.id for piece in state.pieces] == ["left", "right"]


@pytest.mark.parametrize(
    "source",
    [
        {
            "kind": "line",
            "start": [0, 0],
            "end": [1, 1],
            "controls": [],
            "center": [],
            "sweep_deg": "0",
            "parent": "invented",
        },
        {
            "kind": "line",
            "start": [0, 0],
            "end": [float("nan"), 1],
            "controls": [],
            "center": [],
            "sweep_deg": "0",
        },
    ],
)
def test_malformed_source_not_tolerated_as_provenance(source):
    with pytest.raises(ValueError):
        CurveSource.from_dict(source)
