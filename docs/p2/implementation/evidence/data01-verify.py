"""Run scoped recovery checks and bind the actual process to this checkout."""

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
FILES = (
    "src/archpapercraft/authoring/recovery.py",
    "src/archpapercraft/application/author_controller.py",
    "src/archpapercraft/ui/author_recovery.py",
    "src/archpapercraft/ui/author_window.py",
    "tests/authoring/test_recovery.py",
    "tests/authoring/test_recovery_workspace.py",
)


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in FILES}


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "src"))
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    before = hashes()
    started = time.monotonic()
    result = pytest.main([
        "tests/authoring/test_recovery.py", "tests/authoring/test_recovery_workspace.py",
        "tests/authoring/test_controller.py", "tests/authoring/test_workspace.py",
        "tests/authoring/test_curve_workspace.py", "tests/authoring/test_profile_workspace.py",
        "tests/authoring/test_segmentation_workspace.py", "-q",
        "--junitxml=docs/p2/implementation/evidence/data01-recovery-final.xml",
    ])
    imports = {name: module.__file__ for name, module in list(sys.modules.items())
               if name.startswith("archpapercraft") and getattr(module, "__file__", None)}
    assert imports and all(Path(path).resolve().is_relative_to(ROOT / "src")
                           for path in imports.values()), imports
    after = hashes()
    assert after == before
    evidence = {
        "base_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_changes": subprocess.check_output(["git", "status", "--short"], text=True),
        "pytest_exit": int(result), "elapsed_seconds": time.monotonic() - started,
        "lf_sha256_before_equals_after": after, "actual_finish_imports": imports,
        "window_hook": "Applied exact data01-window-hooks.patch for this verification only; "
                       "workspace owner applies these same hooks to combined UI candidate.",
        "proof_kind": "offscreen component + storage + actual child-process abrupt exit, "
                      "not native desktop, novice usability or product acceptance",
        "scope_limit": "Unconfirmed controls in separate modal construction previews are not "
                       "serialized; confirmed domain + main inspector raw edit + sketch protected.",
        "earlier_diagnostic_failure": "Additional source2 test first called guessed nonexistent "
                                      "add_loft_surface API (1FAIL AttributeError); test setup now "
                                      "uses public target() fixture. No product fix implied.",
    }
    target = ROOT / "docs/p2/implementation/evidence/data01-recovery-binding.json"
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
