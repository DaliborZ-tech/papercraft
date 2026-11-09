"""Conservative planar material sets around certified authored curve chords.

For simple, proven source loops, the true material and its chord proxy can
disagree only inside the certified boundary tubes. Subtracting every tube
therefore gives material that is certainly present; adding them gives material
that may be present. These are geometric bounds, never a physical-build proof.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import lru_cache

from shapely import Polygon, from_wkb
from shapely.ops import unary_union

from .errors import ValidationError
from .geometry import material_polygon, number, vector


@dataclass(frozen=True)
class MaterialEnvelopes:
    """Immutable Shapely sets in the requested frame and its length units."""

    proxy: object
    guaranteed: object
    possible: object
    uncertainty_band: object
    max_error: float
    proof: str
    source_segment_ids: tuple[str, ...] = ()

    @property
    def is_exact(self):
        return self.uncertainty_band.is_empty

    @property
    def max_error_mm(self):
        return self.max_error


_EXACT = "EXACT_LINE_AND_TAB_MATERIAL; no tessellation reservation"
_PROOF = (
    "CERTIFIED_CHORD_PLUS_NATIVE_SVG_BOUNDARY_TUBES; "
    "optional output reservation also bounds serialized manufacturing paths. "
    "requires proven simple source loops and a current verified part projection. "
    "Each oriented rectangle extends by delta both along and normal to its chord, "
    "covering its Euclidean delta-neighborhood, including endpoint caps. "
    "Outward numerical reservations cover rectangle construction rounding. "
    "guaranteed=proxy-minus-tubes; possible=proxy-union-tubes. "
    "Uncertainty is not a proven collision or proven absence of collision; "
    "no physical-build certificate."
)


def _finite_point(point):
    return tuple(vector(point, 2))


def _rounding_guard(*points):
    magnitude = max(1.0, *(abs(value) for point in points for value in point))
    # Arithmetic below uses differences, a unit tangent, products and sums.
    # Reserve substantially more than their combined outward rounding error.
    return 128 * math.ulp(magnitude)


def _tube(start, end, delta):
    """An outer rectangle with square caps, never an inscribed round buffer."""
    a, b = _finite_point(start), _finite_point(end)
    delta = number(delta, "Mez křivkové odchylky", nonnegative=True)
    guard = _rounding_guard(a, b)
    radius = math.nextafter(delta + guard, math.inf)
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if not math.isfinite(length):
        raise ValidationError("Rozsah křivkového obalu přesahuje podporovanou přesnost.")
    tx, ty = (dx / length, dy / length) if length > 0 else (1.0, 0.0)
    nx, ny = -ty, tx
    corners = [
        (point[0] + along * radius * tx + normal * radius * nx,
         point[1] + along * radius * ty + normal * radius * ny)
        for point, along in ((a, -1), (b, 1)) for normal in (-1, 1)
    ]
    # A tiny axis-aligned Minkowski square around every computed corner protects
    # against rounding of the tangent and vertex construction itself. Its convex
    # hull is an outer set, unlike polygonal approximations of circular caps.
    expanded = [
        (math.nextafter(x + sx * guard, -math.inf if sx < 0 else math.inf),
         math.nextafter(y + sy * guard, -math.inf if sy < 0 else math.inf))
        for x, y in corners for sx in (-1, 1) for sy in (-1, 1)
    ]
    if not all(math.isfinite(v) for point in expanded for v in point):
        raise ValidationError("Rozsah křivkového obalu není konečný.")
    return Polygon(expanded).convex_hull


@lru_cache(maxsize=64)
def _bounded_sets(proxy_wkb, chords, source_signature):
    # All arguments are immutable, derived from actual source, scale and cached
    # geometry. No global project revision or caller-supplied mutable hash is used.
    del source_signature
    proxy = from_wkb(proxy_wkb)
    band = unary_union([_tube(a, b, delta) for a, b, delta in chords])
    return proxy, proxy.difference(band), proxy.union(band), band


def _signature(project, surface_ids):
    surfaces = {sid: asdict(project.surfaces[sid]) for sid in sorted(surface_ids)}
    profile_ids = {pid for sid in surface_ids
                   for pid in [project.surfaces[sid].profile_id,
                               *project.surfaces[sid].hole_profile_ids]}
    return json.dumps({
        "scale": project.scale,
        "surfaces": surfaces,
        "profiles": {pid: asdict(project.profiles[pid]) for pid in sorted(profile_ids)},
    }, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _result(proxy, chords, signature, segment_ids):
    if not chords:
        return MaterialEnvelopes(proxy, proxy, proxy, Polygon(), 0.0, _EXACT)
    canonical = tuple(sorted((min(a, b), max(a, b), delta) for a, b, delta in chords))
    proxy, guaranteed, possible, band = _bounded_sets(proxy.wkb, canonical, signature)
    return MaterialEnvelopes(
        proxy, guaranteed, possible, band, max(c[2] for c in chords), _PROOF,
        tuple(sorted(segment_ids)),
    )


def _is_exact_line_trace(profile, segment):
    """A cubic control hull contained in its endpoint segment has that exact image.

    Convex containment proves no point leaves the straight segment; continuity
    and fixed endpoints prove every point of that segment is reached. This says
    nothing about a linear source parameter, arclength or semantic curve kind.
    Topological/regularity validation remains the caller's separate obligation.
    """
    if segment.kind != "cubic":
        return False
    a = tuple(Fraction(x) for x in profile.vertex(segment.start_vertex_id).point)
    b = tuple(Fraction(x) for x in profile.vertex(segment.end_vertex_id).point)
    d = tuple(y-x for x, y in zip(a, b))
    square = sum(x*x for x in d)
    if not square:
        return False
    for key in ("control1", "control2"):
        p = tuple(Fraction(x)-x0 for x, x0 in zip(segment.data[key], a))
        if d[0]*p[1] != d[1]*p[0] or not 0 <= sum(x*y for x, y in zip(d, p)) <= square:
            return False
    return True


def _curved_certificates(project, surface_id):
    surface = project.surfaces[surface_id]
    if surface.kind != "planar":
        raise ValidationError(
            "Tato plocha potřebuje vlastní doloženou mapu materiálového obalu; "
            "rovinný křivkový obal ji nemůže nahradit."
        )
    found = {}
    for pid in [surface.profile_id, *surface.hole_profile_ids]:
        profile = project.profiles[pid]
        curved_ids = {s.id for s in profile.segments
                      if s.kind != "line" and not _is_exact_line_trace(profile, s)}
        if not curved_ids:
            continue
        projection = project.profile_projection(pid)
        for certificate in projection["curves"]:
            if certificate["segment_id"] not in curved_ids:
                continue
            if certificate.get("status") != "CERTIFIED":
                raise ValidationError("Křivkový materiál nemá doloženou mez odchylky.")
            number(certificate["max_chord_deviation_bound"], nonnegative=True)
            number(certificate["svg_deviation_bound"], nonnegative=True)
            if len(certificate["points"]) < 2:
                raise ValidationError("Křivkový materiál nemá úplný řetěz tětiv.")
            found[certificate["segment_id"]] = certificate
        if set(found).intersection(curved_ids) != curved_ids:
            raise ValidationError("V materiálovém obalu chybí zdrojová křivka.")
    return found


def _chord_delta(certificate, factor, start, end, output_error=0):
    source_bound = (certificate["max_chord_deviation_bound"]
                    + certificate["svg_deviation_bound"])
    scaled = math.nextafter(source_bound * factor, math.inf)
    return math.nextafter(scaled + output_error + _rounding_guard(start, end), math.inf)


def _check_chord_chain(edges):
    """Reject duplicate, missing or disconnected cached chord coverage."""
    adjacency, unique = {}, set()
    for edge in edges:
        a, b = _finite_point(edge["start"]), _finite_point(edge["end"])
        key = tuple(sorted((a, b)))
        if a == b or key in unique:
            raise ValidationError("Materiálový obal obsahuje opakovanou nebo nulovou tětivu.")
        unique.add(key)
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    ends = [p for p, neighbors in adjacency.items() if len(neighbors) == 1]
    if len(ends) != 2 or any(len(neighbors) not in (1, 2) for neighbors in adjacency.values()):
        raise ValidationError("Materiálový obal nemá úplný souvislý řetěz tětiv.")
    visited, pending = set(), [ends[0]]
    while pending:
        point = pending.pop()
        if point not in visited:
            visited.add(point)
            pending.extend(adjacency[point] - visited)
    if len(visited) != len(adjacency):
        raise ValidationError("Materiálový obal obsahuje oddělené řetězce tětiv.")


def surface_envelopes(project, surface_id, *, paper=False):
    """Return material bounds in the surface's model UV or paper-scaled UV.

    Source loops must already have passed the source-topology proof. This helper
    bounds their material representation; it does not prove their simplicity.
    """
    surface = project.surfaces[surface_id]
    factor = project.scale if paper else 1.0
    number(factor, "Měřítko materiálu", positive=True)
    profile_ids = [surface.profile_id, *surface.hole_profile_ids]
    loops = [[(x * factor, y * factor) for x, y in project.profile_outline(pid)]
             for pid in profile_ids]
    proxy = material_polygon(loops[0], loops[1:])
    certificates = _curved_certificates(project, surface_id)
    chords = []
    for certificate in certificates.values():
        points = [tuple(v * factor for v in p) for p in certificate["points"]]
        for a, b in zip(points, points[1:]):
            chords.append((a, b, _chord_delta(certificate, factor, a, b)))
    return _result(proxy, chords, _signature(project, [surface_id]), certificates)


def part_envelopes(project, part, *, output_error_mm=0):
    """Return local paper-mm material bounds, including exact straight tabs.

    A nonzero output reservation covers every boundary, including straight
    neighboring parts and tabs. The caller must verify the cache against source
    before using these sets. Missing/repeated curve chord coverage is rejected.
    """
    if part.stale:
        raise ValidationError("Materiálový díl je neaktuální. Nejprve jej přepočítejte.")
    output_error_mm = number(output_error_mm, "Mez odchylky výstupu", nonnegative=True)
    polygons = [material_polygon(loops[0], loops[1:]) for loops in part.polygons.values()]
    polygons.extend(Polygon(path["points"]) for path in part.paths["TABS"])
    proxy = unary_union(polygons)
    chords, source_ids = [], set()
    if output_error_mm:
        for polygon in polygons:
            for ring in [polygon.exterior, *polygon.interiors]:
                points = [_finite_point(point) for point in ring.coords]
                chords.extend((a, b, output_error_mm) for a, b in zip(points, points[1:]))
    for sid in part.surface_ids:
        certificates = _curved_certificates(project, sid)
        for segment_id, certificate in certificates.items():
            edges = [edge for edge in part.edges
                     if edge["surface_id"] == sid and edge["edge_id"] == segment_id]
            if len(edges) != len(certificate["points"]) - 1:
                raise ValidationError(
                    "Materiálový obal nepokrývá všechny tětivy zdrojové křivky. "
                    "Přepočítejte díl."
                )
            _check_chord_chain(edges)
            source_ids.add(segment_id)
            for edge in edges:
                a, b = _finite_point(edge["start"]), _finite_point(edge["end"])
                chords.append((a, b, _chord_delta(
                    certificate, project.scale, a, b, output_error_mm,
                )))
    return _result(proxy, chords, _signature(project, part.surface_ids), source_ids)
