"""Analytic expectations, bounded whole-curve errors and negative certification."""

import math

import numpy as np
import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import (
    Curve,
    certify_curve,
    derivative,
    evaluate,
    svg_commands,
)


def certificate(curve, **kwargs):
    return certify_curve(curve, chord_tolerance=kwargs.pop("chord_tolerance", 0.001),
                         length_tolerance=kwargs.pop("length_tolerance", 0.001), **kwargs)


def arch():
    return Curve((0, 0), (10, 0), "cubic", {"control1": (0, 10), "control2": (10, 10)}, "arch")


def test_line_evaluation_derivative_native_svg_and_exact_length():
    line = Curve((1, 2), (4, 6), segment_id="edge-17")
    assert evaluate(line, 0.25) == (1.75, 3)
    assert derivative(line, 0.5) == (3, 4)
    assert svg_commands(line) == "M 1 2 L 4 6"
    result = certificate(line)
    assert result.status == "CERTIFIED" and result.segment_id == "edge-17"
    assert result.parameters == (0, 1) and result.parameter_intervals == ((0, 1),)
    assert result.length_lower <= 5 <= result.length_upper
    assert result.regularity == "REGULAR"


@pytest.mark.parametrize("sweep,end", [(90, (0, 10)), (-90, (0, -10)), (270, (0, -10))])
def test_circle_analytic_length_sagitta_and_oriented_svg(sweep, end):
    curve = Curve((10, 0), end, "arc", {"center": (0, 0), "sweep_deg": sweep}, "round")
    result = certificate(curve)
    expected = 10 * abs(sweep) * math.pi / 180
    assert result.status == "CERTIFIED"
    assert result.length_lower <= expected <= result.length_upper
    assert result.length_upper - result.length_lower <= 0.001
    assert result.max_chord_deviation_bound <= 0.001
    for t0, t1 in result.parameter_intervals:
        theta = abs(sweep) * math.pi / 180 * (t1 - t0)
        sagitta = 10 * (1 - math.cos(theta / 2))
        assert sagitta <= result.max_chord_deviation_bound
    assert " A 10 10 0 " + str(int(abs(sweep) > 180)) + " " + str(int(sweep > 0)) in svg_commands(
        curve
    )
    assert math.hypot(*derivative(curve, 0.4)) == pytest.approx(expected)


def test_arc_endpoint_rounding_is_in_precision_budget_not_silently_changed():
    curve = Curve((10, 0), (1e-8, 10), "arc", {"center": (0, 0), "sweep_deg": 90})
    result = certificate(curve, chord_tolerance=1e-10, length_tolerance=1e-10)
    assert result.status == "UNRESOLVED"
    assert evaluate(curve, 1) == (1e-8, 10)


def test_cubic_exact_polynomial_expected_derivative_and_native_svg():
    curve = arch()
    assert evaluate(curve, 0.5) == (5, 7.5)
    assert derivative(curve, 0) == (0, 30)
    assert derivative(curve, 0.5) == (15, 0)
    assert svg_commands(curve) == "M 0 0 C 0 10 10 10 10 0"
    # This cubic is x=30t²-20t³, y=30t-30t²; its exact length is 20.
    result = certificate(curve)
    assert result.status == "CERTIFIED"
    assert result.length_lower <= 20 <= result.length_upper
    assert result.length_upper - result.length_lower <= 0.001
    assert result.max_chord_deviation_bound <= 0.001
    assert result.regularity == "NOT_PROVEN"  # No sampled-zero regularity claim.
    assert result.parameters[0] == 0 and result.parameters[-1] == 1
    assert all(a[1] == b[0] for a, b in zip(result.parameter_intervals,
                                          result.parameter_intervals[1:]))


def test_collinear_monotone_cubic_has_exact_straight_length():
    curve = Curve((0, 0), (12, 0), "cubic", {"control1": (2, 0), "control2": (8, 0)})
    result = certificate(curve)
    assert result.status == "CERTIFIED" and len(result.parameter_intervals) == 1
    assert result.length_lower <= 12 <= result.length_upper


def test_cubic_length_encloses_independent_high_precision_quadrature_and_dense_geometry():
    curve = Curve((0, 0), (4, 3), "cubic", {"control1": (8, -5), "control2": (-3, 9)})
    result = certificate(curve)
    assert result.status == "CERTIFIED"
    # Independent derivative polynomial from the four authored control points.
    length, error = quad(lambda t: math.hypot(
        24 * (1-t)**2 - 66 * (1-t)*t + 21*t*t,
        -15 * (1-t)**2 + 84 * (1-t)*t - 18*t*t,
    ), 0, 1, epsabs=1e-11, epsrel=1e-11)
    assert error < 1e-8
    assert result.length_lower < length < result.length_upper
    assert result.length_upper - result.length_lower <= 0.001
    # Sampling is an additional negative oracle, not the claimed positive proof.
    for index, (a, b) in enumerate(result.parameter_intervals):
        p, q = np.asarray(result.points[index]), np.asarray(result.points[index + 1])
        for t in np.linspace(a, b, 5):
            point = np.array([24*t - 57*t*t + 37*t**3, -15*t + 57*t*t - 39*t**3])
            fraction = np.clip(np.dot(point-p, q-p) / np.dot(q-p, q-p), 0, 1)
            assert np.linalg.norm(point - (p + fraction*(q-p))) <= result.max_chord_deviation_bound


def test_total_length_gap_is_bounded_globally_not_per_leaf():
    curve = arch()
    loose = certificate(curve, chord_tolerance=0.02, length_tolerance=0.01)
    tight = certificate(curve, chord_tolerance=0.02, length_tolerance=0.00001)
    assert loose.status == tight.status == "CERTIFIED"
    assert tight.length_upper - tight.length_lower <= 0.00001
    assert tight.length_lower >= loose.length_lower
    assert tight.length_upper <= loose.length_upper
    assert len(tight.parameter_intervals) > len(loose.parameter_intervals)


@pytest.mark.parametrize("budget", [{"max_depth": 0}, {"max_segments": 1}, {"max_segments": 3}])
def test_finite_budget_cannot_issue_false_certificate(budget):
    result = certificate(arch(), **budget)
    assert result.status == "BUDGET_EXHAUSTED"
    assert result.parameters[0] == 0 and result.parameters[-1] == 1
    assert (result.max_chord_deviation_bound > 0.001
            or result.length_upper-result.length_lower > 0.001)


def test_large_translation_below_precision_reserve_is_unresolved():
    curve = Curve((1e10, 1e10), (1e10+10, 1e10))
    result = certificate(curve, chord_tolerance=1e-7, length_tolerance=1e-7)
    assert result.status == "UNRESOLVED"
    assert result.numerical_guard > 1e-7


def test_rigid_rotation_and_scale_preserve_source_and_scale_bounds():
    curve = arch()
    original = certificate(curve)
    def transform(p):
        return 7 - 2*p[1], -11 + 2*p[0]
    transformed = Curve(transform(curve.start), transform(curve.end), "cubic",
                        {key: transform(value) for key, value in curve.data.items()})
    result = certificate(transformed, chord_tolerance=0.002, length_tolerance=0.002)
    assert result.status == "CERTIFIED"
    assert result.length_lower <= 40 <= result.length_upper
    assert result.length_upper == pytest.approx(2 * original.length_upper)
    assert result.length_lower == pytest.approx(2 * original.length_lower)
    assert evaluate(transformed, 0.37) == pytest.approx(transform(evaluate(curve, 0.37)))


def test_stationary_cubic_length_certificate_does_not_certify_regularity():
    curve = Curve((0, 0), (1, 0), "cubic", {"control1": (0, 0), "control2": (1, 0)})
    result = certificate(curve)
    assert result.status == "CERTIFIED" and result.regularity == "SINGULAR"
    assert derivative(curve, 0) == (0, 0)
    assert "no loft" in result.message


def test_interior_stationary_parameter_is_not_missed_by_chord_only_acceptance():
    # x=(2t-1)^3 has length2, but derivative vanishes at t=1/2.
    curve = Curve((-1, 0), (1, 0), "cubic", {"control1": (1, 0), "control2": (-1, 0)})
    result = certificate(curve)
    assert result.status == "CERTIFIED" and result.regularity == "SINGULAR"
    assert result.length_lower <= 2 <= result.length_upper
    assert 0.5 in result.parameters


def test_separate_segments_keep_sharp_corner_and_source_interval_identity():
    left = Curve((0, 0), (10, 10), segment_id="left")
    right = Curve((10, 10), (20, 0), segment_id="right")
    a, b = certificate(left), certificate(right)
    assert a.segment_id == "left" and b.segment_id == "right"
    assert a.points[-1] == b.points[0] == (10, 10)
    assert derivative(left, 1) == (10, 10) and derivative(right, 0) == (10, -10)


@pytest.mark.parametrize("factory", [
    lambda: Curve((0, 0), (0, 0)),
    lambda: Curve((0, 0), (1, 0), "arc", {"center": (0, 0), "sweep_deg": 90}),
    lambda: Curve((1, 0), (1, 0), "arc", {"center": (0, 0), "sweep_deg": 360}),
    lambda: Curve((1, 0), (0, 1), "arc", {"center": (0, 0), "sweep_deg": -90}),
    lambda: Curve((0, 0), (1, 1), "cubic", {"control1": (math.nan, 0), "control2": (1, 0)}),
    lambda: Curve((0, 0), (1, 1), "arc", {"center": (0, 0), "sweep_deg": math.inf}),
    lambda: Curve((0, 0), (1, 1), "unknown"),
])
def test_invalid_source_is_rejected_without_partial_mutation(factory):
    with pytest.raises(ValueError):
        factory()


@pytest.mark.parametrize("value", [-0.1, 1.1, math.nan, math.inf, True])
def test_invalid_parameter_is_not_clamped(value):
    with pytest.raises(ValueError):
        evaluate(arch(), value)


@pytest.mark.parametrize("kwargs", [
    {"chord_tolerance": 0}, {"length_tolerance": math.inf},
    {"max_segments": 0}, {"max_depth": -1}, {"max_depth": True},
])
def test_invalid_budget_or_tolerance_is_not_replaced_by_a_default(kwargs):
    with pytest.raises(ValueError):
        certificate(arch(), **kwargs)
