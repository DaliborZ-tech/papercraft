"""Papercraft panel — workflow steps: Analyze → Seams → Unfold → Layout → Export."""

from __future__ import annotations

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

    # ── workflow slots ─────────────────────────────────────────────────

    def _on_analyze(self) -> None:
        from archpapercraft.core_geometry.primitives import MeshData
        from archpapercraft.paper_analyzer.classifier import classify_surfaces

        self._project.scene.rebuild_meshes()
        meshes = self._project.scene.collect_meshes()
        if not meshes:
            self._lbl_analyze.setText("No meshes in scene.")
            return

        # analyze the first mesh (simple MVP — later merge)
        mesh = meshes[0]
        self._analysis = classify_surfaces(mesh)
        n_flat = len(self._analysis.flat_patches)
        n_dev = len(self._analysis.developable_patches)
        n_nd = len(self._analysis.non_developable_patches)
        self._lbl_analyze.setText(
            f"Patches: {n_flat} flat, {n_dev} developable, {n_nd} non-developable"
        )

    def _on_auto_seams(self) -> None:
        from archpapercraft.seam_editor.auto_seams import auto_seams

        self._project.scene.rebuild_meshes()
        meshes = self._project.scene.collect_meshes()
        if not meshes:
            self._lbl_seams.setText("No meshes.")
            return
        mesh = meshes[0]
        scale_factor = self._project.settings.scale_factor
        self._seam_graph = auto_seams(mesh, scale=scale_factor)
        parts = self._seam_graph.compute_parts()
        self._lbl_seams.setText(
            f"Seams: {len(self._seam_graph.seam_edges)} edges → {len(parts)} parts"
        )

    def _on_unfold(self) -> None:
        from archpapercraft.unfolder.approx_unfold import unfold_all_parts

        if self._seam_graph is None:
            QMessageBox.warning(self, "Unfold", "Run Auto Seams first.")
            return

        meshes = self._project.scene.collect_meshes()
        if not meshes:
            return
        mesh = meshes[0]
        self._unfolded_parts = unfold_all_parts(mesh, self._seam_graph)
        self._lbl_unfold.setText(f"Unfolded {len(self._unfolded_parts)} parts")

    def _on_export(self, fmt: str) -> None:
        if self._unfolded_parts is None:
            QMessageBox.warning(self, "Export", "Run Unfold first.")
            return

        from archpapercraft.layout_packer.packer import PageSettings, pack_parts
        from archpapercraft.tabs_generator.markings import classify_folds
        from archpapercraft.tabs_generator.tabs import TabSettings, generate_tabs_for_part

        ps = PageSettings()
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

        try:
            if fmt == "pdf":
                from archpapercraft.exporter.pdf_export import export_pdf
                export_pdf(path, self._unfolded_parts, layout, ps, tabs, markings_list, scale)
            elif fmt == "svg":
                from archpapercraft.exporter.svg_export import export_svg
                export_svg(path, self._unfolded_parts, layout, ps, tabs, markings_list, scale)
            elif fmt == "dxf":
                from archpapercraft.exporter.dxf_export import export_dxf
                export_dxf(path, self._unfolded_parts, layout, ps, tabs, markings_list, scale)
            QMessageBox.information(self, "Export", f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))
