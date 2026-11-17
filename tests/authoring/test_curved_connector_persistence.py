"""C registry capability/copy and real-source invalidation; not fold proof."""

import copy
import hashlib
import json

import pytest

from archpapercraft.authoring import (
    AuthorProject,
    ProjectFormatError,
    ValidationError,
    load_project,
)
from archpapercraft.authoring.curved_connectors import _digest
from archpapercraft.authoring.model import identity


def project_with_record():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [20, 0]], closed=False)
    b = p.copy_profile(a, plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]})
    owner = p.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": p.profiles[a].segments[0].id,
                "second_segment_id": p.profiles[b].segments[0].id,
                "first_interval": [0, 1],
                "second_interval": [0, 1],
            }
        ],
    )
    receiver = p.add_surface(p.add_profile([[0, 0], [20, 0], [0, 20]]))
    cid = p.add_curved_connector(
        owner,
        "first",
        receiver,
        receiver_side="inside",
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
        name="Authored intent, geometric proof pending",
    )
    p.validate()
    return p, p.curved_connectors[cid]


def test_schema5_is_an_explicit_safe_copy_and_cannot_smuggle_the_new_registry(tmp_path):
    p = AuthorProject.new()
    sid = p.add_surface(p.add_profile([[0, 0], [1000, 0], [0, 1000]]))
    pid = p.part_for_surface(sid)
    p.set_placement(pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    data = p.to_dict()
    data.pop("curved_connectors")
    data.pop("profile_subdivisions")
    for source_profile in data["profiles"].values():
        for source_segment in source_profile["segments"]:
            source_segment.pop("source_reference")
    data.update(schema_version=5, writer_version="0.3.0-pc008-segmented-variants-experimental")
    path = tmp_path / "schema5-original.apcraft"
    path.write_text(json.dumps(data), encoding="utf8")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    loaded = load_project(path)
    assert loaded.loaded_from_schema == 5 and loaded.requires_save_as
    assert loaded.curved_connectors == {} and loaded.profiles == p.profiles
    assert loaded.parts[pid].frame == p.parts[pid].frame and loaded.placements == p.placements
    with pytest.raises(ValidationError):
        loaded.save(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    loaded.save(tmp_path / "safe-schema6-copy.apcraft")
    assert not load_project(tmp_path / "safe-schema6-copy.apcraft").requires_save_as
    data["curved_connectors"] = {}
    with pytest.raises(ProjectFormatError, match="Starší"):
        AuthorProject.from_dict(data)


def test_new_registry_roundtrips_authored_ids_and_does_not_invent_a_geometric_certificate():
    p, record = project_with_record()
    record.tab_overrides[record.slot_ids[0]] = {"enabled": False}
    record.tab_overrides[record.slot_ids[1]] = {"tip_offset_mm": 0.01}
    restored = AuthorProject.from_dict(p.to_dict())
    assert restored.curved_connectors == p.curved_connectors
    assert restored.curved_connectors[record.id].certificate == {}
    assert restored.to_dict()["schema_version"] == 9
    assert restored.curved_connector_status(record.id)["status"] in ("UNRESOLVED", "STALE")
    restored.curved_connectors[record.id].certificate = {"status": "CERTIFIED_APPROXIMATE"}
    with pytest.raises(ValidationError, match="kruhových"):
        restored.snapshot()  # A stored assertion never substitutes for the missing proof.


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_receiver",
        "shared_owner",
        "count_bool",
        "duplicate_slot",
        "override_unknown",
        "off_not_bool",
    ],
)
def test_registry_references_and_stable_slot_fields_are_strict(mutation):
    p, record = project_with_record()
    if mutation == "unknown_receiver":
        record.receiver_surface_id = identity()
    elif mutation == "shared_owner":
        record.receiver_surface_id = record.owner_surface_id
    elif mutation == "count_bool":
        record.parameters["count"] = True
    elif mutation == "duplicate_slot":
        record.slot_ids[1] = record.slot_ids[0]
    elif mutation == "override_unknown":
        record.tab_overrides[identity()] = {"enabled": False}
    else:
        record.tab_overrides[record.slot_ids[0]] = {"enabled": 0}
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(p.to_dict(validate=False))


def test_complete_geometry_source_excludes_layout_and_cached_or_claimed_proofs():
    p, record = project_with_record()
    other = p.add_surface(p.add_profile([[0, 0], [5, 0], [0, 5]]))
    pid = p.part_for_surface(record.owner_surface_id)
    baseline = p.curved_connector_inputs(record.owner_surface_id)
    assert other in baseline["surfaces"]  # Unconnected material is still a real obstacle.
    assert record.receiver_surface_id in baseline["surfaces"]
    assert "certificate" not in baseline["curved_connectors"][record.id]
    record.certificate = {"status": "BOGUS_CLEAR"}
    record.material = {"paths": "not source authority"}
    p.set_placement(pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    assert _digest(p.curved_connector_inputs(record.owner_surface_id)) == _digest(baseline)
    frame, layout = copy.deepcopy(p.parts[pid].frame), copy.deepcopy(p.placements)
    p.parts[pid].stale = False
    other_profile = p.profiles[p.surfaces[other].profile_id]
    p.move_vertex(other_profile.id, other_profile.vertices[1].id, [6, 0])
    assert p.parts[pid].stale and p.parts[pid].frame == frame and p.placements == layout
    assert _digest(p.curved_connector_inputs(record.owner_surface_id)) != _digest(baseline)


def test_public_slot_edits_count_changes_and_controller_undo_preserve_authored_identity():
    from archpapercraft.application.author_controller import AuthorController

    p, record = project_with_record()
    original = list(record.slot_ids)
    controller = AuthorController()
    controller.project = p
    controller.execute(
        "Off", lambda project: project.set_curved_tab(record.id, original[0], enabled=False)
    )
    controller.execute(
        "Tip", lambda project: project.set_curved_tab(record.id, original[1], tip_offset_mm=0.01)
    )
    before = controller.project.to_dict()
    controller.execute("More", lambda project: project.update_curved_connector(record.id, count=16))
    added = list(controller.project.curved_connectors[record.id].slot_ids)
    assert added[:12] == original and len(added) == 16
    controller.execute("Fewer", lambda project: project.update_curved_connector(record.id, count=8))
    assert controller.project.curved_connectors[record.id].slot_ids == added
    controller.undo()
    controller.undo()
    assert controller.project.to_dict() == before
    controller.redo()
    assert controller.project.curved_connectors[record.id].slot_ids == added
    assert controller.project.curved_connectors[record.id].tab_overrides == {
        original[0]: {"enabled": False},
        original[1]: {"tip_offset_mm": 0.01},
    }


def test_public_bad_update_and_preview_leave_original_state_and_history_intact():
    p, record = project_with_record()
    before = p.to_dict()
    for changes in (
        {"enabled": 1},
        {"count": True},
        {"nominal_base_mm": 0},
        {"min_glue_area_mm2": 0},
        {"gap_mm": 1},
        {"no_such_param": 2},
    ):
        with pytest.raises(ValidationError):
            p.update_curved_connector(record.id, **changes)
        assert p.to_dict() == before
    # Proposed identities belong only to the detached clone, never live material.
    p.remove_curved_connector(record.id)
    clean = p.to_dict()
    preview = p.preview_curved_connector(
        record.owner_surface_id,
        record.rim_side,
        record.receiver_surface_id,
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
    )
    assert preview["preview_only"] and not preview["can_confirm"]
    assert p.to_dict() == clean
