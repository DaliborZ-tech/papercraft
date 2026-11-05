"""Bound a probe process and capture UTF-8 evidence with command, timing and exit code."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
name = sys.argv[1]
command = [sys.executable, str(root / 'tools/revival' / f'{name}.py'), *sys.argv[2:]]
started = datetime.now(timezone.utc).isoformat()
clock = time.perf_counter()
env = dict(os.environ, PYTHONUTF8='1')
try:
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=120, encoding='utf-8', errors='replace')
    output, code = result.stdout + result.stderr, result.returncode
except subprocess.TimeoutExpired as exc:
    output = repr(exc.stdout) + '\n' + repr(exc.stderr) + '\nTIMEOUT: probe child terminated'
    code = 124
out = root / 'docs/revival/evidence'
(out/f'{name}-run.log').write_text(output,encoding='utf-8')
record = dict(command=command,started_utc=started,seconds=round(time.perf_counter()-clock,3),exit_code=code)
(out/f'{name}-run.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
print(output.encode('ascii','backslashreplace').decode())
raise SystemExit(code)
