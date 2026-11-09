"""Source curves and bounded approximations, in the caller's length units.

The cubic proof uses exact rational de Casteljau subdivision of binary input
coordinates. A curve lies in its control hull: distance to its endpoint segment
is bounded by the largest control-point distance; chord/control-polygon lengths
bound its arc length. Bounds are summed over the WHOLE curve, not accepted per
leaf with an unbounded accumulated error. This is not a loft/regularity proof.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from fractions import Fraction
from types import MappingProxyType

_PI_DIGITS = "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998"
_PI_LOWER = Fraction(_PI_DIGITS)
_PI_UPPER = _PI_LOWER + Fraction(1, 10 ** len(_PI_DIGITS.split(".")[1]))


def _point(value):
    if len(value) != 2 or any(isinstance(x, bool) for x in value):
        raise ValueError("A source point needs two finite coordinates")
    point = tuple(float(x) for x in value)
    if not all(math.isfinite(x) for x in point):
        raise ValueError("A source point needs two finite coordinates")
    return point


@dataclass(frozen=True)
class Curve:
    start: tuple
    end: tuple
    kind: str = "line"
    data: object = None
    segment_id: str = ""

    def __post_init__(self):
        start, end = _point(self.start), _point(self.end)
        if start == end:
            raise ValueError("A source segment needs distinct endpoints")
        data = dict(self.data or {})
        if self.kind == "line":
            if data or start == end:
                raise ValueError("A line needs distinct endpoints and no extra data")
        elif self.kind == "arc":
            if set(data) != {"center", "sweep_deg"}:
                raise ValueError("An arc needs center and signed sweep_deg")
            data["center"] = _point(data["center"])
            sweep = data["sweep_deg"]
            if isinstance(sweep, bool) or not math.isfinite(sweep) or not 0 < abs(sweep) < 360:
                raise ValueError("An arc sweep must be nonzero and smaller than 360 degrees")
            radius = math.dist(start, data["center"])
            if radius <= 0:
                raise ValueError("An arc radius must be positive")
            angle = math.radians(sweep)
            x, y = (a - b for a, b in zip(start, data["center"]))
            expected = (data["center"][0] + x * math.cos(angle) - y * math.sin(angle),
                        data["center"][1] + x * math.sin(angle) + y * math.cos(angle))
            if math.dist(expected, end) > 1e-7:
                raise ValueError("Arc endpoint does not match its center and signed sweep")
        elif self.kind == "cubic":
            if set(data) != {"control1", "control2"}:
                raise ValueError("A cubic needs two control points")
            data = {key: _point(value) for key, value in data.items()}
            if start == end == data["control1"] == data["control2"]:
                raise ValueError("A constant cubic has no material curve")
        else:
            raise ValueError("Unknown source curve kind")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)
        object.__setattr__(self, "data", MappingProxyType(data))


def _parameter(t):
    if isinstance(t, bool) or not math.isfinite(t) or not 0 <= t <= 1:
        raise ValueError("Curve parameter must be in [0, 1]")
    return float(t)


def _control(curve):
    points = [curve.start, curve.end] if curve.kind == "line" else [
        curve.start, curve.data["control1"], curve.data["control2"], curve.end,
    ]
    return tuple(tuple(Fraction(x) for x in point) for point in points)


def _lerp(a, b, t):
    return tuple((1 - t) * x + t * y for x, y in zip(a, b))


def evaluate(curve, t):
    """Evaluate the authored source, independent of display tessellation."""
    t = _parameter(t)
    if t == 0:
        return curve.start
    if t == 1:
        return curve.end
    if curve.kind == "arc":
        angle = math.radians(curve.data["sweep_deg"]) * t
        x, y = (a - b for a, b in zip(curve.start, curve.data["center"]))
        return (curve.data["center"][0] + x * math.cos(angle) - y * math.sin(angle),
                curve.data["center"][1] + x * math.sin(angle) + y * math.cos(angle))
    points, parameter = _control(curve), Fraction(t)
    while len(points) > 1:
        points = tuple(_lerp(a, b, parameter) for a, b in zip(points, points[1:]))
    return tuple(float(x) for x in points[0])


def derivative(curve, t):
    t = _parameter(t)
    if curve.kind == "arc":
        angle = math.radians(curve.data["sweep_deg"])
        theta = angle * t
        x, y = (a - b for a, b in zip(curve.start, curve.data["center"]))
        return (angle * (-x * math.sin(theta) - y * math.cos(theta)),
                angle * (x * math.cos(theta) - y * math.sin(theta)))
    return tuple(float(x) for x in _exact_derivative(curve, t))


def _exact_derivative(curve, t):
    controls = _control(curve)
    degree = len(controls) - 1
    points = tuple(tuple(degree * (y - x) for x, y in zip(a, b))
                   for a, b in zip(controls, controls[1:]))
    while len(points) > 1:
        points = tuple(_lerp(a, b, Fraction(t)) for a, b in zip(points, points[1:]))
    return points[0]


def svg_commands(curve):
    """Local SVG coordinates: M followed by native L, A or C; no flattening.

    Positive source sweep uses SVG sweep=1 in the same coordinate system.
    A caller reflecting Y must also invert the SVG sweep flag or reflect a group.
    """
    def f(x):
        return format(x, ".17g")

    def point(p):
        return " ".join(f(x) for x in p)
    prefix = "M " + point(curve.start) + " "
    if curve.kind == "line":
        return prefix + "L " + point(curve.end)
    if curve.kind == "cubic":
        return prefix + "C " + " ".join(point(p) for p in (
            curve.data["control1"], curve.data["control2"], curve.end,
        ))
    radius = math.dist(curve.start, curve.data["center"])
    sweep = curve.data["sweep_deg"]
    command = f"A {f(radius)} {f(radius)} 0 {int(abs(sweep) > 180)} {int(sweep > 0)} "
    return prefix + command + point(curve.end)


def _sqrt_bounds(value):
    if value == 0:
        return 0.0, 0.0
    # Exact rational squared distance -> outward decimal division and sqrt ->
    # outward binary conversion. Decimal.sqrt is correctly rounded to nearest;
    # next_minus/next_plus enclose it independently of the context's rounding.
    with localcontext() as ctx:
        ctx.prec = 70
        ctx.rounding = ROUND_FLOOR
        low = (Decimal(value.numerator) / Decimal(value.denominator)).sqrt().next_minus()
        ctx.rounding = ROUND_CEILING
        high = (Decimal(value.numerator) / Decimal(value.denominator)).sqrt().next_plus()
        return (max(0.0, math.nextafter(float(low), -math.inf)),
                math.nextafter(float(high), math.inf))


def _distance_bounds(a, b):
    return _sqrt_bounds(sum((x - y) ** 2 for x, y in zip(a, b)))


def _segment_distance_bound(point, a, b):
    vector = tuple(y - x for x, y in zip(a, b))
    length2 = sum(x * x for x in vector)
    if not length2:
        return _distance_bounds(point, a)[1]
    projection = sum((x - y) * v for x, y, v in zip(point, a, vector)) / length2
    nearest = _lerp(a, b, min(Fraction(1), max(Fraction(0), projection)))
    return _distance_bounds(point, nearest)[1]


def _sum_lower(values):
    return max(0.0, math.nextafter(math.fsum(values), -math.inf))


def _sum_upper(values):
    return math.nextafter(math.fsum(values), math.inf)


def _split(controls):
    levels = [controls]
    while len(levels[-1]) > 1:
        levels.append(tuple(_lerp(a, b, Fraction(1, 2))
                            for a, b in zip(levels[-1], levels[-1][1:])))
    return tuple(level[0] for level in levels), tuple(level[-1] for level in reversed(levels))


@dataclass(frozen=True)
class CurveCertificate:
    status: str
    segment_id: str
    parameters: tuple
    points: tuple
    parameter_intervals: tuple
    max_chord_deviation_bound: float
    length_lower: float
    length_upper: float
    numerical_guard: float
    regularity: str
    method: str
    message: str


def certify_curve(curve, *, chord_tolerance, length_tolerance, max_depth=24, max_segments=16384):
    """Bound the whole source curve; no budget/tolerance silently becomes PASS.

    Tolerances use the caller's units, not an implicit model/paper conversion.
    CERTIFIED describes chord approximation and length only. Cubic regularity
    stays NOT_PROVEN unless a sampled exact zero derivative proves SINGULAR.
    """
    for tolerance in (chord_tolerance, length_tolerance):
        if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("Curve tolerances must be finite and positive")
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("Subdivision depth must be a nonnegative integer")
    if type(max_segments) is not int or max_segments < 1:
        raise ValueError("Subdivision segment budget must be a positive integer")
    all_points = [curve.start, curve.end, *(
        [curve.data["center"]] if curve.kind == "arc" else
        [curve.data["control1"], curve.data["control2"]] if curve.kind == "cubic" else []
    )]
    magnitude = max(abs(x) for p in all_points for x in p)
    # A declared conservative floating evaluation reserve; exact cubic hull
    # subdivision and length bounds below do not depend on sampled values.
    guard = 128 * math.ulp(max(1.0, magnitude))
    if curve.kind == "arc":
        guard *= 1 + math.radians(curve.data["sweep_deg"]) ** 2
        center = curve.data["center"]
        theta = math.radians(curve.data["sweep_deg"])
        x, y = (a - b for a, b in zip(curve.start, center))
        predicted = (center[0] + x * math.cos(theta) - y * math.sin(theta),
                     center[1] + x * math.sin(theta) + y * math.cos(theta))
        guard += math.dist(predicted, curve.end)
        exact_start = tuple(Fraction(x) for x in curve.start)
        exact_center = tuple(Fraction(x) for x in center)
        radius_lower, radius_upper = _distance_bounds(exact_start, exact_center)
        sweep_fraction = abs(Fraction(curve.data["sweep_deg"])) / 180
    unresolved = guard >= min(chord_tolerance, length_tolerance / 4)
    controls = None if curve.kind == "arc" else _control(curve)
    pending = deque([(0.0, 1.0, 0, controls)])
    leaves, exhausted, count = [], False, 1
    while pending:
        t0, t1, depth, controls = pending.popleft()
        if curve.kind == "arc":
            span = Fraction(t1) - Fraction(t0)
            angle_upper = _PI_UPPER * sweep_fraction * span
            delta = math.nextafter(float(angle_upper), math.inf)
            # Sagitta r*(1-cos(delta/2)) <= r*delta²/8 on minor arcs.
            sagitta_upper = Fraction(radius_upper) * angle_upper ** 2 / 8
            deviation = math.nextafter(float(sagitta_upper) + guard, math.inf)
            exact_low = Fraction(radius_lower) * _PI_LOWER * sweep_fraction * span
            exact_high = Fraction(radius_upper) * angle_upper
            low = max(0.0, math.nextafter(float(exact_low), -math.inf) - guard * float(span))
            high = math.nextafter(float(exact_high) + guard * float(span), math.inf)
            must_split = delta > math.pi
        else:
            low = _distance_bounds(controls[0], controls[-1])[0]
            high = _sum_upper(_distance_bounds(a, b)[1] for a, b in zip(controls, controls[1:]))
            deviation = max(_segment_distance_bound(p, controls[0], controls[-1])
                            for p in controls) + guard
            must_split = False
        acceptable = (not must_split and deviation <= chord_tolerance
                      and high - low <= length_tolerance * (t1 - t0))
        if not acceptable and not unresolved and depth < max_depth and count < max_segments:
            middle = (t0 + t1) / 2
            left, right = (None, None) if controls is None else _split(controls)
            pending.extend([(t0, middle, depth + 1, left), (middle, t1, depth + 1, right)])
            count += 1
        else:
            exhausted |= not acceptable and not unresolved
            leaves.append((t0, t1, deviation, low, high))
    leaves.sort()
    parameters = (leaves[0][0], *(leaf[1] for leaf in leaves))
    length_low = _sum_lower(leaf[3] for leaf in leaves)
    length_high = _sum_upper(leaf[4] for leaf in leaves)
    deviation = max(leaf[2] for leaf in leaves)
    if not all(math.isfinite(x) for x in (length_low, length_high, deviation, guard)):
        unresolved = True
    if length_high - length_low > length_tolerance or deviation > chord_tolerance:
        exhausted |= not unresolved
    status = "UNRESOLVED" if unresolved else "BUDGET_EXHAUSTED" if exhausted else "CERTIFIED"
    regularity = "REGULAR" if curve.kind != "cubic" else "NOT_PROVEN"
    if curve.kind == "cubic" and any(_exact_derivative(curve, t) == (0, 0) for t in parameters):
        regularity = "SINGULAR"
    return CurveCertificate(
        status, curve.segment_id, parameters, tuple(evaluate(curve, t) for t in parameters),
        tuple((leaf[0], leaf[1]) for leaf in leaves), deviation, length_low, length_high,
        guard, regularity,
        "ANALYTIC_ARC_LENGTH_AND_SAGITTA_BOUND" if curve.kind == "arc" else
        "EXACT_RATIONAL_CASTELJAU_HULL_AND_CHORD_CONTROL_POLYGON_LENGTH_BOUNDS",
        "Length/chord bounds only; no loft, topology or physical-build certificate. "
        + ("Floating precision reserve exceeds the requested tolerance." if unresolved else
           "Finite subdivision budget exhausted; requested bounds not established." if exhausted
           else "Whole-curve length gap and every chord meet the requested tolerances."),
    )
