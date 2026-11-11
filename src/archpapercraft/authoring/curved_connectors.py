"""Authored curved-rim connectors, source closure and explicit recomputation.

The native shell, deforming collar and whole assembly are separate proofs.
Missing source transfer or material coverage must never become a scene CLEAR.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, replace
from fractions import Fraction
from functools import lru_cache

import numpy as np

from .commands import atomic
from .errors import ValidationError
from .geometry import number
from .model import CurvedConnector, Issue, identity, uuid

CURVED_CONNECTOR_CONTRACT = "ATTACHED_NATIVE_RIM_COLLAR_SOURCE_TRANSFER_V1"
MAX_CURVED_CONNECTORS = 64
MAX_CURVED_SLOTS = 1000
PARAMETERS = {
    "count",
    "depth_mm",
    "relief_mm",
    "nominal_base_mm",
    "gap_mm",
    "min_glue_area_mm2",
    "max_position_mm",
    "max_differential_deformation",
    "publication_error_budget_mm",
}


class CurvedConnectorError(ValidationError):
    def __init__(self, message, *, code="CURVED_CONNECTOR_UNRESOLVED", report=None):
        self.code = code
        self.report = copy.deepcopy(
            report or {"status": "UNRESOLVED", "code": code, "message": message}
        )
        super().__init__(code + ": " + message)


def _json(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf8")).hexdigest()


def _authored(record):
    return {
        key: copy.deepcopy(getattr(record, key))
        for key in (
            "id",
            "name",
            "revision",
            "owner_surface_id",
            "rim_side",
            "receiver_surface_id",
            "receiver_side",
            "parameters",
            "slot_ids",
            "tab_overrides",
            "enabled",
        )
    }


def _has_active_tabs(record):
    """Authored intent can remain while its entire material set is switched off."""
    return record.enabled and any(
        record.tab_overrides.get(tab_id, {}).get("enabled", True)
        for tab_id in record.slot_ids[: record.parameters["count"]]
    )


def _connector_surface_ids(project, connector):
    if connector.attachment_id:
        relation = project.attachments[connector.attachment_id]
        return {relation.source_surface_id, relation.target_surface_id}
    relation = project.joints[connector.joint_id]
    return {relation.surface_a, relation.surface_b}


def _parameters(values):
    if not isinstance(values, dict) or set(values) != PARAMETERS:
        raise ValidationError("Kruhové chlopně potřebují úplné známé parametry.")
    count = values["count"]
    if type(count) is not int or not 1 <= count <= MAX_CURVED_SLOTS:
        raise ValidationError("Počet kruhových záložek musí být celé číslo1 až1000.")
    for key in (
        "depth_mm",
        "relief_mm",
        "min_glue_area_mm2",
        "max_position_mm",
        "max_differential_deformation",
        "publication_error_budget_mm",
    ):
        number(values[key], key, positive=True)
    if not values["relief_mm"] < values["depth_mm"]:
        raise ValidationError("Nelepený ohybový pás musí být menší než hloubka záložky.")
    if values["max_differential_deformation"] >= 1:
        raise ValidationError("Geometrická mez deformace musí být menší než100%.")
    if values["publication_error_budget_mm"] >= values["max_position_mm"]:
        raise ValidationError("Celková polohová mez musí ponechat rezervu pro výrobní výstup.")
    if (values["nominal_base_mm"] is None) == (values["gap_mm"] is None):
        raise ValidationError("Zadejte šířku záložky nebo minimální mezeru, právě jednu volbu.")
    if values["nominal_base_mm"] is not None:
        number(values["nominal_base_mm"], "Šířka záložky", positive=True)
    if values["gap_mm"] is not None:
        number(values["gap_mm"], "Minimální mezera", nonnegative=True)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    x, y, z = a
    u, v, w = b
    return y * w - z * v, z * u - x * w, x * v - y * u


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _circle_source(profile):
    """Recognize the supplied material circle, never a display mesh or preset."""
    from .circular_shell import _exact_radius
    from .profile_curves import source_curve

    if not profile.closed or not profile.segments:
        raise CurvedConnectorError(
            "Příjemce potřebuje uzavřenou skutečnou kruhovou hranici.",
            code="RECEIVER_CIRCLE_UNRESOLVED",
        )
    curves = [source_curve(profile, segment) for segment in profile.segments]
    if any(curve.kind != "arc" for curve in curves):
        raise CurvedConnectorError(
            "Tento kruhový spoj potřebuje skutečný disk s kruhovými otvory.",
            code="RECEIVER_CIRCLE_UNRESOLVED",
        )
    circle = _exact_radius(curves)
    sweeps = [Fraction(curve.data["sweep_deg"]) for curve in curves]
    if (
        circle is None
        or sum(abs(value) for value in sweeps) != 360
        or any(value * sweeps[0] <= 0 for value in sweeps)
    ):
        raise CurvedConnectorError(
            "Kruhovou hranici příjemce nelze doložit z jeho skutečných oblouků.",
            code="RECEIVER_CIRCLE_UNRESOLVED",
        )
    center, radius = circle
    u, v, origin = (
        tuple(map(Fraction, getattr(profile.plane, key))) for key in ("u", "v", "origin")
    )
    if _dot(u, u) != 1 or _dot(v, v) != 1 or _dot(u, v) != 0:
        raise CurvedConnectorError(
            "Kruhová rovina nemá doloženou izometrii zdrojové báze.",
            code="RECEIVER_FRAME_UNRESOLVED",
        )
    return {
        "profile_id": profile.id,
        "center_uv": center,
        "radius": radius,
        "center": tuple(o + center[0] * a + center[1] * b for o, a, b in zip(origin, u, v)),
        "u": u,
        "v": v,
        "normal": _cross(u, v),
        "segment_ids": tuple(segment.id for segment in profile.segments),
    }


def _receiver_binding(project, record, rim_binding):
    """Exact common-source-frame disk/holes for the supported contact family.

    Different, unproved transforms/planes are refused. No guessed nominal disk
    replaces authored holes, receiver side or the actual material source UUID.
    """
    from .curved_tabs import Cap, CircularHole

    owner, receiver = (
        project.surfaces[record.owner_surface_id],
        project.surfaces[record.receiver_surface_id],
    )
    index = 0 if record.rim_side == "first" else 1
    owner_profile = project.profiles[owner.source_profile_ids()[index]]
    owner_circle = _circle_source(owner_profile)
    profiles = [project.profiles[pid] for pid in receiver.source_profile_ids()]
    circles = [_circle_source(profile) for profile in profiles]
    outer = circles[0]
    owner_matrix, receiver_matrix = (
        project._surface_matrix(owner.id),
        project._surface_matrix(receiver.id),
    )
    if not np.array_equal(owner_matrix, receiver_matrix):
        raise CurvedConnectorError(
            "Plášť a příjemce zatím nemají doložený společný skutečný rám.",
            code="RECEIVER_FRAME_UNRESOLVED",
        )
    first, second = [_circle_source(project.profiles[pid]) for pid in owner.source_profile_ids()]
    height = _dot(_sub(second["center"], first["center"]), first["normal"])
    if height == 0:
        raise CurvedConnectorError("Kruhový plášť nemá nenulovou osovou výšku.")
    axis_sign = (1 if height > 0 else -1) * (1 if index else -1)
    outward = tuple(axis_sign * value for value in first["normal"])
    side_sign = 1 if record.receiver_side == "outside" else -1
    contact_normal = tuple(side_sign * value for value in outer["normal"])
    if contact_normal != outward:
        raise CurvedConnectorError(
            "Zvolená strana příjemce nesměřuje do skutečného kontaktu.",
            code="RECEIVER_SIDE_UNRESOLVED",
        )
    if outer["center"] != owner_circle["center"]:
        raise CurvedConnectorError(
            "Příjemce není v doloženém společném středu kruhového okraje.",
            code="RECEIVER_PLANE_UNRESOLVED",
        )
    for circle in circles:
        if (
            _dot(_sub(circle["center"], outer["center"]), outward) != 0
            or abs(_dot(circle["normal"], outward)) != 1
        ):
            raise CurvedConnectorError(
                "Otvor příjemce není ve skutečné kontaktní rovině.",
                code="RECEIVER_PLANE_UNRESOLVED",
            )
    # Source seam is reconstructed with exact quarter turns from its actual
    # stored correspondence, avoiding a rounded libm point as a new authority.
    reference = owner.params["correspondences"][0]
    side = record.rim_side
    segment = owner_profile.segment(reference[side + "_segment_id"])
    start = owner_profile.vertex(segment.start_vertex_id).point
    angle = Fraction(reference[side + "_interval"][0]) * Fraction(segment.data["sweep_deg"])
    if angle % 90:
        raise CurvedConnectorError("Zdrojový šev nemá doložený přesný kruhový rám.")
    radial2 = tuple(
        Fraction(value) - center for value, center in zip(start, owner_circle["center_uv"])
    )
    for _ in range(int(abs(angle) / 90)):
        x, y = radial2
        radial2 = (-y, x) if angle > 0 else (y, -x)
    radius = owner_circle["radius"]
    radial = tuple(
        (radial2[0] * u + radial2[1] * v) / radius
        for u, v in zip(owner_circle["u"], owner_circle["v"])
    )
    tangent = _cross(outward, radial)
    scale = Fraction(project.scale)
    holes = []
    for circle in circles[1:]:
        delta = _sub(circle["center"], owner_circle["center"])
        holes.append(
            CircularHole(
                _dot(delta, radial) * scale, _dot(delta, tangent) * scale, circle["radius"] * scale
            )
        )
    source = {
        "surface": asdict(receiver),
        "profiles": [asdict(profile) for profile in profiles],
        "part_id": receiver.part_id,
        "front_side": project.parts[receiver.part_id].front_side,
        "receiver_side": record.receiver_side,
        "scale": project.scale,
        "owner_source_digest": rim_binding["source_digest"],
        "condition": "EXACT_COMMON_AUTHORED_POSE_AND_COPLANAR_COAXIAL_SOURCE_DISK_WITH_HOLES",
    }
    cap = Cap(outer["radius"] * scale, receiver.id, holes=tuple(holes), contact_side="front")
    return cap, {
        "source_binding": source,
        "source_digest": _digest(source),
        "outer_profile_id": profiles[0].id,
        "hole_profile_ids": [p.id for p in profiles[1:]],
        "source_radial": radial,
        "source_tangent": tangent,
        "source_outward": outward,
        "condition": source["condition"],
        "receiver_contact_is_printed_side": record.receiver_side == source["front_side"],
    }


def _exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: _exact_json(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_exact_json(child) for child in value]
    return value


def _mapped_commands(commands, chart):
    """Actual circular endpoint packet; its fan/Jacobian is certified separately."""
    matrix = [[Fraction(value) for value in row] for row in chart["matrix"]]
    shift = tuple(map(Fraction, chart["translation"]))
    reflected = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0] < 0
    result = []
    for command in commands:
        op = command[0]
        if op == "Z":
            result.append(["Z"])
            continue
        if op not in ("M", "L", "A"):
            raise CurvedConnectorError("Kruhová záložka ztratila nativní A/L konstrukci.")
        x, y = map(Fraction, command[-2:])
        point = [float(_dot(row, (x, y)) + value) for row, value in zip(matrix, shift)]
        if op == "A":
            result.append(
                [
                    "A",
                    float(command[1]),
                    float(command[2]),
                    0,
                    int(command[4]),
                    int(command[5]) ^ int(reflected),
                    *point,
                ]
            )
        else:
            result.append([op, *point])
    return result


def _source_fragments(project, owner_id, side, full_rim, interval):
    """Attribute an enclosing turn interval to exact, ordered authored sources."""
    profile = project.profiles[full_rim["profile_id"]]
    lower, upper = interval
    cursor, fragments = Fraction(0), []
    for source in full_rim["source_intervals"]:
        segment = profile.segment(source["segment_id"])
        a, b = map(Fraction, source["parameter_interval"])
        span = abs(Fraction(segment.data["sweep_deg"]) * (b - a)) / 360
        if span <= 0:
            raise CurvedConnectorError("Zdrojový interval kruhového okraje není kladný.")
        lo, hi = max(lower, cursor), min(upper, cursor + span)
        if lo < hi:
            start = a + (b - a) * (lo - cursor) / span
            end = a + (b - a) * (hi - cursor) / span
            fragments.append(
                {
                    **copy.deepcopy(source),
                    "source_turn_coverage_exact": [str(lo), str(hi)],
                    "parameter_coverage_exact": [str(start), str(end)],
                    "coverage_kind": "OUTWARD_ENCLOSURE_NOT_AN_EXACT_IRRATIONAL_ENDPOINT",
                }
            )
        cursor += span
    if cursor != 1 or not fragments:
        raise CurvedConnectorError(
            "Kruhový okraj nemá úplné doložené pokrytí zdrojových intervalů."
        )
    if any(
        source["feature_id"] != owner_id or source["profile_id"] != profile.id
        for source in fragments
    ):
        raise CurvedConnectorError(
            "Zdrojové UUID kruhového okraje se neshoduje se skutečnou plochou."
        )
    return fragments


def _prepare_native_slots_uncached(project, record, bare_part=None):
    """Fresh native packets and whole-source transfer; not body-union approval."""
    from .curve_area import native_region_area_bounds
    from .curved_tabs import Limits, Rim, _geometry, _pi, periodic_tabs
    from .curved_tabs_chart import certify_native_tab_chart
    from .curved_tabs_transfer import (
        ANGULAR_KIND,
        CHART_KIND,
        RECEIVER_KIND,
        ReceiverTransferBounds,
        SourceTransferBounds,
        TabChartBounds,
        certify_source_transfer,
    )

    owner = record.owner_surface_id
    part = project.parts[project.surfaces[owner].part_id] if bare_part is None else bare_part
    common = project._circular_rim_binding(owner, record.rim_side, part_override=part)
    cap, receiver = _receiver_binding(project, record, common)
    source = project.curved_connector_inputs(owner)
    digest = _digest(source)
    params = record.parameters
    rim = Rim(
        Fraction(common["radius_exact"]),
        Fraction(common["native_radial_slope_exact"]),
        common["rim_id"],
        owner,
    )
    direction = common["source_turn_direction"]
    centers = [float(Fraction(2 * i + 1, 2 * params["count"])) for i in range(params["count"])]
    turns = sorted((direction * Fraction(value)) % 1 for value in centers)
    requested_gap = Fraction(params["gap_mm"]) if params["gap_mm"] is not None else Fraction(0)
    if params["nominal_base_mm"] is not None:
        base = Fraction(params["nominal_base_mm"])
    else:
        separation = min(b - a for a, b in zip(turns, [*turns[1:], turns[0] + 1]))
        source_radius = Fraction(common["source_radius_bounds"]["lower_exact"])
        reserve = 2 * (
            Fraction(params["publication_error_budget_mm"])
            + Fraction(common["native_position_bound_paper_mm"])
        )
        width = Fraction(rim.radius_mm) * (
            2 * _pi()[0] * separation - (requested_gap + reserve) / source_radius
        )
        grid = 10**24
        base = Fraction(width.numerator * grid // width.denominator, grid)
        if base <= 0:
            raise CurvedConnectorError(
                "Zadané mezery a ověřovací rezerva nenechávají kladnou záložku."
            )
    generated = periodic_tabs(
        rim,
        cap.part_id,
        count=params["count"],
        nominal_base_mm=base,
        depth_mm=params["depth_mm"],
        relief_mm=params["relief_mm"],
    )
    tabs, slots, charts = [], [], []
    source_ids = tuple(
        sorted(
            {
                owner,
                *project.surfaces[owner].source_profile_ids(),
                common["rim_id"],
                record.id,
                *record.slot_ids,
            }
        )
    )
    for i, generated_tab in enumerate(generated):
        slot_id, center = record.slot_ids[i], centers[i]
        override = record.tab_overrides.get(slot_id, {})
        tab = replace(
            generated_tab,
            tab_id=slot_id,
            center_turn=(direction * Fraction(center)) % 1,
            enabled=record.enabled and override.get("enabled", True),
            tip_offset_mm=override.get("tip_offset_mm", 0),
            requested_min_gap_mm=requested_gap,
        )
        tabs.append(tab)
        if not tab.enabled:
            slots.append({"connector_id": record.id, "tab_id": slot_id, "enabled": False})
            continue
        geometry = _geometry(rim, tab)
        slot_rim = project._circular_rim_binding(
            owner, record.rim_side, source_turn=center, part_override=part
        )
        chart = slot_rim["chart_to_paper"]
        loop = _mapped_commands(geometry["flat_native_loop"], chart)
        shared = _mapped_commands(geometry["shared_base_commands"], chart)
        sides = _mapped_commands(geometry["cut_side_commands"], chart)
        apex = sides[1][-2:]
        certificate = certify_native_tab_chart(
            rim,
            tab,
            shared,
            apex,
            chart["matrix"],
            chart["translation"],
            source_ids=source_ids,
            source_digest=digest,
        )
        if certificate["status"] == "CERTIFIED_NATIVE_CHART":
            charts.append(
                TabChartBounds(
                    slot_id,
                    certificate["paper_chart_matrix"],
                    certificate["paper_chart_derivative_remainder"],
                    certificate["native_chart_position_error_mm"],
                    certificate["native_chart_digest"],
                )
            )
        a, b = geometry["half_angle"]
        half_turn = a / (2 * _pi()[1]), b / (2 * _pi()[0])
        start = Fraction(center) - half_turn[1], Fraction(center) - half_turn[0]
        end = Fraction(center) + half_turn[0], Fraction(center) + half_turn[1]
        if start[0] < 0 or end[1] > 1:
            raise CurvedConnectorError("Záložka přesahuje periodický šev rozvinu.")
        area = native_region_area_bounds([geometry["flat_native_loop"]])
        slots.append(
            {
                "connector_id": record.id,
                "tab_id": slot_id,
                "enabled": True,
                "owner_surface_id": owner,
                "receiver_surface_id": record.receiver_surface_id,
                "rim_id": common["rim_id"],
                "rim_side": record.rim_side,
                "paper_native_loop": loop,
                "paper_shared_base_commands": shared,
                "paper_cut_side_commands": sides,
                "paper_apex": apex,
                "source_material_area_bounds_exact": [str(value) for value in area],
                "source_turn": center,
                "nominal_source_turn_exact": str(Fraction(2 * i + 1, 2 * params["count"])),
                "source_turn_interval_bounds_exact": _exact_json([start, end]),
                "source_turn_interval": [str(start[0]), str(end[1])],
                "shared_base_source_direction": direction,
                "source_intervals": _source_fragments(
                    project, owner, record.rim_side, common, (start[0], end[1])
                ),
                "rim_source_digest": common["source_digest"],
                "source_digest": digest,
                "receiver_source_digest": receiver["source_digest"],
                "chart_to_paper": copy.deepcopy(chart),
                "native_chart_certificate": _exact_json(certificate),
                "reference_tab": _exact_json(asdict(tab)),
                "reference_rim": _exact_json(asdict(rim)),
            }
        )
    frame = common["world_frame"]
    matrix = tuple(
        tuple(frame[column][row] for column in ("radial", "tangent", "outward_z"))
        for row in range(3)
    )
    transfer = SourceTransferBounds(
        tuple(common["source_radius_bounds"][key] for key in ("lower_exact", "upper_exact")),
        tuple(common["source_radial_slope_bounds"][key] for key in ("lower_exact", "upper_exact")),
        common["rim_id"],
        owner,
        source_ids=source_ids,
        source_digest=digest,
        native_chart_digest=_digest([(c.tab_id, c.native_chart_digest) for c in charts]),
        world_frame_matrix=matrix,
        world_frame_operator_remainder=common["world_frame_operator_error_bound_exact"],
        world_frame_position_error_mm=common["world_frame_center_error_bound_paper_mm_exact"],
        native_chart_kind=CHART_KIND,
        source_angular_correspondence_kind=ANGULAR_KIND,
        tab_charts=tuple(charts),
    )
    receiver_ids = tuple(
        sorted(
            {
                record.receiver_surface_id,
                *project.surfaces[record.receiver_surface_id].source_profile_ids(),
            }
        )
    )
    receiver_transfer = ReceiverTransferBounds(
        cap.part_id,
        source_ids=receiver_ids,
        source_digest=receiver["source_digest"],
        common_frame_kind=RECEIVER_KIND,
        plane_offset_bounds_mm=(0, 0),
        # All circle/holes use the same exact authored frame. Native publication
        # retains a separate bounded boundary tube, never a guessed nominal disk.
        radius_error_mm=Fraction(1, 100),
        frame_position_error_mm=common["world_frame_center_error_bound_paper_mm_exact"],
        hole_radius_errors_mm=tuple(Fraction(1, 100) for _ in cap.holes),
        hole_center_errors_mm=tuple(0 for _ in cap.holes),
    )
    material = project.material_profile
    limits = Limits(
        Fraction(params["max_position_mm"]) - Fraction(params["publication_error_budget_mm"]),
        params["max_differential_deformation"],
        params["min_glue_area_mm2"],
        material["thickness_mm"],
        material["clearance_mm"],
        material["bend_radius_mm"],
    )
    report = certify_source_transfer(rim, tuple(tabs), cap, limits, transfer, receiver_transfer)
    return {
        "source_binding": source,
        "source_fingerprint": digest,
        "rim_binding": common,
        "receiver_binding": _exact_json(receiver),
        "source_transfer": _exact_json(report),
        "slots": slots,
        "physical_build": "NOT_VERIFIED",
        "scope": "NATIVE_PACKET_AND_SOURCE_TRANSFER_ONLY; ACTUAL_BODY_UNION_AND_SCENE_REQUIRED",
    }


def rebuild_curved_material_binding(body_binding, paper_frame, curved_inputs):
    """Rebuild source-only context, never a persisted/cached body approval.

    Publication must ALSO close these selected-scene inputs against the full
    source-project snapshot. This function binds exact owner records and frames,
    and supplies immutable-authored geometry for a fresh native composition.
    """
    from .loft_surface import _profile_from_record
    from .model import (
        Attachment,
        Connector,
        Joint,
        MaterialPart,
        PaperFrame,
        Placement,
        SurfaceFeature,
    )
    from .project import AuthorProject, _record

    source = copy.deepcopy(curved_inputs)
    expected = {
        "contract",
        "owner_surface_id",
        "scale",
        "material_profile",
        "curved_connectors",
        "bound_sources",
        "surfaces",
        "profiles",
        "parts",
        "joints",
        "attachments",
        "connectors",
    }
    if (
        not isinstance(source, dict)
        or set(source) not in (expected, expected | {"profile_subdivisions"})
        or source["contract"] != CURVED_CONNECTOR_CONTRACT
    ):
        raise CurvedConnectorError("Chybí úplný aktuální autorský vstup kruhových chlopní.")
    if len(_json(source).encode("utf8")) > 32 * 1024 * 1024:
        raise CurvedConnectorError("Zdroj kruhových chlopní překročil konečný32MiB rozpočet.")
    for key, limit in (
        ("parts", 4096),
        ("surfaces", 4096),
        ("profiles", 8192),
        ("curved_connectors", MAX_CURVED_CONNECTORS),
    ):
        if not isinstance(source[key], dict) or len(source[key]) > limit:
            raise CurvedConnectorError("Neplatný nebo příliš velký zdrojový registr " + key + ".")
    owner_id = source["owner_surface_id"]
    if (
        body_binding["surface"]["id"] != owner_id
        or source["surfaces"].get(owner_id) != body_binding["surface"]
        or source["scale"] != body_binding["scale"]
    ):
        raise CurvedConnectorError("Zdroj chlopní nenáleží skutečnému tělu a měřítku.")
    context = AuthorProject(name="Source-only curved material binding", scale=source["scale"])
    context.material_profile = copy.deepcopy(source["material_profile"])
    context._validate_material_profile()
    context.profiles = {pid: _profile_from_record(raw) for pid, raw in source["profiles"].items()}
    for pid, profile in context.profiles.items():
        if profile.id != pid:
            raise CurvedConnectorError("Zdrojový profil má odlišnou skutečnou identitu.")
        profile.validate()
    context.surfaces = {
        sid: _record(SurfaceFeature, raw) for sid, raw in source["surfaces"].items()
    }
    context.profile_subdivisions = copy.deepcopy(source.get("profile_subdivisions", {}))
    context._validate_profile_subdivisions()
    context.parts = {}
    fields = {"id", "name", "number", "lineage", "surface_ids", "frame", "front_side"}
    for pid, raw in source["parts"].items():
        if not isinstance(raw, dict) or set(raw) != fields or raw["id"] != pid:
            raise CurvedConnectorError("Zdrojový díl nemá úplný skutečný frame a identitu.")
        row = copy.deepcopy(raw)
        row["frame"] = _record(PaperFrame, row["frame"])
        context.parts[pid] = MaterialPart(**row)
    context.placements = {pid: Placement() for pid in context.parts}
    context.joints = {key: _record(Joint, row) for key, row in source["joints"].items()}
    context.attachments = {
        key: _record(Attachment, row) for key, row in source["attachments"].items()
    }
    context.connectors = {key: _record(Connector, row) for key, row in source["connectors"].items()}
    context.curved_connectors = {
        key: CurvedConnector(**row) for key, row in source["curved_connectors"].items()
    }
    expected_surfaces = []
    for pid, part in context.parts.items():
        expected_surfaces.extend(part.surface_ids)
        if (
            not part.surface_ids
            or part.front_side not in ("inside", "outside")
            or part.frame.root_surface_id not in part.surface_ids
        ):
            raise CurvedConnectorError("Zdrojový díl má neplatný materiálový rám.")
        for sid in part.surface_ids:
            if sid not in context.surfaces or context.surfaces[sid].part_id != pid:
                raise CurvedConnectorError("Zdroj nepokrývá skutečné materiálové díly a plochy.")
        profile = context.profiles[context.surfaces[part.frame.root_surface_id].profile_id]
        if (
            profile.vertex(part.frame.anchor_vertex_id) is None
            or profile.segment(part.frame.axis_segment_id) is None
        ):
            raise CurvedConnectorError("Zdrojový frame má ztracenou přesnou kotvu.")
    if len(expected_surfaces) != len(set(expected_surfaces)) or set(expected_surfaces) != set(
        context.surfaces
    ):
        raise CurvedConnectorError("Zdrojová materiálová coverage není přesná a úplná.")
    for sid, surface in context.surfaces.items():
        if surface.id != sid or any(
            pid not in context.profiles for pid in surface.source_profile_ids()
        ):
            raise CurvedConnectorError("Zdrojový povrch má neplatné skutečné profily.")
        context._surface_matrix(sid)
    own = context.surfaces[owner_id]
    if [asdict(context.profiles[pid]) for pid in own.source_profile_ids()] != body_binding[
        "profiles"
    ]:
        raise CurvedConnectorError("Kruhový zdroj má jiné skutečné profily než tělo.")
    if asdict(context.parts[own.part_id].frame) != paper_frame:
        raise CurvedConnectorError("Kruhový zdroj má jinou skutečnou papírovou kotvu.")
    for sid, bound in source["bound_sources"].items():
        actual = {
            "surface": asdict(context.surfaces[sid]),
            "profiles": [
                asdict(context.profiles[pid]) for pid in context.surfaces[sid].source_profile_ids()
            ],
        }
        if actual != bound:
            raise CurvedConnectorError(
                "Zdroj kruhového spoje obsahuje rozpornou vazbu příjemce/těla."
            )
    context._validate_curved_connectors()
    if context.curved_connector_inputs(owner_id) != source:
        raise CurvedConnectorError("Rekonstruovaný zdroj kruhového spoje není kanonický.")
    context._curved_source_context_only = True
    return context


@lru_cache(maxsize=4)
def _native_slot_json(source_json, connector_id, frame_json):
    source = json.loads(source_json)
    binding = source["bound_sources"][source["owner_surface_id"]]
    body = {**binding, "scale": source["scale"]}
    context = rebuild_curved_material_binding(body, json.loads(frame_json), source)
    record = context.curved_connectors[connector_id]
    return _json(_exact_json(_prepare_native_slots_uncached(context, record)))


def _prepare_native_slots(project, record, bare_part=None):
    source = project.curved_connector_inputs(record.owner_surface_id)
    part = (
        project.parts[project.surfaces[record.owner_surface_id].part_id]
        if bare_part is None
        else bare_part
    )
    # Only private immutable bytes are cached; no returned list can poison a
    # later proof. Every source coordinate/UUID/frame/parameter enters the key.
    return json.loads(_native_slot_json(_json(source), record.id, _json(asdict(part.frame))))


@lru_cache(maxsize=2)
def _curved_canonical_snapshot_json(source_json):
    from .project import AuthorProject

    source = json.loads(source_json)
    for key, limit in (
        ("parts", 4096),
        ("surfaces", 4096),
        ("profiles", 8192),
        ("curved_connectors", MAX_CURVED_CONNECTORS),
    ):
        if not isinstance(source.get(key), dict) or len(source[key]) > limit:
            raise CurvedConnectorError("Kruhová publikace nemá úplný konečný registr " + key + ".")
    if not isinstance(source.get("pages"), list) or not 1 <= len(source["pages"]) <= 64:
        raise CurvedConnectorError("Kruhová publikace překročila podporovaný počet stránek.")
    project = AuthorProject.from_dict(source)
    return _json(project.snapshot())


def validate_curved_snapshot_binding(data):
    """Close ALL material/source/pose/coverage, separately from native body proof.

    No exporter validator is called here, so staged output validation cannot
    recurse through itself. Returned metadata is detached; only strings cache.
    """
    checks = data.get("construction_checks", {})
    source = checks.get("curved_source_project")
    reports = checks.get("curved_connectors", {})
    hinted = any(
        report.get("source_binding", {}).get("curved_material_inputs")
        for report in checks.get("lofts", {}).values()
        if isinstance(report, dict)
    )
    if source is None and not reports and not hinted:
        return {}
    if not isinstance(source, dict) or not source.get("curved_connectors"):
        raise CurvedConnectorError("Chybí úplný aktuální autorský projekt pro kruhovou publikaci.")
    # Reuse the existing exact JSON preflight budgets, not any export function.
    from archpapercraft.exporter.segmented_output_validation import _json as bounded_json

    source_json = bounded_json(source, sort_keys=False)
    canonical = json.loads(_curved_canonical_snapshot_json(source_json))
    if bounded_json(data) != bounded_json(canonical):
        raise CurvedConnectorError(
            "Kruhová publikace neodpovídá všem skutečným zdrojům a tiskovým dílům."
        )
    return {
        "status": "CANONICAL_SOURCE_AND_COMPLETE_MATERIAL_COVERAGE_VERIFIED",
        "source_project_digest": hashlib.sha256(source_json.encode("utf8")).hexdigest(),
        "connector_ids": list(reports),
        "physical_build": "NOT_VERIFIED",
    }


def _surface_control_box(project, surface_id):
    """Exact affine hull enclosure of continuous material, never render mesh."""
    from .curved_tabs import _sqrt
    from .profile_curves import source_curve

    surface = project.surfaces[surface_id]
    matrix = [[Fraction(value) for value in row] for row in project._surface_matrix(surface_id)]
    boxes = []
    for pid in surface.source_profile_ids():
        profile = project.profiles[pid]
        points = []
        for segment in profile.segments:
            curve = source_curve(profile, segment)
            if curve.kind == "arc":
                center = tuple(map(Fraction, curve.data["center"]))
                radius = max(
                    _sqrt(sum((Fraction(a) - b) ** 2 for a, b in zip(point, center)))[1]
                    for point in (curve.start, curve.end)
                )
                points.extend(
                    (center[0] + x * radius, center[1] + y * radius)
                    for x in (-1, 1)
                    for y in (-1, 1)
                )
            elif curve.kind == "cubic":
                points.extend(
                    tuple(map(Fraction, point))
                    for point in (
                        curve.start,
                        curve.data["control1"],
                        curve.data["control2"],
                        curve.end,
                    )
                )
            elif curve.kind == "line":
                points.extend(tuple(map(Fraction, point)) for point in (curve.start, curve.end))
            else:
                raise CurvedConnectorError("Kontrolní obal okolní křivky není podporovaný.")
        if not points:
            raise CurvedConnectorError("Okolní plocha nemá úplný zdrojový obrys.")
        origin, u, v = (
            tuple(map(Fraction, getattr(profile.plane, key))) for key in ("origin", "u", "v")
        )
        world = []
        for x, y in points:
            local = tuple(o + x * a + y * b for o, a, b in zip(origin, u, v))
            world.append(
                tuple(
                    (_dot(row[:3], local) + row[3]) * Fraction(project.scale) for row in matrix[:3]
                )
            )
        boxes.extend(world)
    # Planar interiors and ruled blends lie in the convex hull of their entire
    # boundary/control hulls. Ignoring holes enlarges this obstruction safely.
    return tuple(
        (min(point[axis] for point in boxes), max(point[axis] for point in boxes))
        for axis in range(3)
    )


def _expanded(box, padding):
    return tuple((low - padding, high + padding) for low, high in box)


def _box_separation(first, second):
    from .curved_tabs import _sqrt

    distances = [max(Fraction(0), a - d, c - b) for (a, b), (c, d) in zip(first, second)]
    return _sqrt(sum(value * value for value in distances))[0]


def _legacy_connector_box(project, connector_id):
    connector = project.connectors[connector_id]
    lengths = [Fraction(connector.width_mm)]
    outlines = [connector.outline_mm]
    for override in connector.tab_overrides.values():
        if "width_mm" in override:
            lengths.append(Fraction(override["width_mm"]))
        outlines.append(override.get("outline_mm", []))
    for outline in outlines:
        lengths.extend(sum(abs(Fraction(value)) for value in point) for point in outline)
    # Every rigid phase preserves distance from the actual source hinge. The
    # complete source-face hull includes that hinge; default tab x stays on it,
    # and explicit custom coordinates receive their entire L1-radius reserve.
    return _expanded(_surface_control_box(project, connector.owner_surface_id), max(lengths))


def _curved_motion_box(project, record, prepared):
    from .curved_tabs import Rim, Tab, _geometry, _sqrt

    report, binding = prepared["source_transfer"], prepared["rim_binding"]
    if "world_frame_singular_bounds" not in report:
        raise CurvedConnectorError("Celý prostor pohybu nemá doložený zdrojový rám.")
    source_radius = tuple(
        Fraction(binding["source_radius_bounds"][key]) for key in ("lower_exact", "upper_exact")
    )
    source_slope = tuple(
        Fraction(binding["source_radial_slope_bounds"][key])
        for key in ("lower_exact", "upper_exact")
    )
    world_upper = Fraction(report["world_frame_singular_bounds"][1])
    world_center = [
        Fraction(value) * Fraction(project.scale)
        for value in binding["world_frame"]["center_model_mm"]
    ]
    extent = Fraction(0)
    rows = {row["tab_id"]: row for row in report["tabs"] if row["status"] != "OFF"}
    for slot in prepared["slots"]:
        if not slot["enabled"]:
            continue
        rim, tab = Rim(**slot["reference_rim"]), Tab(**slot["reference_tab"])
        geometry = _geometry(rim, tab)
        r, k = Fraction(rim.radius_mm), Fraction(rim.radial_slope)
        a = geometry["half_angle"][1]
        dr = max(abs(value - r) for value in source_radius)
        dk = max(abs(value - k) for value in source_slope)
        max_k = max(abs(value) for value in (*source_slope, k))
        h = _sqrt(1 - max_k * max_k)[0]
        if h <= 0:
            raise CurvedConnectorError("Zdrojový ohyb nemá kladnou směrovou mez.")
        displacement = geometry["position_bound_mm"] + dr * a + r * abs(k) * a * a / 2 * dk / h
        # G=Rr0+x*t0+y*d(t), |d|=1. Collar adds the proved D bound.
        # The bijective native chart changes parametrization, not this set.
        radius = world_upper * (
            source_radius[1] + geometry["xe"] + geometry["depth"] + displacement
        )
        radius += Fraction(binding["world_frame_center_error_bound_paper_mm_exact"])
        radius += (
            world_upper
            * Fraction(record.parameters["publication_error_budget_mm"])
            * Fraction(rows[slot["tab_id"]]["source_singular_value_bounds"][1])
        )
        extent = max(extent, radius)
    if extent <= 0:
        raise CurvedConnectorError(
            "Sada nemá žádný doložený aktivní materiál pro prostorovou kontrolu."
        )
    return tuple((value - extent, value + extent) for value in world_center)


def _scene_clearance(project, record, prepared):
    """Conservative whole-phase foreign-material proof, conditional on profile."""
    material = project.material_profile
    if prepared["source_fingerprint"] != _digest(
        project.curved_connector_inputs(record.owner_surface_id)
    ):
        raise CurvedConnectorError("Prostorová kontrola má zastaralý skutečný zdroj.")
    thickness = Fraction(material["thickness_mm"] or 0)
    bend, clearance = Fraction(material["bend_radius_mm"]), Fraction(material["clearance_mm"])
    motion = _expanded(
        _curved_motion_box(project, record, prepared), thickness / 2 + bend + clearance
    )
    other_padding = thickness / 2 + bend
    checked, unresolved = [], []
    physical = project.material_part_ids()
    for sid, surface in sorted(project.surfaces.items()):
        if surface.part_id not in physical or sid in (
            record.owner_surface_id,
            record.receiver_surface_id,
        ):
            continue
        box = _expanded(_surface_control_box(project, sid), other_padding)
        distance = _box_separation(motion, box)
        checked.append(
            {
                "kind": "SOURCE_CONTINUOUS_SURFACE_CONTROL_HULL",
                "id": sid,
                "bounds_exact": _exact_json(box),
                "separation_lower_exact": str(distance),
                "status": "PROVEN_FAR" if distance > 0 else "UNRESOLVED_NEAR",
            }
        )
        if distance <= 0:
            unresolved.append(sid)
    for cid, connector in sorted(project.connectors.items()):
        if not connector.enabled or connector.owner_surface_id not in project.surfaces:
            continue
        if project.surfaces[connector.owner_surface_id].part_id not in physical:
            continue
        box = _expanded(_legacy_connector_box(project, cid), other_padding)
        distance = _box_separation(motion, box)
        checked.append(
            {
                "kind": "LEGACY_TAB_ALL_PHASE_HINGE_RADIUS_HULL",
                "id": cid,
                "bounds_exact": _exact_json(box),
                "separation_lower_exact": str(distance),
                "status": "PROVEN_FAR" if distance > 0 else "UNRESOLVED_NEAR",
            }
        )
        if distance <= 0:
            unresolved.append(cid)
    for other in sorted(project.curved_connectors.values(), key=lambda item: item.id):
        if other.id == record.id or not _has_active_tabs(other):
            continue
        try:
            other_prepared = _prepare_native_slots(project, other)
            box = _expanded(_curved_motion_box(project, other, other_prepared), other_padding)
            distance = _box_separation(motion, box)
            checked.append(
                {
                    "kind": "OTHER_CURVED_TAB_WHOLE_PHASE_HULL",
                    "id": other.id,
                    "bounds_exact": _exact_json(box),
                    "separation_lower_exact": str(distance),
                    "status": "PROVEN_FAR" if distance > 0 else "UNRESOLVED_NEAR",
                }
            )
            if distance <= 0:
                unresolved.append(other.id)
        except (ValidationError, ValueError, KeyError, TypeError):
            unresolved.append(other.id)
            checked.append(
                {
                    "kind": "OTHER_CURVED_TAB_WHOLE_PHASE_HULL",
                    "id": other.id,
                    "status": "UNRESOLVED_SOURCE",
                }
            )
    return {
        "status": (
            "UNRESOLVED"
            if unresolved
            else "PROVEN_FAR"
            if material["thickness_mm"] is not None
            else "UNVERIFIED_MATERIAL"
        ),
        "scope": "ENTIRE_DECLARED_CURVED_MATERIAL_ALL_PHASES_VS_ALL_SELECTED_FOREIGN_MATERIAL",
        "motion_bounds_exact": _exact_json(motion),
        "checked": checked,
        "unresolved_obstacle_ids": sorted(set(unresolved)),
        "material_known": material["thickness_mm"] is not None,
        "physical_build": "NOT_VERIFIED",
    }


def _compact_certificate(check, material_report):
    return {
        "contract": CURVED_CONNECTOR_CONTRACT,
        "status": check["status"],
        "source_transfer_digest": _digest(check["source_transfer"]),
        "scene_digest": _digest(check["scene_clearance"]),
        "material_digest": material_report["canonical_material_digest"],
    }


def _compact_material(check, material_report):
    return {
        "contract": material_report["contract"],
        "canonical_material_digest": material_report["canonical_material_digest"],
        "active_tab_ids": [slot["tab_id"] for slot in check["slots"] if slot["enabled"]],
    }


def _source_display_paths(project, prepared, slot):
    """Floating display of the actual-source map, never a numerical certificate.

    F_s uses the native theta/f/alpha but the current source R/k and common Q,
    as specified in PC007B_SOURCE_TRANSFER_PROOF §2. The interval midpoints
    here only select drawing coordinates; all acceptance uses whole intervals.
    """
    from .curved_tabs import Rim, Tab, _geometry

    rim, tab = Rim(**slot["reference_rim"]), Tab(**slot["reference_tab"])
    shape, binding = _geometry(rim, tab), prepared["rim_binding"]
    native_radius, native_slope = float(shape["radius"]), float(shape["slope"])
    radius = float(
        sum(
            Fraction(binding["source_radius_bounds"][key]) for key in ("lower_exact", "upper_exact")
        )
        / 2
    )
    slope = float(
        sum(
            Fraction(binding["source_radial_slope_bounds"][key])
            for key in ("lower_exact", "upper_exact")
        )
        / 2
    )
    frame = binding["world_frame"]
    angle = math.tau * float(Fraction(tab.center_turn))
    sine, cosine = math.sin(angle), math.cos(angle)

    def world(x, y, phase):
        f = (
            -native_slope
            * x
            * x
            / native_radius
            / (1 + math.sqrt(1 - (native_slope * x / native_radius) ** 2))
            if native_slope
            else 0.0
        )
        theta = (
            math.asin(native_slope * x / native_radius) / native_slope
            if native_slope
            else x / native_radius
        )
        alpha = max(0.0, (float(shape["relief"]) - y) / (float(shape["relief"]) - f))
        if phase == 1:
            radial, vertical = -1.0, 0.0
        else:
            direction = phase * math.pi + (1 - phase) * math.acos(slope)
            radial, vertical = math.cos(direction), math.sin(direction)
        local = (
            radius * (1 - alpha + alpha * math.cos(theta)) + (y - alpha * f) * radial,
            radius * alpha * math.sin(theta) + (1 - alpha) * x,
            (y - alpha * f) * vertical,
        )
        common = (
            local[0] * cosine - local[1] * sine,
            local[0] * sine + local[1] * cosine,
            local[2],
        )
        result = [
            frame["center_model_mm"][axis]
            + sum(
                frame[name][axis] * value
                for name, value in zip(("radial", "tangent", "outward_z"), common, strict=True)
            )
            / project.scale
            for axis in range(3)
        ]
        if not all(math.isfinite(value) for value in result):
            raise CurvedConnectorError("Náhled skutečného zdroje není konečný.")
        return result

    hinge = []
    halfwidth = float(shape["xe"])
    for index in range(17):
        x = halfwidth * (2 * index / 16 - 1)
        f = (
            -native_slope
            * x
            * x
            / native_radius
            / (1 + math.sqrt(1 - (native_slope * x / native_radius) ** 2))
            if native_slope
            else 0.0
        )
        hinge.append(world(x, f, 1))
    glue = [
        world(float(tangent), float(shape["radius"] - radial), 1)
        for radial, tangent in shape["glue_triangle_local"]
    ]
    return {
        "scope": "DISPLAY_ONLY_ACTUAL_SOURCE_INTERVAL_MIDPOINTS_NOT_PROOF",
        "units": "model_mm",
        "phase": 1,
        "hinge_world": hinge,
        "glue_patch_world": [*glue, glue[0][:]],
        "source_radius_bounds_mm": copy.deepcopy(binding["source_radius_bounds"]),
        "source_radial_slope_bounds": copy.deepcopy(binding["source_radial_slope_bounds"]),
        "acceptance_uses_samples": False,
    }


class CurvedConnectorCommands:
    def _curved_domain_material_checks(self, owner_surface_id, bare_part):
        checks, slots = {}, []
        for record in self.curved_connectors.values():
            if record.owner_surface_id != owner_surface_id or not _has_active_tabs(record):
                continue
            prepared = _prepare_native_slots(self, record, bare_part)
            if any(
                slot["enabled"]
                and slot["native_chart_certificate"]["status"] != "CERTIFIED_NATIVE_CHART"
                for slot in prepared["slots"]
            ):
                raise CurvedConnectorError(
                    "Skutečný nativní materiál záložky nemá doložený jednoduchý rám."
                )
            scene = _scene_clearance(self, record, prepared)
            if (
                prepared["source_transfer"]["status"] == "CERTIFIED_TRANSFER"
                and scene["status"] == "PROVEN_FAR"
            ):
                status = "CERTIFIED_APPROXIMATE"
            elif self.material_profile["thickness_mm"] is None and scene["status"] != "UNRESOLVED":
                status = "UNVERIFIED"
            else:
                status = "UNRESOLVED"
            checks[record.id] = {**prepared, "scene_clearance": scene, "status": status}
            slots.extend(prepared["slots"])
        return checks, slots

    def compose_curved_connector_material(self, owner_surface_id, bare_part):
        """Caller for the separately owned actual native material composer."""
        if not self.curved_connector_inputs(owner_surface_id):
            return bare_part
        try:
            from .circular_material import compose_circular_rim_tabs
        except ImportError as exc:
            raise CurvedConnectorError(
                "Skládání nativního kruhového materiálu zatím není dostupné.",
                code="CURVED_MATERIAL_COMPOSER_UNAVAILABLE",
            ) from exc
        checks, slots = self._curved_domain_material_checks(owner_surface_id, bare_part)
        part = compose_circular_rim_tabs(self, bare_part, slots)
        report = copy.deepcopy(getattr(part, "_circular_material_report", None))
        expected = {slot["tab_id"] for slot in slots if slot["enabled"]}
        if not isinstance(report, dict) or set(report.get("active_tab_ids", [])) != expected:
            raise CurvedConnectorError("Skutečný řez pláště neprokazuje úplné identity záložek.")
        report["domain_connector_checks"] = checks
        report["source_native_strain"] = {
            "status": (
                "SOURCE_NATIVE_STRAIN_CERTIFIED"
                if all(
                    check["source_transfer"]["status"] == "CERTIFIED_TRANSFER"
                    for check in checks.values()
                )
                else "UNRESOLVED"
            ),
            "scope": "CURRENT_SOURCE_TO_SAME_ACTUAL_NATIVE_A_L_WHOLE_COLLAR_CHART",
            "pdf_cubic_deformation": "NOT_CLAIMED",
            "physical_build": "NOT_VERIFIED",
        }
        report["domain_status"] = (
            "CERTIFIED_APPROXIMATE"
            if all(check["status"] == "CERTIFIED_APPROXIMATE" for check in checks.values())
            else "UNRESOLVED"
            if any(check["status"] == "UNRESOLVED" for check in checks.values())
            else "UNVERIFIED"
        )
        report["physical_build"] = "NOT_VERIFIED"
        part._circular_material_report = report
        return part

    def curved_connector_material_report(self, owner_surface_id, bare_part=None):
        """Fresh complete material report, never the record's cached approval."""
        from .loft_surface import build_loft_part

        part = (
            self.parts[self.surfaces[owner_surface_id].part_id] if bare_part is None else bare_part
        )
        report = getattr(part, "_circular_material_report", None)
        current = _digest(self.curved_connector_inputs(owner_surface_id))
        if report is None or report.get("inputs_digest") != current:
            part = build_loft_part(self, part)
            report = getattr(part, "_circular_material_report", None)
        if report is None:
            raise CurvedConnectorError(
                "Skutečný nativní materiál pláště nemá čerstvý důkaz spojení."
            )
        actual = _digest(
            {"CUT": part.paths["CUT"], "TABS": part.paths["TABS"], "GUIDES": part.paths["GUIDES"]}
        )
        # The composer's digest covers its command lists, not the path wrappers.
        # Its independent topology/source/area proof is retained in this report.
        return {**copy.deepcopy(report), "actual_geometry_digest": actual}

    def _refresh_curved_material_caches(self, built):
        for part in built.values():
            report = getattr(part, "_circular_material_report", None)
            if report is None:
                continue
            for cid, check in report.get("domain_connector_checks", {}).items():
                record = self.curved_connectors[cid]
                record.source_binding = copy.deepcopy(check["source_binding"])
                record.source_fingerprint = check["source_fingerprint"]
                record.certificate = _compact_certificate(check, report)
                record.material = _compact_material(check, report)

    def _curved_assembly_clearance_key(self):
        from .bend import BendCommands

        base = BendCommands._assembly_clearance_key(self)
        owners = sorted(
            {
                record.owner_surface_id
                for record in self.curved_connectors.values()
                if _has_active_tabs(record) and record.owner_surface_id in self.surfaces
            }
        )
        if not owners:
            return base
        return _digest(
            {
                "base_assembly": base,
                "curved_material_contract": CURVED_CONNECTOR_CONTRACT,
                "curved_material_inputs": [self.curved_connector_inputs(owner) for owner in owners],
            }
        )

    def _curved_legacy_bend_clearance(self, connector_id):
        """Legacy tab consumers must not omit current curved-tab material.

        Unsupported nearby nonplanar/curved material is explicitly unresolved.
        A legacy known collision is preserved even with such foreign uncertainty.
        Far omissions use complete source/whole-phase hull proofs, never meshes.
        """
        from .bend import BendCommands

        records = sorted(
            (record for record in self.curved_connectors.values() if _has_active_tabs(record)),
            key=lambda item: item.id,
        )
        if not records:
            return BendCommands.connector_bend_clearance(self, connector_id)
        key = self._assembly_clearance_key()
        cached = getattr(self, "_curved_legacy_bend_cache", None)
        if cached is not None and cached[0] == key and connector_id in cached[1]:
            return json.loads(cached[1][connector_id])
        connector = self.connectors[connector_id]
        geometry = self._connector_geometry(connector_id)
        if not connector.enabled or not geometry["tabs"]:
            return {"status": "NOT_APPLICABLE", "tabs": [], "message": "Žádná aktivní záložka."}
        profile = self.material_profile
        thickness, bend = (
            Fraction(profile["thickness_mm"] or 0),
            Fraction(profile["bend_radius_mm"]),
        )
        padding = thickness / 2 + bend
        moving = _expanded(
            _legacy_connector_box(self, connector_id), padding + Fraction(profile["clearance_mm"])
        )
        checked, unresolved = [], []
        omitted_surfaces = {
            sid for sid, surface in self.surfaces.items() if surface.kind != "planar"
        }
        for sid in sorted(omitted_surfaces):
            box = _expanded(_surface_control_box(self, sid), padding)
            distance = _box_separation(moving, box)
            checked.append(
                {
                    "id": sid,
                    "kind": "CONTINUOUS_NONPLANAR_SOURCE_CONTROL_HULL",
                    "status": "PROVEN_FAR" if distance > 0 else "UNRESOLVED_NEAR",
                    "separation_lower_exact": str(distance),
                }
            )
            if distance <= 0:
                unresolved.append(sid)
        # The planar kernel cannot reconstruct a tab whose other relation end
        # was omitted. Its whole-phase hinge-radius hull remains a conservative
        # obstacle, instead of allowing a KeyError to erase another collision.
        omitted_connectors = {
            cid
            for cid, value in self.connectors.items()
            if _connector_surface_ids(self, value) & omitted_surfaces
        }
        for cid in sorted(omitted_connectors):
            foreign = self.connectors[cid]
            if not foreign.enabled:
                continue
            distance = _box_separation(moving, _expanded(_legacy_connector_box(self, cid), padding))
            checked.append(
                {
                    "id": cid,
                    "kind": "OMITTED_LEGACY_TAB_ALL_PHASE_HINGE_RADIUS_HULL",
                    "status": "PROVEN_FAR" if distance > 0 else "UNRESOLVED_NEAR",
                    "separation_lower_exact": str(distance),
                }
            )
            if distance <= 0:
                unresolved.append(cid)
        for record in records:
            try:
                packet = _prepare_native_slots(self, record)
                box = _expanded(_curved_motion_box(self, record, packet), padding)
                distance = _box_separation(moving, box)
                checked.append(
                    {
                        "id": record.id,
                        "kind": "CURVED_MATERIAL_ALL_PHASES",
                        "status": "PROVEN_FAR" if distance > 0 else "UNRESOLVED_NEAR",
                        "separation_lower_exact": str(distance),
                    }
                )
                if distance <= 0:
                    unresolved.append(record.id)
            except (ValidationError, ValueError, KeyError, TypeError):
                unresolved.append(record.id)
                checked.append(
                    {
                        "id": record.id,
                        "kind": "CURVED_MATERIAL_ALL_PHASES",
                        "status": "UNRESOLVED_SOURCE",
                    }
                )
        # The straight kernel explicitly supports planar material only. Its
        # remaining scene still supplies every ordinary negative witness.
        view = copy.copy(self)
        view.surfaces = {
            sid: value for sid, value in self.surfaces.items() if sid not in omitted_surfaces
        }
        view.connectors = {
            cid: value for cid, value in self.connectors.items() if cid not in omitted_connectors
        }
        view._assembly_clearance_key = lambda: _digest(
            {"complete_source": key, "planar_view": sorted(view.surfaces)}
        )
        try:
            result = copy.deepcopy(BendCommands.connector_bend_clearance(view, connector_id))
        except (ValidationError, ValueError, KeyError, StopIteration):
            result = {
                "status": "UNRESOLVED",
                "tabs": [],
                "message": "Přímý ohyb nemá doloženou podporovanou zdrojovou geometrii.",
            }
        if unresolved and result["status"] != "COLLISION":
            result.update(
                status="UNRESOLVED",
                message=(
                    "Prostor ohybu u kruhového nebo nerovinného materiálu zatím nelze doložit. "
                    "Upravte konstrukci nebo polohu dotčených dílů."
                ),
            )
            for tab in result.get("tabs", []):
                if tab.get("status") != "COLLISION":
                    tab["status"] = "UNRESOLVED"
        result["curved_material_dependency"] = {
            "status": (
                "UNRESOLVED"
                if unresolved
                else "PROVEN_FAR"
                if profile["thickness_mm"] is not None
                else "UNVERIFIED_MATERIAL"
            ),
            "material_known": profile["thickness_mm"] is not None,
            "source_digest": key,
            "checked": checked,
            "unresolved_ids": sorted(set(unresolved)),
            "scope": "ALL_CURRENT_CURVED_MATERIAL_AND_CONTINUOUS_NONPLANAR_FOREIGN_SURFACES",
        }
        if cached is None or cached[0] != key:
            self._curved_legacy_bend_cache = key, {}
        self._curved_legacy_bend_cache[1][connector_id] = _json(_exact_json(result))
        return result

    @atomic
    def add_curved_connector(
        self,
        owner_surface_id,
        rim_side,
        receiver_surface_id,
        *,
        min_glue_area_mm2,
        receiver_side="outside",
        count=12,
        depth_mm=9.5,
        relief_mm=0.6,
        nominal_base_mm=None,
        gap_mm=None,
        max_position_mm=0.01,
        max_differential_deformation=0.01,
        publication_error_budget_mm=0.000001,
        name="Dělené kruhové chlopně",
    ):
        values = {
            "count": count,
            "depth_mm": depth_mm,
            "relief_mm": relief_mm,
            "nominal_base_mm": nominal_base_mm,
            "gap_mm": gap_mm,
            "min_glue_area_mm2": min_glue_area_mm2,
            "max_position_mm": max_position_mm,
            "max_differential_deformation": max_differential_deformation,
            "publication_error_budget_mm": publication_error_budget_mm,
        }
        _parameters(values)
        for key, value in values.items():
            if key != "count" and value is not None:
                values[key] = number(value)
        cid = identity()
        self.curved_connectors[cid] = CurvedConnector(
            cid,
            name,
            owner_surface_id,
            rim_side,
            receiver_surface_id,
            receiver_side,
            values,
            [identity() for _ in range(count)],
        )
        # Creating author intent never silently certifies or recomputes it.
        self._touch([owner_surface_id])
        return cid

    def preview_curved_connector(self, *args, **kwargs):
        clone = copy.deepcopy(self)
        cid = clone.add_curved_connector(*args, **kwargs)
        record = clone.curved_connectors[cid]
        material = None
        try:
            clone.recompute([clone.surfaces[record.owner_surface_id].part_id])
            material = clone.curved_connector_material_report(record.owner_surface_id)
        except (ValidationError, ValueError, KeyError, AttributeError) as exc:
            error = str(exc)
        else:
            error = None
        result = clone.curved_connector_status(cid)
        return {
            **result,
            "preview_only": True,
            "can_confirm": result["status"] == "CERTIFIED_APPROXIMATE",
            "can_create_authored_intent": True,
            "material_report": material,
            "material_error": error,
            "proposed_record": asdict(clone.curved_connectors[cid]),
        }

    def curved_connector_geometry(self, connector_id):
        """Readonly modeler selection packet, with explicit drawing-only 3D paths.

        Stale/unresolved sources return authored slot identities and repair state
        but no apparently current paper/assembled overlay. Every active command
        is the same actual packet consumed by the canonical material composer.
        """
        status = self.curved_connector_status(connector_id)
        record = self.curved_connectors[connector_id]
        rows = []
        for index, tab_id in enumerate(record.slot_ids):
            override = record.tab_overrides.get(tab_id, {})
            in_count = index < record.parameters["count"]
            rows.append(
                {
                    "id": tab_id,
                    "index": index,
                    "in_current_count": in_count,
                    "enabled": record.enabled and in_count and override.get("enabled", True),
                    "tip_offset_mm": override.get("tip_offset_mm", 0),
                    "paper_native_loop": None,
                    "paper_shared_base_commands": None,
                    "paper_cut_side_commands": None,
                    "source_intervals": [],
                    "assembled_display": None,
                }
            )
        if status["status"] == "CERTIFIED_APPROXIMATE":
            prepared = _prepare_native_slots(self, record)
            packets = {slot["tab_id"]: slot for slot in prepared["slots"]}
            for row in rows:
                if not row["enabled"]:
                    continue
                slot = packets[row["id"]]
                for key in (
                    "paper_native_loop",
                    "paper_shared_base_commands",
                    "paper_cut_side_commands",
                    "source_intervals",
                ):
                    row[key] = copy.deepcopy(slot[key])
                row["assembled_display"] = _source_display_paths(self, prepared, slot)
        return {
            **status,
            "contract": "READONLY_CURVED_SELECTION_NATIVE_PACKET_AND_SOURCE_DISPLAY_V1",
            "mode": "APPROXIMATE",
            "owner_part_id": self.part_for_surface(record.owner_surface_id),
            "receiver_part_id": self.part_for_surface(record.receiver_surface_id),
            "rim_side": record.rim_side,
            "receiver_side": record.receiver_side,
            "all_tabs": rows,
            "display_is_proof": False,
        }

    @atomic
    def update_curved_connector(self, connector_id, **changes):
        record = self.curved_connectors[connector_id]
        extra = {"receiver_surface_id", "receiver_side", "enabled", "name"}
        if set(changes) - PARAMETERS - extra:
            raise ValidationError("Neznámá úprava kruhového spoje.")
        if "enabled" in changes and type(changes["enabled"]) is not bool:
            raise ValidationError("Vypnutí sady záložek musí být výslovná volba.")
        params = copy.deepcopy(record.parameters)
        params.update({key: value for key, value in changes.items() if key in PARAMETERS})
        _parameters(params)
        for key, value in params.items():
            if key != "count" and value is not None:
                params[key] = number(value)
        modified = params != record.parameters or any(
            getattr(record, key) != value for key, value in changes.items() if key in extra
        )
        if not modified:
            return
        record.parameters = params
        for key, value in changes.items():
            if key in extra:
                setattr(record, key, value)
        while len(record.slot_ids) < params["count"]:
            record.slot_ids.append(identity())
        record.revision += 1
        self._touch([] if set(changes) == {"name"} else [record.owner_surface_id])

    @atomic
    def set_curved_tab(self, connector_id, tab_id, *, enabled=None, tip_offset_mm=None):
        record = self.curved_connectors[connector_id]
        if tab_id not in record.slot_ids:
            raise ValidationError("Vyberte existující slot kruhové záložky.")
        changes = copy.deepcopy(record.tab_overrides.get(tab_id, {}))
        if enabled is not None:
            if type(enabled) is not bool:
                raise ValidationError("Vypnutí záložky musí být výslovná volba.")
            changes["enabled"] = enabled
        if tip_offset_mm is not None:
            changes["tip_offset_mm"] = number(tip_offset_mm, "Posun vrcholu záložky")
        if changes == record.tab_overrides.get(tab_id, {}):
            return
        record.tab_overrides[tab_id] = changes
        record.revision += 1
        self._touch([record.owner_surface_id])

    @atomic
    def remove_curved_connector(self, connector_id):
        owner = self.curved_connectors.pop(connector_id).owner_surface_id
        self._touch([owner])

    def curved_connector_status(self, connector_id):
        if connector_id not in self.curved_connectors:
            raise ValidationError("Vyberte existující kruhový spoj.")
        record = self.curved_connectors[connector_id]
        source = self.curved_connector_inputs(record.owner_surface_id)
        fingerprint = _digest(source)
        if not _has_active_tabs(record):
            status, code, message = (
                "NOT_APPLICABLE",
                "CURVED_CONNECTOR_OFF",
                "Sada kruhových záložek nebo všechny její sloty jsou vypnuté.",
            )
        elif record.source_binding and fingerprint != record.source_fingerprint:
            status, code, message = (
                "STALE",
                "CURVED_CONNECTOR_STALE",
                "Zdroj nebo okolní konstrukce se změnily. Přepočítejte celý díl pláště.",
            )
        elif (
            not record.source_binding
            or self.parts[self.surfaces[record.owner_surface_id].part_id].stale
        ):
            status, code, message = (
                "STALE",
                "CURVED_MATERIAL_RECOMPUTE",
                "Přepočítejte celý díl pláště pro aktuální kruhové záložky.",
            )
        else:
            try:
                from .loft_surface import build_loft_part

                part = self.parts[self.surfaces[record.owner_surface_id].part_id]
                rebuilt = build_loft_part(self, part)
                if any(
                    getattr(part, key) != getattr(rebuilt, key)
                    for key in ("paths", "polygons", "edges", "labels")
                ):
                    raise CurvedConnectorError(
                        "Uložený materiál kruhových chlopní se neshoduje se zdrojem."
                    )
                report = rebuilt._circular_material_report
                check = report["domain_connector_checks"][record.id]
                if record.certificate != _compact_certificate(
                    check, report
                ) or record.material != _compact_material(check, report):
                    raise CurvedConnectorError(
                        "Uložený důkaz kruhového materiálu je poškozený; přepočítejte díl."
                    )
                status = check["status"]
                code = (
                    "CURVED_SOURCE_AND_MATERIAL_CERTIFIED"
                    if status == "CERTIFIED_APPROXIMATE"
                    else "CURVED_SOURCE_OR_SCENE_UNRESOLVED"
                )
                message = (
                    "Zdroj, nativní materiál a zadaný digitální prostor pohybu jsou doložené."
                    if status == "CERTIFIED_APPROXIMATE"
                    else "Pohyb nebo lepicí plocha záložek nejsou v aktuální sestavě doložené."
                )
                if self.material_profile["thickness_mm"] is None:
                    message = "Zadejte tloušťku papíru; bez ní není prostor pohybu doložený."
            except (ValidationError, ValueError, KeyError, AttributeError) as exc:
                status, code, message = "UNRESOLVED", "SOURCE_TRANSFER_UNRESOLVED", str(exc)
        if not _has_active_tabs(record):
            pass
        elif status == "CERTIFIED_APPROXIMATE" and record.source_fingerprint != fingerprint:
            status, code, message = (
                "STALE",
                "CURVED_CONNECTOR_STALE",
                "Zdroj kruhového spoje není aktuální.",
            )
        return {
            "status": status,
            "code": code,
            "message": message,
            "connector_id": record.id,
            "owner_surface_id": record.owner_surface_id,
            "receiver_surface_id": record.receiver_surface_id,
            "current_source_fingerprint": fingerprint,
            "source_fingerprint": record.source_fingerprint,
            "scope": "SOURCE_TRANSFER_AND_COMPLETE_ACTUAL_MATERIAL_REQUIRED",
            "physical_build": "NOT_VERIFIED",
        }

    def curved_connector_issues(self):
        result = []
        for record in self.curved_connectors.values():
            report = self.curved_connector_status(record.id)
            if report["status"] not in ("NOT_APPLICABLE", "CERTIFIED_APPROXIMATE"):
                part = self.surfaces[record.owner_surface_id].part_id
                result.append(
                    Issue(
                        "curved:" + record.id,
                        report["code"],
                        "error",
                        report["message"],
                        (part,),
                        digest=_digest(report),
                    )
                )
        return result

    def curved_connector_inputs(self, owner_surface_id):
        """Complete authored dependencies, excluding proof/cache recursion.

        This input belongs in part_input and publisher canonical source binding.
        Every selected material face is included, including unconnected faces.
        Layout and unrelated labels are independent of assembled geometry.
        """
        records = [
            record
            for record in self.curved_connectors.values()
            if record.owner_surface_id == owner_surface_id and _has_active_tabs(record)
        ]
        if not records:
            return {}
        material_ids = self.material_part_ids()
        surfaces = {
            sid: surface
            for sid, surface in self.surfaces.items()
            if surface.part_id in material_ids
        }
        profile_ids = {pid for surface in surfaces.values() for pid in surface.source_profile_ids()}
        return {
            "contract": CURVED_CONNECTOR_CONTRACT,
            "owner_surface_id": owner_surface_id,
            "scale": self.scale,
            "material_profile": copy.deepcopy(self.material_profile),
            "curved_connectors": {
                record.id: _authored(record)
                for record in sorted(self.curved_connectors.values(), key=lambda record: record.id)
                if _has_active_tabs(record) and record.owner_surface_id in surfaces
            },
            "bound_sources": {
                sid: {
                    "surface": asdict(self.surfaces[sid]),
                    "profiles": [
                        asdict(self.profiles[pid])
                        for pid in self.surfaces[sid].source_profile_ids()
                    ],
                }
                for sid in sorted(
                    {
                        sid
                        for record in records
                        for sid in (record.owner_surface_id, record.receiver_surface_id)
                    }
                )
            },
            "surfaces": {sid: asdict(surface) for sid, surface in sorted(surfaces.items())},
            "profiles": {pid: asdict(self.profiles[pid]) for pid in sorted(profile_ids)},
            **({"profile_subdivisions": copy.deepcopy({
                key: value for key, value in self.profile_subdivisions.items()
                if value["history"]["profile_id"] in profile_ids
            })} if any(value["history"]["profile_id"] in profile_ids
                       for value in self.profile_subdivisions.values()) else {}),
            "parts": {
                pid: {
                    "id": pid,
                    "name": self.parts[pid].name,
                    "number": self.parts[pid].number,
                    "lineage": list(self.parts[pid].lineage),
                    "surface_ids": list(self.parts[pid].surface_ids),
                    "frame": asdict(self.parts[pid].frame),
                    "front_side": self.parts[pid].front_side,
                }
                for pid in sorted(material_ids)
            },
            "joints": {
                key: asdict(value)
                for key, value in sorted(self.joints.items())
                if {value.surface_a, value.surface_b} <= set(surfaces)
            },
            "attachments": {
                key: asdict(value)
                for key, value in sorted(self.attachments.items())
                if {value.source_surface_id, value.target_surface_id} <= set(surfaces)
            },
            "connectors": {
                key: asdict(value)
                for key, value in sorted(self.connectors.items())
                if value.owner_surface_id in surfaces
            },
        }

    def _validate_curved_connectors(self):
        if (
            not isinstance(self.curved_connectors, dict)
            or len(self.curved_connectors) > MAX_CURVED_CONNECTORS
        ):
            raise ValidationError("Neplatný nebo příliš velký registr kruhových chlopní.")
        ids, occupied = [], set()
        material_ids = self.material_part_ids()
        for key, record in self.curved_connectors.items():
            uuid(key)
            if (
                key != record.id
                or not isinstance(record.name, str)
                or type(record.enabled) is not bool
            ):
                raise ValidationError("Neplatná identita nebo stav kruhové chlopně.")
            if type(record.revision) is not int or record.revision < 1:
                raise ValidationError("Neplatná revize kruhové chlopně.")
            if (
                record.owner_surface_id not in self.surfaces
                or record.receiver_surface_id not in self.surfaces
            ):
                raise ValidationError("Kruhová chlopeň odkazuje na chybějící skutečnou plochu.")
            owner, receiver = (
                self.surfaces[record.owner_surface_id],
                self.surfaces[record.receiver_surface_id],
            )
            if owner.id == receiver.id or owner.part_id == receiver.part_id:
                raise ValidationError("Kruhový plášť a příjemce musí být různé materiálové díly.")
            if (
                owner.kind != "ruled_loft"
                or receiver.kind != "planar"
                or record.rim_side not in ("first", "second")
                or record.receiver_side not in ("inside", "outside")
            ):
                raise ValidationError(
                    "Zvolte kruhový okraj pláště a stranu skutečného rovinného příjemce."
                )
            if record.enabled and {owner.part_id, receiver.part_id} - material_ids:
                raise ValidationError(
                    "Kruhové chlopně nesmějí spojovat tiskový materiál s netisknoucí referencí."
                )
            location = owner.id, record.rim_side
            if location in occupied:
                raise ValidationError("Kruhový okraj už má vlastní sadu záložek.")
            occupied.add(location)
            _parameters(record.parameters)
            if (
                not isinstance(record.slot_ids, list)
                or not record.parameters["count"] <= len(record.slot_ids) <= MAX_CURVED_SLOTS
                or len(set(record.slot_ids)) != len(record.slot_ids)
            ):
                raise ValidationError("Kruhové záložky potřebují úplné stabilní identity slotů.")
            for value in record.slot_ids:
                uuid(value)
            if not isinstance(record.tab_overrides, dict) or set(record.tab_overrides) - set(
                record.slot_ids
            ):
                raise ValidationError("Úprava kruhové záložky nemá platný slot.")
            for override in record.tab_overrides.values():
                if not isinstance(override, dict) or set(override) - {"enabled", "tip_offset_mm"}:
                    raise ValidationError("Neznámá autorská úprava trojúhelníkové záložky.")
                if "enabled" in override and type(override["enabled"]) is not bool:
                    raise ValidationError("Vypnutí záložky musí být výslovná volba.")
                if "tip_offset_mm" in override:
                    number(override["tip_offset_mm"], "Posun vrcholu záložky")
            for field in ("source_binding", "certificate", "material"):
                if not isinstance(getattr(record, field), dict):
                    raise ValidationError("Odvozený důkaz kruhové chlopně musí být objekt.")
            if not isinstance(record.source_fingerprint, str):
                raise ValidationError("Kruhová chlopeň nemá platnou zdrojovou vazbu.")
            if (
                record.source_binding
                and _digest(record.source_binding) != record.source_fingerprint
            ):
                raise ValidationError("Zdrojová vazba kruhové chlopně má rozporný otisk.")
            ids.extend([record.id, *record.slot_ids])
        return ids
