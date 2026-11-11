"""Final pinned native/editor/artifact and metadata audit, never opens a GUI."""
import hashlib,json,math,re,subprocess,sys,xml.etree.ElementTree as ET
from fractions import Fraction as F
from pathlib import Path
import numpy as np
OWN=Path(__file__).resolve().parent;ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else OWN.parents[3]
CODE='e7826dd9b8b90843cdba72a6ae6fd52f0936a1ea';META='89a14c57bab917d03ec3f63e6ada1ce04a89d0bb'
candidate=json.loads((OWN/'pc008-integration-review-candidate-e782.json').read_text())
archive=Path(candidate['isolated_directory']);assert candidate['source_sha']==CODE
sys.path.insert(0,str(archive/'src'))
from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions
from archpapercraft.exporter.svg_curve_validation import read_svg_cut_regions
from archpapercraft.exporter.segmented_output_validation import validate_segmented_snapshot,validate_segmented_vector_outputs
from archpapercraft.exporter.author_export import _curve_output_expectations
NS='{http://www.w3.org/2000/svg}';E=ROOT/'docs/p2/implementation/evidence'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
assert not git('diff','--name-only',CODE,META,'--','src','tools','pyproject.toml').strip()
def pinned(relative):return git('show',META+':'+relative)
def report_json(path):return json.loads(pinned(path.relative_to(ROOT).as_posix()))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def area(points):return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2
def polynomial_green(commands):
 total=F(0);current=None;start=None
 def segment(controls):
  if len(controls)==2:coeff=[controls[0],tuple(b-a for a,b in zip(*controls))]
  else:
   a,b,c,d=controls
   coeff=[a,tuple(3*(y-x) for x,y in zip(a,b)),tuple(3*(z-2*y+x) for x,y,z in zip(a,b,c)),tuple(w-3*z+3*y-x for x,y,z,w in zip(a,b,c,d))]
  return sum((x[0]*j*y[1]-x[1]*j*y[0])/F(i+j) for i,x in enumerate(coeff) for j,y in enumerate(coeff) if j)/2
 for c in commands:
  if c[0]=='M':current=tuple(c[1:]);start=current
  elif c[0]=='L':end=tuple(c[1:]);total+=segment([current,end]);current=end
  elif c[0]=='C':controls=[current,*[tuple(c[i:i+2]) for i in (1,3,5)]];total+=segment(controls);current=controls[-1]
  elif c[0]=='Z':total+=segment([current,start]);current=start
  else:raise AssertionError('Unexpected actual PDF polynomial opcode '+c[0])
 return abs(total)
def signature(value):
 tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',value)
 current=[F(0),F(0)];start=None;result=[];command=None;i=0
 while i<len(tokens):
  if tokens[i].isalpha():command=tokens[i];i+=1
  c=command.upper();relative=command.islower()
  if c=='Z':
   if result and result[-1][0]=='L' and list(result[-1][1:])==start:result.pop()
   result.append(('Z',));current=list(start);command=None;continue
  n={'M':2,'L':2,'H':1,'V':1,'C':6,'A':7}[c];q=list(map(F,tokens[i:i+n]));assert len(q)==n;i+=n
  if c=='H':q=[q[0]+(current[0] if relative else 0),current[1]];c='L'
  elif c=='V':q=[current[0],q[0]+(current[1] if relative else 0)];c='L'
  elif relative:
   for j in ([5] if c=='A' else range(0,n,2)):q[j]+=current[0];q[j+1]+=current[1]
  result.append((c,*q));current=q[-2:]
  if c=='M':start=list(current);command='l' if relative else 'L'
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
def source_point(profile,segment_id,t):
 segment=next(s for s in profile.segments if s.id==segment_id)
 a=profile.vertex(segment.start_vertex_id).point;b=profile.vertex(segment.end_vertex_id).point
 if segment.kind=='line':point=[(1-t)*x+t*y for x,y in zip(a,b)]
 else:
  assert segment.kind=='arc';cx,cy=segment.data['center'];angle=math.radians(segment.data['sweep_deg'])*t
  x,y=a[0]-cx,a[1]-cy;point=[cx+x*math.cos(angle)-y*math.sin(angle),cy+x*math.sin(angle)+y*math.cos(angle)]
 return [(profile.plane.origin[i]+profile.plane.u[i]*point[0]+profile.plane.v[i]*point[1])*.01 for i in range(3)]
def source_green(profile):
 total=0.
 for segment in profile.segments:
  a=profile.vertex(segment.start_vertex_id).point;b=profile.vertex(segment.end_vertex_id).point
  if segment.kind=='line':total+=(a[0]*b[1]-a[1]*b[0])/2
  else:
   cx,cy=segment.data['center'];r2=(a[0]-cx)**2+(a[1]-cy)**2
   total+=(cx*(b[1]-a[1])-cy*(b[0]-a[0])+r2*math.radians(segment.data['sweep_deg']))/2
 return abs(total)*.0001
native_results={};all_area=[]
for kind,count,paired in [('line',64,84),('gothic',96,96)]:
 folder=E/f'pc008-D-{kind}-desktop-e7826dd-run01';r=report_json(folder/'results.json')
 assert r['source_sha']==CODE and r['status']=='PASS_REQUESTED_FIXTURE' and not r['failures']
 for path,digest in r['source_files_sha256'].items():
  raw=(archive/path).read_bytes();assert digest in {hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),hashlib.sha256(raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')).hexdigest()},path
 for path,digest in r['files_sha256'].items():assert sha(folder/path)==digest,path
 model=folder/('D-segmented' if kind=='line' else 'D-gothic');raw=json.loads((model/(model.name+'.apcraft')).read_text(encoding='utf8'))
 p=AuthorProject.from_dict(raw);snapshot=json.loads((model/'snapshot.json').read_text(encoding='utf8'));assert json.loads(json.dumps(p.snapshot(),allow_nan=False))==snapshot
 assert snapshot['construction_checks']['segmented_source_project']==raw
 v=next(iter(p.segmented_variants.values()));target=p.surfaces[v.target_surface_id];first,second=[p.profiles[pid] for pid in target.source_profile_ids()]
 assert len(v.triangle_bindings)==count and len(v.paired_seams)==paired and p.loft_status(target.id)['status']=='REJECTED'
 assert len(p.material_part_ids())==count+(2 if kind=='gothic' else 0) and len(p.surfaces)==count+(3 if kind=='gothic' else 1)
 svgs=[model/f"export/page-{page['id']}.svg" for page in snapshot['pages']];pdf=model/'export/model.pdf'
 expected=_curve_output_expectations(snapshot);svg={};labels={}
 for page_index,path in enumerate(svgs):
  local={pid:e for pid,e in expected.items() if e['page_index']==page_index};svg.update(read_svg_cut_regions(path,local)['parts'])
  for group in ET.parse(path).getroot().findall(f'{NS}g[@data-part-id]'):
   labels[group.get('data-part-id')]=[''.join(t.itertext()) for t in group.iter(f'{NS}text')]
 actual_pdf=read_pdf_cut_regions(pdf)['parts'];assert set(svg)==set(actual_pdf)==p.material_part_ids()
 closure=validate_segmented_snapshot(snapshot);guard=validate_segmented_vector_outputs(snapshot,svgs,pdf,expected_parts=expected)
 assert len(closure)==len(guard['parts'])==count and guard['status']=='VERIFIED'
 assert all(row['area_budget_basis']=='SOURCE_PLANE_BODY_ONLY_EXCLUDES_CONNECTORS' for row in guard['parts'].values())
 areas=[]
 for row,triangle in zip(v.triangle_bindings,v.certificate['math']['triangles']):
  world=[];ref=target.params['correspondences'][triangle['patch_index']]
  for uv in triangle['parameter_vertices_exact']:
   u,w=map(float,map(F,uv))
   if kind=='line':point=(40*u,20*u*w,30*w)
   else:
    ends=[]
    for side,profile in [('first',first),('second',second)]:
     a,b=ref[side+'_interval'];ends.append(source_point(profile,ref[side+'_segment_id'],a+(b-a)*u))
    point=[(1-w)*a+w*b for a,b in zip(*ends)]
   world.append(point)
  a,b=[np.array(q)-world[0] for q in world[1:]];want=float(np.linalg.norm(np.cross(a,b)))/2
  pid=row['part_id'];s=area([c[1:] for c in svg[pid]['loops'][0] if c[0] in ('M','L')]);d=area([c[1:] for c in actual_pdf[pid]['loops'][0] if c[0] in ('M','L')])
  assert abs(float(s)-want)<.01 and abs(float(d)-want)<.01
  assert p.parts[pid].name==f'P{p.parts[pid].number}' and labels[pid]==[p.parts[pid].name]
  assert actual_pdf[pid]['page_index']==svg[pid]['page_index']
  areas.append(dict(part_id=pid,svg_error=abs(float(s)-want),pdf_error=abs(float(d)-want)))
 walls=[]
 if kind=='gothic':
  for surface in p.surfaces.values():
   if not surface.hole_profile_ids:continue
   assert len(surface.hole_profile_ids)==1
   hole=p.profiles[surface.hole_profile_ids[0]];outer=p.profiles[surface.profile_id]
   assert hole.id in target.source_profile_ids() and len(svg[surface.part_id]['loops'])==len(actual_pdf[surface.part_id]['loops'])==2
   want=source_green(outer)-source_green(hole)
   # Actual SVG Green integral is independently read with the previously audited oracle.
   sys.path.insert(0,str(archive/'tools/authoring'));from vector_curve_oracle import svg_signed_area
   group=next(g for path in svgs for g in ET.parse(path).getroot().findall(f'{NS}g[@data-part-id]') if g.get('data-part-id')==surface.part_id)
   cut=next(g for g in group if g.get('data-role')=='CUT');aa=[abs(svg_signed_area(path.get('d'))) for path in cut]
   net=max(aa)-(sum(aa)-max(aa));assert abs(net-want)<.01
   pdf_areas=[polynomial_green(loop) for loop in actual_pdf[surface.part_id]['loops']]
   pdf_net=max(pdf_areas)-(sum(pdf_areas)-max(pdf_areas))
   assert abs(float(pdf_net)-want)<.01 and abs(float(min(pdf_areas))-source_green(hole))<.01
   walls.append(dict(part_id=surface.part_id,hole_profile_id=hole.id,source_net_area=want,actual_svg_net_area=net,actual_pdf_net_area=float(pdf_net),hole_area=source_green(hole),actual_pdf_hole_area=float(min(pdf_areas))))
  assert len(walls)==2
 manifest=json.loads((model/'export/.author-export.json').read_text(encoding='utf8'))
 canonical=dict(snapshot);canonical.pop('metadata',None)
 assert hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()==manifest['snapshot_digest']
 assert len([x for x in r['dialogs'] if x.get('native_seen') and x.get('accepted')])==3
 native_results[kind]=dict(elapsed=r['elapsed_seconds'],source_hashes=len(r['source_files_sha256']),artifact_hashes=len(r['files_sha256']),
  source_surfaces=len(p.surfaces),printed_parts=len(p.material_part_ids()),triangles=count,paired_seams=paired,
  page_parts=[sum(e['page_index']==i for e in expected.values()) for i in range(2)],max_svg_area_error=max(x['svg_error'] for x in areas),max_pdf_area_error=max(x['pdf_error'] for x in areas),walls=walls,
  new_user=r['new_user'],physical_build=r['physical_build'])
 all_area.extend(areas)
editor_results=[]
for path in E.glob('pc008-D-*-inkscape-e7826dd-page*-run01/editor-results.json'):
 r=report_json(path);assert r['source_sha']==CODE and r['status']=='PASS'
 assert hashlib.sha256((archive/'tools/authoring/editor_probe.py').read_bytes()).hexdigest()==r['script_sha256']
 for name,digest in r['files_sha256'].items():assert sha(path.parent/name)==digest
 original=Path(r['origin_source']);assert sha(original)==sha(path.parent/'editor-original.svg')
 for name,digest in r['origin_bundle_sha256'].items():assert sha(original.parent/name)==digest
 before=ET.parse(path.parent/'editor-original.svg').getroot();after=ET.parse(path.parent/'editor-edited.svg').getroot()
 assert all(before.get(k)==after.get(k) for k in ('width','height','viewBox'))
 guide_a=before.find(f"{NS}g[@id='page-GUIDES']");guide_b=after.find(f"{NS}g[@id='page-GUIDES']")
 ca,cb=signature(guide_a.find(f'{NS}path').get('d')),signature(guide_b.find(f'{NS}path').get('d'))
 assert ca==cb and ca[0][0]=='M' and ca[1][0]=='L'
 assert (ca[1][1]-ca[0][1])**2+(ca[1][2]-ca[0][2])**2==10000
 a={e.get('id'):e for e in before.iter() if e.get('id')};b={e.get('id'):e for e in after.iter() if e.get('id')}
 changed=r['actual_inkscape_action_edits'];part=changed['part_id'];label=changed['label_id']
 assert ''.join(b[label].itertext())=='Žluťoučký – vlastní díl'
 assert '#b43d28' in b[label].get('style','')
 assert {g.get('data-role') for g in a[part] if g.tag!=NS+'title'}=={g.get('data-role') for g in b[part] if g.tag!=NS+'title'}
 max_drift=F(0);native_arcs=0
 for id,e in a.items():
  if e.tag==NS+'path':
   assert id in b
   first_sig,last_sig=signature(e.get('d')),signature(b[id].get('d'));assert len(first_sig)==len(last_sig)
   for x,y in zip(first_sig,last_sig):
    assert x[0]==y[0] and len(x)==len(y)
    if x[0]=='A':native_arcs+=1;assert x[4:6]==y[4:6]
    drift=max((abs(c-d) for c,d in zip(x[1:],y[1:])),default=F(0));max_drift=max(max_drift,drift);assert drift<=F(1,50000)
  if e.tag==NS+'text' and id!=label:assert ''.join(e.itertext())==''.join(b[id].itertext())
 m1,m2=transform(a[part].get('transform')),transform(b[part].get('transform'))
 delta=m2-m1;assert np.max(np.abs(delta[:2,:2]))<2e-7
 assert np.max(np.abs(delta[:2,2]-np.array([10,15])*25.4/96))<2e-5
 assert r['native_gui_text_edit']['foreground_verified_before_each_chord'] and r['origin_bundle_preserved_after_run']
 editor_results.append(dict(folder=path.parent.name,seconds=r['elapsed_seconds'],artifact_hashes=len(r['files_sha256']),native_arc_commands=native_arcs,max_local_drift=float(max_drift),unicode_text=''.join(b[label].itertext()),scope=r['scope']))
assert len(editor_results)==4
suite=pinned('docs/p2/implementation/evidence/pc008-integrated-suite-e7826dd-run01.xml');doc=ET.fromstring(suite);cases=list(doc.iter('testcase'))
assert len(cases)==1370 and not any(any(e.tag in ('failure','error','skipped') for e in case) for case in cases)
time=float(next(doc.iter('testsuite')).get('time'));assert abs(time-315.601)<.01
rawlog=pinned('docs/p2/implementation/evidence/pc008-integrated-suite-e7826dd-run01.log')
log=rawlog.decode('utf-16' if rawlog.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');assert '1370 passed' in log
queue=json.loads(pinned('05_WORK_QUEUE.json'));assert queue['release_readiness'].startswith('NOT_READY') and 'B1/B2/Bezier' not in queue['current_delivery']['next_required_technical_work'].split(';')[0]
assert all(t['status']!='COMPLETE' for t in queue['tickets'] if t['id'] in ('PC-008','PC-009','PC-010'))
out=dict(source_sha=CODE,metadata_sha=META,source_equals_metadata_runtime=True,native=native_results,editors=editor_results,suite=dict(tests=1370,failures=0,errors=0,skips=0,seconds=time,sha256=hashlib.sha256(suite).hexdigest()),
 status='PASS_FINAL_D_B3_TECHNICAL_INCREMENT_AUDIT_NOT_WHOLE_PC008_OR_P2_ACCEPTANCE')
(OWN/'pc008-integration-review-final-e782.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps(out,indent=2,ensure_ascii=True))
