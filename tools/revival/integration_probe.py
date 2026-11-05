"""P0 diagnostic experiments. Exit success means evidence collected, not product PASS."""
from __future__ import annotations

import json
import math
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch
from pathlib import Path

import numpy as np

from archpapercraft.exporter.pdf_export import export_pdf
from archpapercraft.exporter.svg_export import export_svg
from archpapercraft.layout_packer.packer import (LayoutResult, Orientation, PageSettings, PartRotation, PlacedPart, pack_parts)
from archpapercraft.project_io.project import Project
from archpapercraft.scene_graph.node import NodeType
from archpapercraft.tabs_generator.tabs import TabSettings, generate_tabs_for_part
from archpapercraft.unfolder.exact_unfold import UnfoldedPart

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/revival/evidence"


def rect(w, h):
    return np.array([[0., 0.], [w, 0.], [w, h], [0., h]])


def part(w=100., h=40.):
    return UnfoldedPart(0, rect(w, h), np.array([[0, 1, 2], [0, 2, 3]]), np.arange(4), cut_edges=[(0, 1), (1, 2), (2, 3), (3, 0)])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    scene = Project().scene
    parent = scene.add_node("parent", NodeType.GROUP)
    parent.transform.position[:] = [100, 200, 300]
    parent.transform.rotation[:] = [0, 0, 90]
    child = scene.add_node("child", NodeType.PRIMITIVE_BOX, parent=parent, dx=10., dy=20., dz=30.)
    child.transform.position[:] = [5, 0, 0]
    scene.rebuild_meshes()
    actual = scene.collect_visible_meshes(world_space=True)[0].vertices
    local = child.mesh.vertices + [5, 0, 0]
    expected = np.column_stack([-local[:, 1], local[:, 0], local[:, 2]]) + [100, 200, 300]
    report["parent_transform"] = dict(max_vertex_error_mm=float(np.max(np.linalg.norm(actual-expected, axis=1))), actual_first=actual[0].tolist(), expected_first=expected[0].tolist())
    parent.visible = False
    report["hidden_parent"] = dict(visible_meshes=len(scene.collect_visible_meshes(True)), expected=0)
    sample_path = ROOT / "samples/house_with_dome.apcraft"
    sample = Project.load(sample_path)
    raw = json.loads(sample_path.read_text(encoding="utf-8"))
    saved = sample.to_dict()
    report["sample_roundtrip"] = dict(nodes=len(sample.scene.root.children), semantic_equal=raw == saved, original_preserved=True)
    from archpapercraft.core_geometry.units import to_mm
    length = sample.scene.root.children[0].parameters["length"]
    report["sample_units"] = dict(internal_unit=raw["settings"]["_internal_unit"], model_length=length, expected_paper_mm=length/100, pipeline_paper_mm=length*to_mm(1.,sample.settings.units)*sample.settings.scale_factor)
    unknown = dict(raw, version="999.0", future_payload={"must_preserve": True})
    loaded = Project.from_dict(unknown)
    report["future_schema"] = dict(accepted=True, saved_version=loaded.to_dict()["version"], unknown_preserved="future_payload" in loaded.to_dict())
    with tempfile.TemporaryDirectory(prefix='papercraft-save-fault-') as temp:
        target = Path(temp)/'project.apcraft'
        specimen = Project()
        specimen.save(target)
        previous = target.read_bytes()
        def interrupted_write(path, text, **kwargs):
            with path.open('wb') as stream:
                stream.write(text.encode('utf-8')[:12])
            raise OSError('Injected interrupted save after partial write')
        with patch.object(Path,'write_text',interrupted_write):
            try:
                specimen.save(target)
            except OSError as exc:
                report['save_fault'] = dict(error=str(exc),previous_bytes=len(previous),remaining_bytes=target.stat().st_size,original_preserved=target.read_bytes()==previous)
    obj = part(180., 40.)
    layout = pack_parts([obj.vertices_2d], PageSettings())
    tabs = generate_tabs_for_part(obj.vertices_2d, [(0, 3)], {}, TabSettings())
    tab_min = np.min(np.vstack([t.polygon for t in tabs]), axis=0)+layout.placements[0].offset+10
    report["tab_envelope"] = dict(expected_margin_mm=10, actual_min_mm=tab_min.tolist(), packed_min_mm=(layout.placements[0].bbox_min+10).tolist())
    from archpapercraft.commands.command_stack import AddNodeCommand, CommandStack
    stack = CommandStack()
    stack.execute(AddNodeCommand(scene, 'A', NodeType.PRIMITIVE_BOX))
    stack.mark_saved()
    stack.undo()
    stack.execute(AddNodeCommand(scene, 'B', NodeType.PRIMITIVE_BOX))
    report['dirty_branch_same_depth'] = dict(expected_modified=True, actual_modified=stack.is_modified)
    obj = part()
    layout = LayoutResult(1, [PlacedPart(0, 0, np.array([15., 25.]), rotation=PartRotation.DEG_90)])
    ps = PageSettings(orientation=Orientation.LANDSCAPE)
    export_svg(OUT/"diagnostic-landscape.svg", [obj], layout, ps)
    export_pdf(OUT/"diagnostic-landscape.pdf", [obj], layout, ps, scale_label="1:100")
    root = ET.parse(OUT/"diagnostic-landscape.svg").getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    lines = root.findall(".//s:g[@id='cut']/s:line", ns)
    edges = [math.hypot(float(e.attrib['x2'])-float(e.attrib['x1']),float(e.attrib['y2'])-float(e.attrib['y1'])) for e in lines]
    coords = np.array([[float(e.attrib[k]) for k in ('x1','y1')] for e in lines] + [[float(e.attrib[k]) for k in ('x2','y2')] for e in lines])
    report["svg_export"] = dict(width=root.attrib['width'], height=root.attrib['height'], expected_landscape=[297,210], groups=[g.attrib.get('id') for g in root.findall('s:g',ns)], cut_lengths_mm=edges, actual_bounds_mm=[coords.min(axis=0).tolist(),coords.max(axis=0).tolist()], expected_rotated_size_mm=[40,100], actual_size_mm=np.ptp(coords,axis=0).tolist())
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    pdf = QPdfDocument()
    pdf.load(str(OUT/"diagnostic-landscape.pdf"))
    size = pdf.pagePointSize(0)
    report["pdf_export"] = dict(page_count=pdf.pageCount(), page_mm=[size.width()*25.4/72,size.height()*25.4/72], text=pdf.getAllText(0).text())
    pdf.render(0,QSize(1188,840)).save(str(OUT/"diagnostic-landscape-pdf.png"))
    pdf.close()
    try:
        import pypdf
    except ImportError:
        report["pdf_structure"] = "NOT_RUN: pypdf unavailable; Qt render and source inspection only"
    else:
        page = pypdf.PdfReader(OUT/"diagnostic-landscape.pdf").pages[0]
        content = page.get_contents().get_data().decode('latin1')
        report["pdf_structure"] = dict(vector_line_operators=content.count(' l '), image_xobjects=str(page.get('/Resources',{}).get('/XObject',{})), content=content)
        from pypdf.generic import ContentStream
        points = [list(map(float,operands)) for operands,operator in ContentStream(page.get_contents(),page.pdf).operations if operator in (b'm',b'l')]
        paper_points = np.array([[x*25.4/72, float(page.mediabox.height)*25.4/72-y*25.4/72] for x,y in points])
        report['svg_pdf_layout_comparison'] = dict(svg_top_left_mm=coords.min(axis=0).tolist(),pdf_top_left_mm=paper_points.min(axis=0).tolist(),pdf_bottom_right_mm=paper_points.max(axis=0).tolist(),same_top_left=bool(np.allclose(coords.min(axis=0),paper_points.min(axis=0),atol=.01)))
    print(json.dumps(report,indent=2,ensure_ascii=False))
    (OUT/"integration-results.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")


if __name__ == "__main__":
    main()
