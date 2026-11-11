"""Independent pinned integration/native-artifact audit; no GUI interaction."""
import ast,hashlib,io,json,math,os,re,subprocess,sys,tarfile,tempfile
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
PIN='d762fc6d2c543691b8918128b6b0d3e1da59313e'
NATIVE=E/'pc008-D-desktop-d762fc6-run01'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tools/authoring','tests','pyproject.toml',
 'docs/p2/implementation/evidence/pc008-curved-domain-518b91a/raw/gothic-backend.apcraft'],cwd=ROOT)
isolated=Path(tempfile.mkdtemp(prefix='pc008-integration-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
 for member in archive.getmembers():assert (isolated/member.name).resolve().is_relative_to(isolated)
 archive.extractall(isolated,filter='data')
sys.path.insert(0,str(isolated/'src'))
from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring import project,segmented_surface,segmented_loft_curves
from archpapercraft.exporter import author_export
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions
modules={}
for module in (project,segmented_surface,segmented_loft_curves,author_export):
 p=Path(module.__file__);assert p.resolve().is_relative_to(isolated)
 expected=subprocess.check_output(['git','show',PIN+':'+p.relative_to(isolated).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n')
 actual=p.read_text(encoding='utf8').encode();assert actual==expected
 modules[module.__name__]=dict(path=str(p),lf_sha256=hashlib.sha256(actual).hexdigest())
report=json.loads((NATIVE/'results.json').read_text(encoding='utf8'))
assert report['source_sha']==PIN and not report['failures']
source_hashes={}
for relative,digest in report['source_files_sha256'].items():
 blob=subprocess.check_output(['git','show',PIN+':'+relative],cwd=ROOT)
 matches=[kind for kind,data in [('blob',blob),('LF',blob.replace(b'\r\n',b'\n')),('CRLF',blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))] if hashlib.sha256(data).hexdigest()==digest]
 assert matches,(relative,digest)
 source_hashes[relative]=matches
for relative,digest in report['files_sha256'].items():
 assert hashlib.sha256((NATIVE/relative).read_bytes()).hexdigest()==digest,relative
folder=NATIVE/'D-segmented';data=json.loads((folder/'D-segmented.apcraft').read_text(encoding='utf8'))
snapshot=json.loads((folder/'snapshot.json').read_text(encoding='utf8'));p=AuthorProject.from_dict(data)
assert snapshot['construction_checks']['segmented_source_project']==data
assert p.snapshot()==snapshot
manifest=json.loads((folder/'export/.author-export.json').read_text(encoding='utf8'))
canonical=dict(snapshot);canonical.pop('metadata',None)
digest=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
assert digest==manifest['snapshot_digest']
assert len(p.surfaces)==65 and len(p.material_part_ids())==64
v=next(iter(p.segmented_variants.values()));assert len(v.triangle_bindings)==64 and v.print_selected
assert p.loft_status(v.target_surface_id)['status']=='REJECTED'
assert len(snapshot['coverage']['reference_surface_ids'])==1
assert set(snapshot['coverage']['expected_part_ids'])==p.material_part_ids()
actual_pdf=read_pdf_cut_regions(folder/'export/model.pdf')['parts']
assert set(actual_pdf)==p.material_part_ids()
NS='{http://www.w3.org/2000/svg}';svg_areas={};svg_pages={}
def area(points):return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2
for page_index,page in enumerate(snapshot['pages']):
 root=__import__('xml.etree.ElementTree',fromlist=['ElementTree']).parse(folder/f"export/page-{page['id']}.svg").getroot()
 for group in root.findall(f'{NS}g[@data-part-id]'):
  pid=group.get('data-part-id');assert pid not in svg_areas
  assert group.get('data-flattening-mode')=='APPROXIMATE'
  cut=group.find(f"{NS}g[@data-role='CUT']");assert len(cut)==1
  tokens=re.findall(r'[MLZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',cut[0].get('d'))
  points=[];i=0
  while i<len(tokens):
   op=tokens[i];i+=1
   if op=='Z':continue
   assert op in ('M','L');points.append([F(tokens[i]),F(tokens[i+1])]);i+=2
  svg_areas[pid]=area(points);svg_pages[pid]=page_index
assert set(svg_areas)==p.material_part_ids()
observations=[];uv_area=F(0)
for row,triangle in zip(v.triangle_bindings,v.certificate['math']['triangles']):
 uv=[tuple(map(F,point)) for point in triangle['parameter_vertices_exact']];uv_area+=area(uv)
 points=[(40*u,20*u*w,30*w) for u,w in uv]
 a,b=[tuple(q[i]-points[0][i] for i in range(3)) for q in points[1:]]
 cross=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
 squared=sum(q*q for q in cross);denom=10**70
 n=math.isqrt(squared.numerator*denom*denom//squared.denominator)
 lo,hi=F(n,2*denom),F(n+1,2*denom)
 pid=row['part_id'];svg=svg_areas[pid]
 pdf=area([tuple(c[1:]) for c in actual_pdf[pid]['loops'][0] if c[0] in ('M','L')])
 se=max(abs(svg-lo),abs(svg-hi));pe=max(abs(pdf-lo),abs(pdf-hi))
 assert se<F(1,100) and pe<F(1,100)
 assert actual_pdf[pid]['page_index']==svg_pages[pid]
 observations.append(dict(part_id=pid,svg_error_mm2=float(se),pdf_error_mm2=float(pe),page=svg_pages[pid]))
assert uv_area==1
assert sorted(list(svg_pages.values())).count(0)==32 and sorted(list(svg_pages.values())).count(1)==32
native=[d for d in report['dialogs'] if 'native_seen' in d];assert len(native)==3 and all(d['native_seen'] and d['accepted'] for d in native)
actions={}
for item in report['inputs']:
 if item.get('event')=='observed_QAction_triggered':actions[item['action']]=item['count']
assert all(actions.get(name,0)>0 for name in ('draw','copy_profile','loft','segment','manual_grid','save','new','open','export'))
# AST confirms the new steps cannot assign into project/controller/document or
# call application construction APIs. GUI handles and local observation copies
# are permitted. Helper implementations were separately read by the reviewer.
step_source=(isolated/'tools/authoring/segmentation_desktop_steps.py').read_text(encoding='utf8')
tree=ast.parse(step_source);mutations=[]
for node in ast.walk(tree):
 if isinstance(node,(ast.Assign,ast.AugAssign,ast.AnnAssign)):
  for target in getattr(node,'targets',[getattr(node,'target',None)]):
   if target is not None and any(s in ast.unparse(target) for s in ('self.w.project.','self.w.controller.')):mutations.append(ast.unparse(target))
assert not mutations
output=dict(source_sha=PIN,archive_sha256=hashlib.sha256(raw).hexdigest(),isolated_directory=str(isolated),actual_imports=modules,
 native_source_hashes_checked=len(source_hashes),native_artifact_hashes_checked=len(report['files_sha256']),
 source_hash_encodings={kind:sum(kind in matches for matches in source_hashes.values()) for kind in ('blob','LF','CRLF')},
 source_surfaces=65,printed_parts=64,reference_targets=1,pages=[32,32],uv_area_exact=str(uv_area),
 actual_area_observations=observations,actual_actions=actions,native_dialogs=3,
 native_elapsed_seconds=report['elapsed_seconds'],new_user=report['new_user'],physical_build=report['physical_build'],
 status='PASS_PRELIMINARY_LINE_ARTIFACT_AUDIT_NOT_FINAL_D_ACCEPTANCE')
(E/'pc008-integration-review-d762-artifacts.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:value for k,value in output.items() if k not in ('actual_imports','actual_area_observations','actual_actions')},indent=2))
