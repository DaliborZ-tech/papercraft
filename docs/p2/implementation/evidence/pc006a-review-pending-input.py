"""Pinned Qt regression: pending numeric input must precede save/export snapshot.

Setup is a controller fixture; the behavior under review uses real widgets,
shortcuts and a real QMessageBox. Not a native desktop or novice-user proof.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--include-invalid", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from archpapercraft.ui.author_window import AuthorMainWindow
import archpapercraft.ui.author_window as imported

assert Path(imported.__file__).resolve().is_relative_to(args.source.resolve())
app = QApplication([])
scratch = Path(tempfile.mkdtemp(prefix="pc006a-review-pending-input-"))
results = []


def fixture(name):
    window = AuthorMainWindow(settings=QSettings(str(scratch / (name+".ini")), QSettings.Format.IniFormat))
    window.resize(1450, 900)
    window.show()
    window.activateWindow()
    window.raise_()
    QTest.qWait(60)
    def operation(project):
        profile = project.add_profile([[0, 0], [10000, 0], [10000, 5000], [0, 5000]])
        surface = project.add_surface(profile)
        project.set_placement(project.part_for_surface(surface), page_id=project.pages[0].id, x_mm=30, y_mm=30)
        return surface
    sid = window.controller.execute("Reviewer fixture", operation)
    window.select_surface(sid)
    profile = window.project.profiles[window.project.surfaces[sid].profile_id]
    window.vertex_choice.setCurrentIndex(1)
    assert window.selected_vertex == (profile.id, profile.vertices[1].id)
    path = scratch / (name+".apcraft")
    window.controller.save(path)
    return window, profile.id, profile.vertices[1].id, path


def pending(window, text="11"):
    window.vertex_x.setFocus()
    QTest.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClicks(window.vertex_x, text)  # UI metres.
    QTest.qWait(10)


def dispose(window):
    window.hide()
    window.deleteLater()
    app.processEvents()


window, profile, vertex, path = fixture("save")
pending(window)
text = window.vertex_x.text()
QTest.keyClick(window.vertex_x, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
QTest.qWait(60)
saved = json.loads(path.read_text(encoding="utf-8"))
saved_profile = saved["profiles"][profile]
saved_x = next(v["point"][0] for v in saved_profile["vertices"] if v["id"] == vertex)
current_x = window.project.profiles[profile].vertex(vertex).point[0]
results.append({"name": "pending_vertex_CtrlS_existing_path", "typed_text": text, "saved_x_model_mm": saved_x, "current_source_x_model_mm": current_x, "dirty_after_shortcut": window.controller.dirty, "pass": saved_x == 11000 and current_x == 11000})
dispose(window)

window, profile, vertex, path = fixture("export")
original_revision = window.project.revision
export_folder = scratch / "export"
export_folder.mkdir()
dialogs = []


def dialog_driver():
    modal = app.activeModalWidget()
    if isinstance(modal, QMessageBox):
        dialogs.append({"title": modal.windowTitle(), "text": modal.text(), "revision_at_dialog": window.project.revision, "source_x_at_dialog": window.project.profiles[profile].vertex(vertex).point[0]})
        button = modal.button(QMessageBox.StandardButton.Ok)
        if button is not None:
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        else:
            modal.reject()


timer = QTimer()
timer.timeout.connect(dialog_driver)
timer.start(25)
pending(window)
with patch.object(QFileDialog, "getExistingDirectory", return_value=str(export_folder)):
    QTest.keyClick(window.vertex_x, Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier)
    QTest.qWait(60)
timer.stop()
manifest_file = export_folder / ".author-export.json"
manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else None
current_x = window.project.profiles[profile].vertex(vertex).point[0]
stale = any(p.stale for p in window.project.parts.values())
results.append({"name": "pending_vertex_CtrlE_snapshot_before_modal_commit", "original_revision": original_revision, "current_revision": window.project.revision, "current_source_x_model_mm": current_x, "part_stale_after_modal": stale, "export_created": manifest is not None, "export_manifest_revision": manifest.get("revision") if manifest else None, "dialogs": dialogs, "pass": current_x == 11000 and not manifest_file.exists()})
dispose(window)

window, profile, vertex, path = fixture("new")
original_project_id = window.project.project_id
replace_dialogs = []
def cancel_replace():
    modal = app.activeModalWidget()
    if isinstance(modal, QMessageBox):
        replace_dialogs.append({"title": modal.windowTitle(), "text": modal.text()})
        button = modal.button(QMessageBox.StandardButton.Cancel)
        if button is not None:
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        else:
            modal.reject()
timer = QTimer()
timer.timeout.connect(cancel_replace)
timer.start(25)
pending(window)
QTest.keyClick(window.vertex_x, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
QTest.qWait(60)
timer.stop()
results.append({"name": "pending_vertex_CtrlN_must_not_discard_without_dirty_prompt", "original_project_id": original_project_id, "current_project_id": window.project.project_id, "source_retained": profile in window.project.profiles, "dialogs": replace_dialogs, "pass": window.project.project_id == original_project_id and profile in window.project.profiles and any(d["title"] == "Neuložený model" for d in replace_dialogs)})
dispose(window)

if args.include_invalid:
    for shortcut in (Qt.Key.Key_S, Qt.Key.Key_E, Qt.Key.Key_N):
        label = chr(shortcut.value)
        window, profile, vertex, path = fixture("invalid-"+label)
        before_state = window.project.to_dict()
        before_bytes, before_time = path.read_bytes(), path.stat().st_mtime_ns
        invalid_dialogs = []
        def reject_invalid_modal():
            modal = app.activeModalWidget()
            if isinstance(modal, QMessageBox):
                invalid_dialogs.append({"title": modal.windowTitle(), "text": modal.text()})
                button = modal.button(QMessageBox.StandardButton.Ok)
                if button is None:
                    button = modal.button(QMessageBox.StandardButton.Cancel)
                if button is not None:
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                else:
                    modal.reject()
        timer = QTimer()
        timer.timeout.connect(reject_invalid_modal)
        timer.start(25)
        pending(window, "-1")  # Would cross the fixed left edge: invalid material.
        folder = scratch / ("invalid-export-"+label)
        folder.mkdir()
        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(folder)):
            QTest.keyClick(window.vertex_x, shortcut, Qt.KeyboardModifier.ControlModifier)
            QTest.qWait(60)
        timer.stop()
        same_state = window.project.to_dict() == before_state
        same_disk = path.read_bytes() == before_bytes and path.stat().st_mtime_ns == before_time
        no_export = not list(folder.iterdir())
        warning = any(d["title"] == "Změnu nelze dokončit" for d in invalid_dialogs)
        no_confirmation = not any(d["title"] in ("Vektorový export", "Neuložený model") for d in invalid_dialogs)
        results.append({"name": "invalid_pending_vertex_Ctrl"+label, "source_unchanged": same_state, "saved_bytes_and_mtime_unchanged": same_disk, "no_export": no_export, "dialogs": invalid_dialogs, "pass": same_state and same_disk and no_export and warning and no_confirmation})
        dispose(window)

result = {"source_sha": args.sha, "source_root": str(args.source), "scratch": str(scratch), "evidence_kind": "offscreen_real_Qt_widgets_shortcuts_modal; controller_setup; not_native_or_human", "results": results, "pass": sum(r["pass"] for r in results), "fail": sum(not r["pass"] for r in results)}
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(1 if result["fail"] else 0)
