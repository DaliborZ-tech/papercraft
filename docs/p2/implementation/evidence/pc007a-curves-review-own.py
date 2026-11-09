"""Independent reviewer analytic/negative curve oracles, exact source 8074d3e."""
import math

import numpy as np
import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import Curve, certify_curve, derivative, evaluate, svg_commands


def cert(c, **kwargs):
    return certify_curve(c, chord_tolerance=kwargs.pop('chord_tolerance', 0.001),
                         length_tolerance=kwargs.pop('length_tolerance', 0.001), **kwargs)


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
    assert native[7:9] == [str(int(abs(sweep)>180)), str(int(sweep>0))]
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
    assert proof.status == 'CERTIFIED'  # Actual problematic result at reviewed source.
    # SVG large-arc=1, sweep=1 and these endpoints/radius choose the right-hand
    # center (perpendicular bisector), not authored center (0,0).
    svg_center = (1+math.sqrt(1-epsilon**2/4), epsilon/2)
    svg_midpoint = (svg_center[0]+1, svg_center[1])
    actual = evaluate(c, 0.5)
    discrepancy = math.dist(svg_midpoint, actual)
    assert discrepancy < proof.max_chord_deviation_bound, (discrepancy, proof)
