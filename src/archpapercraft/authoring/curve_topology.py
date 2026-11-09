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

from .curves import Curve, _control, _split, _sqrt_bounds, evaluate


@dataclass(frozen=True)
class TopologyCertificate:
    status: str
    reason: str
    witness: dict | None
    examined_nodes: int
    numerical_guard: float
    proof: tuple[str, ...]


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

    def ends(self):
        if self.controls is not None:
            return self.controls[0], self.controls[-1]
        return _fraction_point(evaluate(self.curve, self.t0)), _fraction_point(
            evaluate(self.curve, self.t1)
        )

    def split(self, budget):
        if self.depth >= budget.depth:
            raise _UnresolvedError("Finite topology subdivision depth exhausted")
        middle = (self.t0 + self.t1) / 2
        if middle == self.t0 or middle == self.t1:
            raise _UnresolvedError("Topology parameter precision exhausted")
        left, right = (None, None) if self.controls is None else _split(self.controls)
        return (_Node(self.curve, self.t0, middle, self.depth+1, left),
                _Node(self.curve, middle, self.t1, self.depth+1, right))


def _fraction_point(point):
    return tuple(Fraction(x) for x in point)


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def _arc_values(node, normal=(1, 0)):
    """Exact extrema locations of a sinusoidal circular-arc projection.

    Values use the declared floating evaluation reserve. Authored endpoints
    remain endpoints; no finite subset of curve samples is the range proof.
    """
    curve = node.curve
    center = curve.data["center"]
    radius = math.dist(curve.start, center)
    start_angle = math.atan2(curve.start[1]-center[1], curve.start[0]-center[0])
    sweep = math.radians(curve.data["sweep_deg"])
    a, b = sorted((start_angle+sweep*node.t0, start_angle+sweep*node.t1))
    phi = math.atan2(float(normal[1]), float(normal[0]))
    values = [float(_dot(point, normal)) for point in node.ends()]
    interior = []
    for k in range(math.floor((a-phi)/math.pi)-1, math.ceil((b-phi)/math.pi)+2):
        angle = phi+k*math.pi
        if a < angle < b:
            value = (_dot(center, normal)
                     + radius*math.hypot(*normal)*(1 if k % 2 == 0 else -1))
            values.append(float(value))
            interior.append(float(value))
    return values, interior


def _bbox(node, budget):
    if node.controls is not None:
        return tuple((float(min(p[i] for p in node.controls))-budget.guard,
                      float(max(p[i] for p in node.controls))+budget.guard) for i in (0, 1))
    return tuple((min(values)-budget.guard, max(values)+budget.guard)
                 for values, _ in (_arc_values(node, (1, 0)), _arc_values(node, (0, 1))))


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
    values, interior = _arc_values(node, normal)
    guard = budget.guard*math.hypot(*normal)
    # An interior extremum near zero cannot be waved away as an endpoint.
    interior_ok = all(value-float(offset) > guard for value in interior)
    endpoints_ok = all(value > guard or (value == 0 and point in allowed)
                       for point, value in zip(ends, endpoint_values))
    nonnegative = interior_ok and endpoints_ok
    return nonnegative, nonnegative and endpoints_strict


def _endpoint_only(a, b, allowed, budget):
    if not allowed:
        return False
    origin = next(iter(allowed))
    vectors = [(Fraction(1), Fraction(0)), (Fraction(0), Fraction(1))]
    outgoing = [point for node in (a, b) for point in node.ends() if point != origin]
    if a.controls:
        outgoing.extend(a.controls)
    if b.controls:
        outgoing.extend(b.controls)
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


def _arc_contains_interior(node, point, guard):
    curve, center = node.curve, node.curve.data["center"]
    radius = math.dist(curve.start, center)
    angle = math.atan2(point[1]-center[1], point[0]-center[0])
    start = math.atan2(curve.start[1]-center[1], curve.start[0]-center[0])
    sweep = math.radians(curve.data["sweep_deg"])
    distance = ((angle-start) if sweep > 0 else (start-angle)) % (2*math.pi)
    reserve = 8*guard/radius
    return abs(sweep)*node.t0+reserve < distance < abs(sweep)*node.t1-reserve


def _circle_line_roots(arc, point, direction):
    center = _fraction_point(arc.curve.data["center"])
    radial = _sub(_fraction_point(arc.curve.start), center)
    relative = _sub(point, center)
    aa, bb, cc = (_dot(direction, direction), 2*_dot(relative, direction),
                  _dot(relative, relative)-_dot(radial, radial))
    discriminant = bb*bb-4*aa*cc
    if aa == 0 or discriminant < 0:
        return []
    low, high = _sqrt_bounds(discriminant)
    roots = []
    for sign in (-1, 1):
        bounds = [(-bb+sign*Fraction(value))/(2*aa) for value in (low, high)]
        roots.append((min(bounds), max(bounds)))
    return roots


def _analytic_arc_witness(a, b, allowed, budget):
    if a.curve.kind != "arc":
        a, b = b, a
    if a.curve.kind != "arc":
        return None
    if b.curve.kind == "line":
        point, end = b.ends()
        direction = _sub(end, point)
        roots = _circle_line_roots(a, point, direction)
        for low, high in roots:
            if not 0 <= low <= high <= 1:
                continue
            if float(high-low)*max(abs(float(v)) for v in direction) > budget.guard:
                continue
            value = (low+high)/2
            candidate = tuple(x+value*v for x, v in zip(point, direction))
            candidate_float = tuple(float(x) for x in candidate)
            if _arc_contains_interior(a, candidate_float, budget.guard):
                return _witness(a, b, candidate, "ANALYTIC_CIRCLE_LINE_ROOT_IN_ARC_INTERVAL")
    elif b.curve.kind == "arc":
        c0, c1 = (_fraction_point(n.curve.data["center"]) for n in (a, b))
        r0, r1 = (_dot(_sub(_fraction_point(n.curve.start), c),
                       _sub(_fraction_point(n.curve.start), c)) for n, c in ((a, c0), (b, c1)))
        normal = tuple(2*x for x in _sub(c1, c0))
        length2 = _dot(normal, normal)
        if length2:
            offset = r0-r1+_dot(c1, c1)-_dot(c0, c0)
            point = tuple(x*offset/length2 for x in normal)
            direction = (-normal[1], normal[0])
            for low, high in _circle_line_roots(a, point, direction):
                if float(high-low)*max(abs(float(v)) for v in direction) > budget.guard:
                    continue
                candidate = tuple(x+(low+high)/2*v for x, v in zip(point, direction))
                cf = tuple(float(x) for x in candidate)
                if all(_arc_contains_interior(n, cf, budget.guard) for n in (a, b)):
                    return _witness(a, b, candidate, "ANALYTIC_CIRCLE_CIRCLE_INTERSECTION")
        elif r0 == r1:
            for node, other in ((a, b), (b, a)):
                candidate = evaluate(node.curve, (node.t0+node.t1)/2)
                if _arc_contains_interior(other, candidate, budget.guard):
                    return _witness(a, b, candidate, "COINCIDENT_CIRCLE_ARC_OVERLAP")
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
             "ANALYTIC_ARC_EXTREMA_AND_CIRCLE_INTERSECTION_WITNESSES",
             "SHARED_ENDPOINT_ONLY_SEPARATING_HALFPLANES",
             "DECLARED_ARC_ENDPOINT_CONSTRAINTS_WITHIN_FLOAT_EVALUATION_RESERVE",
             "QUERY_AVOIDING_CONVEX_HOMOTOPY_AND_EXACT_CHORD_WINDING")
    try:
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
                node = _Node(curve, controls=None if curve.kind == "arc" else _control(curve))
                current.extend(_simple_pieces(node, budget))
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
        return TopologyCertificate("VALID", "Native curve boundary topology proved", None,
                                   budget.used, budget.guard, proof)
    except _InvalidError as exc:
        return TopologyCertificate("INVALID", exc.reason, exc.witness,
                                   budget.used, budget.guard, proof)
    except (_UnresolvedError, ArithmeticError, ValueError) as exc:
        return TopologyCertificate("UNRESOLVED", str(exc), None, budget.used, budget.guard, proof)
