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
    entry_scope: str = "AUTHORED_CURVE_DESCRIPTORS"


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
        result.append(_endpoint_arc_node(curve, start, end, r, sweep,
                                         index/len(arcs), (index+1)/len(arcs)))
        start = end
    return result


def _endpoint_arc_node(curve, start, end, radius, sweep, t0=0.0, t1=1.0):
    """Direct exact-input builder; no conversion through source center/sweep."""
    chord = _sub(end, start)
    squared = _dot(chord, chord)
    h2 = radius*radius-squared/4
    if radius <= 0 or squared <= 0 or h2 <= 0:
        raise _UnresolvedError("Native SVG arc is not a strictly minor circle interval")
    distance, height = _isqrt(_iv(squared)), _isqrt(_iv(h2))
    weight = _idiv(height, _iv(radius))
    sign = 1 if sweep else -1
    perpendicular = (-chord[1]*sign, chord[0]*sign)
    midpoint = tuple((a+b)/2 for a, b in zip(start, end))
    ratio = _idiv(height, distance)
    center = tuple(_iadd(_iv(m), _imul(_iv(p), ratio))
                   for m, p in zip(midpoint, perpendicular))
    q_weighted = tuple(_isub(_imul(weight, _iv(m)),
                            _idiv(_imul(_iv(p), distance), _iv(4*radius)))
                       for m, p in zip(midpoint, perpendicular))
    homogeneous = ((*(_iv(x) for x in start), _iv(1)),
                   (*q_weighted, weight), (*(_iv(x) for x in end), _iv(1)))
    native = {"center": center, "radius": radius, "start": start, "end": end, "sign": sign}
    return _Node(curve, t0, t1, homogeneous=homogeneous, native=native)


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
        result["line_side_values_exact"] = [str(values[0]), str(values[-1])]
        result["proper_interior_crossing"] = min(projections) > 0 and max(projections) < length2
        return result
    if len(points) == 2:
        determinant = _cross(direction, _sub(points[1], points[0]))
        if determinant:
            t = _cross(_sub(points[0], a), _sub(points[1], points[0])) / determinant
            u = _cross(_sub(points[0], a), direction) / determinant
            point = tuple(x+t*v for x, v in zip(a, direction))
            if 0 <= t <= 1 and 0 <= u <= 1 and point not in allowed:
                result = _witness(line, other, point, "EXACT_RATIONAL_LINE_INTERSECTION")
                result["proper_interior_crossing"] = 0 < t < 1 and 0 < u < 1
                return result
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


def _native_root_witness(a, b, point, method, transverse=False):
    middle = tuple(sum(value)/2 for value in point)
    result = _witness(a, b, middle, method)
    result["point_bounds"] = [[float(lo), float(hi)] for lo, hi in point]
    result["point"] = None  # The interval, rather than its midpoint, encloses the true root.
    result["proper_interior_crossing"] = transverse
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
                return _native_root_witness(
                    a, b, point, "NATIVE_SVG_CIRCLE_LINE_INTERVAL_ROOT",
                    parameter[0] > 0 and parameter[1] < 1,
                )
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
                return _native_root_witness(
                    a, b, point, "NATIVE_SVG_CIRCLE_CIRCLE_INTERVAL_ROOT", True,
                )
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


def _check_region_nodes(nodes, query_points, budget):
    """Shared native/source engine; all input construction precedes this proof."""
    indexed = [(li, ni, node) for li, loop in enumerate(nodes) for ni, node in enumerate(loop)]
    for (ia, ja, a), (ib, jb, b) in combinations(indexed, 2):
        adjacent = ia == ib and (jb == ja+1 or (ja == 0 and jb == len(nodes[ia])-1))
        allowed = set(a.ends()) & set(b.ends()) if adjacent else set()
        _pair(a, b, allowed, budget)
    for index, point in enumerate(query_points[1:], start=1):
        if _winding(nodes[0], point, budget) == 0:
            raise _InvalidError("A hole lies outside the outer authored boundary",
                                {"hole": index-1, "point": [float(x) for x in point],
                                 "point_exact": [str(x) for x in point], "winding": 0})
        for other_index, other in enumerate(nodes[1:], start=1):
            if index != other_index and _winding(other, point, budget) != 0:
                raise _InvalidError("Authored holes are nested", {"hole": index-1,
                                                                  "inside_hole": other_index-1})


def _topology_proof():
    return ("EXACT_RATIONAL_BERNSTEIN_HULLS_AND_MONOTONE_SELF_PROOFS",
            "FIXED_ENDPOINT_NATIVE_SVG_ARCS_WITH_INTERVAL_RATIONAL_QUADRATIC_CONTROLS",
            "ANALYTIC_INTERVAL_CIRCLE_INTERSECTION_WITNESSES",
            "SHARED_ENDPOINT_ONLY_SEPARATING_HALFPLANES",
            "QUERY_AVOIDING_CONVEX_HOMOTOPY_AND_EXACT_CHORD_WINDING")


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
    proof = _topology_proof()
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
        _check_region_nodes(nodes, [loop[0].start for loop in loops], budget)
        return TopologyCertificate("VALID", "Native manufacturing-curve topology proved", None,
                                   budget.used, budget.guard, proof)
    except _InvalidError as exc:
        return TopologyCertificate("INVALID", exc.reason, exc.witness,
                                   budget.used, budget.guard, proof)
    except (_UnresolvedError, ArithmeticError, ValueError) as exc:
        return TopologyCertificate("UNRESOLVED", str(exc), None, budget.used, budget.guard, proof)


@dataclass(frozen=True)
class _NativeCurve:
    start: tuple
    end: tuple
    kind: str
    segment_id: str


def _native_scalar(value):
    if isinstance(value, bool):
        raise _UnresolvedError("Boolean is not a native coordinate")
    return Fraction(value)


def _parse_native_loop(commands, prefix, budget):
    nodes, current, start, closed = [], None, None, False
    sizes = {"M": 2, "L": 2, "C": 6, "A": 7, "Z": 0}
    for index, command in enumerate(commands):
        if not isinstance(command, (tuple, list)) or not command:
            raise _UnresolvedError("Native commands must be nonempty tuple/list records")
        operation = command[0]
        if operation not in sizes or len(command)-1 != sizes[operation] or closed:
            raise _UnresolvedError("Unsupported or malformed absolute native path command")
        budget.tick()
        values = tuple(_native_scalar(x) for x in command[1:])
        if operation == "M":
            if start is not None:
                raise _UnresolvedError(
                    "Each native boundary must contain exactly one closed subpath"
                )
            current = start = values
            continue
        if current is None:
            raise _UnresolvedError("Native boundary must begin with an absolute M command")
        if operation == "Z":
            endpoint = start
            closed = True
        else:
            endpoint = values[-2:]
        kind = "cubic" if operation == "C" else "arc" if operation == "A" else "line"
        curve = _NativeCurve(current, endpoint, kind, f"{prefix}:{index}")
        if operation == "A":
            rx, ry, rotation, large, sweep = values[:5]
            if rx != ry or rx <= 0 or rotation != 0 or large != 0 or sweep not in (0, 1):
                raise _UnresolvedError(
                    "Only unrotated minor native circle A commands are supported"
                )
            if current != endpoint:
                nodes.append(_endpoint_arc_node(curve, current, endpoint, rx, sweep))
        elif operation == "C":
            controls = (current, values[:2], values[2:4], endpoint)
            if any(point != current for point in controls):
                nodes.extend(_simple_pieces(_Node(curve, controls=controls), budget))
        elif endpoint != current:
            nodes.extend(_simple_pieces(_Node(curve, controls=(current, endpoint)), budget))
        current = endpoint
    if not closed:
        raise _UnresolvedError("Native topology requires an explicit closed Z boundary")
    if not nodes:
        raise _InvalidError("Native boundary contains no material curve")
    return nodes, start


def _native_budget(command_loops, max_depth, max_nodes):
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("Topology depth must be a nonnegative integer")
    if type(max_nodes) is not int or max_nodes < 0:
        raise ValueError("Topology node budget must be a nonnegative integer")
    numbers = [_native_scalar(value) for loop in command_loops
               for command in loop for value in command[1:]]
    magnitude = max((abs(x) for x in numbers), default=Fraction(1))
    guard = 256*math.ulp(float(max(Fraction(1), magnitude)))
    if not math.isfinite(guard):
        raise _UnresolvedError("Native coordinate precision reserve is not finite")
    return _Budget(max_nodes, max_depth, guard)


def certify_native_region_topology(outer_commands, holes_commands=(), *,
                                   max_depth=24, max_nodes=20000):
    """Certify exactly supplied absolute M/L/C/A/Z coordinates, not a source surrogate.

    Records are tuples/lists such as ('M',x,y), ('C',x1,y1,x2,y2,x,y),
    ('A',r,r,0,0,sweep,x,y), ('Z',). Decimal, Fraction and decimal strings
    remain exact rationals; floats retain their exact binary values. No source
    Curve construction, center/sweep conversion or SVG reserialization occurs.
    Each argument is one closed subpath; ellipses/major arcs are UNRESOLVED.
    """
    proof = _topology_proof()
    geometry = "EXACTLY_SUPPLIED_NATIVE_PATH_GEOMETRY"
    entry = "SUPPLIED_ABSOLUTE_NATIVE_PATH_COMMANDS_EXACT_RATIONAL_COORDINATES"
    budget = _Budget(max_nodes, max_depth, 0.0)
    try:
        loops = [tuple(outer_commands), *(tuple(hole) for hole in holes_commands)]
        budget = _native_budget(loops, max_depth, max_nodes)
        parsed = [_parse_native_loop(loop, f"loop-{index}", budget)
                  for index, loop in enumerate(loops)]
        _check_region_nodes([nodes for nodes, _ in parsed], [point for _, point in parsed], budget)
        return TopologyCertificate("VALID", "Supplied native path topology proved", None,
                                   budget.used, budget.guard, proof, geometry, entry)
    except _InvalidError as exc:
        return TopologyCertificate("INVALID", exc.reason, exc.witness, budget.used,
                                   budget.guard, proof, geometry, entry)
    except (_UnresolvedError, ArithmeticError, ValueError, TypeError, IndexError) as exc:
        return TopologyCertificate("UNRESOLVED", str(exc), None, budget.used,
                                   budget.guard, proof, geometry, entry)


@dataclass(frozen=True)
class RegionSeparationCertificate:
    status: str
    reason: str
    witness: dict | None
    examined_nodes: int
    numerical_guard: float
    proof: tuple[str, ...]
    geometry_scope: str = "EXACTLY_SUPPLIED_NATIVE_PATH_GEOMETRY"
    entry_scope: str = "TWO_SUPPLIED_NATIVE_MATERIAL_REGIONS_WITH_HOLES"


def _material_contains(region, point, budget):
    return _winding(region[0], point, budget) != 0 and all(
        _winding(hole, point, budget) == 0 for hole in region[1:]
    )


def _strict_common_interior(first, second, budget):
    """A verified interior point proves positive area, never global absence."""
    boxes = [tuple((min(p[i] for n in region[0] for p in _hull(n)),
                    max(p[i] for n in region[0] for p in _hull(n))) for i in (0, 1))
             for region in (first, second)]
    overlap = [(max(a[0], b[0]), min(a[1], b[1])) for a, b in zip(*boxes)]
    if any(lo >= hi for lo, hi in overlap):
        return None
    for x in (Fraction(1, 2), Fraction(1, 4), Fraction(3, 4)):
        for y in (Fraction(1, 2), Fraction(1, 4), Fraction(3, 4)):
            point = tuple(lo+t*(hi-lo) for (lo, hi), t in zip(overlap, (x, y)))
            try:
                if all(_material_contains(region, point, budget) for region in (first, second)):
                    return {"method": "CERTIFIED_STRICT_COMMON_INTERIOR_POINT",
                            "point_exact": [str(value) for value in point]}
            except _UnresolvedError:
                if budget.used > budget.limit:
                    raise
                # A candidate on a boundary is not an area witness. Other
                # candidates may still prove an open common interior.
    return None


def certify_native_region_separation(first_outer, first_holes, second_outer, second_holes, *,
                                     max_depth=24, max_nodes=20000):
    """Prove DISJOINT material or positive-area OVERLAP for exact supplied paths.

    Both input regions must first pass their own topology proof. A boundary
    touch/overlap alone never proves positive material area. Holes are voids;
    containment is tested in both directions with certified material winding.
    All unresolved contact, unsupported geometry and exhausted budgets block.
    """
    proof = (*_topology_proof(),
             "POSITIVE_AREA_REQUIRES_STRICT_COMMON_INTERIOR_OR_PROVED_INTERIOR_BOUNDARY_CROSSING",
             "DISJOINT_REQUIRES_BOUNDARY_SEPARATION_AND_SYMMETRIC_MATERIAL_WINDING")
    budget = _Budget(max_nodes, max_depth, 0.0)

    def result(status, reason, witness=None):
        return RegionSeparationCertificate(status, reason, witness, budget.used,
                                           budget.guard, proof)

    try:
        commands = [[tuple(first_outer), *(tuple(hole) for hole in first_holes)],
                    [tuple(second_outer), *(tuple(hole) for hole in second_holes)]]
        budget = _native_budget([loop for region in commands for loop in region],
                                max_depth, max_nodes)
        regions = []
        for ri, command_loops in enumerate(commands):
            parsed = [_parse_native_loop(loop, f"region-{ri}-loop-{li}", budget)
                      for li, loop in enumerate(command_loops)]
            nodes, points = [a for a, _ in parsed], [b for _, b in parsed]
            _check_region_nodes(nodes, points, budget)
            regions.append(nodes)
        boundary_failure = None
        try:
            for a_loop in regions[0]:
                for b_loop in regions[1]:
                    for a in a_loop:
                        for b in b_loop:
                            _pair(a, b, set(), budget)
        except _InvalidError as exc:
            if exc.witness and exc.witness.get("proper_interior_crossing"):
                return result("OVERLAP", "Proved interior material-boundary crossing",
                              exc.witness)
            boundary_failure = exc.reason
        except _UnresolvedError as exc:
            boundary_failure = str(exc)
        if boundary_failure is None:
            for own, other in ((regions[0], regions[1]), (regions[1], regions[0])):
                point = own[0][0].ends()[0]
                if _material_contains(other, point, budget):
                    return result("OVERLAP", "Outer boundary lies strictly inside other material",
                                  {"method": "STRICT_MATERIAL_CONTAINMENT_WITH_DISJOINT_BOUNDARIES",
                                   "point_exact": [str(x) for x in point]})
            return result("DISJOINT",
                          "All boundaries separated and neither material contains the other")
        if budget.used <= budget.limit:
            witness = _strict_common_interior(*regions, budget)
            if witness:
                return result("OVERLAP", "Proved positive-area common material interior", witness)
        return result("UNRESOLVED",
                      "Boundary contact does not establish positive area: "+boundary_failure)
    except _InvalidError as exc:
        return result("UNRESOLVED", "An input material region is not valid: "+exc.reason,
                      exc.witness)
    except (_UnresolvedError, ArithmeticError, ValueError, TypeError, IndexError) as exc:
        return result("UNRESOLVED", str(exc))
