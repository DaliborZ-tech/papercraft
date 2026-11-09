"""Independent exact polynomial, pi and positive arcsin-series area oracles."""
import copy
from decimal import Decimal
from fractions import Fraction as Q
import math
import os
from pathlib import Path

import pytest
from archpapercraft.authoring.curve_area import native_region_area_bounds
import archpapercraft.authoring.curve_area as actual

assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())
PI_LO=Q('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')
PI_HI=PI_LO+Q(1,10**100)

def root(q):
    den=1<<400;k=math.isqrt(q.numerator*den*den//q.denominator)
    return Q(k,den),Q(k if k*k*q.denominator==q.numerator*den*den else k+1,den)

def minor_segment(radius,chord):
    """Area r²(asin x-x sqrt(1-x²)), independent of endpoint atan/center code."""
    radius,chord=Q(radius),Q(chord);x=chord/(2*radius);assert 0<x<=Q(1,2)
    total=Q(0)
    for n in range(256):
        total+=Q(math.comb(2*n,n),4**n*(2*n+1))*x**(2*n+1)
        following=Q(math.comb(2*n+2,n+1),4**(n+1)*(2*n+3))*x**(2*n+3)
        # Consecutive positive terms have ratio strictly less than x².
        tail=following/(1-x*x)
        if tail*radius*radius<Q(1,10**90):break
    else:raise AssertionError('Independent arcsin oracle did not converge')
    lo,hi=root(1-x*x)
    return radius*radius*(total-x*hi),radius*radius*(total+tail-x*lo)

def encloses(actual_bounds,expected):
    lo,hi=actual_bounds;a,b=expected
    assert isinstance(lo,Q) and isinstance(hi,Q)
    assert lo<=a<=b<=hi,(float(lo),float(a),float(b),float(hi))
    assert lo.denominator<=10**24 and hi.denominator<=10**24

def rectangle(x,y,w,h,reverse=False):
    points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    if reverse:points.reverse()
    return [('M',*points[0]),*[('L',*p) for p in points[1:]],('Z',)]

def circular_segment(radius,chord,large,sweep,shift=(Q(0),Q(0))):
    x,y=shift
    return [('M',x-Q(chord)/2,y),('A',radius,radius,Decimal('137.25'),large,sweep,x+Q(chord)/2,y),('Z',)]

@pytest.mark.parametrize('large',[0,1])
@pytest.mark.parametrize('sweep',[0,1])
@pytest.mark.parametrize('radius,chord',[(1,1),(7,2),(10**8,1)])
def test_minor_major_and_reversed_endpoint_arcs(radius,chord,large,sweep):
    small=minor_segment(radius,chord)
    expected=(radius*radius*PI_LO-small[1],radius*radius*PI_HI-small[0]) if large else small
    encloses(native_region_area_bounds([circular_segment(radius,chord,large,sweep)]),expected)

@pytest.mark.parametrize('shift',[Q(10)**20,-Q(10)**70])
def test_translation_of_curved_loop_preserves_area_at_large_exact_coordinates(shift):
    expected=minor_segment(5,3)
    encloses(native_region_area_bounds([circular_segment(5,3,0,1,(shift,-shift))]),expected)

@pytest.mark.parametrize('large,sweep',[(0,0),(0,1),(1,0),(1,1)])
def test_svg_radius_correction_has_actual_semicircle_area(large,sweep):
    # Chord6 forces r3 even when the declared radius is only1/10.
    encloses(native_region_area_bounds([circular_segment(Q(1,10),6,large,sweep)]),(Q(9,2)*PI_LO,Q(9,2)*PI_HI))

def circle(r,cx=0,cy=0,sweep=1):
    return [('M',cx+r,cy),('A',r,r,0,0,sweep,cx-r,cy),('A',r,r,0,0,sweep,cx+r,cy),('Z',)]

def arch(w,h,cx=0,cy=0,reverse=False):
    if reverse:return [('M',cx,cy),('L',cx+w,cy),('C',cx+w,cy+h,cx,cy+h,cx,cy),('Z',)]
    return [('M',cx,cy),('C',cx,cy+h,cx+w,cy+h,cx+w,cy),('Z',)]

@pytest.mark.parametrize('reverse',[False,True])
def test_exact_cubic_arch_and_net_holes_with_decimal_tokens(reverse):
    # x=w(3t²-2t³),y=3h(t-t²); |int y dx|=3wh/5.
    hole=arch(Q(7),Q(5),Q(2),Q(3),reverse)
    assert native_region_area_bounds([hole])==(21,21)
    outer=rectangle(Q(0),Q(0),Q(50),Q(40),not reverse)
    second=circle(Q(2),Q(20),Q(20),int(reverse))
    loops=[hole,second,outer];saved=copy.deepcopy(loops)
    encloses(native_region_area_bounds(loops),(1979-4*PI_HI,1979-4*PI_LO))
    assert loops==saved

def test_actual_cubic_circle_has_its_own_exact_area_not_nominal_pi():
    k=Q('0.55');r=Q(3);h=k*r
    loop=[('M',r,0),('C',r,h,h,r,0,r),('C',-h,r,-r,h,-r,0),('C',-r,-h,-h,-r,0,-r),('C',h,-r,r,-h,r,0),('Z',)]
    expected=r*r*(2+Q(12,5)*k-Q(3,5)*k*k)
    assert native_region_area_bounds([loop])==(expected,expected)
    assert 9*PI_LO-expected>Q(1,100)

def test_exact_large_translated_cubic_and_tiny_outward_quantization():
    shift=Q(10)**100
    expected=Q(3,5)*Q(7,3)*Q(5,7)
    encloses(native_region_area_bounds([arch(Q(7,3),Q(5,7),shift,-shift)]),(expected,expected))
    tiny=Q(1,10**20)
    encloses(native_region_area_bounds([rectangle(Q(0),Q(0),tiny,tiny)]),(tiny*tiny,tiny*tiny))

@pytest.mark.parametrize('damage',[
    [('M',0,0),('C',1,2,3,4,5),('Z',)],
    [('M',0,0),('C',1,2,3,4,float('nan'),6),('Z',)],
    [('M',0,0),('Z',)],[],
    [('M',0,0),('A',1,2,0,0,1,1,0),('Z',)],
    [('M',0,0),('A',1,1,0,Q(1,2),1,1,0),('Z',)],
    [('M',0,0),('A',1,1,0,0,True,1,0),('Z',)],
    [('M',0,0),('L','1e9999',0),('Z',)],
    [('M',0,0),('L','1'*4097,0),('Z',)],
    [('M',0,0),('L',1,1),('M',2,2),('Z',)],
    [('M',0,0),('L',1,1),('Z',),('L',2,2)],
    [('M',0,0),('L',1,1)]])
def test_malformed_unsupported_or_unbounded_input_is_refused(damage):
    with pytest.raises(ValueError):native_region_area_bounds([damage])

@pytest.mark.parametrize('budget',[0,-1,True,3.0])
def test_invalid_command_budget(budget):
    with pytest.raises(ValueError):native_region_area_bounds([rectangle(0,0,2,3)],max_commands=budget)

def test_iterator_budget_is_global_and_no_partial_certificate():
    commands=rectangle(0,0,10,10);holes=rectangle(1,1,2,2)
    with pytest.raises(ValueError,match='budget'):native_region_area_bounds((iter(x) for x in [commands,holes]),max_commands=9)
    assert native_region_area_bounds((iter(x) for x in [commands,holes]),max_commands=10)==(96,96)

def test_empty_or_ambiguous_outer_refused_and_hole_order_winding_irrelevant():
    with pytest.raises(ValueError):native_region_area_bounds([])
    with pytest.raises(ValueError):native_region_area_bounds([rectangle(0,0,2,2),rectangle(0,0,2,2)])
    assert native_region_area_bounds([rectangle(2,2,3,4,True),rectangle(0,0,20,20),rectangle(8,8,2,5)])==(378,378)
