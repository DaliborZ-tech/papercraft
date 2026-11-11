"""Explicit uniform paper properties; no inferred thickness or physical approval."""

import copy
import json

import pytest

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ProjectFormatError, ValidationError
from archpapercraft.authoring.project import SCHEMA_VERSION


def test_material_is_explicit_persistent_undoable_and_invalidates_only_source_evidence(tmp_path):
    controller = AuthorController()
    controller.new()
    sid = controller.execute(
        "Own surface", lambda p: p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 50]]))
    )
    project = controller.project
    part = project.part_for_surface(sid)
    project.set_placement(part, project.pages[0].id, 60, 60, 30,
                          position_locked=True, rotation_locked=True)
    before = copy.deepcopy(project.to_dict())
    placement = copy.deepcopy(project.placements[part])
    controller.execute("Measured paper", lambda p: p.set_material_profile(
        thickness_mm=0.2, clearance_mm=0.05, bend_radius_mm=0.1, crease_zone_mm=0.7
    ))
    assert project.material_profile == dict(
        thickness_mm=0.2, clearance_mm=0.05, bend_radius_mm=0.1, crease_zone_mm=0.7
    )
    assert project.parts[part].stale and project.placements[part] == placement
    controller.save(tmp_path / "measured-paper.apcraft")
    restored = AuthorProject.load(controller.file_path)
    assert restored.material_profile == project.material_profile
    controller.undo()
    assert controller.project.to_dict() == before
    controller.redo()
    assert controller.project.material_profile["thickness_mm"] == 0.2
    controller.execute("Unknown paper", lambda p: p.set_material_profile(thickness_mm=None))
    assert controller.project.material_profile["thickness_mm"] is None


@pytest.mark.parametrize("values", [
    dict(thickness_mm=0), dict(thickness_mm=-0.1), dict(thickness_mm=True),
    dict(thickness_mm=float("nan")), dict(clearance_mm=-1), dict(bend_radius_mm=True),
    dict(crease_zone_mm=-1),
])
def test_invalid_material_changes_are_atomic(values):
    project = AuthorProject.new()
    before = project.to_dict()
    with pytest.raises(ValidationError):
        project.set_material_profile(**values)
    assert project.to_dict() == before


def test_draft_schema_requires_exact_material_fields_not_a_silent_default():
    project = AuthorProject.new()
    for mutate in (
        lambda data: data.pop("material_profile"),
        lambda data: data["material_profile"].pop("thickness_mm"),
        lambda data: data["material_profile"].update(grammage=200),
    ):
        data = project.to_dict()
        mutate(data)
        with pytest.raises(ProjectFormatError):
            AuthorProject.from_dict(data)


def test_known_prior_b_draft_is_only_saved_as_copy_and_gets_no_measured_material(tmp_path):
    project = AuthorProject.new()
    sid = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 50]]))
    part = project.part_for_surface(sid)
    project.set_placement(part, project.pages[0].id, 60, 60, 30,
                          position_locked=True, rotation_locked=True)
    data = project.to_dict()
    del data["material_profile"]
    data.update(schema_version=2, writer_version="0.3.0-pc006b-experimental")
    data.pop("segmented_variants")  # Reconstruct the historical format envelope.
    data.pop("profile_subdivisions")
    original = tmp_path / "earlier-B.apcraft"
    original.write_text(json.dumps(data), encoding="utf8")
    original_bytes = original.read_bytes()
    controller = AuthorController()
    controller.open(original)
    assert controller.copy_source_path == original and controller.file_path is None
    assert controller.project.material_profile["thickness_mm"] is None
    assert controller.project.parts[part].stale
    assert controller.project.placements[part] == project.placements[part]
    with pytest.raises(ValueError):
        controller.save(original)
    controller.save(tmp_path / "B-material-copy.apcraft")
    assert original.read_bytes() == original_bytes
    assert controller.project.to_dict()["schema_version"] == SCHEMA_VERSION
