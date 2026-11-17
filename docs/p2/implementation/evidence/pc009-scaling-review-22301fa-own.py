"""Independent CLI rejection tests: real source, no application or desktop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
SOURCE = '22301faa45c8393cc127a3f117b0708cd48eea5f'
SCRIPT = ROOT/'tools/authoring/desktop_scaling_probe.py'

def run(output):
    return subprocess.run([sys.executable, str(SCRIPT), '--scale', '1.5', '--expected-sha',
                           'wrong-sha', '--output', str(output)], capture_output=True,
                          cwd=ROOT, env=dict(os.environ, QT_QPA_PLATFORM='offscreen',
                                            PYTHONPATH=str(ROOT/'src')))

def hashes(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}

assert subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip() == SOURCE
records = []
with tempfile.TemporaryDirectory(prefix='papercraft-scaling-own-') as temporary:
    base = Path(temporary)
    file = base/'existing-file'
    file.write_bytes(b'previous independent evidence\x00\xff')
    before = hashes(base)
    result = run(file)
    assert result.returncode != 0 and b'fresh directory' in result.stderr and hashes(base) == before
    records.append(dict(case='existing ordinary file', returncode=result.returncode,
                        stderr=result.stderr.decode(), preserved=True))
    folder = base/'older-run'
    (folder/'nested').mkdir(parents=True)
    (folder/'scaling-observations.json').write_bytes(b'{"older":1}\n')
    (folder/'nested'/'foreign.txt').write_bytes(b'foreign payload')
    before = hashes(base)
    result = run(folder)
    assert result.returncode != 0 and b'fresh directory' in result.stderr and hashes(base) == before
    records.append(dict(case='existing directory and nested foreign bytes', returncode=result.returncode,
                        stderr=result.stderr.decode(), preserved=True))
    output = base/'not-created'
    before = hashes(base)
    result = run(output)
    assert result.returncode != 0 and b'Expected reviewed source wrong-sha' in result.stderr
    assert SOURCE.encode() in result.stderr and not output.exists() and hashes(base) == before
    records.append(dict(case='wrong SHA reports actual own worktree and creates no output',
                        returncode=result.returncode, stderr=result.stderr.decode(), preserved=True))

raw = dict(source_sha=SOURCE, script=str(SCRIPT), cases=records, status='PASS',
           executed_application=False, executed_native_input=False,
           git_script_sha256=hashlib.sha256(subprocess.check_output(
               ['git', '-C', str(ROOT), 'show', SOURCE+':tools/authoring/desktop_scaling_probe.py'])).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(raw, indent=2)+'\n', encoding='utf-8')
print('3 independent real CLI negatives PASS; no application started')
