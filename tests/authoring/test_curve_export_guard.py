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


def test_v02_coarse_pdf_circle_exceeding_normative_area_is_blocked_and_old_bundle_preserved(
    tmp_path, monkeypatch,
):
    project = AuthorProject.new(scale=1)
    outer = project.add_profile([[0, 0], [120, 0], [120, 100], [0, 100]])
    hole = project.add_profile(segments=[
        {"kind": "arc", "start": [40, 50], "end": [80, 50],
         "data": {"center": [60, 50], "sweep_deg": 180}},
        {"kind": "arc", "start": [80, 50], "end": [40, 50],
         "data": {"center": [60, 50], "sweep_deg": 180}},
    ])
    sid = project.add_surface(outer, [hole])
    project.set_placement(project.part_for_surface(sid), project.pages[0].id, 20, 20)
    snapshot = project.snapshot()
    directory = tmp_path / "bundle"
    author_export.export_all(snapshot, directory)
    manifest = json.loads((directory / ".author-export.json").read_text())
    assert manifest["actual_curve_output_checks"]["area_agreement"]["status"] == "VERIFIED"
    before = hashes(directory)
    # The previous writer's .001 paper-mm positional budget met position checks,
    # but its actual net wall lost .03634 mm2. That is not permission to relax AC.
    original_cubics = author_export._arc_cubics
    calls = []

    def backend_ignores_requested_precision(arc, *, tolerance_mm=None):
        calls.append(tolerance_mm)
        return original_cubics(arc, tolerance_mm=0.001)

    monkeypatch.setattr(author_export, "_arc_cubics", backend_ignores_requested_precision)
    with pytest.raises(CurveOutputError, match="plošnou shodu") as caught:
        author_export.export_all(snapshot, directory)
    assert caught.value.part_id == project.part_for_surface(sid)
    assert caught.value.report["status"] == "REJECTED"
    assert hashes(directory) == before
    assert min(value for value in calls if value is not None) < 0.00001


def test_export_automatically_tightens_arc_precision_instead_of_asking_for_geometry_knowledge(
    tmp_path, monkeypatch,
):
    project = AuthorProject.new(scale=1)
    profile = project.add_profile(segments=[
        {"kind": "arc", "start": [20, 0], "end": [-20, 0],
         "data": {"center": [0, 0], "sweep_deg": 180}},
        {"kind": "arc", "start": [-20, 0], "end": [20, 0],
         "data": {"center": [0, 0], "sweep_deg": 180}},
    ])
    sid = project.add_surface(profile)
    project.set_placement(project.part_for_surface(sid), project.pages[0].id, 50, 50)
    monkeypatch.setattr(author_export, "PDF_ARC_TOLERANCE_MM", 0.001)
    author_export.export_all(project.snapshot(), tmp_path / "bundle")
    manifest = json.loads((tmp_path / "bundle/.author-export.json").read_text())
    attempts = manifest["pdf_arc_approximation"]["precision_attempts"]
    assert attempts[0]["status"] == "AREA_BUDGET_NOT_MET"
    assert attempts[-1]["status"] == "ACTUAL_GEOMETRY_AND_AREA_VERIFIED"
    assert len(attempts) <= 4
    assert manifest["actual_curve_output_checks"]["area_agreement"]["status"] == "VERIFIED"


def test_large_rotated_part_keeps_normative_area_without_rounding_its_ctm_to_six_digits(tmp_path):
    project = AuthorProject.new(scale=1)
    large = project.add_surface(project.add_profile([[0, 0], [135, 0], [135, 200], [0, 200]]))
    large_pid = project.part_for_surface(large)
    project.set_placement(large_pid, project.pages[0].id, 70, 11, 17)
    circle = project.add_profile(segments=[
        {"kind": "arc", "start": [2, 0], "end": [-2, 0],
         "data": {"center": [0, 0], "sweep_deg": 180}},
        {"kind": "arc", "start": [-2, 0], "end": [2, 0],
         "data": {"center": [0, 0], "sweep_deg": 180}},
    ])
    curved = project.add_surface(circle)
    project.add_page()
    project.set_placement(project.part_for_surface(curved), project.pages[1].id, 50, 50)
    author_export.export_all(project.snapshot(), tmp_path / "bundle")
    manifest = json.loads((tmp_path / "bundle/.author-export.json").read_text())
    bounds = manifest["actual_curve_output_checks"]["pdf"]["parts"][large_pid][
        "material_area_bounds_mm2"
    ]
    # Independent rectangle area. Exact raw CTM tokens retain the rotation; the
    # six-digit CTM previously exceeded the relative 1e-6 area acceptance here.
    from fractions import Fraction

    assert abs(float(Fraction(bounds["lower"]))-135*200) < 1e-8
    assert abs(float(Fraction(bounds["upper"]))-135*200) < 1e-8


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
