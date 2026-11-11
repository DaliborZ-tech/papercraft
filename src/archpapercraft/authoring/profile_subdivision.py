"""Authored line subdivision with replayed trims and semantic paper anchors.

This first application slice keeps a historical edge as one geometric edge.
It never replaces a reference with the first descendant or the closest vertex.
Arc/cubic application adapters are deliberately separate from this line slice.
"""

from __future__ import annotations

import copy
from fractions import Fraction
from types import SimpleNamespace

import numpy as np

from .commands import atomic
from .curve_subdivision import (
    CurveSource,
    CurveSubdivisionHistory,
    SourcePointReference,
    TrimReference,
)
from .errors import ValidationError
from .model import CurveSegment, Vertex, identity, uuid
from .profile_curves import source_curve


def _piece_source(piece):
    controls = piece.controls_exact()
    return CurveSource("line", controls[0], controls[-1])


def _float_point(piece, parameter):
    return [float(sum(interval) / 2) for interval in piece.point_bounds(parameter)]


def _record_history(record):
    return CurveSubdivisionHistory.from_dict(record["history"])


class ProfileSubdivisionCommands:
    def _profile_edge_exists(self, profile_id, segment_id):
        try:
            self.resolve_profile_edge(profile_id, segment_id)
        except ValidationError:
            return False
        return True

    def profile_edge_overlap(self, profile_id, first_id, second_id):
        if first_id == second_id:
            return True
        first = self._subdivision_record(profile_id, first_id)
        if first is None or first is not self._subdivision_record(profile_id, second_id):
            return False
        history = _record_history(first)
        a, b = [
            history.resolve(TrimReference(item, profile_id, item)) for item in (first_id, second_id)
        ]
        return any(
            x.piece_id == y.piece_id
            and max(min(x.start, x.end), min(y.start, y.end))
            < min(max(x.start, x.end), max(y.start, y.end))
            for x in a.uses
            for y in b.uses
        )

    def _subdivision_record(self, profile_id, segment_id):
        for record in self.profile_subdivisions.values():
            if record["history"]["profile_id"] == profile_id and segment_id in record["edges"]:
                return record
        return None

    def resolve_profile_vertex(self, profile_id, vertex_id):
        profile = self.profiles[profile_id]
        active = profile.vertex(vertex_id)
        if active is not None:
            return copy.deepcopy(active.point)
        for record in self.profile_subdivisions.values():
            if record["history"]["profile_id"] != profile_id or vertex_id not in record["points"]:
                continue
            segment_id, parameter = record["points"][vertex_id]
            history = _record_history(record)
            result = history.resolve_point(
                SourcePointReference(vertex_id, profile_id, segment_id, Fraction(parameter))
            )
            if result.status not in ("SINGLE", "SHARED_POINT"):
                break
            if any(profile.segment(use.piece_id) is None for use in result.uses):
                break
            use = result.uses[0]
            piece = next(p for p in history.pieces if p.id == use.piece_id)
            return _float_point(piece, use.parameter)
        raise ValidationError(
            "ANCHOR_UNRESOLVED: historický bod nemá jednoznačný zdroj. Zvolte kotvu znovu."
        )

    def resolve_profile_edge(self, profile_id, segment_id, *, axis=False):
        """A full historical trim remains one edge; a bent chain is unresolved.

        For a paper axis only, the semantic chord is the two material endpoints.
        This does not turn a bent chain into a straight hinge or glue edge.
        """
        profile = self.profiles[profile_id]
        edge = profile.segment(segment_id)
        if edge is not None:
            return edge, np.array(
                [
                    profile.vertex(edge.start_vertex_id).point,
                    profile.vertex(edge.end_vertex_id).point,
                ]
            )
        record = self._subdivision_record(profile_id, segment_id)
        if record is None:
            raise ValidationError("REFERENCE_UNRESOLVED: historická hrana chybí. Vyberte ji znovu.")
        history = _record_history(record)
        result = history.resolve(TrimReference(segment_id, profile_id, segment_id))
        if result.status not in ("SINGLE", "CHAIN"):
            raise ValidationError("REFERENCE_UNRESOLVED: dějiny hrany neposkytují úplný zdroj.")
        if any(profile.segment(use.piece_id) is None for use in result.uses):
            raise ValidationError(
                "REFERENCE_UNRESOLVED: původní obrys byl nahrazen; vyberte zdroj znovu."
            )
        pieces = {piece.id: piece for piece in history.pieces}
        controls = [
            pieces[use.piece_id].source.controls_on(
                pieces[use.piece_id].source_start
                + use.start * (pieces[use.piece_id].source_end - pieces[use.piece_id].source_start),
                pieces[use.piece_id].source_start
                + use.end * (pieces[use.piece_id].source_end - pieces[use.piece_id].source_start),
            )
            for use in result.uses
        ]
        first, last = controls[0][0], controls[-1][-1]
        dx, dy = last[0] - first[0], last[1] - first[1]
        if not dx and not dy:
            raise ValidationError("REFERENCE_UNRESOLVED: zdrojový směr je nulový.")
        if any(a[-1] != b[0] for a, b in zip(controls, controls[1:])):
            raise ValidationError("REFERENCE_UNRESOLVED: potomci hrany na sebe nenavazují.")
        if not axis:
            family = [
                (pieces[use.piece_id].geometry_generation, pieces[use.piece_id].source)
                for use in result.uses
            ]
            if any(item != family[0] for item in family[1:]):
                raise ValidationError(
                    "REFERENCE_UNRESOLVED: upravené potomky nelze převést na jeden původní úsek. "
                    "Vyberte zdroj spoje znovu."
                )
            # Exact rational collinearity and monotonicity, not a visual fit.
            extent = dx * dx + dy * dy
            positions = []
            for chain in controls:
                for x, y in chain:
                    if (x - first[0]) * dy != (y - first[1]) * dx:
                        raise ValidationError(
                            "REFERENCE_UNRESOLVED: upravený řetězec není přímý ohyb. "
                            "Vyberte spoj znovu."
                        )
                    positions.append(((x - first[0]) * dx + (y - first[1]) * dy) / extent)
            if any(a > b for a, b in zip(positions, positions[1:])):
                raise ValidationError("REFERENCE_UNRESOLVED: potomci mění směr zdrojové hrany.")
        start_id, end_id = record["edges"][segment_id]
        return SimpleNamespace(
            id=segment_id, kind="line", data={}, start_vertex_id=start_id, end_vertex_id=end_id
        ), np.array([list(map(float, first)), list(map(float, last))])

    def _sync_profile_subdivisions(self, profile_id):
        """Declare actual active geometry edits; preserve ancestry, invalidate fit.

        Only active LINE sources belong to this slice. Original replacement
        profiles leave historical references explicitly unresolved.
        """
        profile = self.profiles[profile_id]
        for record in self.profile_subdivisions.values():
            if record["history"]["profile_id"] != profile_id:
                continue
            history = _record_history(record)
            for piece in history.pieces:
                segment = profile.segment(piece.id)
                if segment is None:
                    continue
                if segment.kind != "line":
                    raise ValidationError(
                        "Nejprve zrušte dělení nebo vytvořte nový křivkový obrys; "
                        "tento zdroj má přímou historii."
                    )
                actual = CurveSource.from_curve(source_curve(profile, segment))
                expected = _piece_source(piece)
                # A float projection must not silently redefine rational source.
                if actual.start != tuple(Fraction(float(v)) for v in expected.start) or (
                    actual.end != tuple(Fraction(float(v)) for v in expected.end)
                ):
                    history = history.edit(piece.id, actual)
            record["history"] = history.to_dict()
        for joint in self.joints.values():
            for sid, edge_id in ((joint.surface_a, joint.edge_a), (joint.surface_b, joint.edge_b)):
                if self.surfaces[sid].profile_id == profile_id:
                    try:
                        self.resolve_profile_edge(profile_id, edge_id)
                    except ValidationError:
                        joint.unresolved = True
        for attachment in self.attachments.values():
            surface = self.surfaces[attachment.source_surface_id]
            if surface.profile_id == profile_id and attachment.source_edge_id:
                try:
                    self.resolve_profile_edge(profile_id, attachment.source_edge_id)
                except ValidationError:
                    attachment.unresolved = True

    @atomic
    def split_profile_segment(self, profile_id, segment_id, parameter=0.5):
        profile = self.profiles[profile_id]
        segment = profile.segment(segment_id)
        if segment is None or segment.kind != "line":
            raise ValidationError(
                "Vyberte aktivní úsečku obrysu. Křivkové dělení vyžaduje vlastní zdrojový adaptér."
            )
        record = self._subdivision_record(profile_id, segment_id)
        if record is None:
            history = CurveSubdivisionHistory(
                profile_id, segment_id, CurveSource.from_curve(source_curve(profile, segment))
            )
            record = {
                "history": history.to_dict(),
                "edges": {segment_id: [segment.start_vertex_id, segment.end_vertex_id]},
                "points": {
                    segment.start_vertex_id: [segment_id, "0"],
                    segment.end_vertex_id: [segment_id, "1"],
                },
            }
            self.profile_subdivisions[segment_id] = record
        else:
            history = _record_history(record)
        left_id, right_id, vertex_id = identity(), identity(), identity()
        changed = history.split(segment_id, parameter, left_id, right_id)
        left = next(piece for piece in changed.pieces if piece.id == left_id)
        point = _float_point(left, 1)
        index = next(i for i, edge in enumerate(profile.segments) if edge.id == segment_id)
        profile.vertices.insert(index + 1, Vertex(vertex_id, point))
        profile.segments[index : index + 1] = [
            CurveSegment(left_id, "line", segment.start_vertex_id, vertex_id),
            CurveSegment(right_id, "line", vertex_id, segment.end_vertex_id),
        ]
        record["history"] = changed.to_dict()
        record["edges"].update(
            {
                left_id: [segment.start_vertex_id, vertex_id],
                right_id: [vertex_id, segment.end_vertex_id],
            }
        )
        record["points"][vertex_id] = [segment_id, str(Fraction(parameter))]
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))
        return {"vertex_id": vertex_id, "segment_ids": [left_id, right_id]}

    @atomic
    def merge_profile_segments(self, profile_id, segment_ids):
        profile = self.profiles[profile_id]
        ids = list(segment_ids)
        if len(ids) < 2:
            raise ValidationError("Vyberte sousední potomky stejného dělení.")
        record = self._subdivision_record(profile_id, ids[0])
        if record is None or any(
            self._subdivision_record(profile_id, item) is not record for item in ids
        ):
            raise ValidationError("Spojit lze jen sousední potomky stejného nezměněného zdroje.")
        index = next((i for i, edge in enumerate(profile.segments) if edge.id == ids[0]), -1)
        selected = profile.segments[index : index + len(ids)] if index >= 0 else []
        if [edge.id for edge in selected] != ids:
            raise ValidationError("Vyberte aktivní sousední úseky v pořadí obrysu.")
        history, merged_id = _record_history(record), identity()
        changed = history.merge(ids, merged_id)
        first, last = selected[0].start_vertex_id, selected[-1].end_vertex_id
        profile.segments[index : index + len(ids)] = [CurveSegment(merged_id, "line", first, last)]
        del profile.vertices[index + 1 : index + len(ids)]
        record["history"] = changed.to_dict()
        record["edges"][merged_id] = [first, last]
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))
        return merged_id

    def _validate_profile_subdivisions(self):
        if (
            not isinstance(self.profile_subdivisions, dict)
            or len(self.profile_subdivisions) > 10000
        ):
            raise ValidationError("Neplatný nebo příliš rozsáhlý registr dělení profilů.")
        active_ids = {
            value
            for profile in self.profiles.values()
            for value in [*[v.id for v in profile.vertices], *[s.id for s in profile.segments]]
        }
        retired = set()
        seen_edges = set()
        for root_id, record in self.profile_subdivisions.items():
            uuid(root_id)
            if not isinstance(record, dict) or set(record) != {"history", "edges", "points"}:
                raise ValidationError("Dělení potřebuje úplné zdroje, hrany a body.")
            history = _record_history(record)
            if (
                root_id != record["history"]["segment_id"]
                or history.profile_id not in self.profiles
            ):
                raise ValidationError("Historie dělení nepatří uvedenému profilu.")
            profile = self.profiles[history.profile_id]
            edges, points = record["edges"], record["points"]
            if not isinstance(edges, dict) or not isinstance(points, dict):
                raise ValidationError("Neplatné registry zdrojových hran a bodů.")
            expected = {root_id}
            for event in record["history"]["events"]:
                if event[0] == "split":
                    expected.update(event[3:5])
                elif event[0] == "merge":
                    expected.add(event[2])
            if set(edges) != expected or seen_edges & expected:
                raise ValidationError("Identita dělení se opakuje nebo chybí ve zdrojové historii.")
            seen_edges.update(expected)
            for edge_id, ends in edges.items():
                uuid(edge_id)
                if not isinstance(ends, list) or len(ends) != 2 or ends[0] == ends[1]:
                    raise ValidationError("Historická hrana potřebuje dva různé zdrojové body.")
                if any(vid not in points for vid in ends):
                    raise ValidationError("Historická hrana ztratila bodovou referenci.")
                if edge_id in active_ids and profile.segment(edge_id) is None:
                    raise ValidationError("Historická hrana koliduje s jiným aktivním zdrojem.")
            # Replay the incidence rules too: callers cannot forge a child by
            # merely keeping the valid event list and swapping its vertex IDs.
            root_start, root_end = edges[root_id]
            expected_points = {root_start: [root_id, "0"], root_end: [root_id, "1"]}
            for event in record["history"]["events"]:
                if event[0] == "split":
                    parent, left, right = edges[event[1]], edges[event[3]], edges[event[4]]
                    if left[0] != parent[0] or right[1] != parent[1] or left[1] != right[0]:
                        raise ValidationError("Dělení nemá zdrojově navazující vrcholy.")
                    if left[1] in expected_points:
                        raise ValidationError("Nový řez nesmí znovu použít historický vrchol.")
                    expected_points[left[1]] = [event[1], event[2]]
                elif event[0] == "merge":
                    sources = [edges[item] for item in event[1]]
                    if any(a[1] != b[0] for a, b in zip(sources, sources[1:])) or (
                        edges[event[2]] != [sources[0][0], sources[-1][1]]
                    ):
                        raise ValidationError("Spojení nemá původní souvislou topologii.")
            if points != expected_points:
                raise ValidationError("Historické body nejsou odvozené z přesného replay dělení.")
            for vertex_id, reference in points.items():
                uuid(vertex_id)
                if vertex_id in active_ids and profile.vertex(vertex_id) is None:
                    raise ValidationError("Historický bod koliduje s jiným aktivním zdrojem.")
                if (
                    not isinstance(reference, list)
                    or len(reference) != 2
                    or reference[0] not in edges
                ):
                    raise ValidationError("Historický bod nemá úplnou zdrojovou referenci.")
                SourcePointReference(
                    vertex_id, history.profile_id, reference[0], Fraction(reference[1])
                )
            for piece in history.pieces:
                if piece.source.kind != "line":
                    raise ValidationError("Tento aplikační kontrakt dělení podporuje úsečky.")
                active = profile.segment(piece.id)
                if active is None:
                    # Explicit replacement retains old history for inspection.
                    continue
                if [active.start_vertex_id, active.end_vertex_id] != edges[piece.id]:
                    raise ValidationError("Aktivní úsek nemá původní incidence.")
                if (
                    active.kind != "line"
                    or active.data
                    or any(
                        profile.vertex(vid).point != _float_point(piece, parameter)
                        for vid, parameter in zip(edges[piece.id], (0, 1))
                    )
                ):
                    raise ValidationError("Aktivní geometrie neodpovídá zdroji dělení.")
            retired.update((set(edges) | set(points)) - active_ids)
        return retired
