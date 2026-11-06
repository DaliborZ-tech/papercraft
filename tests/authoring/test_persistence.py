import copy
import hashlib
import json

import pytest

from archpapercraft.authoring import (
    AuthorProject,
    LegacyProject,
    ProjectFormatError,
    UnsupportedOperationError,
    load_project,
)


def authored():
    p = AuthorProject.new(name="Žlutá vlastní stěna")
    sid = p.add_surface(p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]]))
    p.set_placement(
        p.part_for_surface(sid),
        p.pages[0].id,
        40,
        50,
        30,
        position_locked=True,
        rotation_locked=True,
    )
    return p, sid


def test_complete_roundtrip_with_stale_geometry_and_author_layout(tmp_path):
    p, sid = authored()
    profile = p.profiles[p.surfaces[sid].profile_id]
    p.move_vertex(profile.id, profile.vertices[2].id, [10000, 5000])
    destination = tmp_path / "vlastní.apcraft"
    p.save(destination)
    reopened = load_project(destination)
    assert reopened.to_dict() == p.to_dict()
    assert reopened.parts[p.part_for_surface(sid)].stale
    assert reopened.placements[p.part_for_surface(sid)].rotation_locked


def test_interrupted_save_preserves_original_and_removes_only_owned_temporary(
    tmp_path, monkeypatch
):
    p, sid = authored()
    path = tmp_path / "model.apcraft"
    p.save(path)
    original = path.read_bytes()
    import archpapercraft.authoring.project as module

    monkeypatch.setattr(
        module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk unavailable"))
    )
    with pytest.raises(OSError):
        p.save(path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(schema_version=999),
        lambda d: d.update(schema_version=True),
        lambda d: d.update(unknown=True),
        lambda d: next(iter(d["profiles"].values())).update(unknown=True),
        lambda d: next(iter(d["profiles"].values()))["vertices"][0].update(unknown=True),
        lambda d: d.update(next_part_number=1),
        lambda d: d.update(scale=float("nan")),
    ],
)
def test_malformed_or_future_schema_is_rejected(mutation):
    p, _ = authored()
    data = copy.deepcopy(p.to_dict())
    mutation(data)
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)


@pytest.mark.parametrize(
    "content", ['{"application":1,"application":2}', '{"scale":NaN}', "[1,2,3]", "{bad"]
)
def test_bad_json_has_concrete_format_error(tmp_path, content):
    path = tmp_path / "invalid.apcraft"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ProjectFormatError):
        load_project(path)


def test_legacy_read_only_no_writer_overwrite_or_raw_mutation(tmp_path):
    path = tmp_path / "old.apcraft"
    path.write_text(json.dumps({"version": "0.2.0", "settings": {}, "scene": []}), encoding="utf-8")
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    legacy = load_project(path)
    assert isinstance(legacy, LegacyProject)
    legacy.raw["scene"].append({"bad": True})
    assert legacy.raw["scene"] == []
    with pytest.raises(UnsupportedOperationError):
        legacy.save(tmp_path / "copy.apcraft")
    p, _ = authored()
    with pytest.raises(UnsupportedOperationError):
        p.save(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
