"""Interval-certified curved ruled loft segmentation; no flattenability grant.

For F=(1-v)C0(u)+v*C1(u), the bilinear interpolant has error
Muu*hu^2/8, where Muu bounds both true source second derivatives. Its
triangulation adds at most Muv*hu*hv/4: the bilinear mixed difference is
the double integral of F_uv=C1'-C0'. Actual delivered vertex uncertainty
is additional. All three are SAME-PARAMETER bounds on entire faces.

Polynomial source intervals use exact restricted Bernstein hulls. Circular
source intervals use the already proved rational Taylor sin/cos enclosures.
The Jacobian is interval enclosed over each complete parameter cell. Positive
projection on the actual delivered triangle normal proves regional regularity;
interval dot/cross bounds prove a normal-angle upper bound. No sample absence
of singularities, triangle residual or epsilon fit is a positive certificate.
"""

from __future__ import annotations

import math
from fractions import Fraction

from .curve_area import _add as _iadd
from .curve_area import _atan, _pi, _scalar, _sqrt
from .curve_area import _mul as _imul
from .curve_area import _neg as _ineg
from .loft_area import _sin_cos
from .loft_geometry import LoftCorrespondence, LoftProfile, _profile
from .segmented_loft import (
    _add,
    _cross,
    _dot,
    _float,
    _float_lower,
    _float_upper,
    _lower,
    _mul,
    _node_key,
    _norm,
    _sub,
    _upper,
    _world,
)

_ZERO = Fraction(0)
_ONE = Fraction(1)
_EDGE_INTERVALS = 4


def _point(value):
    return value, value


def _ivec(point):
    return tuple(_point(x) for x in point)


def _ivadd(a, b):
    return tuple(_iadd(x, y) for x, y in zip(a, b))


def _ivsub(a, b):
    return _ivadd(a, tuple(_ineg(value) for value in b))


def _ivmul(a, factor):
    return tuple(_imul(x, factor) for x in a)


def _ivcross(a, b):
    return tuple(
        _iadd(_imul(a[i], b[j]), _ineg(_imul(a[j], b[i]))) for i, j in ((1, 2), (2, 0), (0, 1))
    )


def _ivnorm(a):
    if all(low == high for low, high in a):
        return _norm(tuple(low for low, _ in a))
    low = sum((min(x * x, y * y) if x * y > 0 else _ZERO for x, y in a), _ZERO)
    high = sum((max(x * x, y * y) for x, y in a), _ZERO)
    return _sqrt(low)[0], _sqrt(high)[1]


def _ivdot(a, b):
    result = _point(_ZERO)
    for value, exact in zip(a, b):
        result = _iadd(result, _imul(value, _point(exact)))
    return result


def _blend(a, b, parameter):
    return _ivadd(_ivmul(a, _point(1 - parameter)), _ivmul(b, _point(parameter)))


def _blend_range(a, b, start, end):
    first, last = _blend(a, b, start), _blend(a, b, end)
    return tuple((min(x[0], y[0]), max(x[1], y[1])) for x, y in zip(first, last))


def _split(controls, parameter):
    left, right, current = [controls[0]], [controls[-1]], list(controls)
    while len(current) > 1:
        current = [
            _add(_mul(a, 1 - parameter), _mul(b, parameter)) for a, b in zip(current, current[1:])
        ]
        left.append(current[0])
        right.append(current[-1])
    return tuple(left), tuple(reversed(right))


def _restrict(controls, start, end):
    if start == end:
        return (_split(controls, start)[0][-1],)
    if end < 1:
        controls = _split(controls, end)[0]
    if start > 0:
        controls = _split(controls, start / end)[1]
    return controls


class _SourceCurve:
    """Original source, including explicit reverse; never reconstruct an arc."""

    def __init__(self, profile, curve, interval):
        self.profile, self.curve = profile, curve
        self.start, self.end = (Fraction(x) for x in interval)
        self.change = self.end - self.start
        self.cache = {}
        if curve.kind == "arc":
            center = tuple(_scalar(x) for x in curve.data["center"])
            x, y = (_scalar(a) - b for a, b in zip(curve.start, center))
            u, v = (tuple(_scalar(x) for x in axis) for axis in (profile.u, profile.v))
            self.center = _world(profile, center)
            self.a, self.b = _add(_mul(u, x), _mul(v, y)), _add(_mul(u, -y), _mul(v, x))
            self.omega = _imul(_pi(), _point(_scalar(curve.data["sweep_deg"]) / 180))
            aa, bb, ab = _dot(self.a, self.a), _dot(self.b, self.b), _dot(self.a, self.b)
            discriminant = _sqrt((aa - bb) ** 2 + 4 * ab * ab)[1]
            eigen_lower = max(_ZERO, (aa + bb - discriminant) / 2)
            eigen_upper = (aa + bb + discriminant) / 2
            omega_absolute = min(abs(x) for x in self.omega), max(abs(x) for x in self.omega)
            # Exact Gram eigenvalue enclosure of [A B]. This includes actual
            # nonideal binary world bases instead of assuming a perfect circle
            # after an approximately orthonormal floating-point transform.
            self.arc_speed = (
                omega_absolute[0] * _sqrt(eigen_lower)[0] * abs(self.change),
                omega_absolute[1] * _sqrt(eigen_upper)[1] * abs(self.change),
            )
        else:
            points = [curve.start, curve.end]
            if curve.kind == "cubic":
                points = [curve.start, curve.data["control1"], curve.data["control2"], curve.end]
            self.controls = tuple(_world(profile, point) for point in points)

    def bounds(self, start, end, derivative=0):
        key = start, end, derivative
        if key in self.cache:
            return self.cache[key]
        parameters = self.start + self.change * start, self.start + self.change * end
        lo, hi = min(parameters), max(parameters)
        if self.curve.kind == "arc":
            angle = _imul(self.omega, (lo, hi))
            sine, cosine = _sin_cos(angle)
            # Known global trigonometric ranges tighten the outward Taylor bound.
            sine = max(-_ONE, sine[0]), min(_ONE, sine[1])
            cosine = max(-_ONE, cosine[0]), min(_ONE, cosine[1])
            radial = _ivadd(_ivmul(_ivec(self.a), cosine), _ivmul(_ivec(self.b), sine))
            if derivative == 0:
                result = _ivadd(_ivec(self.center), radial)
            elif derivative == 1:
                tangent = _ivadd(_ivmul(_ivec(self.a), _ineg(sine)), _ivmul(_ivec(self.b), cosine))
                result = _ivmul(tangent, _imul(self.omega, _point(self.change)))
            else:
                result = _ivmul(radial, _ineg(_imul(self.omega, self.omega)))
                result = _ivmul(result, _point(self.change * self.change))
        else:
            controls = self.controls
            for _ in range(derivative):
                degree = len(controls) - 1
                controls = tuple(_mul(_sub(b, a), degree) for a, b in zip(controls, controls[1:]))
                if not controls:
                    controls = ((_ZERO, _ZERO, _ZERO),)
                    break
            controls = _restrict(controls, lo, hi)
            result = tuple(
                (min(p[i] for p in controls), max(p[i] for p in controls)) for i in range(3)
            )
            result = _ivmul(result, _point(self.change**derivative))
        if derivative == 0:
            # Source APIs retain authored corner coordinates. Their accepted
            # circular endpoint consistency tolerance is NOT an identity.
            # Enclose both the analytic limit and the stored endpoint whenever
            # this closed interval reaches it (also needed by Sv/Jacobian).
            corners = []
            if lo == 0:
                corners.append(_world(self.profile, self.curve.start))
            if hi == 1:
                corners.append(_world(self.profile, self.curve.end))
            for corner in corners:
                result = tuple((min(a, x), max(b, x)) for (a, b), x in zip(result, corner))
        self.cache[key] = result
        return result

    def chosen_point(self, u):
        parameter = self.start + self.change * u
        if parameter == 0:
            return _world(self.profile, self.curve.start)
        if parameter == 1:
            return _world(self.profile, self.curve.end)
        return tuple((a + b) / 2 for a, b in self.bounds(u, u))


class _Patch:
    def __init__(self, first, second, reference):
        a = next(c for c in first.curves if c.segment_id == reference.first_segment_id)
        b = next(c for c in second.curves if c.segment_id == reference.second_segment_id)
        self.first = _SourceCurve(first, a, reference.first_interval)
        self.second = _SourceCurve(second, b, reference.second_interval)
        self.source = {
            "first_profile_id": first.profile_id,
            "second_profile_id": second.profile_id,
            "first_segment_id": reference.first_segment_id,
            "second_segment_id": reference.second_segment_id,
            "first_parameter_interval": [int(x) for x in reference.first_interval],
            "second_parameter_interval": [int(x) for x in reference.second_interval],
        }
        self.kinds = a.kind, b.kind

    def node(self, u, v):
        analytic = _blend(self.first.bounds(u, u), self.second.bounds(u, u), v)
        chosen = _add(_mul(self.first.chosen_point(u), 1 - v), _mul(self.second.chosen_point(u), v))
        floats = [_float(x) for x in chosen]
        rounded = tuple(Fraction(x) for x in floats)
        # Covers both the analytic curve and authored corner at its stored
        # endpoint. No exact endpoint-on-circle identity is assumed from a float.
        error = max(_ivnorm(_ivsub(analytic, _ivec(rounded)))[1], _norm(_sub(chosen, rounded))[1])
        return (u, v), analytic, floats, rounded, error

    def derivatives(self, u0, u1, v0, v1):
        a, b = self.first.bounds(u0, u1), self.second.bounds(u0, u1)
        da, db = self.first.bounds(u0, u1, 1), self.second.bounds(u0, u1, 1)
        du = _blend_range(da, db, v0, v1)
        dv = _ivsub(b, a)
        return du, dv

    def position(self, u0, u1, v0, v1):
        muu = max(_ivnorm(curve.bounds(u0, u1, 2))[1] for curve in (self.first, self.second))
        muv = _ivnorm(_ivsub(self.second.bounds(u0, u1, 1), self.first.bounds(u0, u1, 1)))[1]
        return muu * (u1 - u0) ** 2 / 8, muv * (u1 - u0) * (v1 - v0) / 4

    def normal(self, u0, u1, v0, v1, rounded, scale):
        du, dv = self.derivatives(u0, u1, v0, v1)
        jacobian = _ivcross(du, dv)
        plane = _cross(_sub(rounded[1], rounded[0]), _sub(rounded[2], rounded[0]))
        plane_upper = _norm(plane)[1]
        minimum_dot = _ivdot(jacobian, plane)[0]
        if plane_upper <= 0 or minimum_dot <= 0:
            return None
        numerator = _ivnorm(_ivcross(jacobian, _ivec(plane)))[1]
        ratio = numerator / minimum_dot
        angle = (
            _ZERO
            if ratio == 0
            else _atan(ratio)[1]
            if ratio <= 1
            else _pi()[1] / 2 - _atan(1 / ratio)[0]
        )
        angle = min(Fraction(90), _upper(angle * 180 / _pi()[0]))
        regularity = minimum_dot / plane_upper
        if _lower(regularity * scale * scale) <= 0:
            return None
        return angle, regularity, plane

    def edge_lengths(self, uv, rounded, scale):
        (u0, v0), (u1, v1) = uv
        hu, hv = u1 - u0, v1 - v0
        boundary_curve = self.first if v0 == v1 == 0 else self.second if v0 == v1 == 1 else None
        if boundary_curve is not None and boundary_curve.curve.kind == "arc":
            derivative_low, derivative_high = (x * abs(hu) for x in boundary_curve.arc_speed)
        else:
            derivative_low = derivative_high = _ZERO
            for i in range(_EDGE_INTERVALS):
                t0, t1 = Fraction(i, _EDGE_INTERVALS), Fraction(i + 1, _EDGE_INTERVALS)
                us = u0 + hu * t0, u0 + hu * t1
                vs = v0 + hv * t0, v0 + hv * t1
                du, dv = self.derivatives(min(us), max(us), min(vs), max(vs))
                tangent = _ivadd(_ivmul(du, _point(hu)), _ivmul(dv, _point(hv)))
                low, high = _ivnorm(tangent)
                derivative_low += low / _EDGE_INTERVALS
                derivative_high += high / _EDGE_INTERVALS
        endpoints, reservation = [], _ZERO
        for u, v in uv:
            analytic = _blend(self.first.bounds(u, u), self.second.bounds(u, u), v)
            chosen = _add(
                _mul(self.first.chosen_point(u), 1 - v), _mul(self.second.chosen_point(u), v)
            )
            reservation += _ivnorm(_ivsub(analytic, _ivec(chosen)))[1]
            endpoints.append(analytic)
        chord = _ivnorm(_ivsub(endpoints[1], endpoints[0]))
        low = max(_ZERO, max(derivative_low, chord[0]) - reservation) * scale
        high = (derivative_high + reservation) * scale
        delivered = tuple(x * scale for x in _norm(_sub(rounded[1], rounded[0])))
        mismatch = max(abs(high - delivered[0]), abs(delivered[1] - low))
        return low, high, *delivered, mismatch


def _candidate(patches, nu, nv, closed, scale):
    triangles, edges, reports = [], {}, []
    deviation = model_deviation = rounding = max_angle = _ZERO
    minimum_regularity = minimum_model_regularity = None
    for pindex, patch in enumerate(patches):
        nodes = {
            (i, j): patch.node(Fraction(i, nu), Fraction(j, nv))
            for i in range(nu + 1)
            for j in range(nv + 1)
        }
        rounding = max(rounding, *(p[4] for p in nodes.values()))
        indices = []
        for i in range(nu):
            for j in range(nv):
                u0, u1, v0, v1 = (
                    Fraction(i, nu),
                    Fraction(i + 1, nu),
                    Fraction(j, nv),
                    Fraction(j + 1, nv),
                )
                curvature, bilinear = patch.position(u0, u1, v0, v1)
                keys = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
                for half in ((0, 1, 2), (0, 2, 3)):
                    selected = [nodes[keys[h]] for h in half]
                    normal = patch.normal(u0, u1, v0, v1, [p[3] for p in selected], scale)
                    if normal is None:
                        return None, "REGIONAL_REGULARITY_OR_DELIVERED_PLANE_UNRESOLVED"
                    angle, regularity, plane = normal
                    paper_regularity = _lower(regularity * scale * scale)
                    minimum_regularity = (
                        paper_regularity
                        if minimum_regularity is None
                        else min(minimum_regularity, paper_regularity)
                    )
                    minimum_model_regularity = (
                        regularity
                        if minimum_model_regularity is None
                        else min(minimum_model_regularity, regularity)
                    )
                    model_position = curvature + bilinear + max(p[4] for p in selected)
                    position = _upper(model_position * scale)
                    model_deviation, deviation = (
                        max(model_deviation, model_position),
                        max(deviation, position),
                    )
                    max_angle = max(max_angle, angle)
                    index = len(triangles)
                    indices.append(index)
                    triangle = {
                        "patch_index": pindex,
                        "parameter_vertices_exact": [[str(x) for x in p[0]] for p in selected],
                        "world_vertices_model_mm": [p[2] for p in selected],
                        "analytic_source_vertex_enclosures_model_mm_exact": [
                            [[str(x) for x in interval] for interval in p[1]] for p in selected
                        ],
                        "delivered_vertices_model_mm_exact": [
                            [str(x) for x in p[3]] for p in selected
                        ],
                        "position_error_bound_paper_mm_exact": str(position),
                        "position_error_bound_model_mm_exact": str(_upper(model_position)),
                        "source_interpolation_bound_model_mm_exact": str(_upper(curvature)),
                        "bilinear_triangulation_bound_model_mm_exact": str(_upper(bilinear)),
                        "normal_angle_bound_deg_exact": str(angle),
                        "regularity_lower_paper_mm2_exact": str(paper_regularity),
                        "delivered_plane_normal_exact": [str(x) for x in plane],
                    }
                    triangles.append(triangle)
                    for a, b in ((0, 1), (1, 2), (2, 0)):
                        ka, kb = keys[half[a]], keys[half[b]]
                        node_a = _node_key(pindex, *ka, nu, len(patches), closed)
                        node_b = _node_key(pindex, *kb, nu, len(patches), closed)
                        key = tuple(sorted((node_a, node_b)))
                        use = {
                            "triangle_index": index,
                            "patch_index": pindex,
                            "parameter_endpoints_exact": [
                                triangle["parameter_vertices_exact"][k] for k in (a, b)
                            ],
                        }
                        if key not in edges:
                            lengths = patch.edge_lengths(
                                (selected[a][0], selected[b][0]),
                                (selected[a][3], selected[b][3]),
                                scale,
                            )
                            edges[key] = {"uses": [], "lengths": lengths}
                        edges[key]["uses"].append(use)
        reports.append(
            {
                "source": patch.source,
                "source_curve_kinds": list(patch.kinds),
                "target_developability": "NOT_CLASSIFIED_BY_SEGMENTATION",
                "parameter_area_exact": "1",
                "triangle_indices": indices,
            }
        )
    records, boundary, max_difference, pairs = [], [_ZERO] * 4, _ZERO, 0
    for edge in edges.values():
        uses, lengths = edge["uses"], edge["lengths"]
        if len(uses) not in (1, 2):
            raise ValueError("Derived parameter edge incidence is invalid")
        if len(uses) == 2:
            pairs += 1
        else:
            boundary = [a + b for a, b in zip(boundary, lengths[:4])]
        low, high, delivered_low, delivered_high, difference = lengths
        max_difference = max(max_difference, difference)
        records.append(
            {
                "role": "PAIRED_ISLAND_CUT" if len(uses) == 2 else "SOURCE_BOUNDARY_CUT",
                "uses": uses,
                "source_length_lower_paper_mm_exact": str(_lower(low)),
                "source_length_upper_paper_mm_exact": str(_upper(high)),
                "delivered_length_lower_paper_mm_exact": str(_lower(delivered_low)),
                "delivered_length_upper_paper_mm_exact": str(_upper(delivered_high)),
                "absolute_length_difference_bound_paper_mm_exact": str(_upper(difference)),
            }
        )
    boundary_difference = max(abs(boundary[1] - boundary[2]), abs(boundary[3] - boundary[0]))
    return {
        "patches": reports,
        "triangles": triangles,
        "edges": records,
        "max_surface_deviation_paper_mm": _float_upper(deviation),
        "max_surface_deviation_paper_mm_exact": str(deviation),
        "max_surface_deviation_model_mm": _float_upper(_upper(model_deviation)),
        "max_surface_deviation_model_mm_exact": str(_upper(model_deviation)),
        "max_normal_angle_bound_deg": _float_upper(max_angle),
        "max_normal_angle_bound_deg_exact": str(max_angle),
        "regularity_lower_paper_mm2": _float_lower(minimum_regularity),
        "regularity_lower_paper_mm2_exact": str(minimum_regularity),
        "regularity_lower_model_mm2_exact": str(_lower(minimum_model_regularity)),
        "numerical_vertex_error_bound_paper_mm": _float_upper(_upper(rounding * scale)),
        "numerical_vertex_error_bound_model_mm": _float_upper(_upper(rounding)),
        "lengths": {
            "scope": "TRIANGLE_EDGES_VS_SAME_SOURCE_PARAMETER_PATHS_NOT_GEODESICS",
            "source_proof": (
                "Whole-interval derivative norm integration, boundary-arc Gram speed and "
                "analytic chord; endpoint-consistency reserve included"
            ),
            "integration_subintervals_per_edge": _EDGE_INTERVALS,
            "max_edge_absolute_difference_bound_paper_mm": _float_upper(_upper(max_difference)),
            "boundary_absolute_difference_bound_paper_mm": _float_upper(
                _upper(boundary_difference)
            ),
            "source_boundary_lower_paper_mm_exact": str(_lower(boundary[0])),
            "source_boundary_upper_paper_mm_exact": str(_upper(boundary[1])),
            "delivered_boundary_lower_paper_mm_exact": str(_lower(boundary[2])),
            "delivered_boundary_upper_paper_mm_exact": str(_upper(boundary[3])),
        },
        "counts": {
            "patches": len(patches),
            "cells": len(patches) * nu * nv,
            "triangles": len(triangles),
            "triangle_island_parts": len(triangles),
            "paired_cut_seams": pairs,
            "source_boundary_cut_segments": len(records) - pairs,
            "manufactured_triangle_cut_segments": 3 * len(triangles),
        },
    }, None


def _sources(first, second, correspondences, max_cells):
    for profile in (first, second):
        if (
            not isinstance(profile, LoftProfile)
            or not isinstance(profile.profile_id, str)
            or not profile.profile_id
            or not isinstance(profile.closed, bool)
        ):
            raise ValueError("Source profile identities and topology must be explicit")
        _profile(profile)
        if any(not isinstance(c.segment_id, str) or not c.segment_id for c in profile.curves):
            raise ValueError("Source segments need explicit string identities")
    if first.profile_id == second.profile_id:
        raise ValueError("Source profile identities must be distinct")
    if first.closed != second.closed:
        raise ValueError("Matched source profiles need consistent open/closed topology")
    if not isinstance(correspondences, (tuple, list)) or not 0 < len(correspondences) <= max_cells:
        raise ValueError("Source correspondence exceeds the bounded source budget")
    previous, endpoints, matched = None, [], [set(), set()]
    for reference in correspondences:
        if not isinstance(reference, LoftCorrespondence):
            raise ValueError("Source correspondence must be explicit")
        starts, ends = [], []
        for index, (profile, sid, interval) in enumerate(
            (
                (first, reference.first_segment_id, reference.first_interval),
                (second, reference.second_segment_id, reference.second_interval),
            )
        ):
            if (
                any(isinstance(x, bool) for x in interval)
                or tuple(interval) not in ((0, 1), (1, 0))
                or sid in matched[index]
            ):
                raise ValueError("Each full oriented source interval must occur exactly once")
            curve = next((c for c in profile.curves if c.segment_id == sid), None)
            if curve is None or curve.kind not in ("line", "arc", "cubic"):
                raise ValueError("Only LINE/ARC/CUBIC source curves have proved interval bounds")
            start, end = (curve.start, curve.end) if interval[0] == 0 else (curve.end, curve.start)
            starts.append(start)
            ends.append(end)
            matched[index].add(sid)
        if previous is not None and previous != starts:
            raise ValueError("Explicit source intervals do not form a continuous ordered profile")
        previous = ends
        endpoints.append((starts, ends))
    if any(
        ids != {c.segment_id for c in profile.curves}
        for ids, profile in zip(matched, (first, second))
    ):
        raise ValueError("Every declared source segment must be covered exactly once")
    if first.closed and endpoints[-1][1] != endpoints[0][0]:
        raise ValueError("The closed source seam does not close")
    return [_Patch(first, second, reference) for reference in correspondences]


def segment_curved_loft(
    first, second, correspondences, *, scale, max_deviation_mm, max_cells, max_depth
):
    """Implementation behind the unchanged public segment_ruled_loft dispatch."""
    examined, source = 0, {}
    try:
        for value in (scale, max_deviation_mm):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("Scale and deviation budget must be finite and positive")
        if (
            type(max_cells) is not int
            or max_cells < 1
            or type(max_depth) is not int
            or not 0 <= max_depth <= 32
        ):
            raise ValueError("Cell/depth budgets are invalid")
        patches = _sources(first, second, correspondences, max_cells)
        source = {
            "first_profile_id": first.profile_id,
            "second_profile_id": second.profile_id,
            "first_closed": first.closed,
            "second_closed": second.closed,
            "correspondences": [p.source for p in patches],
            "expected_first_segment_ids": [c.segment_id for c in first.curves],
            "expected_second_segment_ids": [c.segment_id for c in second.curves],
        }
        scale_q, budget = Fraction(scale), Fraction(max_deviation_mm)
        if budget < Fraction(1, 10**24):
            raise ValueError("Deviation budget is below the public rounding budget")
        nu = nv = 1
        reason = "No bounded candidate was produced"
        for depth in range(max_depth + 1):
            count = len(patches) * nu * nv
            if count > max_cells:
                raise ValueError("The bounded segmentation cell budget was exhausted: " + reason)
            examined += count
            position = (
                max(
                    sum(
                        patch.position(Fraction(i, nu), Fraction(i + 1, nu), _ZERO, Fraction(1, nv))
                    )
                    for patch in patches
                    for i in range(nu)
                )
                * scale_q
            )
            candidate = None
            if position <= budget:
                candidate, reason = _candidate(patches, nu, nv, first.closed, scale_q)
            else:
                reason = "Whole-interior curved interpolation exceeds the requested budget"
            if (
                candidate is not None
                and Fraction(candidate["max_surface_deviation_paper_mm_exact"]) <= budget
            ):
                candidate.update(
                    {
                        "status": "CERTIFIED",
                        "mode": "APPROXIMATE",
                        "segmentation_only": True,
                        "family": "INTERVAL_CURVED_RULED_TRIANGLE_ISLANDS",
                        "source": source,
                        "scale": scale,
                        "requested_deviation_budget_paper_mm": max_deviation_mm,
                        "subdivisions": {"u": nu, "v": nv, "refinement_rounds": depth},
                        "examined_cells": examined,
                        "proof": {
                            "position": (
                                "Whole face SAME-PARAMETER: Muu*hu^2/8 + Muv*hu*hv/4 + "
                                "delivered vertex enclosure error"
                            ),
                            "derivatives": (
                                "Exact restricted Bernstein hulls or rational Taylor trigonometric "
                                "intervals of actual world source curves"
                            ),
                            "normal": (
                                "Entire-cell interval Jacobian; positive dot against delivered "
                                "float plane and interval cross/atan bound"
                            ),
                            "length": (
                                "Source derivative norm interval integration and boundary-arc Gram "
                                "speed, not mesh-derived expectation"
                            ),
                            "endpoints": (
                                "Authored corner coordinates retained; analytic source endpoint "
                                "discrepancy is enclosed in values/Jacobian and vertex reservations"
                            ),
                            "coverage": (
                                "Complete oriented source segments and conforming dyadic parameter "
                                "triangles; no tessellation identity"
                            ),
                            "limits": (
                                "No trim holes, general intersections, topology proof, source area "
                                "distortion, practical assembly, UI or persistence"
                            ),
                        },
                        "global_embedding": "NOT_CHECKED",
                        "source_area_distortion": "NOT_CERTIFIED_BY_THIS_COMPONENT",
                        "physical_build": "NOT_VERIFIED",
                    }
                )
                return candidate
            if candidate is not None:
                reason = "DELIVERED_VERTEX_RESERVATION_EXCEEDS_BUDGET"
            if reason == "REGIONAL_REGULARITY_OR_DELIVERED_PLANE_UNRESOLVED" and nv < nu:
                nv *= 2
            else:
                nu *= 2
        raise ValueError("The bounded segmentation depth budget was exhausted: " + str(reason))
    except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError) as exc:
        return {
            "status": "UNRESOLVED",
            "mode": "UNRESOLVED",
            "segmentation_only": True,
            "message": str(exc),
            "source": source,
            "examined_cells": examined,
            "supported_source_kinds": ["line", "arc", "cubic"],
            "next_action": (
                "Edit source correspondence or choose a feasible explicit budget; "
                "the original target remains unchanged and is never marked EXACT"
            ),
            "physical_build": "NOT_VERIFIED",
        }
