"""Read-only default-label bbox and pinned delivery/skills audit."""
import json,subprocess,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent;ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else OWN.parents[3]
CODE='e7826dd9b8b90843cdba72a6ae6fd52f0936a1ea';META='89a14c57bab917d03ec3f63e6ada1ce04a89d0bb'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(path):return git('show',META+':'+path)
norm=['AGENTS.md','02_CODEX_MANDATE.md','03_EPICS_AND_ROADMAP.md','04_ACCEPTANCE_AND_VERIFICATION.md','docs/p2/v1.2']
assert not git('diff','--name-only',CODE,META,'--',*norm).strip()
delta=git('diff','--name-only','56152164152e438a37ac6c4f4a599349260c0d34',META).decode().splitlines()
assert delta==['05_WORK_QUEUE.json']
q=json.loads(blob('05_WORK_QUEUE.json'));assert q['release_readiness'].startswith('NOT_READY')
assert 'D/B3' in q['current_delivery']['next_required_technical_work']
assert all(t['status'] in ('IN_PROGRESS','PLANNED') for t in q['tickets'] if t['id'] in ('PC-007B','PC-008','PC-009','PC-010'))
skills=json.loads(blob('docs/p2/SKILL_IMPROVEMENTS.json'));entries={e['id']:e for e in skills['entries']}
for id in ('SK-011','SK-013','SK-014'):assert entries[id]['effectiveness']=='PENDING_NEXT_USE'
assert entries['SK-013']['next_use']['status']==entries['SK-014']['next_use']['status']=='NOT_RUN'
assert 'numeric comparator' in entries['SK-011']['d_transfer_2026_11_11']['limitations']
assert '268' in entries['SK-011']['d_transfer_2026_11_11']['limitations'] and '5ad' in entries['SK-011']['d_transfer_2026_11_11']['limitations']
assert entries['SK-011']['additional_advice']['effectiveness']=='PENDING_NEXT_USE'
pages=[]
for path in (ROOT/'docs/p2/implementation/evidence').glob('pc008-D-*-inkscape-e7826dd-page*-run01/editor-results.json'):
 r=json.loads(blob(path.relative_to(ROOT).as_posix()))
 command=next(c for c in r['commands'] if '--query-all' in c['command'] and any('editor-original.svg' in arg for arg in c['command']))
 bounds={}
 for line in command['stdout'].splitlines():
  parts=line.split(',')
  if len(parts)!=5:continue
  try:bounds[parts[0]]=tuple(map(float,parts[1:]))
  except ValueError:pass
 import xml.etree.ElementTree as ET
 ns='{http://www.w3.org/2000/svg}';root=ET.parse(path.parent/'editor-original.svg').getroot()
 labels=[]
 for group in root.findall(f'{ns}g[@data-part-id]'):
  if group.get('data-flattening-mode')!='APPROXIMATE':continue
  texts=list(group.iter(f'{ns}text'));assert len(texts)==1
  text=texts[0];assert ''.join(text.itertext()).startswith('P') and ''.join(text.itertext())[1:].isdigit()
  labels.append((text.get('id'),bounds[text.get('id')]))
 overlaps=[]
 for i,(a,ba) in enumerate(labels):
  for b,bb in labels[i+1:]:
   width=min(ba[0]+ba[2],bb[0]+bb[2])-max(ba[0],bb[0]);height=min(ba[1]+ba[3],bb[1]+bb[3])-max(ba[1],bb[1])
   if width>1e-6 and height>1e-6:overlaps.append((a,b))
 assert not overlaps,overlaps
 pages.append(dict(folder=path.parent.name,generated_labels=len(labels),positive_label_bbox_overlaps=0,
  max_actual_label_width_mm=max(b[2] for _,b in labels)*25.4/96,
  evidence='Actual Inkscape query-all of untouched original SVG; 96px/in physical conversion'))
assert sorted(p['generated_labels'] for p in pages)==[32,32,48,48]
out=dict(source_sha=CODE,metadata_sha=META,normative_acceptance_unchanged=True,mechanical_metadata_delta=delta,
 labels=pages,DU02='CLOSED_IN_ACTUAL_LINE_AND_GOTHIC_DEFAULT_LAYOUT_VECTOR_SCOPE',
 skills={'SK013':'APPROVED_TEXT_SCOPE; NEXT_USE_NOT_RUN','SK014':'APPROVED_LABEL_ADVICE_AND_CURRENT_REPAIR_SCOPE; OTHER_TYPES_PENDING',
 'SK011_SO01':'APPROVED_BODY_ONLY_ADVICE_AND_BOUNDED_D_TRANSFER; COMPARATOR_ONLY_NEGATIVE_NOT_DOMAIN_FALSE_SAFE'},
 limitations='No novice/physical or whole PC008/P2 acceptance. Pending independent status fields may be truthfully updated to this review only.')
(OWN/'pc008-integration-review-labels-metadata.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print(json.dumps(out,indent=2))
