"""Whole-interval, source-local coalescing of already bounded binary L/C.

For each fine interval, restrict the actual candidate cubic by exact rational
de Casteljau. The difference Bernstein controls bound the SAME-u distance.
The integral of its derivative norm is bounded by the sum of successive
difference-control distances. Sum these LENGTH bounds globally, not per node.
This proves neither topology nor area nor external-editor serialization.
"""

from __future__ import annotations

import copy
import math
from fractions import Fraction

from .curves import _sqrt_bounds


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("Křivka potřebuje konečnou číselnou hodnotu.")
    if not math.isfinite(value):
        raise ValueError("Křivka potřebuje konečnou číselnou hodnotu.")
    return Fraction(value)


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Kubická hranice potřebuje rovinné body.")
    return tuple(_number(x) for x in value)


def _upper(value):
    return 0.0 if value == 0 else math.nextafter(float(value), math.inf)


def _norm(value):
    return Fraction(_sqrt_bounds(sum(x*x for x in value))[1])


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _mix(a, b, t):
    return tuple((1-t)*x+t*y for x, y in zip(a, b))


def _split(controls, t):
    rows = [tuple(controls)]
    for _ in range(3):
        rows.append(tuple(_mix(a, b, t) for a, b in zip(rows[-1], rows[-1][1:])))
    return tuple(row[0] for row in rows), tuple(row[-1] for row in reversed(rows))


def restrict_cubic(controls, start, end):
    """Exact rational restriction, with the original nonuniform u preserved."""
    controls = tuple(_point(p) for p in controls)
    a, b = _number(start), _number(end)
    if len(controls) != 4 or not 0 <= a < b <= 1:
        raise ValueError("Neplatný interval kubické hranice.")
    if b != 1:
        controls = _split(controls, b)[0]
    return controls if a == 0 else _split(controls, a/b)[1]


def _controls(segment):
    points = (segment["start"], segment["end"]) if segment["kind"] == "line" else (
        segment["start"], segment["data"]["control1"],
        segment["data"]["control2"], segment["end"])
    controls = tuple(_point(p) for p in points)
    if any(Fraction(float(x)) != x for p in controls for x in p):
        raise ValueError("Původní binární konce a řídicí body musí zůstat přesně zachované.")
    return controls


def _identity(source):
    for key in ("profile_id", "segment_id"):
        if not isinstance(source.get(key), str) or not source[key]:
            raise ValueError("Chybí identita zdrojového segmentu.")
    return tuple(source.get(k) for k in ("feature_id", "patch_id", "profile_id", "segment_id"))


def reverse_segment(segment):
    """Reverse geometry AND every retained fine source interval, detached."""
    result = copy.deepcopy(segment)
    result["start"], result["end"] = result["end"], result["start"]
    if result["kind"] == "cubic":
        data = result["data"]
        data["control1"], data["control2"] = data["control2"], data["control1"]
    source = result.get("source")
    if source is not None:
        for record in [source, *source.get("subintervals", [])]:
            for key in ("parameter_interval", "loft_parameter_interval", "v_interval"):
                if key in record:
                    record[key].reverse()
            if "direction" in record:
                record["direction"] *= -1
        if "subintervals" in source:
            source["subintervals"].reverse()
    return result


class _WorkLimitError(Exception):
    pass


def _candidate(records, lo, hi, position_budget, length_budget, work):
    work["candidates"] += 1
    if work["candidates"] > work["max_candidates"]:
        raise _WorkLimitError
    first, last = records[lo], records[hi-1]
    a, b = first[1][0], last[1][1]
    h = b-a
    start, end = first[0][0], last[0][-1]
    controls = (start, end)
    if len(first[0]) == 4:
        d0 = tuple(3*x/(first[1][1]-a) for x in _sub(first[0][1], start))
        d1 = tuple(3*x/(b-last[1][0]) for x in _sub(end, last[0][2]))
        # Quantize once, then prove these binary controls, not ideal handles.
        controls = (start, tuple(Fraction(float(x+h*d/3)) for x, d in zip(start, d0)),
                    tuple(Fraction(float(x-h*d/3)) for x, d in zip(end, d1)), end)
    max_position, length = Fraction(0), Fraction(0)
    for fine, (u, v) in records[lo:hi]:
        work["comparisons"] += 1
        if work["comparisons"] > work["max_comparisons"]:
            raise _WorkLimitError
        restricted = (restrict_cubic(controls, (u-a)/h, (v-a)/h) if len(controls) == 4 else
                      (_mix(start, end, (u-a)/h), _mix(start, end, (v-a)/h)))
        differences = tuple(_sub(x, y) for x, y in zip(restricted, fine))
        # Squared rational comparison rejects distant candidates before sqrt.
        if any(sum(x*x for x in d) > position_budget**2 for d in differences):
            return None
        max_position = max(max_position, *(_norm(d) for d in differences))
        length += sum((_norm(_sub(y, x)) for x, y in zip(differences, differences[1:])),
                      Fraction(0))
        if length > length_budget or max_position > position_budget:
            return None
    return controls, max_position, length


def _boundary(boundary, position_budget, length_budget, count, work):
    segments = boundary["segments"]
    output, position, length = [], Fraction(0), Fraction(0)
    start = 0
    while start < len(segments):
        segment = segments[start]
        if segment["kind"] not in ("cubic", "line"):
            raise ValueError("Slučování podporuje pouze nativní L nebo C.")
        identity = _identity(segment["source"])
        end = start+1
        while end < len(segments) and segments[end]["kind"] == segment["kind"]:
            before, after = segments[end-1], segments[end]
            if _identity(after["source"]) != identity:
                break
            if (before["end"] != after["start"] or
                    before["source"]["loft_parameter_interval"][1] !=
                    after["source"]["loft_parameter_interval"][0] or
                    before["source"]["parameter_interval"][1] !=
                    after["source"]["parameter_interval"][0]):
                raise ValueError("Zdrojové intervaly kubické hranice na sebe nenavazují.")
            end += 1
        chain = segments[start:end]
        records = []
        for s in chain:
            interval = tuple(_number(t) for t in s["source"]["loft_parameter_interval"])
            if len(interval) != 2 or not 0 <= interval[0] < interval[1] <= 1:
                raise ValueError("Loftové intervaly musí striktně růst v rozsahu 0 až 1.")
            original = tuple(_number(t) for t in s["source"]["parameter_interval"])
            if (len(original) != 2 or not all(0 <= t <= 1 for t in original) or
                    original[0] == original[1] or
                    type(s["source"]["direction"]) is not int or
                    s["source"]["direction"] != (1 if original[1] > original[0] else -1)):
                raise ValueError("Neplatný orientovaný zdrojový interval.")
            records.append((_controls(s), interval))
        stack = [(0, len(chain))]
        while stack:
            lo, hi = stack.pop()
            proof = None if hi-lo == 1 else _candidate(
                records, lo, hi, position_budget, length_budget*Fraction(hi-lo, count), work)
            if proof is None and hi-lo > 1:
                middle = (lo+hi)//2
                stack.extend([(middle, hi), (lo, middle)])
                continue
            if proof is None:
                output.append(copy.deepcopy(chain[lo]))
                continue
            controls, error, length_error = proof
            source = copy.deepcopy(chain[lo]["source"])
            source["parameter_interval"][1] = chain[hi-1]["source"]["parameter_interval"][1]
            source["loft_parameter_interval"][1] = (
                chain[hi-1]["source"]["loft_parameter_interval"][1])
            source["subintervals"] = [copy.deepcopy(s["source"]) for s in chain[lo:hi]]
            output.append({
                "kind": segment["kind"], "start": list(map(float, controls[0])),
                "end": list(map(float, controls[-1])),
                "data": ({"control1": list(map(float, controls[1])),
                          "control2": list(map(float, controls[2]))} if len(controls) == 4 else {}),
                "source": source,
                "coalescing": {"status": "CERTIFIED_SAME_U_AND_GLOBAL_LENGTH",
                               "scope": "ACTUAL_COARSE_VS_ORIGINAL_FINE_SAME_U; NOT_SOURCE_ONLY",
                               "fine_segments": hi-lo,
                               "position_bound_exact": str(error),
                               "length_bound_exact": str(length_error)},
            })
            position, length = max(position, error), length+length_error
        start = end
    return output, position, length


def coalesce_native_loft_boundaries(native, *, position_budget_mm=0.008,
                                    length_budget_mm=0.008,
                                    merge_position_budget_mm=1e-5,
                                    merge_length_budget_mm=1e-4,
                                    max_segments=65536, max_candidates=65536,
                                    max_comparisons=262144):
    """Detach a proved fit, preserving every fine provenance interval.

    Work exhaustion returns the ORIGINAL proved representation with an explicit
    NOT_APPLIED status, never a partially checked curve or partial certificate.
    The caller must still prove actual resulting topology and intrinsic area.
    """
    from .loft_curves import _commands, _native_derivative

    limits = (max_segments, max_candidates, max_comparisons)
    if any(type(x) is not int or x < 1 for x in limits):
        raise ValueError("Rozpočty práce musejí být kladná celá čísla.")
    if native.get("status") != "CERTIFIED_REPRESENTATION_ONLY":
        raise ValueError("Slučování vyžaduje již doložené nativní hranice.")
    count = sum(len(p[s]["segments"]) for p in native["patches"] for s in ("first", "second"))
    if count == 0 or count > max_segments:
        raise ValueError("Slučování překročilo vstupní rozpočet segmentů.")
    position_budget, length_budget = _number(position_budget_mm), _number(length_budget_mm)
    position_before = _number(native["position_error_bound_paper_mm"])
    length_before = _number(native["boundary_length_error_bound_paper_mm"])
    if min(position_budget, length_budget) <= 0 or min(position_before, length_before) < 0:
        raise ValueError("Původní meze musí být nezáporné a zadané rozpočty kladné.")
    position_left, length_left = position_budget-position_before, length_budget-length_before
    position_limit = _number(merge_position_budget_mm)
    length_limit = _number(merge_length_budget_mm)
    if min(position_limit, length_limit) <= 0:
        raise ValueError("Chybový rozpočet slučování musí být kladný.")
    if "coalescing" in native:
        # A certificate is relative to the original fine representation. Do not
        # recursively compact it while silently nesting/spending its budget.
        if min(position_left, length_left) < 0:
            raise ValueError("Opakované slučování nesmí přijmout slabší certifikát.")
        return copy.deepcopy(native)
    result = copy.deepcopy(native)
    if min(position_left, length_left) <= 0:
        result["coalescing"] = {"status": "NOT_APPLIED_NO_REMAINING_ERROR_BUDGET"}
        return result
    position_limit = min(position_left, position_limit)
    length_limit = min(length_left, length_limit)
    counts = {s: sum(len(p[s]["segments"]) for p in native["patches"])
              for s in ("first", "second")}
    work = {"candidates": 0, "comparisons": 0, "max_candidates": max_candidates,
            "max_comparisons": max_comparisons}
    error, lengths = Fraction(0), {"first": Fraction(0), "second": Fraction(0)}
    try:
        for patch in result["patches"]:
            for side in ("first", "second"):
                boundary = patch[side]
                segments, position, length = _boundary(
                    boundary, position_limit, length_limit, max(1, counts[side]), work)
                boundary["segments"] = segments
                if any("coalescing" in s for s in segments):
                    boundary["representation"] = (
                        "NATIVE_BOUNDED_COALESCED_LINES" if
                        all(s["kind"] == "line" for s in segments) else
                        "NATIVE_BOUNDED_COALESCED_HERMITE_CUBICS")
                    boundary["ideal_continuity"] = (
                        "SAME_U_BOUNDED_LINEAR_CHORD_NOT_C1_CLAIM" if
                        all(s["kind"] == "line" for s in segments) else
                        "END_DERIVATIVES_FROM_PROVED_FINE_BOUNDARY")
                boundary["coalescing"] = {"position_bound_exact": str(position),
                                           "length_bound_exact": str(length)}
                jumps = [_norm(_sub(_native_derivative(a, True), _native_derivative(b, False)))
                         for a, b in zip(segments, segments[1:])]
                boundary["binary_control_derivative_jump_bound_paper_mm_per_u"] = _upper(
                    max(jumps, default=0))
                boundary["exact_c1_of_binary_controls"] = all(j == 0 for j in jumps)
                boundary["line_interpolant_deviation_bound_paper_mm"] = _upper(
                    _number(boundary["line_interpolant_deviation_bound_paper_mm"])+position)
                boundary["length_excess_bound_paper_mm"] = _upper(
                    _number(boundary["length_excess_bound_paper_mm"])+length)
                error, lengths[side] = max(error, position), lengths[side]+length
            # Retain the exact explicit closing rulings; rebuild only the two
            # profile chains. Their nested source intervals reverse together.
            old = patch["closed_boundary_segments"]
            rulings = [s for s in old if s.get("source", {}).get("kind") ==
                       "EXPLICIT_MATCHED_RULING"]
            if len(rulings) != 2:
                raise ValueError("Chybí oba explicitní uzavírací generátory.")
            loop = [*copy.deepcopy(patch["first"]["segments"]), copy.deepcopy(rulings[0]),
                    *[reverse_segment(s) for s in reversed(patch["second"]["segments"])],
                    copy.deepcopy(rulings[1])]
            patch["closed_boundary_segments"] = loop
            patch["closed_boundary_commands"] = _commands(loop)
    except _WorkLimitError:
        result = copy.deepcopy(native)
        result["coalescing"] = {"status": "NOT_APPLIED_WORK_BUDGET_EXHAUSTED", **work}
        return result
    position = _number(native["position_error_bound_paper_mm"])+error
    length = _number(native["boundary_length_error_bound_paper_mm"])+max(lengths.values())
    result.update(
        position_error_bound_paper_mm=_upper(position),
        boundary_length_error_bound_paper_mm=_upper(length),
        both_profile_boundaries_length_error_bound_paper_mm=_upper(
            _number(native["both_profile_boundaries_length_error_bound_paper_mm"])+sum(lengths.values())),
        line_interpolant_deviation_bound_paper_mm=_upper(
            _number(native["line_interpolant_deviation_bound_paper_mm"])+error),
        native_boundary_length_excess_bound_paper_mm={s: _upper(
            _number(native["native_boundary_length_excess_bound_paper_mm"][s])+lengths[s])
            for s in ("first", "second")},
        same_parameter_position_proof="SOURCE_TO_FINE_BOUND_PLUS_EXACT_RESTRICTION_BERNSTEIN_BOUND",
        length_proof="SOURCE_TO_FINE_BOUND_PLUS_GLOBAL_SUM_INTEGRAL_DERIVATIVE_DIFFERENCE_NORM",
        coalescing={"status": "CERTIFIED_SAME_U_AND_GLOBAL_LENGTH", **work,
                    "position_bound_exact": str(error), "position_bound_paper_mm": _upper(error),
                    "length_bound_exact": {s: str(lengths[s]) for s in lengths},
                    "length_bound_paper_mm": {s: _upper(lengths[s]) for s in lengths},
                    "input_segments": count,
                    "output_segments": sum(len(p[s]["segments"]) for p in result["patches"]
                                           for s in ("first", "second")),
                    "topology_area_editor": "CALLER_MUST_VERIFY_SEPARATELY"},
    )
    # Outward published summaries themselves must stay inside the budget.
    if (_number(result["position_error_bound_paper_mm"]) > _number(position_budget_mm) or
            _number(result["boundary_length_error_bound_paper_mm"]) > _number(length_budget_mm)):
        result = copy.deepcopy(native)
        result["coalescing"] = {"status": "NOT_APPLIED_NO_REMAINING_ERROR_BUDGET", **work}
    return result
