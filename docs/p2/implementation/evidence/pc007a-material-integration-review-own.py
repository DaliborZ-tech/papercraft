"""Independent bounded planar material, contact and continuous-fold review."""
import copy
import math

import numpy as np
import pytest
from shapely import MultiPolygon, Point, Polygon

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.attachments import source_outward
from archpapercraft.authoring.bend import _guaranteed_triangles
from archpapercraft.authoring.clearance import FoldSweep, MaterialObstacle, MaterialProfile, ContactAllowance, check_fold_clearance
from archpapercraft.authoring.curve_material import surface_envelopes
from archpapercraft.authoring.curves import evaluate
from archpapercraft.authoring.profile_curves import source_curve


def circle(p,r=1,center=(0,0),offset=0,plane=None):
    a=[center[0]+r*math.cos(offset),center[1]+r*math.sin(offset)]
    b=[center[0]-r*math.cos(offset),center[1]-r*math.sin(offset)]
    return p.add_profile(segments=[{'kind':'arc','start':a,'end':b,'data':{'center':list(center),'sweep_deg':180}},
                                   {'kind':'arc','start':b,'end':a,'data':{'center':list(center),'sweep_deg':180}}],plane=plane)


def fold_scene(known):
    p=AuthorProject.new(scale=1)
    profile=p.add_profile([[20,0],[60,0],[60,20],[20,20]],plane={'origin':[0,5,0],'u':[1,0,0],'v':[0,0,1]})
    wall=p.add_surface(profile)
    base=p.add_surface(p.add_profile([[0,0],[100,0],[100,100],[0,100]]))
    aid=p.attach_edge_to_surface(wall,p.profiles[profile].segments[0].id,base,target_side='outside',glue_direction=-1)
    cid=p.set_attachment_tab(aid,width_mm=5,taper=1)
    if known:p.set_material_profile(thickness_mm=0.2)
    return p,cid


@pytest.mark.parametrize('known',[False,True])
def test_own_sixty_degree_native_bulge_witness_is_not_missed_by_chords(known):
    p,cid=fold_scene(known)
    epsilon=(1-math.cos(math.pi/64))/2
    y=5-4*math.sin(math.pi/3)
    pid=circle(p,center=(19+epsilon,-2),offset=math.pi/64,plane={'origin':[0,y,0],'u':[1,0,0],'v':[0,0,1]})
    obstacle=p.add_surface(pid)
    witness=(20+epsilon/2,-2)
    assert (witness[0]-(19+epsilon))**2<1
    assert not Polygon(p.profile_outline(pid)).covers(Point(witness))
    # At -60 degrees, rho=4 gives exactly y=5-4*sin60 and z=-2;
    # both endpoint poses avoid this circle plane/material.
    result=p.connector_bend_clearance(cid)
    assert result['status']=='UNRESOLVED',result
    detail=result['tabs'][0]
    assert obstacle in detail['expected_obstacle_ids']
    assert detail['material_envelopes']['bounds'][obstacle]['possible_material_fully_covered']
    assert detail['material_envelopes']['guaranteed_check']['status']!='COLLISION'
    assert detail['material_envelopes']['possible_check']['status']!='CLEAR'


@pytest.mark.parametrize('known',[False,True])
def test_own_guaranteed_mid_sweep_collision_survives_extra_far_curve_uncertainty(known):
    p,cid=fold_scene(known)
    plane={'origin':[0,5-4*math.sin(math.pi/3),0],'u':[1,0,0],'v':[0,0,1]}
    certain=p.add_surface(circle(p,center=(30,-2),offset=math.pi/64,plane=plane))
    first=p.connector_bend_clearance(cid)
    assert first['status']=='COLLISION' and first['tabs'][0]['obstacle_id']==certain
    far=p.add_surface(circle(p,center=(80,-2),offset=math.pi/64,plane=plane))
    after=p.connector_bend_clearance(cid)
    assert after['status']=='COLLISION' and after['tabs'][0]['obstacle_id']==certain
    assert far in after['tabs'][0]['expected_obstacle_ids']
    assert after['tabs'][0]['material_envelopes']['guaranteed_check']['status']=='COLLISION'


def contact_receiver():
    p=AuthorProject.new(scale=1)
    outer=p.add_profile([[-10,-10],[10,-10],[10,10],[-10,10]])
    hole=circle(p,r=5)
    receiver=p.add_surface(outer,[hole])
    return p,receiver


def small_trace(p,center,tangent,depth=0.01,length=0.0001):
    n=np.array([tangent[1],-tangent[0]])
    a,b=np.asarray(center)-length/2*tangent,np.asarray(center)+length/2*tangent
    pid=p.add_profile([a.tolist(),b.tolist(),(b+depth*n).tolist(),(a+depth*n).tolist()])
    return p.add_surface(pid),p.profiles[pid].segments[0].id


def test_own_contact_between_nodes_inside_true_hole_is_unknown_not_fake_receiver():
    p,receiver=contact_receiver()
    theta=math.pi/128
    normal=np.array([math.cos(theta),math.sin(theta)])
    tangent=np.array([-normal[1],normal[0]])
    sagitta=5*(1-math.cos(theta))
    center=(5-sagitta/2)*normal
    source,edge=small_trace(p,center,tangent)
    assert np.linalg.norm(center)<5
    before=copy.deepcopy(p.to_dict())
    with pytest.raises(ValidationError,match='CURVE_CONTACT_UNRESOLVED'):
        p.attach_edge_to_surface(source,edge,receiver)
    assert p.to_dict()==before


def test_own_clear_receiver_margin_and_known_void_remain_distinct():
    p,receiver=contact_receiver()
    source,edge=small_trace(p,[8,0],np.array([0.,1.]),length=0.1)
    aid=p.attach_edge_to_surface(source,edge,receiver)
    assert p.attachment_geometry(aid)['valid']
    bad,edge=small_trace(p,[0,0],np.array([1.,0.]),depth=1,length=1)
    with pytest.raises(ValidationError,match='TRACE_OUTSIDE_MATERIAL'):
        p.attach_edge_to_surface(bad,edge,receiver)


def test_own_whole_curved_source_is_refused_but_explicit_patch_remains_supported():
    p=AuthorProject.new(scale=1)
    source=p.add_surface(circle(p,r=2))
    receiver=p.add_surface(p.add_profile([[-5,-5],[5,-5],[5,5],[-5,5]]))
    target=[[-4,-4],[4,-4],[4,4],[-4,4]]
    with pytest.raises(ValidationError,match='CURVE_SOURCE_REGION_UNRESOLVED'):
        p.set_glue_region(source,receiver,target)
    patch=[[-0.5,-0.5],[0.5,-0.5],[0.5,0.5],[-0.5,0.5]]
    aid=p.set_glue_region(source,receiver,target,source_outline_uv=patch)
    assert p.attachment_geometry(aid)['available_area_mm2']==pytest.approx(1)


def test_own_straight_diameter_outward_comes_from_true_semidisk_not_endpoint_polygon():
    p=AuthorProject.new(scale=1)
    pid=p.add_profile(segments=[{'kind':'arc','start':[-3,0],'end':[3,0],'data':{'center':[0,0],'sweep_deg':-180}},
                               {'kind':'line','start':[3,0],'end':[-3,0]}])
    sid=p.add_surface(pid)
    _,outward=source_outward(p,sid,p.profiles[pid].segments[1].id)
    assert outward==pytest.approx([0,-1])


@pytest.mark.parametrize('bend',[0,1e-12])
def test_own_collinear_cubic_image_exactness_does_not_reparameterize_source(bend):
    p=AuthorProject.new(scale=1)
    pid=p.add_profile(segments=[{'kind':'cubic','start':[0,0],'end':[6,0],'control1':[1,bend],'control2':[3,0]},
                               {'kind':'line','start':[6,0],'end':[6,3]},
                               {'kind':'line','start':[6,3],'end':[0,3]},
                               {'kind':'line','start':[0,3],'end':[0,0]}])
    sid=p.add_surface(pid)
    source=source_curve(p.profiles[pid],p.profiles[pid].segments[0])
    assert evaluate(source,0.5)[0]==2.25
    bounds=surface_envelopes(p,sid)
    assert bounds.is_exact == (bend==0)
    assert p.profiles[pid].segments[0].kind=='cubic'


def test_own_guaranteed_multipolygon_and_hole_triangles_never_fill_void():
    first=Polygon([(0,0),(4,0),(4,4),(0,4)],[[(1,1),(3,1),(3,3),(1,3)]])
    second=Polygon([(10,0),(12,0),(12,2),(10,2)])
    faces,omitted=_guaranteed_triangles(MultiPolygon([first,second]))
    assert omitted==0 and sum(Polygon(f).area for f in faces)==pytest.approx(16)
    assert all(not Polygon(f).covers(Point(2,2)) for f in faces)
    assert any(Polygon(f).covers(Point(11,1)) for f in faces)


def kernel_scene():
    sweep=FoldSweep([[[0,0,0],[2,0,0],[2,0,-2],[0,0,-2]]],[0,0,0],[2,0,0],-90,'source','receiver',[0,1,0],[0,0,-1])
    empty=[MaterialObstacle(sid,np.empty((0,3,3)),0.1) for sid in ('source','receiver')]
    return sweep,empty


def test_own_empty_lower_ids_have_explicit_scope_and_default_still_refuses():
    sweep,obstacles=kernel_scene()
    args={'expected_obstacle_ids':['source','receiver']}
    assert check_fold_clearance(sweep,MaterialProfile(0.1),obstacles,**args).status=='UNRESOLVED'
    lower=check_fold_clearance(sweep,MaterialProfile(0.1),obstacles,lower_bound_only=True,**args)
    assert lower.status=='CLEAR' and lower.material_domain=='GUARANTEED_LOWER_BOUND_ONLY'
    assert set(lower.empty_obstacle_ids)=={'source','receiver'}


def test_own_all_angle_aabb_does_not_prune_midpoint_collision_or_drop_far_identity():
    sweep,obstacles=kernel_scene()
    obstacles.extend([MaterialObstacle('mid',[[[0.5,-1,-1.2],[1.5,-1,-1.2],[1.5,-1,-0.8]],[[0.5,-1,-1.2],[1.5,-1,-0.8],[0.5,-1,-0.8]]],0.1),
                      MaterialObstacle('far',[[[10,-1,-1],[12,-1,-1],[12,-1,1]]],0.1)])
    result=check_fold_clearance(sweep,MaterialProfile(0.1),obstacles,expected_obstacle_ids=[o.id for o in obstacles],lower_bound_only=True)
    assert result.status=='COLLISION' and result.obstacle_id=='mid'
    assert set(result.checked_obstacle_ids)=={o.id for o in obstacles}
    assert any(row['obstacle_id']=='far' and row['disjoint_full_sweep_triangles'] for row in result.broad_phase_pruning)


def test_own_permission_pruning_requires_whole_angular_domain_not_only_final_phase():
    sweep,obstacles=kernel_scene()
    obstacles[0]=MaterialObstacle('source',[[[0,0,0],[2,0,0],[2,0,1]],[[0,0,0],[2,0,1],[0,0,1]]],0.1,'source')
    box=[[x,y,z] for x in (-0.2,2.2) for y in (-0.2,0.2) for z in (-0.2,0.2)]
    def check(interval):
        return check_fold_clearance(sweep,MaterialProfile(0.1),obstacles,expected_obstacle_ids=['source','receiver'],lower_bound_only=True,
            allowances=[ContactAllowance('source','hinge',box,interval,'Finite independent crease permission')])
    late=check((-90,-70))
    assert late.status=='COLLISION',late
    assert not any(row['interaction_inside_whole_fold_permission_triangles'] for row in late.broad_phase_pruning)
    full=check((-90,0))
    assert full.status=='CLEAR',full
    assert any(row['interaction_inside_whole_fold_permission_triangles'] for row in full.broad_phase_pruning)
