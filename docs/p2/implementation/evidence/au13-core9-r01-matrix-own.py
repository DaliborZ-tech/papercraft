"""Independent authority/orphan/layout checks; this is not a desktop proof."""

import copy
import hashlib
import json
import os
from fractions import Fraction as Q
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring import project as project_module
from archpapercraft.authoring.errors import UnsupportedOperationError
from archpapercraft.authoring.project import ProjectFormatError
from archpapercraft.exporter.author_export import export_all

ROOT = Path(__file__).resolve().parents[4]
assert Path(project_module.__file__).resolve() == ROOT / "src/archpapercraft/authoring/project.py"


def source_profile(p, kind, *, z=0, factor=1):
    if kind == "arc":
        a, b = [20 * factor, 0], [-20 * factor, 0]
        data = {"center": [0, 0], "sweep_deg": 180}
    else:
        a, b = [0, 0], [4 * factor, 0]
        data = {"control1": [0, 4 * factor], "control2": [4 * factor, 4 * factor]}
    return p.add_profile(
        segments=[dict(kind=kind, start=a, end=b, data=data)], closed=False,
        plane=dict(origin=[0, 0, z], u=[1, 0, 0], v=[0, 1, 0]),
    )


@pytest.mark.parametrize("kind", ["arc", "cubic"])
@pytest.mark.parametrize("retired", ["root", "left", "right"])
@pytest.mark.parametrize("authority", [None, {}, False])
def test_retired_piece_cannot_reenter_even_with_invalid_or_absent_authority(kind, retired, authority):
    p = AuthorProject.new(scale=0.1)
    pid = source_profile(p, kind)
    root = p.profiles[pid].segments[0].id
    split = p.split_profile_segment(pid, root, Q(1, 3))
    p.merge_profile_segments(pid, split["segment_ids"])
    raw = p.to_dict()
    segment = raw["profiles"][pid]["segments"][0]
    segment["id"] = {"root": root, "left": split["segment_ids"][0],
                     "right": split["segment_ids"][1]}[retired]
    segment["source_reference"] = authority
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_self_consistent_foreign_source_and_all_native_cache_do_not_replace_history(kind):
    p, donor = AuthorProject.new(scale=0.1), AuthorProject.new(scale=0.1)
    pid, other = source_profile(p, kind), source_profile(donor, kind, factor=1.25)
    for project, profile_id in ((p, pid), (donor, other)):
        project.split_profile_segment(profile_id, project.profiles[profile_id].segments[0].id,
                                      Q(1, 3))
    raw, alternate = p.to_dict(), donor.to_dict()
    victim, forged = raw["profiles"][pid], alternate["profiles"][other]
    for vertex, counterpart in zip(victim["vertices"], forged["vertices"]):
        vertex["point"] = counterpart["point"]
    for segment, counterpart in zip(victim["segments"], forged["segments"]):
        segment["data"] = counterpart["data"]
        segment["source_reference"]["source"] = counterpart["source_reference"]["source"]
    # Both curves and every projected cache coordinate are valid and mutually
    # consistent, but they are not the source replayed by the victim history.
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_live_child_cannot_lose_authority_by_none_or_missing_field(kind):
    p = AuthorProject.new(scale=0.1)
    pid = source_profile(p, kind)
    p.split_profile_segment(pid, p.profiles[pid].segments[0].id, Q(2, 7))
    for omit in (False, True):
        raw = p.to_dict()
        segment = raw["profiles"][pid]["segments"][0]
        if omit:
            segment.pop("source_reference")
        else:
            segment["source_reference"] = None
        with pytest.raises(ProjectFormatError):
            AuthorProject.from_dict(raw)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
@pytest.mark.parametrize("replacement", ["whole", "mixed"])
def test_legitimate_orphan_or_mixed_generation_preserves_authored_work_and_stays_unresolved(
        kind, replacement, tmp_path):
    p = AuthorProject.new(scale=0.1)
    a, b = source_profile(p, kind), source_profile(p, kind, z=10)
    root, peer = p.profiles[a].segments[0].id, p.profiles[b].segments[0].id
    sid = p.add_loft(a, b, correspondences=[dict(first_segment_id=root, second_segment_id=peer)])
    part = p.part_for_surface(sid)
    cut = p.split_profile_segment(a, root, Q(2, 7))
    p.set_anchor(part, sid, cut["vertex_id"], cut["segment_ids"][0])
    p.recompute()
    page = p.add_page()
    p.set_placement(part, page, 67, 83, 30, position_locked=True, rotation_locked=True)
    untouched = copy.deepcopy(p.profiles[b])
    layout, frame, paths = (copy.deepcopy(p.placements[part]), copy.deepcopy(p.parts[part].frame),
                            copy.deepcopy(p.parts[part].paths))
    correspondence = copy.deepcopy(p.surfaces[sid].params["correspondences"])
    archive = copy.deepcopy(p.profile_subdivisions)
    if replacement == "whole":
        p.update_profile(a, [[0, 0], [4, 2], [8, 0]], closed=False)
        assert p.profile_subdivisions == archive
    elif kind == "cubic":
        segment = p.profiles[a].segments[0]
        data = copy.deepcopy(segment.data)
        data["control1"][1] += 0.25
        p.set_profile_segment(a, segment.id, kind="cubic", data=data)
    else:
        vertex = p.profiles[a].vertices[0]
        p.move_vertex(a, vertex.id, [vertex.point[0] + 0.25, vertex.point[1]])
    assert p.profiles[b] == untouched
    assert p.surfaces[sid].params["reference_state"] == "UNRESOLVED"
    assert p.surfaces[sid].params["correspondences"] == correspondence
    assert p.placements[part] == layout and p.parts[part].frame == frame
    assert p.parts[part].paths == paths and p.parts[part].stale
    path = tmp_path / "unresolved.apcraft"
    p.save(path)
    q = load_project(path)
    assert q.to_dict() == p.to_dict()
    before = q.to_dict()
    with pytest.raises(ValidationError):
        q.snapshot()
    assert q.to_dict() == before


ARTIFACTS = [
    "pc006a-desktop-7da2403-run04/own-model.apcraft",
    "pc007a-loft-B1-desktop-a46f179-run01/loft-B1/loft-B1.apcraft",
    "pc008-D-gothic-desktop-e7826dd-run01/D-gothic/D-gothic.apcraft",
    "pc008-AU13-line-desktop-24e0801-run05/AU13-line/AU13-line.apcraft",
    "pc007b-C-cylinder-desktop-8f1ec63-run02/C-cylinder/C-cylinder.apcraft",
    "pc007b-C-cone-desktop-8f1ec63-run02/C-cone/C-cone.apcraft",
    "pc007b-C-near-desktop-5283632-run02/C-near/C-near.apcraft",
]


@pytest.mark.parametrize("relative", ARTIFACTS)
def test_original_actual_artifacts_keep_all_source_ids_anchors_and_manual_layout(relative, tmp_path):
    evidence = Path(os.environ.get("CORE9_ARTIFACT_ROOT", ROOT / "docs/p2/implementation/evidence"))
    path = evidence / relative
    original_bytes = path.read_bytes()
    original = json.loads(original_bytes)
    digest = hashlib.sha256(original_bytes).hexdigest()
    p = load_project(path)
    assert p.requires_save_as and p.loaded_from_schema == original["schema_version"]
    copy_path = tmp_path / "copy9.apcraft"
    with pytest.raises(UnsupportedOperationError):
        p.save(path)
    p.save(copy_path)
    p = load_project(copy_path)
    for pid, profile in original["profiles"].items():
        actual = p.to_dict()["profiles"][pid]
        assert actual["vertices"] == profile["vertices"]
        for now, old in zip(actual["segments"], profile["segments"]):
            assert {key: value for key, value in now.items() if key != "source_reference"} == old
    for key in ("surfaces", "connections", "curved_connectors", "segmented_variants", "placements"):
        if key in original:
            assert p.to_dict()[key] == original[key]
    for part_id, part in p.parts.items():
        assert vars(part.frame) == original["parts"][part_id]["frame"]
    p.recompute()
    for part_id, part in p.parts.items():
        assert vars(part.frame) == original["parts"][part_id]["frame"]
        assert vars(p.placements[part_id]) == original["placements"][part_id]
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    export_all(p.snapshot(), tmp_path / "bundle")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
