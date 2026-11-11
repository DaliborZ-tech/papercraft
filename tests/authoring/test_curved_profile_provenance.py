"""Live schema9 commands/source history/loft, not desktop or physical proof."""

import copy
import json
import math
from fractions import Fraction as Q
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.errors import UnsupportedOperationError
from archpapercraft.authoring.profile_curves import source_curve
from archpapercraft.authoring.project import ProjectFormatError
from archpapercraft.exporter.author_export import export_all


def profile(project, kind, *, closed=False, height=0):
    data = (
        {"center": [0, 0], "sweep_deg": 180}
        if kind == "arc"
        else {"control1": [0, 4], "control2": [4, 4]}
    )
    a, b = ([20, 0], [-20, 0]) if kind == "arc" else ([0, 0], [4, 0])
    segments = [{"kind": kind, "start": a, "end": b, "data": data}]
    if closed:
        segments.append({"kind": "line", "start": b, "end": a, "data": {}})
    return project.add_profile(
        segments=segments,
        closed=closed,
        plane={"origin": [0, 0, height], "u": [1, 0, 0], "v": [0, 1, 0]},
    )


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_live_split_inverse_merge_keeps_source_geometry_and_saved_references(tmp_path, kind):
    p = AuthorProject.new(scale=0.1)
    pid = profile(p, kind, closed=True)
    sid = p.add_surface(pid)
    part_id = p.part_for_surface(sid)
    p.set_placement(part_id, p.pages[0].id, 40, 50, 17, position_locked=True, rotation_locked=True)
    frame, layout = copy.deepcopy(p.parts[part_id].frame), copy.deepcopy(p.placements[part_id])
    root = p.profiles[pid].segments[0].id
    cut = p.split_profile_segment(pid, root, Q(1, 3))
    assert all(s.source_reference is not None for s in p.profiles[pid].segments[:2])
    for s in p.profiles[pid].segments[:2]:
        v = source_curve(p.profiles[pid], s)
        if kind == "arc":
            assert v.radius_bounds()[0] <= 20 <= v.radius_bounds()[1]
    p.recompute()
    source = tmp_path / "split.apcraft"
    p.save(source)
    raw = source.read_bytes()
    reopened = load_project(source)
    assert reopened.to_dict() == p.to_dict()
    reopened.merge_profile_segments(pid, cut["segment_ids"])
    reopened.recompute()
    assert reopened.parts[part_id].frame == frame and reopened.placements[part_id] == layout
    assert reopened.resolve_profile_vertex(pid, cut["vertex_id"])
    assert source.read_bytes() == raw


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_live_one_sided_loft_split_keeps_original_patch_phi_and_vector_output(tmp_path, kind):
    p = AuthorProject.new(scale=0.1)
    a, b = profile(p, kind), profile(p, kind, height=10)
    x, y = p.profiles[a].segments[0].id, p.profiles[b].segments[0].id
    sid = p.add_loft(a, b, correspondences=[{"first_segment_id": x, "second_segment_id": y}])
    part = p.part_for_surface(sid)
    params = copy.deepcopy(p.surfaces[sid].params)
    before = p.loft_status(sid)["flattening"]
    p.set_placement(part, p.pages[0].id, 40, 50, 17, position_locked=True, rotation_locked=True)
    cut = p.split_profile_segment(a, x, Q(1, 3))
    assert p.surfaces[sid].params == params and len(p.profiles[b].segments) == 1
    p.recompute()
    after = p.loft_status(sid)
    assert after["status"] == "EXACT" and after["flattening"] == before
    assert len(after["patches"]) == 1
    saved = tmp_path / "loft.apcraft"
    p.save(saved)
    reopened = load_project(saved)
    assert reopened.surfaces[sid].params == params
    for issue in reopened.validate_layout():
        if issue.severity == "warning":
            reopened.acknowledge(issue.id)
    export_all(reopened.snapshot(), tmp_path / "bundle")
    reopened.merge_profile_segments(a, cut["segment_ids"])
    reopened.recompute()
    assert reopened.loft_status(sid)["status"] == "EXACT"
    assert reopened.surfaces[sid].params == params


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_measured_distance_inverse_uses_true_source_length(kind):
    p = AuthorProject.new(scale=0.1)
    pid = profile(p, kind)
    edge = p.profiles[pid].segments[0].id
    length = p.profile_segment_length(pid, edge)
    expected = 20 * math.pi if kind == "arc" else 8
    assert length["lower"] <= expected <= length["upper"]
    distance = expected / 3
    result = p.profile_segment_parameter_at_length(pid, edge, distance, tolerance_model_mm=1e-4)
    parameter = result["parameter"]
    assert type(parameter) is Q and result["actual_error_bound_model_mm"] <= 1e-4
    if kind == "arc":
        assert float(parameter) == pytest.approx(1 / 3, abs=1e-10)
    else:
        # Exact independent source arclength: L(u)=8u³-12u²+12u.
        actual = 8 * parameter**3 - 12 * parameter**2 + 12 * parameter
        assert abs(float(actual) - distance) <= result["actual_error_bound_model_mm"]
        assert abs(float(parameter) - 1 / 3) > 0.02
    split = p.split_profile_segment(pid, edge, parameter)
    assert len(split["segment_ids"]) == 2


def test_known8_copy_rejects_new_field_smuggling_and_keeps_original_bytes(tmp_path):
    p = AuthorProject.new()
    pid = profile(p, "arc")
    raw = p.to_dict()
    raw["schema_version"], raw["writer_version"] = (
        8,
        "0.3.0-pc008-authoring-provenance-experimental",
    )
    for source in raw["profiles"].values():
        for segment in source["segments"]:
            segment.pop("source_reference")
    source = tmp_path / "published8.apcraft"
    source.write_text(json.dumps(raw), encoding="utf-8")
    before = source.read_bytes()
    loaded = load_project(source)
    assert loaded.requires_save_as and loaded.loaded_from_schema == 8
    assert loaded.profiles[pid].segments[0].source_reference is None
    with pytest.raises(UnsupportedOperationError):
        loaded.save(source)
    loaded.save(tmp_path / "copy9.apcraft")
    assert source.read_bytes() == before
    raw["profiles"][pid]["segments"][0]["source_reference"] = None
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_geometry_edit_keeps_historical_loft_unresolved_and_saveable(tmp_path, kind):
    p = AuthorProject.new(scale=0.1)
    a, b = profile(p, kind), profile(p, kind, height=10)
    root = p.profiles[a].segments[0].id
    sid = p.add_loft(
        a,
        b,
        correspondences=[
            {"first_segment_id": root, "second_segment_id": p.profiles[b].segments[0].id}
        ],
    )
    params = copy.deepcopy(p.surfaces[sid].params)
    cut = p.split_profile_segment(a, root, Q(1, 3))
    segment = p.profiles[a].segment(cut["segment_ids"][0])
    data = copy.deepcopy(segment.data)
    if kind == "cubic":
        data["control1"][1] += 0.25
        p.set_profile_segment(a, segment.id, kind=kind, data=data)
    else:
        point = p.profiles[a].vertex(segment.start_vertex_id).point
        p.move_vertex(a, segment.start_vertex_id, [point[0] + 0.25, point[1]])
    assert p.surfaces[sid].params["reference_state"] == "UNRESOLVED"
    assert p.surfaces[sid].params["correspondences"] == params["correspondences"]
    saved = tmp_path / "edited.apcraft"
    p.save(saved)
    q = load_project(saved)
    assert q.to_dict() == p.to_dict()
    with pytest.raises(ValidationError):
        q.snapshot()


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_copy_scales_original_source_once_and_remaps_history_ids(kind):
    p = AuthorProject.new(scale=0.1)
    pid = profile(p, kind)
    root = p.profiles[pid].segments[0].id
    cut = p.split_profile_segment(pid, root, Q(1, 3))
    original = copy.deepcopy(p.to_dict())
    copied = p.copy_profile(pid, factor=1.2)
    assert len(p.profiles[copied].segments) == 2
    assert not (
        {s.id for s in p.profiles[pid].segments} & {s.id for s in p.profiles[copied].segments}
    )
    for segment in p.profiles[copied].segments:
        view = source_curve(p.profiles[copied], segment)
        assert view.profile_id == copied
        if kind == "arc":
            assert view.radius_bounds()[0] <= 24 <= view.radius_bounds()[1]
        else:
            assert view.root_source.controls == ((Q(0), Q(4.8)), (Q(4.8), Q(4.8)))
    assert p.profiles[pid] == AuthorProject.from_dict(original).profiles[pid]
    p.merge_profile_segments(copied, [s.id for s in p.profiles[copied].segments])
    assert len(p.profiles[copied].segments) == 1
    assert p.resolve_profile_vertex(pid, cut["vertex_id"])


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_retired_loft_material_point_and_child_axis_remain_same_chart(tmp_path, kind):
    p = AuthorProject.new(scale=0.1)
    a, b = profile(p, kind), profile(p, kind, height=10)
    root = p.profiles[a].segments[0].id
    sid = p.add_loft(
        a,
        b,
        correspondences=[
            {"first_segment_id": root, "second_segment_id": p.profiles[b].segments[0].id}
        ],
    )
    cut = p.split_profile_segment(a, root, Q(1, 3))
    part_id = p.part_for_surface(sid)
    p.set_anchor(part_id, sid, cut["vertex_id"], cut["segment_ids"][0])
    p.recompute()
    paths = copy.deepcopy(p.parts[part_id].paths)
    frame = copy.deepcopy(p.parts[part_id].frame)
    p.merge_profile_segments(a, cut["segment_ids"])
    p.recompute()
    assert p.parts[part_id].frame == frame and p.parts[part_id].paths == paths
    p.save(tmp_path / "retired-anchor.apcraft")
    q = load_project(tmp_path / "retired-anchor.apcraft")
    assert q.parts[part_id].frame == frame
    q.set_placement(part_id, q.pages[0].id, 50, 60)
    for issue in q.validate_layout():
        if issue.severity == "warning":
            q.acknowledge(issue.id)
    export_all(q.snapshot(), tmp_path / "bundle")


def test_circular_body_and_receiver_split_preserve_retired_source_seam_and_output(tmp_path):
    from test_curved_connector_sources import receiver_source

    p, connector, _ = receiver_source("first")
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    owner = p.surfaces[connector.owner_surface_id]
    receiver = p.surfaces[connector.receiver_surface_id]
    first = owner.profile_id
    root = owner.params["correspondences"][0]["first_segment_id"]
    params = copy.deepcopy(owner.params)
    frame = copy.deepcopy(p.parts[owner.part_id].frame)
    p.recompute()
    p.split_profile_segment(first, root, Q(1, 3))
    p.split_profile_segment(
        receiver.profile_id, p.profiles[receiver.profile_id].segments[0].id, Q(1, 3)
    )
    p.recompute()
    assert owner.params == params and p.parts[owner.part_id].frame == frame
    assert p.curved_connector_status(connector.id)["status"] == "CERTIFIED_APPROXIMATE"
    # Keep separate authored pages and locks; no placement may be silently repacked.
    for index, part in enumerate(p.parts.values()):
        page = p.pages[0].id if index == 0 else p.add_page()
        p.set_placement(part.id, page, 40, 50, position_locked=True, rotation_locked=True)
    p.save(tmp_path / "curved.apcraft")
    q = load_project(tmp_path / "curved.apcraft")
    assert q.to_dict() == p.to_dict()
    for issue in q.validate_layout():
        if issue.severity == "warning":
            q.acknowledge(issue.id)
    export_all(q.snapshot(), tmp_path / "bundle")


@pytest.mark.parametrize(
    "relative",
    [
        "pc006a-desktop-7da2403-run04/own-model.apcraft",
        "pc007a-loft-B1-desktop-a46f179-run01/loft-B1/loft-B1.apcraft",
        "pc008-D-gothic-desktop-e7826dd-run01/D-gothic/D-gothic.apcraft",
        "pc007b-circular-material-67c44ae-run01/cone-first/authored.apcraft",
        "pc008-AU13-line-desktop-24e0801-run05/AU13-line/AU13-line.apcraft",
    ],
)
def test_actual_published_artifacts_load_as_safe_copy_and_keep_authored_work(tmp_path, relative):
    source = Path(__file__).parents[2] / "docs/p2/implementation/evidence" / relative
    before = source.read_bytes()
    original = json.loads(before)
    p = load_project(source)
    assert p.requires_save_as and p.loaded_from_schema == original["schema_version"]
    assert p.segmented_variants == AuthorProject.from_dict(original).segmented_variants
    for part_id, part in p.parts.items():
        archived = original["parts"][part_id]
        assert part.stale  # Actual historical derived capability is explicitly stale.
        assert part.paths == archived["paths"]
        assert vars(part.frame) == archived["frame"]
        assert vars(p.placements[part_id]) == original["placements"][part_id]
    preserved_generations = copy.deepcopy(p.to_dict()["segmented_variants"])
    with pytest.raises(UnsupportedOperationError):
        p.save(source)
    p.save(tmp_path / "copy9.apcraft")
    assert source.read_bytes() == before
    p.recompute()
    assert p.to_dict()["segmented_variants"] == preserved_generations
    for part_id, part in p.parts.items():
        assert vars(part.frame) == original["parts"][part_id]["frame"]
        assert vars(p.placements[part_id]) == original["placements"][part_id]
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    export_all(p.snapshot(), tmp_path / "bundle")
    assert source.read_bytes() == before


@pytest.mark.parametrize("damage", ["cache", "source", "generation", "history", "missing"])
def test_current9_descriptor_is_strict_and_bound_to_replayed_active_piece(damage):
    p = AuthorProject.new()
    pid = profile(p, "arc")
    p.split_profile_segment(pid, p.profiles[pid].segments[0].id, Q(1, 3))
    raw = p.to_dict()
    segment = raw["profiles"][pid]["segments"][0]
    if damage == "cache":
        segment["data"]["sweep_deg"] += 1e-10
    elif damage == "source":
        segment["source_reference"]["source"]["sweep_deg"] = "179"
    elif damage == "generation":
        segment["source_reference"]["generation"] += 1
    elif damage == "history":
        segment["source_reference"]["history_id"] = p.project_id
    else:
        segment.pop("source_reference")
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_repeated_topological_split_keeps_whole_source_and_original_loft_parameter(kind):
    p = AuthorProject.new(scale=0.1)
    a, b = profile(p, kind), profile(p, kind, height=10)
    first, second = p.profiles[a].segments[0].id, p.profiles[b].segments[0].id
    cut = p.split_profile_segment(a, first, Q(1, 3))
    nested = p.split_profile_segment(a, cut["segment_ids"][0], Q(1, 2))
    sid = p.add_loft(
        a, b, correspondences=[{"first_segment_id": first, "second_segment_id": second}]
    )
    assert p.loft_status(sid)["status"] == "EXACT"
    params = copy.deepcopy(p.surfaces[sid].params)
    p.merge_profile_segments(a, nested["segment_ids"])
    p.merge_profile_segments(a, [s.id for s in p.profiles[a].segments])
    p.recompute()
    assert p.loft_status(sid)["status"] == "EXACT"
    assert p.surfaces[sid].params == params
    assert p.parts[p.part_for_surface(sid)].frame.axis_segment_id == first


def test_authored_arc_endpoint_gap_is_preserved_and_bounded_not_repaired(tmp_path):
    p = AuthorProject.new(scale=0.1)
    end = [-20 + 1e-8, 0]
    pid = p.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [20, 0],
                "end": end,
                "data": {"center": [0, 0], "sweep_deg": 180},
            },
            {"kind": "line", "start": end, "end": [20, 0], "data": {}},
        ]
    )
    root = p.profiles[pid].segments[0].id
    cut = p.split_profile_segment(pid, root, Q(1, 3))
    last = source_curve(p.profiles[pid], p.profiles[pid].segment(cut["segment_ids"][1]))
    assert tuple(last.end) == tuple(end)
    assert last.endpoint_gap_bound() > 0
    assert last.root_source.end == tuple(map(Q, end))
    from archpapercraft.authoring.profile_source_views import native_projection_certificate

    certificate = native_projection_certificate(
        last, position_budget=0.01, length_budget=0.01, area_budget=0.01
    )
    assert certificate["status"] == "CERTIFIED"
    # The old authored endpoint gap is a metric bound, never an exact topology
    # or hinge proof. Preserve the valid source document and refuse the surface.
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_surface(pid)
    assert p.to_dict() == before
    p.save(tmp_path / "source-gap.apcraft")
    assert load_project(tmp_path / "source-gap.apcraft").to_dict() == before


def test_generation_hash_legacy_none_normalization_is_detached_and_not_a_descriptor_bypass():
    from dataclasses import asdict

    from archpapercraft.authoring.segmented_surface import _fingerprint, _geometry_binding

    p = AuthorProject.new()
    pid = profile(p, "arc", closed=True)
    sid = p.add_surface(pid)
    binding = {
        "surface": asdict(p.surfaces[sid]),
        "profiles": [asdict(p.profiles[pid])],
        "scale": p.scale,
    }
    original = copy.deepcopy(binding)
    current = _fingerprint(binding)
    legacy = copy.deepcopy(binding)
    for segment in legacy["profiles"][0]["segments"]:
        segment.pop("source_reference")
    assert _fingerprint(legacy) == current
    assert binding == original
    root = p.profiles[pid].segments[0].id
    p.split_profile_segment(pid, root, Q(1, 3))
    qualified = {**binding, "profiles": [asdict(p.profiles[pid])]}
    qualified_original = copy.deepcopy(qualified)
    geometric = _geometry_binding(p.profiles[pid], p.surfaces[sid])
    p.profiles[pid].segments[0].source_reference["generation"] += 1
    assert _geometry_binding(p.profiles[pid], p.surfaces[sid]) != geometric
    altered = copy.deepcopy(qualified)
    altered["profiles"][0]["segments"][0]["source_reference"]["generation"] += 1
    assert _fingerprint(altered) != _fingerprint(qualified)
    assert qualified == qualified_original


@pytest.mark.parametrize("distance", [0, -1, math.nan, math.inf, True, 20 * math.pi])
def test_measured_inverse_rejects_bad_distances_without_geometry_change(distance):
    p = AuthorProject.new()
    pid = profile(p, "arc")
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.profile_segment_parameter_at_length(pid, p.profiles[pid].segments[0].id, distance)
    assert p.to_dict() == before
