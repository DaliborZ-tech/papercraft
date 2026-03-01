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

from archpapercraft.commands.command_stack import (
    AddNodeCommand,
    CommandStack,
    RemoveNodeCommand,
    SetParameterCommand,
    SetTransformCommand,
)
from archpapercraft.preferences.settings import Preferences
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
        self._prefs = Preferences.load()
        self.command_stack = CommandStack(
            max_depth=self._prefs.general.max_undo_depth,
            on_change=self._on_undo_redo_change,
        )
        self._selected_node = None

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

        # ── propojení signálů ──────────────────────────────────────────
        self.object_tree.node_selected.connect(self._on_node_selected)
        self.properties.param_changed.connect(self._on_param_changed)
        self.properties.param_value_changed.connect(self._on_param_value_changed)
        self.properties.transform_changed.connect(self._on_transform_changed)

        # ── aplikace nastavení ─────────────────────────────────────────
        self._apply_preferences()

        # ── automatické ukládání ───────────────────────────────────────
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(self._prefs.general.autosave_interval_sec * 1000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    # ── menu ───────────────────────────────────────────────────────────

    def _build_menus(self) -> None:
        mb = self.menuBar()
        self._shortcut_actions: dict[str, QAction] = {}

        # ── Soubor ────────────────────────────────────────────────────
        file_menu = mb.addMenu("&Soubor")

        new_act = QAction("&Nový projekt", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._new_project)
        file_menu.addAction(new_act)
        self._shortcut_actions["new_project"] = new_act

        open_act = QAction("&Otevřít…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._open_project)
        file_menu.addAction(open_act)
        self._shortcut_actions["open_project"] = open_act

        save_act = QAction("&Uložit", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._save_project)
        file_menu.addAction(save_act)
        self._shortcut_actions["save_project"] = save_act

        save_as_act = QAction("Uložit &jako…", self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_act)
        self._shortcut_actions["save_as"] = save_as_act

        file_menu.addSeparator()

        export_act = QAction("&Export…", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self._export_default)
        file_menu.addAction(export_act)
        self._shortcut_actions["export"] = export_act

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
        self._shortcut_actions["undo"] = self._undo_act

        self._redo_act = QAction("Z&novu", self)
        self._redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_act.setEnabled(False)
        self._redo_act.triggered.connect(self._redo)
        edit_menu.addAction(self._redo_act)
        self._shortcut_actions["redo"] = self._redo_act

        edit_menu.addSeparator()

        delete_act = QAction("&Smazat", self)
        delete_act.setShortcut(QKeySequence("Delete"))
        delete_act.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_act)
        self._shortcut_actions["delete"] = delete_act

        dup_act = QAction("D&uplikovat", self)
        dup_act.setShortcut(QKeySequence("Ctrl+D"))
        dup_act.triggered.connect(self._duplicate_selected)
        edit_menu.addAction(dup_act)
        self._shortcut_actions["duplicate"] = dup_act

        edit_menu.addSeparator()

        select_all_act = QAction("Vybrat vš&e", self)
        select_all_act.setShortcut(QKeySequence("Ctrl+A"))
        select_all_act.triggered.connect(self._select_all)
        edit_menu.addAction(select_all_act)
        self._shortcut_actions["select_all"] = select_all_act

        focus_act = QAction("Zaměřit &výběr", self)
        focus_act.setShortcut(QKeySequence("Numpad ."))
        focus_act.triggered.connect(self._focus_selection)
        edit_menu.addAction(focus_act)
        self._shortcut_actions["focus_selection"] = focus_act

        snap_act = QAction("Přichytávání", self)
        snap_act.setCheckable(True)
        snap_act.setChecked(self._prefs.snap.enabled)
        snap_act.setShortcut(QKeySequence("S"))
        snap_act.triggered.connect(self._toggle_snap)
        edit_menu.addAction(snap_act)
        self._shortcut_actions["toggle_snap"] = snap_act
        self._snap_act = snap_act

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

        _view_shortcut_keys = {
            "TOP": "view_top",
            "FRONT": "view_front",
            "SIDE": "view_side",
            "PERSPECTIVE": "view_perspective",
        }
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
            skey = _view_shortcut_keys.get(preset)
            if skey:
                self._shortcut_actions[skey] = act

        view_menu.addSeparator()

        wireframe_act = QAction("Drátový model", self)
        wireframe_act.setCheckable(True)
        wireframe_act.setChecked(True)
        wireframe_act.triggered.connect(self._toggle_wireframe)
        view_menu.addAction(wireframe_act)

        grid_act = QAction("Mřížka", self)
        grid_act.setCheckable(True)
        grid_act.setChecked(True)
        grid_act.triggered.connect(self._toggle_grid)
        view_menu.addAction(grid_act)
        self._shortcut_actions["toggle_grid"] = grid_act

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
        from archpapercraft.ui.wizard import ProjectWizard

        wizard = ProjectWizard(self)
        if wizard.exec():
            settings = wizard.get_settings()
            self.project = Project()
            self.project.settings = settings
            self.command_stack.clear()
            self._selected_node = None
            self._refresh_all()
            self.statusBar().showMessage(f"Nový projekt: {settings.name}")

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
            self.command_stack.mark_saved()
            self.statusBar().showMessage(f"Uloženo: {self.project.file_path}")

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Uložit jako", "", "ArchPapercraft (*.apcraft)"
        )
        if path:
            self.project.save(path)
            self.command_stack.mark_saved()
            self.statusBar().showMessage(f"Uloženo: {path}")

    def _add_object(self) -> None:
        act = self.sender()
        if act is None:
            return
        ntype_name = act.data()
        from archpapercraft.scene_graph.node import NodeType

        ntype = NodeType[ntype_name]
        name = ntype_name.replace("PRIMITIVE_", "").replace("_", " ").title()
        cmd = AddNodeCommand(self.project.scene, name, ntype)
        self.command_stack.execute(cmd)
        self._refresh_all()
        self.statusBar().showMessage(f"Přidáno: {name}")

    def _undo(self) -> None:
        desc = self.command_stack.undo_description
        if self.command_stack.undo():
            self._refresh_all()
            self.statusBar().showMessage(f"Zpět: {desc}")

    def _redo(self) -> None:
        desc = self.command_stack.redo_description
        if self.command_stack.redo():
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

    # ── výběr a editace uzlů ──────────────────────────────────────────

    def _on_node_selected(self, node_id: str) -> None:
        """Strom objektů emitoval node_selected — zobraz ve vlastnostech a zvýrazni."""
        node = self.project.scene.find_node(node_id)
        self._selected_node = node
        self.properties.set_node(node)
        self.viewport.set_selected_node(node)
        if node:
            self.statusBar().showMessage(f"Vybráno: {node.name}")

    def _on_param_changed(self) -> None:
        """Properties panel reportuje změnu parametru — rebuild + refresh."""
        self.project.scene.rebuild_meshes()
        self.viewport.update()

    def _on_param_value_changed(self, key: str, old_value: float) -> None:
        """Parametr změněn v properties panelu — uloží do undo stacku.

        ``old_value`` je hodnota PŘED změnou (z properties panelu).
        """
        if self._selected_node is None:
            return
        new_value = self._selected_node.parameters.get(key)
        cmd = SetParameterCommand(self._selected_node, key, new_value)
        cmd._old_value = old_value  # přepsat — uzel už má novou hodnotu
        self.command_stack.push_executed(cmd)

    def _on_transform_changed(self) -> None:
        """Transformace změněna v properties panelu — ulož snapshot pro undo."""
        if self._selected_node is None:
            return
        # Příkaz se vytvoří s aktuální (novou) transformací;
        # _old se nastaví ručně ze snapshot uloženého před změnou.
        cmd = SetTransformCommand(self._selected_node, self._selected_node.transform)
        snap = self.properties._last_transform_snapshot
        if snap:
            pos, rot = snap
            cmd._old.position[:] = pos
            cmd._old.rotation[:] = rot
        self.command_stack.push_executed(cmd)
        # Aktualizovat snapshot pro příští změnu
        self.properties._last_transform_snapshot = (
            tuple(self._selected_node.transform.position.tolist()),
            tuple(self._selected_node.transform.rotation.tolist()),
        )

    def _delete_selected(self) -> None:
        """Smaž vybraný uzel ze scény (s Undo podporou)."""
        if self._selected_node is None:
            return
        name = self._selected_node.name
        cmd = RemoveNodeCommand(self.project.scene, self._selected_node)
        self.command_stack.execute(cmd)
        self._selected_node = None
        self.properties.set_node(None)
        self.viewport.set_selected_node(None)
        self._refresh_all()
        self.statusBar().showMessage(f"Smazáno: {name}")

    def _duplicate_selected(self) -> None:
        """Duplikuj vybraný uzel (vytvoří kopii se stejnými parametry, s Undo)."""
        if self._selected_node is None:
            return
        src = self._selected_node
        from archpapercraft.scene_graph.node import NodeType

        cmd = AddNodeCommand(
            self.project.scene,
            f"{src.name} (kopie)",
            src.node_type,
            **dict(src.parameters),
        )
        self.command_stack.execute(cmd)
        # Kopíruj transformaci s mírným offsetem
        if cmd._node is not None:
            cmd._node.transform.position[:] = src.transform.position
            cmd._node.transform.rotation[:] = src.transform.rotation
            cmd._node.transform.position[0] += 0.5
        self.project.scene.rebuild_meshes()
        self._refresh_all()
        self.statusBar().showMessage(f"Duplikováno: {src.name} (kopie)")

    def _select_all(self) -> None:
        """Select all nodes in the scene tree."""
        nodes = list(self.project.scene.root.children)
        if nodes:
            # Select the first node and show status with count
            self._on_node_selected(nodes[0].node_id)
            self.object_tree.select_all()
            self.statusBar().showMessage(f"Vybráno {len(nodes)} objektů")

    def _focus_selection(self) -> None:
        """Frame the selected node in the viewport camera."""
        if self._selected_node is None:
            self.statusBar().showMessage("Žádný výběr pro zaměření")
            return
        self.viewport.focus_on_node(self._selected_node)
        self.statusBar().showMessage(f"Zaměřeno na: {self._selected_node.name}")

    def _toggle_snap(self) -> None:
        """Toggle snapping on/off."""
        self._prefs.snap.enabled = not self._prefs.snap.enabled
        if hasattr(self, "_snap_act"):
            self._snap_act.setChecked(self._prefs.snap.enabled)
        state = "zapnuto" if self._prefs.snap.enabled else "vypnuto"
        self.statusBar().showMessage(f"Přichytávání: {state}")

    def _show_preferences(self) -> None:
        """Otevře dialog předvoleb."""
        from archpapercraft.ui.preferences_dialog import PreferencesDialog

        dlg = PreferencesDialog(self._prefs, parent=self)
        if dlg.exec():
            self._apply_preferences()
            self.statusBar().showMessage("Předvolby uloženy a aplikovány")

    def _apply_preferences(self) -> None:
        """Aplikuje aktuální nastavení na běžící komponenty."""
        prefs = self._prefs

        # Autosave interval
        if hasattr(self, "_autosave_timer"):
            self._autosave_timer.setInterval(prefs.general.autosave_interval_sec * 1000)

        # Undo depth
        self.command_stack._max_depth = prefs.general.max_undo_depth

        # Theme (dark / light / system)
        self._apply_theme(prefs.general.theme)

        # Viewport nastavení
        self.viewport.apply_preferences(prefs.viewport)

        # Klávesové zkratky
        self._apply_shortcuts()

    def _apply_theme(self, theme: str) -> None:
        """Apply dark/light/system theme via QPalette on the Fusion style."""
        from PySide6.QtGui import QColor, QPalette
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return

        if theme == "dark":
            p = QPalette()
            p.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            p.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
            p.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
            p.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
            p.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
            p.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
            p.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
            p.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            p.setColor(QPalette.ColorRole.HighlightedText, QColor(240, 240, 240))
            p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
            p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
            app.setPalette(p)
        elif theme == "light":
            p = QPalette()
            p.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
            p.setColor(QPalette.ColorRole.WindowText, QColor(30, 30, 30))
            p.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
            p.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
            p.setColor(QPalette.ColorRole.Text, QColor(30, 30, 30))
            p.setColor(QPalette.ColorRole.Button, QColor(230, 230, 230))
            p.setColor(QPalette.ColorRole.ButtonText, QColor(30, 30, 30))
            p.setColor(QPalette.ColorRole.Highlight, QColor(51, 153, 255))
            p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            app.setPalette(p)
        else:
            # system — reset to default palette
            app.setPalette(app.style().standardPalette())

    def _apply_shortcuts(self) -> None:
        """Aplikuje klávesové zkratky z nastavení na akce v menu."""
        sc = self._prefs.shortcuts
        mapping = {
            "new_project": sc.new_project,
            "open_project": sc.open_project,
            "save_project": sc.save_project,
            "save_as": sc.save_as,
            "undo": sc.undo,
            "redo": sc.redo,
            "delete": sc.delete,
            "duplicate": sc.duplicate,
            "select_all": sc.select_all,
            "focus_selection": sc.focus_selection,
            "toggle_snap": sc.toggle_snap,
            "toggle_grid": sc.toggle_grid,
            "view_top": sc.view_top,
            "view_front": sc.view_front,
            "view_side": sc.view_side,
            "view_perspective": sc.view_perspective,
            "export": sc.export,
        }
        for key, shortcut in mapping.items():
            act = self._shortcut_actions.get(key)
            if act and shortcut:
                act.setShortcut(QKeySequence(shortcut))

    def _export_default(self) -> None:
        """Export v preferovaném formátu z panelu papercraftu."""
        fmt = self._prefs.export.default_format
        self.papercraft._on_export(fmt)

    # ── closeEvent ─────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Kontrola neuložených změn při zavírání okna."""
        if self.command_stack.is_modified:
            reply = QMessageBox.question(
                self,
                "Neuložené změny",
                "Projekt obsahuje neuložené změny.\nChcete je uložit před zavřením?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_project()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

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
