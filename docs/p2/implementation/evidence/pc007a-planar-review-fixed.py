"""Independent follow-up oracles on the archived 820ab66 source, not working HEAD."""

import hashlib
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from shapely import Point

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.curve_material import surface_envelopes

PIN = "820ab6672d6a3f252391807b4c2c626c51a040bb"


def circle(project, radius=2, center=(0, 0)):
    x, y = center
    return project.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [x + radius, y],
                "end": [x - radius, y],
                "center": [x, y],
                "sweep_deg": 180,
            },
            {
                "kind": "arc",
                "start": [x - radius, y],
                "end": [x + radius, y],
                "center": [x, y],
                "sweep_deg": 180,
            },
        ]
    )


def curved_workflow():
    p = AuthorProject.new(scale=1)
    s = p.add_surface(circle(p))
    p.set_placement(p.part_for_surface(s), p.pages[0].id, 100, 100)
    return p


def rectangle(p):
    return p.part_for_surface(p.add_surface(p.add_profile([[0, 0], [10, 0], [10, 10], [0, 10]])))


def test_exact_archived_module_and_source_hash_manifest():
    import archpapercraft.authoring.curve_material as module

    root = Path(os.environ["PC007A_REVIEW_ARCHIVE"])
    assert (
        Path(module.__file__).resolve() == root / "src/archpapercraft/authoring/curve_material.py"
    )
    tracked = sorted((root / "src/archpapercraft").rglob("*.py"))
    manifest = {
        str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for f in tracked
    }
    assert len(manifest) > 40
    import json

    Path(os.environ["PC007A_REVIEW_MANIFEST"]).write_text(
        json.dumps(
            {"source_pin": PIN, "module_path": module.__file__, "files": manifest}, indent=2
        ),
        encoding="utf8",
    )


@pytest.mark.parametrize("gap,unresolved", [(0.009, True), (0.015, True), (0.025, False)])
def test_output_reservation_is_applied_to_both_straight_neighbors(gap, unresolved):
    p = curved_workflow()
    a, b = rectangle(p), rectangle(p)
    p.set_placement(a, p.pages[0].id, 40, 40)
    p.set_placement(b, p.pages[0].id, 50 + gap, 40)
    issues = p.validate_layout()
    matching = [i for i in issues if i.code == "CURVE_LAYOUT_UNRESOLVED"]
    # At .015 no single .01 expansion reaches the original neighbor. Only
    # correct reservation of both printed boundaries detects the uncertainty.
    assert bool(matching) == unresolved
    if unresolved:
        assert all(i.severity == "error" for i in matching)
        for i in matching:
            before = p.to_dict()
            with pytest.raises(ValidationError):
                p.acknowledge(i.id)
            assert p.to_dict() == before
        with pytest.raises(ValidationError):
            p.snapshot()
    else:
        assert p.snapshot()


@pytest.mark.parametrize("x,blocked", [(0.005, True), (0.025, False)])
def test_physical_sheet_output_uncertainty_is_hard_error(x, blocked):
    p = curved_workflow()
    a = rectangle(p)
    p.set_placement(a, p.pages[0].id, x, 40)
    found = [i for i in p.validate_layout() if i.code == "CURVE_SHEET_UNRESOLVED"]
    assert bool(found) == blocked
    assert all(i.severity == "error" for i in found)


@pytest.mark.parametrize("scale", [1, 0.01])
def test_circle_hole_bounds_contain_analytic_material_and_exclude_void(scale):
    p = AuthorProject.new(scale=scale)
    outer = p.add_profile([[0, 0], [40, 0], [40, 40], [0, 40]])
    hole = circle(p, 5, (20, 20))
    s = p.add_surface(outer, [hole])
    env = surface_envelopes(p, s, paper=True)
    assert not env.possible.covers(Point(20 * scale, 20 * scale))
    for i in range(71):
        theta = (i + 0.317) * math.tau / 71
        for radius in (4.999, 5.001, 5.01):
            witness = Point(
                scale * (20 + radius * math.cos(theta)), scale * (20 + radius * math.sin(theta))
            )
            # Exact physical material is outside the analytic radius-five hole.
            if radius > 5:
                assert env.possible.covers(witness)
            elif env.guaranteed.covers(witness):
                pytest.fail("Guaranteed material includes true circular void")


def test_no_output_reservation_is_invented_in_all_straight_workflow():
    p = AuthorProject.new(scale=1)
    a, b = rectangle(p), rectangle(p)
    p.set_placement(a, p.pages[0].id, 40, 40)
    p.set_placement(b, p.pages[0].id, 50.015, 40)
    assert not p.validate_layout()
    assert p.snapshot()


@pytest.mark.parametrize("angle", [37, 141, 283])
def test_both_neighbor_reservations_survive_page_rotation(angle):
    p = curved_workflow()
    a, b = rectangle(p), rectangle(p)
    radians = math.radians(angle)
    p.set_placement(a, p.pages[0].id, 60, 60, angle)
    p.set_placement(
        b, p.pages[0].id, 60 + 10.015 * math.cos(radians), 60 + 10.015 * math.sin(radians), angle
    )
    issues = p.validate_layout()
    assert any(i.code == "CURVE_LAYOUT_UNRESOLVED" for i in issues)
    with pytest.raises(ValidationError):
        p.snapshot()


def test_actual_staged_svg_shallow_crossing_blocks_publication_atomically(tmp_path, monkeypatch):
    from archpapercraft.exporter import author_export
    from archpapercraft.exporter.curve_output_validation import CurveOutputError

    p = curved_workflow()
    snapshot = p.snapshot()
    directory = tmp_path / "bundle"
    author_export.export_all(snapshot, directory)
    before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in directory.iterdir()}
    original = author_export._svg

    def shallow_crossing(*args, **kwargs):
        original(*args, **kwargs)
        path = args[4]
        tree = ET.parse(path)
        ns = "{http://www.w3.org/2000/svg}"
        cut = tree.find(f".//{ns}g[@data-role='CUT']")
        for child in list(cut):
            cut.remove(child)
        ET.SubElement(
            cut, ns + "path", {"d": "M 0 .0005 C 3 -.001 7 -.001 10 .0005 L 10 0 L 0 0 Z"}
        )
        tree.write(path, encoding="utf8", xml_declaration=True)

    monkeypatch.setattr(author_export, "_svg", shallow_crossing)
    with pytest.raises(CurveOutputError):
        author_export.export_all(snapshot, directory)
    after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in directory.iterdir()}
    assert after == before
    assert not list(tmp_path.glob(".author-export-*"))
