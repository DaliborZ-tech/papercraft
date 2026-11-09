"""Conservative topology of authored curves, independent of display chords.

Positive proofs use control-hull/analytic-arc separation and endpoint-only
halfplanes. A chord polygon is used for winding only after a convex homotopy
has been proved to avoid the query point. Exhaustion never produces VALID.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from .curves import Curve, _arc_svg_plan, _control, _split, _sqrt_bounds


@dataclass(frozen=True)
class TopologyCertificate:
    status: str
    reason: str
    witness: dict | None
    examined_nodes: int
    numerical_guard: float
    proof: tuple[str, ...]
    geometry_scope: str = "MANUFACTURING_NATIVE_SVG_ENDPOINT_ARCS_AND_AUTHORED_LINES_CUBICS"


class _UnresolvedError(Exception):
    pass


class _InvalidError(Exception):
    def __init__(self, reason, witness=None):
        self.reason, self.witness = reason, witness


@dataclass
class _Budget:
    limit: int
    depth: int
    guard: float
    used: int = 0

    def tick(self):
        self.used += 1
        if self.used > self.limit:
            raise _UnresolvedError("Finite topology node budget exhausted")


@dataclass(frozen=True)
class _Node:
    curve: Curve
    t0: float = 0.0
    t1: float = 1.0
    depth: int = 0
    controls: tuple | None = None
    homogeneous: tuple | None = None
    native: dict | None = None

    def ends(self):
        if self.controls is not None:
            return self.controls[0], self.controls[-1]
        return tuple(tuple(sum(value)/2 for value in point)
                     for point in (_cartesian(self.homogeneous[0]),
                                   _cartesian(self.homogeneous[-1])))

    def split(self, budget):
        if self.depth >= budget.depth:
            raise _UnresolvedError("Finite topology subdivision depth exhausted")
        middle = (self.t0 + self.t1) / 2
        if middle == self.t0 or middle == self.t1:
            raise _UnresolvedError("Topology parameter precision exhausted")
        if self.controls is not None:
            left, right = _split(self.controls)
            return (_Node(self.curve, self.t0, middle, self.depth+1, left),
                    _Node(self.curve, middle, self.t1, self.depth+1, right))
        levels = [self.homogeneous]
        while len(levels[-1]) > 1:
            levels.append(tuple(tuple(_idiv(_iadd(x, y), _iv(2)) for x, y in zip(a, b))
                                for a, b in zip(levels[-1], levels[-1][1:])))
        left = tuple(level[0] for level in levels)
        right = tuple(level[-1] for level in reversed(levels))
        return (_Node(self.curve, self.t0, middle, self.depth+1,
                      homogeneous=left, native=self.native),
                _Node(self.curve, middle, self.t1, self.depth+1,
                      homogeneous=right, native=self.native))


def _fraction_point(point):
    return tuple(Fraction(x) for x in point)


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def _iv(value):
    return (Fraction(value), Fraction(value))


def _iadd(a, b):
    return a[0]+b[0], a[1]+b[1]


def _ineg(a):
    return -a[1], -a[0]


def _isub(a, b):
    return _iadd(a, _ineg(b))


def _imul(a, b):
    values = [x*y for x in a for y in b]
    return min(values), max(values)


def _idiv(a, b):
    if b[0] <= 0 <= b[1]:
        raise _UnresolvedError("Interval geometry has an unresolved zero denominator")
    return _imul(a, (1/b[1], 1/b[0]))


def _isquare(a):
    return (Fraction(0) if a[0] <= 0 <= a[1] else min(x*x for x in a), max(x*x for x in a))


def _isqrt(a):
    if a[0] < 0:
        raise _UnresolvedError("Circle intersection or arc weight is not strictly established")
    return Fraction(_sqrt_bounds(a[0])[0]), Fraction(_sqrt_bounds(a[1])[1])


def _cartesian(homogeneous):
    return tuple(_idiv(value, homogeneous[2]) for value in homogeneous[:2])


def _hull(node):
    if node.controls is not None:
        return node.controls
    points = []
    for control in node.homogeneous:
        x, y = _cartesian(control)
        points.extend((a, b) for a in x for b in y)
    return tuple(points)


def _native_arcs(curve):
    """The fixed-endpoint SVG circles, with rigorous interval rational controls.

    For minor endpoint-form arcs, w=h/r>0 and w*Q=w*mid-perp(chord)*d/(4r).
    Thus the exact manufactured arc is a positive-weight rational quadratic
    within these homogeneous control intervals, including its shared endpoints.
    """
    arcs, deviation, length_error = _arc_svg_plan(curve)
    if not math.isfinite(deviation+length_error):
        raise _UnresolvedError("Native SVG arc cannot be represented with bounded circles")
    start, result = _fraction_point(curve.start), []
    for index, (radius, sweep, endpoint) in enumerate(arcs):
        end, r = _fraction_point(endpoint), Fraction(radius)
        chord = _sub(end, start)
        squared = _dot(chord, chord)
        h2 = r*r-squared/4
        if squared <= 0 or h2 <= 0:
            raise _UnresolvedError("Native SVG arc is not a strictly minor circle interval")
        distance, height = _isqrt(_iv(squared)), _isqrt(_iv(h2))
        weight = _idiv(height, _iv(r))
        sign = 1 if sweep else -1
        perpendicular = (-chord[1]*sign, chord[0]*sign)
        midpoint = tuple((a+b)/2 for a, b in zip(start, end))
        ratio = _idiv(height, distance)
        center = tuple(_iadd(_iv(m), _imul(_iv(p), ratio))
                       for m, p in zip(midpoint, perpendicular))
        q_weighted = tuple(_isub(_imul(weight, _iv(m)),
                                _idiv(_imul(_iv(p), distance), _iv(4*r)))
                           for m, p in zip(midpoint, perpendicular))
        homogeneous = ((*(_iv(x) for x in start), _iv(1)),
                       (*q_weighted, weight), (*(_iv(x) for x in end), _iv(1)))
        native = {"center": center, "radius": r, "start": start, "end": end, "sign": sign}
        result.append(_Node(curve, index/len(arcs), (index+1)/len(arcs),
                            homogeneous=homogeneous, native=native))
        start = end
    return result


def _bbox(node, budget):
    controls = _hull(node)
    return tuple((math.nextafter(float(min(p[i] for p in controls)), -math.inf)-budget.guard,
                  math.nextafter(float(max(p[i] for p in controls)), math.inf)+budget.guard)
                 for i in (0, 1))


def _boxes_separate(a, b, budget):
    ba, bb = _bbox(a, budget), _bbox(b, budget)
    return any(x[1] < y[0] or y[1] < x[0] for x, y in zip(ba, bb))


def _positive_side(node, normal, origin, allowed, budget):
    """Return (nonnegative, strictly positive except allowed endpoints)."""
    offset = _dot(normal, origin)
    ends = node.ends()
    endpoint_values = [_dot(normal, p)-offset for p in ends]
    endpoints_strict = all(value > 0 or point in allowed
                           for point, value in zip(ends, endpoint_values))
    if node.controls is not None:
        values = [_dot(normal, p)-offset for p in node.controls]
        nonnegative = min(values) >= 0
        return nonnegative, nonnegative and max(values) > 0 and endpoints_strict
    boxes = [_cartesian(control) for control in node.homogeneous]
    ranges = [_isub(_iadd(_imul(_iv(normal[0]), box[0]),
                          _imul(_iv(normal[1]), box[1])), _iv(offset)) for box in boxes]
    nonnegative = all(value[0] >= 0 for value in ranges)
    # Positive rational Bernstein weights: an entire control interval must be
    # strictly positive, not merely one possible corner of an uncertain hull.
    interior_strict = any(value[0] > 0 for value in ranges)
    fixed_endpoints = [all(lo == hi for lo, hi in box) for box in (boxes[0], boxes[-1])]
    endpoints_strict = all(value[0] > 0 or (fixed and point in allowed)
                           for value, fixed, point in zip((ranges[0], ranges[-1]),
                                                          fixed_endpoints, ends))
    return nonnegative, nonnegative and interior_strict and endpoints_strict


def _endpoint_only(a, b, allowed, budget):
    if not allowed:
        return False
    origin = next(iter(allowed))
    vectors = [(Fraction(1), Fraction(0)), (Fraction(0), Fraction(1))]
    outgoing = [point for node in (a, b) for point in node.ends() if point != origin]
    outgoing.extend(_hull(a))
    outgoing.extend(_hull(b))
    outgoing = [_sub(p, origin) for p in outgoing]
    vectors.extend(outgoing)
    vectors.extend((-v[1], v[0]) for v in outgoing)
    if len(outgoing) >= 2:
        vectors.append(_sub(outgoing[0], outgoing[-1]))
    for normal in vectors:
        if normal == (0, 0):
            continue
        for sign in (1, -1):
            n = tuple(sign*x for x in normal)
            positive, strict_a = _positive_side(a, n, origin, allowed, budget)
            negative, strict_b = _positive_side(b, tuple(-x for x in n), origin, allowed, budget)
            if positive and negative and (strict_a or strict_b):
                return True
    return False


def _witness(a, b, point, method):
    return {"segments": [a.curve.segment_id, b.curve.segment_id],
            "parameter_intervals": [[a.t0, a.t1], [b.t0, b.t1]],
            "point": [float(x) for x in point], "method": method}


def _linear_witness(line, other, allowed):
    """Exact Bernstein sign-change witness against a finite authored line."""
    a, b = line.ends()
    direction = _sub(b, a)
    length2 = _dot(direction, direction)
    points = other.controls
    if points is None:
        return None
    values = [_cross(_sub(p, a), direction) for p in points]
    projections = [_dot(_sub(p, a), direction) for p in points]
    for point, value, projection in zip((points[0], points[-1]),
                                       (values[0], values[-1]),
                                       (projections[0], projections[-1])):
        if value == 0 and 0 <= projection <= length2 and point not in allowed:
            return _witness(line, other, point, "EXACT_AUTHORED_ENDPOINT_ON_OTHER_CURVE")
    if values[0]*values[-1] < 0 and min(projections) >= 0 and max(projections) <= length2:
        point = tuple((x+y)/2 for x, y in zip(points[0], points[-1]))
        result = _witness(line, other, point, "BERNSTEIN_SIGN_CHANGE_WITHIN_LINE_INTERVAL")
        result["point"] = None  # The certified root is bracketed, not a sampled midpoint.
        result["line_side_values"] = [float(values[0]), float(values[-1])]
        return result
    if len(points) == 2:
        determinant = _cross(direction, _sub(points[1], points[0]))
        if determinant:
            t = _cross(_sub(points[0], a), _sub(points[1], points[0])) / determinant
            u = _cross(_sub(points[0], a), direction) / determinant
            point = tuple(x+t*v for x, v in zip(a, direction))
            if 0 <= t <= 1 and 0 <= u <= 1 and point not in allowed:
                return _witness(line, other, point, "EXACT_RATIONAL_LINE_INTERSECTION")
    return None


def _icross(a, b):
    return _isub(_imul(a[0], b[1]), _imul(a[1], b[0]))


def _idot(a, b):
    return _iadd(_imul(a[0], b[0]), _imul(a[1], b[1]))


def _native_arc_contains(node, point):
    native = node.native
    center = native["center"]
    radial = tuple(_isub(value, c) for value, c in zip(point, center))
    first = tuple(_isub(_iv(value), c) for value, c in zip(native["start"], center))
    last = tuple(_isub(_iv(value), c) for value, c in zip(native["end"], center))
    a, b = _icross(first, radial), _icross(radial, last)
    if native["sign"] < 0:
        a, b = _ineg(a), _ineg(b)
    return a[0] > 0 and b[0] > 0


def _native_root_witness(a, b, point, method):
    middle = tuple(sum(value)/2 for value in point)
    result = _witness(a, b, middle, method)
    result["point_bounds"] = [[float(lo), float(hi)] for lo, hi in point]
    result["point"] = None  # The interval, rather than its midpoint, encloses the true root.
    return result


def _analytic_arc_witness(a, b, allowed, budget):
    if a.native is None:
        a, b = b, a
    if a.native is None or a.depth or b.depth:
        return None
    c0, r0 = a.native["center"], _iv(a.native["radius"])
    if b.curve.kind == "line":
        start, end = b.ends()
        direction = tuple(_iv(x) for x in _sub(end, start))
        relative = tuple(_isub(_iv(x), c) for x, c in zip(start, c0))
        aa = _idot(direction, direction)
        bb = _imul(_iv(2), _idot(relative, direction))
        cc = _isub(_idot(relative, relative), _isquare(r0))
        discriminant = _isub(_isquare(bb), _imul(_iv(4), _imul(aa, cc)))
        if discriminant[0] <= 0:
            return None
        root = _isqrt(discriminant)
        for sign in (-1, 1):
            parameter = _idiv(_iadd(_ineg(bb), _imul(_iv(sign), root)), _imul(_iv(2), aa))
            if parameter[0] < 0 or parameter[1] > 1:
                continue
            point = tuple(_iadd(_iv(x), _imul(parameter, d)) for x, d in zip(start, direction))
            if _native_arc_contains(a, point):
                return _native_root_witness(a, b, point, "NATIVE_SVG_CIRCLE_LINE_INTERVAL_ROOT")
    elif b.native is not None:
        c1, r1 = b.native["center"], _iv(b.native["radius"])
        # Identical fixed-endpoint/radius/sweep geometry is an exact overlap,
        # independent of the two uncertain algebraic-center enclosures.
        same = (a.native["start"], a.native["end"], a.native["sign"]) == (
            b.native["start"], b.native["end"], b.native["sign"]
        )
        reverse = (a.native["start"], a.native["end"], a.native["sign"]) == (
            b.native["end"], b.native["start"], -b.native["sign"]
        )
        if r0 == r1 and (same or reverse):
            result = _witness(a, b, a.native["start"], "IDENTICAL_NATIVE_SVG_ARC_OVERLAP")
            result["point"] = None
            return result
        delta = tuple(_isub(y, x) for x, y in zip(c0, c1))
        distance2 = _iadd(_isquare(delta[0]), _isquare(delta[1]))
        if distance2[0] <= 0:
            return None
        distance = _isqrt(distance2)
        along = _idiv(_iadd(_isub(_isquare(r0), _isquare(r1)), distance2),
                       _imul(_iv(2), distance))
        height2 = _isub(_isquare(r0), _isquare(along))
        if height2[0] <= 0:
            return None
        height = _isqrt(height2)
        unit = tuple(_idiv(value, distance) for value in delta)
        base = tuple(_iadd(c, _imul(along, u)) for c, u in zip(c0, unit))
        perpendicular = (_ineg(unit[1]), unit[0])
        for sign in (-1, 1):
            point = tuple(_iadd(p, _imul(_iv(sign), _imul(height, v)))
                          for p, v in zip(base, perpendicular))
            if _native_arc_contains(a, point) and _native_arc_contains(b, point):
                return _native_root_witness(a, b, point, "NATIVE_SVG_CIRCLE_CIRCLE_INTERVAL_ROOT")
    return None


def _pair(a, b, allowed, budget):
    pending = [(a, b)]
    while pending:
        a, b = pending.pop()
        budget.tick()
        if _boxes_separate(a, b, budget) or _endpoint_only(a, b, allowed, budget):
            continue
        witness = None
        if a.controls is not None and b.controls is not None:
            shared = (set(a.ends()) & set(b.ends())) - allowed
            if shared:
                witness = _witness(a, b, next(iter(shared)), "EXACT_DYADIC_CURVE_INTERSECTION")
        if a.curve.kind == "line":
            witness = witness or _linear_witness(a, b, allowed)
        elif b.curve.kind == "line":
            witness = witness or _linear_witness(b, a, allowed)
        if witness is None:
            witness = _analytic_arc_witness(a, b, allowed, budget)
        if witness is not None:
            raise _InvalidError("Authored curve boundaries intersect or overlap", witness)
        ba, bb = _bbox(a, budget), _bbox(b, budget)
        size_a = max(hi-lo for lo, hi in ba)
        size_b = max(hi-lo for lo, hi in bb)
        if size_a >= size_b:
            pending.extend((child, b) for child in a.split(budget))
        else:
            pending.extend((a, child) for child in b.split(budget))


def _simple_pieces(node, budget):
    budget.tick()
    if node.curve.kind in ("line", "arc"):
        return [node]
    differences = [_sub(b, a) for a, b in zip(node.controls, node.controls[1:])]
    candidates = [(1, 0), (0, 1), _sub(node.controls[-1], node.controls[0])]
    for direction in candidates:
        values = [_dot(d, direction) for d in differences]
        if (min(values) >= 0 and max(values) > 0) or (max(values) <= 0 and min(values) < 0):
            return [node]  # Strictly monotone interior projection; exact Bernstein proof.
    pieces = [piece for child in node.split(budget) for piece in _simple_pieces(child, budget)]
    for (ia, a), (ib, b) in combinations(enumerate(pieces), 2):
        allowed = set(a.ends()) & set(b.ends()) if ib == ia+1 else set()
        _pair(a, b, allowed, budget)
    return pieces


def _winding(loop, point, budget):
    """Certified homotopy to chords, followed by exact rational winding."""
    query = _fraction_point(point)
    pending, pieces = list(reversed(loop)), []
    while pending:
        node = pending.pop()
        budget.tick()
        box = _bbox(node, budget)
        outside = any(float(query[i]) < low or float(query[i]) > high
                      for i, (low, high) in enumerate(box))
        if outside:
            pieces.append(node.ends())
        else:
            pending.extend(reversed(node.split(budget)))
    winding = 0
    for a, b in pieces:
        side = _cross(_sub(b, a), _sub(query, a))
        if a[1] <= query[1] < b[1] and side > 0:
            winding += 1
        elif b[1] <= query[1] < a[1] and side < 0:
            winding -= 1
    return winding


def certify_region_topology(outer, holes=(), *, max_depth=24, max_nodes=20000):
    """Prove supported simple native-curve loops and strictly contained holes.

    INVALID needs an explicit analytic/Bernstein witness or certified winding.
    Unsupported/near-contact/precision/budget cases remain UNRESOLVED. This
    does not validate surface regularity, manufacturing detail or physical fit.
    """
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("Topology depth must be a nonnegative integer")
    if type(max_nodes) is not int or max_nodes < 0:
        raise ValueError("Topology node budget must be a nonnegative integer")
    loops = [tuple(outer), *(tuple(hole) for hole in holes)]
    points = [p for loop in loops for curve in loop
              for p in (curve.start, curve.end, *(
                  curve.data.values() if curve.kind == "cubic" else
                  [curve.data["center"]] if curve.kind == "arc" else []
              ))]
    magnitude = max((abs(x) for p in points for x in p), default=1.0)
    budget = _Budget(max_nodes, max_depth, 256*math.ulp(max(1.0, magnitude)))
    proof = ("EXACT_RATIONAL_BERNSTEIN_HULLS_AND_MONOTONE_SELF_PROOFS",
             "FIXED_ENDPOINT_NATIVE_SVG_ARCS_WITH_INTERVAL_RATIONAL_QUADRATIC_CONTROLS",
             "ANALYTIC_INTERVAL_CIRCLE_INTERSECTION_WITNESSES",
             "SHARED_ENDPOINT_ONLY_SEPARATING_HALFPLANES",
             "QUERY_AVOIDING_CONVEX_HOMOTOPY_AND_EXACT_CHORD_WINDING")
    try:
        if not math.isfinite(budget.guard):
            raise _UnresolvedError("Topology coordinate precision reserve is not finite")
        nodes = []
        for loop in loops:
            if len(loop) < 2 or any(not isinstance(curve, Curve) for curve in loop):
                raise _InvalidError("A boundary needs at least two authored source curves")
            if any(a.end != b.start for a, b in zip(loop, (*loop[1:], loop[0]))):
                raise _InvalidError("Authored boundary endpoints are not a closed continuous loop")
            current = []
            for curve in loop:
                if curve.kind == "arc":
                    # Large accepted source endpoint discrepancies cannot be
                    # turned into an endpoint-only topological assertion.
                    center = curve.data["center"]
                    theta = math.radians(curve.data["sweep_deg"])
                    x, y = _sub(curve.start, center)
                    predicted = (center[0]+x*math.cos(theta)-y*math.sin(theta),
                                 center[1]+x*math.sin(theta)+y*math.cos(theta))
                    if math.dist(predicted, curve.end) > budget.guard:
                        raise _UnresolvedError(
                            "Arc endpoint mismatch exceeds topology precision reserve"
                        )
                    arc_nodes = _native_arcs(curve)
                    current.extend(arc_nodes)
                    for _ in arc_nodes:
                        budget.tick()
                else:
                    current.extend(_simple_pieces(_Node(curve, controls=_control(curve)), budget))
            nodes.append(current)
        indexed = [(li, ni, node) for li, loop in enumerate(nodes) for ni, node in enumerate(loop)]
        for (ia, ja, a), (ib, jb, b) in combinations(indexed, 2):
            adjacent = ia == ib and (jb == ja+1 or (ja == 0 and jb == len(nodes[ia])-1))
            allowed = set(a.ends()) & set(b.ends()) if adjacent else set()
            _pair(a, b, allowed, budget)
        for index, hole in enumerate(nodes[1:], start=1):
            point = loops[index][0].start
            if _winding(nodes[0], point, budget) == 0:
                raise _InvalidError("A hole lies outside the outer authored boundary",
                               {"hole": index-1, "point": list(point), "winding": 0})
            for other_index, other in enumerate(nodes[1:], start=1):
                if index != other_index and _winding(other, point, budget) != 0:
                    raise _InvalidError("Authored holes are nested", {"hole": index-1,
                                                                  "inside_hole": other_index-1})
        return TopologyCertificate("VALID", "Native manufacturing-curve topology proved", None,
                                   budget.used, budget.guard, proof)
    except _InvalidError as exc:
        return TopologyCertificate("INVALID", exc.reason, exc.witness,
                                   budget.used, budget.guard, proof)
    except (_UnresolvedError, ArithmeticError, ValueError) as exc:
        return TopologyCertificate("UNRESOLVED", str(exc), None, budget.used, budget.guard, proof)
