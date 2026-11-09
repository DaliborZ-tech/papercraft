"""Corruption of staged manufacturing bytes must never replace an old bundle."""

import hashlib
import json
import xml.etree.ElementTree as ET

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter import author_export
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.svg_curve_validation import validate_svg_curve_geometry

NS = "{http://www.w3.org/2000/svg}"


def curved_snapshot():
    project = AuthorProject.new(scale=1)
    profile = project.add_profile([[0, 0], [40, 0], [40, 40], [0, 40]])
    hole = project.add_profile(segments=[
        {"kind": "arc", "start": [25, 20], "end": [15, 20],
         "data": {"center": [20, 20], "sweep_deg": 180}},
        {"kind": "arc", "start": [15, 20], "end": [25, 20],
         "data": {"center": [20, 20], "sweep_deg": 180}},
    ])
    sid = project.add_surface(profile, [hole])
    pid = project.part_for_surface(sid)
    project.set_placement(pid, project.pages[0].id, 40, 50, 17)
    return project, pid


def hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}


def test_actual_svg_and_pdf_manufacturing_are_checked_before_publication(tmp_path):
    project, pid = curved_snapshot()
    project.add_page()
    author_export.export_all(project.snapshot(), tmp_path / "bundle")
    manifest = json.loads((tmp_path / "bundle/.author-export.json").read_text())
    actual = manifest["actual_curve_output_checks"]
    assert actual["pdf"]["status"] == "VALID"
    assert actual["pdf"]["parts"][pid]["loop_count"] == 2
    assert actual["svg"][0]["parts"][pid]["loop_count"] == 2
    assert actual["svg"][0]["status"] == "VALID"
    assert actual["svg"][1]["status"] == "NO_MATERIAL"
    assert actual["pdf"]["physical_build"] == "NOT_VERIFIED"
    assert actual["pdf"]["new_user_test"] == "NOT_RUN"


@pytest.mark.parametrize("format_name", ["svg", "pdf"])
def test_missing_actual_hole_or_pdf_cut_role_preserves_every_previous_byte(
    tmp_path, monkeypatch, format_name,
):
    project, _ = curved_snapshot()
    directory = tmp_path / "bundle"
    snapshot = project.snapshot()
    author_export.export_all(snapshot, directory)
    before = hashes(directory)
    if format_name == "svg":
        original = author_export._svg

        def lose_hole(*args, **kwargs):
            original(*args, **kwargs)
            path = args[4]
            tree = ET.parse(path)
            cut = tree.find(f".//{NS}g[@data-role='CUT']")
            assert len(cut) == 2
            cut.remove(cut[-1])
            tree.write(path, encoding="utf8", xml_declaration=True)

        monkeypatch.setattr(author_export, "_svg", lose_hole)
    else:
        original = author_export._pdf

        def lose_cut(*args, **kwargs):
            bound = original(*args, **kwargs)
            path = args[3]
            reader = PdfReader(path)
            writer = PdfWriter()
            for page in reader.pages:
                contents = page.get_contents().get_data()
                assert b"/APRole_CUT BMC" in contents
                stream = DecodedStreamObject()
                stream.set_data(contents.replace(b"/APRole_CUT BMC", b"/APRole_ARTWORK BMC"))
                page[NameObject("/Contents")] = stream
                writer.add_page(page)
            with path.open("wb") as handle:
                writer.write(handle)
            return bound

        monkeypatch.setattr(author_export, "_pdf", lose_cut)
    with pytest.raises(CurveOutputError):
        author_export.export_all(snapshot, directory)
    assert hashes(directory) == before
    assert not list(tmp_path.glob(".author-export-*"))


def test_actual_svg_shallow_crossing_is_not_mistaken_for_valid_source_metadata(tmp_path):
    project, pid = curved_snapshot()
    author_export.export_all(project.snapshot(), tmp_path / "bundle")
    path = next((tmp_path / "bundle").glob("*.svg"))
    tree = ET.parse(path)
    cut = tree.find(f".//{NS}g[@data-role='CUT']")
    for node in list(cut):
        cut.remove(node)
    ET.SubElement(cut, NS + "path", {
        "d": "M 0 .0005 C 3 -.001 7 -.001 10 .0005 L 10 0 L 0 0 Z",
    })
    tree.write(path, encoding="utf8", xml_declaration=True)
    with pytest.raises(CurveOutputError):
        validate_svg_curve_geometry(path, {pid: {"name": "Arched test", "page_index": 0,
                                                "loop_count": 1}})
