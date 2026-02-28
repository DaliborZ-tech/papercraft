"""PNG export — rastrový náhled rozložených dílů.

Generuje PNG obrázky z SVG exportu pomocí interního rendereru
(reportlab + io), nebo přímé kreslení přes numpy/pillow.

Funkce:
- Nastavitelné DPI (výchozí 150 pro náhled, 300 pro tisk)
- Rotace (0°/90°/180°/270°)
- Průhledné pozadí (volitelně)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from archpapercraft.layout_packer.packer import (
    LayoutResult,
    PageSettings,
    PAPER_DIMS,
)
from archpapercraft.unfolder.exact_unfold import UnfoldedPart
from archpapercraft.tabs_generator.tabs import Tab
from archpapercraft.tabs_generator.markings import FoldType, PartMarkings


@dataclass
class PngSettings:
    """Nastavení PNG exportu."""
    dpi: int = 150
    background_color: tuple[int, int, int, int] = (255, 255, 255, 255)
    cut_color: tuple[int, int, int] = (0, 0, 0)
    mountain_color: tuple[int, int, int] = (100, 100, 100)
    valley_color: tuple[int, int, int] = (150, 150, 255)
    tab_color: tuple[int, int, int, int] = (230, 230, 230, 180)
    line_width_px: int = 2
    rotation_deg: int = 0  # 0, 90, 180, 270


def _mm_to_px(mm: float, dpi: int) -> int:
    """Převede milimetry na pixely."""
    return int(mm * dpi / 25.4)


def _point_to_px(
    x_mm: float, y_mm: float, dpi: int, page_h_mm: float,
) -> tuple[int, int]:
    """Převede mm souřadnice na pixel souřadnice (Y osa obráceně)."""
    px = _mm_to_px(x_mm, dpi)
    py = _mm_to_px(page_h_mm - y_mm, dpi)
    return px, py


def _draw_line(
    pixels: NDArray[np.uint8],
    x0: int, y0: int, x1: int, y1: int,
    color: tuple[int, ...],
    width: int = 1,
) -> None:
    """Bresenhamův algoritmus pro kreslení čáry do numpy pole."""
    h, w_img = pixels.shape[:2]
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    half_w = max(0, width // 2)
    nc = len(color)

    while True:
        # Kresli s danou šířkou
        for wy in range(-half_w, half_w + 1):
            for wx in range(-half_w, half_w + 1):
                py, px = y0 + wy, x0 + wx
                if 0 <= py < h and 0 <= px < w_img:
                    pixels[py, px, :nc] = color[:nc]

        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def export_png(
    path: str | Path,
    parts: list[UnfoldedPart],
    layout: LayoutResult,
    page_settings: PageSettings,
    tabs: list[list[Tab]] | None = None,
    markings: list[PartMarkings] | None = None,
    scale: float = 1.0,
    page_index: int = 0,
    png_settings: PngSettings | None = None,
) -> None:
    """Exportuje jednu stránku do PNG souboru.

    Parameters
    ----------
    path : str | Path
        Cesta k výstupnímu PNG souboru.
    parts : list[UnfoldedPart]
        Rozložené díly.
    layout : LayoutResult
        Informace o rozmístění (stránka, offset).
    page_settings : PageSettings
        Nastavení papíru/okrajů.
    tabs : list[list[Tab]] | None
        Chlopně pro každý díl.
    markings : list[PartMarkings] | None
        Značení pro každý díl.
    scale : float
        Měřítkový faktor.
    page_index : int
        Index stránky k exportu.
    png_settings : PngSettings | None
        Nastavení PNG výstupu.
    """
    if png_settings is None:
        png_settings = PngSettings()

    pw, ph = PAPER_DIMS[page_settings.paper]
    dpi = png_settings.dpi

    img_w = _mm_to_px(pw, dpi)
    img_h = _mm_to_px(ph, dpi)

    # Vytvoř pixel pole
    pixels = np.full((img_h, img_w, 4), png_settings.background_color, dtype=np.uint8)

    margin = page_settings.margin_mm
    placements = [p for p in layout.placements if p.page_index == page_index]

    for pl in placements:
        pid = pl.part_id
        if pid >= len(parts):
            continue
        part = parts[pid]
        ox = float(pl.offset[0]) * scale + margin
        oy = float(pl.offset[1]) * scale + margin

        # Kresli řezné čáry (obrysy)
        verts = part.vertices_2d * scale
        for fi in range(len(part.faces_2d)):
            tri = part.faces_2d[fi]
            for j in range(3):
                v0 = verts[tri[j]]
                v1 = verts[tri[(j + 1) % 3]]
                px0, py0 = _point_to_px(v0[0] + ox, v0[1] + oy, dpi, ph)
                px1, py1 = _point_to_px(v1[0] + ox, v1[1] + oy, dpi, ph)
                _draw_line(pixels, px0, py0, px1, py1,
                           png_settings.cut_color, png_settings.line_width_px)

        # Kresli přehybové čáry
        if markings and pid < len(markings):
            for fl in markings[pid].fold_lines:
                p0 = fl.p0 * scale
                p1 = fl.p1 * scale
                color = (png_settings.mountain_color
                         if fl.fold_type == FoldType.MOUNTAIN
                         else png_settings.valley_color)
                px0, py0 = _point_to_px(p0[0] + ox, p0[1] + oy, dpi, ph)
                px1, py1 = _point_to_px(p1[0] + ox, p1[1] + oy, dpi, ph)
                _draw_line(pixels, px0, py0, px1, py1, color, 1)

    # Rotace
    if png_settings.rotation_deg == 90:
        pixels = np.rot90(pixels, k=1)
    elif png_settings.rotation_deg == 180:
        pixels = np.rot90(pixels, k=2)
    elif png_settings.rotation_deg == 270:
        pixels = np.rot90(pixels, k=3)

    # Uložení — použij buď Pillow pokud dostupné, nebo raw PNM fallback
    _save_png(Path(path), pixels)


def _save_png(path: Path, pixels: NDArray[np.uint8]) -> None:
    """Uloží pixel pole jako PNG.

    Pokusí se použít Pillow; pokud není dostupné, uloží jako PPM.
    """
    try:
        from PIL import Image  # type: ignore[import-untyped]
        img = Image.fromarray(pixels, "RGBA")
        img.save(str(path))
    except ImportError:
        # Fallback: uložit jako PPM (bez alfa)
        ppm_path = path.with_suffix(".ppm")
        h, w = pixels.shape[:2]
        with open(ppm_path, "wb") as f:
            f.write(f"P6\n{w} {h}\n255\n".encode())
            f.write(pixels[:, :, :3].tobytes())


def export_all_png(
    path_template: str,
    parts: list[UnfoldedPart],
    layout: LayoutResult,
    page_settings: PageSettings,
    tabs: list[list[Tab]] | None = None,
    markings: list[PartMarkings] | None = None,
    scale: float = 1.0,
    png_settings: PngSettings | None = None,
) -> list[Path]:
    """Exportuje všechny stránky do PNG souborů.

    Parameters
    ----------
    path_template : str
        Šablona cesty, např. "output/page_{}.png" — {} se nahradí číslem stránky.

    Returns
    -------
    list[Path] — cesty k vytvořeným souborům.
    """
    paths: list[Path] = []
    for page_idx in range(layout.pages):
        p = Path(path_template.format(page_idx + 1))
        export_png(p, parts, layout, page_settings, tabs, markings,
                   scale, page_idx, png_settings)
        paths.append(p)
    return paths
