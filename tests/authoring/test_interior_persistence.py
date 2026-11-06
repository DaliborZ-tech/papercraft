import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_interior import wall_roof

from archpapercraft.authoring import AuthorProject, ProjectFormatError, UnsupportedOperationError


def test_actual_schema_one_implicit_tab_can_be_edited_individually_in_its_copy(tmp_path):
    source = (
        Path(__file__).resolve().parents[2] / "docs/p2/implementation/evidence/"
        "pc006a-desktop-7da2403-run04/own-model.apcraft"
    )
    original = source.read_bytes()
    legacy = json.loads(original)
    project = AuthorProject.load(source)
    cid = next(iter(project.connectors))
    connector = project.connectors[cid]
    assert connector.id == legacy["connectors"][cid]["id"]
    assert connector.owner_surface_id == legacy["connectors"][cid]["owner_surface_id"]
    assert len(connector.tab_ids) == 1 and connector.tab_ids[0] != cid
    tid = connector.tab_ids[0]
    project.set_connector_tab(cid, tid, enabled=False)
    copy_path = tmp_path / "own-editable-copy.apcraft"
    project.save(copy_path)
    restored = AuthorProject.load(copy_path)
    assert restored.connectors[cid].tab_ids == [tid]
    assert restored.connectors[cid].tab_overrides[tid]["enabled"] is False
    assert source.read_bytes() == original


def legacy_a_document():
    p = AuthorProject.new(scale=1)
    profile = p.add_profile([[0, 0], [40, 0], [40, 20], [0, 20]])
    sid = p.add_surface(profile)
    p.set_placement(
        p.part_for_surface(sid),
        p.pages[0].id,
        60,
        60,
        30,
        position_locked=True,
        rotation_locked=True,
    )
    data = p.to_dict()
    data.update(schema_version=1, writer_version="0.3.0-experimental")
    del data["attachments"], data["next_attachment_number"], data["material_profile"]
    return data, sid


def test_known_a_file_import_preserves_source_ids_layout_and_origin_requires_copy(tmp_path):
    data, sid = legacy_a_document()
    path = tmp_path / "original006A.apcraft"
    path.write_text(json.dumps(data), encoding="utf8")
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    p = AuthorProject.load(path)
    assert p.loaded_from_schema == 1 and p.requires_save_as
    assert p.loaded_source_path == str(path.resolve())
    assert p.to_dict()["profiles"] == data["profiles"]
    assert p.to_dict()["surfaces"] == data["surfaces"]
    assert p.to_dict()["placements"] == data["placements"]
    assert p.parts[p.part_for_surface(sid)].stale
    with pytest.raises(UnsupportedOperationError):
        p.save(path)
    p.recompute()
    target = tmp_path / "copy006B.apcraft"
    p.save(target)
    assert not p.requires_save_as
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
    assert json.loads(target.read_text(encoding="utf8"))["schema_version"] == 3
    restored = AuthorProject.load(target)
    assert restored.loaded_from_schema == 3 and not restored.requires_save_as
    undo = AuthorProject.from_dict(p.to_dict())
    assert undo.loaded_from_schema is None and not undo.requires_save_as


@pytest.mark.parametrize(
    "missing",
    [("attachments",), ("next_attachment_number",), ("attachments", "next_attachment_number")],
)
def test_schema_two_cannot_silently_drop_attachment_registry_as_legacy(missing):
    p, wall, roof, edge = wall_roof()
    p.attach_edge_to_surface(wall, edge, roof)
    data = p.to_dict()
    for key in missing:
        del data[key]
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)


def test_forged_schema_one_with_new_writer_is_not_a_supported_old_envelope():
    p, wall, roof, edge = wall_roof()
    p.attach_edge_to_surface(wall, edge, roof)
    data = p.to_dict()
    data["schema_version"] = 1
    del data["attachments"], data["next_attachment_number"]
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("requested_placement", []),
        ("source_region_uv", ""),
        ("target_side", "back"),
        ("glue_direction", True),
        ("source_interval", [1, 0]),
    ],
)
def test_attachment_schema_invalid_types_do_not_survive_roundtrip(field, value):
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    data = p.to_dict()
    data["attachments"][aid][field] = copy.deepcopy(value)
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)
