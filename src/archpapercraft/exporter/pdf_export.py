"""PDF export using reportlab.

Produces one PDF page per layout page with:
- cut lines (solid black)
- fold lines (mountain = dashed, valley = dash-dot)
- tabs (light grey fill + cut outline)
- part IDs and edge-match numbers
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from reportlab.lib.pagesizes import A4, A3, letter
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from archpapercraft.layout_packer.packer import (
    LayoutResult,
    PageSettings,
    PaperSize,
    Orientation,
    PAPER_DIMS,
)
from archpapercraft.tabs_generator.markings import FoldLine, FoldType, PartMarkings
from archpapercraft.tabs_generator.tabs import Tab
from archpapercraft.unfolder.exact_unfold import UnfoldedPart


_RL_SIZES = {
    PaperSize.A4: A4,
    PaperSize.A3: A3,
    PaperSize.LETTER: letter,
}


def export_pdf(
    path: str | Path,
    parts: list[UnfoldedPart],
    layout: LayoutResult,
    page_settings: PageSettings,
    tabs: list[list[Tab]] | None = None,
    markings: list[PartMarkings] | None = None,
    scale: float = 1.0,
    scale_label: str = "",
) -> None:
    """Write a multi-page PDF to *path*.

    Parameters
    ----------
    path
        Output PDF file path.
    parts
        Unfolded part data.
    layout
        Placement information (which page, offset).
    page_settings
        Paper/margin settings.
    tabs
        Per-part list of Tab objects.
    markings
        Per-part fold-line and numbering markings.
    scale
        mm-per-model-unit scale factor.
    scale_label
        Scale label (e.g. ``"1:100"``).  If set, a scale bar is drawn.
    """
    pagesize = _RL_SIZES.get(page_settings.paper, A4)
    if page_settings.orientation == Orientation.LANDSCAPE:
        pagesize = (pagesize[1], pagesize[0])

    c = Canvas(str(path), pagesize=pagesize)
    margin = page_settings.margin_mm * mm

    for page_idx in range(layout.pages):
        if page_idx > 0:
            c.showPage()

        c.setFont("Helvetica", 6)

        # gather placements on this page
        placements = [p for p in layout.placements if p.page_index == page_idx]

        for pl in placements:
            pid = pl.part_id
            if pid >= len(parts):
                continue
            part = parts[pid]
            # offset is already in paper mm (packer applied scale)
            ox, oy = float(pl.offset[0]) * mm, float(pl.offset[1]) * mm

            # ── cut lines (edges of triangles on the boundary) ─────────
            c.setStrokeColorRGB(0, 0, 0)
            c.setLineWidth(0.5)
            _draw_triangles(c, part, margin + ox, margin + oy, scale)

            # ── fold lines ─────────────────────────────────────────────
            if markings and pid < len(markings):
                _draw_fold_lines(c, markings[pid], margin + ox, margin + oy, scale)

            # ── tabs ───────────────────────────────────────────────────
            if tabs and pid < len(tabs):
                _draw_tabs(c, tabs[pid], margin + ox, margin + oy, scale)

            # ── part label ─────────────────────────────────────────────
            cx = margin + ox + float(part.vertices_2d[:, 0].mean()) * mm * scale
            cy = margin + oy + float(part.vertices_2d[:, 1].mean()) * mm * scale
            c.setFillColorRGB(0, 0, 0)
            c.drawCentredString(cx, cy, f"P{pid + 1}")

        # ── scale bar (měřítkové pravítko) ─────────────────────────
        if scale_label:
            _draw_scale_bar(c, pagesize, margin, scale_label)

    c.save()


def _draw_triangles(
    c: Canvas,
    part: UnfoldedPart,
    ox: float,
    oy: float,
    scale: float,
) -> None:
    """Draw triangle edges as solid cut lines."""
    drawn: set[tuple[int, int]] = set()
    for face in part.faces:
        for j in range(3):
            e = tuple(sorted((int(face[j]), int(face[(j + 1) % 3]))))
            if e in drawn:
                continue
            drawn.add(e)
            x0 = ox + float(part.vertices_2d[e[0], 0]) * mm * scale
            y0 = oy + float(part.vertices_2d[e[0], 1]) * mm * scale
            x1 = ox + float(part.vertices_2d[e[1], 0]) * mm * scale
            y1 = oy + float(part.vertices_2d[e[1], 1]) * mm * scale
            c.line(x0, y0, x1, y1)


def _draw_fold_lines(
    c: Canvas,
    mark: PartMarkings,
    ox: float,
    oy: float,
    scale: float,
) -> None:
    for fl in mark.fold_lines:
        x0 = ox + float(fl.p0[0]) * mm * scale
        y0 = oy + float(fl.p0[1]) * mm * scale
        x1 = ox + float(fl.p1[0]) * mm * scale
        y1 = oy + float(fl.p1[1]) * mm * scale

        c.setStrokeColorRGB(0.4, 0.4, 0.4)
        c.setLineWidth(0.3)

        if fl.fold_type == FoldType.MOUNTAIN:
            c.setDash(3, 2)
        else:
            c.setDash([3, 1, 1, 1], 0)

        c.line(x0, y0, x1, y1)
        c.setDash([])


def _draw_tabs(
    c: Canvas,
    tab_list: list[Tab],
    ox: float,
    oy: float,
    scale: float,
) -> None:
    for tab in tab_list:
        path = c.beginPath()
        pts = tab.polygon
        path.moveTo(ox + float(pts[0, 0]) * mm * scale, oy + float(pts[0, 1]) * mm * scale)
        for pt in pts[1:]:
            path.lineTo(ox + float(pt[0]) * mm * scale, oy + float(pt[1]) * mm * scale)
        path.close()
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setLineWidth(0.3)
        c.drawPath(path, fill=1)

        # match ID label
        if tab.match_id:
            mx = ox + float(pts[:, 0].mean()) * mm * scale
            my = oy + float(pts[:, 1].mean()) * mm * scale
            c.setFillColorRGB(0.3, 0.3, 0.3)
            c.setFont("Helvetica", 4)
            c.drawCentredString(mx, my, str(tab.match_id))


def _draw_scale_bar(
    c: Canvas,
    pagesize: tuple[float, float],
    margin: float,
    scale_label: str,
) -> None:
    """Nakreslí měřítkové pravítko v pravém dolním rohu stránky.

    Pravítko má vždy délku 50 mm na papíře.
    """
    bar_length_paper = 50 * mm  # 50 mm na papíře
    bar_height = 3 * mm
    x_right = pagesize[0] - margin
    y_bottom = margin

    x_start = x_right - bar_length_paper
    y_bar = y_bottom

    # Alternující černobílé segmenty (5 segmentů po 10 mm)
    seg_count = 5
    seg_width = bar_length_paper / seg_count

    c.setLineWidth(0.3)
    for i in range(seg_count):
        sx = x_start + i * seg_width
        if i % 2 == 0:
            c.setFillColorRGB(0, 0, 0)
        else:
            c.setFillColorRGB(1, 1, 1)
        c.rect(sx, y_bar, seg_width, bar_height, fill=1, stroke=1)

    # Rámeček kolem celého pravítka
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.rect(x_start, y_bar, bar_length_paper, bar_height, fill=0, stroke=1)

    # Popisek měřítka
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 6)
    c.drawCentredString(
        x_start + bar_length_paper / 2,
        y_bar + bar_height + 1.5 * mm,
        f"Měřítko {scale_label}  |  50 mm na papíře",
    )
