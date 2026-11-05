"""Record reproducible baseline commands without changing production code."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/revival/evidence"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    commands = [
        ("environment", [sys.executable, "-c", "import platform,sys; print(platform.platform()); print(sys.version); import archpapercraft,PySide6,numpy,scipy,reportlab,svgwrite,OpenGL; print('imports OK')"]),
        ("dependencies", ["uv", "pip", "check", "--python", sys.executable]),
        ("packages", ["uv", "pip", "freeze", "--python", sys.executable]),
        ("pytest-baseline", [sys.executable, "-m", "pytest", "tests", "-ra", "--junitxml=docs/revival/evidence/pytest-baseline.xml"]),
    ]
    records = []
    env = os.environ.copy()
    env["APPDATA"] = tempfile.mkdtemp(prefix="papercraft-baseline-settings-")
    env["PYTHONUTF8"] = "1"
    for name, command in commands:
        started = datetime.now(timezone.utc).isoformat()
        clock = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (EVIDENCE / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        record = dict(name=name, command=command, started_utc=started, seconds=round(time.perf_counter()-clock, 3), exit_code=result.returncode)
        records.append(record)
        print(json.dumps(record), flush=True)
    (EVIDENCE / "baseline-commands.json").write_text(json.dumps(dict(os=platform.platform(), python=sys.version, commands=records), indent=2), encoding="utf-8")
    return int(any(record["exit_code"] for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
