"""Actual circular A or PDF cubic chains against native source arcs.

All serialized decimal operands stay rational. PDF controls are compared with
whole-interval Hermite enclosures of the source circle plus its fourth-
derivative remainder. Actual cubic lengths use rational subdivision bounds.
"""

from fractions import Fraction as Q

from archpapercraft.authoring.circular_shell import _native_arc_length
from archpapercraft.authoring.curve_area import _add, _mul, _neg, _point, _sqrt
from archpapercraft.authoring.curve_topology import _endpoint_arc_node
from archpapercraft.authoring.loft_area import _sin_cos


def _sub(a, b):
    return _add(a, _neg(b))


def _error(value, interval):
    return max(abs(value - interval[0]), abs(value - interval[1]))


def _node(start, command):
    if command[1] != command[2] or command[3] != 0 or command[4] != 0 or command[5] not in (0, 1):
        raise ValueError("Circular publisher requires unchanged minor circular A semantics.")
    return _endpoint_arc_node(None, tuple(start), tuple(command[-2:]), command[1], command[5])


def _cubic_length(controls, budget, work):
    stack, low, high = [(controls, budget)], Q(0), Q(0)
    while stack:
        values, allowance = stack.pop()
        work[0] += 1
        if work[0] > 100000:
            raise ValueError("Actual PDF cubic length exhausted its finite proof budget.")
        def distance(a, b):
            return _sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        lower = distance(values[0], values[-1])[0]
        upper = sum(distance(a, b)[1] for a, b in zip(values, values[1:]))
        if upper - lower <= allowance:
            low, high = low + lower, high + upper
            continue
        rows = [values]
        for _ in range(3):
            rows.append(
                [tuple((x + y) / 2 for x, y in zip(a, b)) for a, b in zip(rows[-1], rows[-1][1:])]
            )
        stack.extend(
            [
                (tuple(r[0] for r in rows), allowance / 2),
                (tuple(r[-1] for r in reversed(rows)), allowance / 2),
            ]
        )
    return low, high


def _pdf_arc(start, command, cubics, target_start, work):
    node = _node(start, command)
    center, radius = node.native["center"], command[1]
    length = _native_arc_length(start, command[-2:], radius)
    angle = (length[0] / radius, length[1] / radius)
    if not command[5]:
        angle = _neg(angle)
    step = _mul(angle, _point(Q(1, len(cubics))))
    vector = tuple(_sub(_point(x), c) for x, c in zip(start, center))

    def point_and_tangent(index):
        sine, cosine = _sin_cos(_mul(angle, _point(Q(index, len(cubics)))))
        x = _sub(_mul(vector[0], cosine), _mul(vector[1], sine))
        y = _add(_mul(vector[0], sine), _mul(vector[1], cosine))
        return tuple(_add(c, v) for c, v in zip(center, (x, y))), (_neg(y), x)

    bound, actual_low, actual_high = Q(0), Q(0), Q(0)
    p = target_start
    for index, cubic in enumerate(cubics):
        a, da = point_and_tangent(index)
        b, db = point_and_tangent(index + 1)
        ideal = (
            a,
            tuple(_add(v, _mul(d, _mul(step, _point(Q(1, 3))))) for v, d in zip(a, da)),
            tuple(_sub(v, _mul(d, _mul(step, _point(Q(1, 3))))) for v, d in zip(b, db)),
            b,
        )
        controls = (tuple(p), tuple(cubic[1:3]), tuple(cubic[3:5]), tuple(cubic[5:7]))
        bound = max(
            bound, *(sum(_error(x, iv) for x, iv in zip(q, v)) for q, v in zip(controls, ideal))
        )
        lo, hi = _cubic_length(controls, Q(1, 1000000 * len(cubics)), work)
        actual_low, actual_high, p = actual_low + lo, actual_high + hi, cubic[-2:]
    # Component Hermite remainder M4*h^4/384, Euclidean <=sqrt(2) bound.
    bound += Q(3, 2) * radius * max(abs(t) for t in step) ** 4 / 384
    return bound, max(abs(actual_low - length[1]), abs(actual_high - length[0]))


def coordinate_errors(source, target):
    source = [[c[0], *map(Q, c[1:])] for c in source]
    target = [[c[0], *map(Q, c[1:])] for c in target]
    position = length = Q(0)
    source_point = target_point = start_source = start_target = None
    cursor, work = 0, [0]
    for command in source:
        op = command[0]
        if cursor >= len(target):
            raise ValueError("Actual circular output lost a source interval.")
        actual = target[cursor]
        if op == "A":
            source_node = _node(source_point, command)
            source_length = _native_arc_length(source_point, command[-2:], command[1])
            if actual[0] == "A":
                actual_node = _node(target_point, actual)
                if actual[5] != command[5]:
                    raise ValueError("Actual A reversed its source orientation.")
                center_error = sum(
                    max(abs(x - y) for x in a for y in b)
                    for a, b in zip(source_node.native["center"], actual_node.native["center"])
                )
                endpoint_error = max(
                    sum(abs(x - y) for x, y in zip(a, b))
                    for a, b in ((source_point, target_point), (command[-2:], actual[-2:]))
                )
                r0, r1 = command[1], actual[1]
                error = center_error + endpoint_error + abs(r0 - r1)
                if min(r0, r1) <= 0 or error >= min(r0, r1) / 4:
                    raise ValueError("Actual A is outside the supported metric neighborhood.")
                position = max(
                    position, center_error + abs(r0 - r1) + 4 * max(r0, r1) * error / min(r0, r1)
                )
                actual_length = _native_arc_length(target_point, actual[-2:], r1)
                length += max(
                    abs(actual_length[0] - source_length[1]),
                    abs(actual_length[1] - source_length[0]),
                )
                cursor += 1
            elif actual[0] == "C":
                cubics = []
                while cursor < len(target) and target[cursor][0] == "C":
                    cubics.append(target[cursor])
                    cursor += 1
                    if sum(abs(x - y) for x, y in zip(cubics[-1][-2:], command[-2:])) < Q(1, 1000):
                        break
                bound, deficit = _pdf_arc(source_point, command, cubics, target_point, work)
                position, length = max(position, bound), length + deficit
                actual = cubics[-1]
            else:
                raise ValueError("Actual output replaced a native arc with unsupported geometry.")
            source_point, target_point = command[-2:], actual[-2:]
            continue
        if op != actual[0] or len(command) != len(actual):
            raise ValueError("Actual circular output changed a source line/curve or coverage.")
        a = [tuple(command[i : i + 2]) for i in range(1, len(command), 2)]
        b = [tuple(actual[i : i + 2]) for i in range(1, len(actual), 2)]
        if op == "Z":
            a, b = [start_source], [start_target]
        errors = [(x - u, y - v) for (x, y), (u, v) in zip(a, b)]
        position = max(position, *(abs(x) + abs(y) for x, y in errors))
        if op != "M":
            chain = [tuple(x - y for x, y in zip(source_point, target_point)), *errors]
            length += sum(abs(x - u) + abs(y - v) for (x, y), (u, v) in zip(chain, chain[1:]))
        else:
            start_source, start_target = a[0], b[0]
        source_point, target_point = a[-1], b[-1]
        cursor += 1
    if cursor != len(target):
        raise ValueError("Actual circular output contains unbound intervals.")
    return position, length
