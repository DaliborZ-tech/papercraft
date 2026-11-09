"""Planar material projection, seams, tabs and footprint validation."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict

import numpy as np
from shapely import Polygon, box
from shapely.ops import unary_union

from .attachments import (
    attachment_geometry,
    connector_shapes,
    edge_source,
    source_outward,
    trace_connector_contact,
)
from .errors import ValidationError
from .geometry import material_polygon, page_points, path, signed_area
from .model import Issue

ROLES = ("CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "GUIDES")


def digest(data):
    return hashlib.sha256(
        json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def part_input(project, part):
    touched = set(part.surface_ids)
    joints = [j for j in project.joints.values() if {j.surface_a, j.surface_b} & touched]
    for joint in joints:
        touched.update((joint.surface_a, joint.surface_b))
    attachments = [
        a
        for a in project.attachments.values()
        if {a.source_surface_id, a.target_surface_id} & touched
    ]
    for attachment in attachments:
        touched.update((attachment.source_surface_id, attachment.target_surface_id))
    surfaces = {sid: asdict(project.surfaces[sid]) for sid in sorted(touched)}
    profile_ids = {
        pid
        for sid in touched
        for pid in [project.surfaces[sid].profile_id, *project.surfaces[sid].hole_profile_ids]
    }
    return digest(
        {
            "scale": project.scale,
            "surfaces": surfaces,
            "profiles": {pid: asdict(project.profiles[pid]) for pid in sorted(profile_ids)},
            "joints": [asdict(j) for j in sorted(joints, key=lambda j: j.id)],
            "attachments": [asdict(a) for a in sorted(attachments, key=lambda a: a.id)],
            "connectors": {
                j.connector_id: asdict(project.connectors[j.connector_id])
                for j in [*joints, *attachments]
                if j.connector_id
            },
            "frame": asdict(part.frame),
            "front_side": part.front_side,
            "surface_ids": part.surface_ids,
            "name": part.name,
        }
    )


def _rotation(angle):
    return np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])


def _frame_map(project, part):
    frame = part.frame
    if frame.root_surface_id not in part.surface_ids:
        raise ValidationError("ANCHOR_UNRESOLVED: kořen dílu chybí.")
    profile = project.profiles[project.surfaces[frame.root_surface_id].profile_id]
    vertex, segment = profile.vertex(frame.anchor_vertex_id), profile.segment(frame.axis_segment_id)
    if vertex is None or segment is None or segment.kind != "line":
        raise ValidationError("ANCHOR_UNRESOLVED: zvolte znovu kotvu a směr dílu.")
    start, end = (
        profile.vertex(segment.start_vertex_id).point,
        profile.vertex(segment.end_vertex_id).point,
    )
    axis = np.asarray(end) - start
    if np.linalg.norm(axis) <= 1e-9:
        raise ValidationError("ANCHOR_UNRESOLVED: směr kotvy je nulový.")
    rotation = _rotation(-math.atan2(axis[1], axis[0])) * project.scale
    return rotation, -rotation @ np.asarray(vertex.point)


def _map_points(points, mapping):
    rotation, offset = mapping
    return np.asarray(points, dtype=float) @ rotation.T + offset


def _edge_points(project, surface_id, edge_id):
    return edge_source(project, surface_id, edge_id)[2]


def edge_world(project, surface_id, edge_id):
    return project._surface_world_points(surface_id, _edge_points(project, surface_id, edge_id))


def validate_joint_contact(project, joint):
    if joint.unresolved:
        raise ValidationError("REFERENCE_UNRESOLVED: po změně obrysu vyberte znovu hrany spoje.")
    a, b = (
        edge_world(project, joint.surface_a, joint.edge_a),
        edge_world(project, joint.surface_b, joint.edge_b),
    )
    tolerance = max(1e-6, 1e-9 * float(np.linalg.norm(a[1] - a[0])))
    if abs(np.linalg.norm(a[1] - a[0]) - np.linalg.norm(b[1] - b[0])) > tolerance:
        raise ValidationError("Hrany spoje mají různé fyzické délky.")
    reversed_match = max(np.linalg.norm(a[0] - b[1]), np.linalg.norm(a[1] - b[0]))
    direct_match = max(np.linalg.norm(a[0] - b[0]), np.linalg.norm(a[1] - b[1]))
    if min(reversed_match, direct_match) > tolerance:
        raise ValidationError("Hrany se v prostoru nepotkávají. Nejprve přisuňte plochy k sobě.")
    return reversed_match <= direct_match


def _polygon_loops(polygon):
    if polygon.geom_type == "Polygon":
        return [
            path(list(polygon.exterior.coords)[:-1], True),
            *[path(list(r.coords)[:-1], True) for r in polygon.interiors],
        ]
    if polygon.geom_type == "MultiPolygon":
        return [p for geometry in polygon.geoms for p in _polygon_loops(geometry)]
    raise ValidationError("Rozvin nevytvořil plošný materiál.")


def fold_role(project, source_id, target_id, edge_id, front_side):
    a, b = project.world_geometry(source_id), project.world_geometry(target_id)
    world = edge_world(project, source_id, edge_id)
    tangent = (world[1] - world[0]) / np.linalg.norm(world[1] - world[0])
    angle = math.atan2(
        float(np.dot(tangent, np.cross(a["normal"], b["normal"]))),
        float(np.dot(a["normal"], b["normal"])),
    )
    if front_side == "inside":
        angle = -angle
    return "GUIDES" if abs(angle) < 1e-10 else ("FOLD_MOUNTAIN" if angle > 0 else "FOLD_VALLEY")


def connector_contact(project, joint, connector):
    """Nominal straight-hinge footprint after folding into the receiver plane."""
    validate_joint_contact(project, joint)
    sid = joint.surface_b if connector.owner_surface_id == joint.surface_a else joint.surface_a
    edge_id = joint.edge_b if sid == joint.surface_b else joint.edge_a
    surface = project.surfaces[sid]
    profile = project.profiles[surface.profile_id]
    edge = _edge_points(project, sid, edge_id) * project.scale
    tangent = (edge[1] - edge[0]) / np.linalg.norm(edge[1] - edge[0])
    inward = np.array([-tangent[1], tangent[0]])
    if signed_area(profile.points) < 0:
        inward = -inward
    target = material_polygon(
        np.array(profile.points) * project.scale,
        [np.array(project.profiles[h].points) * project.scale for h in surface.hole_profile_ids],
    )
    owner = connector.owner_surface_id
    owner_edge = joint.edge_a if owner == joint.surface_a else joint.edge_b
    owner_world = edge_world(project, owner, owner_edge)
    target_world = edge_world(project, sid, edge_id)
    reverse = math.dist(owner_world[0], target_world[1]) < math.dist(
        owner_world[0], target_world[0]
    )
    start = edge[1] if reverse else edge[0]
    axis = -tangent if reverse else tangent
    polygons, tabs = [], []
    for tab in connector_shapes(connector, math.dist(*edge)):
        points = start + tab["points"][:, :1] * axis + tab["points"][:, 1:] * inward
        footprint = Polygon(points)
        polygons.append(footprint)
        tabs.append(
            {
                "tab_id": tab["id"],
                "footprint_uv_mm": points.tolist(),
                "nominal_area_mm2": footprint.area,
                "available_area_mm2": footprint.intersection(target).area,
                "receiver_surface_id": sid,
                "receiver_side": connector.receiver_side,
            }
        )
    footprint = unary_union(polygons)
    return {
        "nominal_area_mm2": footprint.area,
        "available_area_mm2": footprint.intersection(target).area,
        "receiver_surface_id": sid,
        "footprint": tabs[0]["footprint_uv_mm"] if tabs else [],
        "tabs": tabs,
    }


def build_part(project, old_part):
    part = copy.deepcopy(old_part)
    part.paths = {role: [] for role in ROLES}
    part.polygons, part.edges, part.labels = {}, [], []
    maps = {part.frame.root_surface_id: _frame_map(project, part)}
    for joint in project.joints.values():
        if {joint.surface_a, joint.surface_b} & set(part.surface_ids):
            validate_joint_contact(project, joint)
    folds = [
        j for j in project.joints.values() if j.mode == "fold" and j.surface_a in part.surface_ids
    ]
    if (
        any(j.surface_b not in part.surface_ids for j in folds)
        or len(folds) != len(part.surface_ids) - 1
    ):
        raise ValidationError("Přehyby dílu netvoří úplný strom.")
    while len(maps) < len(part.surface_ids):
        progressed = False
        for joint in folds:
            a, b, ea, eb = joint.surface_a, joint.surface_b, joint.edge_a, joint.edge_b
            if a not in maps and b in maps:
                a, b, ea, eb = b, a, eb, ea
            if a not in maps or b in maps:
                continue
            reversed_match = validate_joint_contact(project, joint)
            target = _map_points(_edge_points(project, a, ea), maps[a])
            source = _edge_points(project, b, eb)
            if reversed_match:
                source = source[::-1]
            vector_a, vector_b = target[1] - target[0], source[1] - source[0]
            angle = math.atan2(vector_a[1], vector_a[0]) - math.atan2(vector_b[1], vector_b[0])
            rotation = _rotation(angle) * project.scale
            maps[b] = rotation, target[0] - rotation @ source[0]
            progressed = True
        if not progressed:
            raise ValidationError("Přehyby obsahují cyklus nebo chybějící plochu.")
    material = []
    for sid in part.surface_ids:
        surface = project.surfaces[sid]
        profiles = [
            project.profiles[pid] for pid in [surface.profile_id, *surface.hole_profile_ids]
        ]
        loops = [_map_points(profile.points, maps[sid]).tolist() for profile in profiles]
        polygon = material_polygon(loops[0], loops[1:])
        reference = (
            project._source_polygon(surface.profile_id, surface.hole_profile_ids).area
            * project.scale
            * project.scale
        )
        if not math.isfinite(reference) or abs(polygon.area - reference) > max(
            0.01, 1e-6 * reference
        ):
            raise ValidationError("Rozvin ztrácí požadovanou plošnou přesnost.")
        for profile, flattened in zip(profiles, loops):
            original = np.asarray(profile.points)
            flat = np.asarray(flattened)
            expected_lengths = (
                np.linalg.norm(np.roll(original, -1, axis=0) - original, axis=1) * project.scale
            )
            actual_lengths = np.linalg.norm(np.roll(flat, -1, axis=0) - flat, axis=1)
            if not np.isfinite(flat).all() or np.any(
                abs(expected_lengths - actual_lengths) > np.maximum(0.01, 1e-6 * expected_lengths)
            ):
                raise ValidationError("Rozvin ztrácí požadovanou délkovou přesnost.")
        if any(polygon.intersection(previous).area > 1e-8 for previous in material):
            raise ValidationError(
                "Plochy se po rozvinutí překrývají. Přidejte řez nebo jinak rozdělte díl."
            )
        material.append(polygon)
        part.polygons[sid] = loops
        for profile in profiles:
            for edge in profile.segments:
                points = _map_points(_edge_points(project, sid, edge.id), maps[sid])
                part.edges.append(
                    {
                        "surface_id": sid,
                        "edge_id": edge.id,
                        "start": points[0].tolist(),
                        "end": points[1].tolist(),
                    }
                )
    tabs = []
    for joint in project.joints.values():
        if joint.surface_a not in part.surface_ids and joint.surface_b not in part.surface_ids:
            continue
        sid, edge_id = (
            (joint.surface_a, joint.edge_a)
            if joint.surface_a in part.surface_ids
            else (joint.surface_b, joint.edge_b)
        )
        points = _map_points(_edge_points(project, sid, edge_id), maps[sid])
        if joint.mode == "fold":
            if sid != joint.surface_a:
                continue
            role = fold_role(
                project, joint.surface_a, joint.surface_b, joint.edge_a, part.front_side
            )
            part.paths[role].append(path(points))
        else:
            center = points.mean(axis=0)
            part.labels.append(
                {
                    "text": f"J{joint.number}",
                    "x": float(center[0]),
                    "y": float(center[1]),
                    "size_mm": 2.0,
                }
            )
        if not joint.connector_id or joint.mode != "cut":
            continue
        connector = project.connectors[joint.connector_id]
        if connector.owner_surface_id not in part.surface_ids:
            continue
        sid = connector.owner_surface_id
        edge_id = joint.edge_a if sid == joint.surface_a else joint.edge_b
        points = _map_points(_edge_points(project, sid, edge_id), maps[sid])
        tangent = (points[1] - points[0]) / np.linalg.norm(points[1] - points[0])
        outward = np.array([tangent[1], -tangent[0]])
        outer = part.polygons[sid][0]
        if signed_area(outer) < 0:
            outward = -outward
        receiver = joint.surface_b if sid == joint.surface_a else joint.surface_a
        role = fold_role(project, sid, receiver, edge_id, part.front_side)
        for shape in connector_shapes(connector, math.dist(*points)):
            tab = points[0] + shape["points"][:, :1] * tangent + shape["points"][:, 1:] * outward
            tab_polygon = Polygon(tab)
            if any(tab_polygon.intersection(p).area > 1e-8 for p in [*material, *tabs]):
                raise ValidationError(
                    "FLAT_CONNECTOR_COLLISION: chlopeň překrývá vlastní materiál "
                    "nebo sousední záložku."
                )
            tabs.append(tab_polygon)
            part.paths["TABS"].append(path(tab, True))
            hinge = points[0] + shape["hinge"][:, :1] * tangent
            part.paths[role].append(path(hinge))
    for attachment in project.attachments.values():
        source, target = attachment.source_surface_id, attachment.target_surface_id
        if not {source, target} & set(part.surface_ids):
            continue
        contact = attachment_geometry(project, attachment)
        # Glue marks are guides, never cuts. A mark on the reverse is not silently
        # mirrored onto the currently printed face.
        if target in maps and attachment.target_side == part.front_side:
            region = contact.get("target_region_uv", contact["target_uv"])
            points = _map_points(region, maps[target])
            part.paths["GUIDES"].append(path(points, attachment.kind == "glue_region"))
            center = points.mean(axis=0)
            part.labels.append(
                {
                    "text": f"A{attachment.number}",
                    "x": float(center[0]),
                    "y": float(center[1]),
                    "size_mm": 2.0,
                }
            )
        if source not in maps:
            continue
        source_points = _map_points(contact["source_uv"], maps[source])
        center = source_points.mean(axis=0)
        part.labels.append(
            {
                "text": f"A{attachment.number} · "
                + ("rub" if attachment.target_side == "inside" else "líc"),
                "x": float(center[0]),
                "y": float(center[1]),
                "size_mm": 2.0,
            }
        )
        if attachment.connector_id is None:
            continue
        connector = project.connectors[attachment.connector_id]
        tangent = (source_points[1] - source_points[0]) / math.dist(*source_points)
        _, source_normal = source_outward(project, source, attachment.source_edge_id)
        flat_normal = maps[source][0] @ source_normal / project.scale
        folded = trace_connector_contact(project, attachment, connector)
        angle = math.radians(folded[0]["fold_angle_deg"]) if folded else 0
        if part.front_side == "inside":
            angle = -angle
        role = "GUIDES" if abs(angle) < 1e-10 else ("FOLD_MOUNTAIN" if angle > 0 else "FOLD_VALLEY")
        for shape in connector_shapes(connector, math.dist(*source_points)):
            points = (
                source_points[0]
                + shape["points"][:, :1] * tangent
                + shape["points"][:, 1:] * flat_normal
            )
            polygon = Polygon(points)
            if any(polygon.intersection(p).area > 1e-8 for p in [*material, *tabs]):
                raise ValidationError(
                    "FLAT_CONNECTOR_COLLISION: chlopeň překrývá vlastní materiál "
                    "nebo sousední záložku."
                )
            tabs.append(polygon)
            part.paths["TABS"].append(path(points, True))
            part.paths[role].append(path(source_points[0] + shape["hinge"][:, :1] * tangent))
    union = unary_union([*material, *tabs])
    part.paths["CUT"] = _polygon_loops(union)
    label_at = material[0].representative_point()
    part.labels.insert(0, {"text": part.name, "x": label_at.x, "y": label_at.y, "size_mm": 2.5})
    part.stale = False
    part.input_digest = part_input(project, part)
    # Layout edits advance the document revision without changing this source.
    # Rebuilding an already current part must not turn a saved model dirty.
    if old_part.stale or part.input_digest != old_part.input_digest:
        part.source_revision = project.revision
    return part


def part_material(part):
    polygons = [material_polygon(loops[0], loops[1:]) for loops in part.polygons.values()]
    polygons.extend(Polygon(p["points"]) for p in part.paths["TABS"])
    return unary_union(polygons)


def geometry_payload(part):
    return {
        key: copy.deepcopy(getattr(part, key)) for key in ("polygons", "paths", "labels", "edges")
    }


def validate_layout(project):
    issues, materials = [], {}

    def issue(code, message, parts=(), severity="error", joint_id=None, evidence=None):
        issue_id = digest([code, sorted(parts), joint_id])[:24]
        relevant = {}
        for pid in parts:
            part = project.parts.get(pid)
            if part is not None:
                placement = project.placements.get(pid)
                page = next(
                    (p for p in project.pages if placement and p.id == placement.page_id), None
                )
                relevant[pid] = {
                    "input": part.input_digest,
                    "placement": asdict(placement) if placement else None,
                    "page": asdict(page) if page else None,
                }
        signature = digest([issue_id, relevant] + ([evidence] if evidence is not None else []))
        issues.append(
            Issue(
                issue_id,
                code,
                severity,
                message,
                tuple(parts),
                joint_id,
                signature,
                project.acknowledgements.get(issue_id) == signature,
            )
        )

    try:
        project.validate()
    except (
        ValidationError,
        TypeError,
        KeyError,
        AttributeError,
        ValueError,
        IndexError,
        OverflowError,
    ) as exc:
        issue("INVALID_PROJECT", f"Projekt obsahuje neplatnou vazbu nebo geometrii: {exc}")
        return issues
    for pid, part in project.parts.items():
        if part.stale or part.input_digest != part_input(project, part):
            issue(
                "STALE", "Díl je po změně konstrukce neaktuální. Přepočítejte jeho rozvin.", (pid,)
            )
            continue
        try:
            expected = build_part(project, part)
            if geometry_payload(expected) != geometry_payload(part):
                issue(
                    "INVALID_CACHE",
                    "Uložený rozvin neodpovídá zdrojové konstrukci. Přepočítejte jej.",
                    (pid,),
                )
                continue
            placement = project.placements[pid]
            if placement.page_id is None:
                issue("UNPLACED", "Díl čeká na odkládací ploše. Přesuňte jej na stránku.", (pid,))
                continue
            page = next(p for p in project.pages if p.id == placement.page_id)
            transformed = []
            for loops in part.polygons.values():
                transformed.append(
                    material_polygon(
                        page_points(loops[0], placement),
                        [page_points(h, placement) for h in loops[1:]],
                    )
                )
            transformed.extend(
                Polygon(page_points(tab["points"], placement)) for tab in part.paths["TABS"]
            )
            material = unary_union(transformed)
            materials[pid] = material
            if not box(0, 0, page.width_mm, page.height_mm).covers(material):
                issue("PHYSICAL_OVERFLOW", "Díl včetně chlopní přesahuje fyzický list.", (pid,))
            elif not box(
                page.margin_mm,
                page.margin_mm,
                page.width_mm - page.margin_mm,
                page.height_mm - page.margin_mm,
            ).covers(material):
                issue(
                    "PRINT_MARGIN",
                    "Díl zasahuje do doporučeného tiskového okraje.",
                    (pid,),
                    "warning",
                )
            if (
                material.intersection(
                    box(10, page.height_mm - 18, page.width_mm - 10, page.height_mm - 2)
                ).area
                > 1e-8
            ):
                issue(
                    "PRINT_GUIDE_OVERLAP",
                    "Díl překrývá kalibraci nebo pokyny v zápatí.",
                    (pid,),
                    "warning",
                )
            if any(
                np.linalg.norm(np.roll(np.array(loop), -1, axis=0) - loop, axis=1).min() < 0.5
                for loops in part.polygons.values()
                for loop in loops
            ):
                issue(
                    "SMALL_DETAIL", "Díl má detail menší než 0,5 mm na papíře.", (pid,), "warning"
                )
        except (ValidationError, TypeError, ValueError, KeyError, AttributeError) as exc:
            issue("INVALID_GEOMETRY", f"Rozvin nelze ověřit: {exc}", (pid,))
    ids = list(materials)
    for index, a in enumerate(ids):
        for b in ids[index + 1 :]:
            if (
                project.placements[a].page_id == project.placements[b].page_id
                and materials[a].intersection(materials[b]).area > 1e-8
            ):
                issue(
                    "MATERIAL_OVERLAP",
                    "Vystřihované díly se překrývají včetně chlopní.",
                    (a, b),
                    "warning",
                )
    # All connector kinds share one assembly-space registry. Page/tray position
    # must not hide a collision between tabs that meet on the same receiver.
    folded_regions = []

    def register_folded(target, side, contact, parts, relation_id):
        loops = contact.get("footprint_loops_uv_mm", [contact.get("footprint_uv_mm")])
        region = Polygon(loops[0], loops[1:])
        for sid, other_side, other, other_id, other_parts in folded_regions:
            if (
                sid != target
                or (side != other_side and "unknown" not in (side, other_side))
                or region.intersection(other).area <= 1e-8
            ):
                continue
            unknown = "unknown" in (side, other_side)
            issue(
                "FOLDED_SIDE_UNRESOLVED" if unknown else "FOLDED_CONNECTOR_COLLISION",
                (
                    "Nelze vyloučit překryv ohnutých chlopní: strana protikusu není určená. "
                    "Určete ji ve vlastnostech spoje, nebo upravte chlopně."
                    if unknown else
                    "Lepené části nebo ohnuté záložky zasahují do stejného místa "
                    "na stejné straně protikusu. Upravte jejich tvar, polohu nebo dělení."
                ) + f" ({other_id}).",
                tuple(dict.fromkeys([*parts, *other_parts])),
                joint_id=relation_id,
            )
        folded_regions.append((target, side, region, contact["tab_id"], parts))

    for joint in project.joints.values():
        if joint.unresolved:
            issue(
                "REFERENCE_UNRESOLVED",
                "Po změně obrysu vyberte znovu hrany spoje.",
                tuple(
                    {
                        project.surfaces[joint.surface_a].part_id,
                        project.surfaces[joint.surface_b].part_id,
                    }
                ),
                joint_id=joint.id,
            )
            continue
        if not joint.connector_id or joint.mode != "cut":
            continue
        connector = project.connectors[joint.connector_id]
        pid = project.surfaces[connector.owner_surface_id].part_id
        try:
            contact = connector_contact(project, joint, connector)
            target = contact["receiver_surface_id"]
            for tab in contact["tabs"]:
                register_folded(
                    target, connector.receiver_side, tab,
                    tuple(dict.fromkeys([pid, project.part_for_surface(target)])), joint.id,
                )
            if contact["nominal_area_mm2"] - contact["available_area_mm2"] > max(
                1e-8, contact["nominal_area_mm2"] * 1e-10
            ):
                issue(
                    "GLUE_AREA_PARTIAL",
                    "Chlopeň není celá podepřená materiálem protikusu. Upravte ji nebo příjemce.",
                    (pid,),
                    joint_id=joint.id,
                )
        except ValidationError as exc:
            issue("JOINT_CONTACT", str(exc), (pid,), joint_id=joint.id)
        if connector.width_mm < 2:
            issue("SMALL_TAB", "Chlopeň je užší než 2 mm na papíře.", (pid,), "warning", joint.id)
        issue(
            "MATERIAL_CLEARANCE_UNVERIFIED",
            "Digitální spoj nenahrazuje ohnutí, slepení a ověření pevnosti výtiskem. "
            "Při neznámé tloušťce je hledání střetů omezené a nedokazuje jejich nepřítomnost.",
            (pid,),
            "warning",
            joint.id,
            evidence=project._assembly_clearance_key(),
        )
    for attachment in project.attachments.values():
        source, target = attachment.source_surface_id, attachment.target_surface_id
        parts = tuple(
            dict.fromkeys([project.part_for_surface(source), project.part_for_surface(target)])
        )
        try:
            geometry = attachment_geometry(project, attachment)
            if attachment.source_edge_id is None:
                register_folded(target, attachment.target_side, {
                    "tab_id": attachment.id,
                    "footprint_loops_uv_mm": [
                        (np.asarray(loop) * project.scale).tolist()
                        for loop in geometry["target_loops_uv"]
                    ],
                }, parts, attachment.id)
            if attachment.connector_id:
                contacts = trace_connector_contact(
                    project, attachment, project.connectors[attachment.connector_id]
                )
                for contact in contacts:
                    if contact["nominal_area_mm2"] - contact["available_area_mm2"] > max(
                        1e-8, contact["nominal_area_mm2"] * 1e-10
                    ):
                        issue(
                            "FOLDED_GLUE_AREA_PARTIAL",
                            "Ohnutá záložka není celá na lepicím materiálu protikusu.",
                            parts,
                            joint_id=attachment.id,
                        )
                    register_folded(target, attachment.target_side, contact, parts, attachment.id)
        except ValidationError as exc:
            issue("ATTACHMENT_CONTACT", str(exc), parts, joint_id=attachment.id)
        issue(
            "MATERIAL_CLEARANCE_UNVERIFIED",
            "Digitální geometrie nenahrazuje skutečné ohnutí, lepení a pevnost konkrétního "
            "papíru. Při neznámé tloušťce je hledání střetů omezené a nedokazuje jejich "
            "nepřítomnost; ověřte výtiskem.",
            parts,
            "warning",
            attachment.id,
            evidence=project._assembly_clearance_key() if attachment.connector_id else None,
        )
    tab_owners = {
        "tab:" + tid: (connector, index + 1)
        for connector in project.connectors.values()
        for index, tid in enumerate(connector.tab_ids)
    }

    def bend_obstacle_description(obstacle_id, affected_parts):
        if obstacle_id in project.surfaces:
            affected_parts.append(project.part_for_surface(obstacle_id))
            return f"plochy „{project.surfaces[obstacle_id].name}“"
        if obstacle_id in tab_owners:
            owner, ordinal = tab_owners[obstacle_id]
            sid = owner.owner_surface_id
            pid = project.part_for_surface(sid)
            affected_parts.append(pid)
            return (
                f"chlopně {ordinal} dílu „{project.parts[pid].name}“ "
                f"na ploše „{project.surfaces[sid].name}“"
            )
        return "jiného materiálu modelu"

    for cid, connector in project.connectors.items():
        report = project.connector_bend_clearance(cid)
        if report["status"] in ("CLEAR", "UNVERIFIED", "NOT_APPLICABLE"):
            continue
        source, receiver = project._connector_surfaces(connector)
        parts = [project.part_for_surface(source), project.part_for_surface(receiver)]
        relation_id = connector.attachment_id or connector.joint_id
        failing = [tab for tab in report["tabs"] if tab["status"] in ("COLLISION", "UNRESOLVED")]
        for detail in failing or [report]:
            detail_parts = parts.copy()
            obstacle = detail.get("obstacle_id")
            collision = detail["status"] == "COLLISION"
            target = bend_obstacle_description(obstacle, detail_parts) if collision else None
            angle = detail.get("witness_angle_deg")
            angle_text = f" při {angle:g}°" if angle is not None else ""
            message = (
                f"Při ohýbání záložka naráží do {target}{angle_text}. "
                "Upravte chlopeň, mezeru nebo polohu překážky."
                if collision else
                "Prostor pro ohnutí této záložky nelze v zadaném materiálovém modelu doložit. "
                "Zkontrolujte parametry papíru, místní pás ohybu a geometrii spoje."
            )
            unresolved = detail.get("unresolved_layer_obstacle_ids", [])
            if unresolved:
                targets = [bend_obstacle_description(oid, detail_parts) for oid in unresolved]
                message += (
                    " Neurčené vrstvy vůči: " + "; ".join(targets) + ". "
                    "U připojení určete stranu a zkontrolujte skutečné uspořádání vrstev."
                )
            if report.get("message"):
                message += " " + report["message"]
            issue("BEND_COLLISION" if collision else "BEND_UNRESOLVED", message,
                  tuple(dict.fromkeys(detail_parts)), joint_id=relation_id, evidence=report)
    return issues
