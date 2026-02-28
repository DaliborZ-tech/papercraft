# ArchPapercraft Studio

**Architecture-first 3D modeler with papercraft / paper model export.**

Create architectural models (walls, roofs, gothic windows, onion domes) and export
print-ready cutting templates (PDF / SVG / DXF) with tabs, fold lines, and assembly
numbering — all in one offline desktop application.

---

## Features (MVP)

| Module | Capability |
|---|---|
| **Modeler** | Primitives (box, cylinder, cone), extrude, revolve, booleans |
| **Arch presets** | Wall, Opening, Gabled roof, Gothic window, Onion dome |
| **Paper analyzer** | Flat / developable / non-developable surface classification |
| **Seam editor** | Auto seams (sharp edges + A4 limit) + manual seam painting |
| **Unfolder** | Exact unfold (planes, cylinders) + approx strategies (gores, rings, facets) |
| **Tabs & markings** | Auto tabs, mountain/valley fold lines, part & edge numbering |
| **Layout** | Auto-packing onto A4/A3/Letter pages |
| **Export** | PDF (print), SVG (Inkscape), DXF (plotter/laser — cut/score layers) |

## Quick start

```bash
# 1. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux

# 2. Install in development mode
pip install -e ".[dev]"

# 3. (Optional) Install OpenCascade back-end
#    Requires conda – see docs/install_occ.md
pip install pythonocc-core

# 4. Run
archpapercraft
# — or —
python -m archpapercraft
```

## Project structure

```
src/archpapercraft/
├── core_geometry/    # OpenCascade wrapper, solids, booleans, triangulation
├── scene_graph/      # Object tree, transforms, parameters
├── arch_presets/     # Parametric architectural objects
├── paper_analyzer/   # Surface classification
├── seam_editor/      # Auto + manual seams
├── unfolder/         # Exact & approximate unfolding
├── tabs_generator/   # Tabs, fold lines, numbering
├── layout_packer/    # Page layout / bin-packing
├── exporter/         # PDF / SVG / DXF export
├── project_io/       # Project save / load / autosave
└── ui/               # PySide6 GUI (viewport, panels, wizard)
```

## Tech stack

* **GUI** — PySide6 (Qt 6)
* **CAD kernel** — OpenCascade (via pythonocc-core) for B-Rep solids, booleans, revolve
* **Triangulation** — OpenCascade mesh + numpy fallback
* **Export** — reportlab (PDF), svgwrite (SVG), ezdxf (DXF)

## License

MIT
