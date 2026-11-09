"""Independent topology oracles; no sampled polygon grants positive proof."""
import math

import pytest

from archpapercraft.authoring.curves import Curve, svg_commands
from archpapercraft.authoring.curve_topology import certify_region_topology


def polygon(points,prefix='p'):
    return tuple(Curve(a,b,segment_id=prefix+str(i)) for i,(a,b) in enumerate(zip(points,points[1:]+points[:1])))


def circle(x,y,r,prefix='c'):
    a,b=(x+r,y),(x-r,y)
    return (Curve(a,b,'arc',{'center':(x,y),'sweep_deg':180},prefix+'0'),
            Curve(b,a,'arc',{'center':(x,y),'sweep_deg':180},prefix+'1'))


@pytest.mark.parametrize('epsilon',[1e-6,1e-9,1e-12])
def test_own_hidden_cubic_crossing_is_invalid_even_when_chord_is_rectangle(epsilon):
    a,b=(0,epsilon),(10,epsilon)
    c=Curve(a,b,'cubic',{'control1':(3,-epsilon),'control2':(7,-epsilon)},'hidden')
    boundary=(c,Curve(b,(10,0)),Curve((10,0),(0,0)),Curve((0,0),a))
    result=certify_region_topology(boundary)
    assert result.status=='INVALID',result
    assert result.witness is not None


def test_own_adjacent_cubic_second_crossing_not_waived_by_shared_endpoint():
    c=Curve((4,4),(0,0),'cubic',{'control1':(-1,3),'control2':(-0.01,0.2)},'return')
    result=certify_region_topology((Curve((0,0),(0,4)),Curve((0,4),(4,4)),c))
    assert result.status=='INVALID',result


def test_own_disjoint_holes_inside_annular_like_native_boundary():
    outer=circle(0,0,10)
    holes=(circle(-3,0,1,'left'),circle(3,0,1,'right'))
    result=certify_region_topology(outer,holes)
    assert result.status=='VALID',result


def test_own_nested_and_outside_holes_have_hard_witnesses():
    result=certify_region_topology(circle(0,0,10),(circle(0,0,4,'h0'),circle(0,0,1,'h1')))
    assert result.status=='INVALID' and 'nested' in result.reason.lower()
    result=certify_region_topology(circle(0,0,10),(circle(12,0,1,'h'),))
    assert result.status=='INVALID' and 'outside' in result.reason.lower()


@pytest.mark.parametrize('offset',[0,1e-12])
def test_own_coincident_or_crossing_circle_holes_never_pass(offset):
    result=certify_region_topology(circle(0,0,10),(circle(0,0,1,'a'),circle(offset,0,1,'b')))
    assert result.status!='VALID',result


@pytest.mark.parametrize('delta',[1e-14,math.ulp(1.0),math.ulp(1.0)/2])
def test_T01_small_endpoint_constraint_cannot_fabricate_native_intersection(delta):
    x=1+delta/2
    arc=Curve((0,1),(1,0),'arc',{'center':(delta,0),'sweep_deg':-90},'native-quarter')
    assert svg_commands(arc)=='M 0 1 A 1 1 0 0 0 1 0'
    if x==1:
        # The expression has rounded onto the actual native boundary. We avoid
        # a zero-length authored line and make the contact explicit instead.
        boundary=(arc,Curve((1,0),(1,2)),Curve((1,2),(0,2)),Curve((0,2),(0,1)))
    else:
        boundary=(arc,Curve((1,0),(x,0)),Curve((x,0),(x,2)),Curve((x,2),(0,2)),Curve((0,2),(0,1)))
    result=certify_region_topology(boundary)
    # Native unit quarter has x<=1. The short outward bridge followed by
    # vertical x>=1 creates a simple closed Jordan boundary. Precision may
    # remain unknown, but a nominal-center intersection is not a true witness.
    assert result.status!='INVALID',result


def test_own_both_semicircle_directions_form_simple_material_with_real_hole():
    upper,lower=circle(0,0,5)
    outer=(Curve(lower.end,lower.start,'arc',{'center':(0,0),'sweep_deg':-180},'r0'),
           Curve(upper.end,upper.start,'arc',{'center':(0,0),'sweep_deg':-180},'r1'))
    assert certify_region_topology(outer,(circle(0,0,1),)).status=='VALID'


@pytest.mark.parametrize('limit',[0,1,2])
def test_own_global_budget_exhaustion_never_grants_valid(limit):
    result=certify_region_topology(circle(0,0,10),(circle(3,0,1),),max_nodes=limit)
    assert result.status=='UNRESOLVED',result


def test_own_source_tangent_hole_requires_strict_separation_not_point_sampling():
    result=certify_region_topology(circle(0,0,10),(circle(9,0,1,'t'),),max_nodes=1000)
    assert result.status!='VALID'
