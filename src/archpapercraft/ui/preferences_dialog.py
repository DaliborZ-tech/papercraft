"""Dialog předvoleb — edituje všechny kategorie nastavení aplikace."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.preferences.settings import (
    ExportSettings,
    GeneralSettings,
    KeyboardShortcuts,
    Preferences,
    SnapPreferences,
    ViewportSettings,
)


class PreferencesDialog(QDialog):
    """Dialog předvoleb (Ctrl+,) — záložkový layout."""

    def __init__(self, prefs: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Předvolby")
        self.setMinimumSize(520, 480)
        self._prefs = prefs

        layout = QVBoxLayout(self)

        # ── záložky ────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_general_tab()
        self._build_viewport_tab()
        self._build_snap_tab()
        self._build_export_tab()
        self._build_shortcuts_tab()

        # ── tlačítka ───────────────────────────────────────────────────
        btn_box = QDialogButtonBox()
        btn_ok = btn_box.addButton(QDialogButtonBox.StandardButton.Ok)
        btn_cancel = btn_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        btn_reset = btn_box.addButton("Výchozí", QDialogButtonBox.ButtonRole.ResetRole)

        btn_ok.setText("OK")
        btn_cancel.setText("Zrušit")

        btn_box.accepted.connect(self._apply_and_accept)
        btn_box.rejected.connect(self.reject)
        btn_reset.clicked.connect(self._reset_defaults)

        layout.addWidget(btn_box)

    # ── záložka: Obecné ────────────────────────────────────────────────

    def _build_general_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        g = self._prefs.general

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["cs", "en"])
        self._lang_combo.setCurrentText(g.language)
        form.addRow("Jazyk:", self._lang_combo)

        self._units_combo = QComboBox()
        self._units_combo.addItems(["mm", "cm", "m", "in", "ft"])
        self._units_combo.setCurrentText(g.default_units)
        form.addRow("Výchozí jednotky:", self._units_combo)

        self._scale_edit = QLineEdit(g.default_scale)
        form.addRow("Výchozí měřítko:", self._scale_edit)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["system", "light", "dark"])
        self._theme_combo.setCurrentText(g.theme)
        form.addRow("Téma:", self._theme_combo)

        self._autosave_spin = QSpinBox()
        self._autosave_spin.setRange(10, 3600)
        self._autosave_spin.setSuffix(" s")
        self._autosave_spin.setValue(g.autosave_interval_sec)
        form.addRow("Interval autouložení:", self._autosave_spin)

        self._undo_depth_spin = QSpinBox()
        self._undo_depth_spin.setRange(10, 10000)
        self._undo_depth_spin.setValue(g.max_undo_depth)
        form.addRow("Max. hloubka Zpět:", self._undo_depth_spin)

        self._tabs.addTab(w, "Obecné")

    # ── záložka: Viewport ──────────────────────────────────────────────

    def _build_viewport_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        v = self._prefs.viewport

        self._grid_size_spin = QDoubleSpinBox()
        self._grid_size_spin.setRange(0.1, 10000)
        self._grid_size_spin.setDecimals(1)
        self._grid_size_spin.setValue(v.grid_size)
        self._grid_size_spin.setSuffix(" mm")
        form.addRow("Velikost mřížky:", self._grid_size_spin)

        self._grid_sub_spin = QSpinBox()
        self._grid_sub_spin.setRange(1, 100)
        self._grid_sub_spin.setValue(v.grid_subdivisions)
        form.addRow("Dělení mřížky:", self._grid_sub_spin)

        self._orbit_sens = QDoubleSpinBox()
        self._orbit_sens.setRange(0.1, 10.0)
        self._orbit_sens.setDecimals(2)
        self._orbit_sens.setValue(v.orbit_sensitivity)
        form.addRow("Citlivost orbity:", self._orbit_sens)

        self._pan_sens = QDoubleSpinBox()
        self._pan_sens.setRange(0.1, 10.0)
        self._pan_sens.setDecimals(2)
        self._pan_sens.setValue(v.pan_sensitivity)
        form.addRow("Citlivost posunu:", self._pan_sens)

        self._zoom_sens = QDoubleSpinBox()
        self._zoom_sens.setRange(0.1, 10.0)
        self._zoom_sens.setDecimals(2)
        self._zoom_sens.setValue(v.zoom_sensitivity)
        form.addRow("Citlivost zoomu:", self._zoom_sens)

        self._show_grid_cb = QCheckBox()
        self._show_grid_cb.setChecked(v.show_grid)
        form.addRow("Zobrazit mřížku:", self._show_grid_cb)

        self._show_axes_cb = QCheckBox()
        self._show_axes_cb.setChecked(v.show_axes)
        form.addRow("Zobrazit osy:", self._show_axes_cb)

        self._tabs.addTab(w, "Viewport")

    # ── záložka: Přichytávání ──────────────────────────────────────────

    def _build_snap_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        s = self._prefs.snap

        self._snap_enabled_cb = QCheckBox()
        self._snap_enabled_cb.setChecked(s.enabled)
        form.addRow("Přichytávání zapnuto:", self._snap_enabled_cb)

        self._snap_grid_cb = QCheckBox()
        self._snap_grid_cb.setChecked(s.snap_to_grid)
        form.addRow("K mřížce:", self._snap_grid_cb)

        self._snap_vertex_cb = QCheckBox()
        self._snap_vertex_cb.setChecked(s.snap_to_vertex)
        form.addRow("K vrcholům:", self._snap_vertex_cb)

        self._snap_edge_cb = QCheckBox()
        self._snap_edge_cb.setChecked(s.snap_to_edge)
        form.addRow("K hranám:", self._snap_edge_cb)

        self._snap_axis_cb = QCheckBox()
        self._snap_axis_cb.setChecked(s.snap_to_axis)
        form.addRow("K osám:", self._snap_axis_cb)

        self._angle_snap_cb = QCheckBox()
        self._angle_snap_cb.setChecked(s.angle_snap)
        form.addRow("Úhlové přichytávání:", self._angle_snap_cb)

        self._angle_step = QDoubleSpinBox()
        self._angle_step.setRange(1, 90)
        self._angle_step.setDecimals(1)
        self._angle_step.setSuffix("°")
        self._angle_step.setValue(s.angle_step_deg)
        form.addRow("Úhlový krok:", self._angle_step)

        self._tabs.addTab(w, "Přichytávání")

    # ── záložka: Export ────────────────────────────────────────────────

    def _build_export_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        e = self._prefs.export

        self._export_fmt = QComboBox()
        self._export_fmt.addItems(["pdf", "svg", "dxf", "png"])
        self._export_fmt.setCurrentText(e.default_format)
        form.addRow("Výchozí formát:", self._export_fmt)

        self._export_paper = QComboBox()
        self._export_paper.addItems(["A4", "A3", "Letter", "Legal"])
        self._export_paper.setCurrentText(e.default_paper)
        form.addRow("Papír:", self._export_paper)

        self._export_margin = QDoubleSpinBox()
        self._export_margin.setRange(0, 50)
        self._export_margin.setDecimals(1)
        self._export_margin.setSuffix(" mm")
        self._export_margin.setValue(e.default_margin_mm)
        form.addRow("Okraj:", self._export_margin)

        self._export_grammage = QSpinBox()
        self._export_grammage.setRange(80, 400)
        self._export_grammage.setSuffix(" g/m²")
        self._export_grammage.setValue(e.default_grammage)
        form.addRow("Gramáž:", self._export_grammage)

        self._export_tab_shape = QComboBox()
        self._export_tab_shape.addItems(["straight", "tapered", "tooth"])
        self._export_tab_shape.setCurrentText(e.tab_shape)
        form.addRow("Tvar chlopní:", self._export_tab_shape)

        self._export_guide_cb = QCheckBox()
        self._export_guide_cb.setChecked(e.include_build_guide)
        form.addRow("Sestavovací návod:", self._export_guide_cb)

        self._export_dpi = QSpinBox()
        self._export_dpi.setRange(72, 600)
        self._export_dpi.setValue(e.png_dpi)
        form.addRow("PNG DPI:", self._export_dpi)

        self._tabs.addTab(w, "Export")

    # ── záložka: Klávesové zkratky ─────────────────────────────────────

    def _build_shortcuts_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        k = self._prefs.shortcuts

        self._shortcut_edits: dict[str, QLineEdit] = {}
        labels = {
            "new_project": "Nový projekt",
            "open_project": "Otevřít",
            "save_project": "Uložit",
            "save_as": "Uložit jako",
            "undo": "Zpět",
            "redo": "Znovu",
            "delete": "Smazat",
            "duplicate": "Duplikovat",
            "select_all": "Vybrat vše",
            "focus_selection": "Zaostřit výběr",
            "toggle_grid": "Mřížka",
            "toggle_snap": "Přichytávání",
            "view_top": "Pohled shora",
            "view_front": "Pohled zepředu",
            "view_side": "Pohled z boku",
            "view_perspective": "Perspektiva",
            "export": "Export",
        }
        for attr, label in labels.items():
            edit = QLineEdit(getattr(k, attr))
            edit.setPlaceholderText("např. Ctrl+Shift+X")
            self._shortcut_edits[attr] = edit
            form.addRow(f"{label}:", edit)

        self._tabs.addTab(w, "Klávesové zkratky")

    # ── čtení / zápis nastavení ────────────────────────────────────────

    def _apply_and_accept(self) -> None:
        """Přenese hodnoty z UI do Preferences a zavře dialog."""
        g = self._prefs.general
        g.language = self._lang_combo.currentText()
        g.default_units = self._units_combo.currentText()
        g.default_scale = self._scale_edit.text()
        g.theme = self._theme_combo.currentText()
        g.autosave_interval_sec = self._autosave_spin.value()
        g.max_undo_depth = self._undo_depth_spin.value()

        v = self._prefs.viewport
        v.grid_size = self._grid_size_spin.value()
        v.grid_subdivisions = self._grid_sub_spin.value()
        v.orbit_sensitivity = self._orbit_sens.value()
        v.pan_sensitivity = self._pan_sens.value()
        v.zoom_sensitivity = self._zoom_sens.value()
        v.show_grid = self._show_grid_cb.isChecked()
        v.show_axes = self._show_axes_cb.isChecked()

        s = self._prefs.snap
        s.enabled = self._snap_enabled_cb.isChecked()
        s.snap_to_grid = self._snap_grid_cb.isChecked()
        s.snap_to_vertex = self._snap_vertex_cb.isChecked()
        s.snap_to_edge = self._snap_edge_cb.isChecked()
        s.snap_to_axis = self._snap_axis_cb.isChecked()
        s.angle_snap = self._angle_snap_cb.isChecked()
        s.angle_step_deg = self._angle_step.value()

        e = self._prefs.export
        e.default_format = self._export_fmt.currentText()
        e.default_paper = self._export_paper.currentText()
        e.default_margin_mm = self._export_margin.value()
        e.default_grammage = self._export_grammage.value()
        e.tab_shape = self._export_tab_shape.currentText()
        e.include_build_guide = self._export_guide_cb.isChecked()
        e.png_dpi = self._export_dpi.value()

        k = self._prefs.shortcuts
        for attr, edit in self._shortcut_edits.items():
            setattr(k, attr, edit.text())

        self._prefs.save()
        self.accept()

    def _reset_defaults(self) -> None:
        """Obnoví výchozí hodnoty do dialogu."""
        defaults = Preferences.reset()
        self._prefs.general = defaults.general
        self._prefs.viewport = defaults.viewport
        self._prefs.snap = defaults.snap
        self._prefs.export = defaults.export
        self._prefs.shortcuts = defaults.shortcuts

        # Znovu naplnit UI
        self._tabs.clear()
        self._build_general_tab()
        self._build_viewport_tab()
        self._build_snap_tab()
        self._build_export_tab()
        self._build_shortcuts_tab()
