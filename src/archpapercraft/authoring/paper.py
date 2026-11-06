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
            "connectors": {
                j.connector_id: asdict(project.connectors[j.connector_id])
                for j in joints
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
    surface = project.surfaces[surface_id]
    profile = project.profiles[surface.profile_id]
    edge = profile.segment(edge_id)
    if edge is None:
        raise ValidationError("REFERENCE_UNRESOLVED: hrana spoje chybí.")
    return np.array(
        [profile.vertex(edge.start_vertex_id).point, profile.vertex(edge.end_vertex_id).point]
    )


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
    if connector.shape == "triangle":
        points = [edge[0], edge[1], edge.mean(axis=0) + inward * connector.width_mm]
    else:
        inset = (1 - connector.taper) * np.linalg.norm(edge[1] - edge[0]) / 2
        points = [
            edge[0],
            edge[1],
            edge[1] - tangent * inset + inward * connector.width_mm,
            edge[0] + tangent * inset + inward * connector.width_mm,
        ]
    target = material_polygon(
        np.array(profile.points) * project.scale,
        [np.array(project.profiles[h].points) * project.scale for h in surface.hole_profile_ids],
    )
    footprint = Polygon(points)
    return {
        "nominal_area_mm2": footprint.area,
        "available_area_mm2": footprint.intersection(target).area,
        "receiver_surface_id": sid,
        "footprint": points,
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
        profile = profiles[0]
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
        inset = (1 - connector.taper) * np.linalg.norm(points[1] - points[0]) / 2
        if connector.shape == "triangle":
            tab = [points[0], points[1], points.mean(axis=0) + outward * connector.width_mm]
        else:
            tab = [
                points[0],
                points[1],
                points[1] - tangent * inset + outward * connector.width_mm,
                points[0] + tangent * inset + outward * connector.width_mm,
            ]
        tab_polygon = Polygon(tab)
        if any(tab_polygon.intersection(p).area > 1e-8 for p in material):
            raise ValidationError(
                "Chlopeň zasahuje do vlastního materiálu. Změňte šířku nebo tvar."
            )
        tabs.append(tab_polygon)
        part.paths["TABS"].append(path(tab, True))
        receiver = joint.surface_b if sid == joint.surface_a else joint.surface_a
        part.paths[fold_role(project, sid, receiver, edge_id, part.front_side)].append(path(points))
    union = unary_union([*material, *tabs])
    part.paths["CUT"] = _polygon_loops(union)
    label_at = material[0].representative_point()
    part.labels.insert(0, {"text": part.name, "x": label_at.x, "y": label_at.y, "size_mm": 2.5})
    part.stale = False
    part.source_revision = project.revision
    part.input_digest = part_input(project, part)
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

    def issue(code, message, parts=(), severity="error", joint_id=None):
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
        signature = digest([issue_id, relevant])
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
            "Digitální spoj nezaručuje ohyb a pevnost konkrétního papíru; ověřte výtiskem.",
            (pid,),
            "warning",
            joint.id,
        )
    return issues
