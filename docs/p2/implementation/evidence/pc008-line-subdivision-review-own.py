"""Independent algebra, source projection and UUID/error-boundary witnesses."""
import copy,json,math
from fractions import Fraction as F
import pytest
from archpapercraft.authoring import AuthorProject,ProjectFormatError,ValidationError
from archpapercraft.authoring.curve_subdivision import CurveSource,CurveSubdivisionHistory,TrimReference,SourcePointReference


@pytest.mark.parametrize('a,b',[(F(2,7),F(5,6)),(F(5,6),F(2,7)),(F(0),F(999,1000))])
def test_cubic_restriction_matches_independent_endpoint_jet_formula(a,b):
 p=((F(1),F(2)),(F(5),F(-3)),(F(-2),F(7)),(F(9),F(4)))
 source=CurveSource('cubic',p[0],p[-1],p[1:3])
 def value(t):return tuple(sum(math.comb(3,i)*(1-t)**(3-i)*t**i*p[i][j] for i in range(4)) for j in range(2))
 def derivative(t):return tuple(sum(3*math.comb(2,i)*(1-t)**(2-i)*t**i*(p[i+1][j]-p[i][j]) for i in range(3)) for j in range(2))
 q0,q3=value(a),value(b);d=b-a
 expected=(q0,tuple(x+d*v/3 for x,v in zip(q0,derivative(a))),tuple(x-d*v/3 for x,v in zip(q3,derivative(b))),q3)
 assert source.controls_on(a,b)==expected


def test_nonuniform_nested_history_and_reverse_trim_affine_coordinates():
 h=CurveSubdivisionHistory('p','root',CurveSource('line',(1,2),(22,30)))
 h=h.split('root',F(1,3),'a','b').split('b',F(2,5),'b1','b2').merge(['b1','b2'],'mb')
 r=h.resolve(TrimReference('stable-trim','p','root',F(5,6),F(1,6)))
 assert r.reference.id=='stable-trim' and r.status=='CHAIN'
 assert [(u.piece_id,u.start,u.end) for u in r.uses]==[('mb',F(3,4),F(0)),('a',F(1),F(1,2))]
 assert CurveSubdivisionHistory.from_dict(json.loads(json.dumps(h.to_dict()))).to_dict()==h.to_dict()


def test_shared_point_is_not_a_nearest_point_after_geometry_edit():
 h=CurveSubdivisionHistory('p','root',CurveSource('line',(0,0),(12,0))).split('root',F(1,3),'a','b')
 reference=SourcePointReference('v','p','root',F(1,3))
 assert h.resolve_point(reference).status=='SHARED_POINT'
 changed=h.edit('b',CurveSource('line',(4,0),(12,1)))
 assert changed.resolve_point(reference).status=='UNRESOLVED'
 with pytest.raises(ValueError):changed.merge(['a','b'],'same-coordinate-is-not-same-generation')


def test_retired_identity_cannot_be_reused_and_one_edge_adapter_refuses_chain():
 h=CurveSubdivisionHistory('p','root',CurveSource('line',(0,0),(10,0))).split('root',F(1,2),'a','b')
 with pytest.raises(ValueError):h.merge(['a','b'],'root')
 assert h.resolve(TrimReference('t','p','root'),require_single=True).status=='UNRESOLVED'


def test_large_numeric_split_does_not_claim_unchanged_straight_material():
 p=AuthorProject.new(scale=1)
 pid=p.add_profile([[1e16,0],[1e16+4,3]],closed=False)
 old=p.profiles[pid].segments[0].id;before=p.to_dict()
 try:result=p.split_profile_segment(pid,old,F(1,4))
 except ValidationError:
  assert p.to_dict()==before;return
 actual=p.profiles[pid].vertex(result['vertex_id']).point
 a=p.profiles[pid].vertices[0].point;b=p.profiles[pid].vertices[-1].point
 dx,dy=map(F,(b[0]-a[0],b[1]-a[1]));x,y=F(actual[0])-F(a[0]),F(actual[1])-F(a[1])
 cross=dx*y-dy*x
 deviation_squared=cross*cross/(dx*dx+dy*dy)
 if deviation_squared>F(1,10000):
  with pytest.raises(ValidationError,match='UNRESOLVED'):
   p.resolve_profile_edge(pid,old)


def retired_pair():
 p=AuthorProject.new(scale=1);records=[]
 for offset in (0,20):
  pid=p.add_profile([[offset,0],[offset+12,0],[offset+12,6],[offset,6]])
  sid=p.add_surface(pid);edge=p.profiles[pid].segments[0].id
  result=p.split_profile_segment(pid,edge,F(1,3));p.merge_profile_segments(pid,result['segment_ids']);p.recompute()
  records.append((pid,sid,edge,result))
 return p,records


def test_global_retired_vertex_uuid_cannot_alias_a_different_profile():
 p,records=retired_pair();raw=p.to_dict()
 first,second=records;alias=first[3]['vertex_id'];old=second[3]['vertex_id']
 record=raw['profile_subdivisions'][second[2]]
 record['points'][alias]=record['points'].pop(old)
 for ends in record['edges'].values():
  for i,value in enumerate(ends):
   if value==old:ends[i]=alias
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(raw)


def test_malformed_rational_history_is_typed_format_error():
 p,records=retired_pair();raw=p.to_dict()
 raw['profile_subdivisions'][records[0][2]]['history']['events'][0][2]='1/0'
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(raw)


def test_unknown_schema6_and_legacy_new_registry_are_rejected():
 p=AuthorProject.new();raw=p.to_dict();raw['schema_version']=6
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(raw)
 raw=p.to_dict();raw.update(schema_version=5,writer_version='0.3.0-pc008-segmented-variants-experimental')
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(raw)


@pytest.mark.parametrize('sign',[1,-1])
def test_arc_children_keep_nominal_circle_and_outward_exact_quarter_bounds(sign):
 source=CurveSource('arc',(3,0),(0,3*sign),center=(0,0),sweep_deg=90*sign)
 h=CurveSubdivisionHistory('p','arc',source).split('arc',F(1,3),'a','b')
 assert [p.sweep_deg_exact for p in h.pieces]==[F(30*sign),F(60*sign)]
 x,y=h.pieces[0].point_bounds(1)
 assert x[0]>0 and x[0]*x[0]<=F(27,4)<=x[1]*x[1]
 assert y[0]<=F(3*sign,2)<=y[1]
 assert x[1]-x[0]<F(1,10**40) and y[1]-y[0]<F(1,10**40)
 assert h.pieces[0].source is source and h.pieces[1].source is source


def test_exact_near_boundary_reference_is_not_snapped_to_shared_point():
 h=CurveSubdivisionHistory('p','root',CurveSource('line',(0,0),(12,0))).split('root',F(2,3),'a','b')
 near=F(2,3)+F(1,2**80)
 r=h.resolve(TrimReference('t','p','root',F(2,3),near))
 assert r.status=='SINGLE' and len(r.uses)==1 and r.uses[0].piece_id=='b'
 assert r.uses[0].start==0 and r.uses[0].end==3*F(1,2**80)
 q=h.resolve_point(SourcePointReference('v','p','root',near))
 assert q.status=='SINGLE' and q.uses[0].piece_id=='b' and q.uses[0].parameter>0


def test_bounded_history_replay_rejects_excessive_event_count_before_replaying():
 h=CurveSubdivisionHistory('p','root',CurveSource('line',(0,0),(12,0)))
 data=h.to_dict();data['events']=[['split','root','1/2','a','b']]*1025
 with pytest.raises(ValueError,match='budget'):CurveSubdivisionHistory.from_dict(data)


@pytest.mark.parametrize('known',[False,True])
def test_known_native_retired_tab_owner_uses_whole_hinge_consumer(known):
 from test_curve_bend import wall_base
 p,cid,wall,_=wall_base(known=known)
 before=p.connector_bend_clearance(cid)
 profile=p.profiles[p.surfaces[wall].profile_id]
 connector=copy.deepcopy(p.connectors[cid]);geometry=p._connector_geometry(cid)
 p.split_profile_segment(profile.id,profile.segments[0].id,F(2,7))
 after=p.connector_bend_clearance(cid)
 assert after['status']==before['status'] and p._connector_geometry(cid)==geometry
 assert p.connectors[cid]==connector


def test_shared_seed_between_two_roots_is_valid_but_created_vertex_cannot_alias():
 p=AuthorProject.new(scale=1);pid=p.add_profile([[0,0],[12,0],[12,6],[0,6]]);p.add_surface(pid)
 records=[]
 for index in (0,1):
  edge=p.profiles[pid].segments[index].id;r=p.split_profile_segment(pid,edge,F(1,3))
  p.merge_profile_segments(pid,r['segment_ids']);records.append((edge,r))
 p.recompute();state=p.to_dict();assert AuthorProject.from_dict(state).to_dict()==state
 a,b=records;record=state['profile_subdivisions'][b[0]];old=b[1]['vertex_id'];alias=a[1]['vertex_id']
 record['points'][alias]=record['points'].pop(old)
 for ends in record['edges'].values():
  for i,x in enumerate(ends):
   if x==old:ends[i]=alias
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(state)


def test_retired_vertex_cannot_alias_a_retired_edge_uuid():
 p,records=retired_pair();state=p.to_dict();a,b=records;record=state['profile_subdivisions'][b[2]]
 old=b[3]['vertex_id'];alias=a[2]
 record['points'][alias]=record['points'].pop(old)
 for ends in record['edges'].values():
  for i,x in enumerate(ends):
   if x==old:ends[i]=alias
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(state)


def test_missing_registry_and_poisoned_fresh_cache_cannot_be_exportable():
 p,records=retired_pair();raw=p.to_dict();raw['profile_subdivisions']={}
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(raw)
 p=AuthorProject.new(scale=1);pid=p.add_profile([[0,0],[12,0],[12,6],[0,6]]);sid=p.add_surface(pid)
 p.split_profile_segment(pid,p.profiles[pid].segments[0].id,F(2,7))
 raw=p.to_dict();raw['parts'][p.surfaces[sid].part_id]['stale']=False
 try:q=AuthorProject.from_dict(raw)
 except ProjectFormatError:return
 with pytest.raises(ValidationError):q.snapshot()


def test_live_arc_subdivision_is_explicitly_rejected_without_mutation():
 p=AuthorProject.new(scale=1);pid=p.add_profile(segments=[dict(kind='arc',start=[3,0],end=[0,3],data=dict(center=[0,0],sweep_deg=90))],closed=False)
 before=p.to_dict()
 with pytest.raises(ValidationError):p.split_profile_segment(pid,p.profiles[pid].segments[0].id)
 assert p.to_dict()==before


from test_workspace import window as _window_fixture,arrange_rectangle
window=_window_fixture


def test_widget_stale_confirmation_keeps_the_new_live_state(window,qtbot):
 from PySide6.QtCore import QTimer,Qt
 from PySide6.QtWidgets import QApplication,QDialogButtonBox
 from archpapercraft.ui.author_subdivision import SubdivisionDialog
 sid=arrange_rectangle(window);pid=window.project.surfaces[sid].profile_id
 def confirm():
  dialog=QApplication.activeModalWidget();assert isinstance(dialog,SubdivisionDialog)
  window.controller.execute('Simulated concurrent name edit',lambda p:setattr(p,'name','Changed during preview'))
  qtbot.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok),Qt.MouseButton.LeftButton)
 QTimer.singleShot(0,confirm);window.actions['split_profile'].trigger()
 assert window.project.name=='Changed during preview' and not window.project.profile_subdivisions
 assert len(window.project.profiles[pid].vertices)==4
 assert any('Projekt se od náhledu změnil' in str(x) for x in window._test_warnings)


def test_widget_c05_main_numeric_input_commits_before_dialog_then_cancel(window,qtbot):
 from PySide6.QtCore import QTimer,Qt
 from PySide6.QtWidgets import QApplication
 sid=arrange_rectangle(window);profile=window.project.profiles[window.project.surfaces[sid].profile_id]
 vertex=profile.vertices[1].id;window.select_vertex(profile.id,vertex)
 window.vertex_x.setFocus();window.vertex_x.selectAll();qtbot.keyClicks(window.vertex_x,'11')
 seen=[]
 def cancel():
  dialog=QApplication.activeModalWidget();seen.append(dialog.source.profiles[profile.id].vertex(vertex).point[0]);dialog.reject()
 QTimer.singleShot(0,cancel);window.actions['split_profile'].trigger()
 assert seen==[11000.] and window.project.profiles[profile.id].vertex(vertex).point[0]==11000
 assert not window.project.profile_subdivisions


def test_closed_polygon_topology_only_split_preserves_original_area_budget():
 p=AuthorProject.new(scale=1/1024)
 pid=p.add_profile([[1e16,0],[1e16+2,2**20],[1e16+4,0]])
 before=p.to_dict();profile=p.profiles[pid]
 def exact_area():
  points=[tuple(map(F,v.point)) for v in profile.vertices]
  return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))*F(p.scale)**2/2
 old=exact_area();assert old==2
 try:p.split_profile_segment(pid,profile.segments[0].id,F(1,4))
 except ValidationError:
  assert p.to_dict()==before;return
 actual=exact_area()
 assert abs(actual-old)<=max(F(1,100),old/1000000),dict(source_area=str(old),actual_area=str(actual),delta=str(actual-old))


def joined_surface_with_unrelated_hole():
 from test_paper import two_panels
 p,wall,roof,wa,rb=two_panels()
 hole=p.add_profile([[2000,1000],[4000,1000],[4000,2000],[2000,2000]])
 p.add_hole(wall,hole)
 joint=p.connect_edges(wall,wa,roof,rb)
 return p,wall,roof,hole,joint


def test_subdivide_hole_does_not_resolve_outer_joint_against_the_wrong_profile():
 p,wall,roof,hole,joint=joined_surface_with_unrelated_hole()
 before=copy.deepcopy(p.joints[joint]);profile=p.profiles[hole]
 p.split_profile_segment(hole,profile.segments[0].id,F(1,2))
 assert p.joints[joint]==before and not p.joints[joint].unresolved


def test_unrelated_hole_edit_does_not_destroy_a_valid_outer_edge_reference():
 p,wall,roof,hole,joint=joined_surface_with_unrelated_hole()
 assert not p.profile_subdivisions
 profile=p.profiles[hole];p.move_vertex(hole,profile.vertices[1].id,[4500,1000])
 assert not p.joints[joint].unresolved


def profile_area_exact(profile,scale):
 pts=[tuple(map(F,v.point)) for v in profile.vertices]
 return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(pts,pts[1:]+pts[:1])))*F(scale)**2/2


def test_whole_body_holes_share_one_area_budget_not_one_budget_per_profile():
 p=AuthorProject.new(scale=1/8192)
 outer=p.add_profile([[1e16,0],[1e16+64,0],[1e16+64,2**22],[1e16,2**22]])
 sid=p.add_surface(outer);holes=[]
 for offset in (8,32,48):
  hid=p.add_profile([[1e16+offset,2**18],[1e16+offset+2,2**18+2**20],[1e16+offset+4,2**18]])
  p.add_hole(sid,hid);holes.append(hid)
 def body():return profile_area_exact(p.profiles[outer],p.scale)-sum(profile_area_exact(p.profiles[h],p.scale) for h in holes)
 source=body();assert source==F(125,32)
 for i,hid in enumerate(holes):
  before=p.to_dict();profile=p.profiles[hid]
  try:p.split_profile_segment(hid,profile.segments[0].id,F(1,4))
  except ValidationError:
   assert i==2 and p.to_dict()==before;return
  assert source-body()==F(i+1,256)
 assert abs(source-body())<=F(1,100),dict(source_area=str(source),actual_area=str(body()),delta=str(source-body()))


def test_accepted_area_projection_is_rechecked_on_scale_and_closed_load():
 p=AuthorProject.new(scale=1/8192)
 pid=p.add_profile([[1e16,0],[1e16+2,2**20],[1e16+4,0]])
 p.split_profile_segment(pid,p.profiles[pid].segments[0].id,F(1,4))
 state=p.to_dict();assert AuthorProject.from_dict(state).to_dict()==state
 assert profile_area_exact(p.profiles[pid],p.scale)==F(9,256)
 with pytest.raises(ValidationError):p.set_scale(1/4096)
 assert p.to_dict()==state
 corrupt=copy.deepcopy(state);corrupt['scale']=1/4096
 with pytest.raises(ProjectFormatError):AuthorProject.from_dict(corrupt)
