"""Tests for PDF / SVG / DXF export (smoke tests — verify no exceptions)."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import make_box_mesh
from archpapercraft.layout_packer.packer import PageSettings, pack_parts
from archpapercraft.seam_editor.auto_seams import auto_seams
from archpapercraft.tabs_generator.markings import classify_folds
from archpapercraft.tabs_generator.tabs import TabSettings, generate_tabs_for_part
from archpapercraft.unfolder.approx_unfold import unfold_all_parts


def _prepare():
    """Prepare a box, seams, unfolded parts, tabs, markings."""
    mesh = make_box_mesh(2, 3, 4)
    sg = auto_seams(mesh, sharp_angle_deg=60)
    parts = unfold_all_parts(mesh, sg)

    outlines = [p.vertices_2d for p in parts]
    ps = PageSettings()
    layout = pack_parts(outlines, ps, scale=1.0)

    tabs_list = []
    markings_list = []
    edge_ids = sg.compute_edge_match_ids()
    ts = TabSettings()
    for part in parts:
        tabs_list.append(generate_tabs_for_part(part.vertices_2d, part.cut_edges, edge_ids, ts))
        markings_list.append(classify_folds(part.vertices_2d, part.fold_edges, part.part_id))

    return parts, layout, ps, tabs_list, markings_list


class TestPDFExport:
    def test_export_creates_file(self):
        from archpapercraft.exporter.pdf_export import export_pdf

        parts, layout, ps, tabs, marks = _prepare()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.pdf"
            export_pdf(path, parts, layout, ps, tabs, marks, scale=1.0)
            assert path.exists()
            assert path.stat().st_size > 0


class TestSVGExport:
    def test_export_creates_file(self):
        from archpapercraft.exporter.svg_export import export_svg

        parts, layout, ps, tabs, marks = _prepare()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.svg"
            export_svg(path, parts, layout, ps, tabs, marks, scale=1.0)
            assert path.exists()
            assert path.stat().st_size > 0


class TestDXFExport:
    def test_export_creates_file(self):
        from archpapercraft.exporter.dxf_export import export_dxf

        parts, layout, ps, tabs, marks = _prepare()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.dxf"
            export_dxf(path, parts, layout, ps, tabs, marks, scale=1.0)
            assert path.exists()
            assert path.stat().st_size > 0
