"""Sketch-first authoring workspace linking source construction and paper parts."""
# ruff: noqa: N802 -- Qt closeEvent uses the framework's method name.

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.ui.author_attachment import AttachmentDialog, GlueRegionDialog
from archpapercraft.ui.author_connectors import ConnectorPanel
from archpapercraft.ui.author_curves import CurveEditorDialog, CurveSketch
from archpapercraft.ui.author_editing import DeletePartDialog, RenameDialog
from archpapercraft.ui.author_export_job import ExportProgressDialog
from archpapercraft.ui.author_loft import LoftProfilesDialog
from archpapercraft.ui.author_manual_layout import ManualGridDialog
from archpapercraft.ui.author_material import MaterialDialog
from archpapercraft.ui.author_paper import AuthorPaperView
from archpapercraft.ui.author_profile_placement import ProfilePlacementDialog
from archpapercraft.ui.author_segmentation import SegmentedVariantDialog
from archpapercraft.ui.author_subdivision import SubdivisionDialog
from archpapercraft.ui.author_viewport import AuthorViewport


class AuthorMainWindow(QMainWindow):
    def __init__(self, parent=None, *, settings=None):
        super().__init__(parent)
        self.resize(1660, 960)
        self.settings = settings or QSettings("ArchPapercraft", "Authoring")
        self.selected_surface = None
        self.selected_profile = None
        self.selected_generation = None
        self.selected_edge = None
        self.selected_vertex = None
        self.connect_source = None
        self.draft_surface = self.draft_plane = None
        self.current_joint = None
        self._updating = False
        self._shown = {}
        self._raw = {}
        self.sections = {}
        self._frame_next = True
        self._command_errors = 0
        self._committing_input = False
        self.controller = AuthorController(self.refresh)
        self.actions = {}
        self._build_workspace()
        self._build_actions()
        self._build_properties()
        self.controller.new()
        QTimer.singleShot(0, self._initial_frame)

    @property
    def project(self):
        return self.controller.project

    @property
    def selected_part(self):
        if self.project and self.selected_surface in self.project.surfaces:
            return self.project.surfaces[self.selected_surface].part_id
        return None

    @property
    def unit_factor(self):
        return float(self.units.currentData())

    def _build_workspace(self):
        body = QWidget()
        layout = QVBoxLayout(body)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("QLabel { background: #e8f3ef; padding: 9px; color: #254f42; }")
        layout.addWidget(self.hint)
        self.context = QLabel()
        self.context.setWordWrap(True)
        layout.addWidget(self.context)
        self.sketch = CurveSketch()
        self.viewport = AuthorViewport()
        self.paper = AuthorPaperView()
        construction = QSplitter(Qt.Orientation.Vertical)
        construction.addWidget(self.sketch)
        construction.addWidget(self.viewport)
        construction.setSizes([430, 320])
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.addWidget(construction)
        self.workspace_splitter.addWidget(self.paper)
        self.workspace_splitter.setSizes([560, 640])
        layout.addWidget(self.workspace_splitter)
        self.setCentralWidget(body)
        self.sketch.outline_finished.connect(self.create_outline)
        self.sketch.open_profile_finished.connect(self.create_open_profile)
        self.sketch.curve_profile_finished.connect(self.create_curve_profile)
        self.sketch.vertex_selected.connect(self.select_vertex)
        self.sketch.vertex_moved.connect(self.move_vertex)
        self.sketch.status.connect(self.statusBar().showMessage)
        self.sketch.draft_changed.connect(self.update_guidance)
        self.viewport.surface_selected.connect(self.select_surface)
        self.viewport.edge_selected.connect(self.select_edge)
        self.viewport.profile_selected.connect(self.select_profile)
        self.paper.part_selected.connect(self.select_part)
        # Completing a connection may rebuild the paper scene; finish the item event first.
        self.paper.edge_selected.connect(self.select_edge, Qt.ConnectionType.QueuedConnection)
        self.paper.placement_changed.connect(self.move_part)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Moje plochy a díly")
        self.tree.itemSelectionChanged.connect(self.tree_selection)
        tree_dock = QDockWidget("Konstrukce", self)
        tree_dock.setWidget(self.tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, tree_dock)
        self.issues = QListWidget()
        self.issues.itemClicked.connect(self.select_issue)
        self.issues.itemActivated.connect(self.select_issue)
        self.issues.currentItemChanged.connect(lambda *_: self.update_ack_button())
        self.issues.setMaximumHeight(130)
        issues_box = QWidget()
        issues_layout = QVBoxLayout(issues_box)
        issues_layout.addWidget(self.issues)
        self.ack_button = QPushButton("Přijmout vybrané varování pro tento stav")
        self.ack_button.clicked.connect(self.acknowledge)
        issues_layout.addWidget(self.ack_button)
        issues_dock = QDockWidget("Co je potřeba zkontrolovat", self)
        issues_dock.setWidget(issues_box)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, issues_dock)

    def _action(self, key, text, slot, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        self.actions[key] = action
        return action

    def _build_actions(self):
        project_menu = self.menuBar().addMenu("Projekt")
        for key, text, slot, shortcut in [
            ("new", "Nový prázdný model", self.new_project, "Ctrl+N"),
            ("open", "Otevřít…", self.open_project, "Ctrl+O"),
            ("save", "Uložit", self.save_project, "Ctrl+S"),
            ("save_as", "Uložit jako…", lambda: self.save_project(save_as=True), "Ctrl+Shift+S"),
            ("export", "Exportovat SVG a PDF…", self.export_project, "Ctrl+E"),
        ]:
            project_menu.addAction(self._action(key, text, slot, shortcut))
        project_menu.addAction(
            self._action("material", "Papír a místo pro ohyb…", self.edit_material)
        )
        edit = self.menuBar().addMenu("Úpravy")
        edit.addAction(self._action("undo", "Vrátit změnu", self.undo_command, "Ctrl+Z"))
        edit.addAction(self._action("redo", "Zopakovat změnu", self.redo_command, "Ctrl+Y"))
        edit.addAction(self._action(
            "rename", "Pojmenovat model a vybraný díl…", self.rename_selection, "F2"
        ))
        edit.addAction(self._action(
            "delete_part", "Odstranit vybraný papírový díl…", self.delete_selected_part
        ))
        construct = self.menuBar().addMenu("Vytvořit")
        construct.addAction(
            self._action("draw", "Nakreslit vlastní díl", self.start_outline, "Ctrl+L")
        )
        construct.addAction(self._action("rectangle", "Obdélník z rozměrů…", self.create_rectangle))
        construct.addAction(self._action(
            "edit_curve", "Upravit vybraný úsek profilu…", self.edit_curve
        ))
        construct.addAction(self._action(
            "split_profile", "Rozdělit vybraný úsek obrysu…", self.split_profile_segment
        ))
        construct.addAction(self._action(
            "merge_profile", "Spojit původní úseky obrysu…", self.merge_profile_segments
        ))
        construct.addAction(self._action(
            "copy_profile", "Kopie vybraného profilu do hloubky…", self.copy_selected_profile
        ))
        construct.addAction(self._action(
            "profile_plane", "Hloubka a rovina vybraného profilu…", self.place_selected_profile
        ))
        construct.addAction(self._action(
            "loft", "Vytvořit plochu mezi dvěma profily…", self.create_loft
        ))
        construct.addAction(self._action(
            "edit_loft", "Upravit profily a šev této plochy…", self.edit_loft
        ))
        construct.addAction(self._action(
            "segment", "Odvodit rovinné díly s povolenou odchylkou…", self.segment_surface
        ))
        construct.addAction(self._action(
            "manual_grid", "Ruční rozmístění více dílů…", self.manual_grid
        ))
        construct.addAction(
            self._action(
                "open_profile",
                "Uložit jako otevřený profil",
                self.sketch.finish_open_profile,
                "Ctrl+Return",
            )
        )
        construct.addAction(
            self._action(
                "append_profile",
                "Přidat bod do otevřeného profilu…",
                self.append_profile_point,
            )
        )
        construct.addAction(
            self._action(
                "profile_surface",
                "Uzavřít profil a vytvořit plochu",
                self.surface_from_profile,
            )
        )
        construct.addAction(
            self._action("finish", "Uzavřít obrys a vytvořit plochu", self.sketch.finish_outline)
        )
        construct.addAction(
            self._action("hole", "Nakreslit otvor do vybrané plochy", self.start_hole, "Ctrl+H")
        )
        construct.addAction(
            self._action(
                "attach_inside", "Připojit hranu dovnitř plochy…", self.attach_inside, "Ctrl+J"
            )
        )
        construct.addAction(
            self._action(
                "glue_region", "Přilepit plochu oblastí…", self.glue_region, "Ctrl+Shift+J"
            )
        )
        construct.addAction(
            self._action("cancel", "Zrušit rozpracovanou operaci", self.cancel_operation, "Esc")
        )
        construct.addAction(
            self._action(
                "recompute",
                "Přepočítat papírové díly",
                lambda: self.run(self.controller.recompute),
                "Ctrl+R",
            )
        )
        view_menu = self.menuBar().addMenu("Zobrazení a pomoc")
        view_menu.addAction(self._action("focus", "Zaměřit vybraný díl", self.focus_selection, "F"))
        view_menu.addAction(
            self._action("focus_all", "Zaměřit celý model a stránky", self.focus_all, "Home")
        )
        # Canvas navigation must not steal Home/F from a focused property/list.
        for key in ("focus", "focus_all"):
            self.actions[key].setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
            for canvas in (self, self.sketch, self.viewport, self.paper):
                canvas.addAction(self.actions[key])
        self.tips_action = QAction("Zobrazovat tipy", self, checkable=True)
        self.tips_action.setChecked(self.settings.value("tips_enabled", True, type=bool))
        self.tips_action.toggled.connect(self.set_tips)
        view_menu.addAction(self.tips_action)
        view_menu.addAction(self._action("repeat_tip", "Připomenout postup", self.repeat_tip, "F1"))
        toolbar = QToolBar("Tvorba a ověření", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.curve_mode = QComboBox()
        for label, mode in (("Úsečka", "line"), ("Oblouk přes tři body", "arc"),
                            ("Křivka se dvěma úchopy", "cubic")):
            self.curve_mode.addItem(label, mode)
        self.curve_mode.setToolTip("Tvar dalšího úseku při kreslení vlastního profilu")
        self.curve_mode.currentIndexChanged.connect(self.change_curve_mode)
        self.sketch.segment_mode_changed.connect(
            lambda mode: self.curve_mode.setCurrentIndex(self.curve_mode.findData(mode))
        )
        toolbar.addWidget(self.curve_mode)
        for key in (
            "draw",
            "rectangle",
            "finish",
            "hole",
            "cancel",
            "undo",
            "redo",
            "recompute",
            "export",
        ):
            toolbar.addAction(self.actions[key])

    @staticmethod
    def _spin(low=-1e9, high=1e9, decimals=6, suffix=""):
        field = QDoubleSpinBox()
        field.setRange(low, high)
        field.setDecimals(decimals)
        field.setKeyboardTracking(False)
        field.setSuffix(suffix)
        return field

    def _section(self, layout, title, *, collapsed=False):
        button = QToolButton()
        button.setText(title)
        button.setCheckable(True)
        button.setChecked(not collapsed)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setArrowType(Qt.ArrowType.RightArrow if collapsed else Qt.ArrowType.DownArrow)
        layout.addWidget(button)
        box = QWidget()
        form = QFormLayout(box)
        form.setContentsMargins(2, 4, 2, 10)
        layout.addWidget(box)
        box.setVisible(not collapsed)
        button.toggled.connect(box.setVisible)
        button.toggled.connect(
            lambda checked: button.setArrowType(
                Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
            )
        )
        self.sections[title] = (button, box)
        return form

    def _build_properties(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        self.selection_label = QLabel("Zatím není vybraná plocha.")
        self.selection_label.setWordWrap(True)
        layout.addWidget(self.selection_label)
        commands = QHBoxLayout()
        self.rename_button = QPushButton("Pojmenovat…")
        self.rename_button.clicked.connect(self.rename_selection)
        commands.addWidget(self.rename_button)
        self.delete_part_button = QPushButton("Odstranit díl…")
        self.delete_part_button.clicked.connect(self.delete_selected_part)
        commands.addWidget(self.delete_part_button)
        layout.addLayout(commands)
        form = self._section(layout, "Jednotky a tvorba")
        self.units = QComboBox()
        for label, factor in [("m", 1000), ("cm", 10), ("mm", 1)]:
            self.units.addItem(label, factor)
        self.units.currentIndexChanged.connect(self.unit_changed)
        form.addRow("Rozměry modelu", self.units)
        self.plane = QComboBox()
        for label, value in [
            ("Vodorovně (půdorys)", "XY"),
            ("Svisle (stěna)", "XZ"),
            ("Svisle (čelo)", "YZ"),
        ]:
            self.plane.addItem(label, value)
        form.addRow("Nová pracovní rovina", self.plane)
        self.scale_field = self._spin(1, 1e6, 3)
        self.scale_field.editingFinished.connect(self.change_scale)
        form.addRow("Měřítko 1 :", self.scale_field)
        self.grid = self._spin(0, 10000, 4)
        self.grid.setValue(0.1)
        self.grid.valueChanged.connect(
            lambda value: setattr(self.sketch, "grid_mm", value * self.unit_factor)
        )
        form.addRow("Síť obrysu (Alt obejde)", self.grid)
        self.material_button = QPushButton("Papír a místo pro ohyb…")
        self.material_button.clicked.connect(self.edit_material)
        form.addRow(self.material_button)
        form = self._section(layout, "Profil a křivky")
        self.curve_choice = QComboBox()
        self.curve_choice.currentIndexChanged.connect(self.choose_curve)
        form.addRow("Úsek zdrojového profilu", self.curve_choice)
        self.curve_edit_button = QPushButton("Upravit tvar a úchopy…")
        self.curve_edit_button.clicked.connect(self.edit_curve)
        form.addRow(self.curve_edit_button)
        self.split_profile_button = QPushButton("Rozdělit úsek…")
        self.split_profile_button.clicked.connect(self.split_profile_segment)
        form.addRow(self.split_profile_button)
        self.merge_profile_button = QPushButton("Spojit původní úseky…")
        self.merge_profile_button.clicked.connect(self.merge_profile_segments)
        form.addRow(self.merge_profile_button)
        self.copy_profile_button = QPushButton("Kopie profilu do hloubky…")
        self.copy_profile_button.clicked.connect(self.copy_selected_profile)
        form.addRow(self.copy_profile_button)
        self.profile_plane_button = QPushButton("Hloubka a rovina profilu…")
        self.profile_plane_button.clicked.connect(self.place_selected_profile)
        form.addRow(self.profile_plane_button)
        self.loft_button = QPushButton("Plocha mezi dvěma profily…")
        self.loft_button.clicked.connect(self.create_loft)
        form.addRow(self.loft_button)
        self.loft_edit_button = QPushButton("Upravit dvojice profilů a šev…")
        self.loft_edit_button.clicked.connect(self.edit_loft)
        form.addRow(self.loft_edit_button)
        self.generation_choice = QComboBox()
        self.generation_choice.currentIndexChanged.connect(self.choose_generation)
        form.addRow("Odvozené generace", self.generation_choice)
        self.segmentation_status = QLabel()
        self.segmentation_status.setWordWrap(True)
        self.segmentation_status.setTextFormat(Qt.TextFormat.PlainText)
        form.addRow(self.segmentation_status)
        self.segment_button = QPushButton("Odvodit rovinné díly…")
        self.segment_button.clicked.connect(self.segment_surface)
        form.addRow(self.segment_button)
        self.select_generation_button = QPushButton("Použít vybranou generaci pro tisk")
        self.select_generation_button.clicked.connect(self.use_generation)
        form.addRow(self.select_generation_button)
        self.restore_target_button = QPushButton("Vrátit původní konstrukční cíl")
        self.restore_target_button.clicked.connect(self.restore_target)
        form.addRow(self.restore_target_button)
        form = self._section(layout, "Bod obrysu")
        self.vertex_choice = QComboBox()
        self.vertex_choice.currentIndexChanged.connect(self.choose_vertex)
        form.addRow("Vybraný bod", self.vertex_choice)
        self.vertex_x, self.vertex_y = self._spin(), self._spin()
        self.vertex_x.editingFinished.connect(self.edit_vertex)
        self.vertex_y.editingFinished.connect(self.edit_vertex)
        form.addRow("Vodorovně", self.vertex_x)
        form.addRow("Svisle v obrysu", self.vertex_y)
        form = self._section(layout, "Umístění v prostoru", collapsed=True)
        self.transform_fields = []
        for label in (
            "Posun X",
            "Posun Y",
            "Výška Z",
            "Natočení X (°)",
            "Natočení Y (°)",
            "Natočení Z (°)",
        ):
            spin = self._spin()
            spin.editingFinished.connect(self.edit_transform)
            self.transform_fields.append(spin)
            form.addRow(label, spin)
        form = self._section(layout, "Hrany, spoj a chlopeň")
        self.edge_form = form
        self.edge_choice = QComboBox()
        self.edge_choice.currentIndexChanged.connect(self.choose_edge)
        form.addRow("Okraj vybrané plochy", self.edge_choice)
        self.connect_button = QPushButton("Připojit k další hraně")
        self.connect_button.clicked.connect(self.start_connection)
        form.addRow(self.connect_button)
        self.attach_inside_button = QPushButton("Připojit dovnitř plochy…")
        self.attach_inside_button.clicked.connect(self.attach_inside)
        form.addRow(self.attach_inside_button)
        self.glue_region_button = QPushButton("Přilepit plochu oblastí…")
        self.glue_region_button.clicked.connect(self.glue_region)
        form.addRow(self.glue_region_button)
        self.joint_choice = QComboBox()
        self.joint_choice.currentIndexChanged.connect(self.choose_joint)
        form.addRow("Existující spoj", self.joint_choice)
        self.joint_mode = QComboBox()
        self.joint_mode.addItem("Řez a lepení", "cut")
        self.joint_mode.addItem("Souvislý přehyb", "fold")
        self.joint_mode.currentIndexChanged.connect(self.change_joint)
        form.addRow("Způsob spojení", self.joint_mode)
        self.tab_owner = QComboBox()
        self.tab_owner.currentIndexChanged.connect(self.change_tab)
        form.addRow("Chlopeň", self.tab_owner)
        self.tab_width = self._spin(0.01, 1000, 4, " mm")
        self.tab_taper = self._spin(0, 1, 4)
        self.tab_shape = QComboBox()
        self.tab_shape.addItem("Zkosená", "trapezoid")
        self.tab_shape.addItem("Trojúhelníková", "triangle")
        self.tab_width.editingFinished.connect(self.change_tab)
        self.tab_taper.editingFinished.connect(self.change_tab)
        self.tab_shape.currentIndexChanged.connect(self.change_tab)
        form.addRow("Šířka na papíře", self.tab_width)
        form.addRow("Poměr zúžení", self.tab_taper)
        form.addRow("Tvar", self.tab_shape)
        self.partner_label = QLabel()
        self.partner_label.setWordWrap(True)
        form.addRow(self.partner_label)
        self.partner_button = QPushButton("Ukázat protikus")
        self.partner_button.clicked.connect(self.show_partner)
        form.addRow(self.partner_button)
        form = self._section(layout, "Autorské spoje a záložky")
        self.connectors_panel = ConnectorPanel(self)
        self.connectors_panel.relation_changed.connect(self.show_connector_relation)
        form.addRow(self.connectors_panel)
        form = self._section(layout, "Díl na papíře")
        self.page_choice = QComboBox()
        self.page_choice.currentIndexChanged.connect(self.edit_placement)
        form.addRow("Umístění", self.page_choice)
        self.paper_x, self.paper_y, self.paper_angle = (
            self._spin(suffix=" mm"),
            self._spin(suffix=" mm"),
            self._spin(suffix="°"),
        )
        for label, spin in [
            ("Kotva X", self.paper_x),
            ("Kotva Y", self.paper_y),
            ("Natočení", self.paper_angle),
        ]:
            spin.editingFinished.connect(self.edit_placement)
            form.addRow(label, spin)
        self.position_lock = QCheckBox("Zamknout polohu")
        self.rotation_lock = QCheckBox("Zamknout natočení")
        self.position_lock.toggled.connect(self.edit_locks)
        self.rotation_lock.toggled.connect(self.edit_locks)
        form.addRow(self.position_lock)
        form.addRow(self.rotation_lock)
        self.front_side = QComboBox()
        self.front_side.addItem("Potištěná strana ven", "outside")
        self.front_side.addItem("Potištěná strana dovnitř", "inside")
        self.front_side.currentIndexChanged.connect(self.change_front)
        form.addRow(self.front_side)
        self.anchor_button = QPushButton("Změnit kotvu dílu…")
        self.anchor_button.clicked.connect(self.change_anchor)
        form.addRow(self.anchor_button)
        self.manual_grid_button = QPushButton("Ruční rozmístění více dílů…")
        self.manual_grid_button.clicked.connect(self.manual_grid)
        form.addRow(self.manual_grid_button)
        row = QHBoxLayout()
        for text, callback in [("Přidat A4", self.add_page), ("Odebrat stránku", self.delete_page)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        form.addRow(row)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setMinimumWidth(280)
        dock = QDockWidget("Vlastnosti a další krok", self)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def run(self, operation):
        try:
            return operation()
        except Exception as exc:
            if isinstance(exc, CurveOutputError) and exc.part_id in self.project.parts:
                self.select_part(exc.part_id)
                self.paper.focus_part(exc.part_id)
                self.viewport.focus_selection()
            self._command_errors += 1
            self.statusBar().showMessage(str(exc), 12000)
            QMessageBox.warning(self, "Změnu nelze dokončit", str(exc))
            return None

    def _initial_frame(self):
        self.viewport.focus_selection(all_surfaces=True)
        self.sketch._first_frame = True
        self.sketch.set_project(self.project, self.selected_surface, self.selected_profile)

    def set_tips(self, checked):
        self.settings.setValue("tips_enabled", checked)
        self.hint.setVisible(checked)

    def repeat_tip(self):
        self.tips_action.setChecked(True)
        self.hint.show()
        self.update_guidance()

    def update_guidance(self):
        profile = self.project.profiles.get(self.selected_profile) if self.project else None
        self.actions["open_profile"].setEnabled(
            self.sketch.drawing and len(self.sketch.points) >= 2 and not self.sketch.hole
        )
        self.actions["append_profile"].setEnabled(profile is not None and not profile.closed)
        self.actions["profile_surface"].setEnabled(
            profile is not None and self.selected_surface is None
            and (len(profile.vertices) >= 3 or any(s.kind != "line" for s in profile.segments))
        )
        self.actions["finish"].setEnabled(
            self.sketch.drawing and len(self.sketch.points) >= 3 and not self.sketch.pending_points
        )
        self.actions["undo"].setEnabled(
            self.controller.can_undo or bool(self.sketch.drawing and self.sketch.points)
        )
        self.actions["redo"].setEnabled(self.controller.can_redo and not self.sketch.drawing)
        can_loft = len(self.project.profiles) >= 2 and not self.sketch.drawing
        self.actions["loft"].setEnabled(can_loft)
        self.loft_button.setEnabled(can_loft)
        self.loft_button.setToolTip(
            "Vyberte dva vlastní profily a určete, které úseky tvoří společnou plochu."
            if can_loft else "Nejprve nakreslete profil a vytvořte druhý profil nebo jeho kopii."
        )
        if self.connect_source:
            text = "Spojení: vyberte druhou hranu v prostoru nebo na papíře. Esc operaci zruší."
        elif self.sketch.drawing:
            text = self.sketch.instruction_text() + " Backspace vrátí vstup, Esc zruší návrh."
        elif profile is not None and self.selected_surface is None:
            used_by_loft = any(s.kind == "ruled_loft" and profile.id in s.source_profile_ids()
                               for s in self.project.surfaces.values())
            text = (
                "Upravujete zdrojový profil plochy. Po změně tvaru nebo hloubky "
                "přepočítejte její papírový díl (Ctrl+R)."
                if used_by_loft else
                "Vybraný profil ještě není tiskový díl. V nabídce Vytvořit přidejte body, "
                "uzavřete jej jako plochu, nebo vytvořte plochu mezi dvěma profily."
            )
        elif not self.project or not self.project.surfaces:
            text = (
                "Začněte tlačítkem Nakreslit vlastní díl, nebo zadejte rozměry obdélníku. "
                "Plocha se ukáže v prostoru i na papíře."
            )
        elif (self.selected_surface and
              self.project.surfaces[self.selected_surface].kind == "ruled_loft" and
              self.viewport.meshes.get(self.selected_surface, {}).get("status") in
              ("REJECTED", "UNRESOLVED")):
            text = (
                "Přesný rozvin této plochy není doložený. "
                + self.viewport.meshes[self.selected_surface].get("message", "")
                + " Upravte tvar nebo hloubku zdrojových profilů, případně jejich dvojice "
                "a směr příkazem Upravit dvojice profilů a šev. "
                "Samotný přepočet nezmění nerozvinutelný tvar. "
                "Příkaz Odvodit rovinné díly nabídne konkrétní aproximaci s uvedenou mezí."
            )
        elif self.selected_part and self.project.parts[self.selected_part].stale:
            text = (
                "Konstrukce se změnila. Papírový díl je neaktuální; "
                "přepočítejte jej (Ctrl+R) a zkontrolujte stránky."
            )
        elif (self.selected_surface and
              self.project.surfaces[self.selected_surface].kind == "ruled_loft"):
            text = (
                "Tvar a hloubku měňte ve zdrojových profilech. "
                "Dvojice úseků a začátek rozvinu upravíte příkazem "
                "Upravit dvojice profilů a šev. Připojení této prostorové plochy "
                "zatím nemá ověřený spoj; nelze je nahradit přímou tětivou."
            )
        elif self.selected_edge:
            text = (
                "Vybranou hranu můžete připojit k protikusu; "
                "potom určíte přehyb nebo lepení s chlopní."
            )
        else:
            text = (
                "Vyberte plochu ve stromu, v prostoru nebo na papíře. "
                "Body měníte v kresbě; díly přetahujete na stránky."
            )
        self.hint.setText(text)
        self.hint.setVisible(self.tips_action.isChecked())
        self.context.setText(
            text if self.connect_source or self.sketch.drawing else self.selection_label.text()
        )

    def refresh(self):
        if not self.project:
            return
        self._updating = True
        try:
            if (
                self.selected_surface is not None
                and self.selected_surface not in self.project.surfaces
            ):
                self.selected_surface = self.selected_edge = self.selected_vertex = (
                    self.current_joint
                ) = None
            if self.selected_profile not in self.project.profiles:
                self.selected_profile = None
            self.tree.clear()
            children = {r["surface_id"] for v in self.project.segmented_variants.values()
                        for r in v.triangle_bindings}
            parents = {}
            for sid, surface in self.project.surfaces.items():
                if sid in children:
                    continue
                part = self.project.parts[surface.part_id]
                item = QTreeWidgetItem(
                    [f"{surface.name} · {part.name}" + (" · přepočítat" if part.stale else "")]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, sid)
                self.tree.addTopLevelItem(item)
                parents[sid] = item
                if surface.kind == "ruled_loft":
                    for side, pid in zip(
                        ("První profil", "Druhý profil"), surface.source_profile_ids()
                    ):
                        child = QTreeWidgetItem([f"{side} · {self.project.profiles[pid].name}"])
                        child.setData(0, Qt.ItemDataRole.UserRole, ("profile", pid))
                        item.addChild(child)
                    item.setExpanded(True)
                if sid == self.selected_surface:
                    self.tree.setCurrentItem(item)
            for vid, variant in self.project.segmented_variants.items():
                state = self.project.segmented_variant_status(vid)["status"]
                group = QTreeWidgetItem([
                    f"{variant.name} · {state} · " +
                    ("tiskový materiál" if variant.print_selected else "uložená generace")
                ])
                group.setData(0, Qt.ItemDataRole.UserRole, ("variant", vid))
                parents[variant.target_surface_id].addChild(group)
                for record in variant.triangle_bindings:
                    sid = record["surface_id"]
                    item = QTreeWidgetItem([
                        f"{self.project.parts[record['part_id']].name} · "
                        f"{self.project.surfaces[sid].name}"
                    ])
                    item.setData(0, Qt.ItemDataRole.UserRole, sid)
                    group.addChild(item)
                    if sid == self.selected_surface:
                        self.tree.setCurrentItem(item)
                group.setExpanded(variant.print_selected)
                parents[variant.target_surface_id].setExpanded(True)
                if (self.selected_generation == vid and
                        self.selected_surface == variant.target_surface_id):
                    self.tree.setCurrentItem(group)
            used_profiles = {
                pid
                for surface in self.project.surfaces.values()
                for pid in surface.source_profile_ids()
            }
            for pid, profile in self.project.profiles.items():
                if pid not in used_profiles:
                    item = QTreeWidgetItem(
                        [f"{profile.name} · {'uzavřený' if profile.closed else 'otevřený'} profil"]
                    )
                    item.setData(0, Qt.ItemDataRole.UserRole, ("profile", pid))
                    self.tree.addTopLevelItem(item)
                    if self.selected_surface is None and pid == self.selected_profile:
                        self.tree.setCurrentItem(item)
            frame_views = self._frame_next
            self._set_viewport_project(frame=frame_views)
            self._frame_next = False
            self._show_source_sketch()
            self.paper.set_project(self.project.print_material_view(), frame=frame_views)
            self._populate_properties()
            self._highlight()
            self.issues.clear()
            for issue in self.project.validate_layout():
                label = (
                    "Přijato"
                    if issue.acknowledged
                    else "Chyba"
                    if issue.severity.lower() == "error"
                    else "Varování"
                )
                item = QListWidgetItem(f"{label}: {issue.message}")
                item.setData(Qt.ItemDataRole.UserRole, issue.id)
                self.issues.addItem(item)
            self.update_ack_button()
            self.actions["undo"].setEnabled(self.controller.can_undo)
            self.actions["redo"].setEnabled(self.controller.can_redo)
            self.actions["hole"].setEnabled(self._planar_selection())
            self._update_edit_actions()
            self.actions["recompute"].setEnabled(bool(self.project.parts))
            self.actions["export"].setEnabled(bool(self.project.parts))
            self.setWindowTitle(
                f"{'* ' if self.controller.dirty else ''}{self.project.name} "
                "— ArchPapercraft Studio"
            )
            self.update_guidance()
        finally:
            self._updating = False

    def _populate_properties(self):
        surface = self.project.surfaces.get(self.selected_surface)
        part = self.project.parts.get(self.selected_part)
        printable = part is not None and part.id in self.project.material_part_ids()
        profile = self.project.profiles.get(
            surface.profile_id if surface else self.selected_profile
        )
        unit = self.unit_factor
        for title in (
            "Bod obrysu",
            "Umístění v prostoru",
            "Hrany, spoj a chlopeň",
            "Autorské spoje a záložky",
            "Díl na papíře",
        ):
            header, box = self.sections[title]
            present = surface is not None or (title == "Bod obrysu" and profile is not None)
            header.setVisible(present)
            box.setVisible(present and header.isChecked())
        self.selection_label.setText(
            f"{surface.name} · {part.name}"
            if surface and part
            else f"{profile.name} · profil zatím není tiskový díl."
            if profile
            else "Zatím není vybraná plocha. Nakreslete vlastní obrys nebo vyberte díl."
        )
        self.scale_field.setValue(1 / self.project.scale)
        self._shown["scale"] = self.scale_field.value()
        self.vertex_choice.clear()
        if profile:
            for profile_id in (surface.source_profile_ids() if surface else [profile.id]):
                profile = self.project.profiles[profile_id]
                for index, vertex in enumerate(profile.vertices):
                    self.vertex_choice.addItem(
                        (
                            f"{profile.name} · "
                            f"Bod {index + 1}"
                        ),
                        (profile_id, vertex.id),
                    )
        index = next(
            (
                i
                for i in range(self.vertex_choice.count())
                if self.vertex_choice.itemData(i) == self.selected_vertex
            ),
            -1,
        )
        if index < 0 and self.vertex_choice.count():
            index = 0
            self.selected_vertex = self.vertex_choice.itemData(index)
        self.vertex_choice.setCurrentIndex(index)
        self._populate_vertex()
        raw_transform = (
            list(surface.position_mm) + list(surface.rotation_deg) if surface else [0.0] * 6
        )
        for index, field in enumerate(self.transform_fields):
            field.setEnabled(surface is not None)
            field.setValue(raw_transform[index] / unit if index < 3 else raw_transform[index])
        self._shown["transform"] = [f.value() for f in self.transform_fields]
        self._raw["transform"] = raw_transform
        self.edge_choice.clear()
        if surface:
            for profile_id in surface.source_profile_ids():
                for edge in self.project.profiles[profile_id].segments:
                    label = {"line": "Úsečka", "arc": "Oblouk", "cubic": "Křivka"}[edge.kind]
                    self.edge_choice.addItem(f"{label} {self.edge_choice.count() + 1}", edge.id)
        self.edge_choice.setCurrentIndex(
            self.edge_choice.findData(self.selected_edge[1]) if self.selected_edge else -1
        )
        straight = self._planar_selection() and self.selected_edge is not None and any(
            s.id == self.selected_edge[1] and s.kind == "line"
            for profile in self.project.profiles.values() for s in profile.segments
        )
        self.connect_button.setEnabled(straight)
        self.connect_button.setToolTip(
            "Spojení přímých hran. Zakřivená hrana se nesmí zaměnit za její tětivu."
        )
        can_attach = straight and len(self.project.surfaces) > 1
        self.attach_inside_button.setEnabled(can_attach)
        self.actions["attach_inside"].setEnabled(can_attach)
        can_glue = self._planar_selection() and len(self.project.surfaces) > 1
        self.glue_region_button.setEnabled(can_glue)
        self.actions["glue_region"].setEnabled(can_glue)
        self.attach_inside_button.setToolTip(
            "Vyberte okraj zdrojové plochy a nakreslete jeho místo na protikusu."
            if can_attach else "Nejprve vytvořte dvě plochy a vyberte okraj jedné z nich."
        )
        self.joint_choice.clear()
        for joint in self.project.joints.values():
            if self.selected_surface in (joint.surface_a, joint.surface_b):
                self.joint_choice.addItem(f"Spoj J{joint.number}", joint.id)
        if (
            self.current_joint not in self.project.joints
            or self.joint_choice.findData(self.current_joint) < 0
        ):
            self.current_joint = (
                self.joint_choice.itemData(0) if self.joint_choice.count() else None
            )
        self.joint_choice.setCurrentIndex(self.joint_choice.findData(self.current_joint))
        self._populate_joint()
        self.page_choice.clear()
        self.page_choice.addItem("Odkládací plocha", None)
        for index, page in enumerate(self.project.pages):
            self.page_choice.addItem(f"Stránka {index + 1}", page.id)
        placement = self.project.placements.get(self.selected_part) if printable else None
        self.page_choice.setEnabled(printable)
        self.page_choice.setCurrentIndex(
            self.page_choice.findData(placement.page_id) if placement else 0
        )
        raw = (
            [placement.x_mm, placement.y_mm, placement.rotation_deg]
            if placement
            else [0.0, 0.0, 0.0]
        )
        for field, value in zip((self.paper_x, self.paper_y, self.paper_angle), raw):
            field.setEnabled(placement is not None)
            field.setValue(value)
        self.position_lock.setChecked(bool(placement and placement.position_locked))
        self.rotation_lock.setChecked(bool(placement and placement.rotation_locked))
        self.position_lock.setEnabled(printable)
        self.rotation_lock.setEnabled(printable)
        self.front_side.setCurrentIndex(self.front_side.findData(part.front_side) if part else 0)
        self.front_side.setEnabled(printable)
        self.anchor_button.setEnabled(printable)
        self.manual_grid_button.setEnabled(bool(self.project.material_part_ids()))
        self.actions["manual_grid"].setEnabled(bool(self.project.material_part_ids()))
        self._shown["placement"] = [
            f.value() for f in (self.paper_x, self.paper_y, self.paper_angle)
        ]
        self._raw["placement"] = raw
        self._raw["page"] = placement.page_id if placement else None
        self.connectors_panel.refresh()
        self._populate_curve_choices()
        self._populate_generations()

    def _segmentation_target(self):
        surface = self.project.surfaces.get(self.selected_surface)
        if surface and surface.kind == "ruled_loft":
            return surface.id
        for variant in self.project.segmented_variants.values():
            if any(r["surface_id"] == self.selected_surface for r in variant.triangle_bindings):
                return variant.target_surface_id
        return None

    def _populate_generations(self):
        target = self._segmentation_target()
        self.generation_choice.clear()
        self.generation_choice.addItem("Nová odvozená generace", None)
        for vid, variant in self.project.segmented_variants.items():
            if variant.target_surface_id == target:
                self.generation_choice.addItem(
                    variant.name + (" · pro tisk" if variant.print_selected else " · zachovaná"),
                    vid,
                )
        if self.selected_generation not in self.project.segmented_variants:
            self.selected_generation = None
        index = self.generation_choice.findData(self.selected_generation)
        self.generation_choice.setCurrentIndex(max(index, 0))
        active = target is not None
        variant = self.project.segmented_variants.get(self.selected_generation)
        for widget in (self.generation_choice, self.segmentation_status, self.segment_button,
                       self.select_generation_button, self.restore_target_button):
            widget.setVisible(active)
        self.actions["segment"].setEnabled(active and not self.sketch.drawing)
        self.segment_button.setEnabled(active and not self.sketch.drawing)
        self.segment_button.setText("Nová generace podle tohoto náhledu…" if variant
                                    else "Odvodit rovinné díly…")
        self.select_generation_button.setEnabled(bool(variant and not variant.print_selected and
            self.project.segmented_variant_status(variant.id)["status"] == "APPROXIMATE"))
        self.restore_target_button.setEnabled(any(
            v.target_surface_id == target and v.print_selected
            for v in self.project.segmented_variants.values()))
        if variant:
            state = self.project.segmented_variant_status(variant.id)
            text = state["status"] + " · " + state["message"]
        elif active:
            text = ("Původní cíl zůstává uložený. Odvození vytvoří samostatné rovinné díly "
                    "s doloženou mezí vůči tomuto cíli, nikoli přesný rozvin hladké plochy.")
        else:
            text = ""
        if self.selected_part and self.selected_part not in self.project.material_part_ids():
            text += " Tento prvek je zachovaná reference, netiskne se."
        self.segmentation_status.setText(text)

    def choose_generation(self):
        if not self._updating:
            target = self._segmentation_target()
            self.selected_generation = self.generation_choice.currentData()
            self.selected_edge = self.selected_vertex = self.current_joint = None
            if target:
                # A generation selection is a target-level context. Keeping a
                # child of the previous generation selected would make the
                # visible properties and generation actions disagree.
                self.select_surface(target)
            else:
                self._sync_selection()

    def segment_surface(self):
        if not self._commit_pending_input() or not self._confirm_sketch_restart():
            return
        target = self._segmentation_target()
        if target is None:
            return
        dialog = SegmentedVariantDialog(
            self.project, target, variant_id=self.selected_generation, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = self.run(lambda: self.controller.execute(
                "Potvrdit odvozené rovinné díly", dialog.apply))
            if result:
                self.selected_generation = result
                first = self.project.segmented_variants[result].triangle_bindings[0]["surface_id"]
                self.select_surface(first)
                self.viewport.focus_selection(all_surfaces=True)
                self.paper.focus_part(self.selected_part)

    def use_generation(self):
        if not self._commit_pending_input() or not self.selected_generation:
            return
        vid = self.selected_generation
        self.run(lambda: self.controller.execute(
            "Zvolit odvozenou generaci pro tisk", lambda p: p.select_segmented_variant(vid)))

    def manual_grid(self):
        if not self._commit_pending_input():
            return
        variant = self.project.segmented_variants.get(self.selected_generation)
        ids = ([r["part_id"] for r in variant.triangle_bindings]
               if variant and variant.print_selected else
               [pid for pid in self.project.parts if pid in self.project.material_part_ids()])
        if not ids:
            return
        dialog = ManualGridDialog(self.project, ids, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.run(lambda: self.controller.execute("Ručně rozmístit vybrané díly", dialog.apply))
            self.paper.fitInView(self.paper.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def restore_target(self):
        if not self._commit_pending_input():
            return
        target = self._segmentation_target()
        if target:
            self.run(lambda: self.controller.execute(
                "Vrátit původní konstrukční cíl", lambda p: p.restore_segmented_target(target)))

    def _set_viewport_project(self, *, frame=False):
        visible = {sid for pid in self.project.material_part_ids()
                   for sid in self.project.parts[pid].surface_ids}
        target = self._segmentation_target()
        if target and (self.selected_surface == target or
                       self.selected_generation in self.project.segmented_variants):
            for variant in self.project.segmented_variants.values():
                if variant.target_surface_id == target:
                    visible.difference_update(r["surface_id"] for r in variant.triangle_bindings)
            if self.selected_surface == target:
                visible.add(target)
            else:
                visible.update(r["surface_id"] for r in self.project.segmented_variants[
                    self.selected_generation].triangle_bindings)
        self.viewport.set_project(self.project, frame=frame, visible_surface_ids=visible)

    def _populate_curve_choices(self):
        previous = self.curve_choice.currentData()
        self.curve_choice.clear()
        surface = self.project.surfaces.get(self.selected_surface)
        profile_ids = (surface.source_profile_ids() if surface else
                       [self.selected_profile] if self.selected_profile else [])
        for pid in profile_ids:
            profile = self.project.profiles[pid]
            for index, segment in enumerate(profile.segments):
                label = {"line": "Úsečka", "arc": "Oblouk", "cubic": "Křivka"}[segment.kind]
                self.curve_choice.addItem(
                    f"{profile.name} · {label} {index + 1}", (pid, segment.id)
                )
        selected = next((self.curve_choice.itemData(i) for i in range(self.curve_choice.count())
                         if self.selected_edge and
                         self.curve_choice.itemData(i)[1] == self.selected_edge[1]), previous)
        index = next((i for i in range(self.curve_choice.count())
                      if self.curve_choice.itemData(i) == selected), -1)
        self.curve_choice.setCurrentIndex(index if index >= 0 else 0)
        enabled = self.curve_choice.count() > 0
        self.curve_edit_button.setEnabled(enabled)
        self.actions["edit_curve"].setEnabled(enabled)
        pair = self.curve_choice.currentData()
        current = self.project.profiles[pair[0]].segment(pair[1]) if pair else None
        line_selected = current is not None and current.kind == "line"
        self.actions["split_profile"].setEnabled(line_selected)
        self.split_profile_button.setEnabled(line_selected)
        record = self.project._subdivision_record(*pair) if pair else None
        merge_enabled = record is not None and len([
            edge for edge in self.project.profiles[pair[0]].segments
            if self.project._subdivision_record(pair[0], edge.id) is record]) >= 2
        self.actions["merge_profile"].setEnabled(merge_enabled)
        self.merge_profile_button.setEnabled(merge_enabled)
        self.actions["copy_profile"].setEnabled(enabled)
        plane_editable = enabled and (surface is None or surface.kind == "ruled_loft")
        self.actions["profile_plane"].setEnabled(plane_editable)
        self.copy_profile_button.setEnabled(enabled)
        self.profile_plane_button.setEnabled(plane_editable)
        editable_loft = surface is not None and surface.kind == "ruled_loft"
        self.actions["edit_loft"].setEnabled(editable_loft)
        self.loft_edit_button.setVisible(editable_loft)
        self.loft_edit_button.setEnabled(editable_loft)
        self.sections["Profil a křivky"][0].setVisible(enabled)
        self.sections["Profil a křivky"][1].setVisible(enabled)

    def choose_curve(self):
        if self._updating or not self.curve_choice.currentData():
            return
        profile_id, segment_id = self.curve_choice.currentData()
        if self.selected_surface:
            self.selected_profile = profile_id
            self.selected_edge = (self.selected_surface, segment_id)
            self._show_source_sketch()
            self._sync_selection()

    def edit_curve(self):
        if not self._commit_pending_input():
            return
        pair = self.curve_choice.currentData()
        if not pair:
            return
        pid, segment_id = pair
        dialog = CurveEditorDialog(
            self.project, pid, segment_id, unit_factor=self.unit_factor, parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.run(lambda: self.controller.execute(
                "Upravit zdrojovou křivku",
                lambda p: p.set_profile_segment(pid, segment_id, **dialog.result_spec),
            ))

    def split_profile_segment(self):
        self._profile_subdivision_dialog(joining=False)

    def merge_profile_segments(self):
        self._profile_subdivision_dialog(joining=True)

    def _profile_subdivision_dialog(self, *, joining):
        if not self._commit_pending_input():
            return
        pair = self.curve_choice.currentData()
        if not pair:
            return
        profile_id, segment_id = pair
        source_state = self.controller.digest(self.project.to_dict())
        dialog = SubdivisionDialog(
            self.project, profile_id, segment_id, joining=joining,
            unit_factor=self.unit_factor, unit_label=self.units.currentText(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        def apply():
            if self.controller.digest(self.project.to_dict()) != source_state:
                raise ValueError("Projekt se od náhledu změnil. Otevřete dělení znovu.")
            if joining:
                new_id = self.controller.execute("Spojit původní úseky", lambda p:
                    p.merge_profile_segments(profile_id, dialog.result_spec["segment_ids"]))
                vertex_id = None
            else:
                result = self.controller.execute("Rozdělit úsek obrysu", lambda p:
                    p.split_profile_segment(profile_id, **dialog.result_spec))
                new_id, vertex_id = result["segment_ids"][0], result["vertex_id"]
            self.selected_vertex = (profile_id, vertex_id) if vertex_id else None
            self.selected_edge = (self.selected_surface, new_id) if self.selected_surface else None
            index = self.curve_choice.findData((profile_id, new_id))
            self.curve_choice.setCurrentIndex(index)
            self._sync_selection()
            self.statusBar().showMessage(
                "Obrys upraven. Pokračujte přepočtem rozvinu; krok lze vrátit Ctrl+Z.", 10000)

        self.run(apply)

    def copy_selected_profile(self):
        self._profile_placement_dialog(copying=True)

    def place_selected_profile(self):
        self._profile_placement_dialog(copying=False)

    def _profile_placement_dialog(self, *, copying):
        if not self._commit_pending_input():
            return
        choice = self.curve_choice.currentData()
        surface = self.project.surfaces.get(self.selected_surface)
        if not choice or (not copying and surface and surface.kind != "ruled_loft"):
            return
        profile_id = choice[0]
        dialog = ProfilePlacementDialog(
            self.project, profile_id, copying=copying, unit_factor=self.unit_factor,
            unit_label=self.units.currentText(), parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        spec = dialog.result_spec

        def operation(project):
            if copying:
                return project.copy_profile(profile_id, **spec)
            project.set_profile_plane(profile_id, **spec["plane"])
            return profile_id

        result = self.run(lambda: self.controller.execute("Umístit zdrojový profil", operation))
        if result:
            self.select_profile(result)

    def _planar_selection(self):
        surface = self.project.surfaces.get(self.selected_surface)
        return surface is not None and surface.kind == "planar"

    def _show_source_sketch(self):
        surface = self.project.surfaces.get(self.selected_surface)
        # A loft is not a filled polygon in the first profile plane. Show its
        # selected live source sketch; the assembled surface remains in 3D.
        sid = None if surface and surface.kind == "ruled_loft" else self.selected_surface
        self.sketch.set_project(self.project, sid, self.selected_profile)

    def create_loft(self):
        self._loft_dialog(editing=False)

    def edit_loft(self):
        self._loft_dialog(editing=True)

    def _loft_dialog(self, *, editing):
        if not self._commit_pending_input() or not self._confirm_sketch_restart():
            return
        surface = self.project.surfaces.get(self.selected_surface)
        if editing and (surface is None or surface.kind != "ruled_loft"):
            return
        if len(self.project.profiles) < 2:
            return
        dialog = LoftProfilesDialog(self.project, self.selected_profile, parent=self)
        if editing:
            dialog.load_parameters(
                surface.profile_id, surface.params, existing_surface_id=surface.id
            )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        def operation(project):
            if not editing:
                return dialog.apply(project)
            dialog.check_source(project)
            parameters = dict(dialog.result_parameters)
            parameters.pop("first_profile_id")
            parameters.pop("end_ruling_id", None)
            project.update_loft(surface.id, **parameters)
            return surface.id

        result = self.run(lambda: self.controller.execute(
            "Upravit plochu mezi profily" if editing else "Vytvořit plochu mezi profily", operation
        ))
        if result:
            self.cancel_operation()
            self.select_surface(result)
            self.viewport.focus_selection()
            self.viewport.focus_selection(all_surfaces=True)

    def change_curve_mode(self):
        self.sketch.set_segment_mode(self.curve_mode.currentData())
        self.update_guidance()

    def _populate_vertex(self):
        vertex = None
        if self.selected_vertex:
            profile = self.project.profiles.get(self.selected_vertex[0])
            vertex = profile.vertex(self.selected_vertex[1]) if profile else None
        for field, value in zip(
            (self.vertex_x, self.vertex_y), vertex.point if vertex else [0.0, 0.0]
        ):
            field.setEnabled(vertex is not None)
            field.setValue(value / self.unit_factor)
        self._shown["vertex"] = [self.vertex_x.value(), self.vertex_y.value()]
        self._raw["vertex"] = list(vertex.point) if vertex else [0.0, 0.0]

    def _populate_joint(self):
        joint = self.project.joints.get(self.current_joint)
        connector = self.project.connectors.get(joint.connector_id) if joint else None
        self.joint_mode.setEnabled(joint is not None)
        self.joint_mode.setCurrentIndex(self.joint_mode.findData(joint.mode) if joint else 0)
        self.tab_owner.clear()
        self.tab_owner.addItem("Bez chlopně", None)
        if joint:
            self.tab_owner.addItem(self.project.surfaces[joint.surface_a].name, joint.surface_a)
            self.tab_owner.addItem(self.project.surfaces[joint.surface_b].name, joint.surface_b)
        self.tab_owner.setCurrentIndex(
            self.tab_owner.findData(connector.owner_surface_id) if connector else 0
        )
        enabled = joint is not None and joint.mode == "cut"
        for field in (self.tab_owner, self.tab_width, self.tab_taper, self.tab_shape):
            field.setEnabled(enabled)
        self.tab_width.setValue(connector.width_mm if connector else 5)
        self.tab_taper.setValue(connector.taper if connector else 0.6)
        self.tab_shape.setCurrentIndex(self.tab_shape.findData(connector.shape) if connector else 0)
        self._shown["tab"] = [
            self.tab_owner.currentData(),
            self.tab_width.value(),
            self.tab_taper.value(),
            self.tab_shape.currentData(),
        ]
        self.partner_button.setEnabled(joint is not None)
        if joint:
            first, second = (
                self.project.parts[self.project.surfaces[sid].part_id]
                for sid in (joint.surface_a, joint.surface_b)
            )

            def page_name(pid):
                page_id = self.project.placements[pid].page_id
                return next(
                    (
                        f"stránka {i + 1}"
                        for i, p in enumerate(self.project.pages)
                        if p.id == page_id
                    ),
                    "odkládací plocha",
                )

            self.partner_label.setText(
                f"J{joint.number}: {first.name} ({page_name(first.id)}) "
                f"↔ {second.name} ({page_name(second.id)})"
            )
        else:
            self.partner_label.setText("Nejprve vyberte a připojte hranu k protikusu.")

    def _highlight(self):
        surfaces = self.project.parts[self.selected_part].surface_ids if self.selected_part else []
        self.viewport.select(surfaces, self.selected_edge)
        self.viewport.select_profile(self.selected_profile if not self.selected_surface else None)
        self.paper.select(self.selected_part, self.selected_edge)

    def select_surface(self, surface_id):
        if not surface_id:
            self.clear_selection()
            return
        if self._updating or surface_id not in self.project.surfaces:
            return
        self.selected_surface = surface_id
        owning = next((v.id for v in self.project.segmented_variants.values()
                       if any(r["surface_id"] == surface_id for r in v.triangle_bindings)), None)
        if owning:
            self.selected_generation = owning
        elif (self.selected_generation not in self.project.segmented_variants or
              self.project.segmented_variants[self.selected_generation].target_surface_id !=
              surface_id):
            self.selected_generation = None
        if self.project.segmented_variants:
            self._set_viewport_project()
        surface = self.project.surfaces[surface_id]
        self.selected_profile = next((pid for pid in surface.source_profile_ids()
            if self.selected_edge and any(s.id == self.selected_edge[1]
                for s in self.project.profiles[pid].segments)), surface.profile_id)
        self.selected_vertex = None
        if self.selected_edge and self.selected_edge[0] != surface_id:
            self.selected_edge = None
        self._show_source_sketch()
        self._sync_selection()

    def _sync_selection(self):
        self._updating = True
        try:
            selection = ("variant", self.selected_generation) if (
                self.selected_generation in self.project.segmented_variants and
                self.selected_surface == self.project.segmented_variants[
                    self.selected_generation].target_surface_id) else self.selected_surface
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.ItemDataRole.UserRole) in (
                        selection, ("profile", self.selected_profile)):
                    self.tree.setCurrentItem(item)
                iterator += 1
            self._populate_properties()
            self._highlight()
            self.actions["hole"].setEnabled(self._planar_selection())
            self._update_edit_actions()
            self.update_guidance()
        finally:
            self._updating = False

    def select_part(self, part_id):
        if not part_id:
            self.clear_selection()
            return
        if not self._updating and part_id in self.project.parts:
            self.select_surface(self.project.surface_for_part(part_id))

    def clear_selection(self):
        if self._updating:
            return
        self.selected_surface = self.selected_profile = self.selected_edge = None
        self.selected_generation = None
        self.selected_vertex = self.current_joint = None
        self._updating = True
        try:
            self.tree.clearSelection()
            self.tree.setCurrentItem(None)
            self.sketch.set_project(self.project)
        finally:
            self._updating = False
        if self.project.segmented_variants:
            self._set_viewport_project()
        self._sync_selection()

    def select_edge(self, surface_id, edge_id):
        if self._updating:
            return
        source = self.connect_source
        if source and source != (surface_id, edge_id):
            result = self.preview_connection(source, (surface_id, edge_id))
            if result:
                self.connect_source = None
                self.current_joint = result
        self.selected_edge = (surface_id, edge_id)
        self.select_surface(surface_id)

    def select_vertex(self, profile_id, vertex_id):
        self.selected_vertex = (profile_id, vertex_id)
        self._updating = True
        try:
            self.vertex_choice.setCurrentIndex(
                next(
                    (
                        i
                        for i in range(self.vertex_choice.count())
                        if self.vertex_choice.itemData(i) == self.selected_vertex
                    ),
                    -1,
                )
            )
            self._populate_vertex()
        finally:
            self._updating = False

    def choose_vertex(self):
        if not self._updating:
            data = self.vertex_choice.currentData()
            if data:
                self.select_vertex(*data)

    def choose_edge(self):
        if not self._updating and self.edge_choice.currentData():
            self.select_edge(self.selected_surface, self.edge_choice.currentData())

    def choose_joint(self):
        if not self._updating:
            self.current_joint = self.joint_choice.currentData()
            self._updating = True
            self._populate_joint()
            self._updating = False
            self.select_connector_relation(("joint", self.current_joint))

    def select_connector_relation(self, relation):
        choice = self.connectors_panel.relationship
        for index in range(choice.count()):
            if choice.itemData(index) == relation:
                choice.setCurrentIndex(index)
                self.show_connector_relation(relation)
                break

    def show_connector_relation(self, relation):
        updating = self._updating
        self._updating = True
        try:
            self.current_joint = relation[1] if relation and relation[0] == "joint" else None
            self.joint_choice.setCurrentIndex(self.joint_choice.findData(self.current_joint))
            self._populate_joint()
            # The two entry points edit the same selected relationship. An interior
            # receiver must never leave another EdgePair active in the basic form.
            for field in (
                self.joint_choice, self.joint_mode, self.tab_owner, self.tab_width,
                self.tab_taper, self.tab_shape, self.partner_label, self.partner_button,
            ):
                self.edge_form.setRowVisible(field, self.current_joint is not None)
            self.viewport.select_relation(relation)
        finally:
            self._updating = updating

    def tree_selection(self):
        if not self._updating and self.tree.selectedItems():
            data = self.tree.selectedItems()[0].data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, (tuple, list)) and data[0] == "profile":
                self.select_profile(data[1])
            elif isinstance(data, (tuple, list)) and data[0] == "variant":
                self.selected_generation = data[1]
                self.select_surface(self.project.segmented_variants[data[1]].target_surface_id)
            else:
                self.selected_generation = None
                self.select_surface(data)

    def start_outline(self):
        if self.sketch.drawing and self.sketch.points and not self.sketch.hole:
            self.sketch.setFocus()
            return
        if not self._confirm_sketch_restart():
            return
        self.connect_source = None
        self.draft_surface = None
        self.draft_plane = self.plane.currentData()
        self.sketch.start_outline()
        self.update_guidance()

    def _confirm_sketch_restart(self):
        if self.sketch.drawing and self.sketch.points:
            answer = QMessageBox.question(
                self, "Rozpracovaný obrys",
                "Nejprve dokončete současný obrys, nebo potvrďte zahození jeho bodů.",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            return answer == QMessageBox.StandardButton.Discard
        return True

    def select_profile(self, profile_id):
        if self._updating or profile_id not in self.project.profiles:
            return
        self.selected_generation = None
        self.selected_surface = self.selected_edge = self.selected_vertex = self.current_joint = (
            None
        )
        self.selected_profile = profile_id
        if self.project.segmented_variants:
            self._set_viewport_project()
        self.sketch.set_project(self.project, None, profile_id)
        self._sync_selection()

    def create_open_profile(self, points):
        result = self.run(
            lambda: self.controller.execute(
                "Vytvořit otevřený profil",
                lambda p: p.add_profile(
                    points,
                    closed=False,
                    name=f"Profil {len(p.profiles) + 1}",
                    plane=self.plane.currentData(),
                ),
            )
        )
        if result:
            self.draft_surface = self.draft_plane = None
            self.select_profile(result)
            self.sketch.focus_surface()
        else:
            self.sketch.points = points
            self.sketch.hole = False
            self.sketch.drawing = True
            self.sketch.setCursor(Qt.CursorShape.CrossCursor)
            self.sketch.redraw()
        self.update_guidance()

    def append_profile_point(self):
        profile = self.project.profiles.get(self.selected_profile)
        if profile is None or profile.closed:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Další bod otevřeného profilu")
        form = QFormLayout(dialog)
        x, y = self._spin(), self._spin()
        x.setValue(profile.points[-1][0] / self.unit_factor)
        y.setValue((profile.points[-1][1] + 1000) / self.unit_factor)
        form.addRow(f"Vodorovně ({self.units.currentText()})", x)
        form.addRow(f"Svisle ({self.units.currentText()})", y)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            point = [x.value() * self.unit_factor, y.value() * self.unit_factor]
            result = self.run(
                lambda: self.controller.execute(
                    "Přidat bod profilu",
                    lambda p: p.append_vertex(profile.id, point),
                )
            )
            if result:
                self.select_vertex(profile.id, result)

    def surface_from_profile(self):
        profile_id = self.selected_profile
        if profile_id not in self.project.profiles or self.selected_surface is not None:
            return

        def operation(project):
            project.close_profile(profile_id)
            return project.add_surface(profile_id, name=f"Plocha {len(project.surfaces) + 1}")

        result = self.run(lambda: self.controller.execute("Vytvořit plochu z profilu", operation))
        if result:
            self.select_surface(result)
            self.viewport.focus_selection()

    def start_hole(self):
        if self._planar_selection():
            if (
                self.sketch.drawing and self.sketch.points and self.sketch.hole
                and self.draft_surface == self.selected_surface
            ):
                self.sketch.setFocus()
                return
            if not self._confirm_sketch_restart():
                return
            self.draft_surface = self.selected_surface
            surface = self.project.surfaces[self.selected_surface]
            self.draft_plane = self.project.profiles[surface.profile_id].plane
            self.sketch.start_outline(hole=True)
            self.update_guidance()

    def cancel_operation(self):
        self._cancel_gesture()
        self.connect_source = None
        if self.sketch.drawing:
            self.sketch.cancel_outline()
        self.draft_surface = self.draft_plane = None
        self.update_guidance()

    def _cancel_gesture(self):
        cancelled = False
        for view in (self.sketch, self.paper):
            grabber = view.scene().mouseGrabberItem()
            if grabber is not None and hasattr(grabber, "cancel_drag"):
                grabber.cancel_drag()
                cancelled = True
        return cancelled

    def undo_command(self):
        if self._cancel_gesture():
            return
        if self.sketch.drawing and self.sketch.points:
            self.sketch.undo_draft_point()
            self.update_guidance()
            return
        self.controller.undo()

    def redo_command(self):
        if self.sketch.drawing or self._cancel_gesture():
            return
        self.controller.redo()

    def create_curve_profile(self, segments, closed, hole):
        surface_id = (self.draft_surface or self.selected_surface) if hole else None
        plane = self.draft_plane or (
            self.project.profiles[self.project.surfaces[surface_id].profile_id].plane
            if hole and surface_id else self.plane.currentData()
        )

        def operation(project):
            pid = project.add_profile(
                segments=segments, closed=closed, plane=plane,
                name="Otvor" if hole else f"Profil {len(project.profiles) + 1}",
            )
            if not closed:
                return pid
            if hole:
                project.add_hole(surface_id, pid)
                return surface_id
            return project.add_surface(pid, name=f"Plocha {len(project.surfaces) + 1}")

        result = self.run(lambda: self.controller.execute(
            "Vytvořit vlastní křivkový profil", operation
        ))
        if result:
            self.sketch.complete_curve_draft()
            self.draft_surface = self.draft_plane = None
            self.select_surface(result) if closed else self.select_profile(result)
            self.sketch.focus_surface()
            self.viewport.focus_selection()
        self.update_guidance()

    def create_outline(self, points, hole=False):
        surface_id = (self.draft_surface or self.selected_surface) if hole else None
        plane = self.draft_plane or (
            self.project.profiles[self.project.surfaces[surface_id].profile_id].plane
            if hole and surface_id
            else self.plane.currentData()
        )

        def operation(project):
            pid = project.add_profile(
                points, name="Otvor" if hole else "Vlastní obrys", plane=plane
            )
            if hole:
                project.add_hole(surface_id, pid)
                return surface_id
            return project.add_surface(pid, name=f"Plocha {len(project.surfaces) + 1}")

        result = self.run(
            lambda: self.controller.execute(
                "Vytvořit otvor" if hole else "Vytvořit vlastní plochu", operation
            )
        )
        if result:
            self.draft_surface = self.draft_plane = None
            self.select_surface(result)
            self.viewport.focus_selection()
            self.sketch.focus_surface()
        else:
            self.sketch.points = points
            self.sketch.hole = hole
            self.sketch.drawing = True
            self.sketch.setCursor(Qt.CursorShape.CrossCursor)
            self.sketch.redraw()
            self.statusBar().showMessage(
                "Obrys se nepoužil. Backspace vrátí poslední bod; Esc návrh zruší."
            )
        self.update_guidance()

    def create_rectangle(self):
        if not self._confirm_sketch_restart():
            return
        self.sketch.cancel_outline()
        self.draft_surface = self.draft_plane = None
        dialog = QDialog(self)
        dialog.setWindowTitle("Vlastní obdélník")
        form = QFormLayout(dialog)
        width, height = self._spin(0.000001, 1e9), self._spin(0.000001, 1e9)
        width.setValue(5_000 / self.unit_factor)
        height.setValue(3_000 / self.unit_factor)
        form.addRow(f"Šířka ({self.units.currentText()})", width)
        form.addRow(f"Výška ({self.units.currentText()})", height)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            w, h = width.value() * self.unit_factor, height.value() * self.unit_factor
            self.create_outline([[0, 0], [w, 0], [w, h], [0, h]])

    def move_vertex(self, profile_id, vertex_id, x, y):
        self.run(
            lambda: self.controller.execute(
                "Posunout bod", lambda p: p.move_vertex(profile_id, vertex_id, [x, y])
            )
        )

    def edit_vertex(self):
        if self._updating or not self.selected_vertex:
            return
        values = [self.vertex_x.value(), self.vertex_y.value()]
        old = self._shown.get("vertex", values)
        if values == old:
            return
        raw = self._raw["vertex"]
        point = [
            raw[i] if value == old[i] else value * self.unit_factor
            for i, value in enumerate(values)
        ]
        self.move_vertex(*self.selected_vertex, *point)

    def edit_transform(self):
        if self._updating or not self.selected_surface:
            return
        values = [f.value() for f in self.transform_fields]
        old = self._shown.get("transform", values)
        if values == old:
            return
        raw = self._raw["transform"]
        changed = [
            raw[i] if v == old[i] else v * self.unit_factor if i < 3 else v
            for i, v in enumerate(values)
        ]
        self.run(
            lambda: self.controller.execute(
                "Umístit plochu",
                lambda p: p.set_transform(self.selected_surface, changed[:3], changed[3:]),
            )
        )

    def change_scale(self):
        if not self._updating and self.scale_field.value() != self._shown.get("scale"):
            self.run(
                lambda: self.controller.execute(
                    "Změnit měřítko", lambda p: p.set_scale(1 / self.scale_field.value())
                )
            )

    def _update_edit_actions(self):
        selected = self.selected_part is not None
        self.actions["delete_part"].setEnabled(selected)
        self.delete_part_button.setEnabled(selected)

    def rename_selection(self):
        if not self._commit_pending_input():
            return
        dialog = RenameDialog(
            self.project, surface_id=self.selected_surface,
            part_id=self.selected_part, parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.run(lambda: self.controller.execute("Pojmenovat model a díl", dialog.apply))

    def delete_selected_part(self):
        if not self._commit_pending_input() or self.selected_part is None:
            return
        dialog = DeletePartDialog(self.project, self.selected_part, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.run(lambda: self.controller.execute("Odstranit papírový díl", dialog.apply))

    def edit_material(self):
        if not self._commit_pending_input():
            return
        dialog = MaterialDialog(self.project, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.run(lambda: self.controller.execute(
                "Změnit papír a místo pro ohyb",
                lambda p: p.set_material_profile(**dialog.result_profile),
            ))

    def unit_changed(self):
        if not self._updating and self.project:
            self.sketch.display_unit = self.units.currentText()
            self.sketch.display_factor = self.unit_factor
            self.grid.setValue(self.sketch.grid_mm / self.unit_factor)
            self._sync_selection()

    def start_connection(self):
        if self.selected_edge:
            self.connect_source = self.selected_edge
            self.update_guidance()

    def attach_inside(self):
        if not self._commit_pending_input() or self.selected_edge is None:
            return
        dialog = AttachmentDialog(
            self.project, self.selected_edge, unit=self.units.currentText(),
            unit_factor=self.unit_factor, parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            spec = dialog.result_spec
            self.run(lambda: self.controller.execute(
                "Připojit hranu dovnitř plochy", lambda p: AttachmentDialog.apply(p, spec)
            ))

    def glue_region(self):
        if not self._commit_pending_input() or self.selected_surface is None:
            return
        dialog = GlueRegionDialog(
            self.project, self.selected_surface, unit=self.units.currentText(),
            unit_factor=self.unit_factor, parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            spec = dialog.result_spec
            self.run(lambda: self.controller.execute(
                "Přilepit plochu oblastí", lambda p: GlueRegionDialog.apply(p, spec)
            ))

    def preview_connection(self, source, target):
        dialog = QDialog(self)
        dialog.setWindowTitle("Umístit a připojit protikus")
        dialog.resize(700, 570)
        layout = QVBoxLayout(dialog)
        description = QLabel(
            "Zvolený protikus se přisune ke hraně. "
            "Zdrojové obrysy a ruční stránky zůstanou zachované. Zrušení nic nezmění."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        angle = self._spin(-180, 180, 3, "°")
        angle.setValue(90)
        row = QFormLayout()
        row.addRow("Úhel mezi plochami", angle)
        layout.addLayout(row)
        preview = AuthorViewport()
        layout.addWidget(preview)
        feedback = QLabel()
        feedback.setWordWrap(True)
        layout.addWidget(feedback)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        state = self.project.to_dict()

        def update_preview():
            try:
                clone = AuthorProject.from_dict(state)
                clone.place_and_connect_edges(*source, *target, angle_deg=angle.value())
                preview.set_project(clone, frame=True)
                preview.select([source[0], target[0]])
                feedback.setText(
                    "Hrany odpovídají. Potvrzením vznikne lepený spoj; "
                    "chlopeň nebo souvislý přehyb zvolíte ve vlastnostech."
                )
                buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            except Exception as exc:
                feedback.setText(str(exc))
                buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        angle.valueChanged.connect(update_preview)
        update_preview()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return self.run(
                lambda: self.controller.execute(
                    "Umístit a připojit protikus",
                    lambda p: p.place_and_connect_edges(*source, *target, angle_deg=angle.value()),
                )
            )
        self.connect_source = None
        return None

    def change_joint(self):
        if not self._updating and self.current_joint:
            self.run(
                lambda: self.controller.execute(
                    "Změnit šev",
                    lambda p: p.set_joint(
                        self.current_joint,
                        mode=self.joint_mode.currentData(),
                        receiving_part_id=self.selected_part,
                    ),
                )
            )

    def change_tab(self):
        if self._updating or not self.current_joint:
            return
        values = [
            self.tab_owner.currentData(),
            self.tab_width.value(),
            self.tab_taper.value(),
            self.tab_shape.currentData(),
        ]
        if values == self._shown.get("tab"):
            return
        self.run(
            lambda: self.controller.execute(
                "Upravit chlopeň",
                lambda p: p.set_tab(
                    self.current_joint,
                    owner=values[0],
                    width_mm=values[1],
                    taper=values[2],
                    shape=values[3],
                ),
            )
        )

    def show_partner(self):
        joint = self.project.joints.get(self.current_joint)
        if joint:
            target = (
                joint.surface_b if self.selected_surface == joint.surface_a else joint.surface_a
            )
            edge = joint.edge_b if target == joint.surface_b else joint.edge_a
            self.select_edge(target, edge)
            self.paper.focus_part(self.selected_part)
            self.viewport.focus_selection()

    def edit_placement(self):
        if self._updating or not self.selected_part:
            return
        values = [self.paper_x.value(), self.paper_y.value(), self.paper_angle.value()]
        old = self._shown.get("placement", values)
        page = self.page_choice.currentData()
        if values == old and page == self._raw.get("page"):
            return
        raw = self._raw["placement"]
        changed = [raw[i] if value == old[i] else value for i, value in enumerate(values)]
        self.move_part(
            self.selected_part,
            {"page_id": page, "x_mm": changed[0], "y_mm": changed[1], "rotation_deg": changed[2]},
        )

    def move_part(self, part_id, values):
        if not self._updating:
            self.run(
                lambda: self.controller.execute(
                    "Rozmístit díl", lambda p: p.set_placement(part_id, **values)
                )
            )

    def edit_locks(self):
        if not self._updating and self.selected_part:
            self.run(
                lambda: self.controller.execute(
                    "Změnit zámky",
                    lambda p: p.set_placement(
                        self.selected_part,
                        position_locked=self.position_lock.isChecked(),
                        rotation_locked=self.rotation_lock.isChecked(),
                    ),
                )
            )

    def change_front(self):
        if not self._updating and self.selected_part:
            self.run(
                lambda: self.controller.execute(
                    "Změnit potištěnou stranu",
                    lambda p: p.set_front_side(self.selected_part, self.front_side.currentData()),
                )
            )

    def change_anchor(self):
        if not self.selected_part:
            return
        part_id = self.selected_part
        dialog = QDialog(self)
        dialog.setWindowTitle("Kotva papírového dílu")
        layout = QFormLayout(dialog)
        choice = QComboBox()
        for sid in self.project.parts[part_id].surface_ids:
            choice.addItem(self.project.surfaces[sid].name, sid)
        preview = QLabel(
            "Volba kořenové plochy změní pevný bod a směr papírového dílu. "
            "Čísla umístění i zámky zůstanou; samotný díl se může na stránce posunout "
            "nebo otočit. Náhled ukazuje výsledek před potvrzením."
        )
        preview.setWordWrap(True)
        layout.addRow(preview)
        layout.addRow("Kořenová plocha", choice)
        preview_view = AuthorPaperView()
        preview_view.setMinimumHeight(350)
        preview_view.setInteractive(False)
        layout.addRow(preview_view)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        state = self.project.to_dict()

        def update_preview():
            try:
                clone = AuthorProject.from_dict(state)
                clone.set_anchor(part_id, choice.currentData())
                preview_view.set_project(clone)
                preview_view.focus_part(part_id)
                buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            except Exception as exc:
                preview.setText(str(exc))
                buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        choice.currentIndexChanged.connect(update_preview)
        update_preview()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.run(
                lambda: self.controller.execute(
                    "Změnit kotvu", lambda p: p.set_anchor(part_id, choice.currentData())
                )
            )

    def add_page(self):
        self.run(lambda: self.controller.execute("Přidat stránku", lambda p: p.add_page()))

    def delete_page(self):
        page = self.page_choice.currentData()
        if (
            page
            and QMessageBox.question(
                self, "Odebrat stránku", "Díly se přesunou na odkládací plochu. Odebrat stránku?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.run(
                lambda: self.controller.execute("Odebrat stránku", lambda p: p.delete_page(page))
            )

    def select_issue(self, item):
        selected = next(
            (
                i
                for i in self.project.validate_layout()
                if i.id == item.data(Qt.ItemDataRole.UserRole)
            ),
            None,
        )
        if selected and selected.part_ids:
            self.select_part(selected.part_ids[0])
            if selected.joint_id:
                kind = "attachment" if selected.joint_id in self.project.attachments else "joint"
                self.select_connector_relation((kind, selected.joint_id))
            self.paper.focus_part(selected.part_ids[0])
            self.paper.show_issue(selected)

    def acknowledge(self):
        item = self.issues.currentItem()
        if item:
            issue_id = item.data(Qt.ItemDataRole.UserRole)
            self.run(
                lambda: self.controller.execute(
                    "Přijmout konkrétní varování", lambda p: p.acknowledge(issue_id)
                )
            )

    def update_ack_button(self):
        item = self.issues.currentItem()
        selected = (
            next(
                (
                    i
                    for i in self.project.validate_layout()
                    if item and i.id == item.data(Qt.ItemDataRole.UserRole)
                ),
                None,
            )
            if self.project
            else None
        )
        self.ack_button.setEnabled(
            selected is not None and selected.severity == "warning" and not selected.acknowledged
        )

    def focus_selection(self):
        self.viewport.focus_selection()
        self.sketch.focus_surface()
        if self.selected_part:
            self.paper.focus_part(self.selected_part)

    def focus_all(self):
        self.viewport.focus_selection(all_surfaces=True)
        self.paper.fitInView(self.paper.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _confirm_replace(self):
        if not self._commit_pending_input():
            return False
        if self.sketch.drawing and self.sketch.points:
            answer = QMessageBox.question(
                self,
                "Rozpracovaný obrys",
                "Obrys ještě není dokončený. Zahodit rozpracované body?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Discard:
                return False
            self.sketch.cancel_outline()
        if not self.controller.dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Neuložený model",
            "Uložit změny před zavřením modelu?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        return bool(self.save_project()) if answer == QMessageBox.StandardButton.Save else True

    def new_project(self):
        if self._confirm_replace():
            self.selected_profile = None
            self.selected_surface = self.selected_edge = self.selected_vertex = (
                self.current_joint
            ) = None
            self.connect_source = None
            self.sketch.cancel_outline()
            self._frame_next = True
            self.controller.new()

    def open_project(self):
        if not self._confirm_replace():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Otevřít model",
            str(self.controller.file_path.parent) if self.controller.file_path else "",
            "Papercraft (*.apcraft *.json)",
        )
        if not path:
            return
        loaded = self.run(lambda: self.controller.open(path))
        if loaded is None:
            return
        if not isinstance(loaded, AuthorProject):
            self.run(lambda: self._show_legacy(loaded))
            return
        self.selected_surface = self.selected_edge = self.selected_vertex = self.current_joint = (
            None
        )
        self.connect_source = None
        self.selected_profile = None
        self._frame_next = True
        self.refresh()
        if self.controller.copy_source_path:
            QMessageBox.information(
                self, "Starší autorský projekt · úprava kopie",
                "Projekt je načtený do nové konstrukční verze. Původní soubor zůstane "
                "beze změny; uložení nabídne nový název kopie. Papírové díly před "
                "exportem přepočítejte a zkontrolujte.",
            )

    def _show_legacy(self, loaded):
        dialog = QDialog(self)
        dialog.setWindowTitle("Starší projekt · pouze prohlížení")
        dialog.resize(1000, 720)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel(
                "Originál zůstává beze změny. "
                "Tento starší formát se zde neupravuje ani nepřepisuje."
            )
        )
        raw = loaded.raw
        if isinstance(raw.get("scene"), list):
            from archpapercraft.project_io.project import Project
            from archpapercraft.ui.viewport_3d import Viewport3D

            legacy = Project.from_dict(raw)
            view = Viewport3D(legacy.scene)
            layout.addWidget(view)
            if legacy.scene.root.children:
                view.focus_on_node(legacy.scene.root.children[0])
        else:
            text = QPlainTextEdit(json.dumps(raw, ensure_ascii=False, indent=2))
            text.setReadOnly(True)
            layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def save_project(self, *, save_as=False):
        if not self._commit_pending_input():
            return False
        if self.sketch.drawing and self.sketch.points:
            QMessageBox.information(
                self,
                "Dokončete obrys",
                "Nejprve obrys dokončete klávesou Enter, nebo jej zrušte klávesou Esc. "
                "Rozpracované body zatím nejsou součástí modelu.",
            )
            return False
        path = self.controller.file_path
        if save_as or path is None:
            source = self.controller.copy_source_path
            default = str(path) if path else (
                str(source.with_name(source.stem + "-copy.apcraft")) if source else "model.apcraft"
            )
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "Uložit model",
                default,
                "Papercraft (*.apcraft)",
            )
            if not selected:
                return False
            path = Path(selected)
        return self.run(lambda: self.controller.save(path)) is not None

    def export_project(self):
        if not self._commit_pending_input():
            return
        if self.sketch.drawing and self.sketch.points:
            QMessageBox.information(
                self, "Dokončete obrys",
                "Nejprve obrys dokončete klávesou Enter, nebo jej zrušte klávesou Esc. "
                "Rozpracované body zatím nejsou součástí modelu ani exportu.",
            )
            return
        snapshot = self.run(self.project.snapshot)
        if snapshot is None:
            return
        if (
            QMessageBox.question(
                self,
                "Vektorový export",
                f"Exportovat {len(snapshot['pages'])} stránek "
                f"v měřítku 1:{1 / self.project.scale:g} "
                "jako editovatelné SVG a vektorové PDF?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            != QMessageBox.StandardButton.Ok
        ):
            return
        base = self.controller.file_path.parent if self.controller.file_path else Path.cwd()
        default = base / "export" if (base / "export").is_dir() else base
        target = QFileDialog.getExistingDirectory(
            self, "Vyberte složku pro SVG a PDF", str(default)
        )
        if not target:
            return
        progress = ExportProgressDialog(snapshot, target, self)
        progress.exec()
        if progress.cancelled:
            self.statusBar().showMessage(str(progress.error), 12000)
            return
        if progress.error is not None:
            def fail():
                raise progress.error
            self.run(fail)
            return
        result = progress.result_paths
        if result is not None:
            QMessageBox.information(
                self,
                "Export dokončen",
                ("Zrušení přišlo během dokončování; výstup byl již uložen.\n"
                 if progress.finished_during_cancel else "") + "Uloženo:\n"
                + "\n".join(Path(p).name for p in result)
                + "\n\nTiskněte 100 %, bez přizpůsobení stránce. Kalibrace má 100 mm.",
            )

    def _commit_pending_input(self):
        """Finish the visible numeric edit before save, snapshot, or replacement."""
        if self._committing_input:
            return True
        field = QApplication.focusWidget()
        while field is not None and field is not self and not isinstance(field, QAbstractSpinBox):
            field = field.parentWidget()
        if not isinstance(field, QAbstractSpinBox) or not self.isAncestorOf(field):
            return True
        if not field.hasAcceptableInput():
            QMessageBox.warning(
                self, "Zkontrolujte zadané číslo",
                "Zadaná hodnota není úplné platné číslo. Opravte ji před pokračováním.",
            )
            field.setFocus()
            return False
        errors_before = self._command_errors
        self._committing_input = True
        try:
            field.interpretText()
            field.editingFinished.emit()
            # Native dialogs must not commit another edit after a snapshot was taken.
            field.clearFocus()
        finally:
            self._committing_input = False
        return self._command_errors == errors_before

    def closeEvent(self, event):
        if self._confirm_replace():
            event.accept()
        else:
            event.ignore()
