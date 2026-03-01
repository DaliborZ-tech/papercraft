"""Panel papercraftu — kroky workflow: Analýza → Švy → Rozložení → Uspořádání → Export."""

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
    """Pravý panel provádějící uživatele workflow papercraftu."""

    def __init__(self, project: Project | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project or Project()

        layout = QVBoxLayout(self)

        # ── 1. Analýza ─────────────────────────────────────────────────
        grp_analyze = QGroupBox("1. Analýza ploch")
        al = QVBoxLayout()
        self._btn_analyze = QPushButton("Analyzovat")
        self._btn_analyze.clicked.connect(self._on_analyze)
        self._lbl_analyze = QLabel("Klikněte na Analyzovat pro klasifikaci ploch.")
        al.addWidget(self._btn_analyze)
        al.addWidget(self._lbl_analyze)
        grp_analyze.setLayout(al)
        layout.addWidget(grp_analyze)

        # ── 2. Švy ────────────────────────────────────────────────────
        grp_seams = QGroupBox("2. Švy")
        sl = QVBoxLayout()
        self._btn_auto_seams = QPushButton("Automatické švy")
        self._btn_auto_seams.clicked.connect(self._on_auto_seams)
        self._lbl_seams = QLabel("Nastavit automatické umístění švů.")
        sl.addWidget(self._btn_auto_seams)
        sl.addWidget(self._lbl_seams)
        grp_seams.setLayout(sl)
        layout.addWidget(grp_seams)

        # ── 3. Rozložení ──────────────────────────────────────────────
        grp_unfold = QGroupBox("3. Rozložení")
        ul = QVBoxLayout()
        uh = QHBoxLayout()
        uh.addWidget(QLabel("Strategie:"))
        self._combo_strategy = QComboBox()
        self._combo_strategy.addItems(["Exact", "Gores", "Rings", "Facets"])
        uh.addWidget(self._combo_strategy)
        uh.addWidget(QLabel("Segmenty:"))
        self._spin_segments = QSpinBox()
        self._spin_segments.setRange(4, 64)
        self._spin_segments.setValue(16)
        uh.addWidget(self._spin_segments)
        ul.addLayout(uh)
        self._btn_unfold = QPushButton("Rozložit")
        self._btn_unfold.clicked.connect(self._on_unfold)
        ul.addWidget(self._btn_unfold)
        self._lbl_unfold = QLabel("")
        ul.addWidget(self._lbl_unfold)
        grp_unfold.setLayout(ul)
        layout.addWidget(grp_unfold)

        # ── 4. Export ──────────────────────────────────────────────────
        grp_export = QGroupBox("4. Rozvržení a export")
        el = QVBoxLayout()
        eh = QHBoxLayout()
        self._btn_pdf = QPushButton("Exportovat PDF")
        self._btn_pdf.clicked.connect(lambda: self._on_export("pdf"))
        self._btn_svg = QPushButton("Exportovat SVG")
        self._btn_svg.clicked.connect(lambda: self._on_export("svg"))
        self._btn_dxf = QPushButton("Exportovat DXF")
        self._btn_dxf.clicked.connect(lambda: self._on_export("dxf"))
        eh.addWidget(self._btn_pdf)
        eh.addWidget(self._btn_svg)
        eh.addWidget(self._btn_dxf)
        el.addLayout(eh)

        eh2 = QHBoxLayout()
        self._btn_png = QPushButton("Exportovat PNG")
        self._btn_png.clicked.connect(lambda: self._on_export("png"))
        self._btn_guide = QPushButton("Sestavovací návod")
        self._btn_guide.clicked.connect(self._on_build_guide)
        eh2.addWidget(self._btn_png)
        eh2.addWidget(self._btn_guide)
        el.addLayout(eh2)

        grp_export.setLayout(el)
        layout.addWidget(grp_export)

        layout.addStretch()

        # internal state
        self._analysis = None
        self._seam_graph = None
        self._unfolded_parts = None
        self._cached_mesh = None

    def set_project(self, project: Project) -> None:
        self._project = project
        self._analysis = None
        self._seam_graph = None
        self._unfolded_parts = None
        self._cached_mesh = None
        self._lbl_analyze.setText("Klikněte na Analyzovat pro klasifikaci ploch.")
        self._lbl_seams.setText("Nastavit automatické umístění švů.")
        self._lbl_unfold.setText("")

    # ── helpers ─────────────────────────────────────────────────────────

    def _get_combined_mesh(self):
        """Přestaví meshe scény a vrátí jeden sloučený mesh (všechny viditelné objekty).

        Transformace uzlů se aplikují, takže mesh je ve world-space.
        """
        from archpapercraft.core_geometry.operations import merge_meshes

        self._project.scene.rebuild_meshes()
        meshes = self._project.scene.collect_visible_meshes(world_space=True)
        if not meshes:
            return None
        return merge_meshes(meshes)

    def _check_csg_requirements(self) -> None:
        """Varuje pokud scéna obsahuje uzly OPENING ale OCC není dostupné."""
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
                "CSG není dostupné",
                "Scéna obsahuje uzly Otvor, ale pythonocc-core "
                "není nainstalován.\n\n"
                "Booleovské operace (odečítání otvorů ze zdí) "
                "nebudou fungovat správně.\n\n"
                "Instalace:  pip install pythonocc-core",
            )

    def _build_page_settings(self):
        """Vytvoří :class:`PageSettings` z aktuálních :class:`ProjectSettings`."""
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
            self._lbl_analyze.setText("Ve scéně nejsou žádné meshe.")
            return

        self._analysis = classify_surfaces(mesh)
        n_flat = len(self._analysis.flat_patches)
        n_dev = len(self._analysis.developable_patches)
        n_nd = len(self._analysis.non_developable_patches)
        self._lbl_analyze.setText(
            f"Díly: {n_flat} plochých, {n_dev} rozvinutelných, {n_nd} nerozvinutelných"
        )

    def _on_auto_seams(self) -> None:
        from archpapercraft.seam_editor.auto_seams import auto_seams
        from archpapercraft.core_geometry.units import to_mm

        mesh = self._get_combined_mesh()
        if mesh is None:
            self._lbl_seams.setText("Žádné meshe.")
            return

        self._cached_mesh = mesh  # uložit pro unfold krok

        # Convert model-unit coords to paper mm:  unit→mm × scale_factor
        unit_to_mm = to_mm(1.0, self._project.settings.units)
        paper_scale = unit_to_mm * self._project.settings.scale_factor
        self._seam_graph = auto_seams(mesh, scale=paper_scale)
        parts = self._seam_graph.compute_parts()
        self._lbl_seams.setText(
            f"Švy: {len(self._seam_graph.seam_edges)} hran → {len(parts)} dílů"
        )

    def _on_unfold(self) -> None:
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy

        if self._seam_graph is None:
            QMessageBox.warning(self, "Rozložení", "Nejprve spusťte Automatické švy.")
            return

        # Použit cached mesh ze seam kroku (garantuje konzistentní indexy)
        mesh = self._cached_mesh
        if mesh is None:
            mesh = self._get_combined_mesh()
        if mesh is None:
            return

        strategy = self._combo_strategy.currentText()
        segments = self._spin_segments.value()

        self._unfolded_parts = unfold_with_strategy(
            mesh, self._seam_graph, strategy=strategy, segments=segments,
        )
        self._lbl_unfold.setText(
            f"Rozloženo {len(self._unfolded_parts)} dílů (strategie: {strategy})"
        )

    def _on_export(self, fmt: str) -> None:
        if self._unfolded_parts is None:
            QMessageBox.warning(self, "Export", "Nejprve rozložte model.")
            return

        from archpapercraft.core_geometry.units import to_mm
        from archpapercraft.layout_packer.packer import pack_parts
        from archpapercraft.tabs_generator.markings import classify_folds
        from archpapercraft.tabs_generator.tabs import TabSettings, generate_tabs_for_part

        # ── PageSettings from project (not defaults) ──────────────
        ps = self._build_page_settings()

        # paper_scale = model-unit → mm on paper.
        # Example: units="m", scale="1:100" → 1000 × 0.01 = 10
        #   → 1.2 m window → 12 mm on paper.
        unit_to_mm = to_mm(1.0, self._project.settings.units)
        scale = unit_to_mm * self._project.settings.scale_factor

        outlines = [p.vertices_2d for p in self._unfolded_parts]
        layout = pack_parts(outlines, ps, scale=scale)

        # generate tabs & markings — tab width must be in model units
        tab_settings = TabSettings(grammage=self._project.settings.paper_grammage)
        if scale > 0:
            tab_settings.width_mm = tab_settings.width_mm / scale  # mm → model
        tabs = []
        markings_list = []
        edge_ids_3d = self._seam_graph.compute_edge_match_ids() if self._seam_graph else {}
        for part in self._unfolded_parts:
            # Převod edge_match_ids z 3D klíčů na 2D klíče přes cut_edge_3d_map
            edge_ids_2d: dict[tuple[int, int], int] = {}
            for ce_2d, ce_3d in part.cut_edge_3d_map.items():
                mid = edge_ids_3d.get(ce_3d, 0)
                if mid:
                    edge_ids_2d[tuple(sorted(ce_2d))] = mid
            t = generate_tabs_for_part(part.vertices_2d, part.cut_edges, edge_ids_2d, tab_settings)
            tabs.append(t)
            m = classify_folds(part.vertices_2d, part.fold_edges, part.part_id)
            markings_list.append(m)

        filters = {
            "pdf": "PDF (*.pdf)",
            "svg": "SVG (*.svg)",
            "dxf": "DXF (*.dxf)",
            "png": "PNG (*.png)",
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
            elif fmt == "png":
                from archpapercraft.exporter.png_export import export_png
                export_png(path, self._unfolded_parts, layout, ps, tabs, markings_list, scale)
            QMessageBox.information(self, "Export", f"Exportováno do {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Chyba exportu", str(exc))

    def _on_build_guide(self) -> None:
        """Generuj sestavovací návod jako textový soubor."""
        if self._unfolded_parts is None:
            QMessageBox.warning(self, "Návod", "Nejprve rozložte model.")
            return

        from archpapercraft.tabs_generator.build_guide import generate_build_guide
        from archpapercraft.tabs_generator.markings import classify_folds

        markings_list = []
        for part in self._unfolded_parts:
            m = classify_folds(part.vertices_2d, part.fold_edges, part.part_id)
            markings_list.append(m)

        guide = generate_build_guide(
            markings_list,
            project_name=self._project.settings.name,
            scale=self._project.settings.scale,
            paper_grammage=self._project.settings.paper_grammage,
        )

        path, _ = QFileDialog.getSaveFileName(
            self, "Uložit sestavovací návod", "", "Text (*.txt)",
        )
        if not path:
            return

        try:
            from pathlib import Path
            Path(path).write_text(guide.to_text(), encoding="utf-8")
            QMessageBox.information(self, "Návod", f"Návod uložen do {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Chyba", str(exc))
