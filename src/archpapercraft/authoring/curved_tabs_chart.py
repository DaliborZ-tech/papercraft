"""Whole-material fan chart for the ACTUAL endpoint-native circular base.

Reference and actual bases use the same rational quadratic parameter, not equal
sample indices. Positive rational weights bound B and B' on the entire base.
F(lambda,t)=Q+lambda*(B(t)-Q) extends the matched base to the actual straight
sides/apex. In Dchi-A the lambda factors cancel; the apex is a continuous
one-sided Lipschitz limit. No position-only claim is used as a derivative bound.
"""

import hashlib
import json
from fractions import Fraction

from .curve_topology import _endpoint_arc_node, _UnresolvedError
from .curved_tabs import _geometry, _q, _sqrt
from .curved_tabs_transfer import CHART_KIND, _identity, _metric


def _iv(value):
    return value, value


def _sub(a, b):
    return a[0] - b[1], a[1] - b[0]


def _norm_bound(vector):
    return _sqrt(sum(max(abs(lo), abs(hi)) ** 2 for lo, hi in vector))[1]


def _point(value):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError("A native chart point needs two exact finite coordinates")
    return tuple(_q(item) for item in value)


def _prime(controls):
    return tuple(
        tuple((2 * (b[0] - a[1]), 2 * (b[1] - a[0])) for a, b in zip(first, second))
        for first, second in zip(controls, controls[1:])
    )


def _native_base(commands, is_arc, expected_sweep):
    if not isinstance(commands, (tuple, list)) or len(commands) != 2:
        raise ValueError("One actual shared native base M+A/L is required")
    move, draw = commands
    if len(move) != 3 or move[0] != "M":
        raise ValueError("The native base must start with M")
    start = _point(move[1:])
    if not is_arc:
        if len(draw) != 3 or draw[0] != "L":
            raise ValueError("A native cylinder base must remain a true line")
        end = _point(draw[1:])
        if start == end:
            raise ValueError("A native base cannot collapse")
        return tuple(
            tuple(_iv(item) for item in (*point, Fraction(1)))
            for point in (start, tuple((a + b) / 2 for a, b in zip(start, end)), end)
        )
    if (
        len(draw) != 8
        or draw[0] != "A"
        or _q(draw[1]) != _q(draw[2])
        or draw[4] != 0
        or draw[5] != expected_sweep
    ):
        raise ValueError("A matching oriented minor native CIRCLE A is required")
    _q(draw[3])  # Rotation has no geometric effect on a circular SVG A.
    end = _point(draw[6:])
    return _endpoint_arc_node(None, start, end, _q(draw[1]), draw[5]).homogeneous


def certify_native_tab_chart(
    rim,
    tab,
    actual_base_commands,
    actual_apex,
    chart_matrix,
    chart_translation,
    *,
    source_ids,
    source_digest,
):
    """Certify a bijective chart to the supplied ACTUAL native arc/straight sides.

    chart_matrix/translation is the reference local-tab -> actual-paper affine
    frame, including reflection. This function proves its whole-domain derivative
    remainder, instead of assuming the actual endpoint SVG arc is that affine
    circle. The domain MUST verify that these are precisely the material-union
    base and actual cut-side apex; this function cannot inspect a project scene.
    """
    result = {
        "status": "UNRESOLVED",
        "method": "POSITIVE_RATIONAL_QUADRATIC_APEX_FAN",
        "tab_id": tab.tab_id,
        "problems": [],
        "native_chart_kind": CHART_KIND,
        "coverage": "ENTIRE_NATIVE_BASE_COLLAR_AND_RIGID_TRIANGLE",
        "caller_condition": "ACTUAL_SHARED_BODY_BASE_AND_CUT_SIDES_MATCH_SUPPLIED_COMMANDS",
    }
    try:
        ids = tuple(source_ids)
        _identity(ids, source_digest)
        matrix = tuple(tuple(_q(item) for item in row) for row in chart_matrix)
        amin, amax, _ = _metric(matrix, 2, 0)
        if amin <= 0:
            raise ValueError("Reference chart linear operator is not proved regular")
        translation, apex = _point(chart_translation), _point(actual_apex)
        determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        g = _geometry(rim, tab)
        k, r, x, y = g["slope"], g["radius"], g["xe"], g["fe"]
        if k:
            q = k * _q(tab.nominal_base_mm) / (4 * r)
            weight = (1 - q * q) / (1 + q * q)
            middle = (Fraction(0), weight * y + x * x / (r / k), weight)
        else:
            middle = (Fraction(0), Fraction(0), Fraction(1))
        native = ((-x, y, Fraction(1)), middle, (x, y, Fraction(1)))
        reference = tuple(
            tuple(
                _iv(
                    sum(matrix[axis][j] * point[j] for j in range(2)) + translation[axis] * point[2]
                )
                for axis in range(2)
            )
            + (_iv(point[2]),)
            for point in native
        )
        expected_sweep = int(k < 0) if determinant > 0 else int(k >= 0)
        actual = _native_base(actual_base_commands, bool(k), expected_sweep)
        wref = min(point[2][0] for point in reference)
        wact = min(point[2][0] for point in actual)
        if min(wref, wact) <= 0:
            raise ValueError("Native rational quadratic weight is not strictly positive")
        delta = tuple(
            tuple(_sub(a, b) for a, b in zip(first, second))
            for first, second in zip(actual, reference)
        )
        dn = max(_norm_bound(point[:2]) for point in delta)
        dw = max(max(abs(a), abs(b)) for _, _, (a, b) in delta)
        bref = max(_norm_bound(point[:2]) for point in reference) / wref
        db = (dn + bref * dw) / wact
        ref_prime, act_prime, del_prime = _prime(reference), _prime(actual), _prime(delta)
        ref_nprime = max(_norm_bound(point[:2]) for point in ref_prime)
        ref_wprime = max(max(abs(a), abs(b)) for _, _, (a, b) in ref_prime)
        act_wprime = max(max(abs(a), abs(b)) for _, _, (a, b) in act_prime)
        delta_nprime = max(_norm_bound(point[:2]) for point in del_prime)
        delta_wprime = max(max(abs(a), abs(b)) for _, _, (a, b) in del_prime)
        bref_prime = (ref_nprime + bref * ref_wprime) / wref
        dbprime = (delta_nprime + db * act_wprime + bref * delta_wprime + dw * bref_prime) / wact
        qnative = g["offset"], g["depth"]
        qreference = tuple(
            sum(matrix[i][j] * qnative[j] for j in range(2)) + translation[i] for i in range(2)
        )
        dq = _norm_bound(tuple(_iv(a - b) for a, b in zip(apex, qreference)))
        # Reference B'(t) is the rational quadratic derivative (not an angular
        # speed). x'(t) >= 2*xe*wref_native because its homogeneous x numerator
        # is linear and |x|<=xe; direct differentiation gives an even tighter
        # positive numerator >=2*xe*wref_native, with denominator <=1.
        native_weight = min(point[2] for point in native)
        dxdt = 2 * x * native_weight
        a = g["half_angle"][1]
        c = 1 - (k * a) ** 2 / 2
        f = r * abs(k) * a * a / 2
        fp = abs(k) * a / c
        det_native = dxdt * (g["depth"] - f - (x + abs(g["offset"])) * fp)
        norm_first = _sqrt((x + abs(g["offset"])) ** 2 + (g["depth"] + f) ** 2)[1]
        # Rational derivative bound in native coordinates, independent of angle
        # parametrization. This upper hull is used only in the inverse estimate.
        h_native = tuple(tuple(_iv(item) for item in point) for point in native)
        nprime = max(_norm_bound(point[:2]) for point in _prime(h_native))
        wprime = max(max(abs(a), abs(b)) for _, _, (a, b) in _prime(h_native))
        bnorm = max(_norm_bound(point[:2]) for point in h_native) / native_weight
        norm_second = (nprime + bnorm * wprime) / native_weight
        if det_native <= 0:
            raise ValueError("Reference whole fan Jacobian lower bound is not positive")
        inverse = _sqrt(norm_first * norm_first + norm_second * norm_second)[1] / det_native
        derivative = _sqrt((db + dq) ** 2 + dbprime * dbprime)[1] * inverse
        actual_det = (
            abs(determinant) * det_native
            - amax * norm_first * dbprime
            - amax * norm_second * (db + dq)
            - (db + dq) * dbprime
        )
        halfplane = g["depth"] - f - (db + dq) / amin
        result.update(
            {
                "base_position_error_bound_mm": db,
                "base_derivative_error_bound_mm": dbprime,
                "apex_position_error_bound_mm": dq,
                "paper_chart_derivative_remainder": derivative,
                "native_chart_position_error_mm": max(db, dq),
                "reference_fan_jacobian_lower": det_native,
                "actual_fan_jacobian_lower": actual_det,
                "actual_fan_halfplane_margin_mm": halfplane,
                "paper_chart_matrix": matrix,
                "paper_chart_translation": translation,
                "source_ids": ids,
                "source_digest": source_digest,
            }
        )
        if actual_det <= 0 or halfplane <= 0 or derivative >= amin:
            raise ValueError("Actual whole fan bijection/regularity is not proved")
        canonical = {
            "rim_id": rim.rim_id,
            "tab_id": tab.tab_id,
            "native_r": str(r),
            "native_k": str(k),
            "reference_homogeneous": [[str(v) for v in p] for p in native],
            "actual_base": [
                [command[0], *(str(_q(v)) for v in command[1:])] for command in actual_base_commands
            ],
            "actual_apex": list(map(str, apex)),
            "matrix": [[str(v) for v in row] for row in matrix],
            "translation": list(map(str, translation)),
            "source_ids": ids,
            "source_digest": source_digest,
        }
        result["native_chart_digest"] = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        result["status"] = "CERTIFIED_NATIVE_CHART"
    except (ValueError, TypeError, OverflowError, _UnresolvedError) as exc:
        result["problems"].append(str(exc))
    return result
