"""Independent reviewer analytic/negative curve oracles, exact source 8074d3e."""
import math

import numpy as np
import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import Curve, certify_curve, derivative, evaluate, svg_commands


def cert(c, **kwargs):
    return certify_curve(c, chord_tolerance=kwargs.pop('chord_tolerance', 0.001),
                         length_tolerance=kwargs.pop('length_tolerance', 0.001), **kwargs)


def own_svg_arcs(text):
    words=text.split()
    assert words[0]=='M'
    start=np.array([float(words[1]),float(words[2])])
    result=[]
    for index in range(3,len(words),8):
        assert words[index]=='A'
        r,ry,rotation,large,sweep,x,y=map(float,words[index+1:index+8])
        assert r==ry and rotation==0 and large==0
        end=np.array([x,y])
        dx,dy=end-start
        coefficient=math.sqrt(r*r/(dx*dx+dy*dy)-0.25)
        center=(start+end)/2+(1 if sweep else -1)*coefficient*np.array([-dy,dx])
        z0=complex(*(start-center))
        z1=complex(*(end-center))
        delta=math.atan2((z1/z0).imag,(z1/z0).real)
        if sweep and delta<0: delta+=math.tau
        if not sweep and delta>0: delta-=math.tau
        result.append((start,end,center,r,delta))
        start=end
    return result


@pytest.mark.parametrize('sweep', [1e-6, -1e-6, 0.01, -0.01, 179.999, -180.001, 359.9])
def test_own_arc_scales_flags_and_analytic_length(sweep):
    r = 3
    a = math.radians(sweep)
    c = Curve((r, 0), (r*math.cos(a), r*math.sin(a)), 'arc', {'center': (0, 0), 'sweep_deg': sweep})
    proof = cert(c)
    assert proof.status == 'CERTIFIED'
    assert proof.length_lower <= r*abs(a) <= proof.length_upper
    assert proof.length_upper-proof.length_lower <= 0.001
    native = svg_commands(c).split()
    assert len(own_svg_arcs(svg_commands(c)))==math.ceil(abs(sweep)/90)
    assert all(native[index+4:index+6]==['0',str(int(sweep>0))] for index in range(3,len(native),8))
    assert proof.regularity == 'REGULAR'


@pytest.mark.parametrize('points', [
    [(0, 0), (0, 100), (0.001, -100), (1, 0)],
    [(0, 0), (1000, 1), (-1000, -1), (0.1, 0.01)],
    [(0, 0), (20, 30), (-20, 30), (0.01, 0)],
    [(0, 0), (0, 1e-6), (1e-6, -1e-6), (1e-6, 0)],
])
def test_own_high_curvature_length_bounds_and_whole_domain(points):
    c = Curve(points[0], points[3], 'cubic', {'control1': points[1], 'control2': points[2]})
    proof = cert(c)
    assert proof.status == 'CERTIFIED'
    p = np.asarray(points)
    # Independent Bernstein polynomial speed; no evaluate/derivative helper.
    def speed(t):
        tangent = 3*((1-t)**2*(p[1]-p[0])+2*t*(1-t)*(p[2]-p[1])+t*t*(p[3]-p[2]))
        return math.hypot(*tangent)
    length, error = quad(speed, 0, 1, epsabs=1e-10, epsrel=1e-12, limit=300)
    assert error < 1e-7
    assert proof.length_lower <= length <= proof.length_upper
    assert proof.length_upper-proof.length_lower <= 0.001
    assert proof.max_chord_deviation_bound <= 0.001
    assert sum(b-a for a,b in proof.parameter_intervals) == 1
    assert proof.regularity in ('NOT_PROVEN', 'SINGULAR')


def test_own_non_dyadic_stationary_cubic_does_not_receive_regularity():
    # x=(3t-1)^3, derivative zero at t=1/3; exact monotone length 9.
    c = Curve((-1, 0), (8, 0), 'cubic', {'control1': (2, 0), 'control2': (-4, 0)})
    p = cert(c)
    assert p.status == 'CERTIFIED' and p.length_lower <= 9 <= p.length_upper
    assert p.regularity != 'REGULAR'
    assert 'no loft' in p.message


def test_own_collinear_reversal_is_not_endpoint_distance():
    c = Curve((0, 0), (0.1, 0), 'cubic', {'control1': (1, 0), 'control2': (-1, 0)})
    # x=6.1t^3-9t^2+3t. Its derivative roots partition monotone intervals.
    critical = sorted(float(x) for x in np.roots([18.3, -18, 3]) if 0 < x < 1)
    params = [0, *critical, 1]
    values = [6.1*t**3-9*t*t+3*t for t in params]
    expected = sum(abs(b-a) for a,b in zip(values,values[1:]))
    p = cert(c)
    assert p.status == 'CERTIFIED' and p.length_lower <= expected <= p.length_upper
    assert expected > 1 and p.length_lower > 1


@pytest.mark.parametrize('budget', [dict(max_segments=1), dict(max_segments=7), dict(max_depth=0)])
def test_own_budget_failure_preserves_complete_parameter_coverage(budget):
    c = Curve((0, 0), (1, 0), 'cubic', {'control1': (0, 100), 'control2': (1, -100)})
    p = cert(c, **budget)
    assert p.status == 'BUDGET_EXHAUSTED'
    assert p.parameters[0] == 0 and p.parameters[-1] == 1
    assert sum(b-a for a,b in p.parameter_intervals) == 1


@pytest.mark.parametrize('translation', [1e10, 1e100])
def test_own_coordinate_precision_guard_is_truthful(translation):
    delta = max(1, math.ulp(translation)*4)
    c = Curve((translation, 0), (translation+delta, 0))
    p = cert(c, chord_tolerance=1e-8, length_tolerance=1e-8)
    assert p.status == 'UNRESOLVED' and p.numerical_guard > 1e-8


def test_R01_native_svg_near_full_arc_must_not_certify_a_different_circle():
    epsilon = 1e-8
    sweep = 360-math.degrees(epsilon)
    c = Curve((1, 0), (1, epsilon), 'arc', {'center': (0, 0), 'sweep_deg': sweep})
    proof = cert(c)
    assert proof.status == 'CERTIFIED'
    # The semantic oracle is unchanged: native geometry must match the authored
    # circle. New writer uses multiple A commands instead of one unstable A.
    arcs=own_svg_arcs(svg_commands(c,chord_tolerance=0.001,length_tolerance=0.001))
    assert len(arcs)==4 and tuple(arcs[-1][1])==c.end
    for index,(start,end,center,r,delta) in enumerate(arcs):
        z=complex(*(start-center))
        for t in (0,0.137,0.5,0.913,1):
            point=center+np.array([(z*complex(math.cos(t*delta),math.sin(t*delta))).real,
                                   (z*complex(math.cos(t*delta),math.sin(t*delta))).imag])
            expected=evaluate(c,(index+t)/len(arcs))
            assert math.dist(point,expected)<=proof.svg_deviation_bound
    assert abs(sum(r*abs(delta) for _,_,_,r,delta in arcs)-math.radians(sweep))<=proof.svg_length_error_bound


@pytest.mark.parametrize('direction',[-1,1])
def test_R01_fixed_both_directions_native_bound_covers_center_and_parameter_errors(direction):
    epsilon=2e-8
    sweep=direction*(360-math.degrees(epsilon))
    c=Curve((2,0),(2,direction*3e-8),'arc',{'center':(0,0),'sweep_deg':sweep})
    proof=cert(c)
    assert proof.status=='CERTIFIED'
    arcs=own_svg_arcs(svg_commands(c,chord_tolerance=0.001,length_tolerance=0.001))
    for index,(start,end,center,r,delta) in enumerate(arcs):
        theta0=math.atan2(*(start-center)[::-1])
        for t in (0.037,0.237,0.537,0.937):
            point=center+r*np.array([math.cos(theta0+t*delta),math.sin(theta0+t*delta)])
            assert math.dist(point,evaluate(c,(index+t)/len(arcs)))<=proof.svg_deviation_bound
    assert abs(sum(r*abs(delta) for _,_,_,r,delta in arcs)-2*abs(math.radians(sweep)))<=proof.svg_length_error_bound


def test_R01_bad_tiny_svg_branch_is_truthfully_unresolved_and_not_strictly_published():
    c=Curve((1,0),(1,-1e-8),'arc',{'center':(0,0),'sweep_deg':math.degrees(1e-8)})
    p=cert(c)
    assert p.status=='UNRESOLVED' and p.svg_deviation_bound>0.001
    with pytest.raises(ValueError):
        svg_commands(c,chord_tolerance=0.001,length_tolerance=0.001)
