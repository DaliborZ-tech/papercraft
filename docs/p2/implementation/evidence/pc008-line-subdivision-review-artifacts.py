"""Pinned native/editor artifact audit; no GUI or production mutation."""
import ast,hashlib,io,json,math,re,subprocess,sys,tarfile,tempfile,xml.etree.ElementTree as ET
from fractions import Fraction as F
from pathlib import Path
import numpy as np
OWN=Path(__file__).resolve().parent
ROOT=Path(sys.argv[1]).resolve()
CODE='24e08019a711c5c7c19ca73a5ac35e5093dfb4d0'
META='93f650c4a22a9d1dffd3b65c69f4b9505d5889f7'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def pinned(relative):return git('show',META+':'+relative)
def read_json(path):
 relative=path.relative_to(ROOT).as_posix();raw=pinned(relative)
 assert raw.replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n'),relative
 return json.loads(raw)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert not git('diff','--name-only',CODE,META,'--','src','tools','tests','pyproject.toml').strip()
subprocess.run(['git','merge-base','--is-ancestor','6796c63dc6aee0cd8331feb22df4e1c4afd0df27',META],cwd=ROOT,check=True)
raw=git('archive','--format=tar',CODE,'src','tools/authoring','pyproject.toml')
archive=Path(tempfile.mkdtemp(prefix='pc008-line-artifact-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
 for member in tar.getmembers():assert (archive/member.name).resolve().is_relative_to(archive)
 tar.extractall(archive,filter='data')
sys.path.insert(0,str(archive/'src'))
from archpapercraft.authoring import AuthorProject,profile_subdivision,curve_subdivision
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions
modules={}
for m in (profile_subdivision,curve_subdivision,sys.modules[read_pdf_cut_regions.__module__]):
 path=Path(m.__file__);assert path.resolve().is_relative_to(archive)
 blob=git('show',CODE+':'+path.relative_to(archive).as_posix()).replace(b'\r\n',b'\n')
 assert blob==path.read_text(encoding='utf8').encode()
 modules[m.__name__]=dict(path=str(path),lf_sha256=hashlib.sha256(blob).hexdigest())
def area(points):return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2
def signature(text):
 tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',text)
 result=[];current=[F(0),F(0)];start=None;op=None;i=0
 while i<len(tokens):
  if tokens[i].isalpha():op=tokens[i];i+=1
  c=op.upper();relative=op.islower()
  if c=='Z':
   if result and result[-1][0]=='L' and list(result[-1][1:])==start:result.pop()
   result.append(('Z',));current=list(start);op=None;continue
  n={'M':2,'L':2,'H':1,'V':1}[c];q=list(map(F,tokens[i:i+n]));i+=n
  if c=='H':q=[q[0]+(current[0] if relative else 0),current[1]];c='L'
  elif c=='V':q=[current[0],q[0]+(current[1] if relative else 0)];c='L'
  elif relative:q=[x+y for x,y in zip(q,current)]
  result.append((c,*q));current=q[-2:]
  if c=='M':start=list(current);op='l' if relative else 'L'
 return result
def transform(text):
 result=np.eye(3)
 for name,body in re.findall(r'(translate|rotate|matrix|scale)\(([^)]+)\)',text or ''):
  q=[float(x) for x in re.split(r'[ ,]+',body.strip())];m=np.eye(3)
  if name=='translate':m[:2,2]=[q[0],q[1] if len(q)>1 else 0]
  elif name=='scale':m[0,0]=q[0];m[1,1]=q[-1]
  elif name=='matrix':m=np.array([[q[0],q[2],q[4]],[q[1],q[3],q[5]],[0,0,1.]])
  else:
   c,s=math.cos(math.radians(q[0])),math.sin(math.radians(q[0]));m[:2,:2]=[[c,-s],[s,c]]
   if len(q)==3:m[:2,2]=np.array(q[1:])-m[:2,:2]@q[1:]
  result=result@m
 return result
E=ROOT/'docs/p2/implementation/evidence'
folder=E/'pc008-AU13-line-desktop-24e0801-run05';r=read_json(folder/'results.json')
assert r['source_sha']==CODE and r['status']=='PASS_REQUESTED_FIXTURE' and not r['failures']
source_hashes={}
for path,digest in r['source_files_sha256'].items():
 blob=(archive/path).read_bytes();lf=blob.replace(b'\r\n',b'\n')
 match=[kind for kind,value in [('blob',blob),('LF',lf),('CRLF',lf.replace(b'\n',b'\r\n'))] if hashlib.sha256(value).hexdigest()==digest]
 assert match,path;source_hashes[path]=match
for path,digest in r['files_sha256'].items():assert sha(folder/path)==digest,path
assert Path(r['actual_application_module']).resolve()==(ROOT/'src/archpapercraft/ui/author_window.py').resolve()
assert len([d for d in r['dialogs'] if d.get('native_seen') and d.get('accepted')])==3
assert r['new_user']=='NOT_RUN' and r['physical_build']=='NOT_RUN'
model=folder/'AU13-line';data=read_json(model/'AU13-line.apcraft');snapshot=read_json(model/'snapshot.json')
p=AuthorProject.from_dict(data);assert p.to_dict()==data and json.loads(json.dumps(p.snapshot(),allow_nan=False))==snapshot
assert data['schema_version']==7 and len(p.surfaces)==3 and len(p.parts)==2 and len(p.profile_subdivisions)==2
assert all(s.kind=='planar' for s in p.surfaces.values()) and not p.segmented_variants
assert set(snapshot['coverage']['expected_part_ids'])==p.material_part_ids() and not snapshot['coverage']['reference_surface_ids']
step=next(x for x in r['steps'] if x['name']=='AU13_LINE_semantic_axis_join_trace_and_mixed_change')
body_id=step['part_id'];wall_id=p.parts[body_id].frame.root_surface_id;wall=p.profiles[p.surfaces[wall_id].profile_id]
base_id=next(x for x in p.parts if x!=body_id);place=p.placements[body_id]
assert (place.x_mm,place.y_mm,place.rotation_deg,place.position_locked,place.rotation_locked)==(60,60,30,True,True)
page_ids=[page.id for page in p.pages]
assert page_ids.index(place.page_id)==1
assert step['source_profile_id']==wall.id and p.parts[body_id].frame.axis_segment_id in p.profile_subdivisions
joint=p.joints[step['joint_id']];attachment=p.attachments[step['attachment_id']];connector=p.connectors[step['connector_id']]
assert not joint.unresolved and not attachment.unresolved and joint.mode=='fold'
assert joint.edge_a in p.profile_subdivisions and attachment.source_edge_id==p.parts[body_id].frame.axis_segment_id
assert attachment.source_interval==[0,1] and connector.width_mm==2 and connector.taper==.6 and connector.count==1 and connector.shape=='trapezoid' and not connector.tab_overrides
histories=[]
for root,record in p.profile_subdivisions.items():
 h=record['history'];active={root:(F(0),F(1))}
 for event in h['events']:
  if event[0]=='split':
   _,old,t,a,b=event;t=F(t);lo,hi=active.pop(old);middle=lo+t*(hi-lo);active[a]=(lo,middle);active[b]=(middle,hi)
  elif event[0]=='merge':
   _,ids,new=event;rows=[active[x] for x in ids]
   assert all(a[1]==b[0] for a,b in zip(rows,rows[1:]));active[new]=(rows[0][0],rows[-1][1])
   for x in ids:del active[x]
  else:raise AssertionError('Unexpected fixture geometry edit in source history')
 assert all(wall.segment(x) is not None for x in active)
 for segment,(lo,hi) in active.items():
  a,b=record['edges'][segment];source=h['source'];start,end=[tuple(map(F,source[k])) for k in ('start','end')]
  for vid,t in ((a,lo),(b,hi)):
   expected=[float(x+t*(y-x)) for x,y in zip(start,end)];assert wall.vertex(vid).point==expected
 histories.append(dict(root=root,event_kinds=[e[0] for e in h['events']],active_intervals={k:[str(x) for x in v] for k,v in active.items()}))
expected_wall=[(60+x*math.cos(math.pi/6)-y*math.sin(math.pi/6),60+x*math.sin(math.pi/6)+y*math.cos(math.pi/6)) for x,y in [(0,0),(100,0),(100,40),(0,40)]]
assert all(math.dist(a,b)<1e-10 for a,b in zip(expected_wall,step['original_wall_points']))
final=step['final_wall_points'];assert all(any(math.dist(a,b)<1e-10 for b in final) for a in expected_wall)
NS='{http://www.w3.org/2000/svg}';svgs=[model/f"export/page-{page['id']}.svg" for page in snapshot['pages']]
svg_areas={};path_ids=set()
for page_index,path in enumerate(svgs):
 root=ET.parse(path).getroot();assert root.get('width')=='210mm' and root.get('height')=='297mm'
 for group in root.findall(f'{NS}g[@data-part-id]'):
  pid=group.get('data-part-id');cut=group.find(f"{NS}g[@data-role='CUT']");assert len(cut)==1
  commands=signature(cut[0].get('d'));assert commands[-1][0]=='Z'
  svg_areas[pid]=area([c[1:] for c in commands if c[0] in ('M','L')])
  assert p.placements[pid].page_id==page_ids[page_index]
  path_ids.update(x.get('id') for x in group.iter(NS+'path'))
assert set(svg_areas)==p.material_part_ids()
pdf=read_pdf_cut_regions(model/'export/model.pdf')['parts'];assert set(pdf)==p.material_part_ids()
den=10**70;n=math.isqrt(2125*den*den);lo,hi=F(n,den),F(n+1,den)
expected={body_id:(F(4160)+100*lo,F(4160)+100*hi),base_id:(F(13000),F(13000))}
areas={}
for pid,limits in expected.items():
 assert len(pdf[pid]['loops'])==1
 commands=pdf[pid]['loops'][0];assert all(c[0] in ('M','L','Z') for c in commands)
 pdf_area=area([c[1:] for c in commands if c[0] in ('M','L')]);svg_area=svg_areas[pid]
 se=max(abs(svg_area-x) for x in limits);pe=max(abs(pdf_area-x) for x in limits)
 assert se<F(1,100) and pe<F(1,100)
 assert pdf[pid]['page_index']==page_ids.index(p.placements[pid].page_id)
 areas[pid]=dict(source_area_interval=[str(x) for x in limits],svg_area_exact=str(svg_area),pdf_area_exact=str(pdf_area),svg_error_upper=float(se),pdf_error_upper=float(pe))
manifest=read_json(model/'export/.author-export.json');canonical=dict(snapshot);canonical.pop('metadata',None)
assert hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()==manifest['snapshot_digest']
editors=[]
for page_index in (1,2):
 f=E/f'pc008-AU13-line-inkscape-24e0801-page{page_index}-run01';e=read_json(f/'editor-results.json')
 assert e['source_sha']==CODE and e['status']=='PASS'
 assert e['script_sha256']==hashlib.sha256((archive/'tools/authoring/editor_probe.py').read_bytes()).hexdigest()
 for name,digest in e['files_sha256'].items():assert sha(f/name)==digest,name
 original=Path(e['origin_source']);assert sha(original)==sha(f/'editor-original.svg')
 for name,digest in e['origin_bundle_sha256'].items():assert sha(original.parent/name)==digest
 a,b=[ET.parse(f/name).getroot() for name in ('editor-original.svg','editor-edited.svg')]
 assert all(a.get(k)==b.get(k) for k in ('width','height','viewBox'))
 aa={x.get('id'):x for x in a.iter() if x.get('id')};bb={x.get('id'):x for x in b.iter() if x.get('id')}
 changes=e['actual_inkscape_action_edits'];label=changes['label_id'];part=changes['part_id']
 assert ''.join(bb[label].itertext())=='\u017dlu\u0165ou\u010dk\u00fd \u2013 vlastn\u00ed d\u00edl'
 assert '#b43d28' in bb[label].get('style','')
 drift=F(0)
 for id,x in aa.items():
  if x.tag==NS+'path':
   first,last=signature(x.get('d')),signature(bb[id].get('d'));assert len(first)==len(last)
   for c,d in zip(first,last):
    assert c[0]==d[0];delta=max((abs(v-w) for v,w in zip(c[1:],d[1:])),default=F(0));drift=max(drift,delta);assert delta<=F(1,50000)
  if x.tag==NS+'text' and id!=label:assert ''.join(x.itertext())==''.join(bb[id].itertext())
 ca,cb=[signature(root.find(f"{NS}g[@id='page-GUIDES']/{NS}path").get('d')) for root in (a,b)]
 assert ca==cb and (ca[1][1]-ca[0][1])**2+(ca[1][2]-ca[0][2])**2==10000
 before,after=transform(aa[part].get('transform')),transform(bb[part].get('transform'))
 assert np.max(np.abs(after[:2,:2]-before[:2,:2]))<2e-7
 assert np.max(np.abs(after[:2,2]-before[:2,2]-np.array([10,15])*25.4/96))<2e-5
 assert e['native_gui_text_edit']['foreground_verified_before_each_chord'] and e['origin_bundle_preserved_after_run']
 editors.append(dict(page=page_index,elapsed=e['elapsed_seconds'],artifact_hashes=len(e['files_sha256']),path_count=len([x for x in aa.values() if x.tag==NS+'path']),maximum_local_drift=float(drift),origin_bytes_preserved=True,unicode_text=''.join(bb[label].itertext())))
suite=pinned('docs/p2/implementation/evidence/au13-line-full-suite-24e0801-run05.xml');doc=ET.fromstring(suite);cases=list(doc.iter('testcase'))
assert len(cases)==1465 and not any(any(e.tag in ('failure','error','skipped') for e in case) for case in cases)
seconds=float(next(doc.iter('testsuite')).get('time'));assert abs(seconds-326.23)<.02
rawlog=pinned('docs/p2/implementation/evidence/au13-line-full-suite-24e0801-run05.log');log=rawlog.decode('utf16' if rawlog.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');assert '1465 passed' in log
historical=[]
for prefix in ('9b87c89','9290a01','a770f8a'):
 path=next(E.glob(f'pc008-AU13-line-desktop-{prefix}-run*/results.json'));h=read_json(path);assert h['status']=='FAIL'
 historical.append(dict(folder=path.parent.name,status=h['status'],source=h['source_sha'],error=h.get('error','')[-900:],original_command_trace=h.get('observed_command_exceptions',[])))
queue=json.loads(pinned('05_WORK_QUEUE.json'));assert queue['release_readiness'].startswith('NOT_READY')
assert all(t['status']!='COMPLETE' for t in queue['tickets'] if t['id'] in ('PC-008','PC-009','PC-010'))
line=next(t for t in queue['tickets'] if t['id']=='PC-008')['live_LINE_progress_2026_11_11'];assert line['code_sha']==CODE
out=dict(status='PASS_LINE_TECHNICAL_INCREMENT_ARTIFACT_AUDIT_NOT_WHOLE_AU13_P2',source_sha=CODE,metadata_sha=META,archive_sha256=hashlib.sha256(raw).hexdigest(),archive_directory=str(archive),actual_imports=modules,runtime_identical=True,source_hashes=len(source_hashes),artifact_hashes=len(r['files_sha256']),native_seconds=r['elapsed_seconds'],actual_native_dialogs=3,histories=histories,areas=areas,editors=editors,suite=dict(tests=1465,failures=0,errors=0,skips=0,seconds=seconds),historical_failures=historical,new_user='NOT_RUN_0',physical='NOT_RUN_P3')
(OWN/'pc008-line-subdivision-review-artifacts-24e0801.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(out,ensure_ascii=True,indent=2))
