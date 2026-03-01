"""SVG export using svgwrite.

Generates one SVG file per page (or one multi-page SVG) with layers:
- cut   (solid lines)
- score (fold lines — mountain / valley)
- tabs  (tab outlines + fill)
- text  (labels, numbering)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import svgwrite

from archpapercraft.layout_packer.packer import LayoutResult, PageSettings, PAPER_DIMS
from archpapercraft.tabs_generator.markings import FoldType, PartMarkings
from archpapercraft.tabs_generator.tabs import Tab
from archpapercraft.unfolder.exact_unfold import UnfoldedPart


def export_svg(
    path: str | Path,
    parts: list[UnfoldedPart],
    layout: LayoutResult,
    page_settings: PageSettings,
    tabs: list[list[Tab]] | None = None,
    markings: list[PartMarkings] | None = None,
    scale: float = 1.0,
    page_index: int = 0,
) -> None:
    """Export one page to an SVG file.

    Call once per page, or call :func:`export_all_svg` for all pages.
    """
    pw, ph = PAPER_DIMS[page_settings.paper]
    dwg = svgwrite.Drawing(
        str(path),
        size=(f"{pw}mm", f"{ph}mm"),
        viewBox=f"0 0 {pw} {ph}",
    )

    # layers as groups
    g_cut = dwg.g(id="cut", stroke="black", stroke_width="0.3", fill="none")
    g_score = dwg.g(id="score", stroke="#666", stroke_width="0.2", fill="none")
    g_tabs = dwg.g(id="tabs", stroke="#999", stroke_width="0.2", fill="#eee")
    g_text = dwg.g(id="text", fill="black", font_size="2.5", font_family="Helvetica")

    margin = page_settings.margin_mm
    placements = [p for p in layout.placements if p.page_index == page_index]

    for pl in placements:
        pid = pl.part_id
        if pid >= len(parts):
            continue
        part = parts[pid]
        # offset is already in paper mm (packer applied scale)
        ox, oy = float(pl.offset[0] + margin), float(pl.offset[1] + margin)

        # cut lines — only boundary/cut edges (not interior fold edges)
        cut_set = set(tuple(sorted(e)) for e in part.cut_edges)
        for e in cut_set:
            x0 = ox + float(part.vertices_2d[e[0], 0]) * scale
            y0 = oy + float(part.vertices_2d[e[0], 1]) * scale
            x1 = ox + float(part.vertices_2d[e[1], 0]) * scale
            y1 = oy + float(part.vertices_2d[e[1], 1]) * scale
            g_cut.add(dwg.line(start=(x0, y0), end=(x1, y1)))

        # fold lines
        if markings and pid < len(markings):
            for fl in markings[pid].fold_lines:
                x0 = ox + float(fl.p0[0]) * scale
                y0 = oy + float(fl.p0[1]) * scale
                x1 = ox + float(fl.p1[0]) * scale
                y1 = oy + float(fl.p1[1]) * scale
                dash = "2,1" if fl.fold_type == FoldType.MOUNTAIN else "2,0.5,0.5,0.5"
                g_score.add(
                    dwg.line(start=(x0, y0), end=(x1, y1), stroke_dasharray=dash)
                )

        # tabs
        if tabs and pid < len(tabs):
            for tab in tabs[pid]:
                pts = [(ox + float(p[0]) * scale, oy + float(p[1]) * scale) for p in tab.polygon]
                g_tabs.add(dwg.polygon(pts))

        # label
        cx = ox + float(part.vertices_2d[:, 0].mean()) * scale
        cy = oy + float(part.vertices_2d[:, 1].mean()) * scale
        g_text.add(dwg.text(f"P{pid + 1}", insert=(cx, cy), text_anchor="middle"))

    dwg.add(g_cut)
    dwg.add(g_score)
    dwg.add(g_tabs)
    dwg.add(g_text)
    dwg.save()


def export_all_svg(
    directory: str | Path,
    parts: list[UnfoldedPart],
    layout: LayoutResult,
    page_settings: PageSettings,
    tabs: list[list[Tab]] | None = None,
    markings: list[PartMarkings] | None = None,
    scale: float = 1.0,
) -> list[Path]:
    """Export all pages as separate SVG files into *directory*."""
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for page in range(layout.pages):
        p = out_dir / f"page_{page + 1:03d}.svg"
        export_svg(p, parts, layout, page_settings, tabs, markings, scale, page_index=page)
        paths.append(p)
    return paths
