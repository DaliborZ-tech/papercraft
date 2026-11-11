"""Read-only audit of actual native input, with no Qt app or runtime imports."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
NATIVE = Path('C:/Users/dalib/projects/papercraft-c-integrated-authoring/docs/p2/implementation/evidence/pc009-C-cylinder-qt150-65b6dae-run02')
SHA = '65b6dae843fe2ec74bb76aa884c1c7afaf826828'

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

result = json.loads((NATIVE/'results.json').read_text(encoding='utf-8'))
trace = json.loads((NATIVE/'scaling-observations.json').read_text(encoding='utf-8'))
events = trace['events']
assert result['source_sha'] == SHA and result['status'] == 'FAIL'
assert len(events) < 20000 and not any('observation_error' in e for e in events)
wheel = [e for e in events if e['type'] == 'Wheel'][-2:]
pan = events[-3:]
assert all(e['type'] in ('MouseButtonPress', 'MouseMove', 'MouseButtonRelease') for e in pan)
press = pan[0]
origin = [g-l for g, l in zip(press['global_point'], press['local_point'])]
assert press['button'] == 4 and wheel[0]['target_class'] == 'QWindow'
assert all(e['paper_transform'] == press['paper_transform'] for e in wheel+pan)
assert all(e['paper_center'] == press['paper_center'] for e in wheel+pan)
assert wheel[0]['global_point'][0] < origin[0]
diff = git('diff', '--name-only', '8f1ec6382d527c719133958e7eb6f78a724ef5d5', SHA, '--', 'src', 'pyproject.toml').decode()
assert diff == ''
payload = dict(
    reviewed_source_sha=SHA, src_vs_8f_diff=diff,
    probe_git_blob_sha256=hashlib.sha256(git('show', SHA+':tools/authoring/desktop_scaling_probe.py')).hexdigest(),
    raw_files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [NATIVE/'results.json', NATIVE/'scaling-observations.json']},
    native_status=result['status'], events=len(events), counts=dict(Counter(e['type'] for e in events)),
    screens=trace['actual_screens'], last_wheel=wheel, last_pan=pan,
    inferred_viewport_global_origin_from_press=origin,
    intended_window_center_from_observed_wheel_times_DPR=[x*1.5 for x in wheel[0]['local_point']],
    interpretation='Actual wheel global x lies left of paper viewport; no product-wheel failure established. Pan may clamp: scroll ranges and unique receiver identity were not recorded.',
    observed_new_users=0, os_scaling_certification='NOT_RUN', normative_ac_changed=False)
out = Path(__file__).with_name('pc009-scaling-review-65b6dae-run01.json')
out.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(output=str(out), events=len(events), hashes=payload['raw_files']), indent=2))
