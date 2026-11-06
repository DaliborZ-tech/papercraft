import copy

import numpy as np
import pytest

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.geometry import page_points


def two_panels(scale=0.01):
    p = AuthorProject.new(scale=scale)
    pa = p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]])
    pb = p.add_profile([[10000, 0], [20000, 0], [20000, 4000], [10000, 4000]])
    a, b = p.add_surface(pa), p.add_surface(pb)
    ea, eb = p.profiles[pa].segments[1].id, p.profiles[pb].segments[3].id
    return p, a, b, ea, eb


def test_cut_fold_split_preserves_root_identity_and_all_page_points():
    p, a, b, ea, eb = two_panels()
    aid, bid = p.part_for_surface(a), p.part_for_surface(b)
    p.set_placement(aid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    j = p.connect_edges(a, ea, b, eb)
    p.set_joint(j, mode="fold", receiving_part_id=aid)
    assert p.part_for_surface(b) == aid and bid not in p.parts
    before = {
        sid: page_points(loops[0], p.placements[aid])
        for sid, loops in p.parts[aid].polygons.items()
    }
    p.set_joint(j, mode="cut")
    assert p.part_for_surface(a) == aid
    new_b = p.part_for_surface(b)
    assert new_b not in (aid, bid)
    assert bid in p.parts[aid].lineage
    for sid in (a, b):
        pid = p.part_for_surface(sid)
        np.testing.assert_allclose(
            page_points(p.parts[pid].polygons[sid][0], p.placements[pid]), before[sid], atol=1e-10
        )
        assert p.placements[pid].position_locked and p.placements[pid].rotation_locked


def test_whole_mixed_part_stale_recompute_preserves_unedited_root_points_and_locks():
    p, a, b, ea, eb = two_panels()
    aid = p.part_for_surface(a)
    j = p.connect_edges(a, ea, b, eb)
    p.set_joint(j, mode="fold", receiving_part_id=aid)
    p.set_placement(aid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    before = page_points(p.parts[aid].polygons[a][0], p.placements[aid])
    profile = p.profiles[p.surfaces[b].profile_id]
    old_cache = copy.deepcopy(p.parts[aid].polygons)
    p.move_vertex(profile.id, profile.vertices[1].id, [21000, 0])
    assert p.parts[aid].stale and p.parts[aid].polygons == old_cache
    assert any(i.code == "STALE" for i in p.validate_layout())
    p.recompute()
    np.testing.assert_allclose(
        page_points(p.parts[aid].polygons[a][0], p.placements[aid]), before, atol=1e-10
    )
    assert p.placements[aid].x_mm == 60 and p.placements[aid].rotation_deg == 30
    assert p.placements[aid].position_locked and p.placements[aid].rotation_locked


def test_one_author_tab_moves_owner_has_only_one_hinge_and_snapshot_material():
    p, a, b, ea, eb = two_panels()
    j = p.connect_edges(a, ea, b, eb)
    p.set_tab(j, owner=a, width_mm=5, taper=0.5)
    aid, bid = p.part_for_surface(a), p.part_for_surface(b)
    assert len(p.parts[aid].paths["TABS"]) == 1 and not p.parts[bid].paths["TABS"]
    assert len(p.parts[aid].paths["GUIDES"]) == 1  # Coplanar mate: no mountain/valley crease.
    connector = p.joints[j].connector_id
    p.set_tab(j, owner=b, shape="triangle")
    assert p.joints[j].connector_id == connector
    assert not p.parts[aid].paths["TABS"] and len(p.parts[bid].paths["TABS"]) == 1
    assert len(p.parts[bid].paths["TABS"][0]["points"]) == 3
    p.set_tab(j, owner=None)
    assert not p.connectors and not p.parts[bid].paths["TABS"]


def test_wrong_joint_and_bad_tab_settings_are_transactional():
    p, a, b, ea, eb = two_panels()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.connect_edges(a, p.profiles[p.surfaces[a].profile_id].segments[0].id, b, eb)
    assert p.to_dict() == before
    j = p.connect_edges(a, ea, b, eb)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_tab(j, owner=a, width_mm=-1)
    assert p.to_dict() == before


def test_layout_checks_full_material_holes_overflow_and_acknowledgements():
    p, a, b, ea, eb = two_panels()
    aid, bid = p.part_for_surface(a), p.part_for_surface(b)
    assert {i.code for i in p.validate_layout()} == {"UNPLACED"}
    p.set_placement(aid, p.pages[0].id, 20, 20)
    p.set_placement(bid, p.pages[0].id, 30, 30)
    overlap = next(i for i in p.validate_layout() if i.code == "MATERIAL_OVERLAP")
    p.acknowledge(overlap.id)
    assert next(i for i in p.validate_layout() if i.id == overlap.id).acknowledged
    # Unrelated source sketches do not invalidate the accepted overlap.
    p.add_profile([[0, 0], [1, 0]], closed=False)
    assert next(i for i in p.validate_layout() if i.id == overlap.id).acknowledged
    p.set_placement(bid, x_mm=31)
    assert not next(i for i in p.validate_layout() if i.id == overlap.id).acknowledged
    p.set_placement(aid, x_mm=200)
    error = next(i for i in p.validate_layout() if i.code == "PHYSICAL_OVERFLOW")
    with pytest.raises(ValidationError):
        p.acknowledge(error.id)
    with pytest.raises(ValidationError):
        p.snapshot()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p, pid: p.parts.pop(pid),
        lambda p, pid: p.parts[pid].surface_ids.clear(),
        lambda p, pid: p.parts[pid].polygons.clear(),
        lambda p, pid: p.parts[pid].paths.pop("CUT"),
        lambda p, pid: p.parts[pid].polygons[next(iter(p.surfaces))][0].__setitem__(0, [999, 999]),
    ],
)
def test_missing_or_tampered_projection_never_silently_omits_a_part(mutation):
    p, a, b, ea, eb = two_panels()
    pid = p.part_for_surface(a)
    p.set_placement(pid, p.pages[0].id, 20, 20)
    p.set_placement(p.part_for_surface(b), p.pages[0].id, 20, 100)
    mutation(p, pid)
    with pytest.raises(ValidationError):
        p.snapshot()


def test_delete_nonempty_page_moves_parts_to_tray_without_moving_or_losing_them():
    p, a, b, ea, eb = two_panels()
    second = p.add_page(landscape=True)
    pid = p.part_for_surface(a)
    p.set_placement(pid, second, 40, 50, 15, position_locked=True)
    p.delete_page(second)
    assert p.placements[pid].page_id is None
    assert (p.placements[pid].x_mm, p.placements[pid].y_mm, p.placements[pid].rotation_deg) == (
        40,
        50,
        15,
    )


def test_position_and_rotation_locks_are_independent():
    p, a, b, ea, eb = two_panels()
    pid = p.part_for_surface(a)
    p.set_placement(pid, p.pages[0].id, 20, 20, position_locked=True)
    p.set_placement(pid, rotation_deg=30)
    with pytest.raises(ValidationError):
        p.set_placement(pid, x_mm=21)
    p.set_placement(pid, position_locked=False, rotation_locked=True)
    p.set_placement(pid, x_mm=21)
    with pytest.raises(ValidationError):
        p.set_placement(pid, rotation_deg=31)


@pytest.mark.parametrize("angle,role", [(0, "GUIDES"), (90, "FOLD_MOUNTAIN"), (-90, "FOLD_VALLEY")])
def test_author_place_connect_has_real_contact_and_correct_fold_polarity(angle, role):
    p = AuthorProject.new()
    profiles = [p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]]) for _ in range(2)]
    a, b = [p.add_surface(profile) for profile in profiles]
    ea, eb = [p.profiles[profile].segments[0].id for profile in profiles]
    old_ids = [v.id for v in p.profiles[profiles[1]].vertices]
    old_placement = copy.deepcopy(p.placements[p.part_for_surface(b)])
    j = p.place_and_connect_edges(a, ea, b, eb, angle_deg=angle)
    aw, bw = p.world_geometry(a)["boundary"][0], p.world_geometry(b)["boundary"][0]
    np.testing.assert_allclose(aw["start"], bw["end"], atol=1e-8)
    np.testing.assert_allclose(aw["end"], bw["start"], atol=1e-8)
    assert p.placements[p.part_for_surface(b)] == old_placement
    assert [v.id for v in p.profiles[profiles[1]].vertices] == old_ids
    p.set_joint(j, mode="fold")
    pid = p.part_for_surface(a)
    assert len(p.parts[pid].paths[role]) == 1
    if angle:
        p.set_front_side(pid, "inside")
        swapped = "FOLD_VALLEY" if role == "FOLD_MOUNTAIN" else "FOLD_MOUNTAIN"
        assert len(p.parts[pid].paths[swapped]) == 1
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.place_and_connect_edges(a, ea, b, eb)
    assert p.to_dict() == before


def test_place_connect_composes_parent_transform_and_rejects_unequal_edges():
    p = AuthorProject.new()
    pa = p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]], plane="XZ")
    pb = p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]], plane="YZ")
    a, b = p.add_surface(pa), p.add_surface(pb)
    parent = [[0, -1, 0, 1000], [1, 0, 0, 2000], [0, 0, 1, 3000], [0, 0, 0, 1]]
    p.set_transform(b, [30, 40, 50], [15, 20, 30], parent_transforms=[parent])
    ea, eb = p.profiles[pa].segments[0].id, p.profiles[pb].segments[0].id
    before = p.to_dict()
    with pytest.raises(ValidationError, match="různou délku"):
        p.place_and_connect_edges(a, ea, b, p.profiles[pb].segments[1].id)
    assert p.to_dict() == before
    p.place_and_connect_edges(a, ea, b, eb, angle_deg=45)
    aw, bw = p.world_geometry(a)["boundary"][0], p.world_geometry(b)["boundary"][0]
    np.testing.assert_allclose(aw["start"], bw["end"], atol=1e-8)
    np.testing.assert_allclose(aw["end"], bw["start"], atol=1e-8)
    assert p.surfaces[b].parent_transforms == [parent]


def test_glue_contact_subtracts_real_receiver_holes_and_cannot_be_acknowledged():
    p, a, b, ea, eb = two_panels()
    hole = p.add_profile([[10050, 1000], [10200, 1000], [10200, 3000], [10050, 3000]])
    p.add_hole(b, hole)
    p.recompute()
    j = p.connect_edges(a, ea, b, eb)
    p.set_tab(j, owner=a, width_mm=5, taper=0.6)
    contact = next(i for i in p.validate_layout() if i.code == "GLUE_AREA_PARTIAL")
    assert contact.severity == "error"
    with pytest.raises(ValidationError):
        p.acknowledge(contact.id)


def test_changed_cut_joint_world_contact_stays_stale_until_repaired():
    p, a, b, ea, eb = two_panels()
    p.connect_edges(a, ea, b, eb)
    p.set_transform(b, [1, 0, 0])
    before = p.to_dict()
    with pytest.raises(ValidationError, match="nepotkávají"):
        p.recompute()
    assert p.to_dict() == before


def test_reversing_joint_storage_does_not_change_fold_type():
    p = AuthorProject.new()
    a_profile, b_profile = [
        p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]]) for _ in range(2)
    ]
    a, b = p.add_surface(a_profile), p.add_surface(b_profile)
    j = p.place_and_connect_edges(
        a,
        p.profiles[a_profile].segments[0].id,
        b,
        p.profiles[b_profile].segments[0].id,
        angle_deg=90,
        mode="fold",
    )
    pid = p.part_for_surface(a)
    assert len(p.parts[pid].paths["FOLD_MOUNTAIN"]) == 1
    joint = p.joints[j]
    joint.surface_a, joint.surface_b = joint.surface_b, joint.surface_a
    joint.edge_a, joint.edge_b = joint.edge_b, joint.edge_a
    p.recompute()
    assert len(p.parts[pid].paths["FOLD_MOUNTAIN"]) == 1
