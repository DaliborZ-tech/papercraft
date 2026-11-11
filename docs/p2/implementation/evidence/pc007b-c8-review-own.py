"""Independent format/history/world closure and harness mathematical witnesses."""
import ast,copy,hashlib,json,math
from dataclasses import asdict
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
import pytest
from test_circular_shell import authored,circle
from test_circular_material_integration import constructed
from test_curved_connector_sources import receiver_source
from archpapercraft.authoring import AuthorProject,ProjectFormatError,ValidationError,load_project
from archpapercraft.authoring.curved_connectors import _receiver_binding,rebuild_curved_material_binding,CurvedConnectorError
from circular_desktop_steps import tab_area

@pytest.fixture(scope='module')
def c_source():
 p,sid,pid,cid=constructed()
 return p.to_dict(),sid,pid,cid

@pytest.mark.parametrize('version',[6,7])
def test_real_capability_copy_and_retired_frame_preserve_original_bytes(version,c_source,tmp_path):
 if version==6:
  p=AuthorProject.from_dict(c_source[0]);absent='profile_subdivisions';writer='0.3.0-pc007b-curved-connectors-experimental'
  assert p.curved_connectors and p.curved_connector_status(c_source[3])['status']=='CERTIFIED_APPROXIMATE'
 else:
  p=AuthorProject.new(scale=1);pid=p.add_profile([[0,0],[24,0],[24,12],[0,12]]);sid=p.add_surface(pid);part=p.part_for_surface(sid);profile=p.profiles[pid];root=profile.segments[0].id
  split=p.split_profile_segment(pid,root,F(1,3));p.recompute();p.set_anchor(part,sid,split['vertex_id'],root);p.merge_profile_segments(pid,split['segment_ids']);p.recompute()
  p.set_placement(part,p.pages[0].id,60,60,30,position_locked=True,rotation_locked=True)
  assert profile.vertex(split['vertex_id']) is None
  absent='curved_connectors';writer='0.3.0-pc008-profile-provenance-experimental'
 expected=p.to_dict();raw=copy.deepcopy(expected);raw.pop(absent);raw.update(schema_version=version,writer_version=writer)
 path=tmp_path/f'real-original-{version}.apcraft';path.write_text(json.dumps(raw),encoding='utf8');original=path.read_bytes()
 q=load_project(path);assert q.requires_save_as and q.loaded_from_schema==version
 assert q.to_dict()==expected
 with pytest.raises(ValidationError):q.save(path)
 assert path.read_bytes()==original
 target=tmp_path/'new-copy.apcraft';q.save(target);r=load_project(target)
 assert not r.requires_save_as and r.to_dict()==expected and path.read_bytes()==original

@pytest.mark.parametrize('version',[6,7])
@pytest.mark.parametrize('injected',['empty','nonempty','missing_known','wrong_writer'])
def test_parallel_old_envelopes_never_smuggle_capabilities(version,injected):
 raw=AuthorProject.new(scale=1).to_dict()
 absent,known=('profile_subdivisions','curved_connectors') if version==6 else ('curved_connectors','profile_subdivisions')
 raw.pop(absent);raw.update(schema_version=version,writer_version='0.3.0-pc007b-curved-connectors-experimental' if version==6 else '0.3.0-pc008-profile-provenance-experimental')
 if injected=='empty':raw[absent]={}
 elif injected=='nonempty':raw[absent]={'undeclared-capability':{}}
 elif injected=='missing_known':raw.pop(known)
 else:raw['writer_version']='unknown future writer'
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(raw)

@pytest.fixture(scope='module')
def coupled(c_source):
 p=AuthorProject.from_dict(c_source[0]);owner=c_source[1];cid=c_source[3]
 profile=p.add_profile([[0,0],[24,0],[24,12],[0,12]]);far=p.add_surface(profile);p.set_transform(far,[2000,1000,0])
 part=p.part_for_surface(far);root=p.profiles[profile].segments[0].id;split=p.split_profile_segment(profile,root,F(1,3));p.recompute()
 p.set_anchor(part,far,split['vertex_id'],root);p.merge_profile_segments(profile,split['segment_ids']);p.recompute()
 p.set_placement(part,p.add_page(),70,100,27,position_locked=True,rotation_locked=True)
 for issue in p.validate_layout():
  assert issue.severity!='error',issue
  if issue.severity=='warning':p.acknowledge(issue.id)
 assert p.curved_connector_status(cid)['status']=='CERTIFIED_APPROXIMATE'
 return p.to_dict(),owner,cid,profile,far,split['vertex_id'],root

def test_bounded_c_context_replays_actual_retired_vertex_and_axis(coupled):
 p=AuthorProject.from_dict(coupled[0]);_,owner,cid,profile,far,anchor,axis=coupled
 body=p.loft_status(owner)['source_binding'];frame=asdict(p.parts[p.part_for_surface(owner)].frame);source=p.curved_connector_inputs(owner)
 assert source['profile_subdivisions']==p.profile_subdivisions
 context=rebuild_curved_material_binding(body,frame,source)
 assert context.resolve_profile_vertex(profile,anchor)==[8,0]
 edge,points=context.resolve_profile_edge(profile,axis,axis=True);assert points.tolist()==[[0,0],[24,0]]
 assert context.curved_connector_inputs(owner)==source
 assert context.curved_connectors[cid].certificate=={} and context.curved_connectors[cid].material=={}
 assert context.parts[p.part_for_surface(far)].frame==p.parts[p.part_for_surface(far)].frame

@pytest.mark.parametrize('attack',['omit_history','bad_event','fake_retired_anchor','extra_field'])
def test_closed_c_context_rejects_missing_poisoned_line_provenance(coupled,attack):
 p=AuthorProject.from_dict(coupled[0]);_,owner,_cid,_profile,far,_anchor,_axis=coupled
 body=p.loft_status(owner)['source_binding'];frame=asdict(p.parts[p.part_for_surface(owner)].frame);source=p.curved_connector_inputs(owner)
 if attack=='omit_history':source.pop('profile_subdivisions')
 elif attack=='bad_event':next(iter(source['profile_subdivisions'].values()))['history']['events'][0][2]='1/0'
 elif attack=='fake_retired_anchor':source['parts'][p.part_for_surface(far)]['frame']['anchor_vertex_id']=p.project_id
 else:source['profile_subdivisions']['unknown']=None
 with pytest.raises((ValidationError,ValueError)):rebuild_curved_material_binding(body,frame,source)

@pytest.mark.parametrize('attack',['history','frame','foreign_pose'])
def test_full_publication_source_fence_covers_line_history_and_actual_foreign_material(coupled,attack):
 from archpapercraft.exporter.loft_output_validation import validate_loft_snapshot
 from archpapercraft.exporter.curve_output_validation import CurveOutputError
 p=AuthorProject.from_dict(coupled[0]);snapshot=p.snapshot();bad=copy.deepcopy(snapshot);source=bad['construction_checks']['curved_source_project']
 if attack=='history':source['profile_subdivisions']={}
 elif attack=='frame':source['parts'][p.part_for_surface(coupled[4])]['frame']['axis_segment_id']=p.project_id
 else:source['surfaces'][coupled[4]]['position_mm'][0]+=1
 with pytest.raises(CurveOutputError):validate_loft_snapshot(bad)

@pytest.mark.parametrize('side',['first','second'])
def test_world_exact_translation_holes_print_side_and_no_source_cache_mutation(side):
 p,record,rim=receiver_source(side,hole=(3,2,.5),r1=20)
 baseline,evidence=_receiver_binding(p,record,rim)
 owner,receiver=p.surfaces[record.owner_surface_id],p.surfaces[record.receiver_surface_id]
 # Distinct dyadic translations; owner offset also participates in subtraction.
 base=[F(257,8),F(-35,4),F(13,2)];delta=[F(37,8),F(-19,4),F(95,8)]
 for pid in receiver.source_profile_ids():
  profile=p.profiles[pid];profile.plane.origin=[float(F(x)-d) for x,d in zip(profile.plane.origin,delta)]
 p.set_transform(owner.id,list(map(float,base)));p.set_transform(receiver.id,[float(a+b) for a,b in zip(base,delta)])
 before=p.to_dict(validate=False);cap,result=_receiver_binding(p,record,p._circular_rim_binding(owner.id,side))
 assert cap==baseline and p.to_dict(validate=False)==before
 assert result['source_binding']['receiver_translation_in_owner_source_exact']==list(map(str,delta))
 assert result['receiver_contact_is_printed_side']==evidence['receiver_contact_is_printed_side']
 assert (cap.holes[0].x_mm,cap.holes[0].y_mm,cap.holes[0].radius_mm)==(3,2 if side=='second' else -2,F(1,2))
 digest=result['source_digest'];p.set_front_side(receiver.part_id,'inside')
 _,flipped=_receiver_binding(p,record,p._circular_rim_binding(owner.id,side))
 assert flipped['receiver_contact_is_printed_side']!=result['receiver_contact_is_printed_side'] and flipped['source_digest']!=digest
 good=receiver.position_mm[2];receiver.position_mm[2]=math.nextafter(good,math.inf)
 with pytest.raises(CurvedConnectorError):_receiver_binding(p,record,p._circular_rim_binding(owner.id,side))

def test_nonidentity_relative_pose_is_unresolved_even_when_visually_tiny():
 p,record,_=receiver_source();receiver=p.surfaces[record.receiver_surface_id]
 p.set_transform(receiver.id,[0,0,0],[0,0,1e-10])
 with pytest.raises(CurvedConnectorError):_receiver_binding(p,record,p._circular_rim_binding(record.owner_surface_id,'second'))

def test_composed_float_pose_cannot_hide_an_authored_half_mm_receiver_offset():
 import numpy as np
 p,record,_=receiver_source();owner=p.surfaces[record.owner_surface_id];receiver=p.surfaces[record.receiver_surface_id]
 # Stored transforms are pure translations, so the independent mathematical
 # world offset is exactly 1/2mm even when float matrix multiplication loses it.
 parent=np.eye(4);parent[0,3]=1e16
 before=p.to_dict(validate=False)
 try:p.set_transform(owner.id,parent_transforms=[parent.tolist()])
 except ValidationError:
  assert p.to_dict(validate=False)==before
  return  # Earlier world length/area precision guard already safely refuses.
 for pid in receiver.source_profile_ids():p.profiles[pid].plane.origin[2]-=30
 p.set_transform(receiver.id,[.5,0,30],parent_transforms=[parent.tolist()])
 assert F(parent[0,3])+F(receiver.position_mm[0])-(F(parent[0,3])+F(owner.position_mm[0]))==F(1,2)
 assert p._surface_matrix(owner.id)[0,3]==p._surface_matrix(receiver.id)[0,3]
 with pytest.raises((CurvedConnectorError,ValidationError)):
  _receiver_binding(p,record,p._circular_rim_binding(owner.id,'second'))

def test_harness_tab_area_matches_independent_circle_green_integral_and_cylinder_limit():
 # Endpoint Green integral for a clockwise circular base between symmetric
 # chord endpoints; source polygon area plus the oriented analytic circle arc.
 # Decimal trigonometric series are independent of the driver's theta-sin sum.
 def sin_decimal(x):
  term=total=x
  for k in range(1,45):term=-term*x*x/Decimal((2*k)*(2*k+1));total+=term
  return total
 def atan_decimal(x):
  return sum(((-1)**k*x**(2*k+1)/Decimal(2*k+1) for k in range(70)),Decimal(0))
 observations=[]
 for r,s in [(10,0),(10,F(-1,3)),(20,F(1,3)),(10,F(1,3000000)),(10,F(-1,3000000))]:
  with localcontext() as ctx:
   ctx.prec=85;radius=Decimal(r);slope=Decimal(s.numerator)/Decimal(s.denominator) if isinstance(s,F) else Decimal(s)
   width=Decimal('.24');depth=Decimal('9.5')
   if not slope:expected=width*depth/2
   else:
    kappa=slope/radius;q=kappa*width/4;h=width/(2*(1+q*q));v=-kappa*width*width/(8*(1+q*q));theta=4*atan_decimal(q)
    rho=1/kappa
    # Direct line/arc Green integral on triangle minus the signed base segment.
    expected=h*(depth-v)-rho*rho*(theta-sin_decimal(theta))/2
   actual=tab_area(r,float(s));error=abs(Decimal.from_float(actual)-expected)
   assert error<Decimal('1e-12'),(r,s,actual,str(expected),str(error))
   observations.append(dict(radius=r,slope=str(s),expected=str(expected),actual=actual,error=float(error)))
 Path(__file__).with_name('pc007b-c8-review-tab-area-oracles.json').write_text(json.dumps(observations,indent=2)+'\n',encoding='utf8')

def test_c_harness_contains_no_document_controller_or_geometry_assignment():
 path=Path(__file__).resolve().parents[4]/'tools/authoring/circular_desktop_steps.py';tree=ast.parse(path.read_text(encoding='utf8'))
 forbidden={'add_profile','add_surface','add_loft','add_curved_connector','set_curved_tab','recompute','from_dict','execute','emit'}
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):assert node.func.attr not in forbidden,node.func.attr
  if isinstance(node,(ast.Assign,ast.AugAssign,ast.AnnAssign)):
   targets=node.targets if isinstance(node,ast.Assign) else [node.target]
   for target in targets:
    text=ast.unparse(target);assert not any(x in text for x in ('.project.','.controller.','.profiles[','.parts[','.surfaces[')),text
