import copy
import math

import numpy as np
import pytest

from archpapercraft.authoring import AuthorProject, ProjectFormatError, ValidationError
from archpapercraft.authoring.geometry import page_points


def wall_roof():
    p = AuthorProject.new(scale=0.01)
    wp = p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]], plane="XZ")
    wall = p.add_surface(wp, name="Vlastní stěna")
    root = math.sqrt(0.5)
    rp = p.add_profile(
        [[0, 0], [10800, 0], [10800, math.sqrt(3500**2 * 2)], [0, math.sqrt(3500**2 * 2)]],
        plane={"origin": [-400, -500, 3500], "u": [1, 0, 0], "v": [0, root, root]},
    )
    roof = p.add_surface(rp, name="Střecha s přesahem")
    return p, wall, roof, p.profiles[wp].segments[2].id


def test_analytical_roof_trace_and_asymmetric_overhang_preserve_source_and_layout():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    geometry = p.attachment_geometry(aid)
    assert geometry["valid"]
    np.testing.assert_allclose(
        geometry["target_uv"],
        [[10400, math.sqrt(500**2 * 2)], [400, math.sqrt(500**2 * 2)]],
        atol=1e-9,
    )
    assert geometry["material_length_mm"] == pytest.approx(10000)
    assert p.parts[p.part_for_surface(roof)].polygons[roof][0][2][1] == pytest.approx(49.497474683)
    pid = p.part_for_surface(wall)
    page = p.add_page()
    p.set_placement(pid, page, 60, 60, 30, position_locked=True, rotation_locked=True)
    placement = copy.deepcopy(p.placements[pid])
    before = page_points(p.parts[pid].polygons[wall][0], placement)
    profile = p.profiles[p.surfaces[roof].profile_id]
    p.move_vertex(profile.id, profile.vertices[1].id, [11200, 0])
    p.move_vertex(profile.id, profile.vertices[2].id, [11200, math.sqrt(3500**2 * 2)])
    assert p.parts[pid].stale
    assert p.attachment_geometry(aid)["target_uv"] == geometry["target_uv"]
    p.recompute()
    np.testing.assert_allclose(
        page_points(p.parts[pid].polygons[wall][0], p.placements[pid]), before
    )
    assert p.placements[pid] == placement
    assert len(p.surfaces) == 2  # No hidden floor or trimmed replacement roof.


def test_one_mm_gap_and_trace_through_hole_rejected_atomically():
    p, wall, roof, edge = wall_roof()
    p.set_transform(wall, [0, 0, 1])
    before = p.to_dict()
    with pytest.raises(ValidationError, match="GAP"):
        p.attach_edge_to_surface(wall, edge, roof)
    assert p.to_dict() == before
    p.set_transform(wall, [0, 0, 0])
    plane = p.profiles[p.surfaces[roof].profile_id].plane
    hole = p.add_profile([[1000, 600], [2000, 600], [2000, 800], [1000, 800]], plane=plane)
    p.add_hole(roof, hole)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="OUTSIDE_MATERIAL"):
        p.attach_edge_to_surface(wall, edge, roof)
    assert p.to_dict() == before


def test_explicit_source_move_retains_invalid_attachment_and_blocks_recompute_and_snapshot():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    p.set_transform(wall, [0, 0, 1])
    assert not p.attachment_geometry(aid)["valid"]
    before = p.to_dict()
    with pytest.raises(ValidationError, match="GAP"):
        p.recompute()
    assert p.to_dict() == before
    assert any(i.code == "ATTACHMENT_CONTACT" for i in p.validate_layout())
    with pytest.raises(ValidationError):
        p.snapshot()
    # An invalid/stale construction remains saveable for an explicit UI repair.
    restored = AuthorProject.from_dict(before)
    assert not restored.attachment_geometry(aid)["valid"]
    restored.set_transform(wall, [0, 0, 0])
    restored.recompute()
    assert restored.attachment_geometry(aid)["valid"]


def test_preview_and_place_use_same_rigid_geometry_without_live_mutation():
    p = AuthorProject.new(scale=1)
    source_profile = p.add_profile([[0, 0], [40, 0], [40, 20], [0, 20]])
    source = p.add_surface(source_profile)
    target = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    edge = p.profiles[source_profile].segments[0].id
    before = p.to_dict()
    preview = p.preview_attachment(source, edge, target, [20, 30], [60, 30], angle_deg=90)
    assert preview["valid"], preview
    assert p.to_dict() == before
    assert (
        AuthorProject.from_dict(preview["project_state"]).world_geometry(source)
        == preview["world_geometry"]
    )
    aid = p.place_and_attach_edge(source, edge, target, [20, 30], [60, 30], angle_deg=90)
    np.testing.assert_allclose(
        p.world_geometry(source)["vertices"], preview["world_geometry"]["vertices"]
    )
    np.testing.assert_allclose(
        p.attachment_geometry(aid)["source_world"], [[20, 30, 0], [60, 30, 0]], atol=1e-9
    )
    saved_request = copy.deepcopy(p.attachments[aid].requested_placement)
    assert saved_request["target_start_uv"] == [20, 30]
    p.move_vertex(
        p.surfaces[target].profile_id,
        p.profiles[p.surfaces[target].profile_id].vertices[1].id,
        [110, 0],
    )
    assert p.attachments[aid].requested_placement == saved_request


@pytest.mark.parametrize("points", [([20, 30], [61, 30]), ([-20, 30], [20, 30])])
def test_bad_place_preview_and_commit_preserve_entire_state(points):
    p = AuthorProject.new(scale=1)
    profile = p.add_profile([[0, 0], [40, 0], [40, 20], [0, 20]])
    source = p.add_surface(profile)
    target = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    edge = p.profiles[profile].segments[0].id
    before = p.to_dict()
    assert not p.preview_attachment(source, edge, target, *points)["valid"]
    with pytest.raises(ValidationError):
        p.place_and_attach_edge(source, edge, target, *points)
    assert p.to_dict() == before


def test_glue_region_checks_real_coplanar_footprint_and_author_region():
    p = AuthorProject.new(scale=1)
    base = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 80], [0, 80]]))
    strip = p.add_surface(p.add_profile([[20, 20], [60, 20], [60, 25], [20, 25]]))
    aid = p.set_glue_region(
        strip, base, [[19, 19], [61, 19], [61, 26], [19, 26]], target_side="outside"
    )
    result = p.attachment_geometry(aid)
    assert result["nominal_area_mm2"] == pytest.approx(200)
    assert result["available_area_mm2"] == pytest.approx(200)
    assert p.parts[p.part_for_surface(base)].paths["GUIDES"][0]["closed"]
    before = p.to_dict()
    with pytest.raises(ValidationError, match="PARTIAL"):
        p.set_glue_region(strip, base, [[20, 20], [50, 20], [50, 25], [20, 25]])
    assert p.to_dict() == before
    p.set_transform(strip, [0, 0, 1])
    assert not p.attachment_geometry(aid)["valid"]


def test_trace_and_region_persistence_provenance_and_topology_replacement():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof, interval=[0.2, 0.8])
    restored = AuthorProject.from_dict(p.to_dict())
    assert restored.attachments[aid] == p.attachments[aid]
    assert restored.attachment_geometry(aid)["material_length_mm"] == pytest.approx(6000)
    profile = p.profiles[p.surfaces[wall].profile_id]
    p.update_profile(profile.id, profile.points)
    assert p.attachments[aid].unresolved
    assert not p.attachment_geometry(aid)["valid"]
    newedge = p.profiles[profile.id].segments[2].id
    p.update_attachment(aid, source_edge_id=newedge)
    assert p.attachments[aid].id == aid and not p.attachments[aid].unresolved
    p.set_anchor(p.part_for_surface(wall), wall)
    p.recompute()
    assert p.attachment_geometry(aid)["valid"]


def test_attachment_schema_rejects_missing_and_unknown_identity_fields():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    payload = p.to_dict()
    del payload["attachments"][aid]["target_side"]
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(payload)


def test_real_fold_mixed_wall_roof_source_edit_and_base_attachment_preserve_all_wall_points():
    p = AuthorProject.new(scale=0.01)
    wp = p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]], plane="XZ")
    wall = p.add_surface(wp)
    old_length = math.sqrt(3000**2 + 3000**2)
    rp = p.add_profile([[0, 0], [10000, 0], [10000, old_length], [0, old_length]])
    roof = p.add_surface(rp)
    p.set_transform(roof, [0, 0, 4000], [45, 0, 0])
    joint = p.connect_edges(
        wall, p.profiles[wp].segments[2].id, roof, p.profiles[rp].segments[0].id
    )
    pid = p.part_for_surface(wall)
    p.set_joint(joint, mode="fold", receiving_part_id=pid)
    base = p.add_surface(
        p.add_profile([[-1500, -2000], [11500, -2000], [11500, 8000], [-1500, 8000]])
    )
    attachment = p.attach_edge_to_surface(wall, p.profiles[wp].segments[0].id, base)
    second_page = p.add_page()
    p.set_placement(pid, second_page, 60, 60, 30, position_locked=True, rotation_locked=True)
    before = page_points(p.parts[pid].polygons[wall][0], p.placements[pid])
    old_frame = copy.deepcopy(p.parts[pid].frame)
    old_placement = copy.deepcopy(p.placements[pid])
    old_edges = [edge.id for edge in p.profiles[rp].segments]
    # Change the actual rise3000→3500 and local source length, not another
    # coplanar extension pretending to exercise the dihedral fold.
    new_length = math.sqrt(3000**2 + 3500**2)
    p.set_transform(roof, [0, 0, 4000], [math.degrees(math.atan2(3500, 3000)), 0, 0])
    p.move_vertex(rp, p.profiles[rp].vertices[2].id, [10000, new_length])
    p.move_vertex(rp, p.profiles[rp].vertices[3].id, [0, new_length])
    assert p.parts[pid].stale
    p.recompute()
    np.testing.assert_allclose(
        page_points(p.parts[pid].polygons[wall][0], p.placements[pid]), before, atol=1e-10
    )
    assert p.parts[pid].frame == old_frame and p.placements[pid] == old_placement
    assert p.attachment_geometry(attachment)["valid"]
    assert [edge.id for edge in p.profiles[rp].segments] == old_edges
    restored = AuthorProject.from_dict(p.to_dict())
    np.testing.assert_allclose(
        page_points(restored.parts[pid].polygons[wall][0], restored.placements[pid]),
        before,
        atol=1e-10,
    )


def test_stable_hole_edge_can_source_a_trace_and_tab_into_the_existing_hole():
    p = AuthorProject.new(scale=1)
    outer = p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    hole = p.add_profile([[30, 30], [70, 30], [70, 70], [30, 70]])
    source = p.add_surface(outer, holes=[hole])
    target_profile = p.add_profile(
        [[20, -20], [80, -20], [80, 20], [20, 20]],
        plane={"origin": [0, 30, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    target = p.add_surface(target_profile)
    eid = p.profiles[hole].segments[0].id
    aid = p.attach_edge_to_surface(source, eid, target, target_side="outside")
    cid = p.set_attachment_tab(aid, width_mm=5, taper=1)
    assert p.attachment_geometry(aid)["valid"]
    assert p.connector_geometry(cid)["tabs"][0]["available_area_mm2"] == pytest.approx(200)
    picked = next(
        e for e in p.part_geometry(p.part_for_surface(source))["edges"] if e["edge_id"] == eid
    )
    assert picked["start"] == [30, 30] and picked["end"] == [70, 30]
    # Editing a different hole corner preserves the source segment identity.
    p.move_vertex(hole, p.profiles[hole].vertices[2].id, [75, 70])
    p.recompute()
    assert p.attachments[aid].source_edge_id == eid


def test_requested_placement_is_history_not_silently_replayed_after_receiver_move():
    p = AuthorProject.new(scale=1)
    profile = p.add_profile([[0, 0], [40, 0], [40, 20], [0, 20]])
    source = p.add_surface(profile)
    target = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    aid = p.place_and_attach_edge(
        source, p.profiles[profile].segments[0].id, target, [20, 30], [60, 30]
    )
    request = copy.deepcopy(p.attachments[aid].requested_placement)
    source_before = p.world_geometry(source)
    p.set_transform(target, [10, 0, 0])
    assert p.attachments[aid].requested_placement == request
    assert p.world_geometry(source) == source_before
    np.testing.assert_allclose(p.attachment_geometry(aid)["target_uv"], [[10, 30], [50, 30]])
