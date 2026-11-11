"""Self-contained exact restricted sources; floating profile data is a cache.

No project lookup, runtime closure or serialized factory can change this view.
Its source/generation/interval are explicit, including an authored arc endpoint
which may differ from the nominal analytic limit under the legacy contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction as Q
from types import MappingProxyType

from .curve_area import _add, _arc, _cross, _cubic, _mul, _neg, _pi, _point, _scalar, _sqrt
from .curve_subdivision import (
    CurveSource,
    CurveSubdivisionHistory,
    SourcePointReference,
    TrimReference,
)
from .curves import Curve

SCHEMA = 1
_FIELDS = {
    "schema",
    "profile_id",
    "history_id",
    "piece_id",
    "generation",
    "source",
    "parameter_interval",
}


class SourceViewError(ValueError):
    """A source reference is malformed, poisoned or mathematically unresolved."""


def _identity(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise SourceViewError("Source identities must be qualified nonempty strings.")
    return value


def _parameter(value):
    try:
        value = _scalar(value)
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise SourceViewError("Source parameters require finite valid rational values.") from exc
    if not 0 <= value <= 1:
        raise SourceViewError("Source parameters must lie in [0,1].")
    return value


def _source_bounds(source, t):
    # Exact quarter turns avoid inventing a nonzero gap at authored cardinal
    # points. Arbitrary phases retain the approved outward trig enclosure.
    quarter = source.sweep_deg * t / 90
    if source.kind == "arc" and quarter.denominator == 1:
        x, y = (a - b for a, b in zip(source.start, source.center))
        x, y = [(x, y), (-y, x), (-x, -y), (y, -x)][int(quarter) % 4]
        return tuple(_point(c + v) for c, v in zip(source.center, (x, y)))
    return source.point_bounds(t)


def _mid(bounds):
    return tuple(float((a + b) / 2) for a, b in bounds)


@dataclass(frozen=True, init=False)
class SourceCurveView(Curve):
    root_source: CurveSource
    parameter_interval: tuple
    profile_id: str
    history_id: str
    generation: int

    def __init__(self, source, interval, *, profile_id, history_id, piece_id, generation):
        if not isinstance(source, CurveSource):
            raise SourceViewError("A detached CurveSource is required.")
        if type(generation) is not int or generation < 0 or generation > 1024:
            raise SourceViewError("Invalid geometry generation.")
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            raise SourceViewError("A restricted source needs two parameters.")
        a, b = map(_parameter, interval)
        if a == b:
            raise SourceViewError("A restricted source must have positive extent.")
        for name, value in (
            ("root_source", source),
            ("parameter_interval", (a, b)),
            ("profile_id", _identity(profile_id)),
            ("history_id", _identity(history_id)),
            ("segment_id", _identity(piece_id)),
            ("generation", generation),
            ("kind", source.kind),
        ):
            object.__setattr__(self, name, value)
        if source.kind == "arc":

            def endpoint(t):
                if t in (0, 1):
                    return source.start if t == 0 else source.end
                return _mid(_source_bounds(source, t))

            start, end = endpoint(a), endpoint(b)
            data = {"center": source.center, "sweep_deg": source.sweep_deg * (b - a)}
        else:
            points = source.controls_on(a, b)
            start, end = points[0], points[-1]
            data = {"control1": points[1], "control2": points[2]} if source.kind == "cubic" else {}
        object.__setattr__(self, "start", tuple(start))
        object.__setattr__(self, "end", tuple(end))
        object.__setattr__(self, "data", MappingProxyType(data))

    @classmethod
    def from_reference(cls, reference, *, expected_profile_id=None, expected_piece_id=None):
        if (
            not isinstance(reference, dict)
            or set(reference) != _FIELDS
            or type(reference["schema"]) is not int
            or reference["schema"] != SCHEMA
        ):
            raise SourceViewError("Unknown source-reference schema or fields.")
        source = CurveSource.from_dict(reference["source"])
        if source.to_dict() != reference["source"]:
            raise SourceViewError("The exact source record is not canonical.")
        interval = reference["parameter_interval"]
        if (
            not isinstance(interval, list)
            or len(interval) != 2
            or any(type(v) is not str or str(_parameter(v)) != v for v in interval)
        ):
            raise SourceViewError("Source intervals require canonical exact rational strings.")
        if (expected_profile_id is not None and reference["profile_id"] != expected_profile_id) or (
            expected_piece_id is not None and reference["piece_id"] != expected_piece_id
        ):
            raise SourceViewError("The source belongs to a different profile or piece.")
        return cls(
            source,
            interval,
            profile_id=reference["profile_id"],
            history_id=reference["history_id"],
            piece_id=reference["piece_id"],
            generation=reference["generation"],
        )

    def to_reference(self):
        return {
            "schema": SCHEMA,
            "profile_id": self.profile_id,
            "history_id": self.history_id,
            "piece_id": self.segment_id,
            "generation": self.generation,
            "source": self.root_source.to_dict(),
            "parameter_interval": list(map(str, self.parameter_interval)),
        }

    def restricted(self, a, b, *, segment_id=None):
        a, b = _parameter(a), _parameter(b)
        start, end = self.parameter_interval
        return type(self)(
            self.root_source,
            (start + a * (end - start), start + b * (end - start)),
            profile_id=self.profile_id,
            history_id=self.history_id,
            piece_id=segment_id or self.segment_id,
            generation=self.generation,
        )

    def reversed(self):
        return self.restricted(1, 0)

    def controls_exact(self):
        return self.root_source.controls_on(*self.parameter_interval)

    def point_bounds(self, t):
        a, b = self.parameter_interval
        return _source_bounds(self.root_source, a + _parameter(t) * (b - a))

    def evaluate(self, t):
        t = _parameter(t)
        if t in (0, 1):
            return tuple(float(x) for x in (self.start if t == 0 else self.end))
        return _mid(self.point_bounds(t))

    def derivative_bounds(self, t):
        t = _parameter(t)
        if self.kind != "arc":
            values = self.controls_exact()
            degree = len(values) - 1
            values = tuple(
                tuple(degree * (y - x) for x, y in zip(a, b)) for a, b in zip(values, values[1:])
            )
            while len(values) > 1:
                values = tuple(
                    tuple((1 - t) * x + t * y for x, y in zip(a, b))
                    for a, b in zip(values, values[1:])
                )
            return tuple(_point(x) for x in values[0])
        x, y = (_add(v, _point(-c)) for v, c in zip(self.point_bounds(t), self.root_source.center))
        omega = _mul(_pi(), _point(self.data["sweep_deg"] / 180))
        return _mul(omega, _neg(y)), _mul(omega, x)

    def endpoint_gap_bound(self):
        return max(
            sum(
                max(abs(_scalar(x) - a), abs(_scalar(x) - b))
                for x, (a, b) in zip(p, self.point_bounds(t))
            )
            for t, p in ((0, self.start), (1, self.end))
        )

    def numerical_guard(self):
        values = [self.start, self.end, *(self.root_source.controls or ())]
        if self.kind != "arc":
            values.extend(self.controls_exact())
        if self.kind == "arc":
            values += [self.root_source.start, self.root_source.center]
        magnitude = max(abs(float(x)) for point in values for x in point)
        rounding = max(sum(abs(Q(float(x)) - _scalar(x)) for x in point) for point in values)
        return math.nextafter(
            float(self.endpoint_gap_bound() + rounding) + 256 * math.ulp(max(1.0, magnitude)),
            math.inf,
        )

    def radius_bounds(self):
        if self.kind != "arc":
            raise SourceViewError("Only an arc has a source circle radius.")
        return _sqrt(
            sum((a - b) ** 2 for a, b in zip(self.root_source.start, self.root_source.center))
        )

    def green_integral_bounds(self):
        """Signed source ∫(xdy-ydx)/2; no topology or endpoint-gap repair."""
        if self.kind == "line":
            a, b = self.controls_exact()
            return _point(_cross(a, b) / 2)
        if self.kind == "cubic":
            return _point(_cubic(*self.controls_exact()))
        a, b = self.point_bounds(0), self.point_bounds(1)
        dx, dy = (_add(y, _neg(x)) for x, y in zip(a, b))
        cx, cy = self.root_source.center
        radius2 = sum((x - y) ** 2 for x, y in zip(self.root_source.start, (cx, cy)))
        omega = _mul(_pi(), _point(self.data["sweep_deg"] / 180))
        return _mul(
            _point(Q(1, 2)),
            _add(_add(_mul(_point(cx), dy), _mul(_point(-cy), dx)), _mul(_point(radius2), omega)),
        )

    def legacy_whole_curve(self):
        """Only genuine binary-identical whole sources may use legacy kernels."""
        if self.parameter_interval != (0, 1):
            return self
        source = self.root_source
        values = [
            *source.start,
            *source.end,
            *source.center,
            source.sweep_deg,
            *(x for p in source.controls for x in p),
        ]
        if any(Q(float(v)) != v for v in values):
            return self
        data = (
            {"center": source.center, "sweep_deg": float(source.sweep_deg)}
            if self.kind == "arc"
            else dict(zip(("control1", "control2"), source.controls))
            if self.kind == "cubic"
            else {}
        )
        return Curve(source.start, source.end, self.kind, data, self.segment_id)


def source_reference(history, piece_id):
    if not isinstance(history, CurveSubdivisionHistory):
        raise SourceViewError("An explicit immutable history is required.")
    piece = next((p for p in history.pieces if p.id == piece_id), None)
    if piece is None:
        raise SourceViewError("The source piece is not active.")
    return SourceCurveView(
        piece.source,
        (piece.source_start, piece.source_end),
        profile_id=history.profile_id,
        history_id=history.to_dict()["segment_id"],
        piece_id=piece.id,
        generation=piece.geometry_generation,
    ).to_reference()


def canonical_projection(reference):
    view = SourceCurveView.from_reference(reference)
    return {
        "kind": view.kind,
        "start": list(map(float, view.start)),
        "end": list(map(float, view.end)),
        "data": {
            key: list(map(float, value)) if isinstance(value, tuple) else float(value)
            for key, value in view.data.items()
        },
    }


def validate_projection(reference, *, kind, start, end, data):
    expected = canonical_projection(reference)
    actual = {"kind": kind, "start": list(start), "end": list(end), "data": dict(data)}

    def valid_numbers(value):
        if isinstance(value, dict):
            return all(valid_numbers(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return all(valid_numbers(v) for v in value)
        return type(value) in (int, float) and math.isfinite(value)

    if actual != expected or not valid_numbers([start, end, data]):
        raise SourceViewError(
            "The floating source cache differs from its canonical exact projection."
        )
    return SourceCurveView.from_reference(reference)


def _resolved_view(history, reference):
    resolution = history.resolve(reference)
    if resolution.status not in ("SINGLE", "CHAIN"):
        raise SourceViewError(resolution.reason)
    pieces = {p.id: p for p in history.pieces}
    family = [
        (pieces[u.piece_id].source, pieces[u.piece_id].geometry_generation) for u in resolution.uses
    ]
    if any(item != family[0] for item in family):
        raise SourceViewError("EDITED_GEOMETRY_GENERATIONS_DO_NOT_FORM_ONE_SOURCE")
    intervals, coverage = [], []
    for use in resolution.uses:
        piece = pieces[use.piece_id]
        start = piece.source_start + use.start * (piece.source_end - piece.source_start)
        end = piece.source_start + use.end * (piece.source_end - piece.source_start)
        intervals.append((start, end))
        coverage.append(
            {
                "piece_id": piece.id,
                "piece_interval": list(map(str, (use.start, use.end))),
                "source_interval": list(map(str, (start, end))),
                "reference_interval": list(map(str, (use.reference_start, use.reference_end))),
            }
        )
    if any(a[1] != b[0] for a, b in zip(intervals, intervals[1:])):
        raise SourceViewError("SOURCE_INTERVALS_ARE_NOT_CONTIGUOUS")
    source, generation = family[0]
    view = SourceCurveView(
        source,
        (intervals[0][0], intervals[-1][1]),
        profile_id=history.profile_id,
        history_id=history.to_dict()["segment_id"],
        piece_id=reference.segment_id,
        generation=generation,
    )
    return view, coverage


def semantic_reference_curves(profile, histories, references):
    """Resolve ordered semantic edges, without repartitioning the opposite loft.

    histories is {root_id: immutable History}; references are ordered IDs or
    qualified TrimReference objects. Partial resolution is distinct from full
    profile material coverage, and cannot grant a whole-profile EXACT result.
    """
    from .profile_curves import source_curve

    curves, coverage, occupied = [], [], {}
    try:
        if not isinstance(histories, dict) or not isinstance(references, (list, tuple)):
            raise SourceViewError("EXPLICIT_HISTORY_MAPPING_AND_ORDERED_REFERENCES_REQUIRED")
        if not references or len(references) > 4096 or len(histories) > 4096:
            raise SourceViewError("SEMANTIC_REFERENCE_BUDGET_OR_EMPTY_INPUT")
        active_ids = [s.id for s in profile.segments]
        if len(set(active_ids)) != len(active_ids):
            raise SourceViewError("DUPLICATE_ACTIVE_SEGMENT_ID")
        owners, work = {}, 0
        for root_id, history in histories.items():
            if (
                not isinstance(history, CurveSubdivisionHistory)
                or history.profile_id != profile.id
                or root_id != history.to_dict()["segment_id"]
            ):
                raise SourceViewError("HISTORY_PROFILE_OR_ROOT_ID_MISMATCH")
            for piece in history.pieces:
                for lineage in piece.lineage:
                    work += 1
                    if work > 65536:
                        raise SourceViewError("SEMANTIC_LINEAGE_WORK_BUDGET_EXHAUSTED")
                    owners.setdefault(lineage.ancestor_id, set()).add(root_id)
        for item in references:
            reference = TrimReference(item, profile.id, item) if isinstance(item, str) else item
            if not isinstance(reference, TrimReference) or reference.profile_id != profile.id:
                raise SourceViewError("QUALIFIED_REFERENCE_PROFILE_MISMATCH")
            candidates = []
            for root_id in owners.get(reference.segment_id, ()):
                history = histories[root_id]
                resolved = history.resolve(reference)
                if resolved.status in ("SINGLE", "CHAIN"):
                    candidates.append(history)
            if len(candidates) > 1:
                raise SourceViewError("AMBIGUOUS_HISTORY_OWNERSHIP")
            if candidates:
                history = candidates[0]
                view, uses = _resolved_view(history, reference)
                for use in uses:
                    segment = profile.segment(use["piece_id"])
                    if segment is None:
                        raise SourceViewError("ACTIVE_SOURCE_PIECE_MISSING_FROM_PROFILE")
                    expected = source_reference(history, segment.id)
                    stored = getattr(segment, "source_reference", None)
                    if stored is not None and stored != expected:
                        raise SourceViewError("ACTIVE_PIECE_DESCRIPTOR_DIFFERS_FROM_REPLAY")
                    validate_projection(
                        expected,
                        kind=segment.kind,
                        data=segment.data,
                        start=profile.vertex(segment.start_vertex_id).point,
                        end=profile.vertex(segment.end_vertex_id).point,
                    )
                curve = view.legacy_whole_curve()
                generation = view.generation
            else:
                segment = profile.segment(reference.segment_id)
                if segment is None:
                    raise SourceViewError("HISTORICAL_SOURCE_NOT_COVERED")
                curve = source_curve(profile, segment)
                if (reference.start, reference.end) != (0, 1):
                    if not isinstance(curve, SourceCurveView):
                        curve = SourceCurveView(
                            CurveSource.from_curve(curve),
                            (0, 1),
                            profile_id=profile.id,
                            history_id=segment.id,
                            piece_id=segment.id,
                            generation=0,
                        )
                    curve = curve.restricted(reference.start, reference.end)
                uses = [
                    {
                        "piece_id": segment.id,
                        "piece_interval": list(map(str, (reference.start, reference.end))),
                        "source_interval": list(map(str, (reference.start, reference.end))),
                        "reference_interval": list(map(str, (reference.start, reference.end))),
                    }
                ]
                generation = getattr(curve, "generation", 0)
            for use in uses:
                interval = tuple(sorted(map(Q, use["piece_interval"])))
                old = occupied.setdefault(use["piece_id"], [])
                if any(max(a, interval[0]) < min(b, interval[1]) for a, b in old):
                    raise SourceViewError("OVERLAPPING_SEMANTIC_MATERIAL_REFERENCES")
                old.append(interval)
            curves.append(curve)
            coverage.append(
                {
                    "reference_id": reference.id,
                    "profile_id": profile.id,
                    "segment_id": reference.segment_id,
                    "parameter_interval": list(map(str, (reference.start, reference.end))),
                    "generation": generation,
                    "uses": uses,
                }
            )
        full = set(occupied) == set(active_ids)
        for intervals in occupied.values():
            ordered, cursor = sorted(intervals), Q(0)
            for a, b in ordered:
                full &= a == cursor
                cursor = b
            full &= cursor == 1
        return {
            "status": "RESOLVED",
            "curves": tuple(curves),
            "coverage": coverage,
            "full_profile_coverage": bool(full),
            "why": "",
        }
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        return {
            "status": "UNRESOLVED",
            "curves": (),
            "coverage": coverage,
            "full_profile_coverage": False,
            "why": str(exc),
        }


def historical_point(history, reference):
    if not isinstance(history, CurveSubdivisionHistory) or not isinstance(
        reference, SourcePointReference
    ):
        raise SourceViewError("An explicit history and qualified point reference are required.")
    resolution = history.resolve_point(reference)
    if resolution.status not in ("SINGLE", "SHARED_POINT"):
        return {"status": "UNRESOLVED", "why": resolution.reason, "uses": ()}
    pieces = {p.id: p for p in history.pieces}
    use = resolution.uses[0]
    piece = pieces[use.piece_id]
    t = piece.source_start + use.parameter * (piece.source_end - piece.source_start)
    nominal = _source_bounds(piece.source, t)
    authored = (
        tuple(map(float, piece.source.start))
        if t == 0
        else tuple(map(float, piece.source.end))
        if t == 1
        else _mid(nominal)
    )
    return {
        "status": resolution.status,
        "why": "",
        "nominal_bounds_exact": nominal,
        "point": authored,
        "uses": tuple((u.piece_id, str(u.parameter)) for u in resolution.uses),
        "generation": piece.geometry_generation,
        "source_parameter_exact": str(t),
        "scope": "SOURCE_POINT_WITH_ALL_OWNERS_NOT_A_NEAREST_VERTEX",
    }


def history_chord(history, segment_id, *, interval=(0, 1)):
    reference = TrimReference(segment_id, history.profile_id, segment_id, *interval)
    try:
        view, uses = _resolved_view(history, reference)
        return {
            "status": "RESOLVED",
            "why": "",
            "source_view": view,
            "points": (view.evaluate(0), view.evaluate(1)),
            "nominal_bounds_exact": (view.point_bounds(0), view.point_bounds(1)),
            "endpoint_gap_bound_exact": str(view.endpoint_gap_bound()),
            "uses": uses,
            "scope": "SEMANTIC_SOURCE_ENDPOINT_CHORD_NOT_AN_EXACT_STRAIGHT_HINGE",
        }
    except SourceViewError as exc:
        return {"status": "UNRESOLVED", "why": str(exc)}


def source_region_area_bounds(outer, holes=(), *, scale=1, max_curves=4096):
    """One original NET body/holes area basis, independent of float projections.

    The caller still proves source topology/closed continuity. Endpoint gaps
    are retained separately; this function never repairs them or approves fit.
    """
    scale = _scalar(scale)
    if scale <= 0 or type(max_curves) is not int or max_curves < 1:
        raise SourceViewError("Positive scale and finite source-area work budget required.")
    if (
        not isinstance(outer, (tuple, list))
        or not isinstance(holes, (tuple, list))
        or len(holes) > max_curves
    ):
        raise SourceViewError("Source area needs finite explicit curve loops.")
    count, areas, gap = 0, [], Q(0)
    for loop in (outer, *holes):
        area, first, previous = _point(Q(0)), None, None
        for curve in loop:
            count += 1
            if count > max_curves or not isinstance(curve, Curve):
                raise SourceViewError("Source area exhausted its known-curve work budget.")
            if first is None:
                first = curve.start
            if previous is not None and previous != curve.start:
                raise SourceViewError("Source area requires the same closed source partition.")
            previous = curve.end
            if not isinstance(curve, SourceCurveView):
                curve = SourceCurveView(
                    CurveSource.from_curve(curve),
                    (0, 1),
                    profile_id="area-only",
                    history_id="area-only",
                    piece_id=curve.segment_id or "area-only",
                    generation=0,
                )
            addition = curve.green_integral_bounds()
            area = (
                (area[0] + addition[0], area[1] + addition[1])
                if area[0] == area[1] and addition[0] == addition[1]
                else _add(area, addition)
            )
            gap += curve.endpoint_gap_bound()
        if first is None or previous != first or area[0] <= 0 <= area[1]:
            raise SourceViewError("Source area has no closed nonzero oriented loop.")
        areas.append(_neg(area) if area[1] < 0 else area)
    low = (areas[0][0] - sum(a[1] for a in areas[1:])) * scale * scale
    high = (areas[0][1] - sum(a[0] for a in areas[1:])) * scale * scale
    if low <= 0:
        raise SourceViewError("Source holes do not leave a proved positive net body area.")
    return {
        "status": "CERTIFIED",
        "area_lower_exact": str(low),
        "area_upper_exact": str(high),
        "endpoint_gap_bound_paper_mm_exact": str(gap * scale),
        "source_curve_count": count,
        "area_basis": "ORIGINAL_NET_BODY_MINUS_HOLES_WITHOUT_TABS",
        "scope": "SOURCE_GREEN_INTEGRALS_ONLY_NOT_TOPOLOGY_OR_ENDPOINT_GAP_CLOSURE",
    }


def native_projection_certificate(
    view, *, position_budget, length_budget, area_budget, max_depth=24, max_segments=16384
):
    """Direct source→actual decimal M/L/C/A bounds; area is not a tube estimate."""
    from .curves import certify_curve, svg_commands

    budgets = tuple(_scalar(v) for v in (position_budget, length_budget, area_budget))
    if min(budgets) <= 0:
        raise SourceViewError("Native projection budgets must be finite positive values.")
    certificate = certify_curve(
        view,
        chord_tolerance=float(budgets[0]),
        length_tolerance=float(budgets[1]),
        max_depth=max_depth,
        max_segments=max_segments,
    )
    import re

    tokens = re.findall(r"[MLCAZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", svg_commands(view))
    commands, index = [], 0
    arity = {"M": 2, "L": 2, "C": 6, "A": 7}
    while index < len(tokens):
        op = tokens[index]
        count = arity[op]
        commands.append([op, *(_scalar(v) for v in tokens[index + 1 : index + 1 + count])])
        index += count + 1
    current, actual = tuple(commands[0][1:]), _point(Q(0))
    for op, *values in commands[1:]:
        end = tuple(values[-2:])
        addition = (
            _point(_cross(current, end) / 2)
            if op == "L"
            else _point(_cubic(current, values[:2], values[2:4], end))
            if op == "C"
            else _arc(current, end, values)
        )
        actual = _add(actual, addition)
        current = end
    source = view.green_integral_bounds()
    error = max(abs(actual[0] - source[1]), abs(actual[1] - source[0]))
    if view.kind == "arc":
        position = _scalar(certificate.svg_deviation_bound)
        length = _scalar(certificate.svg_length_error_bound)
    else:
        original = view.controls_exact()
        native = [tuple(commands[0][1:])]
        native.extend(tuple(commands[1][i : i + 2]) for i in range(1, len(commands[1]), 2))
        differences = [tuple(x - y for x, y in zip(p, q)) for p, q in zip(original, native)]
        position = max(sum(map(abs, p)) for p in differences)
        length = sum(
            sum(abs(x - y) for x, y in zip(p, q)) for p, q in zip(differences, differences[1:])
        )
    return {
        "status": "CERTIFIED"
        if (
            certificate.status == "CERTIFIED"
            and error <= budgets[2]
            and position <= budgets[0]
            and length <= budgets[1]
        )
        else "UNRESOLVED",
        "source_reference": view.to_reference(),
        "source_green_integral_bounds_exact": list(map(str, source)),
        "actual_native_green_integral_bounds_exact": list(map(str, actual)),
        "area_error_bound_exact": str(error),
        "area_budget_exact": str(budgets[2]),
        "endpoint_gap_bound_exact": str(view.endpoint_gap_bound()),
        "position_bound_exact": str(position),
        "length_bound_exact": str(length),
        "curve_status": certificate.status,
        "commands": commands,
        "scope": "SIGNED_SOURCE_TO_ACTUAL_OPEN_GREEN_INTEGRAL; NOT_REGION_TOPOLOGY_OR_FIT",
    }
