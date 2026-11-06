"""Read-only legacy open routes through Qt; not a native GL-rendering proof."""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QMessageBox, QPlainTextEdit
from archpapercraft.ui.author_window import AuthorMainWindow, QFileDialog
import archpapercraft.ui.author_window as imported

assert Path(imported.__file__).resolve().is_relative_to(args.source.resolve())
app = QApplication([])
scratch = Path(tempfile.mkdtemp(prefix="pc006a-review-legacy-ui-"))
bad = scratch / "broken-old.apcraft"
bad.write_text('{"version":"0.2.0","settings":null,"scene":[]}', encoding="utf-8")
bad_scene = scratch / "broken-scene.apcraft"
bad_scene.write_text('{"version":"0.2.0","settings":{},"scene":[null]}', encoding="utf-8")
cases = [
    ("native-0.2", args.source / "samples/house_with_dome.apcraft", "legacy-view"),
    ("prototype-PanelProject", args.source / "docs/p2/evidence/pc006-desktop-final/house.apcraft", "legacy-view"),
    ("corrupt-legacy-settings", bad, "error"),
    ("recognized-legacy-corrupt-scene-viewer-guard", bad_scene, "error"),
]
results = []
for name, path, expected in cases:
    window = AuthorMainWindow(settings=QSettings(str(scratch / (name+".ini")), QSettings.Format.IniFormat))
    window.show()
    app.processEvents()
    window.controller.execute("Own profile", lambda p: p.add_profile([[0, 0], [100, 0]], closed=False))
    own_path = scratch / (name+"-own.apcraft")
    window.controller.save(own_path)
    own_state = window.project.to_dict()
    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    records = []
    def close_modal():
        modal = app.activeModalWidget()
        if isinstance(modal, QMessageBox):
            records.append({"kind": "error", "title": modal.windowTitle(), "text": modal.text()})
            modal.accept()
        elif isinstance(modal, QDialog):
            texts = modal.findChildren(QPlainTextEdit)
            buttons = modal.findChild(QDialogButtonBox)
            records.append({"kind": "legacy-view", "title": modal.windowTitle(), "plain_text_view": bool(texts), "text_is_read_only": all(t.isReadOnly() for t in texts), "buttons": int(buttons.standardButtons().value) if buttons else None})
            modal.reject()
    timer = QTimer()
    timer.timeout.connect(close_modal)
    timer.start(30)
    with patch.object(QFileDialog, "getOpenFileName", return_value=(str(path), "Papercraft")):
        window.actions["open"].trigger()
    timer.stop()
    unchanged_source = hashlib.sha256(path.read_bytes()).hexdigest() == source_hash
    unchanged_active = window.project.to_dict() == own_state and window.controller.file_path == own_path and not window.controller.dirty
    wanted = [r for r in records if r["kind"] == expected]
    read_only = all(r.get("text_is_read_only", True) for r in records)
    close_only = all(r.get("buttons") == QDialogButtonBox.StandardButton.Close.value for r in records if r["kind"] == "legacy-view")
    results.append({"name": name, "source_path": str(path), "source_sha256": source_hash, "records": records, "original_unchanged": unchanged_source, "active_author_project_and_path_unchanged": unchanged_active, "pass": bool(wanted) and unchanged_source and unchanged_active and read_only and close_only})
    window.hide()
    window.deleteLater()
    app.processEvents()
result = {"source_sha": args.sha, "source_root": str(args.source), "evidence_kind": "offscreen_Qt_modal_open_route_and_file_preservation; not_native_GL_or_migration", "results": results, "pass": sum(r["pass"] for r in results), "fail": sum(not r["pass"] for r in results)}
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(1 if result["fail"] else 0)
