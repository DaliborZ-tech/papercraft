"""DXF export using ezdxf.

Generates a DXF file with dedicated layers:
- ``CUT``   — cut lines (continuous)
- ``SCORE`` — fold / score lines (dashed)
- ``TABS``  — tab outlines
- ``TEXT``  — labels & numbering

This is suited for plotter / laser-cutter workflows.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import ezdxf
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

from archpapercraft.layout_packer.packer import LayoutResult, PageSettings
from archpapercraft.tabs_generator.markings import FoldType, PartMarkings
from archpapercraft.tabs_generator.tabs import Tab
from archpapercraft.unfolder.exact_unfold import UnfoldedPart


def export_dxf(
    path: str | Path,
    parts: list[UnfoldedPart],
    layout: LayoutResult,
    page_settings: PageSettings,
    tabs: list[list[Tab]] | None = None,
    markings: list[PartMarkings] | None = None,
    scale: float = 1.0,
) -> None:
    """Zapíše všechny stránky do jednoho DXF souboru (jeden blok na stránku).

    Vyhodí ``RuntimeError`` pokud *ezdxf* není nainstalován.
    """
    if not EZDXF_AVAILABLE:
        raise RuntimeError(
            "DXF export vyžaduje knihovnu ezdxf.  Nainstalujte ji: "
            "pip install archpapercraft-studio[dxf]"
        )
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # Layers
    doc.layers.add("CUT", color=7)  # white/black depending on background
    doc.layers.add("SCORE", color=1)  # red
    doc.layers.add("TABS", color=3)  # green
    doc.layers.add("TEXT", color=5)  # blue

    margin = page_settings.margin_mm

    for pl in layout.placements:
        pid = pl.part_id
        if pid >= len(parts):
            continue
        part = parts[pid]
        # page offset (stack pages horizontally)
        page_off_x = pl.page_index * 400.0  # 400 mm between pages
        # offset je z packeru již v paper mm → nepřenásobovat scale
        ox = page_off_x + float(pl.offset[0]) + margin
        oy = float(pl.offset[1]) + margin

        # ── cut lines ─────────────────────────────────────────────────
        drawn: set[tuple[int, int]] = set()
        for face in part.faces:
            for j in range(3):
                e = tuple(sorted((int(face[j]), int(face[(j + 1) % 3]))))
                if e in drawn:
                    continue
                drawn.add(e)
                x0 = ox + float(part.vertices_2d[e[0], 0]) * scale
                y0 = oy + float(part.vertices_2d[e[0], 1]) * scale
                x1 = ox + float(part.vertices_2d[e[1], 0]) * scale
                y1 = oy + float(part.vertices_2d[e[1], 1]) * scale
                msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "CUT"})

        # ── fold lines ────────────────────────────────────────────────
        if markings and pid < len(markings):
            for fl in markings[pid].fold_lines:
                x0 = ox + float(fl.p0[0]) * scale
                y0 = oy + float(fl.p0[1]) * scale
                x1 = ox + float(fl.p1[0]) * scale
                y1 = oy + float(fl.p1[1]) * scale
                msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "SCORE"})

        # ── tabs ──────────────────────────────────────────────────────
        if tabs and pid < len(tabs):
            for tab in tabs[pid]:
                pts = [
                    (ox + float(p[0]) * scale, oy + float(p[1]) * scale)
                    for p in tab.polygon
                ]
                pts.append(pts[0])  # close
                msp.add_lwpolyline(pts, dxfattribs={"layer": "TABS"})

        # ── label ─────────────────────────────────────────────────────
        cx = ox + float(part.vertices_2d[:, 0].mean()) * scale
        cy = oy + float(part.vertices_2d[:, 1].mean()) * scale
        msp.add_text(
            f"P{pid + 1}",
            dxfattribs={"layer": "TEXT", "height": 3.0},
        ).set_placement((cx, cy))

    doc.saveas(str(path))
