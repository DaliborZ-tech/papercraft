"""Recovery for the active authoring window, separate from explicit project saves."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QLockFile, QObject, QSettings, QSignalBlocker, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.recovery import RecoveryStore


def _fields(host):
    fields = {name: getattr(host, name) for name in (
        "vertex_x", "vertex_y", "paper_x", "paper_y", "paper_angle", "scale_field",
        "grid", "tab_width", "tab_taper",
    )}
    fields.update({f"transform_{i}": field for i, field in enumerate(host.transform_fields)})
    return fields


def _pending_number(host):
    field = QApplication.focusWidget()
    while field is not None and field is not host and not isinstance(field, QAbstractSpinBox):
        field = field.parentWidget()
    if not isinstance(field, QAbstractSpinBox) or field.window() is not host:
        return None
    key = next((key for key, value in _fields(host).items() if value is field), None)
    if key is None:
        return None
    normal = field.prefix() + field.textFromValue(field.value()) + field.suffix()
    if field.lineEdit().text() == normal:
        return None
    return {"field": key, "text": field.lineEdit().text()}


def _pending_name(host):
    field = getattr(host, "selection_name", None)
    surface = host.project.surfaces.get(host.selected_surface)
    if (field is None or not field.hasFocus() or surface is None
            or field.text() == surface.name):
        return None
    return {"surface_id": surface.id, "text": field.text()}


def capture_ui(host):
    """Read raw input without interpretText, focus changes, commands or recompute."""
    sketch = host.sketch
    draft = None
    if sketch.drawing and (sketch.points or sketch.pending_points):
        draft = {name: copy.deepcopy(getattr(sketch, name)) for name in (
            "points", "curve_segments", "pending_points", "segment_mode", "hole", "_input_history",
        )}
        draft.update(plane=host.draft_plane, surface=host.draft_surface)
    return {
        "selection": {name: copy.deepcopy(getattr(host, "selected_" + name))
                      for name in ("surface", "profile", "generation", "edge", "vertex")},
        "joint": host.current_joint,
        "units": host.units.currentData(), "plane": host.plane.currentData(),
        "grid": host.grid.value(), "sketch": draft, "pending_number": _pending_number(host),
        "pending_name": _pending_name(host),
        "context": getattr(host, "workspace_context", None),
        "sketch_visible": host.sketch.isVisibleTo(host),
    }


def _point(point):
    return (isinstance(point, (list, tuple)) and len(point) == 2
            and all(type(x) in (int, float) and math.isfinite(x) for x in point))


def _sketch_state(state, *, history=False):
    if (not isinstance(state, dict) or state.get("segment_mode") not in ("line", "arc", "cubic")
            or type(state.get("hole")) is not bool or state.get("plane") not in ("XY", "XZ", "YZ")
            or not isinstance(state.get("points"), list) or not history and not state["points"]
            or not all(_point(p) for p in state["points"])
            or not isinstance(state.get("pending_points"), list)
            or not all(_point(p) for p in state["pending_points"])
            or len(state["pending_points"]) >= {"line": 1, "arc": 2, "cubic": 3}[
                state["segment_mode"]]
            or not isinstance(state.get("curve_segments"), list)):
        raise ValueError("Rozpracovaný obrys v konceptu není platný.")
    segments = state["curve_segments"]
    if len(segments) != max(0, len(state["points"]) - 1):
        raise ValueError("Rozpracovaný obrys nemá souvislé úseky.")
    for i, segment in enumerate(segments):
        if (not isinstance(segment, dict) or segment.get("kind") not in ("line", "arc", "cubic")
                or not isinstance(segment.get("data"), dict)
                or segment.get("start") != state["points"][i]
                or segment.get("end") != state["points"][i + 1]):
            raise ValueError("Rozpracovaný obrys nemá souvislé úseky.")
        Curve(tuple(segment["start"]), tuple(segment["end"]), segment["kind"], segment["data"])
    if not history:
        if not isinstance(state.get("_input_history"), list):
            raise ValueError("Koncept obsahuje neplatné kroky obrysu.")
        for entry in state["_input_history"]:
            if not isinstance(entry, (tuple, list)) or len(entry) != 4:
                raise ValueError("Koncept obsahuje neplatné kroky obrysu.")
            points, segments, pending, mode = entry
            _sketch_state(dict(state, points=points, curve_segments=segments,
                               pending_points=pending, segment_mode=mode), history=True)


def _validated_ui(host, project, data):
    """Validate before replacing live work. Invalid references never select a nearby ID."""
    if not isinstance(data, dict) or not isinstance(data.get("selection"), dict):
        raise ValueError("Koncept neobsahuje platný pracovní kontext.")
    data = copy.deepcopy(data)
    if data.get("context") not in (None, "Modelování", "Spoje a rozvin", "Stránky", "Export"):
        raise ValueError("Koncept obsahuje neznámý pracovní kontext.")
    if data.get("joint") is not None and data["joint"] not in project.joints:
        raise ValueError("Vybraný spoj konceptu již není dostupný.")
    if type(data.get("sketch_visible")) is not bool:
        raise ValueError("Koncept obsahuje neplatnou viditelnost obrysu.")
    selection = data["selection"]
    for key, records in (("surface", project.surfaces), ("profile", project.profiles),
                         ("generation", project.segmented_variants)):
        if selection.get(key) is not None and selection[key] not in records:
            raise ValueError("Vybraný prvek konceptu již není dostupný.")
    edge, vertex = selection.get("edge"), selection.get("vertex")
    surface = selection.get("surface")
    if surface and selection.get("profile") not in project.surfaces[surface].source_profile_ids():
        raise ValueError("Vybraný profil nepatří k vybrané ploše.")
    generation = project.segmented_variants.get(selection.get("generation"))
    if generation and surface != generation.target_surface_id and not any(
            row["surface_id"] == surface for row in generation.triangle_bindings):
        raise ValueError("Vybraná generace nepatří k vybrané ploše.")
    if edge is not None:
        if (not isinstance(edge, (list, tuple)) or len(edge) != 2
                or edge[0] != selection.get("surface")
                or edge[0] not in project.surfaces
                or not any(s.id == edge[1] for pid in project.surfaces[edge[0]].source_profile_ids()
                           for s in project.profiles[pid].segments)):
            raise ValueError("Vybraný okraj konceptu již není dostupný.")
    if vertex is not None:
        owners = (project.surfaces[surface].source_profile_ids() if surface
                  else [selection.get("profile")])
        if (not isinstance(vertex, (list, tuple)) or len(vertex) != 2
                or vertex[0] not in owners or vertex[0] not in project.profiles
                or not any(v.id == vertex[1] for v in project.profiles[vertex[0]].vertices)):
            raise ValueError("Vybraný bod konceptu již není dostupný.")
    if data.get("joint"):
        joint = project.joints[data["joint"]]
        if surface not in (joint.surface_a, joint.surface_b):
            raise ValueError("Vybraný spoj nepatří k vybrané ploše.")
    if (data.get("units") not in (1, 10, 1000) or data.get("plane") not in ("XY", "XZ", "YZ")
            or type(data.get("grid")) not in (int, float) or not math.isfinite(data["grid"])
            or not 0 <= data["grid"] <= 10000):
        raise ValueError("Koncept obsahuje neplatné jednotky nebo pracovní rovinu.")
    sketch = data.get("sketch")
    if sketch is not None:
        _sketch_state(sketch)
        if sketch["hole"] and (sketch.get("surface") not in project.surfaces
                or sketch["surface"] != selection.get("surface")):
            raise ValueError("Plocha rozpracovaného otvoru již není dostupná.")
    pending = data.get("pending_number")
    if pending is not None and (not isinstance(pending, dict)
            or pending.get("field") not in _fields(host) or not isinstance(pending.get("text"), str)
            or len(pending["text"]) > 1000):
        raise ValueError("Koncept obsahuje neznámý rozepsaný vstup.")
    if pending:
        field = pending["field"]
        if ((field.startswith("vertex_") and vertex is None)
                or field.startswith("paper_") and selection.get("surface") is None
                or field.startswith("transform_") and selection.get("surface") is None
                and selection.get("profile") is None
                or field in ("tab_width", "tab_taper") and data.get("joint") is None):
            raise ValueError("Rozepsaný vstup nemá odpovídající vybraný prvek.")
    name = data.get("pending_name")
    if name is not None:
        field = getattr(host, "selection_name", None)
        if (not isinstance(name, dict) or field is None
                or name.get("surface_id") != surface or surface is None
                or not isinstance(name.get("text"), str)
                or len(name["text"]) > field.maxLength() or pending is not None):
            raise ValueError("Rozepsaný název nemá odpovídající vybranou plochu.")
    return data


def restore_ui(host, data):
    host.sketch.cancel_outline()
    host.connect_source = host.current_joint = None
    host.draft_surface = host.draft_plane = None
    with QSignalBlocker(host.units), QSignalBlocker(host.plane), QSignalBlocker(host.grid):
        host.units.setCurrentIndex(host.units.findData(data["units"]))
        host.plane.setCurrentIndex(host.plane.findData(data["plane"]))
        host.grid.setValue(data["grid"])
    host.sketch.grid_mm = data["grid"] * data["units"]
    host.clear_selection()
    selection = data["selection"]
    host.selected_generation = selection.get("generation")
    host.selected_edge = tuple(selection["edge"]) if selection.get("edge") else None
    if selection.get("surface"):
        host.select_surface(selection["surface"])
    elif selection.get("profile"):
        host.select_profile(selection["profile"])
    if selection.get("vertex"):
        host.select_vertex(*selection["vertex"])
    if data.get("joint"):
        host.current_joint = data["joint"]
        host._sync_selection()
    if data.get("context") and hasattr(host, "set_workspace_context"):
        host.set_workspace_context(data["context"])
    if hasattr(host, "set_sketch_visible"):
        host.set_sketch_visible(data["sketch_visible"])
    sketch = data.get("sketch")
    if sketch:
        for name in ("points", "curve_segments", "pending_points", "segment_mode", "hole"):
            setattr(host.sketch, name, copy.deepcopy(sketch[name]))
        host.sketch._input_history = copy.deepcopy(sketch["_input_history"])
        host.sketch.drawing = True
        host.draft_surface, host.draft_plane = sketch.get("surface"), sketch["plane"]
        host.sketch.setCursor(Qt.CursorShape.CrossCursor)
        host.sketch.redraw()
        host.sketch.segment_mode_changed.emit(host.sketch.segment_mode)
        host.sketch.draft_changed.emit()
    pending = data.get("pending_number")
    name = data.get("pending_name")
    if pending:
        field = _fields(host)[pending["field"]]
        # Expose the existing property section if it was collapsed.
        for button, box in host.sections.values():
            if box.isAncestorOf(field):
                button.setChecked(True)
        with QSignalBlocker(field), QSignalBlocker(field.lineEdit()):
            field.lineEdit().setText(pending["text"])
        field.setFocus()
    elif name is not None:
        # Restore the raw editor only after its exact surface/context was restored.
        # The last valid domain name remains unchanged until explicit confirmation.
        with QSignalBlocker(host.selection_name):
            host.selection_name.setText(name["text"])
        host.selection_name.setFocus()
    elif sketch:
        host.sketch.setFocus()
    host.update_guidance()


class AuthorRecovery(QObject):
    def __init__(self, host, store):
        super().__init__(host)
        self.host, self.store = host, store
        self.session_id = str(uuid4())
        self.lease = None
        self.closed = False
        self.timer = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.checkpoint)
        self.timer.start()
        self.host.controller.on_document_event = self.document_event
        self.host.controller.before_document_replace = self.before_replace
        self.action = QAction("Obnovit neuloženou práci…", host)
        self.action.triggered.connect(self.offer)
        host.menuBar().actions()[0].menu().addAction(self.action)
        host.actions["recover"] = self.action
        QTimer.singleShot(0, self._startup)

    def _claim(self, path):
        path = self.store._owned_path(path)
        self.store.directory.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(path) + ".lock")
        # Long-lived window ownership: timestamp expiry must never steal a live draft.
        # https://doc.qt.io/qt-6/qlockfile.html#setStaleLockTime
        lock.setStaleLockTime(0)
        return lock if lock.tryLock(0) else None

    def _clear_own(self):
        if self.lease is not None:
            self.store.discard(self.store.path(self.session_id))

    def checkpoint(self):
        if self.closed or self.host.project is None:
            return False
        try:
            state = self.host.project.to_dict(validate=False)
            ui = capture_ui(self.host)
            changed = self.host.controller.digest(state) != self.host.controller._saved_digest
            if (not changed and not ui["sketch"] and not ui["pending_number"]
                    and not ui["pending_name"]):
                self._clear_own()
                return False
            if self.lease is None:
                self.lease = self._claim(self.store.path(self.session_id))
                if self.lease is None:
                    raise OSError("Koncept je právě otevřený v jiném okně.")
            source = self.host.controller.file_path or self.host.controller.copy_source_path
            self.store.write(self.session_id, state, ui, source)
            self.host.statusBar().showMessage(
                "Záložní koncept uložen. Soubor modelu uložíte příkazem Uložit.", 5000)
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.host.statusBar().showMessage(f"Záložní koncept se nepodařilo uložit: {exc}", 12000)
            return False

    def document_event(self, event):
        try:
            if event == "replaced":
                self._clear_own()
            elif event == "saved":
                self.checkpoint()
        except OSError as exc:
            self.host.statusBar().showMessage(
                f"Starý koncept se nepodařilo odstranit: {exc}", 12000)

    def before_replace(self):
        try:
            self._clear_own()
            return True
        except OSError as exc:
            QMessageBox.warning(self.host, "Model zůstává otevřený",
                                "Koncept se nepodařilo odstranit. Změna modelu byla zastavena, "
                                "aby se zahozená práce příště znovu nenabízela.\n" + str(exc))
            self.host.refresh()
            return False

    def finished_close(self):
        try:
            self._clear_own()
        except OSError as exc:
            QMessageBox.warning(self.host, "Model zůstává otevřený",
                                "Koncept se nepodařilo odstranit. Zavření bylo zastaveno, "
                                "aby se zahozená práce příště znovu nenabízela.\n" + str(exc))
            return False
        self.timer.stop()
        self.closed = True
        if self.lease is not None:
            self.lease.unlock()
            self.lease = None
        return True

    def available(self):
        result = []
        for path in self.store.candidates():
            if path == self.store.path(self.session_id):
                continue
            try:
                self.store._owned_path(path)
                lease = self._claim(path)
            except (OSError, ValueError):
                continue
            if lease is None:
                continue
            try:
                data = self.store.read(path)
                label = str(data["document"].get("name", "Nepojmenovaný model"))
                label += " · " + data["saved_at"][:19].replace("T", " ") + " UTC"
                if data["original_path"]:
                    label += "\nPůvodní soubor: " + data["original_path"]
                result.append((path, data, label))
            except (OSError, ValueError, TypeError):
                result.append((path, None, "Nečitelný koncept · obsah zůstává zachovaný"))
            finally:
                lease.unlock()
        return result

    def _startup(self):
        if not self.closed and self.available():
            self.offer(startup=True)

    def restore(self, path):
        path = self.store._owned_path(path)
        lease = self._claim(path)
        if lease is None:
            raise ValueError("Koncept je právě otevřený v jiném okně.")
        try:
            data = self.store.read(path)
            project = AuthorProject.from_dict(data["document"])
            ui = _validated_ui(self.host, project, data["ui_draft"])
            if not self.host._confirm_replace():
                return False
            self._clear_own()
            self.host.controller.restore_recovery(data["document"], data["original_path"])
            if self.lease is not None:
                self.lease.unlock()
            self.session_id = path.name.removesuffix(".recovery.json")
            self.lease, lease = lease, None
            restore_ui(self.host, ui)
            self.host.statusBar().showMessage(
                "Obnovena neuložená kopie. Uložte ji pod novým názvem; původní soubor zůstává.",
                15000)
            return True
        finally:
            if lease is not None:
                lease.unlock()

    def offer(self, _checked=False, *, startup=False):
        # Explicit menu operation uses the same pending-input boundary as Open/Save.
        if not startup and not self.host._commit_pending_input():
            return
        candidates = self.available()
        if not candidates:
            if not startup:
                QMessageBox.information(self.host, "Obnova práce", "Žádný volný koncept k obnově.")
            return
        dialog = QDialog(self.host)
        dialog.setWindowTitle("Obnovit neuloženou práci")
        dialog.resize(680, 340)
        layout = QVBoxLayout(dialog)
        label = QLabel("Po přerušení práce zůstaly tyto koncepty. Obnovení otevře neuloženou "
                       "kopii, původní soubor nepřepíše. Později koncept zachová.")
        label.setWordWrap(True)
        layout.addWidget(label)
        listing = QListWidget()
        for path, data, text in candidates:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setData(Qt.ItemDataRole.UserRole + 1, data is not None)
            listing.addItem(item)
        listing.setCurrentRow(0)
        layout.addWidget(listing)
        buttons = QDialogButtonBox()
        restore = buttons.addButton("Obnovit kopii", QDialogButtonBox.ButtonRole.AcceptRole)
        discard = buttons.addButton("Zahodit koncept", QDialogButtonBox.ButtonRole.DestructiveRole)
        later = buttons.addButton("Později", QDialogButtonBox.ButtonRole.RejectRole)
        later.clicked.connect(dialog.reject)

        def selected():
            restore.setEnabled(bool(listing.currentItem() and listing.currentItem().data(
                Qt.ItemDataRole.UserRole + 1)))

        def act(delete=False):
            item = listing.currentItem()
            if item is None:
                return
            path = item.data(Qt.ItemDataRole.UserRole)
            try:
                if delete:
                    lease = self._claim(path)
                    if lease is None:
                        raise ValueError("Koncept je právě otevřený v jiném okně.")
                    try:
                        self.store.discard(path)
                    finally:
                        lease.unlock()
                    listing.takeItem(listing.row(item))
                    if not listing.count():
                        dialog.accept()
                else:
                    # Close the modal before restoring focus/raw numeric text.
                    dialog.accept()
                    self.restore(path)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                QMessageBox.warning(self.host, "Koncept nelze obnovit", str(exc))

        listing.currentItemChanged.connect(lambda *_: selected())
        restore.clicked.connect(lambda: act())
        discard.clicked.connect(lambda: act(True))
        selected()
        layout.addWidget(buttons)
        dialog.exec()


def setup_recovery(host):
    # Explicit INI settings used by tests/proof drivers also isolate all draft discovery.
    if host.settings.format() == QSettings.Format.IniFormat:
        directory = Path(host.settings.fileName()).parent / "recovery"
    else:
        directory = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation)) / "recovery"
    return AuthorRecovery(host, RecoveryStore(directory))
