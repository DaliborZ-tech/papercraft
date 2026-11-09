"""Area enclosures for the supplied native paper-mm paths, never sampled paths.

The caller must already have proved one simple outer boundary and strictly
contained, disjoint holes. This module proves neither topology nor physical fit.
L/C Green integrals are rationally exact. Circular SVG endpoint arcs use outward
rational intervals, including SVG's radius correction. Unsupported input raises
ValueError rather than returning an approximate area as an exact certificate.
"""

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from fractions import Fraction
from functools import lru_cache

_GRID = 10**80
_OUTPUT_GRID = 10**24


def _out(interval, grid=_GRID):
    low, high = interval
    return (Fraction(low.numerator * grid // low.denominator, grid),
            Fraction(-((-high.numerator * grid) // high.denominator), grid))


def _add(a, b):
    return _out((a[0] + b[0], a[1] + b[1]))


def _neg(a):
    return -a[1], -a[0]


def _mul(a, b):
    values = [x * y for x in a for y in b]
    return _out((min(values), max(values)))


def _div(a, b):
    if b[0] <= 0 <= b[1]:
        raise ValueError("Native arc precision is insufficient to bound a denominator")
    return _mul(a, (1 / b[1], 1 / b[0]))


def _point(value):
    return value, value


def _sqrt(value):
    if value < 0:
        raise ValueError("Negative native arc square root")
    if not value:
        return _point(Fraction(0))
    # Directed division brackets the exact rational input. Decimal.sqrt is
    # correctly rounded to nearest; one adjacent decimal encloses that rounding.
    with localcontext() as context:
        context.prec = 90
        context.rounding = ROUND_FLOOR
        low = (Decimal(value.numerator) / Decimal(value.denominator)).sqrt().next_minus()
        context.rounding = ROUND_CEILING
        high = (Decimal(value.numerator) / Decimal(value.denominator)).sqrt().next_plus()
        return Fraction(low), Fraction(high)


@lru_cache(maxsize=512)
def _atan(value):
    """Enclose atan of an exact rational in [0,1] by an alternating series."""
    if not 0 <= value <= 1:
        raise ValueError("Native arc atan argument is outside the supported range")
    if value > Fraction(1, 2):
        return _add(_atan(Fraction(1, 2)),
                    _atan((value - Fraction(1, 2)) / (1 + value / 2)))
    power = _point(value)
    square = _point(value * value)
    result = _point(Fraction(0))
    for index in range(256):
        term = _mul(power, _point(Fraction(1, 2 * index + 1)))
        result = _add(result, term if index % 2 == 0 else _neg(term))
        power = _mul(power, square)
        remainder = power[1] / (2 * index + 3)
        if remainder < Fraction(1, 10**65):
            # Alternating-series remainder has the sign of the next term.
            return (result[0] - (remainder if index % 2 == 0 else 0),
                    result[1] + (remainder if index % 2 else 0))
    raise ValueError("Native area atan budget exhausted")


@lru_cache(maxsize=1)
def _pi():
    # Machin's identity; every operation retains an outward interval.
    return _add(_mul(_point(Fraction(16)), _atan(Fraction(1, 5))),
                _mul(_point(Fraction(-4)), _atan(Fraction(1, 239))))


def _scalar(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a native coordinate")
    if isinstance(value, str) and len(value) > 4096:
        raise ValueError("Native coordinate exceeds the arithmetic input budget")
    try:
        result = Fraction(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Native coordinate must be a finite exact number") from exc
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > 16384:
        raise ValueError("Native coordinate exceeds the arithmetic input budget")
    return result


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _cubic(start, control1, control2, end):
    coefficients = []
    for axis in range(2):
        a, b, c, d = (p[axis] for p in (start, control1, control2, end))
        coefficients.append((a, 3 * (b - a), 3 * (a - 2*b + c), d - a + 3*(b-c)))
    x, y = coefficients
    return sum((Fraction(j, 2*(i+j)) * (x[i]*y[j] - y[i]*x[j])
                for i in range(4) for j in range(1, 4)), Fraction(0))


def _arc(start, end, values):
    rx, ry, _rotation, large, sweep, *_ = values
    if rx <= 0 or rx != ry or large not in (0, 1) or sweep not in (0, 1):
        raise ValueError("Native area supports positive circular SVG arcs with binary flags")
    dx, dy = end[0] - start[0], end[1] - start[1]
    chord2 = dx*dx + dy*dy
    if not chord2:
        raise ValueError("Coincident native arc endpoints do not define an area arc")
    radius2 = max(rx*rx, chord2 / 4)  # SVG radius correction, exactly for a circle.
    factor = _sqrt(radius2 / chord2 - Fraction(1, 4))
    if large == sweep:
        factor = _neg(factor)
    cx = _add(_point((start[0]+end[0])/2), _mul(factor, _point(-dy)))
    cy = _add(_point((start[1]+end[1])/2), _mul(factor, _point(dx)))
    if radius2 == chord2 / 4:
        theta = _pi()
    else:
        quotient = _div(_sqrt(chord2), _add(
            _mul(_point(Fraction(2)), _sqrt(radius2)), _sqrt(4*radius2-chord2)))
        # Exact q is in (0,1); interval rounding can straddle 1 infinitesimally.
        quotient = max(Fraction(0), quotient[0]), min(Fraction(1), quotient[1])
        theta = _mul(_point(Fraction(4)), (_atan(quotient[0])[0], _atan(quotient[1])[1]))
        if large:
            theta = _add(_mul(_point(Fraction(2)), _pi()), _neg(theta))
    if not sweep:
        theta = _neg(theta)
    return _mul(_point(Fraction(1, 2)), _add(
        _add(_mul(cx, _point(dy)), _mul(cy, _point(-dx))),
        _mul(_point(radius2), theta)))


def _loop_area(commands):
    current = start = None
    closed = False
    result = _point(Fraction(0))
    for command in commands:
        if not isinstance(command, (tuple, list)) or not command:
            raise ValueError("Native path commands must be nonempty tuples or lists")
        operation, *raw = command
        counts = {"M": 2, "L": 2, "C": 6, "A": 7, "Z": 0}
        if (not isinstance(operation, str) or operation not in counts
                or len(raw) != counts[operation] or closed):
            raise ValueError("Native area needs one absolute M/L/C/A/Z closed loop")
        values = tuple(_scalar(value) for value in raw)
        if operation == "M":
            if start is not None:
                raise ValueError("A native area loop cannot contain multiple M commands")
            current = start = values
            continue
        if current is None:
            raise ValueError("Native area loop must begin with M")
        if operation == "Z":
            closing = _cross(current, start)/2
            result = result[0] + closing, result[1] + closing
            current, closed = start, True
            continue
        end = values[-2:]
        if operation == "L":
            addition = _point(_cross(current, end)/2)
        elif operation == "C":
            addition = _point(_cubic(current, values[:2], values[2:4], end))
        else:
            addition = _arc(current, end, values)
        # Preserve exact polynomial integrals, including very small coordinates.
        result = result[0]+addition[0], result[1]+addition[1]
        current = end
    if not closed:
        raise ValueError("Native area loop is not explicitly closed with Z")
    if result[0] <= 0 <= result[1]:
        raise ValueError("Native loop area is zero or its sign is not established")
    return result if result[0] > 0 else _neg(result)


def native_region_area_bounds(loops, *, max_commands=20000):
    """Return outward Fraction bounds for net area in supplied paper mm².

    Precondition: topology has proved exactly one outer loop plus its holes.
    Winding and order do not matter: the uniquely largest absolute area is the
    outer boundary. Disjoint material regions are NOT supported by this API.
    No coordinate conversion, source-curve reconstruction or sampling occurs.
    """
    if type(max_commands) is not int or max_commands < 1:
        raise ValueError("Native area command budget must be a positive integer")
    areas, count = [], 0
    for loop in loops:
        # Bound consumption even for iterators; never materialize unbounded input.
        commands = []
        for command in loop:
            count += 1
            if count > max_commands:
                raise ValueError("Native area command budget exhausted")
            commands.append(command)
        areas.append(_loop_area(commands))
    if not areas:
        raise ValueError("Native region needs one outer loop")
    outer = max(range(len(areas)), key=lambda index: areas[index][0])
    if any(areas[outer][0] <= area[1] for index, area in enumerate(areas) if index != outer):
        raise ValueError("Native outer area cannot be distinguished from hole areas")
    low, high = areas[outer]
    for index, area in enumerate(areas):
        if index != outer:
            low, high = low - area[1], high - area[0]
    if low <= 0:
        raise ValueError("Native net material area is not proved positive")
    # Keep the public rational representation compact for evidence serialization.
    return _out((low, high), _OUTPUT_GRID)
