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
    QVBoxLayout,
    QWidget,
)

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter.author_export import export_all
from archpapercraft.ui.author_attachment import AttachmentDialog, GlueRegionDialog
from archpapercraft.ui.author_connectors import ConnectorPanel
from archpapercraft.ui.author_paper import AuthorPaperView
from archpapercraft.ui.author_sketch import AuthorSketch
from archpapercraft.ui.author_viewport import AuthorViewport


class AuthorMainWindow(QMainWindow):
    def __init__(self, parent=None, *, settings=None):
        super().__init__(parent)
        self.resize(1660, 960)
        self.settings = settings or QSettings("ArchPapercraft", "Authoring")
        self.selected_surface = None
        self.selected_profile = None
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
        self.sketch = AuthorSketch()
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
        self.sketch.vertex_selected.connect(self.select_vertex)
        self.sketch.vertex_moved.connect(self.move_vertex)
        self.sketch.status.connect(self.statusBar().showMessage)
        self.sketch.draft_changed.connect(self.update_guidance)
        self.viewport.surface_selected.connect(self.select_surface)
        self.viewport.edge_selected.connect(self.select_edge)
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
        edit = self.menuBar().addMenu("Úpravy")
        edit.addAction(self._action("undo", "Vrátit změnu", self.undo_command, "Ctrl+Z"))
        edit.addAction(self._action("redo", "Zopakovat změnu", self.redo_command, "Ctrl+Y"))
        construct = self.menuBar().addMenu("Vytvořit")
        construct.addAction(
            self._action("draw", "Nakreslit vlastní díl", self.start_outline, "Ctrl+L")
        )
        construct.addAction(self._action("rectangle", "Obdélník z rozměrů…", self.create_rectangle))
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
            profile is not None and self.selected_surface is None and len(profile.vertices) >= 3
        )
        self.actions["finish"].setEnabled(self.sketch.drawing and len(self.sketch.points) >= 3)
        self.actions["undo"].setEnabled(
            self.controller.can_undo or bool(self.sketch.drawing and self.sketch.points)
        )
        self.actions["redo"].setEnabled(self.controller.can_redo and not self.sketch.drawing)
        if self.connect_source:
            text = "Spojení: vyberte druhou hranu v prostoru nebo na papíře. Esc operaci zruší."
        elif self.sketch.drawing:
            text = (
                "Kreslení: klikněte na body, Enter uzavře obrys a vytvoří plochu. "
                "Backspace vrátí bod, Esc zruší návrh."
            )
        elif profile is not None and self.selected_surface is None:
            text = (
                "Vybraný profil ještě není tiskový díl. V nabídce Vytvořit přidejte body, "
                "nebo profil uzavřete a vytvořte plochu."
            )
        elif not self.project or not self.project.surfaces:
            text = (
                "Začněte tlačítkem Nakreslit vlastní díl, nebo zadejte rozměry obdélníku. "
                "Plocha se ukáže v prostoru i na papíře."
            )
        elif self.selected_part and self.project.parts[self.selected_part].stale:
            text = (
                "Konstrukce se změnila. Papírový díl je neaktuální; "
                "přepočítejte jej (Ctrl+R) a zkontrolujte stránky."
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
            for sid, surface in self.project.surfaces.items():
                part = self.project.parts[surface.part_id]
                item = QTreeWidgetItem(
                    [f"{surface.name} · {part.name}" + (" · přepočítat" if part.stale else "")]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, sid)
                self.tree.addTopLevelItem(item)
                if sid == self.selected_surface:
                    self.tree.setCurrentItem(item)
            used_profiles = {
                pid
                for surface in self.project.surfaces.values()
                for pid in [surface.profile_id, *surface.hole_profile_ids]
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
            self.viewport.set_project(self.project, frame=frame_views)
            self._frame_next = False
            self.sketch.set_project(self.project, self.selected_surface, self.selected_profile)
            self.paper.set_project(self.project, frame=frame_views)
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
            self.actions["hole"].setEnabled(self.selected_surface is not None)
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
            for profile_id in [profile.id, *(surface.hole_profile_ids if surface else [])]:
                profile = self.project.profiles[profile_id]
                for index, vertex in enumerate(profile.vertices):
                    self.vertex_choice.addItem(
                        (
                            f"{'Otvor ' if surface and profile_id != surface.profile_id else ''}"
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
            for index, edge in enumerate(self.project.world_geometry(surface.id)["boundary"]):
                self.edge_choice.addItem(f"Okraj {index + 1}", edge["id"])
        self.edge_choice.setCurrentIndex(
            self.edge_choice.findData(self.selected_edge[1]) if self.selected_edge else -1
        )
        self.connect_button.setEnabled(self.selected_edge is not None)
        can_attach = self.selected_edge is not None and len(self.project.surfaces) > 1
        self.attach_inside_button.setEnabled(can_attach)
        self.actions["attach_inside"].setEnabled(can_attach)
        can_glue = self.selected_surface is not None and len(self.project.surfaces) > 1
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
        placement = self.project.placements.get(self.selected_part)
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
        self.position_lock.setEnabled(part is not None)
        self.rotation_lock.setEnabled(part is not None)
        self.front_side.setCurrentIndex(self.front_side.findData(part.front_side) if part else 0)
        self.front_side.setEnabled(part is not None)
        self.anchor_button.setEnabled(part is not None)
        self._shown["placement"] = [
            f.value() for f in (self.paper_x, self.paper_y, self.paper_angle)
        ]
        self._raw["placement"] = raw
        self._raw["page"] = placement.page_id if placement else None
        self.connectors_panel.refresh()

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
        self.paper.select(self.selected_part, self.selected_edge)

    def select_surface(self, surface_id):
        if not surface_id:
            self.clear_selection()
            return
        if self._updating or surface_id not in self.project.surfaces:
            return
        self.selected_surface = surface_id
        self.selected_profile = self.project.surfaces[surface_id].profile_id
        self.selected_vertex = None
        if self.selected_edge and self.selected_edge[0] != surface_id:
            self.selected_edge = None
        self.sketch.select_surface(surface_id)
        self._sync_selection()

    def _sync_selection(self):
        self._updating = True
        try:
            for index in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(index)
                if item.data(0, Qt.ItemDataRole.UserRole) == self.selected_surface:
                    self.tree.setCurrentItem(item)
                elif item.data(0, Qt.ItemDataRole.UserRole) == ("profile", self.selected_profile):
                    self.tree.setCurrentItem(item)
            self._populate_properties()
            self._highlight()
            self.actions["hole"].setEnabled(self.selected_surface is not None)
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
        self.selected_vertex = self.current_joint = None
        self._updating = True
        try:
            self.tree.clearSelection()
            self.tree.setCurrentItem(None)
            self.sketch.set_project(self.project)
        finally:
            self._updating = False
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
            else:
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
        self.selected_surface = self.selected_edge = self.selected_vertex = self.current_joint = (
            None
        )
        self.selected_profile = profile_id
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
        if self.selected_surface:
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
            self.sketch.points.pop()
            self.sketch.redraw()
            self.update_guidance()
            return
        self.controller.undo()

    def redo_command(self):
        if self.sketch.drawing or self._cancel_gesture():
            return
        self.controller.redo()

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
        result = self.run(lambda: export_all(snapshot, target))
        if result is not None:
            QMessageBox.information(
                self,
                "Export dokončen",
                "Uloženo:\n"
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
