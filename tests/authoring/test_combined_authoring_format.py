"""Combined C/LINE capability copies preserve authored work and source closure."""

import copy
import hashlib
import json

import pytest
from test_circular_shell import authored, circle

from archpapercraft.authoring import (
    AuthorProject,
    ProjectFormatError,
    ValidationError,
    load_project,
)


@pytest.mark.parametrize("version,writer,absent", [
    (6, "0.3.0-pc007b-curved-connectors-experimental", "profile_subdivisions"),
    (7, "0.3.0-pc008-profile-provenance-experimental", "curved_connectors"),
])
def test_known_parallel_capabilities_open_as_copies_without_overwriting(
    version, writer, absent, tmp_path
):
    project = AuthorProject.new(scale=1)
    sid = project.add_surface(project.add_profile([[0, 0], [20, 0], [0, 20]]))
    pid = project.part_for_surface(sid)
    project.set_placement(pid, project.pages[0].id, 60, 60, 17,
                          position_locked=True, rotation_locked=True)
    if version == 7:
        profile = project.profiles[project.surfaces[sid].profile_id]
        project.split_profile_segment(profile.id, profile.segments[0].id, .5)
    raw = project.to_dict()
    # Published schema6/7 segments predate the schema9 descriptor field. Only
    # strip the absent legacy default; never erase a qualified analytic source
    # to manufacture a supposedly compatible old document.
    for profile in raw["profiles"].values():
        for segment in profile["segments"]:
            assert segment.pop("source_reference") is None
    raw.pop(absent)
    raw.update(schema_version=version, writer_version=writer)
    path = tmp_path / f"original-v{version}.apcraft"
    path.write_text(json.dumps(raw), encoding="utf-8")
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    restored = load_project(path)
    assert restored.requires_save_as and restored.loaded_from_schema == version
    assert restored.profiles == project.profiles
    assert restored.parts == project.parts and restored.placements == project.placements
    assert restored.profile_subdivisions == project.profile_subdivisions
    assert restored.curved_connectors == project.curved_connectors
    with pytest.raises(ValidationError):
        restored.save(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original
    target = tmp_path / "combined-copy.apcraft"
    restored.save(target)
    assert not load_project(target).requires_save_as
    assert load_project(target).to_dict() == restored.to_dict()
    # Even a null newer descriptor is not part of either old envelope.
    for descriptor in (None, {"piece_id": "counterfeit"}):
        poisoned = copy.deepcopy(raw)
        next(iter(poisoned["profiles"].values()))["segments"][0]["source_reference"] = descriptor
        with pytest.raises(ProjectFormatError, match="Starší formát"):
            AuthorProject.from_dict(poisoned)
    # Merely relabeling a newer capability as an old format remains invalid.
    raw[absent] = {}
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


def test_curved_source_replay_contains_foreign_material_retired_frame_history():
    project, owner, _ = authored(10, 10, 30)
    receiver = project.add_surface(circle(project, 10, 0))
    distant = project.add_surface(project.add_profile([[0, 0], [20, 0], [0, 20]]))
    project.set_transform(distant, position_mm=[1000, 0, 0])
    profile = project.profiles[project.surfaces[distant].profile_id]
    old_axis = project.parts[project.part_for_surface(distant)].frame.axis_segment_id
    project.split_profile_segment(profile.id, old_axis, .5)
    project.set_material_profile(thickness_mm=.2, clearance_mm=.01, bend_radius_mm=0)
    cid = project.add_curved_connector(owner, "first", receiver, receiver_side="inside",
                                       nominal_base_mm=.24, min_glue_area_mm2=1)
    project.recompute()
    assert project.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE"
    inputs = project.curved_connector_inputs(owner)
    assert inputs["profile_subdivisions"] == project.profile_subdivisions
    restored = AuthorProject.from_dict(copy.deepcopy(project.to_dict()))
    assert restored.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE"
    assert restored.parts[restored.part_for_surface(distant)].frame.axis_segment_id == old_axis
    material = restored.curved_connector_material_report(owner)
    assert material["status"] == "CANONICAL_NATIVE_MATERIAL_COMPOSED"
    assert material["domain_connector_checks"][cid]["status"] == "CERTIFIED_APPROXIMATE"
