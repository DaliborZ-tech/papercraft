"""Independent bounded editor geometry comparison; no production imports.

Normalized M/L/C/A/Z operands are exact rationals. A positive result proves
whole-curve proximity, accumulated length and direct closed-loop Green changes.
Minor circles use chord graphs, avoiding unstable large-center subtraction.
Changed closed regions additionally preserve topology by swept hull separation.
The original is an already validated exported source, not a new source approval.
"""

from __future__ import annotations

import math
from fractions import Fraction as Q
from functools import lru_cache

_GRID = 10**80
POSITION = Q(1, 50000)
LENGTH = AREA = Q(1, 100)


class EquivalenceUnresolved(ValueError):  # noqa: N818 - result status uses this name
    pass


def _q(value):
    if isinstance(value, bool):
        raise EquivalenceUnresolved("Boolean is not a path coordinate")
    try:
        result = Q(value)
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise EquivalenceUnresolved("Finite exact path operands are required") from exc
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > 8192:
        raise EquivalenceUnresolved("Path arithmetic input budget exceeded")
    return result


def _sqrt(value):
    if value < 0:
        raise EquivalenceUnresolved("A geometric square root is not real")
    root = math.isqrt(value.numerator * _GRID * _GRID // value.denominator)
    low = Q(root, _GRID)
    return low, low if low * low == value else Q(root + 1, _GRID)


def _out(value):
    a, b = value
    return Q(a.numerator * _GRID // a.denominator, _GRID), Q(
        -((-b.numerator * _GRID) // b.denominator), _GRID
    )


def _iv(value):
    return value, value


def _add(a, b):
    return _out((a[0] + b[0], a[1] + b[1]))


def _neg(a):
    return -a[1], -a[0]


def _sub(a, b):
    return _add(a, _neg(b))


def _mul(a, b):
    values = [x * y for x in a for y in b]
    return _out((min(values), max(values)))


def _div(a, b):
    if b[0] <= 0 <= b[1]:
        raise EquivalenceUnresolved("Unresolved interval denominator")
    return _mul(a, (1 / b[1], 1 / b[0]))


def _norm(vector):
    return _sqrt(sum(value * value for value in vector))[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _atan_small(value):
    total, power = Q(0), value
    for index in range(256):
        total += (-1) ** index * power / (2 * index + 1)
        power *= value * value
        error = power / (2 * index + 3)
        if error < Q(1, 10**95):
            return (total - error, total) if index % 2 == 0 else (total, total + error)
    raise EquivalenceUnresolved("Arctangent proof work budget exhausted")


@lru_cache(maxsize=1)
def _pi():
    # Machin identity, alternating-series bounds, independent of application math.
    a, b = _atan_small(Q(1, 5)), _atan_small(Q(1, 239))
    return 16 * a[0] - 4 * b[1], 16 * a[1] - 4 * b[0]


def _atan(value):
    if value < 0:
        return _neg(_atan(-value))
    if value > 1:
        return _sub(_mul(_iv(Q(1, 2)), _pi()), _atan(1 / value))
    if value > Q(1, 2):
        return _add(_atan_small(Q(1, 2)), _atan_small((value - Q(1, 2)) / (1 + value / 2)))
    return _atan_small(value)


def _cubic_green(points):
    axes = [
        (a, 3 * (b - a), 3 * (a - 2 * b + c), -a + 3 * b - 3 * c + d) for a, b, c, d in zip(*points)
    ]
    x, y = axes
    return (
        sum((x[i] * j * y[j] - y[i] * j * x[j]) / Q(i + j) for i in range(4) for j in range(1, 4))
        / 2
    )


def _arc_data(start, command):
    _, rx, ry, rotation, large, sweep, *end = command
    if rx <= 0 or ry <= 0 or large not in (0, 1) or sweep not in (0, 1):
        raise EquivalenceUnresolved("Invalid native arc radius or flags")
    if rx != ry:
        raise EquivalenceUnresolved("Changed elliptical arcs are outside the circular proof")
    c2 = sum((a - b) ** 2 for a, b in zip(start, end))
    if c2 <= 0 or c2 > 4 * rx * rx:
        raise EquivalenceUnresolved("SVG radius correction or collapsed arc is not supported")
    return rx, tuple(end), c2, large, sweep, rotation


def _green(primitive):
    op, start, command = primitive
    end = command[-2:]
    if op == "L":
        return _iv(_cross(start, end) / 2)
    if op == "C":
        return _iv(_cubic_green((start, command[1:3], command[3:5], command[5:7])))
    radius, end, c2, large, sweep, _ = _arc_data(start, command)
    chord = _sqrt(c2)
    height = _sqrt(radius * radius - c2 / 4)
    if height[0] == 0:
        if c2 != 4 * radius * radius:
            raise EquivalenceUnresolved("Arc area height precision unresolved")
        angle = _pi()
    else:
        ratio = _div(chord, _mul(_iv(Q(2)), height))
        angle = _mul(_iv(Q(2)), (_atan(ratio[0])[0], _atan(ratio[1])[1]))
    if large:
        angle = _sub(_mul(_iv(Q(2)), _pi()), angle)
    sine_term = _mul(chord, height)
    if large:
        sine_term = _neg(sine_term)
    segment = _mul(_iv(Q(1, 2)), _sub(_mul(_iv(radius * radius), angle), sine_term))
    return _add(_iv(_cross(start, end) / 2), segment if sweep else _neg(segment))


def _normalize(signature, max_commands):
    if not isinstance(signature, (list, tuple)) or not 0 < len(signature) <= max_commands:
        raise EquivalenceUnresolved("Finite nonempty normalized path required")
    result = []
    for command in signature:
        if not isinstance(command, (tuple, list)) or not command:
            raise EquivalenceUnresolved("Malformed normalized command")
        op = command[0]
        if (
            op not in {"M", "L", "C", "A", "Z"}
            or len(command) != {"M": 3, "L": 3, "C": 7, "A": 8, "Z": 1}[op]
        ):
            raise EquivalenceUnresolved("Normalized native command kind/arity is unsupported")
        result.append((op, *(_q(value) for value in command[1:])))
    return tuple(result)


def _primitives(signature):
    primitives, loops = [], []
    current = start = None
    loop = -1
    for command in signature:
        op = command[0]
        if op == "M":
            if loop >= 0 and not loops[loop]["closed"]:
                loops[loop]["open"] = True
            loops.append({"closed": False, "open": False})
            loop += 1
            current = start = command[-2:]
        elif current is None:
            raise EquivalenceUnresolved("Path drawing lacks initial M")
        elif op == "Z":
            if loops[loop]["closed"]:
                raise EquivalenceUnresolved("Repeated path closure")
            primitives.append(("L", current, ("L", *start), loop, True))
            current = start
            loops[loop]["closed"] = True
        else:
            if loops[loop]["closed"]:
                raise EquivalenceUnresolved("Draw after closed subpath requires explicit M")
            primitives.append((op, current, command, loop, False))
            current = command[-2:]
    return primitives, loops


def _primitive_error(first, second):
    op, start, command = first[:3]
    _, other_start, other = second[:3]
    if op in ("L", "C"):
        controls = (start, *(command[i : i + 2] for i in range(1, len(command), 2)))
        target = (other_start, *(other[i : i + 2] for i in range(1, len(other), 2)))
        delta = [tuple(x - y for x, y in zip(a, b)) for a, b in zip(controls, target)]
        position = max(_norm(point) for point in delta)
        length = sum(_norm(tuple(x - y for x, y in zip(a, b))) for a, b in zip(delta, delta[1:]))
        return position, length
    r0, end0, c20, large, sweep, rotation = _arc_data(start, command)
    r1, end1, c21, large1, sweep1, rotation1 = _arc_data(other_start, other)
    if (large, sweep, rotation) != (large1, sweep1, rotation1):
        raise EquivalenceUnresolved("Arc flags/rotation changed")
    if (start, command) == (other_start, other):
        return Q(0), Q(0)
    if large or c20 == 4 * r0 * r0 or c21 == 4 * r1 * r1:
        raise EquivalenceUnresolved("Changed major/semicircle requires a separate proof")
    rmin = min(r0, r1)
    cmax = _sqrt(max(c20, c21))[1]
    cmin = _sqrt(min(c20, c21))[0]
    height2 = rmin * rmin - cmax * cmax / 4
    if height2 <= 0 or cmin <= 0:
        raise EquivalenceUnresolved("Minor-circle neighborhood loses regularity")
    q = _sqrt(height2)[0]
    if q <= 0:
        raise EquivalenceUnresolved("Minor-circle precision exhausted")
    endpoint = max(
        sum(abs(x - y) for x, y in zip(a, b)) for a, b in ((start, other_start), (end0, end1))
    )
    dr = abs(r0 - r1)
    dc = 2 * endpoint
    sag = cmax * cmax / (4 * (rmin + q))
    radius_lip = cmax * cmax / (4 * q * (rmin + q))
    chord_lip = cmax / (4 * q)
    position = endpoint + 4 * endpoint / cmin * sag + radius_lip * dr + chord_lip * dc
    x = cmax / (2 * rmin)
    cosine = q / rmin
    length = 2 * x**3 / (3 * cosine**3) * dr + dc / cosine
    return _out(_iv(position))[1], _out(_iv(length))[1]


def _homogeneous(primitive):
    op, start, command = primitive[:3]
    if op != "A":
        return tuple(
            tuple(_iv(v) for v in (*p, Q(1)))
            for p in (start, *(command[i : i + 2] for i in range(1, len(command), 2)))
        )
    radius, end, c2, large, sweep, _ = _arc_data(start, command)
    if large:
        raise EquivalenceUnresolved("Changed path with major-arc topology is unsupported")
    chord = tuple(b - a for a, b in zip(start, end))
    c = _sqrt(c2)
    q = _sqrt(radius * radius - c2 / 4)
    w = _div(q, _iv(radius))
    sign = 1 if sweep else -1
    perp = (-chord[1] * sign, chord[0] * sign)
    mid = tuple((a + b) / 2 for a, b in zip(start, end))
    middle = tuple(
        _sub(_mul(w, _iv(m)), _div(_mul(_iv(p), c), _iv(4 * radius))) for m, p in zip(mid, perp)
    )
    return (
        tuple(_iv(v) for v in (*start, Q(1))),
        (*middle, w),
        tuple(_iv(v) for v in (*end, Q(1))),
    )


def _split(controls):
    rows = [controls]
    while len(rows[-1]) > 1:
        rows.append(
            tuple(
                tuple(_mul(_add(a, b), _iv(Q(1, 2))) for a, b in zip(p, q))
                for p, q in zip(rows[-1], rows[-1][1:])
            )
        )
    return tuple(row[0] for row in rows), tuple(row[-1] for row in reversed(rows))


def _hull(controls):
    if any(point[2][0] <= 0 for point in controls):
        raise EquivalenceUnresolved("Positive rational hull weight not proved")
    return tuple(tuple(_div(value, p[2]) for value in p[:2]) for p in controls)


def _dot(point, direction):
    value = _iv(Q(0))
    for x, n in zip(point, direction):
        value = _add(value, _mul(x, _iv(n)))
    return value


def _directions(points):
    # Candidate directions are search hints only; every accepted sign is rational.
    candidates = [(Q(1), Q(0)), (Q(0), Q(1))]
    vectors = []
    for controls in points:
        a, b = controls[0], controls[-1]
        v = tuple((y[0] + y[1] - x[0] - x[1]) / 2 for x, y in zip(a, b))
        if any(v):
            vectors.append(v)
            candidates.extend((v, tuple(-x for x in v)))
    for i, a in enumerate(vectors):
        for b in vectors[i + 1 :]:
            v = tuple(x + y for x, y in zip(a, b))
            if any(v):
                candidates.extend((v, tuple(-x for x in v)))
    return candidates


def _monotone(controls, direction):
    degree = len(controls) - 1
    numerator = [_dot(p[:2], direction) for p in controls]
    weight = [p[2] for p in controls]
    dn = [_mul(_sub(b, a), _iv(Q(degree))) for a, b in zip(numerator, numerator[1:])]
    dw = [_mul(_sub(b, a), _iv(Q(degree))) for a, b in zip(weight, weight[1:])]
    terms = []
    n = 2 * degree - 1
    for k in range(n + 1):
        total = _iv(Q(0))
        for i in range(degree):
            j = k - i
            if 0 <= j <= degree:
                factor = Q(math.comb(degree - 1, i) * math.comb(degree, j), math.comb(n, k))
                total = _add(
                    total,
                    _mul(_iv(factor), _sub(_mul(dn[i], weight[j]), _mul(dw[i], numerator[j]))),
                )
        terms.append(total)
    return all(a >= 0 for a, _ in terms) and any(a > 0 for a, _ in terms)


class _Node:
    def __init__(self, before, after, loop, index, depth=0):
        self.before, self.after, self.loop, self.index, self.depth = (
            before,
            after,
            loop,
            index,
            depth,
        )
        self.hulls = (_hull(before), _hull(after))
        self.box = tuple(
            (
                min(p[i][0] for hull in self.hulls for p in hull),
                max(p[i][1] for hull in self.hulls for p in hull),
            )
            for i in range(2)
        )

    def split(self):
        a, b = _split(self.before)
        c, d = _split(self.after)
        return (
            _Node(a, c, self.loop, self.index, self.depth + 1),
            _Node(b, d, self.loop, self.index, self.depth + 1),
        )


def _halfplane(first, second, other_joint=False):
    # Expected adjacency at first.end == second.start, for BOTH source/editor.
    for direction in _directions((*first.hulls, *second.hulls)):
        valid = True
        for a, b in zip(first.hulls, second.hulls):
            joint_a, joint_b = a[-1], b[0]
            left = [_dot(tuple(_sub(x, y) for x, y in zip(p, joint_a)), direction) for p in a[:-1]]
            right = [_dot(tuple(_sub(x, y) for x, y in zip(p, joint_b)), direction) for p in b[1:]]
            left_strict = any(iv[1] < 0 for iv in left)
            right_strict = any(iv[0] > 0 for iv in right)
            if not (
                all(iv[1] <= 0 for iv in left)
                and all(iv[0] >= 0 for iv in right)
                and (left_strict or right_strict)
            ):
                valid = False
                break
            # A curve lying entirely in the separating line must not hide
            # the other curve's NON-shared endpoint on its interior.
            if not other_joint and (
                (not right_strict and left[0][1] >= 0) or (not left_strict and right[-1][0] <= 0)
            ):
                valid = False
                break
        if valid and not other_joint:
            # If both interiors are strict, their other endpoints can still
            # lie in the separator. Prove those endpoint sweeps disjoint too.
            ends_a = [h[0] for h in first.hulls]
            ends_b = [h[-1] for h in second.hulls]
            if not any(
                max(p[i][1] for p in ends_a) < min(p[i][0] for p in ends_b)
                or max(p[i][1] for p in ends_b) < min(p[i][0] for p in ends_a)
                for i in range(2)
            ):
                valid = False
        if valid:
            return True
    return False


def _topology(first, second, loops, max_work, max_depth):
    work = [0]

    def charge():
        work[0] += 1
        if work[0] > max_work:
            raise EquivalenceUnresolved("Swept topology work budget exhausted")

    nodes = []
    for i, (a, b) in enumerate(zip(first, second)):
        if a[0] == "L" and (a[1] == a[2][-2:] or b[1] == b[2][-2:]):
            if a[1] == a[2][-2:] and b[1] == b[2][-2:] and a[0] == "L":
                continue
            raise EquivalenceUnresolved("A path edge collapsed during editor round-trip")
        aa, bb = _homogeneous(a), _homogeneous(b)
        # A semicircle's middle weight is zero; one subdivision makes positive hulls.
        seeds = [(aa, bb, 0)]
        while seeds:
            x, y, depth = seeds.pop()
            charge()
            if min(p[2][0] for p in (*x, *y)) <= 0:
                if depth >= max_depth:
                    raise EquivalenceUnresolved("Rational hull depth exhausted")
                xl, xr = _split(x)
                yl, yr = _split(y)
                seeds.extend(((xr, yr, depth + 1), (xl, yl, depth + 1)))
                continue
            node = _Node(x, y, a[3], i, depth)
            if any(_monotone(x, n) and _monotone(y, n) for n in _directions(node.hulls)):
                nodes.append(node)
            elif depth < max_depth:
                xl, xr = _split(x)
                yl, yr = _split(y)
                seeds.extend(((xr, yr, depth + 1), (xl, yl, depth + 1)))
            else:
                raise EquivalenceUnresolved("Whole-curve monotonicity depth exhausted")
    # Ordered leaves have the exact same algebraic endpoints by subdivision.
    adjacency = set()
    for i in range(len(nodes) - 1):
        if nodes[i].loop == nodes[i + 1].loop:
            adjacency.add((i, i + 1))
    for loop, data in enumerate(loops):
        group = [i for i, n in enumerate(nodes) if n.loop == loop]
        if data["closed"] and len(group) > 1:
            adjacency.add((group[-1], group[0]))

    def disjoint(a, b):
        return any(x[1] < y[0] or y[1] < x[0] for x, y in zip(a.box, b.box))

    def pair(a, b, joined=False, other_joint=False):
        charge()
        if (
            disjoint(a, b)
            or joined
            and _halfplane(a, b, other_joint)
            or other_joint
            and _halfplane(b, a, joined)
        ):
            return
        if max(a.depth, b.depth) >= max_depth:
            raise EquivalenceUnresolved("Swept curves touch/cross or topology depth exhausted")
        size_a = max(v - u for u, v in a.box)
        size_b = max(v - u for u, v in b.box)
        if size_a >= size_b:
            left, right = a.split()
            pair(left, b, False, other_joint)
            pair(right, b, joined, False)
        else:
            left, right = b.split()
            pair(a, left, joined, False)
            pair(a, right, False, other_joint)

    active = []
    for index in sorted(range(len(nodes)), key=lambda i: nodes[i].box[0][0]):
        node = nodes[index]
        active = [i for i in active if nodes[i].box[0][1] >= node.box[0][0]]
        for old in active:
            if disjoint(nodes[old], node):
                continue
            pair(nodes[old], node, (old, index) in adjacency, (index, old) in adjacency)
        active.append(index)
    return {
        "status": "SWEPT_SIMPLE_DISJOINT_TOPOLOGY_PRESERVED",
        "work_used": work[0],
        "monotone_leaf_count": len(nodes),
        "max_work": max_work,
        "max_depth": max_depth,
    }


def certify_path_equivalence(before, after, *, max_commands=100000, max_work=200000, max_depth=24):
    """Fixed original limits: 2e-5mm whole position, .01mm length, .01mm² net area.

    Area sums absolute direct signed-Green differences PER closed loop. This
    bounds any preserved body-minus-holes net assignment without enlarging the
    floor by tabs or cancelling errors from different holes.
    """
    result = {
        "status": "UNRESOLVED",
        "position_limit_mm_exact": str(POSITION),
        "length_limit_mm_exact": str(LENGTH),
        "area_limit_mm2_exact": str(AREA),
        "scope": "CERTIFIED_SOURCE_EDITOR_EQUIVALENCE_NOT_NEW_SOURCE_OR_PHYSICAL_APPROVAL",
    }
    try:
        if (
            type(max_commands) is not int
            or max_commands < 1
            or type(max_work) is not int
            or max_work < 1
            or type(max_depth) is not int
            or not 1 <= max_depth <= 32
        ):
            raise EquivalenceUnresolved("Finite positive comparison work budgets required")
        first, second = _normalize(before, max_commands), _normalize(after, max_commands)
        if len(first) != len(second) or any(
            (a[0], len(a)) != (b[0], len(b)) for a, b in zip(first, second)
        ):
            raise EquivalenceUnresolved("Native command kinds or subpath topology changed")
        a, loops = _primitives(first)
        b, otherloops = _primitives(second)
        if loops != otherloops:
            raise EquivalenceUnresolved("Material subpath closure changed")
        if first == second:
            return {
                **result,
                "status": "CERTIFIED",
                "max_position_bound_mm_exact": "0",
                "global_length_difference_bound_mm_exact": "0",
                "net_area_difference_bound_mm2_exact": "0",
                "closed_loop_count": sum(v["closed"] for v in loops),
                "topology": {"status": "EXACT_UNCHANGED_GEOMETRY"},
                "command_count": len(first),
            }
        position = max(
            (
                _norm(tuple(x - y for x, y in zip(c[1:], d[1:])))
                for c, d in zip(first, second)
                if c[0] == "M"
            ),
            default=Q(0),
        )
        length = Q(0)
        green = {}
        arc_count = cubic_count = 0
        for x, y in zip(a, b):
            p, length_delta = _primitive_error(x, y)
            position = max(position, p)
            length += length_delta
            arc_count += x[0] == "A"
            cubic_count += x[0] == "C"
            if x[:3] == y[:3]:
                delta = _iv(Q(0))
            else:
                delta = _sub(_green(y[:3]), _green(x[:3]))
            green[x[3]] = _add(green.get(x[3], _iv(Q(0))), delta)
        area = sum(max(abs(x), abs(y)) for loop, (x, y) in green.items() if loops[loop]["closed"])
        result.update(
            {
                "max_position_bound_mm_exact": str(position),
                "global_length_difference_bound_mm_exact": str(length),
                "net_area_difference_bound_mm2_exact": str(area),
                "closed_loop_count": sum(v["closed"] for v in loops),
                "command_count": len(first),
                "arc_count": arc_count,
                "cubic_count": cubic_count,
                "green_difference_per_subpath_exact": {
                    str(k): list(map(str, v)) for k, v in green.items()
                },
            }
        )
        if position > POSITION or length > LENGTH or area > AREA:
            raise EquivalenceUnresolved(
                "Whole position/global length/direct net area budget not proved"
            )
        result["topology"] = _topology(a, b, loops, max_work, max_depth)
        result["status"] = "CERTIFIED"
    except (EquivalenceUnresolved, ArithmeticError, ValueError, TypeError, IndexError) as exc:
        result["reason"] = str(exc)
    return result


def certify_linear_frame(before, after):
    """Only translate/rotate lists; exact net angle proves identical linear part."""

    def angle(text):
        import re

        if not isinstance(text, str) or len(text) > 65536:
            raise EquivalenceUnresolved("Finite explicit transform list required")
        token = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
        total = Q(0)
        position = 0
        count = 0
        for match in re.finditer(r"(translate|rotate)\s*\(([^)]*)\)", text or ""):
            count += 1
            if count > 256:
                raise EquivalenceUnresolved("Frame operator budget exhausted")
            if text[position : match.start()].strip(" ,\t\r\n"):
                raise EquivalenceUnresolved("Unsupported scale/skew/matrix frame operator")
            values = []
            end = 0
            for value in re.finditer(token, match[2]):
                if match[2][end : value.start()].strip(" ,\t\r\n"):
                    raise EquivalenceUnresolved("Malformed frame operand")
                values.append(_q(value.group()))
                end = value.end()
            if match[2][end:].strip(" ,\t\r\n"):
                raise EquivalenceUnresolved("Malformed frame list")
            if (
                match[1] == "translate"
                and len(values) not in (1, 2)
                or match[1] == "rotate"
                and len(values) not in (1, 3)
            ):
                raise EquivalenceUnresolved("Unsupported frame arity")
            if match[1] == "rotate":
                total += values[0]
            position = match.end()
        if (text or "")[position:].strip(" ,\t\r\n"):
            raise EquivalenceUnresolved("Unsupported scale/skew/matrix frame operator")
        return total % 360

    try:
        first, second = angle(before), angle(after)
        if first != second:
            raise EquivalenceUnresolved("Actual part linear rotation changed")
        return {
            "status": "CERTIFIED_TRANSLATION_ONLY",
            "net_angle_deg_exact": str(first),
            "allowed_operators": ["translate", "rotate"],
            "units_condition": "UNCHANGED_ROOT_VIEWBOX_AND_PHYSICAL_SIZE",
        }
    except (ValueError, ArithmeticError, TypeError) as exc:
        return {"status": "UNRESOLVED", "reason": str(exc)}
