"""Continuous-source scene dependency, cache honesty and reversible author intent.

These are backend construction tests, not a native UI or physical assembly proof.
Foreign material expectations follow elementary axis-box separation and the
independent straight-tab 45-degree witness retained from the B adapter oracle.
"""

import copy
import json
from fractions import Fraction as Q

import pytest
from test_curved_connector_sources import receiver_source

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.curved_connectors import (
    CurvedConnectorError,
    _prepare_native_slots,
    _scene_clearance,
    _surface_control_box,
)


def prepared_scene():
    p, record, _ = receiver_source()
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    return p, record


def foreign_plane(p, *, z=100):
    profile = p.add_profile(
        [[-2, -2], [2, -2], [2, 2], [-2, 2]],
        plane={"origin": [0, 0, z], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    return p.add_surface(profile)


def straight_wall_base(p):
    profile = p.add_profile(
        [[120, 0], [160, 0], [160, 20], [120, 20]],
        plane={"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    wall = p.add_surface(profile)
    base = p.add_surface(p.add_profile([[100, 0], [200, 0], [200, 100], [100, 100]]))
    attachment = p.attach_edge_to_surface(
        wall,
        p.profiles[profile].segments[0].id,
        base,
        target_side="outside",
        glue_direction=-1,
    )
    return p.set_attachment_tab(attachment, width_mm=5, taper=1)


def test_unconnected_actual_source_is_registered_and_move_invalidates_all_phase_proof():
    p, record = prepared_scene()
    foreign = foreign_plane(p)
    packet = _prepare_native_slots(p, record)
    report = _scene_clearance(p, record, packet)
    assert report["status"] == "PROVEN_FAR"
    row = next(row for row in report["checked"] if row["id"] == foreign)
    assert row["kind"] == "SOURCE_CONTINUOUS_SURFACE_CONTROL_HULL"
    assert Q(row["separation_lower_exact"]) > 49
    # The entire XY disk/body fold is inside |x|,|y|,|z-30|<21. The foreign
    # square's z=100 is outside, but the moved square z=30 is not separated.
    p.set_transform(foreign, [0, 0, -70])
    with pytest.raises(CurvedConnectorError, match="zastaralý"):
        _scene_clearance(p, record, packet)
    current = _scene_clearance(p, record, _prepare_native_slots(p, record))
    assert current["status"] == "UNRESOLVED"
    assert current["unresolved_obstacle_ids"] == [foreign]


def test_control_hull_does_not_discard_between_endpoint_cubic_material():
    p, record = prepared_scene()
    profile = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [100, 0],
                "end": [100, 10],
                "data": {"control1": [-40, 0], "control2": [-40, 10]},
            },
            {"kind": "line", "start": [100, 10], "end": [110, 10]},
            {"kind": "line", "start": [110, 10], "end": [110, 0]},
            {"kind": "line", "start": [110, 0], "end": [100, 0]},
        ],
        plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    foreign = p.add_surface(profile)
    # Bernstein convex hull [-40,110] includes x(1/2)=-5, despite both cubic
    # endpoints at x=100. A line-endpoint box would incorrectly prove far.
    assert _surface_control_box(p, foreign) == ((-40, 110), (0, 10), (30, 30))
    report = _scene_clearance(p, record, _prepare_native_slots(p, record))
    assert report["status"] == "UNRESOLVED"
    assert foreign in report["unresolved_obstacle_ids"]


def test_unknown_material_never_promotes_empty_foreign_scene_to_clear():
    p, record, _ = receiver_source()
    report = _scene_clearance(p, record, _prepare_native_slots(p, record))
    assert report["status"] == "UNVERIFIED_MATERIAL"
    assert not report["material_known"]


@pytest.mark.parametrize("known", [False, True])
def test_straight_consumer_preserves_true_negative_with_far_and_near_curved_uncertainty(known):
    p, record, _ = receiver_source()
    if known:
        p.set_material_profile(thickness_mm=0.2, clearance_mm=0.02, bend_radius_mm=0.05)
    cid = straight_wall_base(p)
    clear = p.connector_bend_clearance(cid)
    assert clear["status"] == ("CLEAR" if known else "UNVERIFIED")
    dependency = clear["curved_material_dependency"]
    assert dependency["status"] == ("PROVEN_FAR" if known else "UNVERIFIED_MATERIAL")
    assert all(Q(row["separation_lower_exact"]) > 0 for row in dependency["checked"])
    profile = p.add_profile(
        [[125, -2.5], [155, -2.5], [155, -1.5], [125, -1.5]],
        plane={"origin": [0, 3, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    obstacle = p.add_surface(profile)
    collision = p.connector_bend_clearance(cid)
    assert collision["status"] == "COLLISION"
    assert collision["tabs"][0]["obstacle_id"] == obstacle
    # Same independent 45-degree interior witness as B-02, translated in X.
    # Moving C near makes that extra interaction unresolved, not the known
    # straight-tab intersection with y=3,z=-2 disappear.
    for sid in (record.owner_surface_id, record.receiver_surface_id):
        p.set_transform(sid, [130, 0, 0])
    near = p.connector_bend_clearance(cid)
    assert near["status"] == "COLLISION"
    assert near["tabs"][0]["obstacle_id"] == obstacle
    assert near["curved_material_dependency"]["status"] == "UNRESOLVED"
    assert near["curved_material_dependency"]["source_digest"] != dependency["source_digest"]


def test_near_curved_dependency_blocks_an_otherwise_clear_straight_tab():
    p, record = prepared_scene()
    cid = straight_wall_base(p)
    before = p.connector_bend_clearance(cid)
    assert before["status"] == "CLEAR"
    # Direct source changes with unchanged revision also invalidate the cache.
    for sid in (record.owner_surface_id, record.receiver_surface_id):
        p.surfaces[sid].position_mm[0] = 130
    result = p.connector_bend_clearance(cid)
    assert result["status"] == "UNRESOLVED"
    assert result["curved_material_dependency"]["unresolved_ids"]
    assert (
        result["curved_material_dependency"]["source_digest"]
        != before["curved_material_dependency"]["source_digest"]
    )


def test_live_preview_recomputes_detached_source_and_returns_repairable_negative():
    p, record = prepared_scene()
    p.remove_curved_connector(record.id)
    before = p.to_dict()
    kwargs = dict(nominal_base_mm=0.24, min_glue_area_mm2=1)
    preview = p.preview_curved_connector(
        record.owner_surface_id, "second", record.receiver_surface_id, **kwargs
    )
    assert preview["can_confirm"] and preview["status"] == "CERTIFIED_APPROXIMATE"
    assert preview["material_report"]["domain_status"] == "CERTIFIED_APPROXIMATE"
    assert preview["material_error"] is None and preview["can_create_authored_intent"]
    assert p.to_dict() == before
    foreign_plane(p, z=30)
    before = p.to_dict()
    negative = p.preview_curved_connector(
        record.owner_surface_id, "second", record.receiver_surface_id, **kwargs
    )
    assert not negative["can_confirm"] and negative["status"] == "UNRESOLVED"
    assert negative["can_create_authored_intent"] and negative["message"]
    assert p.to_dict() == before


@pytest.mark.parametrize("field", ["certificate", "material"])
def test_proof_cache_tamper_is_blocked_and_explicit_recompute_repairs(field):
    p, record = prepared_scene()
    p.recompute()
    assert p.curved_connector_status(record.id)["status"] == "CERTIFIED_APPROXIMATE"
    getattr(record, field)["counterfeit"] = True
    result = p.curved_connector_status(record.id)
    assert result["status"] == "UNRESOLVED" and "poškozený" in result["message"]
    p.recompute()
    assert p.curved_connector_status(record.id)["status"] == "CERTIFIED_APPROXIMATE"


def test_complete_proof_survives_sorted_save_and_reopen_with_multiple_foreign_sources(tmp_path):
    p, record = prepared_scene()
    foreign_plane(p, z=100)
    foreign_plane(p, z=-100)
    p.recompute()
    assert p.curved_connector_status(record.id)["status"] == "CERTIFIED_APPROXIMATE"
    source = tmp_path / "scene.apcraft"
    p.save(source)
    # Save sorts all keys; authored insertion order must not influence a proof.
    raw = source.read_bytes()
    reopened = load_project(source)
    assert reopened.curved_connector_status(record.id)["status"] == "CERTIFIED_APPROXIMATE"
    assert reopened.to_dict() == p.to_dict()
    assert source.read_bytes() == raw


def test_all_slots_off_remove_actual_material_without_destroying_authored_ids_or_overrides():
    p, record = prepared_scene()
    p.set_curved_tab(record.id, record.slot_ids[1], tip_offset_mm=0.01)
    p.recompute()
    owner_part = p.parts[p.part_for_surface(record.owner_surface_id)]
    assert len(owner_part.paths["TABS"]) == 12
    initial_slots = record.slot_ids[:]
    initial_frame = copy.deepcopy(owner_part.frame)
    for tab_id in initial_slots:
        p.set_curved_tab(record.id, tab_id, enabled=False)
    assert p.curved_connector_status(record.id)["status"] == "NOT_APPLICABLE"
    assert not p.curved_connector_inputs(record.owner_surface_id)
    p.recompute()
    assert not p.parts[owner_part.id].paths["TABS"]
    assert p.parts[owner_part.id].frame == initial_frame
    assert record.slot_ids == initial_slots
    restored = AuthorProject.from_dict(json.loads(json.dumps(p.to_dict())))
    restored.set_curved_tab(record.id, initial_slots[1], enabled=True)
    restored.recompute()
    assert len(restored.parts[owner_part.id].paths["TABS"]) == 1
    assert restored.curved_connector_status(record.id)["status"] == "CERTIFIED_APPROXIMATE"
    assert (
        restored.curved_connectors[record.id].tab_overrides[initial_slots[1]]["tip_offset_mm"]
        == 0.01
    )


def test_source_binding_fingerprint_cannot_disagree_even_with_authored_values_unchanged():
    p, record = prepared_scene()
    p.recompute()
    raw = p.to_dict()
    raw["curved_connectors"][record.id]["source_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="rozporný otisk"):
        AuthorProject.from_dict(raw)
