"""Pinned Git-object metadata audit, without another product test run."""
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN='71f7b16e4eb220f327a5285321fee8f8b0f45d25'
BASE='63ab275a5fe9b92bdb370a5ec3dedf1c5f70a65e'
PREVIOUS='92978e16628d165b404ea7d58e88449fef7b8aa5'
E='docs/p2/implementation/evidence/'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blobs(paths):
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
                                input=('\n'.join(PIN+':'+p for p in paths)+'\n').encode())
    result={};offset=0
    for path in paths:
        end=raw.index(b'\n',offset);header=raw[offset:end].split();assert header[1]==b'blob'
        size=int(header[2]);offset=end+1
        result[path]=raw[offset:offset+size];offset+=size+1
    assert offset==len(raw)
    return result

protected=['src','tools','pyproject.toml','AGENTS.md','02_CODEX_MANDATE.md','03_EPICS_AND_ROADMAP.md',
           '04_ACCEPTANCE_AND_VERIFICATION.md','docs/p2/v1.2']
assert not git('diff',BASE,PIN,'--',*protected)
delta=git('diff','--name-only',BASE,PIN).decode().splitlines()
last_delta=git('diff','--name-only',PREVIOUS,PIN).decode().splitlines()
assert last_delta==['docs/p2/SKILL_IMPROVEMENTS.json']
paths=['05_WORK_QUEUE.json','docs/p2/SKILL_IMPROVEMENTS.json','.agents/skills/papercraft-verification/SKILL.md',
       'docs/p2/implementation/PC007A_PLANAR_DELIVERY.md','00_START_HERE.md',
       E+'pc007a-planar-final-artifact-review-63ab275.json',E+'pc007a-desktop-63ab275-run04/results.json',
       E+'pc007a-inkscape-63ab275-page1-run03/editor-results.json',E+'pc007a-inkscape-63ab275-page2-run04/editor-results.json',
       E+'pc007a-suite-63ab275-run03.xml']
data=blobs(paths)
q=json.loads(data['05_WORK_QUEUE.json']);ledger=json.loads(data['docs/p2/SKILL_IMPROVEMENTS.json'])
tickets={t['id']:t for t in q['tickets']};current=tickets['PC-007A']
assert current['status']=='IN_PROGRESS' and current['implementation_progress']['whole_ticket_complete'] is False
assert current['reviewed_code_sha']==BASE
assert 'NOT_RUN_END_TO_END' in current['acceptance_state']['AC-AU09']
assert all('PARTIAL' in current['acceptance_state'][ac] for ac in ('AC-AU08','AC-AU13','AC-AU15'))
assert all('no novice observation' in current['acceptance_state']['AC-US0'+str(i)] for i in range(1,8))
for tid in ('PC-007B','PC-008','PC-009','PC-010'):assert tickets[tid]['status']=='PLANNED'
assert q['product_gate']['status']=='PO_ACCEPTED' and q['product_gate']['contract_version']=='1.2'
assert q['cross_cutting_usability']['participants_observed']==0
assert q['cross_cutting_usability']['first_author_test_status']=='NOT_RUN'
assert q['release_readiness'].startswith('NOT_READY') and q['p2_digital_delivery'].startswith('IN_PROGRESS')
assert q['current_delivery']['planar_verified_slice']['whole_PC007A_complete'] is False
assert q['current_delivery']['planar_verified_slice']['novice_participants']==0
assert q['current_delivery']['planar_verified_slice']['physical_proof']=='NOT_RUN_P3'
entries={e['id']:e for e in ledger['entries']}
for key in ('SK-009','SK-010','SK-011'):assert entries[key]['effectiveness']=='PENDING_NEXT_USE'
assert entries['SK-009']['next_use']['source_sha']=='61168e0879157baba1193785b9856f24d1d1c959'
assert entries['SK-009']['next_use']['broader_transfer']=='PENDING_NEXT_USE'
assert entries['SK-010']['next_use']['broader_transfer']=='PENDING_NEXT_USE'
assert entries['SK-011']['next_use']['status']=='NOT_RUN'
assert entries['SK-011']['product_correction']['source_sha']=='3252544850c0d4a9c4465de8f359ec2a5350af27'
assert entries['SK-011']['independent_review']['status']=='PENDING_METADATA_REVIEW'
skill=data['.agents/skills/papercraft-verification/SKILL.md'].decode()
assert 'Odvozený chybový odhad nenahrazuje další normativní přejímku.' in skill
assert 'délková chyba extruze se násobí hloubkou' in skill
assert 'celý řetězec source→výstup proti původní mezi' in skill

# Every local owner-facing link is included in this exact commit.
tracked=set(git('ls-tree','-r','--name-only',PIN).decode().splitlines())
missing=[];checked_links=[]
for path in ('00_START_HERE.md','docs/p2/implementation/PC007A_PLANAR_DELIVERY.md'):
    for target in re.findall(r'\]\(([^)]+)\)',data[path].decode('utf8')):
        if '://' in target or target.startswith('#'):continue
        relative=(Path(path).parent/target.split('#',1)[0]).as_posix()
        # Pure path normalization without depending on mutable working files.
        parts=[]
        for part in relative.split('/'):
            if part=='..':parts.pop()
            elif part!='.':parts.append(part)
        resolved='/'.join(parts);checked_links.append(resolved)
        if resolved not in tracked:missing.append(resolved)
assert not missing,missing

run=json.loads(data[E+'pc007a-desktop-63ab275-run04/results.json'])
final=json.loads(data[E+'pc007a-planar-final-artifact-review-63ab275.json'])
assert final['source_sha']==run['source_sha']==BASE
assert final['V02']=='CLOSED_ON_ACTUAL_NATIVE_SOURCE63_ARTIFACT'
assert final['verdict']=='APPROVED_IN_BOUNDED_PLANAR_AUTHORING_SLICE_SCOPE'
assert final['wall_net_error_mm2']<final['wall_net_limit_mm2']
assert final['hole_error_mm2']<.01
assert run['status']=='PASS_REQUESTED_FIXTURE'
assert all(json.loads(data[E+folder+'/editor-results.json'])['status']=='PASS' for folder in ('pc007a-inkscape-63ab275-page1-run03','pc007a-inkscape-63ab275-page2-run04'))
suite=ET.fromstring(data[E+'pc007a-suite-63ab275-run03.xml']);suites=list(suite.iter('testsuite'))
assert sum(int(s.attrib['tests']) for s in suites)==908
assert sum(int(s.attrib.get(k,0)) for s in suites for k in ('failures','errors','skipped'))==0

def matches(digest,raw):
    candidates={hashlib.sha256(raw).hexdigest()}
    # Git normalizes text checkout EOL; binary records must retain exact bytes.
    if b'\0' not in raw:
        lf=raw.replace(b'\r\n',b'\n')
        candidates|={hashlib.sha256(lf).hexdigest(),hashlib.sha256(lf.replace(b'\n',b'\r\n')).hexdigest()}
    return digest in candidates

nativeprefix=E+'pc007a-desktop-63ab275-run04/'
published=blobs([nativeprefix+name for name in run['files_sha256']])
assert all(matches(digest,published[nativeprefix+name]) for name,digest in run['files_sha256'].items())
out={'metadata_sha':PIN,'previous_metadata_sha':PREVIOUS,'reviewed_code_sha':BASE,
     'protected_paths_unchanged':protected,'delta_file_count':len(delta),'reviewed_metadata_objects_sha256':{p:hashlib.sha256(v).hexdigest() for p,v in data.items()},
     'local_document_links_checked':len(checked_links),'missing_links':missing,'published_native_artifacts_rebound':len(published),
     'full_suite':{'passed':908,'failures':0,'errors':0,'skipped':0},'whole_PC007A':'IN_PROGRESS','P2':'IN_PROGRESS_NOT_READY',
     'novice_participants':0,'physical':'NOT_RUN_P3','SK009_transfer_source':entries['SK-009']['next_use']['source_sha'],
     'SK009_SK010_broader_effectiveness':'PENDING_NEXT_USE','SK011_skill_effectiveness':'PENDING_NEXT_USE; no next ticket use observed',
     'SK011_metadata_review':'APPROVED_IN_SCOPE_BY_THIS_REPORT; ledger truth update may follow',
     'verdict':'APPROVED_IN_PLANAR_METADATA_PUBLICATION_SCOPE','open_blocker_major':0}
(ROOT/E/'pc007a-planar-metadata-review-71f7b16.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in out.items() if k!='reviewed_metadata_objects_sha256'},indent=2))
