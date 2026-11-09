"""Bind actual a1cbf92 core and exact 133a2ef widget; run only API identity smoke."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
root = Path(__file__).resolve().parents[4]
archive = Path(tempfile.gettempdir()) / "pc007a-loft-ui-review-a1cbf92"
sys.path.insert(0, str(archive / "src"))
import archpapercraft.authoring.project as core
import archpapercraft.ui

assert Path(core.__file__).resolve() == archive / "src/archpapercraft/authoring/project.py"
widget = root / "src/archpapercraft/ui/author_loft.py"
spec = importlib.util.spec_from_file_location("archpapercraft.ui.author_loft", widget)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert Path(module.__file__).resolve() == widget
hash_value = hashlib.sha256(widget.read_bytes()).hexdigest()
assert hash_value == "faeeef680b06d3540bbd1bebb32ab29b4c163ddfac73779d15c8c4af51a810f3"
evidence = Path(__file__).parent
(evidence / "pc007a-loft-ui-review-133a2ef-api-binding.json").write_text(json.dumps({
    "core_source_pin": "a1cbf920397694f3b1d3e85a08052acdc3962a7b",
    "core_actual_path": core.__file__,
    "widget_source_pin": "133a2efb5f4a6a1ae43c42cc7b669f27b9cbd410",
    "widget_actual_path": module.__file__, "widget_sha256": hash_value,
    "scope": "WIDGET_AND_PUBLIC_API_IDENTITY_ONLY_NOT_GEOMETRY_APPROVAL",
    "qt_platform": os.environ["QT_QPA_PLATFORM"],
}, indent=2), encoding="utf8")

import pytest

raise SystemExit(pytest.main([
    str(root / "tests/authoring/test_loft_dialog.py"),
    "-k", "test_closed_seam_actual_public_api_creation_and_edit_preserve_exact_requested_identity",
    "-q", "--junitxml=" + str(evidence / "pc007a-loft-ui-review-133a2ef-api-smoke.xml"),
]))
