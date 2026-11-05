"""Read-only structural checks of the P0/P1 delivery and proposal."""
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
queue = json.loads((root/'05_WORK_QUEUE.json').read_text(encoding='utf-8-sig'))
ids = [t['id'] for t in queue['tickets']]
assert len(ids)==len(set(ids))==12
by_id = {t['id']:t for t in queue['tickets']}
visiting,done=set(),set()
def visit(key):
    assert key not in visiting, f'Cycle: {key}'
    if key in done:return
    visiting.add(key)
    for dep in by_id[key]['depends_on']:
        assert dep in by_id
        visit(dep)
    visiting.remove(key)
    done.add(key)
for key in ids:visit(key)
ac_text = (root/'04_ACCEPTANCE_AND_VERIFICATION.md').read_text(encoding='utf-8')
acs = re.findall(r'^\| (AC-\w\d+) \|',ac_text,re.M)
assert len(acs)==len(set(acs))==61
trace = (root/'docs/revival/TRACEABILITY.md').read_text(encoding='utf-8')
for ac in acs:assert f'| {ac} |' in trace,ac
for n in range(1,17):assert f'| E{n:02d} |' in trace
for ticket in queue['tickets']:
    for ac in ticket['acceptance']:
        if ac.startswith('AC-'):assert ac in acs,ac
    if ticket['stage'] not in ['P0','P1']:assert not ticket['execution_authorized_on_realization']
    for path in ticket.get('evidence',[]):
        if path.endswith('REVIEW_REPORT.md'):continue
        assert (root/path).exists(),path
assert queue['product_gate']['auto_approve'] is False
html=(root/'docs/revival/ux-prototype.html').read_text(encoding='utf-8')
script=re.search(r'<script>(.*?)</script>',html,re.S).group(1)
syntax=subprocess.run(['node','--check','--input-type=commonjs'],input=script,text=True,encoding='utf-8',capture_output=True)
assert syntax.returncode==0,syntax.stderr
for state in ['empty','house','joint','stale','collision','export']:
    assert f'{state}:{{' in script
    assert f'data-state="{state}"' in html
for name,expected in [('pytest-baseline.xml',(213,0)),('core-only.xml',(44,0)),('diagnostic-contracts.xml',(6,6))]:
    suites=ET.parse(root/'docs/revival/evidence'/name).getroot().findall('testsuite')
    actual=(sum(int(s.attrib['tests']) for s in suites),sum(int(s.attrib['failures']) for s in suites))
    assert actual==expected,(name,actual)
production=subprocess.run(['git','diff','d689af67e059512fdc99e85e9eb0b8d432f4c5d4','--','src','tests','pyproject.toml'],cwd=root,capture_output=True,text=True)
assert production.returncode==0 and not production.stdout,'Production changed before P2 gate'
print('PASS: 12-ticket DAG, 61 AC, 16 epics, P0/P1 authorization, 6 UX states/JS syntax, evidence counts, unchanged production')
