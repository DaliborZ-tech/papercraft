"""Exact e782 DU02, oracle and current-guard transfer checks, no native driver run."""
import copy,hashlib,io,json,math,subprocess,sys,tarfile,tempfile
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
PIN='e7826dd9b8b90843cdba72a6ae6fd52f0936a1ea'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tools/authoring','tests','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='pc008-candidate-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
 for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
 archive.extractall(target,filter='data')
sys.path[:0]=[str(target/'src'),str(target/'tools/authoring')]
from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring import segmented_surface
from archpapercraft.authoring.editing import rename_author_entities
from archpapercraft.exporter.segmented_output_validation import validate_segmented_snapshot,validate_segmented_vector_outputs
from archpapercraft.exporter.author_export import _curve_output_expectations
import segmentation_desktop_steps as oracle
imports={}
for module in (segmented_surface,oracle):
 p=Path(module.__file__);assert p.resolve().is_relative_to(target)
 blob=subprocess.check_output(['git','show',PIN+':'+p.relative_to(target).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n')
 actual=p.read_text(encoding='utf8').encode();assert actual==blob
 imports[module.__name__]=dict(path=str(p),lf_sha256=hashlib.sha256(actual).hexdigest())
def profile(points,segments,origin=(0,0,0),u=(1,0,0),v=(0,1,0)):
 return NS(vertices=[NS(id=str(i),point=p) for i,p in enumerate(points)],segments=segments,plane=NS(origin=origin,u=u,v=v))
line=NS(id='l',kind='line',start_vertex_id='0',end_vertex_id='1')
q=profile([(2,4),(6,8)],[line],origin=(100,200,300),u=(0,1,0),v=(0,0,1))
assert all(abs(a-b)<1e-14 for a,b in zip(oracle.profile_point(q,'l',.25),(1,2.03,3.05)))
for reverse in (False,True):
 points=[(100,0),(0,100),(0,0)]
 if reverse:points=[(0,100),(100,0),(0,0)]
 arc=NS(id='a',kind='arc',start_vertex_id='0',end_vertex_id='1',data=dict(center=[0,0],sweep_deg=-90 if reverse else 90))
 closure=[NS(id=str(i),kind='line',start_vertex_id=str(a),end_vertex_id=str(b)) for i,(a,b) in enumerate(((1,2),(2,0)))]
 q=profile(points,[arc,*closure]);mid=oracle.profile_point(q,'a',.5)
 assert abs(mid[0]-math.sqrt(.5))<1e-14 and abs(mid[1]-math.sqrt(.5))<1e-14
 assert abs(oracle.profile_area(q)-math.pi/4)<1e-14
assert oracle.triangle_area([(1,2,3),(4,2,3),(1,6,3)])==6
# Actual creation defaults, global numbering, author rename and old load.
p=AuthorProject.new(scale=1);ordinary=p.add_surface(p.add_profile([[0,0],[3,0],[0,3]]))
a=p.add_profile([[0,0],[16,0]],closed=False)
b=p.add_profile([[0,0],[16,8]],closed=False,plane=dict(origin=[0,0,12],u=[1,0,0],v=[0,1,0]))
s=p.add_loft(a,b,correspondences=[dict(first_segment_id=p.profiles[a].segments[0].id,second_segment_id=p.profiles[b].segments[0].id,first_interval=[0,1],second_interval=[0,1])])
preview=p.preview_segmented_variant(s,max_deviation_mm=.26)
vid=p.add_segmented_variant(s,max_deviation_mm=.26,preview_digest=preview['preview_digest'])
rows=p.segmented_variants[vid].triangle_bindings
assert len(rows)==16 and len({p.parts[r['part_id']].name for r in rows})==16
assert all(p.parts[r['part_id']].name==f"P{p.parts[r['part_id']].number}" for r in rows)
pid=rows[0]['part_id'];rename_author_entities(p,part_id=pid,part_name='Owner keeps this long name');p.recompute([pid])
reopened=AuthorProject.from_dict(p.to_dict())
assert reopened.parts[pid].name=='Owner keeps this long name' and reopened.parts[pid].labels[0]['text']=='Owner keeps this long name'
native=E/'pc008-D-desktop-d762fc6-run01/D-segmented';old=json.loads((native/'D-segmented.apcraft').read_text(encoding='utf8'))
loaded=AuthorProject.from_dict(copy.deepcopy(old))
assert {pid:part.name for pid,part in loaded.parts.items()}=={pid:part['name'] for pid,part in old['parts'].items()}
snapshot=json.loads((native/'snapshot.json').read_text(encoding='utf8'))
assert len(validate_segmented_snapshot(snapshot))==64
result=validate_segmented_vector_outputs(snapshot,[native/f"export/page-{page['id']}.svg" for page in snapshot['pages']],native/'export/model.pdf',expected_parts=_curve_output_expectations(snapshot))
assert result['status']=='VERIFIED' and len(result['parts'])==64
assert all(r['area_budget_basis']=='SOURCE_PLANE_BODY_ONLY_EXCLUDES_CONNECTORS' for r in result['parts'].values())
out=dict(source_sha=PIN,archive_sha256=hashlib.sha256(raw).hexdigest(),isolated_directory=str(target),actual_imports=imports,
 checks={'oracle_line_rotated_world_plane':'PASS','oracle_circle_both_sweeps_midpoint_and_Green':'PASS','oracle_triangle_area':'PASS',
 'DU02_new16_global_short_names':'PASS','DU02_explicit_owner_rename_reopen':'PASS','DU02_old64_names_preserved_on_load':'PASS',
 'current5ad_guard_revalidates_old64_source_and_actual_vectors':'PASS'},
 limit='Revalidation of historical d762 artifacts is not a new native run of e782 and not actual new-label layout proof')
(E/'pc008-integration-review-candidate-e782.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print(json.dumps(out,indent=2))
