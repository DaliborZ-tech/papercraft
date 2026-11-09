"""Bounded planar triangle islands derived from explicitly paired line profiles.

This first numerical slice supports LINE/LINE ruled patches only. It never
changes its sources and never grants EXACT to the smooth target. For
S=A+B*u+C*v+D*u*v, splitting a parameter rectangle along (0,0)--(1,1)
has SAME-PARAMETER error <=|D|*du*dv/4 over both entire triangle interiors.
The bound includes the actual rounded output vertices, not just ideal vertices.

An affine exact Jacobian field N=B x C+u*(B x D)+v*(D x C) proves regional
regularity and normal-angle bounds against each delivered triangle's plane.
Intrinsic edge lengths use independent quadratic-Bezier chord/control-polygon
enclosures. Parameter coverage is complete and conforming; global embedding,
practical assembly and an application/persistence API are outside this module.
"""

from __future__ import annotations

import math
from fractions import Fraction

from .curve_area import _atan, _out, _pi, _scalar, _sqrt
from .loft_geometry import LoftCorrespondence, LoftProfile, _pair, _profile

_ZERO = Fraction(0)
_ONE = Fraction(1)
_GRID = 10**24


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _mul(a, factor):
    return tuple(x * factor for x in a)


def _sub(a, b):
    return _add(a, _mul(b, -1))


def _dot(a, b):
    return sum((x * y for x, y in zip(a, b)), _ZERO)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    square = _dot(a, a)
    numerator, denominator = math.isqrt(square.numerator), math.isqrt(square.denominator)
    if (
        numerator * numerator == square.numerator
        and denominator * denominator == square.denominator
    ):
        exact = Fraction(numerator, denominator)
        return exact, exact
    return _sqrt(square)


def _world(profile, point):
    if any(
        not isinstance(p, (tuple, list)) or len(p) != 3
        for p in (profile.origin, profile.u, profile.v)
    ):
        raise ValueError("Source world planes need three exact coordinates in each vector")
    origin, u, v = (tuple(_scalar(x) for x in p) for p in (profile.origin, profile.u, profile.v))
    x, y = (_scalar(p) for p in point)
    return _add(origin, _add(_mul(u, x), _mul(v, y)))


def _surface(coefficients, u, v):
    a, b, c, d = coefficients
    return _add(a, _add(_mul(b, u), _add(_mul(c, v), _mul(d, u * v))))


def _jacobian(coefficients, u, v):
    _, b, c, d = coefficients
    return _add(_cross(b, c), _add(_mul(_cross(b, d), u), _mul(_cross(d, c), v)))


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Derived vertices exceed finite output precision")
    return result


def _float_upper(value):
    result = _float(value)
    if Fraction(result) < value:
        result = math.nextafter(result, math.inf)
    if not math.isfinite(result):
        raise ValueError("An outward finite upper bound cannot be represented")
    return result


def _float_lower(value):
    result = _float(value)
    if Fraction(result) > value:
        result = math.nextafter(result, -math.inf)
    return result


def _upper(value):
    return _out((_ZERO, value), _GRID)[1]


def _lower(value):
    return _out((value, value), _GRID)[0]


def _normal_bounds(coefficients, corners, rounded_vertices, scale):
    edge_a = _sub(rounded_vertices[1], rounded_vertices[0])
    edge_b = _sub(rounded_vertices[2], rounded_vertices[0])
    triangle_normal = _cross(edge_a, edge_b)
    normal_upper = _norm(triangle_normal)[1]
    if normal_upper <= 0:
        return None
    values = [_jacobian(coefficients, u, v) for u, v in corners]
    minimum_dot = min(_dot(value, triangle_normal) for value in values)
    if minimum_dot <= 0:
        return None
    # N is affine. Dot extrema occur at rectangle corners; norm(cross(N,K))
    # is convex, hence its maximum is bounded by the corner maximum. Positive
    # dot proves norm(N)>=min_dot/|K|>0 and angle=atan(|N x K|/(N.K)).
    cross_upper = max(_norm(_cross(value, triangle_normal))[1] for value in values)
    ratio = cross_upper / minimum_dot
    if not ratio:
        angle = _ZERO
    elif ratio <= 1:
        angle = _atan(ratio)[1]
    else:
        angle = _pi()[1] / 2 - _atan(1 / ratio)[0]
    degrees = min(Fraction(90), _upper(angle * 180 / _pi()[0]))
    regularity = _lower(minimum_dot / normal_upper * scale * scale)
    if regularity <= 0:
        return None
    return degrees, regularity, triangle_normal


def _source_patch(first, second, a, b, reference):
    first_start, first_end = _world(first, a.start), _world(first, a.end)
    second_start, second_end = _world(second, b.start), _world(second, b.end)
    coefficients = (
        first_start,
        _sub(first_end, first_start),
        _sub(second_start, first_start),
        _sub(_sub(second_end, second_start), _sub(first_end, first_start)),
    )
    return coefficients, {
        "first_profile_id": first.profile_id,
        "second_profile_id": second.profile_id,
        "first_segment_id": reference.first_segment_id,
        "second_segment_id": reference.second_segment_id,
        "first_parameter_interval": list(reference.first_interval),
        "second_parameter_interval": list(reference.second_interval),
    }


def _node_key(patch_index, i, j, nu, patch_count, closed):
    # Consecutive patches meet by explicit source correspondence, never by
    # nearest world-coordinate matching. Corner rulings share logical nodes.
    if i == 0:
        return "corner", patch_index, j
    if i == nu:
        next_corner = (patch_index + 1) % patch_count if closed else patch_index + 1
        return "corner", next_corner, j
    return "patch", patch_index, i, j


def _edge_lengths(coefficients, uv, rounded, scale):
    (u0, v0), (u1, v1) = uv
    du, dv = u1 - u0, v1 - v0
    a, b, c, d = coefficients
    del a
    first, last = _surface(coefficients, u0, v0), _surface(coefficients, u1, v1)
    velocity = _add(_mul(_add(b, _mul(d, v0)), du), _mul(_add(c, _mul(d, u0)), dv))
    control = _add(first, _mul(velocity, Fraction(1, 2)))
    intrinsic_lower = _norm(_sub(last, first))[0] * scale
    intrinsic_upper = (_norm(_sub(control, first))[1] + _norm(_sub(last, control))[1]) * scale
    chord_lower, chord_upper = (value * scale for value in _norm(_sub(rounded[1], rounded[0])))
    difference = max(abs(intrinsic_upper - chord_lower), abs(chord_upper - intrinsic_lower))
    return intrinsic_lower, intrinsic_upper, chord_lower, chord_upper, difference


def _candidate(patches, nu, nv, closed, scale):
    triangles, edges, reports = [], {}, []
    deviation = rounding = max_angle = _ZERO
    minimum_regularity = None
    patch_count = len(patches)
    for patch_index, (coefficients, provenance) in enumerate(patches):
        nodes = {}
        ideal_error = _norm(coefficients[3])[1] * scale / (4 * nu * nv)
        for i in range(nu + 1):
            for j in range(nv + 1):
                uv = Fraction(i, nu), Fraction(j, nv)
                exact = _surface(coefficients, *uv)
                floats = [_float(value) for value in exact]
                rounded = tuple(Fraction(value) for value in floats)
                error = _norm(_sub(exact, rounded))[1] * scale
                nodes[i, j] = (uv, exact, floats, rounded, error)
                rounding = max(rounding, error)
        patch_triangle_indices = []
        for i in range(nu):
            for j in range(nv):
                keys = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
                corners = [nodes[key][0] for key in keys]
                for half in ((0, 1, 2), (0, 2, 3)):
                    selected = [nodes[keys[index]] for index in half]
                    bound = _normal_bounds(coefficients, corners, [p[3] for p in selected], scale)
                    if bound is None:
                        return None, "Regional regularity/output triangle orientation is unresolved"
                    angle, regularity, triangle_normal = bound
                    minimum_regularity = (
                        regularity
                        if minimum_regularity is None
                        else min(minimum_regularity, regularity)
                    )
                    max_angle = max(max_angle, angle)
                    position = _upper(ideal_error + max(point[4] for point in selected))
                    deviation = max(deviation, position)
                    triangle_index = len(triangles)
                    patch_triangle_indices.append(triangle_index)
                    triangle = {
                        "patch_index": patch_index,
                        "parameter_vertices_exact": [[str(x) for x in p[0]] for p in selected],
                        "world_vertices_model_mm": [p[2] for p in selected],
                        "ideal_vertices_model_mm_exact": [[str(x) for x in p[1]] for p in selected],
                        "delivered_vertices_model_mm_exact": [
                            [str(x) for x in p[3]] for p in selected
                        ],
                        "position_error_bound_paper_mm_exact": str(position),
                        "normal_angle_bound_deg_exact": str(angle),
                        "regularity_lower_paper_mm2_exact": str(regularity),
                        "delivered_plane_normal_exact": [str(x) for x in triangle_normal],
                    }
                    triangles.append(triangle)
                    for first, second in ((0, 1), (1, 2), (2, 0)):
                        ka, kb = keys[half[first]], keys[half[second]]
                        node_a = _node_key(patch_index, *ka, nu, patch_count, closed)
                        node_b = _node_key(patch_index, *kb, nu, patch_count, closed)
                        edge_key = tuple(sorted((node_a, node_b)))
                        use = {
                            "triangle_index": triangle_index,
                            "patch_index": patch_index,
                            "parameter_endpoints_exact": [
                                triangle["parameter_vertices_exact"][n] for n in (first, second)
                            ],
                        }
                        if edge_key not in edges:
                            uv = selected[first][0], selected[second][0]
                            rounded = selected[first][3], selected[second][3]
                            lengths = _edge_lengths(coefficients, uv, rounded, scale)
                            edges[edge_key] = {"uses": [], "lengths": lengths}
                        edges[edge_key]["uses"].append(use)
        determinant = _dot(coefficients[1], _cross(coefficients[2], coefficients[3]))
        reports.append(
            {
                "source": provenance,
                "bilinear_coefficients_model_mm_exact": [[str(x) for x in a] for a in coefficients],
                "developability_determinant_exact": str(determinant),
                "nondevelopable_witness": determinant != 0,
                "parameter_area_exact": "1",
                "triangle_indices": patch_triangle_indices,
            }
        )
    edge_reports, max_length_difference = [], _ZERO
    boundary = [_ZERO, _ZERO, _ZERO, _ZERO]
    seam_pairs = 0
    for record in edges.values():
        uses, lengths = record["uses"], record["lengths"]
        if len(uses) not in (1, 2):
            raise ValueError("The derived parameter triangulation has invalid edge incidence")
        if len(uses) == 2:
            seam_pairs += 1
        else:
            boundary = [a + b for a, b in zip(boundary, lengths[:4])]
        max_length_difference = max(max_length_difference, lengths[4])
        low, high, chord_low, chord_high, difference = lengths
        edge_reports.append(
            {
                "role": "PAIRED_ISLAND_CUT" if len(uses) == 2 else "SOURCE_BOUNDARY_CUT",
                "uses": uses,
                "source_length_lower_paper_mm_exact": str(_lower(low)),
                "source_length_upper_paper_mm_exact": str(_upper(high)),
                "delivered_length_lower_paper_mm_exact": str(_lower(chord_low)),
                "delivered_length_upper_paper_mm_exact": str(_upper(chord_high)),
                "absolute_length_difference_bound_paper_mm_exact": str(_upper(difference)),
            }
        )
    boundary_difference = max(abs(boundary[1] - boundary[2]), abs(boundary[3] - boundary[0]))
    return {
        "patches": reports,
        "triangles": triangles,
        "edges": edge_reports,
        "max_surface_deviation_paper_mm": _float_upper(deviation),
        "max_surface_deviation_paper_mm_exact": str(deviation),
        "max_normal_angle_bound_deg": _float_upper(max_angle),
        "max_normal_angle_bound_deg_exact": str(max_angle),
        "regularity_lower_paper_mm2": _float_lower(minimum_regularity),
        "regularity_lower_paper_mm2_exact": str(minimum_regularity),
        "numerical_vertex_error_bound_paper_mm": _float_upper(_upper(rounding)),
        "lengths": {
            "scope": "TRIANGLE_EDGES_VS_SAME_SOURCE_PARAMETER_PATHS_NOT_GEODESICS",
            "max_edge_absolute_difference_bound_paper_mm": _float_upper(
                _upper(max_length_difference)
            ),
            "boundary_absolute_difference_bound_paper_mm": _float_upper(
                _upper(boundary_difference)
            ),
            "source_boundary_lower_paper_mm_exact": str(_lower(boundary[0])),
            "source_boundary_upper_paper_mm_exact": str(_upper(boundary[1])),
            "delivered_boundary_lower_paper_mm_exact": str(_lower(boundary[2])),
            "delivered_boundary_upper_paper_mm_exact": str(_upper(boundary[3])),
        },
        "counts": {
            "patches": patch_count,
            "cells": patch_count * nu * nv,
            "triangles": len(triangles),
            "triangle_island_parts": len(triangles),
            "paired_cut_seams": seam_pairs,
            "source_boundary_cut_segments": len(edge_reports) - seam_pairs,
            "manufactured_triangle_cut_segments": 3 * len(triangles),
        },
    }, None


def segment_ruled_loft(
    first: LoftProfile,
    second: LoftProfile,
    correspondences: tuple[LoftCorrespondence, ...],
    *,
    scale: float,
    max_deviation_mm=0.25,
    max_cells=4096,
    max_depth=16,
) -> dict:
    """Return detached APPROXIMATE triangle-island geometry or UNRESOLVED.

    All source segments must be lines, explicitly paired once over [0,1] or
    [1,0]. Parameter subdivision is a conforming, globally refined dyadic tensor
    grid, shared across patch boundaries. max_cells caps every candidate grid;
    total examined cells are less than twice that cap. max_depth caps refinement
    rounds. No application UUID is generated: all output indices are result-local
    and provenance is the source segment/interval plus parameter triangle.
    """
    examined, source, last_reason = 0, {}, "No bounded candidate was produced"
    try:
        if not isinstance(first, LoftProfile) or not isinstance(second, LoftProfile):
            raise ValueError("Segmentation needs two explicit source LoftProfile records")
        for value, name in ((scale, "Paper scale"), (max_deviation_mm, "Deviation budget")):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(name + " must be finite and positive")
        if type(max_cells) is not int or max_cells < 1:
            raise ValueError("The cell budget must be a positive integer")
        if type(max_depth) is not int or not 0 <= max_depth <= 32:
            raise ValueError("The refinement depth budget must be an integer in [0,32]")
        if not isinstance(correspondences, (tuple, list)) or len(correspondences) > max_cells:
            raise ValueError("Source correspondences exceed the cell budget")
        for profile in (first, second):
            if (
                not isinstance(profile.profile_id, str)
                or not profile.profile_id
                or not isinstance(profile.closed, bool)
            ):
                raise ValueError("Source profile identity/closed state is missing")
            if any(c.kind != "line" for c in profile.curves):
                raise ValueError("This bounded segmentation slice supports LINE/LINE sources only")
            if any(not isinstance(c.segment_id, str) or not c.segment_id for c in profile.curves):
                raise ValueError("Source segments need explicit identities")
            _profile(profile)
        for reference in correspondences:
            if not isinstance(reference, LoftCorrespondence) or any(
                isinstance(x, bool)
                for interval in (reference.first_interval, reference.second_interval)
                for x in interval
            ):
                raise ValueError("Source correspondence needs explicit oriented numeric intervals")
        pairs = _pair(first, second, correspondences)
        if {r.first_segment_id for _, _, r in pairs} != {c.segment_id for c in first.curves} or {
            r.second_segment_id for _, _, r in pairs
        } != {c.segment_id for c in second.curves}:
            raise ValueError("Every source segment must be covered exactly once")
        if first.closed != second.closed:
            raise ValueError("Matched source profiles need consistent open/closed topology")
        if first.closed and (
            pairs[-1][0].end != pairs[0][0].start or pairs[-1][1].end != pairs[0][1].start
        ):
            raise ValueError("Closed source correspondence does not close at its declared seam")
        patches = [_source_patch(first, second, a, b, reference) for a, b, reference in pairs]
        source = {
            "first_profile_id": first.profile_id,
            "second_profile_id": second.profile_id,
            "first_closed": first.closed,
            "second_closed": second.closed,
            "correspondences": [provenance for _, provenance in patches],
            "expected_first_segment_ids": [c.segment_id for c in first.curves],
            "expected_second_segment_ids": [c.segment_id for c in second.curves],
        }
        scale_q, budget = Fraction(scale), Fraction(max_deviation_mm)
        if budget < Fraction(1, _GRID):
            raise ValueError("Deviation budget is below the public rational rounding budget")
        nu = nv = 1
        for depth in range(max_depth + 1):
            count = len(patches) * nu * nv
            if count > max_cells:
                raise ValueError("The bounded segmentation cell budget was exhausted")
            examined += count
            ideal_error = max(_norm(c[3])[1] for c, _ in patches) * scale_q / (4 * nu * nv)
            candidate = None
            if ideal_error <= budget:
                candidate, last_reason = _candidate(patches, nu, nv, first.closed, scale_q)
            else:
                last_reason = "Whole-interior bilinear deviation exceeds the requested budget"
            if (
                candidate is not None
                and Fraction(candidate["max_surface_deviation_paper_mm_exact"]) <= budget
            ):
                candidate.update(
                    {
                        "status": "CERTIFIED",
                        "mode": "APPROXIMATE",
                        "family": "BILINEAR_LINE_PAIR_TRIANGLE_ISLANDS",
                        "segmentation_only": True,
                        "source": source,
                        "scale": scale,
                        "requested_deviation_budget_paper_mm": max_deviation_mm,
                        "subdivisions": {"u": nu, "v": nv, "refinement_rounds": depth},
                        "examined_cells": examined,
                        "proof": {
                            "position": (
                                "For each ENTIRE parameter triangle: |S-P1|<=|D|*du*dv/4; "
                                "add max actual rounded vertex error"
                            ),
                            "normal": (
                                "Affine exact N; corner min dot and max norm cross against "
                                "delivered plane give regional atan bound and positive regularity"
                            ),
                            "length": (
                                "Source edge is quadratic Bezier: chord <= intrinsic length <= "
                                "control polygon; compare delivered float edge norm intervals"
                            ),
                            "coverage": (
                                "Conforming dyadic tensor rectangles, each split into two disjoint "
                                "parameter triangles; full source intervals exactly once"
                            ),
                            "identity": (
                                "Source IDs/oriented intervals and exact parameter vertices; "
                                "result-local indices are NOT persistent identities"
                            ),
                            "limits": (
                                "LINE/LINE only; no trim holes, global intersections, practical "
                                "seam grouping, connectors, UI or persistence"
                            ),
                        },
                        "global_embedding": "NOT_CHECKED",
                        "source_area_distortion": "NOT_CERTIFIED_BY_THIS_COMPONENT",
                        "physical_build": "NOT_VERIFIED",
                    }
                )
                return candidate
            if nu <= nv:
                nu *= 2
            else:
                nv *= 2
        raise ValueError("The bounded segmentation depth budget was exhausted: " + str(last_reason))
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        return {
            "status": "UNRESOLVED",
            "mode": "UNRESOLVED",
            "segmentation_only": True,
            "message": str(exc),
            "source": source,
            "examined_cells": examined,
            "supported_source_kinds": ["line"],
            "next_action": (
                "This component certifies only paired line segments. Preserve the curved "
                "target and use a separately proved curved-source segmentation method."
                if "LINE/LINE" in str(exc)
                else "Edit the source or choose a feasible explicit deviation/cell budget; "
                "do not mark the original target EXACT"
            ),
            "physical_build": "NOT_VERIFIED",
        }
