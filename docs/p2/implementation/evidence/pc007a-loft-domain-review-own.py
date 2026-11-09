"""Independent domain/crease/area/frame/coverage/topology review cases."""
import copy
from fractions import Fraction as Q
import json
import math
import os
from pathlib import Path
import random
from uuid import uuid4

import numpy as np
import pytest
from shapely import Point,Polygon

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject,ProjectFormatError,ValidationError,load_project
from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring import curve_topology as topology
from archpapercraft.authoring.loft_surface import analysis
import archpapercraft.authoring.loft_surface as actual

assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())

def refs(p,a,b,reverse=False):
    pairs=list(zip(p.profiles[a].segments,p.profiles[b].segments))
    if reverse:pairs.reverse()
    interval=[1,0] if reverse else [0,1]
    return [dict(first_segment_id=x.id,second_segment_id=y.id,first_interval=list(interval),second_interval=list(interval)) for x,y in pairs]

def source(points=None,closed=False,depth=10):
    p=AuthorProject.new(scale=1)
    a=p.add_profile(points or [[0,0],[20,0],[20,10],[40,10]],closed=closed)
    b=p.copy_profile(a,plane=dict(origin=[0,0,depth],u=[1,0,0],v=[0,1,0]))
    return p,a,b

@pytest.mark.parametrize('mirror',[1,-1])
def test_LD01_signed_turns_and_print_side_are_real_fold_polarity(mirror):
    p,a,b=source([[0,0],[20,0],[20,10*mirror],[40,10*mirror]])
    s=p.add_loft(a,b,correspondences=refs(p,a,b));pid=p.part_for_surface(s)
    out=copy.deepcopy(p.parts[pid].paths)
    # Around +z ruling the two true normal turns have opposite signs.
    assert len(out['FOLD_MOUNTAIN'])==len(out['FOLD_VALLEY'])==1
    p.set_front_side(pid,'inside');inside=p.parts[pid].paths
    assert inside['FOLD_VALLEY']==out['FOLD_MOUNTAIN']
    assert inside['FOLD_MOUNTAIN']==out['FOLD_VALLEY']

def test_LD02_whole_native_area_has_normative_budget_or_blocks():
    p=AuthorProject.new(scale=1);a=p.add_profile(segments=[dict(kind='arc',start=[20,0],end=[-20,0],data=dict(center=[0,0],sweep_deg=180))],closed=False)
    b=p.copy_profile(a,plane=dict(origin=[0,0,200],u=[1,0,0],v=[0,1,0]))
    s=p.add_loft(a,b,correspondences=refs(p,a,b));pid=p.part_for_surface(s)
    if p.loft_status(s)['status']!='EXACT':
        with pytest.raises(ValidationError):p.snapshot()
        return
    commands=p.parts[pid].paths['CUT'][0]['commands'];assert {c[0] for c in commands}<={'M','L','Z'}
    points=[tuple(map(Q,c[1:])) for c in commands if c[0] in ['M','L']]
    actual=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2
    pi=Q('3.141592653589793238462643383279502884197169399375105820974944592307816406286')
    expected=4000*pi;tolerance=max(Q(1,100),expected/1000000)
    assert abs(actual-expected)<=tolerance

def test_seam_reorders_real_cut_and_keeps_explicit_frame_locks():
    p,a,b=source([[0,0],[40,0],[40,30],[0,30]],closed=True,depth=10)
    s=p.add_loft(a,b,correspondences=refs(p,a,b));pid=p.part_for_surface(s)
    page=p.add_page();p.set_placement(pid,page,60,60,30,position_locked=True,rotation_locked=True)
    frame=copy.deepcopy(p.parts[pid].frame);placement=copy.deepcopy(p.placements[pid]);old=copy.deepcopy(p.surfaces[s].params)
    initial=next(e for e in p.world_geometry(s)['boundary'] if e['source']['role']=='SEAM_START')
    new_seam=old['correspondences'][1]['id'];p.update_loft(s,seam_patch_id=new_seam)
    assert p.parts[pid].stale
    current=next(e for e in p.world_geometry(s)['boundary'] if e['source']['role']=='SEAM_START')
    assert initial['start']==[0,0,0] and current['start']==[40,0,0]
    assert current['id']==old['correspondences'][1]['ruling_id']
    p.recompute();assert p.parts[pid].frame==frame and p.placements[pid]==placement
    commands=p.parts[pid].paths['CUT'][0]['commands'];xs=[c[i] for c in commands for i in range(1,len(c),2)]
    assert min(xs)<0<max(xs)
    assert p.surfaces[s].params['end_ruling_id']==old['end_ruling_id']

def test_seam_duplicate_anchor_requires_incident_axis_identity_not_nearest():
    p,a,b=source([[0,0],[40,0],[40,30],[0,30]],closed=True)
    s=p.add_loft(a,b,correspondences=refs(p,a,b));pid=p.part_for_surface(s);profile=p.profiles[a]
    before=p.to_dict()
    with pytest.raises(ValidationError,match='ANCHOR_UNRESOLVED'):
        p.set_anchor(pid,s,profile.vertices[0].id,profile.segments[2].id)
    assert p.to_dict()==before
    p.set_anchor(pid,s,profile.vertices[0].id,profile.segments[0].id)
    left=copy.deepcopy(p.parts[pid].polygons[s][0])
    p.set_anchor(pid,s,profile.vertices[0].id,profile.segments[-1].id)
    right=p.parts[pid].polygons[s][0]
    assert left!=right and p.parts[pid].frame.axis_segment_id==profile.segments[-1].id

def test_LD04_open_update_rejects_non_start_seam_without_metadata_only_change():
    p,a,b=source();s=p.add_loft(a,b,correspondences=refs(p,a,b));before=p.to_dict()
    wrong=p.surfaces[s].params['correspondences'][1]['id']
    with pytest.raises(ValidationError):p.update_loft(s,seam_patch_id=wrong)
    assert p.to_dict()==before

@pytest.mark.parametrize('reverse',[False,True])
def test_full_source_coverage_and_direct_world_uv_evaluation(reverse):
    p,a,b=source();s=p.add_loft(a,b,correspondences=refs(p,a,b,reverse))
    mesh=p.world_geometry(s);assert 'normal' not in mesh and mesh['status']=='EXACT'
    used=set()
    for point,norm,meta in zip(mesh['vertices'],mesh['vertex_normals'],mesh['vertex_sources']):
        segment=p.profiles[a].segment(meta['first_segment_id']);v0=p.profiles[a].vertex(segment.start_vertex_id).point;v1=p.profiles[a].vertex(segment.end_vertex_id).point
        u=meta['first_parameter'];expected=[(1-u)*v0[i]+u*v1[i] for i in range(2)]+[10*meta['v']]
        np.testing.assert_allclose(point,expected,atol=1e-12,rtol=0)
        d=np.array([v1[0]-v0[0],v1[1]-v0[1],0.])*(-1 if reverse else 1);normal=np.cross(d,[0,0,10]);normal/=np.linalg.norm(normal)
        np.testing.assert_allclose(norm,normal,atol=1e-12,rtol=0)
        used.add(meta['first_segment_id']);assert meta['feature_id']==s and meta['second_parameter']==u
    assert used=={x.id for x in p.profiles[a].segments}
    assert all(m['feature_id']==s for m in mesh['triangle_sources'])

def test_open_cubic_is_not_closed_by_fake_source_chord():
    p=AuthorProject.new(scale=1);a=p.add_profile(segments=[dict(kind='cubic',start=[0,0],end=[10,0],data=dict(control1=[2,5],control2=[8,5]))],closed=False)
    b=p.copy_profile(a,plane=dict(origin=[0,0,8],u=[1,0,0],v=[0,1,0]));s=p.add_loft(a,b,correspondences=refs(p,a,b))
    status=p.loft_status(s);assert status['status']=='EXACT'
    assert all(v['status']=='VALID' and 'Open' in v['reason'] for v in status['source_topology'].values())
    assert not p.profiles[a].closed and not p.profiles[b].closed
    mesh=p.world_geometry(s)
    for xyz,m in zip(mesh['vertices'],mesh['vertex_sources']):
        u=m['first_parameter'];x=6*(1-u)**2*u+24*(1-u)*u*u+10*u**3;y=15*(1-u)*u
        np.testing.assert_allclose(xyz,[x,y,8*m['v']],atol=1e-12,rtol=0)

@pytest.mark.parametrize('both_reverse',[False,True])
def test_nonlinear_cubic_direction_is_explicit_and_never_heuristically_repaired(both_reverse):
    p=AuthorProject.new(scale=1);a=p.add_profile(segments=[dict(kind='cubic',start=[0,0],end=[6,0],data=dict(control1=[1,0],control2=[3,0]))],closed=False)
    b=p.copy_profile(a,plane=dict(origin=[0,0,7],u=[1,0,0],v=[0,1,0]));mapping=refs(p,a,b,reverse=both_reverse)
    if not both_reverse:mapping[0]['second_interval']=[1,0]
    profiles=copy.deepcopy(p.profiles);s=p.add_loft(a,b,correspondences=mapping)
    assert p.profiles==profiles and p.surfaces[s].params['correspondences'][0]['second_interval']==[1,0]
    if not both_reverse:
        assert p.loft_status(s)['status']!='EXACT'
        with pytest.raises(ValidationError):p.snapshot()
    else:
        assert p.loft_status(s)['status']=='EXACT'
        for xyz,meta in zip(p.world_geometry(s)['vertices'],p.world_geometry(s)['vertex_sources']):
            u=meta['first_parameter'];np.testing.assert_allclose(xyz,[3*u+3*u*u,0,7*meta['v']],atol=1e-12,rtol=0)

def test_coplanar_closed_loft_is_true_region_with_hole():
    p=AuthorProject.new(scale=1);a=p.add_profile([[10,10],[30,10],[30,30],[10,30]]);b=p.add_profile([[0,0],[40,0],[40,40],[0,40]])
    s=p.add_loft(a,b,correspondences=refs(p,a,b));surface=p.surfaces[s]
    assert surface.kind=='planar' and surface.profile_id==b and surface.hole_profile_ids==[a]
    loops=p.parts[surface.part_id].polygons[s];material=Polygon(loops[0],loops[1:])
    assert material.area==1200 and not material.contains(Point(20,20)) and material.contains(Point(5,5))

def test_true_gothic_cone_has_analytic_endpoints_normals_and_native_boundaries():
    p=AuthorProject.new(scale=1);sweep=math.degrees(math.atan2(30,-12.5))-180
    a=p.add_profile(segments=[dict(kind='arc',start=[-20,0],end=[0,30],data=dict(center=[12.5,0],sweep_deg=sweep)),dict(kind='arc',start=[0,30],end=[20,0],data=dict(center=[-12.5,0],sweep_deg=sweep)),dict(kind='line',start=[20,0],end=[-20,0])])
    b=p.copy_profile(a,factor=1.2,plane=dict(origin=[0,0,10],u=[1,0,0],v=[0,1,0]));s=p.add_loft(a,b,correspondences=refs(p,a,b));status=p.loft_status(s)
    assert status['status']=='EXACT' and status['family']=='POSITIVE_HOMOTHETIC_CONE'
    assert status['source_profile_ids']==[a,b] and status['native_topology']['status']=='VALID'
    assert any(c[0]=='C' for c in p.parts[p.part_for_surface(s)].paths['CUT'][0]['commands'])
    mesh=p.world_geometry(s);first_segment=p.profiles[a].segments[0].id;found=0
    for point,normal,meta in zip(mesh['vertices'],mesh['vertex_normals'],mesh['vertex_sources']):
        if meta['first_segment_id']==first_segment and meta['u']==0:
            np.testing.assert_allclose(point,[-20-4*meta['v'],0,10*meta['v']],atol=1e-10,rtol=0)
            np.testing.assert_allclose(normal,np.array([10,0,4])/math.sqrt(116),atol=1e-10,rtol=0);found+=1
    assert found==2 and len({tuple(np.round(n,6)) for n in mesh['vertex_normals']})>3

def test_nominal_arc_endpoint_mismatch_does_not_become_exact_source_topology():
    p=AuthorProject.new(scale=1);before=p.to_dict()
    try:a=p.add_profile(segments=[dict(kind='arc',start=[10,0],end=[0,10.001],data=dict(center=[0,0],sweep_deg=90))],closed=False)
    except ValidationError:
        assert p.to_dict()==before;return
    b=p.copy_profile(a,plane=dict(origin=[0,0,10],u=[1,0,0],v=[0,1,0]));s=p.add_loft(a,b,correspondences=refs(p,a,b))
    assert p.loft_status(s)['status']!='EXACT'
    with pytest.raises(ValidationError):p.snapshot()

def test_unsupported_contact_cannot_invent_bottom_of_perimeter_loft():
    p,a,b=source([[0,0],[100,0],[100,100],[0,100]],closed=True)
    s=p.add_loft(a,b,correspondences=refs(p,a,b));patch=p.add_surface(p.add_profile([[20,20],[40,20],[40,40],[20,40]]));before=p.to_dict()
    with pytest.raises(ValidationError):p.set_glue_region(patch,s,[[10,10],[50,10],[50,50],[10,50]])
    assert p.to_dict()==before

def test_unsupported_loft_obstacle_is_not_silently_ignored_by_bend_registry():
    p,a,b=source();p.add_loft(a,b,correspondences=refs(p,a,b))
    rp=p.add_profile([[0,0],[40,0],[40,40],[0,40]]);receiver=p.add_surface(rp)
    wp=p.add_profile([[0,0],[40,0],[40,20],[0,20]],plane='XZ');wall=p.add_surface(wp)
    j=p.connect_edges(receiver,p.profiles[rp].segments[0].id,wall,p.profiles[wp].segments[0].id)
    p.set_tab(j,owner=wall,width_mm=4);cid=p.joints[j].connector_id
    result=p.connector_bend_clearance(cid)
    assert result['status']=='UNRESOLVED' and result['message']

@pytest.mark.parametrize('which',['first','second'])
def test_both_dependencies_cache_and_locked_anchor_survive_save_undo_redo(which,tmp_path):
    p,a,b=source();s=p.add_loft(a,b,correspondences=refs(p,a,b));pid=p.part_for_surface(s);p.set_placement(pid,p.pages[0].id,60,60,30,position_locked=True,rotation_locked=True)
    c=AuthorController();c.project=p;before=p.to_dict();frame=copy.deepcopy(p.parts[pid].frame);place=copy.deepcopy(p.placements[pid]);old=p.loft_status(s)['source_digest'];target=a if which=='first' else b
    c.execute('Move source plane',lambda p:p.set_profile_plane(target,origin=[0,0,-3 if which=='first' else 13],u=[1,0,0],v=[0,1,0]))
    assert c.project.parts[pid].stale and c.project.loft_status(s)['source_digest']!=old
    c.undo();assert c.project.to_dict()==before
    c.redo();c.recompute();assert not c.project.parts[pid].stale and c.project.parts[pid].frame==frame and c.project.placements[pid]==place
    path=tmp_path/'copy.apcraft';c.save(path);assert load_project(path).to_dict()==c.project.to_dict()

def test_preview_binding_and_cache_results_are_detached_from_actual_feature():
    p,a,b=source();before=p.to_dict();preview=p.preview_loft(a,b,correspondences=refs(p,a,b));assert p.to_dict()==before
    params=preview['params'];s=p.add_loft(a,b,correspondences=params['correspondences'],seam_patch_id=params['seam_patch_id'],end_ruling_id=params['end_ruling_id']);assert s!=preview['surface_id']
    result=analysis(p,p.surfaces[s]);assert result['feature_id']==result['native']['feature_id']==s
    assert preview['surface_id'] not in json.dumps(p.to_dict())
    result['native']['patches'][0]['first']['segments'][0]['source']['feature_id']='poison'
    assert 'poison' not in json.dumps(analysis(p,p.surfaces[s]))
    preview['project_state']['name']='poison';assert p.name!='poison'

def test_poisoned_paper_cache_cannot_export_with_current_source_digest():
    p,a,b=source();s=p.add_loft(a,b,correspondences=refs(p,a,b));pid=p.part_for_surface(s);p.set_placement(pid,p.pages[0].id,30,30)
    data=p.to_dict();data['parts'][pid]['paths']['CUT'][0]['commands'][0][1]+=1
    loaded=AuthorProject.from_dict(data)
    assert any(i.code=='INVALID_CACHE' for i in loaded.validate_layout())
    with pytest.raises(ValidationError):loaded.snapshot()

def test_source_plane_precision_failure_never_has_exact_proof():
    p=AuthorProject.new(scale=1);a=p.add_profile([[0,0],[20,0],[20,10]],closed=False,plane=dict(origin=[1e18,1e18,0],u=[1,0,0],v=[0,1,0]));b=p.copy_profile(a,plane=dict(origin=[1e18,1e18,10],u=[1,0,0],v=[0,1,0]))
    s=p.add_loft(a,b,correspondences=refs(p,a,b));assert p.loft_status(s)['status']=='UNRESOLVED'
    with pytest.raises(ValidationError):p.snapshot()

def test_non_developable_target_persists_without_exact_or_snapshot(tmp_path):
    p,a,b=source();angle=math.radians(25);p.set_profile_plane(b,origin=[0,0,10],u=[math.cos(angle),math.sin(angle),0],v=[-math.sin(angle),math.cos(angle),0])
    profiles=copy.deepcopy(p.profiles);s=p.add_loft(a,b,correspondences=refs(p,a,b));assert p.loft_status(s)['status'] in ['REJECTED','UNRESOLVED'] and p.profiles==profiles
    before=p.to_dict();path=tmp_path/'target.apcraft';p.save(path);assert load_project(path).to_dict()==before
    with pytest.raises(ValidationError):p.snapshot()
    with pytest.raises(ValidationError):p.recompute()
    assert p.to_dict()==before

@pytest.mark.parametrize('damage',['missing','duplicate','reverse_only_one','missing_second','uuid_collision'])
def test_invalid_commands_have_no_partial_mutations(damage):
    p,a,b=source();rows=refs(p,a,b);before=p.to_dict()
    if damage=='missing':rows.pop()
    elif damage=='duplicate':rows[1]['second_segment_id']=rows[0]['second_segment_id']
    elif damage=='reverse_only_one':rows[1]['first_interval']=[1,0]
    elif damage=='uuid_collision':rows[0]['id']=a
    else:b=str(uuid4())
    with pytest.raises(ValidationError):p.add_loft(a,b,correspondences=rows)
    assert p.to_dict()==before

@pytest.mark.parametrize('damage',['second_ref','patch_id','source_bool','unknown_param'])
def test_current_schema_invalid_source_refs_are_typed_errors(damage):
    p,a,b=source();s=p.add_loft(a,b,correspondences=refs(p,a,b));data=p.to_dict();params=data['surfaces'][s]['params']
    if damage=='second_ref':params['second_profile_id']=str(uuid4())
    elif damage=='patch_id':params['correspondences'][0]['id']=False
    elif damage=='source_bool':params['correspondences'][0]['first_interval']=[False,1]
    else:params['nearest_fallback']=True
    with pytest.raises(ProjectFormatError):AuthorProject.from_dict(data)

@pytest.mark.parametrize('seed',[17,43,91,131])
def test_rational_avl_sweep_matches_all_inclusive_bbox_pairs(seed):
    randomizer=random.Random(seed);nodes=[];boxes=[];guard=Q(1,10**17)
    for i in range(75):
        x,y=Q(randomizer.randrange(-20,21),3),Q(randomizer.randrange(-20,21),7);w,h=Q(randomizer.randrange(0,12),3),Q(randomizer.randrange(0,12),7)
        if not w and not h:w=Q(1,3)
        controls=((x,y),(x+w,y+h));curve=Curve(controls[0],controls[1],segment_id=str(i));nodes.append(topology._Node(curve,controls=controls));boxes.append(((x-guard,x+w+guard),(y-guard,y+h+guard)))
    expected={(i,j) for i,a in enumerate(boxes) for j,b in enumerate(boxes) if i<j and all(x[0]<=y[1] and y[0]<=x[1] for x,y in zip(a,b))}
    actual=list(topology._candidate_pairs(nodes,topology._Budget(100000,24,float(guard))))
    # Use exactly the float guard passed to the kernel in the independent boxes.
    g=Q(float(guard));boxes=[((a[0]+guard-g,a[1]-guard+g),(b[0]+guard-g,b[1]-guard+g)) for a,b in boxes]
    expected={(i,j) for i,a in enumerate(boxes) for j,b in enumerate(boxes) if i<j and all(x[0]<=y[1] and y[0]<=x[1] for x,y in zip(a,b))}
    assert set(actual)==expected and len(actual)==len(expected)

def test_candidate_budget_exhaustion_and_hidden_cubic_crossing_never_VALID():
    path=[['M',0,0],['C',3,1e-9,7,1e-9,10,0],['L',10,5e-10],['L',0,5e-10],['Z']]
    assert topology.certify_native_region_topology(path,max_nodes=0).status=='UNRESOLVED'
    assert topology.certify_native_region_topology(path,max_nodes=100000).status!='VALID'
