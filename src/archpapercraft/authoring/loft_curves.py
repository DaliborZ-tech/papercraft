"""Bound native L/C representations of already-proved loft developments.

The solver supplies a global SAME-u bound delta from the true development F to
its piecewise-linear parameter interpolant L. For actual binary cubic controls
B and the degree-elevated line controls D, the Bernstein convex-hull inequality
gives |C(u)-L(u)| <= max_i |B_i-D_i| = eta. Thus |F-C| <= delta+eta+reserve
on the whole source interval, without treating sampled agreement as a proof.

Shared quadratic-interpolant derivatives define an ideal C1 curve inside each
source patch. Binary controls are checked afterwards: their derivative jumps
are bounded explicitly, not misrepresented as exact C1 or serialized-output
proof. Source-patch joins are never smoothed. No topology, assembled geometry,
PDF serialization or physical build is certified by this module.
"""

from __future__ import annotations

import copy
import math
from fractions import Fraction

from .curves import _sqrt_bounds

_FAMILIES = {"NORMAL_EXTRUSION", "CONCENTRIC_PLANAR_ARC_BAND", "POSITIVE_HOMOTHETIC_CONE"}


def _number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("Rozvin potřebuje konečné číselné hodnoty.")
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("Chybový rozpočet a délka parametrového intervalu musí být kladné.")
    return Fraction(value)


def _point(value):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError("Bod rozvinuté hranice potřebuje dvě souřadnice.")
    point = tuple(_number(x) for x in value)
    if any(Fraction(float(x)) != x for x in point):
        raise ValueError("Uzel zdrojového rozvinu nelze zachovat v původní číselné přesnosti.")
    return point


def _upper(value):
    if value == 0:
        return 0.0
    return math.nextafter(float(value), math.inf)


def _norm_upper(value):
    return Fraction(_sqrt_bounds(sum(x*x for x in value))[1])


def _subtract(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _distance_bounds(a, b):
    return tuple(Fraction(x) for x in _sqrt_bounds(sum((x-y)**2 for x, y in zip(a, b))))


def _derivatives(parameters, points):
    """Exact derivative of the neighboring quadratic at each shared knot."""
    hs = [b-a for a, b in zip(parameters, parameters[1:])]
    slopes = [tuple((y-x)/h for x, y in zip(a, b))
              for a, b, h in zip(points, points[1:], hs)]
    if len(slopes) == 1:
        return [slopes[0], slopes[0]]
    first = tuple(((2*hs[0]+hs[1])*a-hs[0]*b)/(hs[0]+hs[1])
                  for a, b in zip(slopes[0], slopes[1]))
    last = tuple(((2*hs[-1]+hs[-2])*b-hs[-1]*a)/(hs[-1]+hs[-2])
                 for a, b in zip(slopes[-2], slopes[-1]))
    middle = [tuple((right*a+left*b)/(left+right) for a, b in zip(before, after))
              for left, right, before, after in zip(hs, hs[1:], slopes, slopes[1:])]
    return [first, *middle, last]


def _straight(points):
    direction = _subtract(points[-1], points[0])
    if direction == (0, 0):
        return False
    return all((p[0]-points[0][0])*direction[1] ==
               (p[1]-points[0][1])*direction[0] for p in points)


def _source(patch, side, index, parameters, feature_id):
    offset = 0 if side == "first" else 1
    a = patch["source_parameters"][index][offset]
    b = patch["source_parameters"][index+1][offset]
    return {
        "feature_id": patch.get("feature_id", feature_id),
        "profile_id": patch[side+"_profile_id"],
        "segment_id": patch[side+"_segment_id"],
        "parameter_interval": [a, b],
        "loft_parameter_interval": [float(parameters[index]), float(parameters[index+1])],
        "direction": 1 if b > a else -1,
    }


def _native_derivative(segment, at_end):
    start, end = _point(segment["start"]), _point(segment["end"])
    a, b = map(Fraction, segment["source"]["loft_parameter_interval"])
    if segment["kind"] == "line":
        return tuple((y-x)/(b-a) for x, y in zip(start, end))
    control = _point(segment["data"]["control2" if at_end else "control1"])
    delta = _subtract(end, control) if at_end else _subtract(control, start)
    return tuple(3*x/(b-a) for x in delta)


def _boundary(patch, side, parameters, points, feature_id):
    straight = _straight(points)
    preserve_lines = straight or patch.get(side+"_source_kind") == "line"
    derivatives = _derivatives(parameters, points)
    segments, max_eta, length_extra = [], Fraction(0), Fraction(0)
    for index, (a, b) in enumerate(zip(points, points[1:])):
        if a == b:
            raise ValueError("Rozvin obsahuje nulovou hranu mezi různými parametry.")
        h = parameters[index+1]-parameters[index]
        # Quantize the ideal Hermite controls once, then prove the ACTUAL
        # returned binary controls. Never clamp a handle independently.
        controls = [a, b]
        data = {}
        kind = "line"
        if not preserve_lines:
            first = tuple(Fraction(float(x+h*d/3)) for x, d in zip(a, derivatives[index]))
            second = tuple(Fraction(float(x-h*d/3)) for x, d in zip(b, derivatives[index+1]))
            controls = [a, first, second, b]
            data = {"control1": list(map(float, first)), "control2": list(map(float, second))}
            kind = "cubic"
            elevated = [a, tuple((2*x+y)/3 for x, y in zip(a, b)),
                        tuple((x+2*y)/3 for x, y in zip(a, b)), b]
            eta = max(_norm_upper(_subtract(x, y)) for x, y in zip(controls, elevated))
            max_eta = max(max_eta, eta)
            polygon_upper = sum((_distance_bounds(x, y)[1]
                                 for x, y in zip(controls, controls[1:])), Fraction(0))
            extra = max(Fraction(0), polygon_upper-_distance_bounds(a, b)[0])
            length_extra += extra
        else:
            eta, extra = Fraction(0), Fraction(0)
        segments.append({
            "kind": kind, "start": list(map(float, a)), "end": list(map(float, b)),
            "data": data, "source": _source(patch, side, index, parameters, feature_id),
            "line_interpolant_deviation_bound_paper_mm": _upper(eta),
            "length_excess_bound_paper_mm": _upper(extra),
        })
    jumps = [_norm_upper(_subtract(_native_derivative(before, True),
                                   _native_derivative(after, False)))
             for before, after in zip(segments, segments[1:])]
    return {
        "segments": segments,
        "representation": "NATIVE_LINES" if preserve_lines else "NATIVE_HERMITE_CUBICS",
        "ideal_continuity": ("STRAIGHT_LOCUS_PARAMETER_SPEED_MAY_JUMP" if straight else
                             "SOURCE_STRAIGHT_BOUNDARY_RETAINS_LINEAR_INTERPOLANT" if preserve_lines
                             else "C1_SHARED_QUADRATIC_DERIVATIVE_WITHIN_SOURCE_PATCH"),
        "binary_control_derivative_jump_bound_paper_mm_per_u": _upper(max(jumps, default=0)),
        "exact_c1_of_binary_controls": all(jump == 0 for jump in jumps),
        "line_interpolant_deviation_bound_paper_mm": _upper(max_eta),
        "length_excess_bound_paper_mm": _upper(length_extra),
    }, max_eta, length_extra


def _reverse(segment):
    result = copy.deepcopy(segment)
    result["start"], result["end"] = result["end"], result["start"]
    if result["kind"] == "cubic":
        data = result["data"]
        data["control1"], data["control2"] = data["control2"], data["control1"]
    source = result["source"]
    for key in ("parameter_interval", "loft_parameter_interval"):
        source[key].reverse()
    source["direction"] *= -1
    return result


def _ruling(start, end, patch, u, feature_id, *, reverse=False):
    endpoint = -1 if u else 0
    return {"kind": "line", "start": list(start), "end": list(end), "data": {},
            "source": {"kind": "EXPLICIT_MATCHED_RULING", "u": u,
                       "feature_id": patch.get("feature_id", feature_id),
                       "v_interval": [1, 0] if reverse else [0, 1],
                       "first_profile_id": patch["first_profile_id"],
                       "second_profile_id": patch["second_profile_id"],
                       "first_segment_id": patch["first_segment_id"],
                       "second_segment_id": patch["second_segment_id"],
                       "first_source_parameter": patch["source_parameters"][endpoint][0],
                       "second_source_parameter": patch["source_parameters"][endpoint][1]}}


def _commands(segments):
    commands = [["M", *segments[0]["start"]]]
    # The final explicit ruling is represented by Z, retaining its provenance
    # in closed_boundary_segments without adding a duplicate zero closing edge.
    for segment in segments[:-1]:
        if segment["kind"] == "line":
            commands.append(["L", *segment["end"]])
        else:
            commands.append(["C", *segment["data"]["control1"],
                             *segment["data"]["control2"], *segment["end"]])
    return [*commands, ["Z"]]


def _validate_patch(patch):
    for side in ("first", "second"):
        if not patch[side+"_segment_id"] or not isinstance(patch[side+"_profile_id"], str):
            raise ValueError("Chybí původní identita zdrojového profilu a segmentu.")
    parameters = [_number(x) for x in patch["parameters"]]
    if any(Fraction(float(t)) != t for t in parameters):
        raise ValueError("Parametr původního rozvinu nelze zachovat v číselné přesnosti.")
    if len(parameters) < 2 or parameters[0] != 0 or parameters[-1] != 1:
        raise ValueError("Rozvin potřebuje úplný explicitní interval parametru 0 až 1.")
    if any(b <= a for a, b in zip(parameters, parameters[1:])):
        raise ValueError("Parametry rozvinu musí striktně růst.")
    source = patch["source_parameters"]
    if len(source) != len(parameters) or any(len(row) != 2 for row in source):
        raise ValueError("Každý uzel potřebuje obě původní zdrojové souřadnice.")
    for column, side in enumerate(("first", "second")):
        interval = patch[side+"_parameter_interval"]
        if list(interval) not in ([0, 1], [1, 0]):
            raise ValueError("Převod podporuje celé orientované zdrojové segmenty.")
        values = [_number(row[column]) for row in source]
        if [values[0], values[-1]] != list(interval) or any(not 0 <= x <= 1 for x in values):
            raise ValueError("Zdrojové parametry neodpovídají orientovanému intervalu.")
        sign = interval[1]-interval[0]
        if any((b-a)*sign <= 0 for a, b in zip(values, values[1:])):
            raise ValueError("Zdrojové parametry změnily směr uvnitř intervalu.")
        if any(value != Fraction(float(interval[0]+t*sign))
               for value, t in zip(values, parameters)):
            raise ValueError("Zdrojová provenance neodpovídá stejnému parametru rozvinu.")
    first = [_point(p) for p in patch["flat_first_paper_mm"]]
    second = [_point(p) for p in patch["flat_second_paper_mm"]]
    if len(first) != len(parameters) or len(second) != len(parameters):
        raise ValueError("Každý parametr potřebuje oba rozvinuté body.")
    return parameters, first, second


def fit_native_loft_boundaries(report, *, position_budget_mm=0.008, length_budget_mm=0.008,
                               rounding_reserve_mm=1e-10, max_segments=65536):
    """Detach a bounded native representation of an EXACT loft solver report.

    Length bounds cover profile-derived boundary chains across ALL patches;
    explicit closing rulings need their own source/end-point proof from the
    caller. An unresolved fit must be refined by rerunning the source solver,
    not by independently clamping controls or silently spending another budget.
    """
    result = {"status": "UNRESOLVED", "proof_scope": "REPRESENTATION_ONLY",
              "topology": "CALLER_VALIDATES_NATIVE_LOOPS_AND_ASSEMBLED_INTERSECTIONS",
              "physical_build": "NOT_VERIFIED", "serialized_output": "NOT_VERIFIED"}
    try:
        position_budget = _number(position_budget_mm, positive=True)
        length_budget = _number(length_budget_mm, positive=True)
        reserve = _number(rounding_reserve_mm)
        if reserve < 0 or type(max_segments) is not int or max_segments < 1:
            raise ValueError("Rezerva musí být nezáporná a rozpočet segmentů kladný.")
        if (report["status"] != "EXACT" or report["family"] not in _FAMILIES or
                report.get("proof_scope") !=
                "DECLARED_REGULAR_PARAMETRIC_FAMILY_AND_BOUNDED_REPRESENTATION"):
            raise ValueError("Nejprve je nutný doložený přesný rozvin podporované rodiny.")
        delta = _number(report["representation_error_bound_paper_mm"])
        source_length = _number(report["boundary_length_error_bound_paper_mm"])
        if min(delta, source_length) < 0:
            raise ValueError("Zdrojové chybové meze nesmějí být záporné.")
        _number(report["regularity_lower_bound_paper_mm2"], positive=True)
        patches, eta, extras = [], Fraction(0), [Fraction(0), Fraction(0)]
        count = 0
        if not report["patches"]:
            raise ValueError("Přesný rozvin neobsahuje žádné zdrojové intervaly.")
        for patch_index, patch in enumerate(report["patches"]):
            parameters, first, second = _validate_patch(patch)
            count += 2*(len(parameters)-1)
            if count > max_segments:
                raise ValueError("Nativní hranice překročily rozpočet segmentů.")
            native_a, eta_a, extra_a = _boundary(
                patch, "first", parameters, first, report.get("feature_id"))
            native_b, eta_b, extra_b = _boundary(
                patch, "second", parameters, second, report.get("feature_id"))
            eta = max(eta, eta_a, eta_b)
            extras[0] += extra_a
            extras[1] += extra_b
            a, b = native_a["segments"], native_b["segments"]
            loop = [*copy.deepcopy(a), _ruling(a[-1]["end"], b[-1]["end"], patch, 1,
                                              report.get("feature_id")),
                    *[_reverse(segment) for segment in reversed(b)],
                    _ruling(b[0]["start"], a[0]["start"], patch, 0,
                            report.get("feature_id"), reverse=True)]
            patches.append({
                "patch_index": patch_index,
                "join_before_kind": patch.get("join_before_kind", "NOT_SPECIFIED"),
                "source_patch_boundary_policy": "NO_CROSS_PATCH_SMOOTHING",
                "first": native_a, "second": native_b,
                "closed_boundary_segments": loop, "closed_boundary_commands": _commands(loop),
                "closed_boundary_topology": "NOT_VERIFIED",
                "closing_ruling_length_proof": "CALLER_VALIDATES_INDEPENDENTLY",
            })
        position = delta+eta+reserve
        length = source_length+max(extras)+reserve
        result.update(
            source_family=report["family"], patches=patches,
            source_coverage=copy.deepcopy(report.get("coverage", {})),
            position_error_bound_paper_mm=_upper(position),
            boundary_length_error_bound_paper_mm=_upper(length),
            source_position_error_bound_paper_mm=float(delta),
            line_interpolant_deviation_bound_paper_mm=_upper(eta),
            source_boundary_length_error_bound_paper_mm=float(source_length),
            native_boundary_length_excess_bound_paper_mm={
                "first": _upper(extras[0]), "second": _upper(extras[1])},
            both_profile_boundaries_length_error_bound_paper_mm=_upper(
                2*source_length+sum(extras)+2*reserve),
            length_scope="GLOBAL_FIRST_OR_SECOND_PROFILE_BOUNDARY_CHAIN; EXCLUDES_CLOSING_RULINGS",
            rounding_reserve_paper_mm=float(reserve),
            requested_position_budget_paper_mm=float(position_budget),
            requested_length_budget_paper_mm=float(length_budget),
            same_parameter_position_proof="SOURCE_F_TO_LINE_DELTA_PLUS_BERNSTEIN_CONTROL_ETA",
            length_proof="SOURCE_CHAIN_DEFICIT_PLUS_SUM_ACTUAL_CUBIC_CONTROL_POLYGON_MINUS_CHORD",
            serialization_scope="BINARY_CONTROL_GEOMETRY_ONLY; PUBLISHER_BUDGET_IS_SEPARATE",
        )
        if (_number(result["position_error_bound_paper_mm"]) > position_budget or
                _number(result["boundary_length_error_bound_paper_mm"]) > length_budget):
            result.update(message="Nativní křivky překročily polohovou nebo délkovou mez. "
                          "Zjemněte původní rozvin a opakujte převod.",
                          next_action="REFINE_SOURCE_SOLVER_AND_REFIT_WITHOUT_HANDLE_CLAMPING")
            return result
        result["status"] = "CERTIFIED_REPRESENTATION_ONLY"
        return result
    except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
        result["message"] = str(exc)
        return result
