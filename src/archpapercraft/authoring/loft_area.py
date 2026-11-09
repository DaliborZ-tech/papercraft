"""Independent intrinsic area bounds for positively homothetic ruled sources.

This is an area certificate, never permission to flatten a surface. In model
coordinates, C1=k*C0+d and k>0 give

    A = (1+k)/2 * integral |C0' x ((k-1)*C0+d)| du.

Polynomial patches use exact Bernstein products and Jensen/control-hull norm
bounds. Circular patches use rigorously enclosed trigonometric evaluations and
the composite Simpson remainder on the WHOLE parameter interval. All geometry,
including the supplied floating-point world bases, is treated as exact rational
input. No projected/flat mesh, sampled area, or unit-normal assumption is used.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from .curve_area import _add, _mul, _out, _pi, _point, _scalar, _sqrt
from .loft_geometry import LoftCorrespondence, LoftProfile, _homothety, _pair, _profile

_ZERO = Fraction(0)
_OUTPUT_GRID = 10**24
_TRIG_TERMS = 36
# All source arc arguments are strictly between -2*pi and 2*pi, hence |x|<7.
# Taylor polynomials end at sin degree 73 / cos degree 72. The displayed
# rational remainders follow Taylor's theorem and |sin^(n)|,|cos^(n)|<=1.
_SIN_REMAINDER = Fraction(7**75, math.factorial(75))
_COS_REMAINDER = Fraction(7**74, math.factorial(74))


def _vec(values):
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ValueError("A source world vector needs three exact finite coordinates")
    return tuple(_scalar(value) for value in values)


def _vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _vmul(a, factor):
    return tuple(x * factor for x in a)


def _dot(a, b):
    return sum((x * y for x, y in zip(a, b)), _ZERO)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(value):
    return _sqrt(_dot(value, value))


def _interval_norm(values):
    low = high = _ZERO
    for a, b in values:
        low += min(a * a, b * b) if a * b > 0 else _ZERO
        high += max(a * a, b * b)
    return _sqrt(low)[0], _sqrt(high)[1]


def _world_control(profile, point):
    origin, u, v = _vec(profile.origin), _vec(profile.u), _vec(profile.v)
    x, y = (_scalar(value) for value in point)
    return _vadd(origin, _vadd(_vmul(u, x), _vmul(v, y)))


@lru_cache(maxsize=8192)
def _sin_cos(angle):
    """Outward rational enclosures; no platform libm values enter a proof."""
    lo, hi = angle
    if not -7 < lo <= hi < 7:
        raise ValueError("The source arc exceeds the trigonometric argument budget")
    middle, radius = (lo + hi) / 2, (hi - lo) / 2
    square = _point(middle * middle)
    sine = term_s = _point(middle)
    cosine = term_c = _point(Fraction(1))
    for index in range(1, _TRIG_TERMS + 1):
        term_s = _mul(term_s, _mul(square, _point(Fraction(-1, 2 * index * (2 * index + 1)))))
        term_c = _mul(term_c, _mul(square, _point(Fraction(-1, (2 * index - 1) * 2 * index))))
        sine, cosine = _add(sine, term_s), _add(cosine, term_c)
    # Both functions are globally 1-Lipschitz, so the input interval radius is
    # additive. _add/_mul also retain every intermediate outward rounding.
    return (
        _out((sine[0] - radius - _SIN_REMAINDER, sine[1] + radius + _SIN_REMAINDER)),
        _out((cosine[0] - radius - _COS_REMAINDER, cosine[1] + radius + _COS_REMAINDER)),
    )


def _split(controls):
    left, right, current = [controls[0]], [controls[-1]], list(controls)
    while len(current) > 1:
        current = [_vmul(_vadd(a, b), Fraction(1, 2)) for a, b in zip(current, current[1:])]
        left.append(current[0])
        right.append(current[-1])
    return tuple(left), tuple(reversed(right))


@dataclass(frozen=True)
class _Polynomial:
    controls: tuple

    def bounds(self, width):
        count = len(self.controls)
        # Restricted Bernstein controls already encode the parameter domain.
        # Integral of B_i^n is 1/(n+1).
        average = tuple(sum((p[i] for p in self.controls), _ZERO) / count for i in range(3))
        lower, average_upper = _norm(average)
        norms = [_norm(point) for point in self.controls]
        upper = sum((bound[1] for bound in norms), _ZERO) / count
        guard = sum((b - a for a, b in norms), _ZERO) / count + (average_upper - lower)
        return lower * width, upper * width, guard * width

    def children(self):
        return tuple(_Polynomial(controls) for controls in _split(self.controls))


def _polynomial(profile, curve, s, d):
    points = [curve.start, curve.end]
    if curve.kind == "cubic":
        points = [curve.start, curve.data["control1"], curve.data["control2"], curve.end]
    controls = [_world_control(profile, point) for point in points]
    degree = len(controls) - 1
    derivative = [_vmul(_vadd(b, _vmul(a, -1)), degree) for a, b in zip(controls, controls[1:])]
    ruling = [_vadd(_vmul(point, s), d) for point in controls]
    product_degree = 2 * degree - 1
    product = []
    for index in range(product_degree + 1):
        value = (_ZERO, _ZERO, _ZERO)
        for i, a in enumerate(derivative):
            j = index - i
            if 0 <= j <= degree:
                weight = Fraction(
                    math.comb(degree - 1, i) * math.comb(degree, j),
                    math.comb(product_degree, index),
                )
                value = _vadd(value, _vmul(_cross(a, ruling[j]), weight))
        product.append(value)
    return _Polynomial(tuple(product))


@dataclass(frozen=True)
class _Arc:
    omega: tuple
    constant: tuple
    cosine: tuple
    sine: tuple
    fourth_bound: Fraction
    constant_norm: tuple | None = None

    def value(self, parameter):
        sine, cosine = _sin_cos(_mul(self.omega, _point(parameter)))
        values = [
            _add(_point(c), _add(_mul(_point(a), cosine), _mul(_point(b), sine)))
            for c, a, b in zip(self.constant, self.cosine, self.sine)
        ]
        return _interval_norm([_mul(self.omega, value) for value in values])

    def bounds(self, start, end):
        width = end - start
        if self.constant_norm is not None:
            return (
                self.constant_norm[0] * width,
                self.constant_norm[1] * width,
                (self.constant_norm[1] - self.constant_norm[0]) * width,
            )
        a, m, b = self.value(start), self.value((start + end) / 2), self.value(end)
        estimate = ((a[0] + 4 * m[0] + b[0]) * width / 6, (a[1] + 4 * m[1] + b[1]) * width / 6)
        remainder = self.fourth_bound * width**5 / 2880
        return (
            max(_ZERO, estimate[0] - remainder),
            estimate[1] + remainder,
            estimate[1] - estimate[0],
        )


def _arc(profile, curve, s, d):
    u, v = _vec(profile.u), _vec(profile.v)
    cx, cy = (_scalar(x) for x in curve.data["center"])
    x, y = _scalar(curve.start[0]) - cx, _scalar(curve.start[1]) - cy
    origin = _world_control(profile, (cx, cy))
    a, b = _vadd(_vmul(u, x), _vmul(v, y)), _vadd(_vmul(u, -y), _vmul(v, x))
    r0 = _vadd(_vmul(origin, s), d)
    constant, cosine, sine = _vmul(_cross(a, b), -s), _cross(b, r0), _vmul(_cross(a, r0), -1)
    omega = _mul(_pi(), _point(_scalar(curve.data["sweep_deg"]) / 180))
    absolute_omega = (min(abs(x) for x in omega), max(abs(x) for x in omega))
    # Exact Gram identities recognize constant norm, including normal circle
    # extrusions and concentric planar/conical bands in actual supplied bases.
    if _dot(constant, cosine) == _dot(constant, sine) == _dot(cosine, sine) == 0 and _dot(
        cosine, cosine
    ) == _dot(sine, sine):
        norm = _mul(absolute_omega, _sqrt(_dot(constant, constant) + _dot(cosine, cosine)))
        return _Arc(omega, constant, cosine, sine, _ZERO, norm)
    normal = _cross(u, v)
    radius = _sqrt(x * x + y * y)[0]
    trace = _sqrt(_dot(u, u) + _dot(v, v))[1]
    # |T| >= |R0.n|/|n| * sigma_min[U,V] * radius*|omega|,
    # sigma_min >= |U x V|/sqrt(|U|^2+|V|^2). No unit-basis shortcut.
    minimum = abs(_dot(r0, normal)) * radius * absolute_omega[0] / trace
    if minimum <= 0:
        raise ValueError("A positive circular Jacobian norm lower bound was not established")
    amplitude = _norm(cosine)[1] + _norm(sine)[1]
    m1, m2, m3, m4 = (absolute_omega[1] ** power * amplitude for power in range(2, 6))
    # Chain rule for f=|T|. The norm's derivatives of orders 1..4 are bounded
    # by 1, 1/m, 6/m^2, 36/m^3 respectively: the third derivative's explicit
    # tensor has three linear terms and one coefficient-3 term; the fourth has
    # three constant, six coefficient-3 and one coefficient-15 terms. Triangle
    # inequalities suffice; no sampled or sharp operator-norm claim is needed.
    # Partitions of order four give 1, (4,3), 6, 1 on the WHOLE source interval.
    fourth = (
        m4
        + (4 * m1 * m3 + 3 * m2 * m2) / minimum
        + 36 * m1 * m1 * m2 / minimum**2
        + 36 * m1**4 / minimum**3
    )
    return _Arc(omega, constant, cosine, sine, fourth)


def _coverage(first, second, correspondences):
    return {
        "first_profile_id": first.profile_id,
        "second_profile_id": second.profile_id,
        "first_closed": first.closed,
        "second_closed": second.closed,
        "expected_first_segment_ids": [curve.segment_id for curve in first.curves],
        "expected_second_segment_ids": [curve.segment_id for curve in second.curves],
        "correspondences": [
            {
                "first_segment_id": reference.first_segment_id,
                "second_segment_id": reference.second_segment_id,
                "first_parameter_interval": list(reference.first_interval),
                "second_parameter_interval": list(reference.second_interval),
            }
            for reference in correspondences
        ],
        "scope": "ALL_SOURCE_SEGMENTS_EXACTLY_ONCE_WITH_EXPLICIT_ORIENTATION",
    }


def _float_out(value, *, upper):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Intrinsic paper area is outside finite floating-point range")
    if (upper and Fraction(result) < value) or (not upper and Fraction(result) > value):
        result = math.nextafter(result, math.inf if upper else -math.inf)
    if not math.isfinite(result):
        raise ValueError("An outward finite intrinsic-area float cannot be represented")
    return result


def certify_loft_intrinsic_area(
    first: LoftProfile,
    second: LoftProfile,
    correspondences: tuple[LoftCorrespondence, ...],
    *,
    scale: float,
    absolute_budget_mm2=1e-4,
    max_nodes=65536,
    max_depth=24,
) -> dict:
    """Enclose actual-source area; CERTIFIED does not certify a development.

    Float inputs mean their exact binary rationals. The area includes only the
    explicitly paired source intervals, which must cover both profiles exactly
    once. Source arc semantics are center/start/signed-sweep; an endpoint's
    serialization discrepancy is NOT a deformation of the intervening arc.
    Node consumption counts examined adaptive subintervals, not display samples.
    """
    examined, coverage = 0, {}
    try:
        if not isinstance(first, LoftProfile) or not isinstance(second, LoftProfile):
            raise ValueError("Intrinsic area needs two source LoftProfile records")
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not math.isfinite(scale)
            or scale <= 0
        ):
            raise ValueError("Paper scale must be finite and positive")
        if (
            isinstance(absolute_budget_mm2, bool)
            or not isinstance(absolute_budget_mm2, (int, float))
            or not math.isfinite(absolute_budget_mm2)
            or absolute_budget_mm2 <= 0
        ):
            raise ValueError("Absolute area budget must be finite and positive")
        if (
            type(max_nodes) is not int
            or max_nodes < 1
            or type(max_depth) is not int
            or not 0 <= max_depth <= 64
        ):
            raise ValueError("Area subdivision budgets are invalid")
        if not isinstance(correspondences, (tuple, list)) or len(correspondences) > max_nodes:
            raise ValueError("Correspondences exceed the bounded source-input budget")
        for profile in (first, second):
            if (
                not isinstance(profile.profile_id, str)
                or not profile.profile_id
                or not isinstance(profile.closed, bool)
            ):
                raise ValueError("Source profile identities and closed states must be explicit")
            if any(
                not isinstance(curve.segment_id, str) or not curve.segment_id
                for curve in profile.curves
            ):
                raise ValueError("Source segment identities must be nonempty strings")
        for reference in correspondences:
            if not isinstance(reference, LoftCorrespondence) or any(
                isinstance(value, bool)
                for interval in (reference.first_interval, reference.second_interval)
                for value in interval
            ):
                raise ValueError("Correspondences need explicit oriented numeric source intervals")
        _profile(first), _profile(second)
        if tuple(first.u) != tuple(second.u) or tuple(first.v) != tuple(second.v):
            raise ValueError("The supported area family needs identical source bases")
        pairs = _pair(first, second, correspondences)
        if {r.first_segment_id for _, _, r in pairs} != {c.segment_id for c in first.curves} or {
            r.second_segment_id for _, _, r in pairs
        } != {c.segment_id for c in second.curves}:
            raise ValueError("Intrinsic area requires complete source-segment coverage")
        coverage = _coverage(first, second, correspondences)
        family = _homothety(pairs)
        if family is None or family[0] <= 0:
            raise ValueError("Positive exact source homothety was not established")
        k, shift = family
        s = k - 1
        u, v, oa, ob = _vec(first.u), _vec(first.v), _vec(first.origin), _vec(second.origin)
        d = _vadd(_vadd(ob, _vmul(oa, -k)), _vadd(_vmul(u, shift[0]), _vmul(v, shift[1])))
        factor = (1 + k) / 2 * Fraction(scale) ** 2
        budget = Fraction(absolute_budget_mm2)
        if budget < Fraction(2, _OUTPUT_GRID):
            raise ValueError("Area budget is below the public rational rounding budget")
        leaves, total_low, total_high, total_guard = [], _ZERO, _ZERO, _ZERO
        original = {curve.segment_id: curve for curve in first.curves}
        serial = 0

        def push(function, start, end, depth):
            nonlocal examined, serial, total_low, total_high, total_guard
            if examined >= max_nodes:
                raise ValueError("Intrinsic area node budget exhausted")
            examined += 1
            if isinstance(function, _Polynomial):
                low, high, guard = function.bounds(end - start)
            else:
                low, high, guard = function.bounds(start, end)
            total_low, total_high, total_guard = (
                total_low + low,
                total_high + high,
                total_guard + guard,
            )
            serial += 1
            heapq.heappush(
                leaves, (-(high - low), serial, function, start, end, depth, low, high, guard)
            )

        for a, _, reference in pairs:
            # Reversing BOTH full source intervals changes orientation, never
            # area. Integrate the original arc to avoid reconstructing its
            # analytic start from a rounded serialized endpoint.
            curve = a
            if a.kind == "arc":
                if tuple(reference.first_interval) != tuple(reference.second_interval):
                    raise ValueError(
                        "Oppositely oriented arc sources need an analytic endpoint proof"
                    )
                curve = original[reference.first_segment_id]
            function = (
                _arc(first, curve, s, d) if curve.kind == "arc" else _polynomial(first, curve, s, d)
            )
            push(function, _ZERO, Fraction(1), 0)
        while True:
            lower, upper = _out((total_low * factor, total_high * factor), _OUTPUT_GRID)
            if upper <= 0:
                raise ValueError("The source has no positive intrinsic area")
            if upper - lower <= budget and lower > 0:
                break
            if not leaves:
                raise ValueError("Positive intrinsic area could not be established")
            _, _, function, start, end, depth, low, high, guard = heapq.heappop(leaves)
            if depth >= max_depth:
                raise ValueError("Intrinsic area depth budget exhausted")
            if examined + 2 > max_nodes:
                raise ValueError("Intrinsic area node budget exhausted")
            total_low, total_high, total_guard = (
                total_low - low,
                total_high - high,
                total_guard - guard,
            )
            middle = (start + end) / 2
            functions = (
                function.children() if isinstance(function, _Polynomial) else (function, function)
            )
            push(functions[0], start, middle, depth + 1)
            push(functions[1], middle, end, depth + 1)
        return {
            "status": "CERTIFIED",
            "family": "POSITIVE_HOMOTHETIC_RULED_SOURCE",
            "area_lower_exact": str(lower),
            "area_upper_exact": str(upper),
            "area_lower_paper_mm2": _float_out(lower, upper=False),
            "area_upper_paper_mm2": _float_out(upper, upper=True),
            "absolute_budget_mm2": absolute_budget_mm2,
            "examined_nodes": examined,
            "numerical_guard_paper_mm2": _float_out(
                _out((_ZERO, total_guard * factor + Fraction(2, _OUTPUT_GRID)), _OUTPUT_GRID)[1],
                upper=True,
            ),
            "coverage": coverage,
            "proof": {
                "area_identity": "(1+k)/2 * integral norm(C0' cross ((k-1)*C0+d)); scale^2",
                "polynomial": (
                    "Exact Bernstein cross-product controls; Jensen lower and control-hull upper"
                ),
                "arc": (
                    "Rational Taylor sin/cos and pi/sqrt intervals; whole-interval norm "
                    "derivative bound; Simpson h^5/2880 remainder"
                ),
                "arc_source_semantics": (
                    "Analytic center/start/signed sweep; stored endpoint proximity is not "
                    "a proof of opposite-orientation correspondence"
                ),
                "basis": (
                    "Actual rational world origins and identical supplied bases, "
                    "never idealized unit axes"
                ),
                "rounding": (
                    "Outward rational operations; public area rounded OUTWARD on a 1e-24 mm2 grid"
                ),
                "scope": "INTRINSIC_AREA_ONLY_NOT_A_FLATTENING_OR_TOPOLOGY_CERTIFICATE",
            },
        }
    except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError) as exc:
        return {
            "status": "UNRESOLVED",
            "family": "UNPROVEN_INTRINSIC_AREA",
            "message": str(exc),
            "examined_nodes": examined,
            "coverage": coverage,
            "proof_scope": "UNRESOLVED_INTRINSIC_AREA_NOT_A_FLATTENING_PERMISSION",
            "next_action": (
                "Reverse both complete source profiles together, or supply an analytic "
                "endpoint proof; do not replace arc correspondence by endpoint proximity."
                if "Oppositely oriented arc" in str(exc)
                else "Correct source correspondence or increase the stated arithmetic budget "
                "and retry; do not bypass intrinsic-area validation."
            ),
        }
