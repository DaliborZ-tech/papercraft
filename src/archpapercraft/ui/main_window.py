"""Hlavní okno aplikace — sestavuje viewport, strom objektů, vlastnosti a panel papercraftu."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from archpapercraft.commands.command_stack import CommandStack
from archpapercraft.project_io.project import Project
from archpapercraft.scene_graph.scene import Scene
from archpapercraft.ui.object_tree import ObjectTreeWidget
from archpapercraft.ui.papercraft_panel import PapercraftPanel
from archpapercraft.ui.properties_panel import PropertiesPanel
from archpapercraft.ui.viewport_3d import Viewport3D


class MainWindow(QMainWindow):
    """Hlavní okno aplikace ArchPapercraft Studio."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ArchPapercraft Studio")
        self.resize(1400, 900)

        # ── data ───────────────────────────────────────────────────────
        self.project = Project()
        self.command_stack = CommandStack(on_change=self._on_undo_redo_change)

        # ── centrální viewport ─────────────────────────────────────────
        self.viewport = Viewport3D(scene=self.project.scene)
        self.setCentralWidget(self.viewport)

        # ── dock: strom objektů ────────────────────────────────────────
        self.tree_dock = QDockWidget("Objekty", self)
        self.object_tree = ObjectTreeWidget(scene=self.project.scene)
        self.tree_dock.setWidget(self.object_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tree_dock)

        # ── dock: vlastnosti ───────────────────────────────────────────
        self.props_dock = QDockWidget("Vlastnosti", self)
        self.properties = PropertiesPanel()
        self.props_dock.setWidget(self.properties)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.props_dock)

        # ── dock: papercraft ───────────────────────────────────────────
        self.paper_dock = QDockWidget("Vystřihováníka", self)
        self.papercraft = PapercraftPanel(project=self.project)
        self.paper_dock.setWidget(self.papercraft)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.paper_dock)

        # ── menu ───────────────────────────────────────────────────────
        self._build_menus()

        # ── panel nástrojů ─────────────────────────────────────────────
        self._build_toolbar()

        # ── stavový řádek ──────────────────────────────────────────────
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Připraven")

        # ── automatické ukládání (každé 2 minuty) ─────────────────────
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(120_000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    # ── menu ───────────────────────────────────────────────────────────

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # ── Soubor ────────────────────────────────────────────────────
        file_menu = mb.addMenu("&Soubor")

        new_act = QAction("&Nový projekt", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._new_project)
        file_menu.addAction(new_act)

        open_act = QAction("&Otevřít…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._open_project)
        file_menu.addAction(open_act)

        save_act = QAction("&Uložit", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._save_project)
        file_menu.addAction(save_act)

        save_as_act = QAction("Uložit &jako…", self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        exit_act = QAction("U&končit", self)
        exit_act.setShortcut(QKeySequence("Alt+F4"))
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # ── Úpravy ───────────────────────────────────────────────────
        edit_menu = mb.addMenu("Ú&pravy")

        self._undo_act = QAction("&Zpět", self)
        self._undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_act.setEnabled(False)
        self._undo_act.triggered.connect(self._undo)
        edit_menu.addAction(self._undo_act)

        self._redo_act = QAction("Z&novu", self)
        self._redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_act.setEnabled(False)
        self._redo_act.triggered.connect(self._redo)
        edit_menu.addAction(self._redo_act)

        edit_menu.addSeparator()

        prefs_act = QAction("&Předvolby…", self)
        prefs_act.setShortcut(QKeySequence("Ctrl+,"))
        prefs_act.triggered.connect(self._show_preferences)
        edit_menu.addAction(prefs_act)

        # ── Přidat ───────────────────────────────────────────────────
        add_menu = mb.addMenu("Př&idat")

        # Primitiva
        prim_menu = add_menu.addMenu("Primitiva")
        for label, ntype in [
            ("Kvádr", "PRIMITIVE_BOX"),
            ("Válec", "PRIMITIVE_CYLINDER"),
            ("Kužel", "PRIMITIVE_CONE"),
            ("Koule", "PRIMITIVE_SPHERE"),
            ("Torus", "PRIMITIVE_TORUS"),
        ]:
            act = QAction(label, self)
            act.setData(ntype)
            act.triggered.connect(self._add_object)
            prim_menu.addAction(act)

        # Architektonické objekty
        arch_menu = add_menu.addMenu("Architektura")
        for label, ntype in [
            ("Zeď", "WALL"),
            ("Otvor (okno/dveře)", "OPENING"),
            ("Střecha (sedlová)", "ROOF"),
            ("Gotické okno", "GOTHIC_WINDOW"),
            ("Cibulovitá kopule", "ONION_DOME"),
            ("Podlaží / deska", "FLOOR_SLAB"),
            ("Věž", "TOWER"),
            ("Opěrný pilíř", "BUTTRESS"),
        ]:
            act = QAction(label, self)
            act.setData(ntype)
            act.triggered.connect(self._add_object)
            arch_menu.addAction(act)

        # ── Zobrazení ────────────────────────────────────────────────
        view_menu = mb.addMenu("&Zobrazení")

        for label, preset in [
            ("Shora (Numpad 7)", "TOP"),
            ("Zepředu (Numpad 1)", "FRONT"),
            ("Z boku (Numpad 3)", "SIDE"),
            ("Perspektiva (Numpad 5)", "PERSPECTIVE"),
        ]:
            act = QAction(label, self)
            act.setData(preset)
            act.triggered.connect(self._set_view_preset)
            view_menu.addAction(act)

        view_menu.addSeparator()

        wireframe_act = QAction("Drátový model", self)
        wireframe_act.setCheckable(True)
        wireframe_act.triggered.connect(self._toggle_wireframe)
        view_menu.addAction(wireframe_act)

        grid_act = QAction("Mřížka", self)
        grid_act.setCheckable(True)
        grid_act.setChecked(True)
        grid_act.triggered.connect(self._toggle_grid)
        view_menu.addAction(grid_act)

        # ── Nápověda ─────────────────────────────────────────────────
        help_menu = mb.addMenu("&Nápověda")
        about_act = QAction("&O programu", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Hlavní", self)
        self.addToolBar(tb)

        for label, slot in [
            ("Nový", self._new_project),
            ("Otevřít", self._open_project),
            ("Uložit", self._save_project),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()

        undo_tb = QAction("Zpět", self)
        undo_tb.triggered.connect(self._undo)
        tb.addAction(undo_tb)

        redo_tb = QAction("Znovu", self)
        redo_tb.triggered.connect(self._redo)
        tb.addAction(redo_tb)

    # ── sloty ──────────────────────────────────────────────────────────

    def _new_project(self) -> None:
        self.project = Project()
        self.command_stack.clear()
        self._refresh_all()
        self.statusBar().showMessage("Nový projekt vytvořen")

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Otevřít projekt", "", "ArchPapercraft (*.apcraft);;Vše (*)"
        )
        if path:
            try:
                self.project = Project.load(path)
                self.command_stack.clear()
                self._refresh_all()
                self.statusBar().showMessage(f"Otevřeno: {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Chyba", f"Nepodařilo se otevřít:\n{exc}")

    def _save_project(self) -> None:
        if self.project.file_path is None:
            self._save_project_as()
        else:
            self.project.save()
            self.statusBar().showMessage(f"Uloženo: {self.project.file_path}")

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Uložit jako", "", "ArchPapercraft (*.apcraft)"
        )
        if path:
            self.project.save(path)
            self.statusBar().showMessage(f"Uloženo: {path}")

    def _add_object(self) -> None:
        act = self.sender()
        if act is None:
            return
        ntype_name = act.data()
        from archpapercraft.scene_graph.node import NodeType

        ntype = NodeType[ntype_name]
        name = ntype_name.replace("PRIMITIVE_", "").replace("_", " ").title()
        self.project.scene.add_node(name, ntype)
        self.project.scene.rebuild_meshes()
        self._refresh_all()
        self.statusBar().showMessage(f"Přidáno: {name}")

    def _undo(self) -> None:
        desc = self.command_stack.undo()
        if desc:
            self._refresh_all()
            self.statusBar().showMessage(f"Zpět: {desc}")

    def _redo(self) -> None:
        desc = self.command_stack.redo()
        if desc:
            self._refresh_all()
            self.statusBar().showMessage(f"Znovu: {desc}")

    def _on_undo_redo_change(self) -> None:
        """Callback z CommandStack — aktualizuje stav menu."""
        self._undo_act.setEnabled(self.command_stack.can_undo)
        self._redo_act.setEnabled(self.command_stack.can_redo)

    def _set_view_preset(self) -> None:
        act = self.sender()
        if act is None:
            return
        preset = act.data()
        self.viewport.set_view_preset(preset)
        self.statusBar().showMessage(f"Pohled: {preset}")

    def _toggle_wireframe(self) -> None:
        self.viewport.toggle_wireframe()

    def _toggle_grid(self) -> None:
        self.viewport.toggle_grid()

    def _show_preferences(self) -> None:
        """Otevře dialog předvoleb."""
        QMessageBox.information(
            self, "Předvolby",
            "Dialog předvoleb bude implementován v další verzi.\n"
            "Nastavení se ukládá do ~/.archpapercraft/settings.json",
        )

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "O programu ArchPapercraft Studio",
            "ArchPapercraft Studio v0.2.0\n\n"
            "Architektura-first 3D modelář\ns exportem papírových vystřihovánek.\n\n"
            "PDF · SVG · DXF · PNG",
        )

    def _autosave(self) -> None:
        result = self.project.autosave()
        if result:
            self.statusBar().showMessage(f"Autouloženo: {result}", 3000)

    def _refresh_all(self) -> None:
        """Obnoví všechny sub-widgety po změnách projektu/scény."""
        self.viewport.set_scene(self.project.scene)
        self.object_tree.set_scene(self.project.scene)
        self.papercraft.set_project(self.project)
