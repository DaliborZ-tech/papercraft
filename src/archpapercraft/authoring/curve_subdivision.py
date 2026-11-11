"""Exact source subdivision and explicit historical trim resolution.

This small per-source history does not mutate a project or choose an application
reference. A CHAIN is an ordered mathematical answer, not permission to replace
a one-edge joint by its first child. Arc children retain the original analytic
source and exact parameter span: rounded endpoints never redefine their circle.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .curve_area import _add, _mul, _pi, _point
from .curve_area import _scalar as _area_scalar
from .curves import Curve
from .loft_area import _sin_cos

_MAX_EVENTS = 1024


def _scalar(value):
    try:
        return _area_scalar(value)
    except ArithmeticError as exc:
        raise ValueError("A source coordinate or parameter needs a valid finite rational") from exc


def _id(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("A source identity must be a nonempty string of at most 128 characters")
    return value


def _parameter(value):
    result = _scalar(value)
    if not 0 <= result <= 1:
        raise ValueError("A source parameter must be in [0, 1]")
    return result


def _xy(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("A source point needs two finite coordinates")
    return tuple(_scalar(item) for item in value)


def _lerp(a, b, t):
    return tuple((1 - t) * x + t * y for x, y in zip(a, b))


def _split_controls(points, t):
    rows = [points]
    while len(rows[-1]) > 1:
        rows.append(tuple(_lerp(a, b, t) for a, b in zip(rows[-1], rows[-1][1:])))
    return tuple(row[0] for row in rows), tuple(row[-1] for row in reversed(rows))


@dataclass(frozen=True)
class CurveSource:
    """Detached exact input; source end is retained even for nominal arc roundoff."""

    kind: str
    start: tuple
    end: tuple
    controls: tuple = ()
    center: tuple = ()
    sweep_deg: Fraction = Fraction(0)

    def __post_init__(self):
        start, end = _xy(self.start), _xy(self.end)
        controls = tuple(_xy(point) for point in self.controls)
        center = _xy(self.center) if self.center else ()
        sweep = _scalar(self.sweep_deg)
        if self.kind == "line" and not controls and not center and sweep == 0:
            data = {}
        elif self.kind == "cubic" and len(controls) == 2 and not center and sweep == 0:
            data = dict(zip(("control1", "control2"), controls))
        elif self.kind == "arc" and not controls and center and 0 < abs(sweep) < 360:
            data = {"center": center, "sweep_deg": float(sweep)}
        else:
            raise ValueError("Malformed exact source descriptor")
        # Match the current authored-curve validity contract; retain the exact
        # rational input rather than the validator's floating-point copy.
        try:
            Curve(start, end, self.kind, data)
        except (OverflowError, TypeError) as exc:
            raise ValueError("Source exceeds the authored finite-coordinate contract") from exc
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)
        object.__setattr__(self, "controls", controls)
        object.__setattr__(self, "center", center)
        object.__setattr__(self, "sweep_deg", sweep)

    @classmethod
    def from_curve(cls, curve: Curve):
        data = curve.data
        return cls(
            curve.kind,
            curve.start,
            curve.end,
            (data["control1"], data["control2"]) if curve.kind == "cubic" else (),
            data["center"] if curve.kind == "arc" else (),
            data["sweep_deg"] if curve.kind == "arc" else Fraction(0),
        )

    def to_dict(self):
        return {
            "kind": self.kind,
            "start": list(map(str, self.start)),
            "end": list(map(str, self.end)),
            "controls": [list(map(str, point)) for point in self.controls],
            "center": list(map(str, self.center)),
            "sweep_deg": str(self.sweep_deg),
        }

    @classmethod
    def from_dict(cls, data):
        keys = {"kind", "start", "end", "controls", "center", "sweep_deg"}
        if not isinstance(data, dict) or set(data) != keys:
            raise ValueError("Unknown or missing exact source fields")
        return cls(**data)

    def controls_on(self, start=0, end=1):
        """Rational de Casteljau, including reversed oriented restrictions."""
        start, end = _parameter(start), _parameter(end)
        if self.kind == "arc" or start == end:
            raise ValueError("Polynomial restriction needs a nonempty line/cubic interval")
        if start > end:
            return tuple(reversed(self.controls_on(end, start)))
        controls = (self.start, *self.controls, self.end)
        if end < 1:
            controls = _split_controls(controls, end)[0]
        if start:
            controls = _split_controls(controls, start / end)[1]
        return controls

    def point_bounds(self, parameter):
        """Outward rational point bounds on the nominal analytic source.

        The stored arc endpoint can differ from its analytic limit under the
        existing authored endpoint tolerance. It is NOT silently substituted.
        """
        t = _parameter(parameter)
        if self.kind != "arc":
            points = (self.start, *self.controls, self.end)
            while len(points) > 1:
                points = tuple(_lerp(a, b, t) for a, b in zip(points, points[1:]))
            return tuple(_point(value) for value in points[0])
        angle = _mul(_pi(), _point(self.sweep_deg * t / 180))
        sine, cosine = _sin_cos(angle)
        x, y = (a - b for a, b in zip(self.start, self.center))
        return (
            _add(_point(self.center[0]), _add(_mul(_point(x), cosine), _mul(_point(-y), sine))),
            _add(_point(self.center[1]), _add(_mul(_point(x), sine), _mul(_point(y), cosine))),
        )


@dataclass(frozen=True)
class LineageMap:
    ancestor_id: str
    ancestor_start: Fraction
    ancestor_end: Fraction
    piece_start: Fraction
    piece_end: Fraction

    def at_piece(self, t):
        return self.ancestor_start + (t - self.piece_start) * (
            self.ancestor_end - self.ancestor_start
        ) / (self.piece_end - self.piece_start)

    def at_ancestor(self, t):
        return self.piece_start + (t - self.ancestor_start) * (
            self.piece_end - self.piece_start
        ) / (self.ancestor_end - self.ancestor_start)


@dataclass(frozen=True)
class CurvePiece:
    id: str
    geometry_generation: int
    source: CurveSource
    source_start: Fraction
    source_end: Fraction
    lineage: tuple[LineageMap, ...]

    def controls_exact(self):
        return self.source.controls_on(self.source_start, self.source_end)

    @property
    def sweep_deg_exact(self):
        if self.source.kind != "arc":
            raise ValueError("Only circular arcs have a signed sweep")
        return self.source.sweep_deg * (self.source_end - self.source_start)

    def point_bounds(self, parameter):
        t = _parameter(parameter)
        return self.source.point_bounds(
            self.source_start + t * (self.source_end - self.source_start)
        )


@dataclass(frozen=True)
class TrimReference:
    id: str
    profile_id: str
    segment_id: str
    start: Fraction = Fraction(0)
    end: Fraction = Fraction(1)

    def __post_init__(self):
        for value in (self.id, self.profile_id, self.segment_id):
            _id(value)
        object.__setattr__(self, "start", _parameter(self.start))
        object.__setattr__(self, "end", _parameter(self.end))
        if self.start == self.end:
            raise ValueError("A trim must have a nonempty oriented interval")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "segment_id": self.segment_id,
            "start": str(self.start),
            "end": str(self.end),
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {
            "id",
            "profile_id",
            "segment_id",
            "start",
            "end",
        }:
            raise ValueError("Unknown or missing historical trim fields")
        return cls(**data)


@dataclass(frozen=True)
class TrimUse:
    piece_id: str
    start: Fraction
    end: Fraction
    reference_start: Fraction
    reference_end: Fraction


@dataclass(frozen=True)
class TrimResolution:
    status: str
    reference: TrimReference
    uses: tuple[TrimUse, ...]
    reason: str = ""


@dataclass(frozen=True)
class SourcePointReference:
    id: str
    profile_id: str
    segment_id: str
    parameter: Fraction

    def __post_init__(self):
        for value in (self.id, self.profile_id, self.segment_id):
            _id(value)
        object.__setattr__(self, "parameter", _parameter(self.parameter))

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "segment_id": self.segment_id,
            "parameter": str(self.parameter),
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {
            "id",
            "profile_id",
            "segment_id",
            "parameter",
        }:
            raise ValueError("Unknown or missing source point fields")
        return cls(**data)


@dataclass(frozen=True)
class PointUse:
    piece_id: str
    parameter: Fraction


@dataclass(frozen=True)
class PointResolution:
    status: str
    reference: SourcePointReference
    uses: tuple[PointUse, ...]
    reason: str = ""


def _coalesce(maps):
    result = []
    for item in sorted(maps, key=lambda x: (x.ancestor_id, x.ancestor_start)):
        if result:
            old = result[-1]
            if (
                old.ancestor_id == item.ancestor_id
                and old.ancestor_end == item.ancestor_start
                and old.piece_end == item.piece_start
                and (old.piece_end - old.piece_start) * (item.ancestor_end - item.ancestor_start)
                == (item.piece_end - item.piece_start) * (old.ancestor_end - old.ancestor_start)
            ):
                result[-1] = LineageMap(
                    old.ancestor_id,
                    old.ancestor_start,
                    item.ancestor_end,
                    old.piece_start,
                    item.piece_end,
                )
                continue
        result.append(item)
    return tuple(result)


class CurveSubdivisionHistory:
    """Immutable per-source topology history, reconstructed by strict event replay.

    IDs are caller-owned opaque identities, qualified by profile_id. Reusing a
    retired ID is forbidden. merge() accepts only adjacent active descendants of
    the SAME immutable geometry generation. edit() deliberately breaks that
    permission while preserving the declared parameter identity of references.
    """

    __slots__ = ("_profile_id", "_segment_id", "_source", "_events", "_pieces", "_ids")

    def __init__(self, profile_id: str, segment_id: str, source: CurveSource):
        if not isinstance(source, CurveSource):
            raise ValueError("A detached CurveSource is required")
        self._profile_id, self._segment_id = _id(profile_id), _id(segment_id)
        self._source, self._events = source, ()
        self._pieces = (
            CurvePiece(
                segment_id,
                0,
                source,
                Fraction(0),
                Fraction(1),
                (LineageMap(segment_id, Fraction(0), Fraction(1), Fraction(0), Fraction(1)),),
            ),
        )
        self._ids = frozenset((segment_id,))

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("Subdivision histories are immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise AttributeError("Subdivision histories are immutable")

    @property
    def profile_id(self):
        return self._profile_id

    @property
    def pieces(self):
        return self._pieces

    def _next(self, event, pieces, new_ids=()):
        if len(self._events) >= _MAX_EVENTS:
            raise ValueError("Subdivision history exceeds its replay work budget")
        for identity in new_ids:
            if _id(identity) in self._ids:
                raise ValueError("An active or retired identity cannot be reused")
        if len(set(new_ids)) != len(new_ids):
            raise ValueError("New descendant identities must be distinct")
        result = object.__new__(type(self))
        for key, value in (
            ("_profile_id", self._profile_id),
            ("_segment_id", self._segment_id),
            ("_source", self._source),
            ("_events", (*self._events, event)),
            ("_pieces", tuple(pieces)),
            ("_ids", self._ids.union(new_ids)),
        ):
            object.__setattr__(result, key, value)
        return result

    def split(self, segment_id, parameter, left_id, right_id):
        t = _parameter(parameter)
        if not 0 < t < 1:
            raise ValueError("Split parameter must be strictly inside the active segment")
        pieces = []
        found = False
        for piece in self._pieces:
            if piece.id != segment_id:
                pieces.append(piece)
                continue
            found = True
            for identity, lo, hi in ((left_id, Fraction(0), t), (right_id, t, Fraction(1))):
                maps = [LineageMap(identity, Fraction(0), Fraction(1), Fraction(0), Fraction(1))]
                for item in piece.lineage:
                    a, b = max(lo, item.piece_start), min(hi, item.piece_end)
                    if a < b:
                        maps.append(
                            LineageMap(
                                item.ancestor_id,
                                item.at_piece(a),
                                item.at_piece(b),
                                (a - lo) / (hi - lo),
                                (b - lo) / (hi - lo),
                            )
                        )
                span = piece.source_end - piece.source_start
                pieces.append(
                    CurvePiece(
                        identity,
                        piece.geometry_generation,
                        piece.source,
                        piece.source_start + lo * span,
                        piece.source_start + hi * span,
                        _coalesce(maps),
                    )
                )
        if not found:
            raise ValueError("Split source is not an active segment")
        return self._next(
            ("split", segment_id, str(t), left_id, right_id), pieces, (left_id, right_id)
        )

    def merge(self, segment_ids, merged_id):
        ids = tuple(segment_ids)
        if len(ids) < 2 or len(set(ids)) != len(ids):
            raise ValueError("Merge needs at least two distinct ordered active descendants")
        try:
            start = [piece.id for piece in self._pieces].index(ids[0])
        except ValueError as exc:
            raise ValueError("Merge source is not active") from exc
        selected = self._pieces[start : start + len(ids)]
        if tuple(piece.id for piece in selected) != ids:
            raise ValueError("Merge sources must be adjacent in their exact source order")
        first = selected[0]
        if any(
            piece.geometry_generation != first.geometry_generation or piece.source != first.source
            for piece in selected
        ):
            raise ValueError("Merge requires the same unedited immutable geometry source")
        if any(a.source_end != b.source_start for a, b in zip(selected, selected[1:])):
            raise ValueError("Merge source intervals must be exactly contiguous")
        lo, hi = first.source_start, selected[-1].source_end
        maps = [LineageMap(merged_id, Fraction(0), Fraction(1), Fraction(0), Fraction(1))]
        for piece in selected:
            a, b = (piece.source_start - lo) / (hi - lo), (piece.source_end - lo) / (hi - lo)
            for item in piece.lineage:
                maps.append(
                    LineageMap(
                        item.ancestor_id,
                        item.ancestor_start,
                        item.ancestor_end,
                        a + item.piece_start * (b - a),
                        a + item.piece_end * (b - a),
                    )
                )
        merged = CurvePiece(
            merged_id, first.geometry_generation, first.source, lo, hi, _coalesce(maps)
        )
        pieces = (*self._pieces[:start], merged, *self._pieces[start + len(ids) :])
        return self._next(("merge", ids, merged_id), pieces, (merged_id,))

    def edit(self, segment_id, source: CurveSource):
        """Explicit geometry edit with unchanged local parameter identity.

        This is NOT a fit or an automatic reparameterization. The application
        must invalidate geometry dependencies; this helper grants no freshness.
        """
        if not isinstance(source, CurveSource):
            raise ValueError("A detached CurveSource is required")
        if not any(piece.id == segment_id for piece in self._pieces):
            raise ValueError("Edit source is not active")
        pieces = tuple(
            CurvePiece(
                piece.id, len(self._events) + 1, source, Fraction(0), Fraction(1), piece.lineage
            )
            if piece.id == segment_id
            else piece
            for piece in self._pieces
        )
        # Store immutable exact source data, not a mutable caller dictionary.
        encoded = tuple((key, _freeze(value)) for key, value in source.to_dict().items())
        return self._next(("edit", segment_id, encoded), pieces)

    def resolve(self, reference: TrimReference, *, require_single=False):
        if not isinstance(reference, TrimReference):
            raise ValueError("A qualified historical TrimReference is required")
        if reference.profile_id != self._profile_id:
            return TrimResolution("UNRESOLVED", reference, (), "PROFILE_ID_MISMATCH")
        lo, hi = sorted((reference.start, reference.end))
        uses = []
        for piece in self._pieces:
            for item in piece.lineage:
                if item.ancestor_id != reference.segment_id:
                    continue
                a, b = max(lo, item.ancestor_start), min(hi, item.ancestor_end)
                if a < b:
                    uses.append(TrimUse(piece.id, item.at_ancestor(a), item.at_ancestor(b), a, b))
        uses.sort(key=lambda use: use.reference_start)
        cursor = lo
        for use in uses:
            if use.reference_start != cursor:
                return TrimResolution("UNRESOLVED", reference, tuple(uses), "AMBIGUOUS_OR_GAPPED")
            cursor = use.reference_end
        if cursor != hi:
            return TrimResolution("UNRESOLVED", reference, tuple(uses), "SOURCE_NOT_COVERED")
        if reference.start > reference.end:
            uses = [
                TrimUse(use.piece_id, use.end, use.start, use.reference_end, use.reference_start)
                for use in reversed(uses)
            ]
        status = "SINGLE" if len(uses) == 1 else "CHAIN"
        if require_single and status == "CHAIN":
            return TrimResolution("UNRESOLVED", reference, tuple(uses), "ONE_TO_MANY_NOT_SUPPORTED")
        return TrimResolution(status, reference, tuple(uses))

    def resolve_point(self, reference: SourcePointReference):
        """Never choose one topological owner for a point shared by children.

        SHARED_POINT proves one analytic material point by identical immutable
        source/generation/parameter, retaining BOTH owners. An application vertex
        identity still needs its explicit topology record. Edited alternatives
        are UNRESOLVED, even when rounded display coordinates happen to match.
        """
        if not isinstance(reference, SourcePointReference):
            raise ValueError("A qualified historical SourcePointReference is required")
        if reference.profile_id != self._profile_id:
            return PointResolution("UNRESOLVED", reference, (), "PROFILE_ID_MISMATCH")
        candidates = []
        for piece in self._pieces:
            for item in piece.lineage:
                if (
                    item.ancestor_id == reference.segment_id
                    and item.ancestor_start <= reference.parameter <= item.ancestor_end
                ):
                    t = item.at_ancestor(reference.parameter)
                    use = PointUse(piece.id, t)
                    if not any(old[0] == use for old in candidates):
                        source_t = piece.source_start + t * (piece.source_end - piece.source_start)
                        candidates.append((use, piece.geometry_generation, piece.source, source_t))
        uses = tuple(item[0] for item in candidates)
        if not candidates:
            return PointResolution("UNRESOLVED", reference, (), "SOURCE_NOT_COVERED")
        if len(candidates) == 1:
            return PointResolution("SINGLE", reference, uses)
        proof = candidates[0][1:]
        if all(item[1:] == proof for item in candidates):
            return PointResolution("SHARED_POINT", reference, uses)
        return PointResolution("UNRESOLVED", reference, uses, "AMBIGUOUS_MATERIAL_POINT")

    def to_dict(self):
        return {
            "schema": 1,
            "profile_id": self._profile_id,
            "segment_id": self._segment_id,
            "source": self._source.to_dict(),
            "events": _thaw(self._events),
        }

    @classmethod
    def from_dict(cls, data):
        if (
            not isinstance(data, dict)
            or set(data)
            != {
                "schema",
                "profile_id",
                "segment_id",
                "source",
                "events",
            }
            or type(data["schema"]) is not int
            or data["schema"] != 1
        ):
            raise ValueError("Unknown subdivision history schema or fields")
        events = data["events"]
        if not isinstance(events, list) or len(events) > _MAX_EVENTS:
            raise ValueError("Invalid subdivision history event budget")
        result = cls(data["profile_id"], data["segment_id"], CurveSource.from_dict(data["source"]))
        for event in events:
            if not isinstance(event, list) or not event:
                raise ValueError("Malformed subdivision history event")
            if event[0] == "split" and len(event) == 5:
                result = result.split(event[1], event[2], event[3], event[4])
            elif event[0] == "merge" and len(event) == 3 and isinstance(event[1], list):
                result = result.merge(event[1], event[2])
            elif event[0] == "edit" and len(event) == 3 and isinstance(event[2], list):
                pairs = event[2]
                if any(not isinstance(pair, list) or len(pair) != 2 for pair in pairs):
                    raise ValueError("Malformed exact edited source")
                try:
                    values = dict(pairs)
                except (TypeError, ValueError) as exc:
                    raise ValueError("Malformed exact edited source fields") from exc
                if len(values) != len(pairs):
                    raise ValueError("Duplicate exact edited source fields")
                result = result.edit(event[1], CurveSource.from_dict(values))
            else:
                raise ValueError("Unknown subdivision history event")
        return result


def _freeze(value):
    return tuple(_freeze(item) for item in value) if isinstance(value, list) else value


def _thaw(value):
    return [_thaw(item) for item in value] if isinstance(value, tuple) else value
