"""Papercraft panel — workflow steps: Analyze → Seams → Unfold → Layout → Export."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.project_io.project import Project

_log = logging.getLogger(__name__)


class PapercraftPanel(QWidget):
    """Right-side panel guiding the user through the papercraft workflow."""

    def __init__(self, project: Project | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project or Project()

        layout = QVBoxLayout(self)

        # ── 1. Analyze ─────────────────────────────────────────────────
        grp_analyze = QGroupBox("1. Analyze surfaces")
        al = QVBoxLayout()
        self._btn_analyze = QPushButton("Analyze")
        self._btn_analyze.clicked.connect(self._on_analyze)
        self._lbl_analyze = QLabel("Click Analyze to classify surfaces.")
        al.addWidget(self._btn_analyze)
        al.addWidget(self._lbl_analyze)
        grp_analyze.setLayout(al)
        layout.addWidget(grp_analyze)

        # ── 2. Seams ──────────────────────────────────────────────────
        grp_seams = QGroupBox("2. Seams")
        sl = QVBoxLayout()
        self._btn_auto_seams = QPushButton("Auto Seams")
        self._btn_auto_seams.clicked.connect(self._on_auto_seams)
        self._lbl_seams = QLabel("Generate automatic seam placement.")
        sl.addWidget(self._btn_auto_seams)
        sl.addWidget(self._lbl_seams)
        grp_seams.setLayout(sl)
        layout.addWidget(grp_seams)

        # ── 3. Unfold ─────────────────────────────────────────────────
        grp_unfold = QGroupBox("3. Unfold")
        ul = QVBoxLayout()
        uh = QHBoxLayout()
        uh.addWidget(QLabel("Strategy:"))
        self._combo_strategy = QComboBox()
        self._combo_strategy.addItems(["Exact", "Gores", "Rings", "Facets"])
        uh.addWidget(self._combo_strategy)
        uh.addWidget(QLabel("Segments:"))
        self._spin_segments = QSpinBox()
        self._spin_segments.setRange(4, 64)
        self._spin_segments.setValue(16)
        uh.addWidget(self._spin_segments)
        ul.addLayout(uh)
        self._btn_unfold = QPushButton("Unfold")
        self._btn_unfold.clicked.connect(self._on_unfold)
        ul.addWidget(self._btn_unfold)
        self._lbl_unfold = QLabel("")
        ul.addWidget(self._lbl_unfold)
        grp_unfold.setLayout(ul)
        layout.addWidget(grp_unfold)

        # ── 4. Export ──────────────────────────────────────────────────
        grp_export = QGroupBox("4. Layout & Export")
        el = QVBoxLayout()
        eh = QHBoxLayout()
        self._btn_pdf = QPushButton("Export PDF")
        self._btn_pdf.clicked.connect(lambda: self._on_export("pdf"))
        self._btn_svg = QPushButton("Export SVG")
        self._btn_svg.clicked.connect(lambda: self._on_export("svg"))
        self._btn_dxf = QPushButton("Export DXF")
        self._btn_dxf.clicked.connect(lambda: self._on_export("dxf"))
        eh.addWidget(self._btn_pdf)
        eh.addWidget(self._btn_svg)
        eh.addWidget(self._btn_dxf)
        el.addLayout(eh)
        grp_export.setLayout(el)
        layout.addWidget(grp_export)

        layout.addStretch()

        # internal state
        self._analysis = None
        self._seam_graph = None
        self._unfolded_parts = None

    def set_project(self, project: Project) -> None:
        self._project = project
        self._analysis = None
        self._seam_graph = None
        self._unfolded_parts = None
        self._lbl_analyze.setText("Click Analyze to classify surfaces.")
        self._lbl_seams.setText("Generate automatic seam placement.")
        self._lbl_unfold.setText("")

    # ── helpers ─────────────────────────────────────────────────────────

    def _get_combined_mesh(self):
        """Rebuild scene meshes and return a single merged mesh (all visible objects)."""
        from archpapercraft.core_geometry.operations import merge_meshes

        self._project.scene.rebuild_meshes()
        meshes = self._project.scene.collect_visible_meshes()
        if not meshes:
            return None
        return merge_meshes(meshes)

    def _check_csg_requirements(self) -> None:
        """Warn if scene contains OPENING nodes but OCC is unavailable."""
        from archpapercraft.core_geometry.backend import get_backend
        from archpapercraft.scene_graph.node import NodeType

        be = get_backend()
        if be.supports_csg:
            return

        has_openings = any(
            n.node_type == NodeType.OPENING
            for n in self._project.scene.root.all_nodes()
        )
        if has_openings:
            QMessageBox.warning(
                self,
                "CSG not available",
                "The scene contains Opening nodes, but pythonocc-core "
                "is not installed.\n\n"
                "Boolean operations (subtracting openings from walls) "
                "will NOT work correctly.\n\n"
                "Install:  pip install pythonocc-core",
            )

    def _build_page_settings(self):
        """Create :class:`PageSettings` from the current :class:`ProjectSettings`."""
        from archpapercraft.layout_packer.packer import (
            PageSettings,
            PaperSize,
            Orientation,
        )

        _PAPER_MAP = {
            "A4": PaperSize.A4,
            "A3": PaperSize.A3,
            "Letter": PaperSize.LETTER,
            "A2": PaperSize.A2,
            "A1": PaperSize.A1,
        }

        settings = self._project.settings
        paper = _PAPER_MAP.get(settings.paper, PaperSize.A4)

        # Prefer saved layout preferences if available
        layout_prefs = self._project.load_layout_settings()
        if layout_prefs:
            orientation_str = layout_prefs.get("orientation", "portrait")
            margin = layout_prefs.get("margin_mm", settings.paper_margin_mm)
        else:
            orientation_str = "portrait"
            margin = settings.paper_margin_mm

        orientation = (
            Orientation.LANDSCAPE
            if orientation_str == "landscape"
            else Orientation.PORTRAIT
        )

        return PageSettings(
            paper=paper,
            orientation=orientation,
            margin_mm=margin,
            bleed_mm=settings.paper_bleed_mm,
        )

    # ── workflow slots ─────────────────────────────────────────────────

    def _on_analyze(self) -> None:
        from archpapercraft.paper_analyzer.classifier import classify_surfaces

        self._check_csg_requirements()

        mesh = self._get_combined_mesh()
        if mesh is None:
            self._lbl_analyze.setText("No meshes in scene.")
            return

        self._analysis = classify_surfaces(mesh)
        n_flat = len(self._analysis.flat_patches)
        n_dev = len(self._analysis.developable_patches)
        n_nd = len(self._analysis.non_developable_patches)
        self._lbl_analyze.setText(
            f"Patches: {n_flat} flat, {n_dev} developable, {n_nd} non-developable"
        )

    def _on_auto_seams(self) -> None:
        from archpapercraft.seam_editor.auto_seams import auto_seams

        mesh = self._get_combined_mesh()
        if mesh is None:
            self._lbl_seams.setText("No meshes.")
            return

        scale_factor = self._project.settings.scale_factor
        self._seam_graph = auto_seams(mesh, scale=scale_factor)
        parts = self._seam_graph.compute_parts()
        self._lbl_seams.setText(
            f"Seams: {len(self._seam_graph.seam_edges)} edges → {len(parts)} parts"
        )

    def _on_unfold(self) -> None:
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy

        if self._seam_graph is None:
            QMessageBox.warning(self, "Unfold", "Run Auto Seams first.")
            return

        mesh = self._get_combined_mesh()
        if mesh is None:
            return

        strategy = self._combo_strategy.currentText()
        segments = self._spin_segments.value()

        self._unfolded_parts = unfold_with_strategy(
            mesh, self._seam_graph, strategy=strategy, segments=segments,
        )
        self._lbl_unfold.setText(
            f"Unfolded {len(self._unfolded_parts)} parts (strategy: {strategy})"
        )

    def _on_export(self, fmt: str) -> None:
        if self._unfolded_parts is None:
            QMessageBox.warning(self, "Export", "Run Unfold first.")
            return

        from archpapercraft.layout_packer.packer import pack_parts
        from archpapercraft.tabs_generator.markings import classify_folds
        from archpapercraft.tabs_generator.tabs import TabSettings, generate_tabs_for_part

        # ── PageSettings from project (not defaults) ──────────────
        ps = self._build_page_settings()
        scale = self._project.settings.scale_factor

        outlines = [p.vertices_2d for p in self._unfolded_parts]
        layout = pack_parts(outlines, ps, scale=scale)

        # generate tabs & markings
        tab_settings = TabSettings(grammage=self._project.settings.paper_grammage)
        tabs = []
        markings_list = []
        for part in self._unfolded_parts:
            edge_ids = self._seam_graph.compute_edge_match_ids() if self._seam_graph else {}
            t = generate_tabs_for_part(part.vertices_2d, part.cut_edges, edge_ids, tab_settings)
            tabs.append(t)
            m = classify_folds(part.vertices_2d, part.fold_edges, part.part_id)
            markings_list.append(m)

        filters = {
            "pdf": "PDF (*.pdf)",
            "svg": "SVG (*.svg)",
            "dxf": "DXF (*.dxf)",
        }
        path, _ = QFileDialog.getSaveFileName(self, f"Export {fmt.upper()}", "", filters[fmt])
        if not path:
            return

        scale_label = self._project.settings.scale

        try:
            if fmt == "pdf":
                from archpapercraft.exporter.pdf_export import export_pdf
                export_pdf(
                    path, self._unfolded_parts, layout, ps,
                    tabs, markings_list, scale, scale_label=scale_label,
                )
            elif fmt == "svg":
                from archpapercraft.exporter.svg_export import export_svg
                export_svg(path, self._unfolded_parts, layout, ps, tabs, markings_list, scale)
            elif fmt == "dxf":
                from archpapercraft.exporter.dxf_export import export_dxf
                export_dxf(path, self._unfolded_parts, layout, ps, tabs, markings_list, scale)
            QMessageBox.information(self, "Export", f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))
