"""Canonical native body/tab material union, with source-bound shared bases.

No sampled polygon is used to approve a union. The manufactured outer boundary
uses original A/L rim fragments and the exact supplied straight tab sides;
shared bases occur once as semantic guides, never as a second cut.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from fractions import Fraction as Q

import numpy as np

from .circular_shell import _native_arc_length, _sum_intervals
from .curve_area import _add, _mul, _neg, _pi, _point, native_region_area_bounds
from .curve_topology import _endpoint_arc_node, certify_native_region_topology
from .curved_tabs import Rim, Tab, _geometry
from .curved_tabs_chart import certify_native_tab_chart
from .errors import ValidationError
from .geometry import material_polygon
from .loft_area import _sin_cos

CONTRACT = "SOURCE_BOUND_CIRCULAR_BODY_AND_CURVED_TAB_UNION_V1"
MAX_SLOTS = 1000
MAX_NODES = 400000
PACKET_POSITION_LIMIT = Q(1, 1000000)


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _q(value):
    if isinstance(value, bool):
        raise ValidationError("Boolean is not a material coordinate or interval.")
    try:
        result = Q(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError("Native material needs finite exact numbers.") from exc
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > 16384:
        raise ValidationError("Native material exhausted its arithmetic input budget.")
    return result


def _commands(value):
    if not isinstance(value, (tuple, list)) or not value:
        raise ValidationError("A complete actual native path is required.")
    counts = {"M": 2, "L": 2, "A": 7, "Z": 0}
    result = []
    for command in value:
        if (
            not isinstance(command, (tuple, list))
            or not command
            or command[0] not in counts
            or len(command) != counts[command[0]] + 1
        ):
            raise ValidationError(
                "Only actual native circular A and straight L material is supported."
            )
        values = []
        for number in command[1:]:
            if type(number) not in (int, float) or not math.isfinite(number):
                raise ValidationError("Actual material packets must retain finite binary operands.")
            values.append(number)
        if command[0] == "A" and (
            values[0] != values[1]
            or values[0] <= 0
            or values[2:4] != [0, 0]
            or values[4] not in (0, 1)
        ):
            raise ValidationError("A material base must be an oriented minor circular A.")
        result.append([command[0], *values])
    return result


def _interval(value):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError("Complete outward source interval bounds are required.")
    low, high = map(_q, value)
    if low > high:
        raise ValidationError("Source interval endpoints are reversed.")
    return low, high


def _source_inputs(project, sid):
    method = getattr(project, "curved_connector_inputs", None)
    result = method(sid) if method is not None else {}
    if not isinstance(result, dict):
        raise ValidationError("Curved material requires actual source registry inputs.")
    _digest(result)
    return result


def _source_coverage(project, rim, lower, upper):
    """Exact identity/coverage attribution, never an endpoint coordinate oracle."""
    profile = project.profiles[rim["profile_id"]]
    cursor, result = Q(0), []
    for source in rim["source_intervals"]:
        a, b = map(_q, source["parameter_interval"])
        segment = profile.segment(source["segment_id"])
        span = abs(_q(segment.data["sweep_deg"]) * (b - a)) / 360
        if span <= 0:
            raise ValidationError("A circular source interval has no positive coverage.")
        lo, hi = max(lower, cursor), min(upper, cursor + span)
        if lo < hi:
            result.append(
                {
                    **copy.deepcopy(source),
                    "source_turn_coverage_exact": [str(lo), str(hi)],
                    "parameter_coverage_exact": [
                        str(a + (b - a) * (lo - cursor) / span),
                        str(a + (b - a) * (hi - cursor) / span),
                    ],
                    "coverage_kind": "OUTWARD_ENCLOSURE_NOT_AN_EXACT_IRRATIONAL_ENDPOINT",
                }
            )
        cursor += span
    if cursor != 1 or not result:
        raise ValidationError("A circular source rim lacks complete identity coverage.")
    return result


def _area_source(body, extras):
    low = Q(body["area_lower_exact"]) + sum(x[0] for x in extras)
    high = Q(body["area_upper_exact"]) + sum(x[1] for x in extras)
    return {
        "status": "CERTIFIED",
        "family": "SOURCE_BODY_PLUS_AUTHORED_CURVED_TAB_MATERIAL",
        "area_lower_exact": str(low),
        "area_upper_exact": str(high),
        "area_lower_paper_mm2": math.nextafter(float(low), -math.inf),
        "area_upper_paper_mm2": math.nextafter(float(high), math.inf),
        "coverage": copy.deepcopy(body["coverage"]),
        "proof": "INDEPENDENT_INTRINSIC_BODY_PLUS_PURE_LOCAL_NATIVE_TAB_AREA_INTERVALS",
    }


def _bounds_error(actual, interval):
    return max(abs(actual - interval[0]), abs(actual - interval[1]))


def _norm_bounds(vector):
    # L1 encloses Euclidean norm without a sampled maximum or float conversion.
    return sum(max(abs(a), abs(b)) for a, b in vector)


def _reference_homogeneous(result, side, turns, rotation, origin):
    shell = result["representation"]["circular_shell"]
    theta = [_mul(_pi(), (2 * t[0], 2 * t[1])) for t in turns]
    signed = shell["native_signed_flat_radius_exact"]
    index = 0 if side == "first" else 1
    if signed is None:
        radius = Q(shell["native_radius_exact"][index])
        y = Q(0) if not index else -Q(shell["native_depth_exact"])
        points = [(_mul(_point(radius), t), _point(y)) for t in theta]
        controls = [(*points[0], _point(Q(1))), (*points[1], _point(Q(1)))]
    else:
        radii = list(map(Q, signed))
        kappa = Q(shell["native_radius_exact"][0]) / radii[0]
        phases = [_mul(_point(kappa), t) for t in theta]
        mid = _mul(_add(*phases), _point(Q(1, 2)))
        delta = _mul(_add(phases[1], _neg(phases[0])), _point(Q(1, 2)))
        weight = _sin_cos(delta)[1]
        if weight[0] <= 0:
            raise ValidationError("Native trim exhausted the strictly minor-arc domain.")
        endpoints = []
        for phase in phases:
            sine, cosine = _sin_cos(phase)
            endpoints.append(
                (
                    _mul(_point(radii[index]), sine),
                    _add(_mul(_point(radii[index]), cosine), _point(-radii[0])),
                )
            )
        sine, cosine = _sin_cos(mid)
        middle = (
            _mul(_point(radii[index]), sine),
            _add(_mul(_point(radii[index]), cosine), _mul(_point(-radii[0]), weight)),
        )
        controls = [(*endpoints[0], _point(Q(1))), (*middle, weight), (*endpoints[1], _point(Q(1)))]
    transformed = []
    for x, y, w in controls:
        point = [
            _add(x, _mul(_point(-Q(float(origin[0]))), w)),
            _add(y, _mul(_point(-Q(float(origin[1]))), w)),
        ]
        transformed.append(
            tuple(
                _sum_intervals([_mul(_point(Q(float(c))), p) for c, p in zip(row, point)])
                for row in rotation
            )
            + (w,)
        )
    return transformed


def _fragment_error(result, side, source_bounds, start, command, rotation, origin):
    # The reference endpoint intervals remain intervals: no midpoint is a trim
    # authority. Positive rational conic weights prove the WHOLE remainder.
    low, high = source_bounds
    reference = _reference_homogeneous(result, side, (low, high), rotation, origin)
    if command[0] == "L":
        actual = [[_point(_q(v)) for v in (*start, 1)], [_point(_q(v)) for v in (*command[-2:], 1)]]
    else:
        actual = _endpoint_arc_node(
            None, tuple(map(_q, start)), tuple(map(_q, command[-2:])), _q(command[1]), command[5]
        ).homogeneous
    w0 = min(p[2][0] for p in reference)
    w1 = min(p[2][0] for p in actual)
    if min(w0, w1) <= 0:
        raise ValidationError("Native trim lacks a positive whole-arc weight bound.")
    n0 = max(_norm_bounds(p[:2]) for p in reference)
    dn = max(
        _norm_bounds([_add(a, _neg(b)) for a, b in zip(x[:2], y[:2])])
        for x, y in zip(actual, reference)
    )
    dw = max(max(abs(a - b) for a in x[2] for b in y[2]) for x, y in zip(actual, reference))
    position = (dn + n0 / w0 * dw) / w1
    if command[0] == "L":
        from .curve_area import _sqrt

        actual_length = _sqrt(sum((_q(x) - _q(y)) ** 2 for x, y in zip(start, command[-2:])))
    else:
        actual_length = _native_arc_length(start, command[-2:], _q(command[1]))
    shell = result["representation"]["circular_shell"]
    index = 0 if side == "first" else 1
    radius = Q(shell["native_radius_exact"][index])
    angular_span = _mul(_pi(), (2 * (high[0] - low[1]), 2 * (high[1] - low[0])))
    angular_span = min(abs(x) for x in angular_span), max(abs(x) for x in angular_span)
    expected_length = _mul(_point(radius), angular_span)
    frame_gram = sum(
        abs(
            sum(Q(float(rotation[k, i])) * Q(float(rotation[k, j])) for k in range(2))
            - (1 if i == j else 0)
        )
        for i in range(2)
        for j in range(2)
    )
    length = (
        max(abs(actual_length[0] - expected_length[1]), abs(actual_length[1] - expected_length[0]))
        + frame_gram * expected_length[1]
    )
    return position, length


def _edge_lists(project, part, result, side, *, proxy):
    from .loft_surface import _local_frame

    rotation, origin = _local_frame(project, part, result)
    source_profile = project.profiles[project.surfaces[part.surface_ids[0]].profile_id]
    offset, edges = Q(0), []
    for patch, native in zip(result["solver"]["patches"], result["native"]["patches"]):
        sweep = abs(_q(source_profile.segment(patch["first_segment_id"]).data["sweep_deg"]))
        if proxy:
            points = (
                (np.asarray(patch["flat_" + side + "_paper_mm"]) - origin) @ rotation.T
            ).tolist()
            rows = [
                (a, b, ["L", *b], _q(t), _q(u), {})
                for a, b, t, u in zip(
                    points, points[1:], patch["parameters"], patch["parameters"][1:]
                )
            ]
        else:
            rows = []
            for segment in native[side]["segments"]:
                start, end = (
                    (np.asarray([segment["start"], segment["end"]]) - origin) @ rotation.T
                ).tolist()
                command = (
                    ["L", *end]
                    if segment["kind"] == "line"
                    else [
                        "A",
                        segment["data"]["radius"],
                        segment["data"]["radius"],
                        0,
                        0,
                        segment["data"]["sweep"],
                        *end,
                    ]
                )
                t, u = map(_q, segment["source"]["loft_parameter_interval"])
                rows.append((start, end, command, t, u, segment["source"]))
        for a, b, command, t, u, source in rows:
            lo, hi = (offset + sweep * t) / 360, (offset + sweep * u) / 360
            edges.append(
                {
                    "start": a,
                    "end": b,
                    "command": command,
                    "lo": lo,
                    "hi": hi,
                    "source": copy.deepcopy(source),
                    "source_lo": lo,
                    "source_hi": hi,
                }
            )
        offset += sweep
    if offset != 360:
        raise ValidationError("Circular material lacks complete actual source coverage.")
    if side == "second":
        reversed_edges = []
        for edge in reversed(edges):
            command = copy.deepcopy(edge["command"])
            command[-2:] = edge["start"]
            if command[0] == "A":
                command[5] ^= 1
            reversed_edges.append(
                {
                    **edge,
                    "start": edge["end"],
                    "end": edge["start"],
                    "command": command,
                    "lo": 1 - edge["hi"],
                    "hi": 1 - edge["lo"],
                    "source_lo": edge["source_hi"],
                    "source_hi": edge["source_lo"],
                }
            )
        edges = reversed_edges
    return edges, rotation, origin


def _locate(edges, bounds, *, finish=False, proxy=False):
    if proxy:
        bounds = ((bounds[0] + bounds[1]) / 2,) * 2  # Drawing only, never the native trim.
    candidates = [
        i for i, edge in enumerate(edges) if edge["lo"] <= bounds[0] <= bounds[1] <= edge["hi"]
    ]
    if not candidates:
        raise ValidationError(
            "A source trim endpoint straddles an unresolved construction boundary."
        )
    return max(candidates) if finish else min(candidates)


def _walk_rim(edges, events, result, side, rotation, origin, *, proxy=False):
    cursor, point, bounds = 0, edges[0]["start"], (Q(0), Q(0))
    commands, owners, proxy_points, position, length = [], [], [point], Q(0), Q(0)

    def emit(end, end_bounds, edge):
        nonlocal point, bounds, position, length
        if point != end:
            command = copy.deepcopy(edge["command"])
            command[-2:] = end
            if not proxy:
                a, b = (
                    (bounds, end_bounds)
                    if side == "first"
                    else ((1 - bounds[1], 1 - bounds[0]), (1 - end_bounds[1], 1 - end_bounds[0]))
                )
                error, delta = _fragment_error(
                    result, side, (a, b), point, command, rotation, origin
                )
                position, length = max(position, error), length + delta
            commands.append(command)
            owners.append({"kind": "BODY", "source": edge["source"]})
            proxy_points.append(end)
        point, bounds = end, end_bounds

    def until(index, end, end_bounds):
        nonlocal cursor
        while cursor < index:
            edge = edges[cursor]
            emit(edge["end"], (edge["hi"], edge["hi"]), edge)
            cursor += 1
        emit(end, end_bounds, edges[cursor])

    previous_end = Q(-1)
    for event in events:
        if event["start_bounds"][0] <= previous_end:
            raise ValidationError(
                "Circular tab source intervals overlap or have unresolved ordering."
            )
        begin = _locate(edges, event["start_bounds"], proxy=proxy)
        finish = _locate(edges, event["end_bounds"], finish=True, proxy=proxy)
        if begin < cursor or finish < begin:
            raise ValidationError("Circular material source ordering changed.")
        until(begin, event["start"], event["start_bounds"])
        commands.extend([["L", *event["apex"]], ["L", *event["end"]]])
        owners.extend(
            [{"kind": "TAB_CUT", "tab_id": event["tab_id"], "connector_id": event["connector_id"]}]
            * 2
        )
        proxy_points.extend([event["apex"], event["end"]])
        cursor, point, bounds = finish, event["end"], event["end_bounds"]
        previous_end = event["end_bounds"][1]
    until(len(edges) - 1, edges[-1]["end"], (Q(1), Q(1)))
    return commands, owners, proxy_points, position, length


def compose_circular_rim_tabs(project, bare_part, slots):
    """Return detached canonical native material; source transfer is separate.

    The domain callback supplies freshly source-derived packets, not cached
    material. Every packet is rebound to current registry fields and the live
    rim/frame; its native chart and pure material area are recomputed here.
    """
    from .loft_surface import _analysis_readonly

    if not isinstance(slots, (tuple, list)) or len(slots) > MAX_SLOTS:
        raise ValidationError("Circular material exhausted its finite slot budget.")
    if len(bare_part.surface_ids) != 1:
        raise ValidationError("Circular attached tabs require their actual single body part.")
    sid = bare_part.surface_ids[0]
    result = _analysis_readonly(project, project.surfaces[sid])
    if result["status"] != "EXACT" or not result.get("representation", {}).get("circular_shell"):
        raise ValidationError("Attached circular material requires a proved native circular body.")
    inputs = _source_inputs(project, sid)
    records = inputs.get("curved_connectors", {})
    fingerprint = _digest(inputs)
    expected, inventory = set(), []
    for cid, record in records.items():
        if record["owner_surface_id"] != sid:
            continue
        for i, tab_id in enumerate(record["slot_ids"]):
            enabled = bool(
                record["enabled"]
                and i < record["parameters"]["count"]
                and record["tab_overrides"].get(tab_id, {}).get("enabled", True)
            )
            inventory.append({"connector_id": cid, "tab_id": tab_id, "enabled": enabled})
            if enabled:
                expected.add(tab_id)
    supplied = [s["tab_id"] for s in slots]
    if (
        len(set(supplied)) != len(supplied)
        or {s["tab_id"] for s in slots if s["enabled"]} != expected
    ):
        raise ValidationError("Circular material lacks exact active tab identity coverage.")
    events, fills, guides, extras, packets = {"first": [], "second": []}, [], [], [], []
    reserve = PACKET_POSITION_LIMIT
    for slot in slots:
        if not slot["enabled"]:
            if slot["tab_id"] not in {x["tab_id"] for x in inventory if not x["enabled"]}:
                raise ValidationError("A disabled packet does not match authored tab state.")
            continue
        record = records.get(slot["connector_id"])
        side = slot["rim_side"]
        if (
            not record
            or record["owner_surface_id"] != sid
            or record["rim_side"] != side
            or record["receiver_surface_id"] != slot["receiver_surface_id"]
            or slot["source_digest"] != fingerprint
        ):
            raise ValidationError("Circular packet source/owner/receiver bindings are stale.")
        rim = project._circular_rim_binding(
            sid, side, source_turn=slot["source_turn"], part_override=bare_part
        )
        if (
            slot["rim_source_digest"] != rim["source_digest"]
            or slot["rim_id"] != rim["rim_id"]
            or slot["chart_to_paper"] != rim["chart_to_paper"]
        ):
            raise ValidationError("Circular packet differs from the current analytic rim/frame.")
        base, sides, loop = (
            _commands(slot[key])
            for key in (
                "paper_shared_base_commands",
                "paper_cut_side_commands",
                "paper_native_loop",
            )
        )
        if (
            len(base) != 2
            or base[0][0] != "M"
            or base[1][0] not in ("A", "L")
            or len(sides) != 3
            or [c[0] for c in sides] != ["M", "L", "L"]
            or sides[0][-2:] != base[1][-2:]
            or sides[-1][-2:] != base[0][-2:]
            or loop != [base[0], base[1], sides[1], ["Z"]]
            or slot["paper_apex"] != sides[1][-2:]
        ):
            raise ValidationError(
                "Actual base, straight sides and filled tab do not share exact endpoints."
            )
        reference = slot.get("reference_tab")
        if not isinstance(reference, dict):
            raise ValidationError(
                "A fresh authored reference tab is required for material binding."
            )
        try:
            tab = Tab(**reference)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid authored reference tab fields.") from exc
        native_rim = Rim(
            _q(rim["radius_exact"]), _q(rim["native_radial_slope_exact"]), rim["rim_id"], sid
        )
        params = record["parameters"]
        override = record["tab_overrides"].get(tab.tab_id, {})
        if (
            tab.tab_id != slot["tab_id"]
            or tab.owner_id != sid
            or tab.receiver_id != slot["receiver_surface_id"]
            or not tab.enabled
            or _q(tab.depth_mm) != _q(params["depth_mm"])
            or _q(tab.relief_mm) != _q(params["relief_mm"])
            or _q(tab.tip_offset_mm) != _q(override.get("tip_offset_mm", 0))
            or params["nominal_base_mm"] is not None
            and _q(tab.nominal_base_mm) != _q(params["nominal_base_mm"])
        ):
            raise ValidationError("Reference tab parameters differ from authored registry values.")
        if _q(tab.center_turn) != (_q(slot["source_turn"]) * rim["source_turn_direction"]) % 1:
            raise ValidationError("Circular source angular correspondence changed.")
        ids = sorted(
            {
                sid,
                *project.surfaces[sid].source_profile_ids(),
                rim["rim_id"],
                slot["connector_id"],
                *record["slot_ids"],
            }
        )
        certificate = certify_native_tab_chart(
            native_rim,
            tab,
            base,
            sides[1][-2:],
            rim["chart_to_paper"]["matrix"],
            rim["chart_to_paper"]["translation"],
            source_ids=ids,
            source_digest=fingerprint,
        )
        if (
            certificate["status"] != "CERTIFIED_NATIVE_CHART"
            or certificate["native_chart_digest"]
            != slot["native_chart_certificate"]["native_chart_digest"]
        ):
            raise ValidationError("Actual native tab chart could not be freshly rebound.")
        limit = min(PACKET_POSITION_LIMIT, _q(params["publication_error_budget_mm"]))
        reserve = min(reserve, limit)
        if certificate["native_chart_position_error_mm"] > limit:
            raise ValidationError(
                "The actual native tab packet exhausted its own publication reserve."
            )
        pure_area = native_region_area_bounds([_geometry(native_rim, tab)["flat_native_loop"]])
        if tuple(map(_q, slot["source_material_area_bounds_exact"])) != pure_area:
            raise ValidationError("Tab source area does not match its pure native material.")
        extras.append(pure_area)
        start, end = map(_interval, slot["source_turn_interval_bounds_exact"])
        if not 0 <= start[0] <= start[1] < end[0] <= end[1] <= 1:
            raise ValidationError("A curved tab crosses the period seam or lacks ordered coverage.")
        if slot["source_intervals"] != _source_coverage(project, rim, start[0], end[1]):
            raise ValidationError("Curved tab provenance does not match actual source intervals.")
        direction = rim["source_turn_direction"]
        if slot["shared_base_source_direction"] != direction:
            raise ValidationError("A shared native base reversed its source direction.")
        low_point, high_point = (
            (base[0][-2:], base[1][-2:]) if direction == 1 else (base[1][-2:], base[0][-2:])
        )
        bounds0, bounds1 = (
            (start, end)
            if side == "first"
            else ((1 - end[1], 1 - end[0]), (1 - start[1], 1 - start[0]))
        )
        point0, point1 = (low_point, high_point) if side == "first" else (high_point, low_point)
        events[side].append(
            {
                "start_bounds": bounds0,
                "end_bounds": bounds1,
                "start": point0,
                "end": point1,
                "apex": sides[1][-2:],
                "tab_id": tab.tab_id,
                "connector_id": slot["connector_id"],
            }
        )
        fills.append({"commands": loop, "closed": True})
        guides.append({"commands": base, "closed": False})
        packets.append(
            {
                "tab_id": tab.tab_id,
                "connector_id": slot["connector_id"],
                "native_chart_digest": certificate["native_chart_digest"],
                "source_area_bounds_exact": list(map(str, pure_area)),
                "publication_error_budget_exact": str(limit),
                "fill_path_index": len(bare_part.paths["TABS"]) + len(fills) - 1,
                "guide_path_index": len(bare_part.paths["GUIDES"]) + len(guides) - 1,
                "guide_semantic_role": "CURVED_ATTACHED_BASE_NOT_A_SECOND_CUT",
                "shared_base_commands": base,
                "source_intervals": slot["source_intervals"],
            }
        )
    part = copy.deepcopy(bare_part)
    if not expected:
        return part
    walked, proxies, position, length = {}, {}, Q(0), Q(0)
    for side in ("first", "second"):
        ordered = sorted(events[side], key=lambda event: event["start_bounds"][0])
        edges, rotation, origin = _edge_lists(project, part, result, side, proxy=False)
        walked[side] = _walk_rim(edges, ordered, result, side, rotation, origin)
        proxy, rotation, origin = _edge_lists(project, part, result, side, proxy=True)
        proxies[side] = _walk_rim(proxy, ordered, result, side, rotation, origin, proxy=True)
        position, length = max(position, walked[side][3]), length + walked[side][4]
    if position > reserve or length > reserve:
        raise ValidationError(
            "Native body trimming exhausted its GLOBAL publication position/length reserve."
        )
    first, second = walked["first"], walked["second"]
    first_start, first_end = first[2][0], first[2][-1]
    second_start, second_end = second[2][0], second[2][-1]
    commands = [["M", *first_start], *first[0], ["L", *second_start], *second[0], ["Z"]]
    owners = [
        {"kind": "BODY"},
        *first[1],
        {"kind": "BODY_RULING"},
        *second[1],
        {"kind": "BODY_RULING"},
    ]
    if second_end != first_start and not all(math.isfinite(x) for x in (*first_end, *second_end)):
        raise ValidationError("Circular material closing ruling is not finite.")
    topology = certify_native_region_topology(commands, max_nodes=MAX_NODES)
    if topology.status != "VALID":
        raise ValidationError(
            "Actual circular material union is not proved simple: " + topology.reason
        )
    points = [*proxies["first"][2], *proxies["second"][2]]
    material_polygon(points)
    part.polygons = {sid: [points]}
    part.paths["CUT"] = [{"commands": commands, "closed": True}]
    part.paths["TABS"].extend(fills)
    part.paths["GUIDES"].extend(guides)
    source = _area_source(result["area"]["source_intrinsic"], extras)
    low, high = native_region_area_bounds([commands])
    basis_low = Q(result["area"]["source_intrinsic"]["area_lower_exact"])
    error = max(abs(low - Q(source["area_upper_exact"])), abs(high - Q(source["area_lower_exact"])))
    allowed = max(Q(1, 100), basis_low / 1000000)  # BODY ONLY, never inflated by tabs.
    if error > allowed:
        raise ValidationError(
            "Actual circular body/tab union exceeds the BODY_ONLY source area budget."
        )
    part._circular_material_report = {
        "contract": CONTRACT,
        "status": "CANONICAL_NATIVE_MATERIAL_COMPOSED",
        "scope": "MATERIAL_UNION_ONLY_NOT_SOURCE_TRANSFER_OR_FULL_ASSEMBLY_APPROVAL",
        "owner_surface_id": sid,
        "inputs_digest": fingerprint,
        "active_tab_ids": sorted(expected),
        "inventory": inventory,
        "slots": packets,
        "source_material_area": source,
        "body_area_basis": copy.deepcopy(result["area"]["source_intrinsic"]),
        "source_to_actual_area_error_exact": str(error),
        "allowed_body_area_error_exact": str(allowed),
        "body_trim_position_error_exact": str(position),
        "body_trim_global_length_error_exact": str(length),
        "publication_error_budget_exact": str(reserve),
        "cut_command_ownership": owners,
        "proxy_extra_error_mm": float(position + 32 * reserve),
        "native_topology": {"status": topology.status, "reason": topology.reason},
        "canonical_material_digest": _digest({"CUT": commands, "TABS": fills, "GUIDES": guides}),
    }
    return part
