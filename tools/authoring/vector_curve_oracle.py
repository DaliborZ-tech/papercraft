"""Independent Green integrals for native author-output paths, in page mm.

This test oracle imports no production geometry/writer helper. SVG circular
arcs are supported; an elliptical or unknown representation is refused.
"""

from __future__ import annotations

import math
import re


def line_integral(a, b):
    return (a[0] * b[1] - a[1] * b[0]) / 2


def cubic_integral(a, first, second, b):
    coeff = []
    for axis in (0, 1):
        p, q, r, s = a[axis], first[axis], second[axis], b[axis]
        coeff.append([p, 3 * (q - p), 3 * (p - 2 * q + r), -p + 3 * q - 3 * r + s])
    x, y = coeff
    return math.fsum((x[i] * j * y[j] - y[i] * j * x[j]) / (i + j)
                     for i in range(4) for j in range(1, 4)) / 2


def circle_integral(a, command):
    r, ry, rotation, large, sweep, bx, by = command
    if r <= 0 or not math.isclose(r, ry, rel_tol=1e-12) or rotation != 0:
        raise AssertionError("Independent oracle supports circular native arcs only")
    dx, dy = bx - a[0], by - a[1]
    chord2 = dx * dx + dy * dy
    if chord2 == 0:
        raise AssertionError("A full circle must be represented by distinct arc segments")
    h2 = r * r / chord2 - 0.25
    if h2 < -1e-12:
        raise AssertionError("Native arc radii do not cover its endpoints")
    h = math.sqrt(max(0, h2)) * (-1 if large == sweep else 1)
    cx, cy = (a[0] + bx) / 2 - h * dy, (a[1] + by) / 2 + h * dx
    first, last = math.atan2(a[1] - cy, a[0] - cx), math.atan2(by - cy, bx - cx)
    delta = (last - first) % (2 * math.pi) if sweep else -((first - last) % (2 * math.pi))
    return (cx * (by - a[1]) - cy * (bx - a[0]) + r * r * delta) / 2


def svg_signed_area(value):
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", value)
    sizes = {"M": 2, "L": 2, "C": 6, "A": 7, "Z": 0}
    terms, index, current, start = [], 0, None, None
    while index < len(tokens):
        op = tokens[index]
        if op not in sizes:
            raise AssertionError("Unexpected SVG representation: " + op)
        args = list(map(float, tokens[index + 1:index + 1 + sizes[op]]))
        if len(args) != sizes[op]:
            raise AssertionError("Incomplete native SVG command")
        index += len(args) + 1
        if op == "M":
            current = start = args
        elif op == "Z":
            terms.append(line_integral(current, start))
            current = start
        else:
            if current is None:
                raise AssertionError("Native path has no start")
            terms.append(line_integral(current, args) if op == "L" else
                         cubic_integral(current, args[:2], args[2:4], args[4:]) if op == "C" else
                         circle_integral(current, args))
            current = args[-2:]
    return math.fsum(terms)


def pdf_stroked_areas(reader):
    """Integrate actual PDF l/c operators after q/Q/cm transforms; exclude fills."""
    from pypdf.generic import ContentStream

    results = []
    for page_index, page in enumerate(reader.pages):
        matrix, stack = [1, 0, 0, 1, 0, 0], []
        terms, closed, current, start = [], [], None, None

        def point(x, y):
            a, b, c, d, e, f = matrix
            return [(a * x + c * y + e) * 25.4 / 72, (b * x + d * y + f) * 25.4 / 72]

        for operands, op in ContentStream(page.get_contents(), reader).operations:
            values = list(map(float, operands)) if op in (b"cm", b"m", b"l", b"c") else []
            if op == b"q":
                stack.append(matrix[:])
            elif op == b"Q":
                matrix = stack.pop()
            elif op == b"cm":
                a, b, c, d, e, f = matrix
                u, v, w, x, y, z = values
                matrix = [a*u+c*v, b*u+d*v, a*w+c*x, b*w+d*x, a*y+c*z+e, b*y+d*z+f]
            elif op == b"m":
                terms, current = [], point(*values)
                start = current
            elif op == b"l":
                end = point(*values)
                terms.append(line_integral(current, end))
                current = end
            elif op == b"c":
                first, second, end = [point(*values[i:i+2]) for i in (0, 2, 4)]
                terms.append(cubic_integral(current, first, second, end))
                current = end
            elif op == b"h":
                terms.append(line_integral(current, start))
                closed.append(math.fsum(terms))
                terms, current = [], start
            elif op in (b"S", b"s", b"f", b"f*", b"B", b"B*", b"b", b"b*", b"n"):
                if op == b"s" and terms:
                    closed.append(math.fsum([*terms, line_integral(current, start)]))
                if op in (b"S", b"s"):
                    results.extend((page_index, abs(area)) for area in closed)
                terms, closed, current, start = [], [], None, None
    return results
