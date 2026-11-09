"""Independent analytic expectations for loft source bf1aff7, no UI proof."""
import math

import numpy as np
import pytest
from scipy.integrate import quad
from shapely import Point, Polygon
from shapely.ops import unary_union

from archpapercraft.authoring.curves import Curve, certify_curve
from archpapercraft.authoring.loft_geometry import LoftProfile, LoftCorrespondence, flatten_loft, sample_loft


def pairs(a,b,reverse=False):
    return [LoftCorrespondence(x.segment_id,y.segment_id,(1,0) if reverse else (0,1),(1,0) if reverse else (0,1)) for x,y in zip(a.curves,b.curves)]


def semicircle(r,z=0,prefix='a'):
    return LoftProfile((Curve((r,0),(-r,0),'arc',{'center':(0,0),'sweep_deg':180},prefix),),origin=(0,0,z),profile_id=prefix)


@pytest.mark.parametrize('k,H,scale', [(2,10,1),(0.5,20,1),(1.25,-12,0.1)])
def test_own_cone_global_parameter_map_matches_analytic_sector(k,H,scale):
    r=8
    a,b=semicircle(r),semicircle(r*k,H,'b')
    report=flatten_loft(a,b,pairs(a,b),scale=scale)
    assert report['status']=='EXACT', report
    R=math.hypot(r,H/(k-1))*scale
    omega=math.pi*r*scale/R
    bound=report['representation_error_bound_paper_mm']
    for u,v in [(0.137,0.31),(0.517,0.77),(0.993,0.005)]:
        observed=sample_loft(report,0,u,v)
        factor=1+v*(k-1)
        true_world=[factor*r*math.cos(math.pi*u),factor*r*math.sin(math.pi*u),H*v]
        true_flat=[factor*R*math.cos(omega*u),factor*R*math.sin(omega*u)]
        assert math.dist(observed['world_model_mm'],true_world)*scale <= bound
        assert math.dist(observed['flat_paper_mm'],true_flat) <= bound
    assert abs(report['total_developed_angle_rad']-omega) <= report['angular_error_bound_rad']
    points=report['patches'][0]['flat_first_paper_mm']
    measured=sum(math.dist(x,y) for x,y in zip(points,points[1:]))
    assert abs(measured-math.pi*r*scale)<=report['boundary_length_error_bound_paper_mm']


def test_own_B2_complete_annular_band_union_keeps_real_hole_and_whole_boundary_budget():
    def profile(r,prefix):
        points=[(r,0),(0,r),(-r,0),(0,-r),(r,0)]
        curves=tuple(Curve(x,y,'arc',{'center':(0,0),'sweep_deg':90},prefix+str(i)) for i,(x,y) in enumerate(zip(points,points[1:])))
        return LoftProfile(curves,profile_id=prefix,closed=True)
    a,b=profile(2,'a'),profile(3,'b')
    report=flatten_loft(a,b,pairs(a,b))
    assert report['status']=='EXACT',report
    material=unary_union([Polygon(p['flat_boundary_paper_mm']) for p in report['patches']])
    assert not material.covers(Point(0,0)) and material.covers(Point(0,2.5))
    assert len(material.interiors)==1
    position=report['representation_error_bound_paper_mm']
    assert abs(material.area-5*math.pi)<10*math.pi*position
    for key,r in [('flat_first_paper_mm',2),('flat_second_paper_mm',3)]:
        length=sum(math.dist(x,y) for p in report['patches'] for x,y in zip(p[key],p[key][1:]))
        assert abs(2*math.pi*r-length)<=report['boundary_length_error_bound_paper_mm']


def test_own_B1_pointed_two_arc_profile_stays_corner_not_tessellation_fold():
    def gothic(k,z,prefix):
        apex=(0,k*math.sqrt(3))
        return LoftProfile((
            Curve((-k,0),apex,'arc',{'center':(k,0),'sweep_deg':-60},prefix+'left'),
            Curve(apex,(k,0),'arc',{'center':(-k,0),'sweep_deg':-60},prefix+'right'),
        ),origin=(0,0,z),profile_id=prefix)
    a,b=gothic(1,0,'a'),gothic(2,3,'b')
    report=flatten_loft(a,b,pairs(a,b))
    assert report['status']=='EXACT',report
    left,right=report['patches']
    assert right['join_before_kind']=='FOLD_CREASE'
    assert left['flat_first_paper_mm'][-1]==pytest.approx(right['flat_first_paper_mm'][0])
    assert left['flat_second_paper_mm'][-1]==pytest.approx(right['flat_second_paper_mm'][0])
    assert all(p['interior_tessellation_role']=='DISPLAY_ONLY_NOT_FOLD' for p in report['patches'])


@pytest.mark.parametrize('k',[-1,-1.4,0])
def test_own_collapsed_homothety_has_analytic_singular_parameter(k):
    a=LoftProfile((Curve((1,0),(0,1),segment_id='a'),))
    b=LoftProfile((Curve((k,0),(0,k),segment_id='b'),),origin=(0,0,5)) if k else LoftProfile((Curve((0,0),(0,1),segment_id='b'),),origin=(0,0,5))
    report=flatten_loft(a,b,pairs(a,b))
    if k:
        assert report['status']=='REJECTED' and report['family']=='SINGULAR_HOMOTHETY'
        assert report['witness']['v']==pytest.approx(1/(1-k))
    else:
        assert report['status']!='EXACT'


def test_own_B3_twisted_arc_is_negative_not_exact_sample_zero():
    a=semicircle(8)
    angle=math.pi/6
    b=LoftProfile((Curve((12,0),(-12,0),'arc',{'center':(0,0),'sweep_deg':180},'b'),),origin=(0,0,10),u=(math.cos(angle),math.sin(angle),0),v=(-math.sin(angle),math.cos(angle),0))
    report=flatten_loft(a,b,pairs(a,b))
    assert report['status']=='REJECTED' and report['family']=='NONDEVELOPABLE'
    assert abs(report['witness']['determinant'])>report['witness']['numerical_reserve']


@pytest.mark.parametrize('reverse',[False,True])
def test_own_source_interval_orientation_maps_forward_and_reverse(reverse):
    a,b=semicircle(3),semicircle(3,5,'b')
    report=flatten_loft(a,b,pairs(a,b,reverse=reverse))
    assert report['status']=='EXACT'
    u=0.217
    expected_t=1-u if reverse else u
    p=sample_loft(report,0,u,0.4)
    expected=[3*math.cos(math.pi*expected_t),3*math.sin(math.pi*expected_t),2]
    assert math.dist(p['world_model_mm'],expected)<=report['representation_error_bound_paper_mm']
    assert report['patches'][0]['source_parameters'][0]==([1,1] if reverse else [0,0])


@pytest.mark.parametrize('which',['stationary','partial','budget'])
def test_own_unsupported_scope_does_not_return_exact(which):
    a,b=semicircle(8),semicircle(12,10,'b')
    refs=pairs(a,b)
    kwargs={}
    if which=='stationary':
        c=Curve((-1,0),(8,0),'cubic',{'control1':(2,0),'control2':(-4,0)},'a')
        d=Curve(c.start,c.end,'cubic',dict(c.data),'b')
        a,b=LoftProfile((c,)),LoftProfile((d,),origin=(0,0,5))
        refs=pairs(a,b)
    elif which=='partial':
        refs=[LoftCorrespondence('a','b',(0.2,0.7),(0.2,0.7))]
    else:
        kwargs['max_segments']=2
    assert flatten_loft(a,b,refs,**kwargs)['status']!='EXACT'


def test_L01_parameterwise_cubic_extrusion_error_is_not_geometric_chord_deviation():
    c=Curve((0,0),(6,0),'cubic',{'control1':(1,0),'control2':(3,0)},'a')
    d=Curve(c.start,c.end,'cubic',dict(c.data),'b')
    a,b=LoftProfile((c,)),LoftProfile((d,),origin=(0,0,10))
    report=flatten_loft(a,b,pairs(a,b))
    assert report['status']=='EXACT'
    observed=sample_loft(report,0,0.5,0.5)
    # C(t)=(3t+3t^2,0), speed >=3, exact arclength=3t+3t^2.
    bound=report['representation_error_bound_paper_mm']
    assert math.dist(observed['world_model_mm'],[2.25,0,5])<=bound
    assert math.dist(observed['flat_paper_mm'],[2.25,5])<=bound


@pytest.mark.parametrize('scale',[1.0,0.1])
def test_L01_fix_global_prefix_plus_parameter_bounds_and_actual_largest_step(scale):
    first=[Curve((0,0),(6,3),'cubic',{'control1':(1,0),'control2':(3,1)},'a0'),
           Curve((6,3),(12,6),'cubic',{'control1':(7,3),'control2':(9,4)},'a1')]
    second=[Curve(c.start,c.end,c.kind,dict(c.data),'b'+str(i)) for i,c in enumerate(first)]
    a,b=LoftProfile(tuple(first)),LoftProfile(tuple(second),origin=(0,0,-7))
    report=flatten_loft(a,b,pairs(a,b),scale=scale)
    assert report['status']=='EXACT',report
    gap=report['arclength_prefix_error_bound_paper_mm']
    interpolation=report['parameter_interpolation_error_bound_paper_mm']
    rounding=report['node_rounding_reserve_paper_mm']
    bound=report['representation_error_bound_paper_mm']
    assert bound>=gap+interpolation+rounding
    # C''=(6,6), so interpolation bound must cover the largest delivered du.
    max_step=max(y-x for p in report['patches'] for x,y in zip(p['parameters'],p['parameters'][1:]))
    source_guard=certify_curve(first[0],chord_tolerance=0.001,length_tolerance=0.001).numerical_guard
    assert interpolation>=scale*(math.sqrt(72)*max_step**2/8+source_guard)
    full_length=quad(lambda t:math.hypot(3+6*t,6*t),0,1,epsabs=1e-12)[0]
    for index in range(2):
        for u,v in [(0.013,0.1),(0.117,0.9),(0.499,0.7),(0.713,0.4),(0.997,0.8)]:
            observed=sample_loft(report,index,u,v)
            expected_world=[6*index+3*u+3*u*u,3*index+3*u*u,-7*v]
            local_length=quad(lambda t:math.hypot(3+6*t,6*t),0,u,epsabs=1e-12)[0]
            expected_flat=[(index*full_length+local_length)*scale,7*v*scale]
            assert math.dist(observed['world_model_mm'],expected_world)*scale<=bound
            assert math.dist(observed['flat_paper_mm'],expected_flat)<=bound
    assert flatten_loft(a,b,pairs(a,b),scale=scale,max_segments=2)['status']=='UNRESOLVED'
