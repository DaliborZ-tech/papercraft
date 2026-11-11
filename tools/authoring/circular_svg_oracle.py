"""Independent high precision Green integral of actual native circular SVG.

This diagnostic oracle imports no application or production geometry. It reads
decimal tokens before any binary conversion. The chord's line integral plus
the oriented circular segment avoids subtracting huge center/radius terms in
almost straight arcs. It is an independent numerical check, not the writer's
interval certificate or a physical claim.
"""

import re
from decimal import Decimal
from decimal import localcontext

PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286"
       "208998628034825342117067982148086513282306647")
TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
SIZES = {"M": 2, "L": 2, "A": 7, "Z": 0}


def _asin(x):
    if not 0 <= x <= 1:
        raise ValueError("Actual arc radius does not span its endpoint chord")
    if x > Decimal(".75"):
        return PI/2 - _asin((1-x*x).sqrt())
    term = total = x
    for n in range(1, 2049):
        term *= x*x*Decimal((2*n-1)**2)/Decimal(2*n*(2*n+1))
        total += term
        if abs(term) < Decimal("1e-115"):
            return total
    raise ValueError("Independent arcsine work budget exceeded")


def _segment(angle):
    term = total = angle**3/6
    for n in range(2, 2049):
        term *= -angle*angle/Decimal((2*n)*(2*n+1))
        total += term
        if abs(term) < Decimal("1e-115"):
            return total
    raise ValueError("Independent circular segment work budget exceeded")


def svg_signed_area(value):
    if not isinstance(value, str) or len(value) > 4*1024*1024:
        raise ValueError("Independent SVG path input budget exceeded")
    tokens, previous = [], 0
    for match in TOKEN.finditer(value):
        if value[previous:match.start()].strip(" \t\r\n,"):
            raise ValueError("Unexpected SVG path syntax")
        tokens.append(match.group())
        previous = match.end()
    if value[previous:].strip(" \t\r\n,") or len(tokens) > 400000:
        raise ValueError("Unexpected or excessive SVG path input")
    with localcontext() as context:
        context.prec = 120
        total, current, start, index = Decimal(0), None, None, 0
        while index < len(tokens):
            op = tokens[index]
            if op not in SIZES:
                raise ValueError("Only explicit native M/L/A/Z circular material is supported")
            size = SIZES[op]
            raw = tokens[index+1:index+1+size]
            if len(raw) != size:
                raise ValueError("Incomplete SVG command")
            try:
                values = list(map(D, raw))
            except ArithmeticError as exc:
                raise ValueError("Invalid SVG number") from exc
            if any(not x.is_finite() or abs(x) > Decimal("1e30")
                   or len(x.as_tuple().digits) > 80 or abs(x.as_tuple().exponent) > 200
                   for x in values):
                raise ValueError("Independent SVG arithmetic budget exceeded")
            index += size+1
            if op == "M":
                if current is not None:
                    raise ValueError("A material subpath must close before another move")
                current = start = values
                continue
            if current is None:
                raise ValueError("SVG material command lacks an initial move")
            end = start if op == "Z" else values[-2:]
            total += (current[0]*end[1]-current[1]*end[0])/2
            if op == "A":
                radius, other, rotation, large, sweep = values[:5]
                if (radius <= 0 or radius != other or rotation != 0
                        or large not in (0, 1) or sweep not in (0, 1)):
                    raise ValueError("Expected a circular arc with valid flags")
                chord2 = sum((a-b)**2 for a, b in zip(current, end))
                if chord2 == 0 or chord2 > 4*radius*radius:
                    raise ValueError("Actual arc endpoints do not define the stated circle")
                angle = 2*_asin(chord2.sqrt()/(2*radius))
                if large:
                    angle = 2*PI-angle
                total += (1 if sweep else -1)*radius*radius*_segment(angle)/2
            current = None if op == "Z" else end
        if current is not None or not tokens:
            raise ValueError("Material SVG path must be nonempty and closed")
        return +total
