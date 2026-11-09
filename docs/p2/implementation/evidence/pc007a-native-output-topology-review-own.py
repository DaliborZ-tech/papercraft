"""Independent exact native-command topology and material separation oracles."""
from decimal import Decimal
from fractions import Fraction

import pytest

from archpapercraft.authoring.curve_topology import (
    certify_native_region_topology as topology,
    certify_native_region_separation as separation,
)


def rect(x0,y0,x1,y1):
    return (('M',x0,y0),('L',x1,y0),('L',x1,y1),('L',x0,y1),('Z',))


def circle(x,y,r):
    return (('M',x+r,y),('A',r,r,0,0,1,x,y+r),('A',r,r,0,0,1,x-r,y),
            ('A',r,r,0,0,1,x,y-r),('A',r,r,0,0,1,x+r,y),('Z',))


def separate(a,b,ah=(),bh=(),**kwargs):
    return separation(a,ah,b,bh,**kwargs)


@pytest.mark.parametrize('shift',[0,10**6])
def test_own_raw_decimal_hidden_crossing_not_erased_by_float_roundtrip(shift):
    d=Fraction(1,10**150)
    y=Fraction(shift)+1
    path=(('M',0,y+d),('C',1,y-d,2,y-d,3,y+d),('L',3,y),('L',0,y),('Z',))
    result=topology(path)
    assert result.status=='INVALID',result
    assert result.witness['line_side_values_exact']
    assert Fraction(result.witness['line_side_values_exact'][0])*Fraction(result.witness['line_side_values_exact'][1])<0


def test_own_exact_mixed_scalar_winding_real_hole_and_orientation():
    outer=rect(Decimal('-5.5'),'-5.5',Fraction(11,2),'5.5')
    hole=(('M','-1','-1'),('L','-1','1'),('L','1','1'),('L','1','-1'),('Z',))
    assert topology(outer,(hole,)).status=='VALID'
    assert separate(outer,rect('-0.5','-0.5','0.5','0.5'),ah=(hole,)).status=='DISJOINT'


@pytest.mark.parametrize('touching',[rect(1,0,2,1),rect(1,1,2,2)])
def test_own_zero_area_edge_or_corner_touch_is_not_positive_overlap(touching):
    assert separate(rect(0,0,1,1),touching).status=='UNRESOLVED'


@pytest.mark.parametrize('d',[Fraction(1,100),Fraction(1,10**40)])
def test_own_positive_gap_never_invents_overlap(d):
    result=separate(rect(0,0,1,1),rect(1+d,0,2,1))
    assert result.status in ('DISJOINT','UNRESOLVED'),result


@pytest.mark.parametrize('d',[Fraction(1,100),Fraction(1,10**40)])
def test_own_positive_area_sliver_never_becomes_disjoint(d):
    result=separate(rect(0,0,1,1),rect(1-d,Fraction(1,4),2,Fraction(3,4)))
    assert result.status in ('OVERLAP','UNRESOLVED'),result
    if d==Fraction(1,100):
        assert result.status=='OVERLAP'


def test_own_far_holes_cannot_delete_certified_overlap_of_unrelated_material():
    a=rect(0,0,100,100)
    b=rect(-1,-1,5,5)
    before=separate(a,b)
    after=separate(a,b,ah=(rect(80,80,90,90),))
    assert before.status==after.status=='OVERLAP'


def test_own_annulus_contains_island_in_void_but_not_its_material_ring():
    a=rect(0,0,10,10)
    hole=rect(2,2,8,8)
    inside_void=rect(3,3,7,7)
    inside_ring=rect(Fraction(1,2),Fraction(1,2),1,1)
    assert separate(a,inside_void,ah=(hole,)).status=='DISJOINT'
    assert separate(inside_void,a,bh=(hole,)).status=='DISJOINT'
    assert separate(a,inside_ring,ah=(hole,)).status=='OVERLAP'
    assert separate(inside_ring,a,bh=(hole,)).status=='OVERLAP'


def test_own_two_nested_annular_materials_keep_correct_winding_side():
    a,b=rect(0,0,10,10),rect(1,1,9,9)
    ah,bh=(rect(2,2,8,8),),(rect(Fraction(3,2),Fraction(3,2),Fraction(17,2),Fraction(17,2)),)
    assert separate(a,b,ah,bh).status=='OVERLAP'


@pytest.mark.parametrize('shift',[0,30])
def test_own_actual_quarter_circle_crossing_and_disjoint_material(shift):
    a=circle(0,0,3)
    b=rect(2+shift,-1,4+shift,1)
    result=separate(a,b)
    assert result.status==('OVERLAP' if shift==0 else 'DISJOINT'),result


def test_own_circle_inside_circle_hole_is_disjoint_actual_native_geometry():
    assert separate(circle(0,0,5),circle(0,0,1),ah=(circle(0,0,2),)).status=='DISJOINT'


def test_own_unsupported_or_invalid_region_cannot_certify_disjoint_material():
    malformed=(('M',0,0),('L',1,1))
    crossed=(('M',0,0),('L',2,2),('L',0,2),('L',2,0),('Z',))
    for invalid in (malformed,crossed):
        assert separate(rect(10,10,11,11),invalid).status=='UNRESOLVED'


@pytest.mark.parametrize('limits',[{'max_nodes':0},{'max_nodes':1},{'max_depth':0,'max_nodes':10}])
def test_own_global_budget_cannot_grant_disjoint_or_overlap(limits):
    assert separate(circle(0,0,3),circle(2,0,3),**limits).status=='UNRESOLVED'


def test_own_implicit_z_edge_is_part_of_topology_not_missing_coverage():
    path=(('M',0,0),('L',3,3),('L',0,3),('L',3,0),('Z',))
    assert topology(path).status=='INVALID'


def test_own_unclosed_subpath_and_unsupported_ellipse_never_become_valid():
    paths=[(('M',0,0),('L',2,0),('L',0,2)),
           (('M',1,0),('A',1,2,0,0,1,0,1),('Z',))]
    assert all(topology(path).status=='UNRESOLVED' for path in paths)
