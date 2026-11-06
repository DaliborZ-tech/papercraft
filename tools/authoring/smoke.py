"""Short native Windows startup probe; not a novice test."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from archpapercraft.ui.author_window import AuthorMainWindow  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True, type=Path, help="New evidence directory")
args = parser.parse_args()
target = args.output.resolve()
target.mkdir(parents=True, exist_ok=False)
app = QApplication([sys.argv[0]])
settings = QSettings(str(target / "settings.ini"), QSettings.Format.IniFormat)
window = AuthorMainWindow(settings=settings)
window.show()
result = {
    "source_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    "source_files": {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "src/archpapercraft").rglob("*.py"))
    },
    "proof_kind": "native Qt startup, not novice or physical proof",
}


def probe():
    try:
        result["blank_surfaces"] = len(window.project.surfaces)
        result["tips_visible"] = window.hint.isVisible()
        result["minimum_width"] = window.minimumSizeHint().width()
        result["size"] = [window.width(), window.height()]
        result["opengl_valid"] = window.viewport.isValid()
        result["dirty"] = window.controller.dirty
        window.grab().save(str(target / "workspace.png"))
        window.screen().grabWindow(window.winId()).save(str(target / "native-window.png"))
        window.viewport.grabFramebuffer().save(str(target / "framebuffer.png"))
        if window.viewport.isValid():
            from OpenGL import GL
            window.viewport.makeCurrent()
            result["opengl_version"] = GL.glGetString(GL.GL_VERSION).decode()
            window.viewport.doneCurrent()
        result["pass"] = result["blank_surfaces"] == 0 and result["opengl_valid"]
    except Exception as exc:
        result["error"] = repr(exc)
        result["pass"] = False
    (target / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    app.exit(0 if result["pass"] else 1)


QTimer.singleShot(1800, probe)
raise SystemExit(app.exec())
