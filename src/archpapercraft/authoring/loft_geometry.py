"""Bounded developments of explicitly matched, authored source curves.

EXACT describes the proved surface family, not zero numerical error. Every
polygonal representation carries separate position and boundary-length bounds.
No sampled zero determinant certifies a general loft. Inputs are never mutated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from .curves import _PI_LOWER, _PI_UPPER, Curve, _sqrt_bounds, certify_curve, derivative, evaluate


@dataclass(frozen=True)
class LoftProfile:
    curves: tuple[Curve, ...]
    origin: tuple = (0, 0, 0)
    u: tuple = (1, 0, 0)
    v: tuple = (0, 1, 0)
    profile_id: str = ""
    closed: bool = False

    @classmethod
    def from_profile(cls, profile):
        return cls(
            tuple(
                Curve(
                    tuple(profile.vertex(s.start_vertex_id).point),
                    tuple(profile.vertex(s.end_vertex_id).point),
                    s.kind,
                    s.data,
                    s.id,
                )
                for s in profile.segments
            ),
            tuple(profile.plane.origin),
            tuple(profile.plane.u),
            tuple(profile.plane.v),
            profile.id,
            profile.closed,
        )


@dataclass(frozen=True)
class LoftCorrespondence:
    first_segment_id: str
    second_segment_id: str
    first_interval: tuple = (0, 1)
    second_interval: tuple = (0, 1)


def _fraction_point(p):
    return tuple(Fraction(x) for x in p)


def _upper(value):
    return math.nextafter(float(value), math.inf)


def _norm_bounds(p):
    return _sqrt_bounds(sum(x * x for x in p))


def _controls(curve):
    if curve.kind == "cubic":
        return [curve.start, curve.data["control1"], curve.data["control2"], curve.end]
    return [curve.start, curve.end]


def _reverse(curve):
    data = dict(curve.data)
    if curve.kind == "arc":
        data["sweep_deg"] = -data["sweep_deg"]
    elif curve.kind == "cubic":
        data = {"control1": data["control2"], "control2": data["control1"]}
    return Curve(curve.end, curve.start, curve.kind, data, curve.segment_id)


def _profile(profile):
    arrays = [np.asarray(x, dtype=float) for x in (profile.origin, profile.u, profile.v)]
    if any(a.shape != (3,) or not np.isfinite(a).all() for a in arrays):
        raise ValueError("Profil potřebuje konečnou prostorovou pracovní rovinu.")
    origin, u, v = arrays
    if (
        abs(np.linalg.norm(u) - 1) > 1e-12
        or abs(np.linalg.norm(v) - 1) > 1e-12
        or abs(np.dot(u, v)) > 1e-12
    ):
        raise ValueError("Osy profilové roviny musí být kolmé a jednotkové.")
    ids = [c.segment_id for c in profile.curves]
    if not ids or any(not cid for cid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Každý zdrojový segment potřebuje vlastní jednoznačnou identitu.")
    return origin, u, v, np.cross(u, v)


def _pair(first, second, correspondence):
    a = {c.segment_id: c for c in first.curves}
    b = {c.segment_id: c for c in second.curves}
    output = []
    for reference in correspondence:
        x, y = a[reference.first_segment_id], b[reference.second_segment_id]
        if tuple(reference.first_interval) not in ((0, 1), (1, 0)) or tuple(
            reference.second_interval
        ) not in ((0, 1), (1, 0)):
            raise ValueError("Přesný režim zatím vyžaduje celé spárované segmenty.")
        output.append(
            (
                _reverse(x) if tuple(reference.first_interval) == (1, 0) else x,
                _reverse(y) if tuple(reference.second_interval) == (1, 0) else y,
                reference,
            )
        )
    if not output:
        raise ValueError("Vyberte explicitní korespondenci segmentů a začátek švu.")
    for p, q in zip(output, output[1:]):
        if p[0].end != q[0].start or p[1].end != q[1].start:
            raise ValueError("Spárované segmenty musí navazovat ve zvoleném směru švu.")
    if len({r.first_segment_id for _, _, r in output}) != len(output) or len(
        {r.second_segment_id for _, _, r in output}
    ) != len(output):
        raise ValueError("Korespondence nesmí opakovat tentýž materiálový interval.")
    return output


def _homothety(pairs):
    """Algebra of original binary source controls, never a sampled family fit."""
    source, target = [], []
    for a, b, _ in pairs:
        if a.kind != b.kind:
            return None
        if a.kind == "arc" and a.data["sweep_deg"] != b.data["sweep_deg"]:
            return None
        aa, bb = _controls(a), _controls(b)
        if a.kind == "arc":
            aa += [a.data["center"]]
            bb += [b.data["center"]]
        source += [_fraction_point(p) for p in aa]
        target += [_fraction_point(p) for p in bb]
    start, other = source[0], target[0]
    k = None
    for a, b in zip(source[1:], target[1:]):
        for axis in range(2):
            if a[axis] != start[axis]:
                k = (b[axis] - other[axis]) / (a[axis] - start[axis])
                break
        if k is not None:
            break
    if k is None:
        return None
    shift = tuple(other[i] - k * start[i] for i in range(2))
    if any(b[i] != k * a[i] + shift[i] for a, b in zip(source, target) for i in range(2)):
        return None
    return k, shift


def _regularity(curve):
    """Positive speed lower bound from Bernstein hulls on entire intervals."""
    if curve.kind == "line":
        return _norm_bounds(
            tuple(Fraction(b) - Fraction(a) for a, b in zip(curve.start, curve.end))
        )[0]
    if curve.kind == "arc":
        radius = _norm_bounds(
            tuple(Fraction(a) - Fraction(b) for a, b in zip(curve.start, curve.data["center"]))
        )[0]
        return max(
            0,
            math.nextafter(
                float(Fraction(radius) * _PI_LOWER * abs(Fraction(curve.data["sweep_deg"])) / 180),
                -math.inf,
            ),
        )
    controls = [_fraction_point(p) for p in _controls(curve)]
    velocities = [tuple(3 * (b - a) for a, b in zip(p, q)) for p, q in zip(controls, controls[1:])]
    pending, lower = [(velocities, 0)], math.inf
    while pending:
        values, depth = pending.pop()
        nearest = []
        for axis in range(2):
            lo, hi = min(p[axis] for p in values), max(p[axis] for p in values)
            nearest.append(lo if lo > 0 else hi if hi < 0 else Fraction(0))
        bound = _norm_bounds(nearest)[0]
        if bound > 0:
            lower = min(lower, bound)
            continue
        if depth >= 16:
            return 0.0
        a, b, c = values
        ab = tuple((x + y) / 2 for x, y in zip(a, b))
        bc = tuple((x + y) / 2 for x, y in zip(b, c))
        mid = tuple((x + y) / 2 for x, y in zip(ab, bc))
        if mid == (0, 0):
            return 0.0
        pending.extend([([a, ab, mid], depth + 1), ([mid, bc, c], depth + 1)])
    return lower


def _bounds(curve, center, h, scale):
    """Global Q,Q',Q'',Q''' norms; rational arithmetic on outward norm bounds."""

    def norm(p):
        return Fraction(_norm_bounds(p)[1])

    controls = [_fraction_point(p) for p in _controls(curve)]
    if curve.kind == "arc":
        origin = _fraction_point(curve.data["center"])
        radius = norm(tuple((a - b) * scale for a, b in zip(controls[0], origin)))
        q0 = norm((origin[0] * scale - center[0], origin[1] * scale - center[1], h)) + radius
        omega = _PI_UPPER * abs(Fraction(curve.data["sweep_deg"])) / 180
        return q0, radius * omega, radius * omega**2, radius * omega**3
    q0 = max(norm((p[0] * scale - center[0], p[1] * scale - center[1], h)) for p in controls)
    results = [q0]
    current = controls
    while len(current) > 1:
        degree = len(current) - 1
        current = [
            tuple(degree * (b - a) for a, b in zip(p, q)) for p, q in zip(current, current[1:])
        ]
        results.append(max(norm(tuple(x * scale for x in p)) for p in current))
    return tuple([*results, *([Fraction(0)] * (4 - len(results)))])


def _world(profile, curve, parameters):
    points = np.asarray([evaluate(curve, t) for t in parameters])
    return (
        np.asarray(profile.origin) + points[:, :1] * profile.u + points[:, 1:] * profile.v
    ).tolist()


def _patch(first, second, a, b, reference, parameters, flat_a, flat_b):
    ta, tb = reference.first_interval, reference.second_interval
    source_parameters = [
        [ta[0] + t * (ta[1] - ta[0]), tb[0] + t * (tb[1] - tb[0])] for t in parameters
    ]
    return {
        "first_profile_id": first.profile_id,
        "second_profile_id": second.profile_id,
        "first_segment_id": reference.first_segment_id,
        "second_segment_id": reference.second_segment_id,
        "first_parameter_interval": list(ta),
        "second_parameter_interval": list(tb),
        "parameters": list(parameters),
        "source_parameters": source_parameters,
        "first_start_tangent": list(derivative(a, 0)),
        "first_end_tangent": list(derivative(a, 1)),
        "world_first_model_mm": _world(first, a, parameters),
        "world_second_model_mm": _world(second, b, parameters),
        "flat_first_paper_mm": flat_a,
        "flat_second_paper_mm": flat_b,
        "flat_boundary_paper_mm": [*flat_a, *reversed(flat_b)],
        "interior_tessellation_role": "DISPLAY_ONLY_NOT_FOLD",
    }


def _negative(first, second, pairs):
    # A robust nonzero determinant at one point is a negative witness. Zeros
    # here never certify regularity or developability on any full interval.
    for a, b, reference in pairs:
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            p, q = np.asarray(_world(first, a, [t])[0]), np.asarray(_world(second, b, [t])[0])
            da, db = np.asarray(derivative(a, t)), np.asarray(derivative(b, t))
            da = da[0] * np.asarray(first.u) + da[1] * np.asarray(first.v)
            db = db[0] * np.asarray(second.u) + db[1] * np.asarray(second.v)
            d, dp = q - p, db - da
            determinant = float(np.dot(da, np.cross(d, dp)))
            size = max(1.0, float(np.linalg.norm(da) * np.linalg.norm(d) * np.linalg.norm(dp)))
            guard = 16384 * math.ulp(size)
            if abs(determinant) > guard:
                return {
                    "status": "REJECTED",
                    "family": "NONDEVELOPABLE",
                    "message": "Tyto nezávislé profily netvoří přesně rozvinutelný pás.",
                    "witness": {
                        "first_segment_id": reference.first_segment_id,
                        "second_segment_id": reference.second_segment_id,
                        "u": t,
                        "determinant": determinant,
                        "numerical_reserve": guard,
                    },
                }
    return {
        "status": "UNRESOLVED",
        "family": "UNPROVEN",
        "message": "Pro tuto korespondenci nebyla prokázána přesná rodina a regularita. "
        "Upravte profily nebo zvolte výslovnou segmentaci.",
    }


def flatten_loft(
    first, second, correspondence, *, scale=1.0, tolerance_mm=0.005, max_segments=16384
):
    """Return a detached JSON report; no schema, controller, mutation or UI.

    Whole matched source segments (including explicit reverse direction) are
    supported. A partial interval is preserved in a truthful UNRESOLVED result.
    Seams open at the first explicit correspondence boundary. Surface-local
    regularity is proved; caller still validates source profile topology and
    assembled intersections as for every other authoring construction.
    """
    try:
        if (
            isinstance(scale, bool)
            or not math.isfinite(scale)
            or scale <= 0
            or isinstance(tolerance_mm, bool)
            or not math.isfinite(tolerance_mm)
            or not 0 < tolerance_mm <= 0.01
            or type(max_segments) is not int
            or max_segments < 2
        ):
            raise ValueError("Měřítko a chybový rozpočet musí být kladné; nejvýše 0,01 mm.")
        oa, ua, va, normal = _profile(first)
        ob, ub, vb, _ = _profile(second)
        pairs = _pair(first, second, correspondence)
        if not np.array_equal(ua, ub) or not np.array_equal(va, vb):
            return _negative(first, second, pairs)
        family = _homothety(pairs)
        if family is None:
            return _negative(first, second, pairs)
        k, shift = family
        if k <= 0:
            return {
                "status": "REJECTED",
                "family": "SINGULAR_HOMOTHETY",
                "message": "Spárované generátory se zhroutí do jediného bodu.",
                "witness": {"v": float(1 / (1 - k))},
            }
        delta = ob - oa
        height = float(np.dot(delta, normal))
        shift = tuple(
            shift[i] + Fraction(float(np.dot(delta, axis))) for i, axis in enumerate((ua, va))
        )
        speed = [_regularity(a) for a, _, _ in pairs]
        if not all(s > 0 for s in speed):
            raise ValueError("Nenulová tečna nebyla prokázána na celém zdrojovém intervalu.")
        magnitude = max(
            1.0,
            *(
                abs(x) * scale
                for profile in (first, second)
                for c in profile.curves
                for p in _controls(c)
                for x in p
            ),
            *(abs(x) * scale for x in (*oa, *ob)),
        )
        frame_error = max(
            abs(float(np.dot(ua, ua)) - 1),
            abs(float(np.dot(va, va)) - 1),
            abs(float(np.dot(ua, va))),
        )
        guard = max(4096 * math.ulp(magnitude), 16 * frame_error * magnitude)
        if magnitude > 1e6 or guard * max_segments > tolerance_mm / 16:
            raise ValueError("Souřadnice překračují podporovanou přesnost rozvinu.")
        # Per-patch length deficit and angular-integration displacement each
        # consume at most one allocation. Sum <= tolerance/2 before numerical
        # reserves; _complete also checks the actual GLOBAL bound, never just
        # each leaf or patch. This is allocation, not a looser public tolerance.
        budget = tolerance_mm / (4 * len(pairs))
        if k == 1:
            if height == 0 or any(x != 0 for x in shift):
                raise ValueError("Podporovaná extruze potřebuje nenulovou normálovou hloubku.")
            patches, offset, total_gap, count, world_error = [], 0.0, 0.0, 0, 0.0
            for a, b, reference in pairs:
                certificate = certify_curve(
                    a,
                    chord_tolerance=budget / scale,
                    length_tolerance=budget / scale,
                    max_segments=max_segments - count,
                )
                if certificate.status != "CERTIFIED":
                    raise ValueError("Nebylo dosaženo meze obloukové délky extrudovaného profilu.")
                parameters = certificate.parameters
                lengths = [
                    math.dist(x, y) * scale
                    for x, y in zip(certificate.points, certificate.points[1:])
                ]
                coordinates = [offset]
                for distance in lengths:
                    coordinates.append(coordinates[-1] + distance)
                gap = max(0, certificate.length_upper * scale - math.fsum(lengths))
                total_gap += gap
                world_error = max(world_error, certificate.max_chord_deviation_bound * scale)
                count += len(lengths)
                flat_a = [[x, 0.0] for x in coordinates]
                flat_b = [[x, abs(height) * scale] for x in coordinates]
                patches.append(_patch(first, second, a, b, reference, parameters, flat_a, flat_b))
                offset = coordinates[-1]
            position = max(total_gap, world_error) + guard * count
            report = _report(
                "NORMAL_EXTRUSION",
                patches,
                position,
                position,
                min(speed) * abs(height) * scale**2,
                "d'=0; [integral |C'|, H v] preserves the first fundamental form; "
                "whole-curve rational chord/control-polygon length enclosures",
                guard,
            )
            return _complete(report, first, second, scale, tolerance_mm)
        if height == 0:
            report = _planar(first, second, pairs, k, shift, scale, budget, guard, max_segments)
        else:
            report = _cone(
                first, second, pairs, k, shift, height, speed, scale, budget, guard, max_segments
            )
        return _complete(report, first, second, scale, tolerance_mm)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {"status": "UNRESOLVED", "family": "UNPROVEN", "message": str(exc)}


def _report(family, patches, position, metric, regularity, proof, guard):
    for index, patch in enumerate(patches):
        if index == 0:
            patch["join_before_kind"] = "EXPLICIT_SEAM"
            continue
        before = np.asarray(patches[index - 1]["first_end_tangent"])
        after = np.asarray(patch["first_start_tangent"])
        before, after = before / np.linalg.norm(before), after / np.linalg.norm(after)
        patch["join_before_kind"] = (
            "SMOOTH_SOURCE_JOIN" if np.linalg.norm(before - after) < 1e-10 else "FOLD_CREASE"
        )
    return {
        "status": "EXACT",
        "family": family,
        "patches": patches,
        "representation_error_bound_paper_mm": position,
        "boundary_length_error_bound_paper_mm": metric,
        "regularity_lower_bound_paper_mm2": regularity * (1 - 1e-10),
        "analytic_metric_identity": proof,
        "numerical_guard_paper_mm": guard,
        "proof_scope": "DECLARED_REGULAR_PARAMETRIC_FAMILY_AND_BOUNDED_REPRESENTATION",
        "source_topology_scope": "CALLER_VALIDATES_PROFILE_TOPOLOGY_AND_ASSEMBLED_INTERSECTIONS",
        "seam": "FIRST_EXPLICIT_CORRESPONDENCE_BOUNDARY",
        "physical_build": "NOT_VERIFIED",
    }


def _complete(report, first, second, scale, tolerance):
    bounds = [
        report["representation_error_bound_paper_mm"],
        report["boundary_length_error_bound_paper_mm"],
    ]
    if any(not math.isfinite(x) or x < 0 or x > tolerance for x in bounds):
        raise ValueError("Celková reprezentační nebo délková mez překročila tiskový rozpočet.")
    regularity = report["regularity_lower_bound_paper_mm2"]
    if not math.isfinite(regularity) or regularity <= 0:
        raise ValueError("Kladná konečná mez regularity není v podporované přesnosti doložená.")
    report.update(
        scale=scale,
        requested_error_budget_paper_mm=tolerance,
        coverage={
            "first_profile_id": first.profile_id,
            "second_profile_id": second.profile_id,
            "expected_first_segment_ids": [c.segment_id for c in first.curves],
            "expected_second_segment_ids": [c.segment_id for c in second.curves],
            "matched_first_segment_ids": [p["first_segment_id"] for p in report["patches"]],
            "matched_second_segment_ids": [p["second_segment_id"] for p in report["patches"]],
            "first_closed": first.closed,
            "second_closed": second.closed,
            "scope": "EXPLICITLY_MATCHED_INTERVALS_ONLY; caller validates intended coverage",
        },
    )
    return report


def sample_loft(report, patch_index, u, v):
    """Evaluate the bounded representation at an explicit source parameter.

    No triangle index is used as source identity. Curved model/flat boundaries
    are interpolated between certified parameter nodes, with the report's
    global position bound. This is not an exact source-curve evaluator.
    """
    if report.get("status") != "EXACT" or any(
        isinstance(t, bool) or not math.isfinite(t) or not 0 <= t <= 1 for t in (u, v)
    ):
        raise ValueError("Mapování potřebuje ověřený report a parametry u,v v [0,1].")
    patch = report["patches"][patch_index]
    ts = patch["parameters"]
    index = min(len(ts) - 2, max(0, int(np.searchsorted(ts, u, side="right")) - 1))
    ratio = (u - ts[index]) / (ts[index + 1] - ts[index])

    def boundary(key):
        values = np.asarray(patch[key])
        return (1 - ratio) * values[index] + ratio * values[index + 1]

    world = (1 - v) * boundary("world_first_model_mm") + v * boundary("world_second_model_mm")
    flat = (1 - v) * boundary("flat_first_paper_mm") + v * boundary("flat_second_paper_mm")
    return {
        "world_model_mm": world.tolist(),
        "flat_paper_mm": flat.tolist(),
        "first_segment_id": patch["first_segment_id"],
        "second_segment_id": patch["second_segment_id"],
        "u": u,
        "v": v,
        "mode": "BOUNDED_PARAMETER_INTERPOLATION",
        "position_error_bound_paper_mm": report["representation_error_bound_paper_mm"],
    }


def _planar(first, second, pairs, k, shift, scale, budget, guard, max_segments):
    center = tuple(-x / (k - 1) for x in shift)
    if any(a.kind != "arc" or _fraction_point(a.data["center"]) != center for a, _, _ in pairs):
        raise ValueError("Rovinný přesný pás je doložen pro soustředné kruhové oblouky.")
    sweeps = [a.data["sweep_deg"] for a, _, _ in pairs]
    if not (all(x > 0 for x in sweeps) or all(x < 0 for x in sweeps)) or abs(sum(sweeps)) > 360:
        raise ValueError("Rovinný pás vyžaduje jednotný směr a nejvýše jednu otáčku.")
    patches, position, metric, count = [], 0.0, 0.0, 0
    for a, b, reference in pairs:
        certificate = certify_curve(
            a,
            chord_tolerance=budget / (scale * max(1, float(k))),
            length_tolerance=budget / (scale * max(1, float(k))),
            max_segments=max_segments - count,
        )
        if certificate.status != "CERTIFIED":
            raise ValueError("Rovinný pás překročil rozpočet reprezentace oblouků.")
        ts = certificate.parameters
        aa = [(np.asarray(evaluate(a, t)) * scale).tolist() for t in ts]
        bb = [
            (
                (np.asarray(evaluate(a, t)) * float(k) + np.asarray([float(x) for x in shift]))
                * scale
            ).tolist()
            for t in ts
        ]
        patches.append(_patch(first, second, a, b, reference, ts, aa, bb))
        position = max(position, certificate.max_chord_deviation_bound * scale * max(1, float(k)))
        metric += (certificate.length_upper - certificate.length_lower) * scale * max(1, float(k))
        count += len(ts) - 1
    radial = min(
        _norm_bounds(tuple(Fraction(x) - y for x, y in zip(a.start, center)))[0]
        for a, _, _ in pairs
    )
    lower = (
        min(1, float(k))
        * abs(float(k - 1))
        * radial**2
        * min(abs(math.radians(s)) for s in sweeps)
        * scale**2
    )
    return _report(
        "CONCENTRIC_PLANAR_ARC_BAND",
        patches,
        position + guard * count,
        metric + guard * count,
        lower,
        "Coplanar positive radial factors, monotone polar angle and nonzero radius; "
        "identity projection preserves metric and the unfilled inner region",
        guard,
    )


def _cone(first, second, pairs, k, shift, height, speed, scale, budget, guard, max_segments):
    scale_q = Fraction(scale)
    center = tuple(-x * scale_q / (k - 1) for x in shift)
    h = Fraction(height) * scale_q / (k - 1)
    rmin = abs(h)
    patches, theta_offset, theta_error, position, metric, count = [], 0.0, 0.0, 0.0, 0.0, 0
    max_factor = max(Fraction(1), k)
    for (a, b, reference), minimum_speed in zip(pairs, speed):
        q0, q1, q2, q3 = _bounds(a, center, h, scale_q)
        guard = max(guard, 4096 * math.ulp(max(1.0, float(q0))))
        vmin = Fraction(minimum_speed) * scale_q
        g0, g1, g2 = q0 * q1, q0 * q2, q1 * q2 + q0 * q3
        wmin = rmin * vmin
        w2 = g2 + g1**2 / wmin
        amin, d1, d2 = rmin**2, 2 * q0 * q1, 2 * (q1**2 + q0 * q2)
        fmax = g0 / amin
        f1 = g1 / amin + g0 * d1 / amin**2
        f2 = w2 / amin + 2 * g1 * d1 / amin**2 + g0 * (2 * d1**2 / amin**3 + d2 / amin**2)
        # X=s*r*exp(i theta); these are GLOBAL derivative bounds on [0,1].
        second_bound = max_factor * (q2 + q1**2 / rmin + q0 * fmax**2 + 2 * q1 * fmax + q0 * f1)
        min_flat_speed = min(Fraction(1), k) * vmin
        length_coefficient = second_bound**2 / (12 * min_flat_speed)
        n = max(
            2,
            math.ceil(math.sqrt(_upper(max_factor * q0 * f2 / (12 * Fraction(budget))))),
            math.ceil(math.sqrt(_upper(second_bound / (8 * Fraction(budget))))),
            math.ceil(math.sqrt(_upper(length_coefficient / Fraction(budget)))),
            math.ceil(_upper(2 * second_bound / min_flat_speed)),
        )
        if count + n > max_segments:
            raise ValueError("Homotetický rozvin překročil doložitelný rozpočet segmentů.")
        ts = np.linspace(0.0, 1.0, n + 1)
        points = np.asarray([evaluate(a, t) for t in ts]) * scale
        q = np.column_stack(
            (
                points[:, 0] - float(center[0]),
                points[:, 1] - float(center[1]),
                np.full(n + 1, float(h)),
            )
        )
        velocities = np.asarray([derivative(a, t) for t in ts]) * scale
        velocities = np.column_stack((velocities, np.zeros(n + 1)))
        radius = np.linalg.norm(q, axis=1)
        angular = np.linalg.norm(np.cross(q, velocities), axis=1) / radius**2
        increments = (angular[:-1] + angular[1:]) / (2 * n)
        theta = np.concatenate(([theta_offset], theta_offset + np.cumsum(increments)))
        local_theta_error = _upper(f2 / (12 * n * n)) + guard * n
        theta_error += local_theta_error
        exact_first = np.column_stack((radius * np.cos(theta), radius * np.sin(theta)))
        exact_second = float(k) * exact_first
        patch = _patch(
            first, second, a, b, reference, ts, exact_first.tolist(), exact_second.tolist()
        )
        patches.append(patch)
        theta_offset = float(theta[-1])
        count += n
        position = max(
            position,
            _upper(max_factor * q0) * theta_error + _upper(second_bound / (8 * n * n)) + guard * n,
        )
        metric += _upper(length_coefficient / (n * n) + max_factor * q0 * f2 / (12 * n * n))
    if theta_offset + theta_error >= math.tau:
        raise ValueError("Nepřekrývání celého kuželového rozvinu nebylo prokázáno do jedné otáčky.")
    if max(position, metric + guard * count) > budget * 4 * len(pairs):
        raise ValueError(
            "Certifikovaná reprezentační nebo délková mez překročila tiskový rozpočet."
        )
    result = _report(
        "POSITIVE_HOMOTHETIC_CONE",
        patches,
        position,
        metric + guard * count,
        min(1, float(k)) * abs(height) * min(speed) * scale**2,
        "d'=(k-1)C0'; H*min|C0'|>0; r=|Q|, theta'=|Q x Q'|/r^2. "
        "Trapezoid error <=sup|theta'''|/(12N^2), polyline error <=sup|X''|/(8N^2). "
        "Boundary-length deficit <=sup|X''|^2/(12 min|X'| N^2) when N>=2M/m.",
        guard,
    )
    result.update(
        homothety_factor=float(k),
        total_developed_angle_rad=theta_offset,
        angular_error_bound_rad=theta_error,
    )
    return result
