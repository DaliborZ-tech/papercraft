"""Independent pinned bytes, XML geometry and native-editor readback audit."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
base = Path(__file__).resolve().parent
sha = '1d8ed8b9db95a7e225ad77fbaffe7b943ddec828'
prod = '7da240386550039761de6861d3149ce9ee1be466'
helper = '5741cf144116123b4a0cb3f1c84987443517662a'
rows = []
def check(name, ok, detail=None):
    rows.append(dict(name=name, passed=bool(ok), detail=detail))
def digest(b):
    return hashlib.sha256(b).hexdigest()
def blob(pin, path):
    return subprocess.check_output(['git', 'show', pin+':'+path])
def gitbytes(path):
    return blob(sha, path.relative_to(base.parents[3]).as_posix())
def load(path):
    data = path.read_bytes()
    check('git-bytes:'+path.name, data == gitbytes(path))
    return json.loads(data)
native = base/'pc006a-desktop-7da2403-run04'
editor = base/'pc006a-inkscape-5741cf1-run06'
n, e = load(native/'results.json'), load(editor/'editor-results.json')
check('source-pins-and-status', n['source_sha']==prod and e['source_sha']==helper and n['status']==e['status']=='PASS')
for directory, report in [(native,n),(editor,e)]:
    for name, expected in report['files_sha256'].items():
        path = directory/name
        check('output-bytes:'+directory.name+'/'+name, digest(path.read_bytes())==expected and path.read_bytes()==gitbytes(path))
for path, expected in n['source_files_sha256'].items():
    raw = blob(prod, path)
    check('native-source:'+path, expected in [digest(raw),digest(raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))])
raw = blob(helper, 'tools/authoring/editor_probe.py')
check('editor-helper-source', e['script_sha256'] in [digest(raw),digest(raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))])
check('helper-production-identical', not subprocess.check_output(['git','diff',prod,helper,'--','src','tests','pyproject.toml']))
for name, expected in e['origin_bundle_sha256'].items():
    check('original-bundle:'+name,digest((native/'export'/name).read_bytes())==expected)
check('raw-input-is-fresh-native-export',(editor/'editor-original.svg').read_bytes()==Path(e['origin_source']).read_bytes())
ns={'s':'http://www.w3.org/2000/svg'}
old,new = [ET.parse(editor/f'editor-{v}.svg').getroot() for v in ['original','edited']]
idx=lambda r:{v.attrib['id']:v for v in r.iter() if 'id' in v.attrib}
oi,ni=idx(old),idx(new)
pid=e['actual_inkscape_action_edits']['part_id']; lid=e['actual_inkscape_action_edits']['label_id']
check('all-original-ids-preserved',oi.keys()<=ni.keys())
check('page-metadata-unchanged',all(new.attrib[k]==v for k,v in old.attrib.items()))
check('seven-original-role-groups',len(old.find(f"s:g[@id='{pid}']",ns).findall('s:g',ns))==7 and all(ni[k].attrib.get('data-role')==v.attrib.get('data-role') for k,v in oi.items() if 'data-role' in v.attrib))
txt=lambda v:''.join(v.itertext())
target='\u017dlu\u0165ou\u010dk\xfd \u2013 vlastn\xed d\xedl'
check('exact-native-multiword-unicode',txt(ni[lid])==target==e['native_gui_text_edit']['text'])
check('other-texts-unchanged',all(txt(v)==txt(ni[k]) for k,v in oi.items() if v.tag.endswith('}text') and k!=lid))
check('native-edit-color','#b43d28' in (ni[lid].attrib.get('style','')+ni[lid].attrib.get('fill','')))
check('preserve-all-exported-text',all(v.attrib.get('{http://www.w3.org/XML/1998/namespace}space')=='preserve' for v in old.findall('.//s:text',ns)))
gui=e['native_gui_text_edit']
check('exact-own-foreground',gui['foreground_verified_before_each_chord'] and gui['own_hwnd']==e['initial_focus']['after_hwnd']==e['own_visible_windows'][0]['hwnd'] and gui['own_pid']>0)

def points(d):
    tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?',d)
    out=[];i=0;op=None;current=np.zeros(2)
    while i<len(tokens):
        if tokens[i].isalpha():op=tokens[i];i+=1
        if op.upper()=='Z':break
        upper=op.upper();assert upper in ['M','L','H','V'],op
        count=2 if upper in ['M','L'] else 1
        val=list(map(float,tokens[i:i+count]));i+=count
        nxt=current.copy()
        if count==2:nxt=np.array(val)+(current if op.islower() else 0)
        elif upper=='H':nxt[0]=val[0]+(current[0] if op.islower() else 0)
        else:nxt[1]=val[0]+(current[1] if op.islower() else 0)
        out.append(nxt.copy());current=nxt
        if upper=='M':op='l' if op.islower() else 'L'
    return np.array(out)
def matrix(s):
    total=np.eye(3)
    for op,text in re.findall(r'(\w+)\(([^)]+)\)',s or ''):
        v=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?',text)));m=np.eye(3)
        if op=='translate':m[:2,2]=v+[0] if len(v)==1 else v
        elif op=='rotate':
            c,s=math.cos(math.radians(v[0])),math.sin(math.radians(v[0]));m[:2,:2]=[[c,-s],[s,c]]
            if len(v)==3:m[:2,2]=np.array(v[1:])-m[:2,:2]@np.array(v[1:])
        elif op=='matrix':m=np.array([[v[0],v[2],v[4]],[v[1],v[3],v[5]],[0,0,1]])
        else:raise AssertionError(op)
        total=total@m
    return total
paths_old=old.findall('.//s:path',ns);paths_new=new.findall('.//s:path',ns)
check('all-path-counts',len(paths_old)==len(paths_new)==3)
areas=[]
for k,v in oi.items():
    if not v.tag.endswith('}path'):continue
    po,pn=points(v.attrib['d']),points(ni[k].attrib['d'])
    check('local-geometry:'+k,np.allclose(po,pn,rtol=0,atol=2e-5))
    areas.append(abs(sum(x[0]*y[1]-x[1]*y[0] for x,y in zip(pn,np.roll(pn,-1,axis=0))))/2)
    xy=np.c_[po,np.ones(len(po))].T
    delta=(matrix(ni[pid].attrib['transform'])@xy-matrix(oi[pid].attrib['transform'])@xy)[:2]
    check('native-group-translation:'+k,np.allclose(delta,np.array([[10],[15]])*25.4/96,rtol=0,atol=2e-5))
check('independent-cut-areas',sorted(areas)==[225.,3600.],list(map(float,areas)))
calold=old.find("s:g[@id='page-GUIDES']/s:path",ns);calnew=new.find("s:g[@id='page-GUIDES']/s:path",ns)
check('only-calibration-id-added',all(calnew.attrib[k]==v for k,v in calold.attrib.items()) and set(calnew.attrib)-set(calold.attrib)=={'id'} and calnew.attrib['id']=='path2')
check('100mm-calibration',np.linalg.norm(points(calnew.attrib['d'])[1]-points(calnew.attrib['d'])[0])==100)

# Same earlier native snapshot through the pinned fixed writer: geometry/PDF
# must be identical; XML differs only by the new text-preservation attributes.
sys.path.insert(0,str(a.source/'src'))
from archpapercraft.exporter import author_export
check('writer-module-source',Path(author_export.__file__).resolve().is_relative_to(a.source.resolve()))
prior=base/'pc006a-desktop-4b172e6-run03'
snapshot=json.loads((prior/'snapshot.json').read_text(encoding='utf8'))
out=Path(tempfile.mkdtemp(prefix='pc006a-review-c06-reexport-'))
files=author_export.export_all(snapshot,out)
for f in files:
    original=prior/'export'/f.name
    if f.suffix=='.pdf':check('same-snapshot-PDF-byte-identical',f.read_bytes()==original.read_bytes())
    else:
        fixed,previous=ET.parse(f).getroot(),ET.parse(original).getroot()
        for t in fixed.findall('.//s:text',ns):
            assert t.attrib.pop('{http://www.w3.org/XML/1998/namespace}space')=='preserve'
        check('same-snapshot-SVG-only-preserve:'+f.name,ET.tostring(fixed)==ET.tostring(previous))
report=dict(metadata_pin=sha,production_pin=prod,helper_pin=helper,results=rows,passed=sum(r['passed'] for r in rows),failed=sum(not r['passed'] for r in rows))
a.output.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
if report['failed']:print(json.dumps([r for r in rows if not r['passed']]))
raise SystemExit(bool(report['failed']))
