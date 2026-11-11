"""Live LINE split/rejoin: semantic anchors, attached edges and persistence."""

import copy
import json
from fractions import Fraction

import numpy as np
import pytest
from test_curve_bend import wall_base
from test_interior import wall_roof
from test_paper import two_panels

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import (
    AuthorProject,
    ProjectFormatError,
    ValidationError,
    load_project,
)
from archpapercraft.authoring.attachments import edge_source
from archpapercraft.authoring.geometry import page_points


def test_mixed_part_axis_split_merge_preserves_all_original_wall_coordinates_and_locks(tmp_path):
    project, wall, roof, wall_edge, roof_edge = two_panels()
    pid = project.part_for_surface(wall)
    joint = project.connect_edges(wall, wall_edge, roof, roof_edge)
    project.set_joint(joint, mode="fold", receiving_part_id=pid)
    page = project.add_page()
    project.set_placement(pid, page, 60, 60, 30, position_locked=True, rotation_locked=True)
    profile = project.profiles[project.surfaces[wall].profile_id]
    old_vertices = [vertex.id for vertex in profile.vertices]
    axis = project.parts[pid].frame.axis_segment_id
    frame, layout = copy.deepcopy(project.parts[pid].frame), copy.deepcopy(project.placements[pid])
    before = page_points(project.parts[pid].polygons[wall][0], layout)
    controller = AuthorController()
    controller.project = project
    split = controller.execute(
        "Rozdělit hranu", lambda p: p.split_profile_segment(profile.id, axis, Fraction(1, 3))
    )
    assert controller.project.parts[pid].stale
    assert controller.project.parts[pid].frame == frame
    controller.recompute()
    current = controller.project
    assert current.parts[pid].frame == frame and current.placements[pid] == layout
    actual = page_points(current.parts[pid].polygons[wall][0], layout)
    # Boundary subdivision adds one vertex. Every authored original vertex
    # remains the same page point; compare source IDs rather than list indices.
    for index, vertex_id in enumerate(old_vertices):
        position = next(
            i for i, v in enumerate(current.profiles[profile.id].vertices) if v.id == vertex_id
        )
        np.testing.assert_array_equal(actual[position], before[index])
    controller.execute(
        "Spojit původní úseky", lambda p: p.merge_profile_segments(profile.id, split["segment_ids"])
    )
    controller.recompute()
    np.testing.assert_array_equal(
        page_points(controller.project.parts[pid].polygons[wall][0], layout), before
    )
    assert controller.project.parts[pid].frame == frame
    target = tmp_path / "mixed-subdivision.apcraft"
    controller.save(target)
    controller.open(target)
    assert controller.project.to_dict() == load_project(target).to_dict()
    np.testing.assert_array_equal(
        page_points(controller.project.parts[pid].polygons[wall][0], layout), before
    )


def test_divide_actual_joined_edge_keeps_one_joint_id_and_no_extra_fold():
    project, wall, roof, first, second = two_panels()
    pid = project.part_for_surface(wall)
    joint = project.connect_edges(wall, first, roof, second)
    project.set_joint(joint, mode="fold", receiving_part_id=pid)
    profile = project.profiles[project.surfaces[wall].profile_id]
    before = edge_source(project, wall, first)[2]
    split = project.split_profile_segment(profile.id, first, Fraction(2, 7))
    assert list(project.joints) == [joint] and not project.joints[joint].unresolved
    np.testing.assert_array_equal(edge_source(project, wall, first)[2], before)
    project.recompute()
    assert len(project.parts[pid].paths["GUIDES"]) == 1
    assert all(
        project.profile_edge_overlap(profile.id, first, item) for item in split["segment_ids"]
    )


def test_interior_trace_split_keeps_interval_receiver_and_connector_ids():
    project, wall, roof, edge = wall_roof()
    aid = project.attach_edge_to_surface(wall, edge, roof)
    before = copy.deepcopy(project.attachments[aid])
    geometry = project.attachment_geometry(aid)
    profile = project.profiles[project.surfaces[wall].profile_id]
    split = project.split_profile_segment(profile.id, edge, Fraction(1, 3))
    project.recompute()
    assert project.attachments[aid] == before
    assert project.attachment_geometry(aid) == geometry
    project.merge_profile_segments(profile.id, split["segment_ids"])
    project.recompute()
    assert project.attachments[aid] == before
    assert project.attachment_geometry(aid) == geometry


def test_retired_split_vertex_remains_a_semantic_anchor_after_inverse_merge():
    project, wall, _, _, _ = two_panels()
    profile = project.profiles[project.surfaces[wall].profile_id]
    pid = project.part_for_surface(wall)
    split = project.split_profile_segment(profile.id, profile.segments[0].id, Fraction(1, 3))
    project.recompute()
    project.set_anchor(pid, wall, split["vertex_id"], split["segment_ids"][0])
    expected = copy.deepcopy(project.parts[pid].polygons)
    project.merge_profile_segments(profile.id, split["segment_ids"])
    project.recompute()
    np.testing.assert_array_equal(
        project.parts[pid].polygons[wall][0],
        [point for i, point in enumerate(expected[wall][0]) if i != 1],
    )
    assert project.parts[pid].frame.anchor_vertex_id == split["vertex_id"]
    assert AuthorProject.from_dict(project.to_dict()).to_dict() == project.to_dict()


def test_edit_split_joined_chain_bends_reference_and_stays_saveable_unresolved():
    project, wall, roof, first, second = two_panels()
    joint = project.connect_edges(wall, first, roof, second)
    profile = project.profiles[project.surfaces[wall].profile_id]
    split = project.split_profile_segment(profile.id, first)
    project.recompute()
    project.move_vertex(profile.id, split["vertex_id"], [11000, 2000])
    assert project.joints[joint].unresolved
    with pytest.raises(ValidationError, match="REFERENCE_UNRESOLVED"):
        edge_source(project, wall, first)
    before = project.to_dict()
    assert AuthorProject.from_dict(before).to_dict() == before
    with pytest.raises(ValidationError):
        project.snapshot()
    with pytest.raises(ValidationError):
        project.merge_profile_segments(profile.id, split["segment_ids"])
    assert project.to_dict() == before


@pytest.mark.parametrize("damage", ["point", "incidence", "geometry", "alias", "cache"])
def test_replay_bound_project_rejects_mutated_incidence_or_active_geometry(damage):
    project, wall, _, _, _ = two_panels()
    profile = project.profiles[project.surfaces[wall].profile_id]
    original = profile.segments[0].id
    split = project.split_profile_segment(profile.id, original)
    raw = project.to_dict()
    record = raw["profile_subdivisions"][original]
    if damage == "point":
        record["points"][split["vertex_id"]][1] = "1/3"
    elif damage == "incidence":
        record["edges"][split["segment_ids"][0]][0] = record["edges"][original][1]
    elif damage == "geometry":
        raw["profiles"][profile.id]["vertices"][1]["point"][0] += 1
    elif damage == "alias":
        record["history"]["events"][0][3] = raw["project_id"]
    else:
        record["children"] = []
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(json.loads(json.dumps(raw)))


@pytest.mark.parametrize("parameter", [False, True, 0, 1, -0.1, float("nan")])
def test_invalid_live_split_is_atomic(parameter):
    project, wall, _, _, _ = two_panels()
    profile = project.profiles[project.surfaces[wall].profile_id]
    before = project.to_dict()
    with pytest.raises(ValidationError):
        project.split_profile_segment(profile.id, profile.segments[0].id, parameter)
    assert project.to_dict() == before


def test_replacing_profile_does_not_resurrect_old_anchor_from_detached_history():
    project, wall, _, _, _ = two_panels()
    profile = project.profiles[project.surfaces[wall].profile_id]
    project.split_profile_segment(profile.id, profile.segments[0].id)
    project.recompute()
    project.update_profile(profile.id, [[0, 0], [2000, 0], [2000, 2000], [0, 2000]])
    before = project.to_dict()
    with pytest.raises(ValidationError, match="UNRESOLVED"):
        project.recompute()
    assert project.to_dict() == before
    assert AuthorProject.from_dict(before).to_dict() == before


def test_schema5_known_copy_keeps_source_layout_and_origin_bytes(tmp_path):
    import hashlib

    project, wall, _, _, _ = two_panels()
    pid = project.part_for_surface(wall)
    project.set_placement(
        pid, project.pages[0].id, 45, 70, 17, position_locked=True, rotation_locked=True
    )
    raw = project.to_dict()
    raw.pop("profile_subdivisions")
    raw.update(schema_version=5, writer_version="0.3.0-pc008-segmented-variants-experimental")
    origin = tmp_path / "v5.apcraft"
    origin.write_text(json.dumps(raw), encoding="utf8")
    before = hashlib.sha256(origin.read_bytes()).hexdigest()
    restored = load_project(origin)
    assert restored.requires_save_as and restored.loaded_from_schema == 5
    assert restored.profiles == project.profiles and restored.placements == project.placements
    assert restored.parts == project.parts and restored.profile_subdivisions == {}
    restored.save(tmp_path / "v7-copy.apcraft")
    assert hashlib.sha256(origin.read_bytes()).hexdigest() == before
    assert load_project(tmp_path / "v7-copy.apcraft").to_dict() == restored.to_dict()


def test_undo_redo_preserves_created_vertex_child_ids_and_retired_provenance():
    project, wall, _, _, _ = two_panels()
    profile = project.profiles[project.surfaces[wall].profile_id]
    controller = AuthorController()
    controller.project = project
    before = project.to_dict()
    controller.execute(
        "Dělení", lambda p: p.split_profile_segment(profile.id, profile.segments[0].id)
    )
    changed = controller.project.to_dict()
    controller.undo()
    assert controller.project.to_dict() == before
    controller.redo()
    assert controller.project.to_dict() == changed


@pytest.mark.parametrize("known", [False, True])
def test_existing_tab_bend_uses_whole_semantic_hinge_after_source_split(known):
    project, connector_id, wall, _ = wall_base(known=known)
    aid = project.connectors[connector_id].attachment_id
    profile = project.profiles[project.surfaces[wall].profile_id]
    original = copy.deepcopy(project.connectors[connector_id])
    before = project.connector_bend_clearance(connector_id)
    contact = project._connector_geometry(connector_id)
    key = project._assembly_clearance_key()
    project.split_profile_segment(profile.id, profile.segments[0].id, Fraction(1, 3))
    assert project._assembly_clearance_key() != key
    after = project.connector_bend_clearance(connector_id)
    assert after["status"] == before["status"]
    assert project._connector_geometry(connector_id) == contact
    assert project.connectors[connector_id] == original
    assert project.attachments[aid].source_edge_id not in {s.id for s in profile.segments}


def test_large_coordinates_reject_out_of_budget_projection_atomically():
    project = AuthorProject.new(scale=1)
    pid = project.add_profile([[1e16, 0], [1e16 + 4, 3]], closed=False)
    before = project.to_dict()
    with pytest.raises(ValidationError, match="SOURCE_PRECISION_UNRESOLVED"):
        project.split_profile_segment(pid, project.profiles[pid].segments[0].id, Fraction(1, 4))
    assert project.to_dict() == before


def test_subbudget_rounding_is_not_a_false_exact_physical_hinge():
    project = AuthorProject.new(scale=1 / 1024)
    pid = project.add_profile([[1e16, 0], [1e16 + 4, 3]], closed=False)
    original = project.profiles[pid].segments[0].id
    project.split_profile_segment(pid, original, Fraction(1, 4))
    with pytest.raises(ValidationError, match="REFERENCE_UNRESOLVED.*zaokrouhlen"):
        project.resolve_profile_edge(pid, original)
    # The semantic paper axis is a coordinate convention, not a hinge proof.
    _, points = project.resolve_profile_edge(pid, original, axis=True)
    np.testing.assert_array_equal(points, [[1e16, 0], [1e16 + 4, 3]])


def test_global_projection_length_budget_is_not_reissued_to_each_history():
    project = AuthorProject.new(scale=1 / 1024)
    points = [point for i in range(6) for point in ([1e16 + 8 * i, 0], [1e16 + 8 * i + 4, 3])]
    pid = project.add_profile(points, closed=False)
    originals = [edge.id for edge in project.profiles[pid].segments[::2]]
    for edge_id in originals[:5]:
        project.split_profile_segment(pid, edge_id, Fraction(1, 4))
    before = project.to_dict()
    # Every individual point error=1/1024 paper mm; the whole-profile length
    # deficit bound6*2/1024 exceeds.01, while5*2/1024 remains below it.
    with pytest.raises(ValidationError, match="SOURCE_PRECISION_UNRESOLVED"):
        project.split_profile_segment(pid, originals[5], Fraction(1, 4))
    assert project.to_dict() == before


def test_connected_oblique_rounding_rejects_split_but_exact_midpoint_keeps_join():
    project = AuthorProject.new(scale=1)
    first = project.add_profile([[0, 0], [120, 40], [100, 100], [-20, 60]])
    second = project.add_profile([[0, 0], [-20, -60], [100, -20], [120, 40]])
    a, b = project.add_surface(first), project.add_surface(second)
    edge = project.profiles[first].segments[0].id
    joint = project.connect_edges(a, edge, b, project.profiles[second].segments[3].id)
    before = project.to_dict()
    with pytest.raises(ValidationError, match="REFERENCE_UNRESOLVED.*zaokrouhlen"):
        project.split_profile_segment(first, edge, Fraction(1, 3))
    assert project.to_dict() == before
    project.split_profile_segment(first, edge, Fraction(1, 2))
    assert not project.joints[joint].unresolved
    project.recompute()


@pytest.mark.parametrize("alias_kind", ["vertex", "edge"])
def test_retired_points_cannot_alias_another_profile_or_historical_edge(alias_kind):
    project, wall, roof, _, _ = two_panels(scale=1)
    records = []
    for sid in (wall, roof):
        profile = project.profiles[project.surfaces[sid].profile_id]
        root = profile.segments[0].id
        split = project.split_profile_segment(profile.id, root)
        project.merge_profile_segments(profile.id, split["segment_ids"])
        project.recompute()
        records.append((root, split))
    raw = project.to_dict()
    alias = records[0][1]["vertex_id"] if alias_kind == "vertex" else records[0][0]
    old = records[1][1]["vertex_id"]
    record = raw["profile_subdivisions"][records[1][0]]
    record["points"][alias] = record["points"].pop(old)
    for ends in record["edges"].values():
        ends[:] = [alias if value == old else value for value in ends]
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


@pytest.mark.parametrize("parameter", ["1/0", "nan", "inf"])
def test_malformed_history_fraction_has_typed_format_failure(parameter):
    project, wall, _, _, _ = two_panels()
    profile = project.profiles[project.surfaces[wall].profile_id]
    root = profile.segments[0].id
    project.split_profile_segment(profile.id, root)
    raw = project.to_dict()
    raw["profile_subdivisions"][root]["history"]["events"][0][2] = parameter
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


def test_closed_body_area_is_not_replaced_by_a_position_or_length_budget():
    project = AuthorProject.new(scale=1 / 1024)
    pid = project.add_profile([[1e16, 0], [1e16 + 2, 2**20], [1e16 + 4, 0]])
    before = project.to_dict()
    # Independent exact shoelace: initial2mm², float-projected split9/4mm².
    with pytest.raises(ValidationError, match="SOURCE_AREA_UNRESOLVED"):
        project.split_profile_segment(pid, project.profiles[pid].segments[0].id, Fraction(1, 4))
    assert project.to_dict() == before


def test_source_edit_keeps_untouched_exact_split_point_and_declares_new_shape():
    project = AuthorProject.new(scale=0.01)
    pid = project.add_profile([[0, 0], [120, 40], [100, 100], [-20, 60]])
    sid = project.add_surface(pid)
    profile = project.profiles[pid]
    root = profile.segments[0].id
    project.split_profile_segment(pid, root, Fraction(1, 3))
    vertex = profile.vertices[0].id
    project.move_vertex(pid, vertex, [-10, 0])
    project.recompute()
    assert not project.parts[project.part_for_surface(sid)].stale
    assert AuthorProject.from_dict(project.to_dict()).to_dict() == project.to_dict()


def test_mixed_arc_profile_keeps_unchanged_curve_terms_in_area_difference():
    project = AuthorProject.new(scale=1)
    pid = project.add_profile(
        segments=[
            {"kind": "line", "start": [0, 0], "end": [20, 0]},
            {
                "kind": "arc",
                "start": [20, 0],
                "end": [20, 20],
                "data": {"center": [20, 10], "sweep_deg": 180},
            },
            {"kind": "line", "start": [20, 20], "end": [0, 20]},
            {"kind": "line", "start": [0, 20], "end": [0, 0]},
        ]
    )
    sid = project.add_surface(pid)
    root = project.profiles[pid].segments[0].id
    project.split_profile_segment(pid, root, Fraction(1, 3))
    project.recompute()
    assert not project.parts[project.part_for_surface(sid)].stale


@pytest.mark.parametrize("operation", ["split", "move"])
def test_hole_edit_preserves_unrelated_outer_edge_join_identity(operation):
    project, wall, roof, first, second = two_panels()
    hole = project.add_profile([[2000, 1000], [4000, 1000], [4000, 2000], [2000, 2000]])
    project.add_hole(wall, hole)
    joint = project.connect_edges(wall, first, roof, second)
    before = copy.deepcopy(project.joints[joint])
    profile = project.profiles[hole]
    if operation == "split":
        project.split_profile_segment(hole, profile.segments[0].id)
    else:
        project.move_vertex(hole, profile.vertices[0].id, [2100, 1100])
    assert project.joints[joint] == before and not project.joints[joint].unresolved
    project.recompute()


def test_three_holes_share_whole_material_body_area_budget():
    project = AuthorProject.new(scale=1 / 8192)
    outer = project.add_profile(
        [
            [1e16 - 16, -(2**20)],
            [1e16 + 64, -(2**20)],
            [1e16 + 64, 3 * 2**20],
            [1e16 - 16, 3 * 2**20],
        ]
    )
    holes = [
        project.add_profile(
            [[1e16 + offset, 0], [1e16 + offset + 2, 2**20], [1e16 + offset + 4, 0]]
        )
        for offset in (0, 16, 32)
    ]
    project.add_surface(outer, holes)
    for pid in holes[:2]:
        project.split_profile_segment(pid, project.profiles[pid].segments[0].id, Fraction(1, 4))
    before = project.to_dict()
    # Each hole's delta1/256mm² is below.01, while the complete body delta
    # 3/256 exceeds it. Body area is <10mm², so original norm is.01mm².
    with pytest.raises(ValidationError, match="SOURCE_AREA_UNRESOLVED"):
        project.split_profile_segment(
            holes[2], project.profiles[holes[2]].segments[0].id, Fraction(1, 4)
        )
    assert project.to_dict() == before
