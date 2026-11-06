"""Read both vector formats and verify declared construction scope survives export."""

import copy
import hashlib
import json
import xml.etree.ElementTree as ET

import pytest
from pypdf import PdfReader
from test_bend_adapter import own_wall_base

from archpapercraft.exporter.author_export import SnapshotError, export_all


def actual_snapshot():
    project, cid, *_ = own_wall_base()
    project.set_material_profile(thickness_mm=0.2, clearance_mm=0.02, bend_radius_mm=0.05)
    project.recompute()
    for index, pid in enumerate(project.parts):
        page = project.pages[0].id if index == 0 else project.add_page()
        project.set_placement(pid, page, 40, 50)
    for issue in project.validate_layout():
        if issue.severity == "warning":
            project.acknowledge(issue.id)
    return project.snapshot(), cid


def files(directory):
    return {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}


def test_actual_material_report_survives_svg_pdf_and_manifest_as_the_same_content(tmp_path):
    snapshot, cid = actual_snapshot()
    checks = snapshot["construction_checks"]
    assert checks["connector_bends"][cid]["status"] == "CLEAR"
    export_all(snapshot, tmp_path)
    expected = json.dumps(checks, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(expected.encode("utf8")).hexdigest()
    manifest = json.loads((tmp_path / ".author-export.json").read_text(encoding="utf8"))
    assert manifest["construction_checks"] == json.loads(expected)
    for svg in tmp_path.glob("*.svg"):
        root = ET.parse(svg).getroot()
        assert root.attrib["data-construction-checks-digest"] == digest
        node = root.find("{http://www.w3.org/2000/svg}metadata[@id='construction-checks']")
        assert json.loads(node.text) == json.loads(expected)
    pdf = PdfReader(tmp_path / "model.pdf")
    summary = json.loads(pdf.metadata["/Keywords"])
    assert summary["construction_checks_digest"] == digest
    assert summary["material_profile"]["thickness_mm"] == 0.2
    assert summary["connector_statuses"][cid] == "CLEAR"
    assert summary["physical_build"] == "NOT_VERIFIED"
    assert manifest["construction_summary"] == summary


@pytest.mark.parametrize("status", ["COLLISION", "UNRESOLVED"])
def test_writer_refuses_blocked_checks_without_touching_existing_bundle(tmp_path, status):
    snapshot, cid = actual_snapshot()
    export_all(snapshot, tmp_path)
    before = files(tmp_path)
    invalid = copy.deepcopy(snapshot)
    invalid["construction_checks"]["connector_bends"][cid]["status"] = status
    with pytest.raises(SnapshotError):
        export_all(invalid, tmp_path)
    assert files(tmp_path) == before
