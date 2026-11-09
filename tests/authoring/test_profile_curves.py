"""Authored curve identity, planar material and native vector cache integration."""

import copy
import json
import math
from pathlib import Path

import pytest

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.project import SCHEMA_VERSION
from archpapercraft.exporter.author_export import export_all


def quarter_profile(project):
    return project.add_profile(segments=[
        {"kind": "arc", "start": [20, 0], "end": [0, 20],
         "data": {"center": [0, 0], "sweep_deg": 90}},
        {"kind": "line", "start": [0, 20], "end": [0, 0]},
        {"kind": "line", "start": [0, 0], "end": [20, 0]},
    ])


def circle_profile(project, radius=2, center=(7, 7)):
    x, y = center
    return project.add_profile(segments=[
        {"kind": "arc", "start": [x + radius, y], "end": [x - radius, y],
         "data": {"center": list(center), "sweep_deg": 180}},
        {"kind": "arc", "start": [x - radius, y], "end": [x + radius, y],
         "data": {"center": list(center), "sweep_deg": 180}},
    ])


def test_two_arc_circle_has_real_material_and_native_paths_not_a_diameter():
    project = AuthorProject.new(scale=1)
    pid = circle_profile(project, 20, (0, 0))
    sid = project.add_surface(pid)
    part = project.parts[project.part_for_surface(sid)]
    assert len(part.polygons[sid][0]) > 100
    arcs = [c for p in part.paths["CUT"] for c in p["commands"] if c[0] == "A"]
    assert len(arcs) >= 2
    assert all(math.isclose(c[1], 20, abs_tol=1e-12) for c in arcs)
    assert all(edge["edge_id"] in {s.id for s in project.profiles[pid].segments}
               for edge in part.edges)
    assert AuthorProject.from_dict(project.to_dict()).to_dict() == project.to_dict()


@pytest.mark.parametrize("radius,small", [(0.1, True), (2, False), (20, False)])
def test_small_detail_checks_true_circle_size_instead_of_tessellation(radius, small):
    project = AuthorProject.new(scale=1)
    sid = project.add_surface(circle_profile(project, radius, (0, 0)))
    project.set_placement(project.part_for_surface(sid), project.pages[0].id, 50, 50)
    assert any(i.code == "SMALL_DETAIL" for i in project.validate_layout()) == small


def test_arc_region_hole_save_reopen_manual_layout_and_both_vector_outputs(tmp_path):
    project = AuthorProject.new(scale=1)
    outer = quarter_profile(project)
    hole = circle_profile(project)
    sid = project.add_surface(outer, [hole])
    part_id = project.part_for_surface(sid)
    project.set_placement(part_id, project.pages[0].id, 60, 60, 30,
                          position_locked=True, rotation_locked=True)
    project.recompute()
    target = tmp_path / "curves.apcraft"
    project.save(target)
    restored = AuthorProject.load(target)
    assert restored.to_dict() == project.to_dict()
    assert not restored.requires_save_as
    paths = restored.parts[part_id].paths["CUT"]
    assert len(paths) == 2 and all("commands" in p for p in paths)
    export_all(restored.snapshot(), tmp_path / "vectors")
    from xml.etree import ElementTree as ET

    svg = ET.parse(next((tmp_path / "vectors").glob("*.svg"))).getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    cut = svg.findall(".//s:g[@data-role='CUT']/s:path", ns)
    assert len(cut) == 2 and all("A " in p.attrib["d"] for p in cut)
    assert all(p.attrib.get("fill-rule") == "evenodd" for p in cut)
    from pypdf import PdfReader
    from pypdf.generic import ContentStream

    pdf = PdfReader(tmp_path / "vectors/model.pdf")
    ops = [op for _, op in ContentStream(pdf.pages[0].get_contents(), pdf).operations]
    assert b"c" in ops and not pdf.pages[0]["/Resources"].get("/XObject")


def test_source_vertex_edit_keeps_arc_bulge_and_handles_with_stable_identities():
    project = AuthorProject.new(scale=1)
    pid = quarter_profile(project)
    sid = project.add_surface(pid)
    ids = [s.id for s in project.profiles[pid].segments]
    vertex_ids = [v.id for v in project.profiles[pid].vertices]
    project.move_vertex(pid, vertex_ids[0], [25, 0])
    project.recompute()
    profile = project.profiles[pid]
    assert [s.id for s in profile.segments] == ids
    assert [v.id for v in profile.vertices] == vertex_ids
    assert profile.segments[0].data["sweep_deg"] == 90
    assert project.parts[project.part_for_surface(sid)].stale is False
    cubic = project.add_profile(segments=[{
        "kind": "cubic", "start": [0, 0], "end": [10, 0],
        "control1": [2, 3], "control2": [8, 3],
    }], closed=False)
    source = project.profiles[cubic]
    project.move_vertex(cubic, source.vertices[0].id, [1, 2])
    assert source.segments[0].data == {"control1": [3, 5], "control2": [8, 3]}


def test_independent_profile_copy_scales_arc_controls_and_can_be_edited_separately():
    project = AuthorProject.new(scale=1)
    pid = quarter_profile(project)
    before = copy.deepcopy(project.profiles[pid])
    copied = project.copy_profile(pid, factor=1.2,
                                  plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]})
    profile = project.profiles[copied]
    assert profile.points == [[24, 0], [0, 24], [0, 0]]
    assert profile.plane.origin == [0, 0, 30]
    assert project.profiles[pid] == before
    assert not {s.id for s in profile.segments} & {s.id for s in before.segments}
    project.set_profile_segment(copied, profile.segments[0].id, kind="arc",
                                data={"center": [0, 0], "sweep_deg": 90})
    assert project.profiles[pid] == before


def test_invalid_curve_change_rolls_back_source_and_existing_layout():
    project = AuthorProject.new(scale=1)
    pid = quarter_profile(project)
    sid = project.add_surface(pid)
    part = project.part_for_surface(sid)
    project.set_placement(part, project.pages[0].id, 50, 70, 17)
    before = copy.deepcopy(project.to_dict())
    with pytest.raises(ValidationError):
        project.set_profile_segment(pid, project.profiles[pid].segments[0].id,
                                    kind="arc", data={"center": [3, 4], "sweep_deg": 0})
    assert project.to_dict() == before


def test_published_schema_three_is_copy_only_even_after_undo_and_failed_command(tmp_path):
    source = (Path(__file__).resolve().parents[2] / "docs/p2/implementation/evidence/"
              "pc006b-desktop-eb08f97-run06/model-A/model-A.apcraft")
    original = tmp_path / "published-B.apcraft"
    original.write_bytes(source.read_bytes())
    before = original.read_bytes()
    controller = AuthorController()
    controller.open(original)
    assert controller.project.loaded_from_schema == 3 and controller.copy_source_path == original
    controller.execute("Edit model name", lambda p: setattr(p, "name", "Changed copy"))
    controller.undo()
    with pytest.raises(ValueError):
        controller.save(original)
    with pytest.raises(ValidationError):
        controller.execute("Fail", lambda p: p.set_scale(0))
    with pytest.raises(ValueError):
        controller.save(original)
    target = tmp_path / "profiles-copy.apcraft"
    controller.save(target)
    assert json.loads(target.read_text(encoding="utf8"))["schema_version"] == SCHEMA_VERSION
    assert original.read_bytes() == before
