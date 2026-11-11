"""Analytic right-circular loft charts, native A/L and detached rim bindings.

Recognition is deliberately strict: exact rational orthonormal common bases,
coaxial centers and complete quarter/half-turn arcs with exact rotated ends.
Other author-created lofts keep the existing general solver, never an epsilon
cylinder classification. Display chords are separate from native arc proofs.
"""

from __future__ import annotations

import copy
import math
from fractions import Fraction as Q

import numpy as np

from .curve_area import _add, _div, _mul, _pi, _point, _sqrt
from .curve_topology import _endpoint_arc_node
from .loft_area import _sin_cos
from .loft_geometry import _complete, _pair, _patch, _report


def reverse_native_segment(segment):
    from .loft_curve_compaction import reverse_segment

    result = reverse_segment(segment)
    if result["kind"] == "arc":
        result["data"]["sweep"] ^= 1
    return result


def serialize_segments(segments):
    commands = [["M", *segments[0]["start"]]]
    for segment in segments:
        if segment["kind"] == "line":
            commands.append(["L", *segment["end"]])
        elif segment["kind"] == "arc":
            radius = segment["data"]["radius"]
            commands.append(["A", radius, radius, 0, 0, segment["data"]["sweep"], *segment["end"]])
        else:
            commands.append(["C", *segment["data"]["control1"],
                             *segment["data"]["control2"], *segment["end"]])
    if commands[-1][0] == "L" and commands[-1][1:] == commands[0][1:]:
        commands.pop()
    return [*commands, ["Z"]]


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _magnitude(interval):
    return max(abs(x) for x in interval)


def _mid(interval):
    return float(sum(interval) / 2)


def _upper(value):
    return 0.0 if not value else math.nextafter(float(value), math.inf)


def _record(interval):
    return {
        "lower_exact": str(interval[0]),
        "upper_exact": str(interval[1]),
        "lower": math.nextafter(float(interval[0]), -math.inf),
        "upper": math.nextafter(float(interval[1]), math.inf),
    }


def _exact_radius(curves):
    center = tuple(map(Q, curves[0].data["center"]))
    square = None
    for curve in curves:
        if curve.kind != "arc" or tuple(map(Q, curve.data["center"])) != center:
            return None
        sweep = Q(curve.data["sweep_deg"])
        if abs(sweep) not in (90, 180):
            return None
        start, end = (
            _sub(tuple(map(Q, curve.start)), center),
            _sub(tuple(map(Q, curve.end)), center),
        )
        rotated = start
        for _ in range(int(abs(sweep) / 90)):
            rotated = (-rotated[1], rotated[0]) if sweep > 0 else (rotated[1], -rotated[0])
        if rotated != end or (square is not None and _dot(start, start) != square):
            return None
        square = _dot(start, start)
    if not square:
        return None
    numerator, denominator = math.isqrt(square.numerator), math.isqrt(square.denominator)
    if numerator * numerator != square.numerator or denominator * denominator != square.denominator:
        return None
    return center, Q(numerator, denominator)


def recognize(first, second, references, *, scale):
    """Return exact source facts or None; no approximate geometric recognition."""
    if not first.closed or not second.closed or not first.curves or not second.curves:
        return None
    if any(c.kind != "arc" for p in (first, second) for c in p.curves):
        return None
    ua, va = tuple(map(Q, first.u)), tuple(map(Q, first.v))
    if (
        tuple(map(Q, second.u)) != ua
        or tuple(map(Q, second.v)) != va
        or _dot(ua, ua) != 1
        or _dot(va, va) != 1
        or _dot(ua, va) != 0
    ):
        return None
    pairs = _pair(first, second, references)
    if len(pairs) != len(first.curves) or len(pairs) != len(second.curves):
        return None
    circles = [_exact_radius([pair[index] for pair in pairs]) for index in (0, 1)]
    if any(circle is None for circle in circles):
        return None
    centers = []
    for profile, (center, _) in zip((first, second), circles):
        centers.append(
            tuple(Q(o) + center[0] * u + center[1] * v for o, u, v in zip(profile.origin, ua, va))
        )
    normal = _cross(ua, va)
    delta = _sub(centers[1], centers[0])
    height = _dot(delta, normal)
    if not height or _dot(delta, ua) or _dot(delta, va):
        return None
    total, sign = Q(0), 1 if pairs[0][0].data["sweep_deg"] > 0 else -1
    r0, r1 = circles[0][1], circles[1][1]
    for index, (a, b, _) in enumerate(pairs):
        sweep = Q(a.data["sweep_deg"])
        if sweep * sign <= 0 or sweep != Q(b.data["sweep_deg"]):
            return None
        if a.end != pairs[(index + 1) % len(pairs)][0].start:
            return None
        if b.end != pairs[(index + 1) % len(pairs)][1].start:
            return None
        if tuple(x * r1 for x in _sub(tuple(map(Q, a.start)), circles[0][0])) != tuple(
            x * r0 for x in _sub(tuple(map(Q, b.start)), circles[1][0])
        ):
            return None
        total += abs(sweep)
    if total != 360:
        return None
    scale = Q(scale)
    radii = (r0 * scale, r1 * scale)
    slant = _sqrt((radii[1] - radii[0]) ** 2 + (height * scale) ** 2)
    return {
        "pairs": pairs,
        "radii": radii,
        "slant": slant,
        "centers": centers,
        "normal": normal,
        "height": height,
        "walk_sign": sign,
        "source_radius_model": (r0, r1),
    }


def transform_native_commands(commands, rotation, origin):
    """Rigid circular A transform; flags/radii are never mistaken for points."""
    rotation, origin = np.asarray(rotation), np.asarray(origin)
    reflected = np.linalg.det(rotation) < 0
    result = []
    for command in commands:
        op = command[0]
        if op == "Z":
            result.append(["Z"])
            continue
        if op == "A":
            if command[1] != command[2] or command[3] != 0:
                raise ValueError("The shell adapter transforms circular native A only.")
            end = (np.asarray(command[-2:]) - origin) @ rotation.T
            result.append(["A", *command[1:5], int(command[5]) ^ int(reflected), *end.tolist()])
        else:
            points = np.asarray([command[i : i + 2] for i in range(1, len(command), 2)]) - origin
            result.append([op, *(x for point in points @ rotation.T for x in point)])
    return result


def certify_source_area(first, second, references, *, scale):
    """Independent intrinsic formula, reading no flat/native manufactured data."""
    from .loft_area import _coverage

    source = recognize(first, second, references, scale=scale)
    if source is None:
        return None
    area = _mul(_pi(), _mul(_point(sum(source["radii"])), source["slant"]))
    return {
        "status": "CERTIFIED",
        "family": "RIGHT_CIRCULAR_SOURCE",
        "area_lower_exact": str(area[0]),
        "area_upper_exact": str(area[1]),
        "area_lower_paper_mm2": math.nextafter(float(area[0]), -math.inf),
        "area_upper_paper_mm2": math.nextafter(float(area[1]), math.inf),
        "coverage": _coverage(first, second, references),
        "proof": {
            "area_identity": "pi*(R0+R1)*sqrt((R1-R0)^2+H^2)",
            "source": "ACTUAL_BINARY_RATIONAL_RADII_HEIGHT_AND_SCALE; EXACT_COMMON_UNIT_BASIS",
            "rounding": "OUTWARD_RATIONAL_PI_AND_SQRT; NO_FLAT_CACHE_INPUT",
        },
    }


def _sum_intervals(values):
    total = _point(Q(0))
    for value in values:
        total = _add(total, value)
    return total


def rim_world_intervals(profile, local, radius_model, matrix, *, source_turn, walk_sign, axis_sign):
    """Analytic source frame enclosures; no samples or libm enter this proof."""
    u, v = tuple(map(Q, profile.plane.u)), tuple(map(Q, profile.plane.v))
    normal = _cross(u, v)
    center = tuple(map(Q, profile.segments[0].data["center"]))
    dx, dy = Q(local[0])-center[0], Q(local[1])-center[1]
    radial = tuple((a*dx+b*dy)/radius_model for a, b in zip(u, v))
    tangent = tuple(walk_sign*x for x in _cross(normal, radial))
    sine, cosine = _sin_cos(_mul(_pi(), _point(2*Q(source_turn))))
    radius_vector = tuple(_add(_mul(_point(a), cosine), _mul(_point(b), sine))
                          for a, b in zip(radial, tangent))
    outward = tuple(axis_sign*x for x in normal)
    out_tangent = (
        _add(_mul(_point(outward[1]), radius_vector[2]),
             _mul(_point(-outward[2]), radius_vector[1])),
        _add(_mul(_point(outward[2]), radius_vector[0]),
             _mul(_point(-outward[0]), radius_vector[2])),
        _add(_mul(_point(outward[0]), radius_vector[1]),
             _mul(_point(-outward[1]), radius_vector[0])))
    rotation = [[Q(float(matrix[i, j])) for j in range(3)] for i in range(3)]

    def mapped(vector):
        return [_sum_intervals([_mul(_point(c), x) for c, x in zip(row, vector)])
                for row in rotation]

    model_center = [Q(o)+a*center[0]+b*center[1] for o, a, b in zip(profile.plane.origin, u, v)]
    world_center = [_point(sum(c*x for c, x in zip(row, model_center))+Q(float(matrix[i, 3])))
                    for i, row in enumerate(rotation)]
    gram_error = sum(abs(sum(rotation[k][i]*rotation[k][j] for k in range(3))-
                         (1 if i == j else 0)) for i in range(3) for j in range(3))
    return {"center_model_mm": [_record(iv) for iv in world_center],
            "radial": [_record(iv) for iv in mapped(radius_vector)],
            "tangent": [_record(iv) for iv in mapped(out_tangent)],
            "outward_z": [_record(iv) for iv in mapped(tuple(_point(x) for x in outward))],
            "source_pose_gram_operator_bound_exact": str(gram_error),
            "proof": "EXACT_SOURCE_UNIT_BASIS; RATIONAL_PI_TAYLOR_WHOLE_ANGLE; ACTUAL_BINARY_POSE"}


def _native_arc_length(start, end, radius):
    from .curve_area import _atan

    chord2 = sum((Q(x) - Q(y)) ** 2 for x, y in zip(start, end))
    if chord2 <= 0 or chord2 >= 4 * radius * radius:
        raise ValueError("Native shell arcs must be strictly minor and nonzero.")
    quotient = _div(_sqrt(chord2), _add(_point(2 * radius), _sqrt(4 * radius * radius - chord2)))
    angle = (4 * _atan(quotient[0])[0], 4 * _atan(quotient[1])[1])
    return _mul(_point(radius), angle)


def build(first, second, references, *, scale, tolerance_mm, max_segments):
    """Produce source-bound analytic charts, or None for the general pipeline."""
    source = recognize(first, second, references, scale=scale)
    if source is None:
        return None
    radii, slant = source["radii"], source["slant"]
    cylinder = radii[0] == radii[1]  # Exact equality, never an epsilon branch.
    dr = radii[0] - radii[1]
    native_radii = tuple(Q(float(r)) for r in radii)
    kappa_source = _point(Q(0)) if cylinder else _div(_point(dr), slant)
    signed_flat = (
        None
        if cylinder
        else tuple(Q(_mid(_div(_mul(_point(r), slant), _point(dr)))) for r in radii)
    )
    if any(r <= 0 for r in native_radii) or signed_flat and any(r == 0 for r in signed_flat):
        return None
    kappa = Q(0) if cylinder else native_radii[0] / signed_flat[0]
    if not cylinder and abs(kappa) >= 1:
        return None
    # Couple the native rim radii to the ONE actual sector angle. Independent
    # binary rounding must not give the second rim a different angular speed.
    if not cylinder:
        native_radii = (native_radii[0], signed_flat[1]*kappa)
    depth = Q(_mid(slant)) if cylinder else signed_flat[0] - signed_flat[1]
    pi = _pi()

    def flat(side, theta):
        if cylinder:
            return (_mul(_point(native_radii[0]), theta), _point(Q(0) if side == 0 else -depth))
        sine, cosine = _sin_cos(_mul(_point(kappa), theta))
        return (
            _mul(_point(signed_flat[side]), sine),
            _add(
                _mul(_point(signed_flat[side]), _add(cosine, _point(Q(-1)))),
                _point(Q(0) if side == 0 else signed_flat[1] - signed_flat[0]),
            ),
        )

    position, length, derivative = Q(0), [Q(0), Q(0)], [Q(0), Q(0)]
    patches, native_patches, offset, count = [], [], Q(0), 0
    magnitude = max(Q(1), *radii, abs(depth), *(abs(x) for x in signed_flat or ()),
                    *(abs(x)*Q(scale)+r for center, r in zip(source["centers"], radii)
                      for x in center))
    guard = Q(4096 * math.ulp(float(magnitude)))
    if guard >= Q(tolerance_mm) / 16:
        return None
    for index, (a, b, reference) in enumerate(source["pairs"]):
        sweep = abs(Q(a.data["sweep_deg"]))
        angle = _mul(pi, _point(sweep / 180))
        bound = max(radii) * angle[1] ** 2
        steps = max(2, math.ceil(math.sqrt(float(bound / (8 * Q(tolerance_mm / 8))))))
        count += steps
        if count > max_segments:
            return None
        parameters = [i / steps for i in range(steps + 1)]
        flat_sides = []
        for side in (0, 1):
            flat_sides.append(
                [
                    [_mid(v) for v in flat(side, _mul(pi, _point((offset + sweep * Q(t)) / 180)))]
                    for t in parameters
                ]
            )
        patch = _patch(first, second, a, b, reference, parameters, *flat_sides)
        patch["join_before_kind"] = "SMOOTH_CIRCULAR_RIM_CONTINUATION"
        patches.append(patch)
        native_patch = {
            "patch_index": index,
            "join_before_kind": patch["join_before_kind"],
            "source_patch_boundary_policy": "ANALYTIC_SMOOTH_CIRCLE_NOT_SCORE_FOLD",
        }
        for side, label in ((0, "first"), (1, "second")):
            segments = []
            native_steps = int(sweep / 90)
            for j in range(native_steps):
                ta, tb = Q(j, native_steps), Q(j + 1, native_steps)
                angles = [_mul(pi, _point((offset + sweep * t) / 180)) for t in (ta, tb)]
                enclosures = [flat(side, angle) for angle in angles]
                ends = [[_mid(v) for v in point] for point in enclosures]
                source_ref = {
                    "profile_id": first.profile_id if side == 0 else second.profile_id,
                    "segment_id": a.segment_id if side == 0 else b.segment_id,
                    "feature_id": None,
                    "parameter_interval": [
                        reference.first_interval[0]
                        + float(ta) * (reference.first_interval[1] - reference.first_interval[0]),
                        reference.first_interval[0]
                        + float(tb) * (reference.first_interval[1] - reference.first_interval[0]),
                    ],
                    "loft_parameter_interval": list(map(float, (ta, tb))),
                    "direction": reference.first_interval[1] - reference.first_interval[0],
                }
                interval = reference.first_interval if side == 0 else reference.second_interval
                source_ref["parameter_interval"] = [
                    interval[0] + float(t) * (interval[1] - interval[0]) for t in (ta, tb)
                ]
                source_ref["direction"] = interval[1] - interval[0]
                segment = {
                    "kind": "line" if cylinder else "arc",
                    "start": ends[0],
                    "end": ends[1],
                    "data": {},
                    "source": source_ref,
                }
                endpoint_error = max(
                    sum(_magnitude((Q(v) - iv[1], Q(v) - iv[0])) for v, iv in zip(point, enclosure))
                    for point, enclosure in zip(ends, enclosures)
                )
                target = _mul(_point(radii[side]), _mul(pi, _point(sweep / (180 * native_steps))))
                if cylinder:
                    actual_length = _sqrt(sum((Q(x) - Q(y)) ** 2 for x, y in zip(*ends)))
                    local_position = endpoint_error + 2 * pi[1] * abs(native_radii[0] - radii[0])
                    local_position += _magnitude((depth - slant[1], depth - slant[0]))
                    speed = _div(actual_length, _mul(pi, _point(sweep/(180*native_steps))))
                    d_error = _magnitude((speed[0]-radii[side], speed[1]-radii[side]))
                else:
                    radius = abs(signed_flat[side])
                    segment["data"] = {"radius": float(radius), "sweep": int(kappa < 0)}
                    node = _endpoint_arc_node(
                        None, tuple(map(Q, ends[0])), tuple(map(Q, ends[1])), radius, int(kappa < 0)
                    )
                    center_error = sum(
                        _magnitude((v[0] - expected, v[1] - expected))
                        for v, expected in zip(node.native["center"], (0, -signed_flat[0]))
                    )
                    if endpoint_error + center_error >= radius / 4:
                        return None
                    exact_radii = [_div(_mul(_point(r), slant), _point(dr)) for r in radii]
                    radial_error = _magnitude(
                        (
                            signed_flat[side] - exact_radii[side][1],
                            signed_flat[side] - exact_radii[side][0],
                        )
                    )
                    origin_error = _magnitude(
                        (signed_flat[0] - exact_radii[0][1], signed_flat[0] - exact_radii[0][0])
                    )
                    phase_error = _magnitude((kappa - kappa_source[1], kappa - kappa_source[0]))
                    local_position = (
                        radial_error
                        + origin_error
                        + radius * 2 * pi[1] * phase_error
                        + center_error
                        + 4 * (endpoint_error + center_error)
                    )
                    actual_length = _native_arc_length(*ends, radius)
                    speed = _div(actual_length, _mul(pi, _point(sweep/(180*native_steps))))
                    ideal_speed = signed_flat[side]*kappa
                    d_error = (abs(ideal_speed-radii[side])+
                               max(ideal_speed, radii[side])*2*pi[1]*phase_error+
                               _magnitude((speed[0]-ideal_speed, speed[1]-ideal_speed))+
                               max(speed[1], ideal_speed)*2*(endpoint_error+center_error)/radius)
                position = max(position, local_position)
                derivative[side] = max(derivative[side], d_error)
                length[side] += max(
                    abs(actual_length[0] - target[1]), abs(actual_length[1] - target[0])
                )
                segments.append(segment)
            native_patch[label] = {
                "segments": segments,
                "representation": "ANALYTIC_NATIVE_L" if cylinder else "ANALYTIC_NATIVE_A",
            }
        native_patches.append(native_patch)
        offset += sweep
    position += guard
    length = [value + guard for value in length]
    if max(position, *length) >= Q("0.008"):
        return None
    display = float(Q(tolerance_mm) / 8 + position)
    if display > tolerance_mm:
        return None
    solver = _complete(
        _report(
            "NORMAL_EXTRUSION" if cylinder else "POSITIVE_HOMOTHETIC_CONE",
            patches,
            display,
            display,
            float(min(radii) * abs(source["height"]) * Q(scale)),
            "EXACT_COAXIAL_COMPLETE_CIRCLES; analytic arc/line isometry; separate display chords",
            float(guard),
        ),
        first,
        second,
        scale,
        tolerance_mm,
    )
    from .loft_curves import _ruling

    for patch, native_patch in zip(patches, native_patches):
        a, b = native_patch["first"]["segments"], native_patch["second"]["segments"]
        native_patch["closed_boundary_segments"] = [
            *copy.deepcopy(a),
            _ruling(a[-1]["end"], b[-1]["end"], patch, 1, None),
            *[reverse_native_segment(s) for s in reversed(b)],
            _ruling(b[0]["start"], a[0]["start"], patch, 0, None, reverse=True),
        ]
        native_patch["closed_boundary_commands"] = serialize_segments(
            native_patch["closed_boundary_segments"])
        native_patch["closed_boundary_topology"] = "CALLER_VALIDATES_ACTUAL_FULL_REGION"
    shell = {
        "family": "RIGHT_CIRCULAR_CYLINDER" if cylinder else "RIGHT_CIRCULAR_FRUSTUM",
        "source_radius_bounds": [_record(_point(r)) for r in radii],
        "source_slant_bounds": _record(slant),
        "source_first_kappa_bounds": _record(kappa_source),
        "native_radius_exact": [str(r) for r in native_radii],
        "native_signed_flat_radius_exact": None if cylinder else list(map(str, signed_flat)),
        "native_depth_exact": str(depth),
        "walk_sign": source["walk_sign"],
        "height_sign": 1 if source["height"] > 0 else -1,
        "world_centers_model_mm": [list(map(float, c)) for c in source["centers"]],
        "world_axis": list(
            map(float, (x * (1 if source["height"] > 0 else -1) for x in source["normal"]))
        ),
        "conditions": "EXACT_RATIONAL_COAXIAL_ORTHONORMAL_BASES_AND_QUARTER_HALF_TURNS",
        "native_position_bound_exact": str(position),
        "native_length_bound_exact": list(map(str, length)),
        "native_rim_tangent_error_mm_per_source_radian_exact": [str(d+guard) for d in derivative],
        "native_radius_error_bound_exact": [str(abs(a-b)) for a, b in zip(native_radii, radii)],
        "native_reference_angular_correspondence": "COMMON_NATIVE_KAPPA_FULL_SOURCE_CIRCLE_ANGLE",
        "derivative_scope": "RIM_TANGENT_ONLY_NOT_A_COLLAR_JACOBIAN_OR_STRAIN_CERTIFICATE",
    }
    native = {
        "status": "CERTIFIED_REPRESENTATION_ONLY",
        "patches": native_patches,
        "source_coverage": solver["coverage"],
        "circular_shell": shell,
        "position_error_bound_paper_mm": _upper(position),
        "boundary_length_error_bound_paper_mm": _upper(max(length)),
        "both_profile_boundaries_length_error_bound_paper_mm": _upper(sum(length)),
        "proof_scope": "DIRECT_ANALYTIC_CIRCULAR_SOURCE_TO_ACTUAL_NATIVE_A_L",
        "same_parameter_position_proof": (
            "SOURCE_RADII_PHASE_INTERVALS_PLUS_NATIVE_ENDPOINT_CENTER_BOUND"),
        "length_proof": "GLOBAL_SUM_SOURCE_ARC_LENGTH_VS_ACTUAL_ENDPOINT_A_OR_L_INTERVALS",
        "serialized_output": "CALLER_MUST_VERIFY",
        "physical_build": "NOT_VERIFIED",
    }
    return solver, native
