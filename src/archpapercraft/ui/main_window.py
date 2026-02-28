"""Main application window — assembles viewport, tree, properties, and papercraft panels."""

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

from archpapercraft.project_io.project import Project
from archpapercraft.scene_graph.scene import Scene
from archpapercraft.ui.object_tree import ObjectTreeWidget
from archpapercraft.ui.papercraft_panel import PapercraftPanel
from archpapercraft.ui.properties_panel import PropertiesPanel
from archpapercraft.ui.viewport_3d import Viewport3D


class MainWindow(QMainWindow):
    """Top-level application window for ArchPapercraft Studio."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ArchPapercraft Studio")
        self.resize(1400, 900)

        # ── data ───────────────────────────────────────────────────────
        self.project = Project()

        # ── central viewport ───────────────────────────────────────────
        self.viewport = Viewport3D(scene=self.project.scene)
        self.setCentralWidget(self.viewport)

        # ── dock: object tree ──────────────────────────────────────────
        self.tree_dock = QDockWidget("Objects", self)
        self.object_tree = ObjectTreeWidget(scene=self.project.scene)
        self.tree_dock.setWidget(self.object_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tree_dock)

        # ── dock: properties ───────────────────────────────────────────
        self.props_dock = QDockWidget("Properties", self)
        self.properties = PropertiesPanel()
        self.props_dock.setWidget(self.properties)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.props_dock)

        # ── dock: papercraft ───────────────────────────────────────────
        self.paper_dock = QDockWidget("Papercraft", self)
        self.papercraft = PapercraftPanel(project=self.project)
        self.paper_dock.setWidget(self.papercraft)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.paper_dock)

        # ── menus ──────────────────────────────────────────────────────
        self._build_menus()

        # ── toolbar ────────────────────────────────────────────────────
        self._build_toolbar()

        # ── status bar ─────────────────────────────────────────────────
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready")

        # ── autosave timer (every 2 minutes) ───────────────────────────
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(120_000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    # ── menus ──────────────────────────────────────────────────────────

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")

        new_act = QAction("&New Project", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._new_project)
        file_menu.addAction(new_act)

        open_act = QAction("&Open…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._open_project)
        file_menu.addAction(open_act)

        save_act = QAction("&Save", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._save_project)
        file_menu.addAction(save_act)

        save_as_act = QAction("Save &As…", self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence("Alt+F4"))
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Add
        add_menu = mb.addMenu("&Add")
        for label, ntype in [
            ("Box", "PRIMITIVE_BOX"),
            ("Cylinder", "PRIMITIVE_CYLINDER"),
            ("Cone", "PRIMITIVE_CONE"),
            ("Wall", "WALL"),
            ("Opening", "OPENING"),
            ("Roof (gabled)", "ROOF"),
            ("Gothic Window", "GOTHIC_WINDOW"),
            ("Onion Dome", "ONION_DOME"),
        ]:
            act = QAction(label, self)
            act.setData(ntype)
            act.triggered.connect(self._add_object)
            add_menu.addAction(act)

        # Help
        help_menu = mb.addMenu("&Help")
        about_act = QAction("&About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        self.addToolBar(tb)

        for label in ["New", "Open", "Save"]:
            act = QAction(label, self)
            if label == "New":
                act.triggered.connect(self._new_project)
            elif label == "Open":
                act.triggered.connect(self._open_project)
            elif label == "Save":
                act.triggered.connect(self._save_project)
            tb.addAction(act)

    # ── slots ──────────────────────────────────────────────────────────

    def _new_project(self) -> None:
        self.project = Project()
        self._refresh_all()
        self.statusBar().showMessage("New project created")

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "ArchPapercraft (*.apcraft);;All (*)"
        )
        if path:
            try:
                self.project = Project.load(path)
                self._refresh_all()
                self.statusBar().showMessage(f"Opened: {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to open project:\n{exc}")

    def _save_project(self) -> None:
        if self.project.file_path is None:
            self._save_project_as()
        else:
            self.project.save()
            self.statusBar().showMessage(f"Saved: {self.project.file_path}")

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "ArchPapercraft (*.apcraft)"
        )
        if path:
            self.project.save(path)
            self.statusBar().showMessage(f"Saved: {path}")

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
        self.statusBar().showMessage(f"Added {name}")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About ArchPapercraft Studio",
            "ArchPapercraft Studio v0.1.0\n\n"
            "Architecture-first 3D modeler\nwith papercraft export.",
        )

    def _autosave(self) -> None:
        result = self.project.autosave()
        if result:
            self.statusBar().showMessage(f"Autosaved: {result}", 3000)

    def _refresh_all(self) -> None:
        """Refresh all sub-widgets after project/scene changes."""
        self.viewport.set_scene(self.project.scene)
        self.object_tree.set_scene(self.project.scene)
        self.papercraft.set_project(self.project)
