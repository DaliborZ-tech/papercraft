"""Straight interior connections and rigid, independently measured glue footprints."""

from __future__ import annotations

import math

import numpy as np
from shapely import LineString, Polygon

from .errors import ValidationError
from .geometry import material_polygon, number, signed_area


def edge_source(project, surface_id, edge_id):
    surface = project.surfaces[surface_id]
    for profile_id in [surface.profile_id, *surface.hole_profile_ids]:
        profile = project.profiles[profile_id]
        edge = profile.segment(edge_id)
        if edge is not None:
            if edge.kind != "line":
                raise ValidationError(
                    "Tento spoj vyžaduje přímý ohyb; zakřivený lem patří do dalšího řezu."
                )
            return (
                profile,
                edge,
                np.array(
                    [
                        profile.vertex(edge.start_vertex_id).point,
                        profile.vertex(edge.end_vertex_id).point,
                    ]
                ),
            )
    raise ValidationError("REFERENCE_UNRESOLVED: zdrojová hrana chybí. Vyberte ji znovu.")


def interval_points(project, attachment):
    _, _, edge = edge_source(project, attachment.source_surface_id, attachment.source_edge_id)
    interval = [number(v, "Interval zdrojové hrany") for v in attachment.source_interval]
    if len(interval) != 2 or not 0 <= interval[0] < interval[1] <= 1:
        raise ValidationError("Interval hrany musí být vzestupný a ležet mezi0 a1.")
    return edge[0] + np.asarray(interval)[:, None] * (edge[1] - edge[0])


def surface_basis(project, surface_id):
    surface = project.surfaces[surface_id]
    plane = project.profiles[surface.profile_id].plane
    matrix = project._surface_matrix(surface_id)
    return (
        project._surface_world_points(surface_id, [[0, 0]])[0],
        matrix[:3, :3] @ np.asarray(plane.u),
        matrix[:3, :3] @ np.asarray(plane.v),
    )


def world_to_uv(project, surface_id, points):
    origin, u, v = surface_basis(project, surface_id)
    relative = np.asarray(points) - origin
    return np.column_stack([relative @ u, relative @ v]), relative @ np.cross(u, v)


def surface_material(project, surface_id, *, paper=False):
    surface = project.surfaces[surface_id]
    factor = project.scale if paper else 1.0
    return material_polygon(
        np.asarray(project.profiles[surface.profile_id].points) * factor,
        [np.asarray(project.profiles[h].points) * factor for h in surface.hole_profile_ids],
    )


def contact_tolerance(project, *regions, span=0):
    """Model-space contact tolerance, bounded by the 0.01 paper-mm budget."""
    extents = [math.hypot(r.bounds[2] - r.bounds[0], r.bounds[3] - r.bounds[1])
               for r in regions]
    return min(0.01 / project.scale, max(1e-6, 1e-9 * max([span, *extents])))


def attachment_geometry(project, attachment):
    """Read-only diagnostics; a projection never substitutes for physical contact."""
    if attachment.unresolved:
        raise ValidationError(
            "REFERENCE_UNRESOLVED: po nahrazení profilu vyberte znovu zdroj spoje."
        )
    source, target = attachment.source_surface_id, attachment.target_surface_id
    material = surface_material(project, target)
    if attachment.source_edge_id is not None:
        local = interval_points(project, attachment)
        world = project._surface_world_points(source, local)
        uv, distances = world_to_uv(project, target, world)
        trace = LineString(uv)
        gap = float(np.max(np.abs(distances)))
        tolerance = contact_tolerance(project, material, span=math.dist(*world))
        if gap > tolerance:
            raise ValidationError(
                f"ATTACHMENT_GAP: hrana je {gap:g} mm od materiálu protikusu. "
                "Přisuňte ji nebo změňte spoj."
            )
        missing = trace.difference(material).length
        if trace.length <= 1e-9 or missing > tolerance:
            raise ValidationError(
                "TRACE_OUTSIDE_MATERIAL: část stopy je mimo protikus nebo v jeho otvoru."
            )
        result = {
            "kind": attachment.kind,
            "source_world": world.tolist(),
            "source_uv": local.tolist(),
            "target_uv": uv.tolist(),
            "contact_gap_mm": gap,
            "material_length_mm": trace.length - missing,
            "receiver_surface_id": target,
            "target_side": attachment.target_side,
            "contact_tolerance_model_mm": tolerance,
        }
        if attachment.kind == "glue_region":
            region = material_polygon(attachment.target_region_uv)
            if (
                not material.buffer(tolerance).covers(region)
                or trace.difference(region).length > tolerance
            ):
                raise ValidationError(
                    "TARGET_GLUE_OUTSIDE: lepicí oblast nebo její stopa "
                    "není na přijímajícím materiálu."
                )
            result["target_region_uv"] = attachment.target_region_uv
        return result
    if attachment.kind != "glue_region":
        raise ValidationError("Neznámý typ připojení.")
    source_material = surface_material(project, source)
    source_polygon = (
        material_polygon(attachment.source_region_uv)
        if attachment.source_region_uv
        else source_material
    )
    tolerance = contact_tolerance(project, material, source_material, source_polygon)
    if not source_material.buffer(tolerance).covers(source_polygon):
        raise ValidationError("SOURCE_GLUE_OUTSIDE: zdrojová lepicí oblast není celá na materiálu.")
    target_region = material_polygon(attachment.target_region_uv)
    if not material.buffer(tolerance).covers(target_region):
        raise ValidationError(
            "TARGET_GLUE_OUTSIDE: cílová lepicí oblast zasahuje mimo materiál nebo do otvoru."
        )
    loops = [
        list(source_polygon.exterior.coords)[:-1],
        *[list(h.coords)[:-1] for h in source_polygon.interiors],
    ]
    world_loops = [project._surface_world_points(source, loop) for loop in loops]
    uv_loops, distances = [], []
    for points in world_loops:
        uv, distance = world_to_uv(project, target, points)
        uv_loops.append(uv)
        distances.extend(distance)
    gap = float(max(abs(v) for v in distances))
    if gap > tolerance:
        raise ValidationError(f"ATTACHMENT_GAP: lepené plochy odděluje mezera {gap:g} mm.")
    footprint = material_polygon(uv_loops[0], uv_loops[1:])
    available = footprint.intersection(target_region).intersection(material).area
    if footprint.area - available > max(1e-8, footprint.area * 1e-10):
        raise ValidationError(
            "GLUE_REGION_PARTIAL: otisk není celý v zadané lepicí oblasti protikusu."
        )
    if not material.buffer(tolerance).covers(footprint) or not target_region.buffer(
        tolerance
    ).covers(footprint):
        raise ValidationError(
            "GLUE_REGION_PARTIAL: otisk přesahuje příjemce nad toleranci kontaktu."
        )
    return {
        "kind": attachment.kind,
        "source_world": world_loops[0].tolist(),
        "source_uv": np.asarray(loops[0]).tolist(),
        "target_uv": uv_loops[0].tolist(),
        "target_loops_uv": [loop.tolist() for loop in uv_loops],
        "target_region_uv": attachment.target_region_uv,
        "contact_gap_mm": gap,
        "nominal_area_mm2": footprint.area * project.scale * project.scale,
        "available_area_mm2": available * project.scale * project.scale,
        "receiver_surface_id": target,
        "target_side": attachment.target_side,
        "contact_tolerance_model_mm": tolerance,
        "target_region_outside_area_mm2": (
            target_region.difference(material).area * project.scale**2
        ),
    }


def connector_shapes(connector, length_mm):
    """Local x follows hinge; positive y is outward on the flat source paper."""
    if not connector.enabled:
        return []
    count, gap = connector.count, connector.gap_mm
    pitch = length_mm / count
    if gap >= pitch:
        raise ValidationError("Mezera záložek spotřebuje celou rozteč.")
    result = []
    ids = connector.tab_ids or [connector.id]  # Explicit compatibility for006A connectors.
    for index, tab_id in enumerate(ids):
        overrides = connector.tab_overrides.get(tab_id, {})
        if not overrides.get("enabled", True):
            continue
        a, b = index * pitch + gap / 2, (index + 1) * pitch - gap / 2
        width = overrides.get("width_mm", connector.width_mm)
        taper = overrides.get("taper", connector.taper)
        shape = overrides.get("shape", connector.shape)
        outline = overrides.get("outline_mm", connector.outline_mm)
        if shape == "custom":
            points = np.asarray(outline, dtype=float)
            if (
                len(points) < 3
                or not np.allclose(points[:2], [[0, 0], [b - a, 0]], atol=1e-9)
                or np.any(points[2:, 1] <= 0)
            ):
                raise ValidationError(
                    "Vlastní obrys potřebuje základnu[0,0]→[délka,0] a vnější body nad ní."
                )
            material_polygon(points)
            points = points + [a, 0]
        elif shape == "triangle":
            points = np.array([[a, 0], [b, 0], [(a + b) / 2, width]])
        else:
            inset = (b - a) * (1 - taper) / 2
            points = np.array([[a, 0], [b, 0], [b - inset, width], [a + inset, width]])
        result.append({"id": tab_id, "points": points, "hinge": np.array([[a, 0], [b, 0]])})
    return result


def trace_connector_contact(project, attachment, connector):
    geometry = attachment_geometry(project, attachment)
    hinge = np.asarray(geometry["target_uv"]) * project.scale
    tangent = (hinge[1] - hinge[0]) / math.dist(*hinge)
    side = np.array([-tangent[1], tangent[0]]) * attachment.glue_direction
    receiver = surface_material(project, attachment.target_surface_id, paper=True)
    if attachment.kind == "glue_region":
        receiver = receiver.intersection(
            material_polygon(np.asarray(attachment.target_region_uv) * project.scale)
        )
    world = np.asarray(geometry["source_world"])
    world_axis = (world[1] - world[0]) / math.dist(*world)
    _, outward = source_outward(project, attachment.source_surface_id, attachment.source_edge_id)
    _, su, sv = surface_basis(project, attachment.source_surface_id)
    _, tu, tv = surface_basis(project, attachment.target_surface_id)
    flat_outward = outward[0] * su + outward[1] * sv
    desired = side[0] * tu + side[1] * tv
    angle = math.atan2(
        float(np.dot(world_axis, np.cross(flat_outward, desired))),
        float(np.dot(flat_outward, desired)),
    )
    # Actual rotation of the flat tab about its straight hinge (Rodrigues),
    # independently projected back to the receiver. No gap is removed by projection.
    folded_outward = (
        flat_outward * math.cos(angle)
        + np.cross(world_axis, flat_outward) * math.sin(angle)
        + world_axis * np.dot(world_axis, flat_outward) * (1 - math.cos(angle))
    )
    result = []
    for tab in connector_shapes(connector, math.dist(*hinge)):
        folded_world = (
            world[0]
            + tab["points"][:, :1] / project.scale * world_axis
            + tab["points"][:, 1:] / project.scale * folded_outward
        )
        footprint_uv, gap = world_to_uv(project, attachment.target_surface_id, folded_world)
        if np.max(np.abs(gap)) > max(1e-6, math.dist(*world) * 1e-9):
            raise ValidationError("FOLDED_CONTACT_GAP: ohnutá chlopeň neleží na přijímající ploše.")
        footprint = footprint_uv * project.scale
        region = Polygon(footprint)
        available = region.intersection(receiver).area
        result.append(
            {
                "tab_id": tab["id"],
                "footprint_uv_mm": footprint.tolist(),
                "nominal_area_mm2": region.area,
                "available_area_mm2": available,
                "receiver_surface_id": attachment.target_surface_id,
                "folded_world": folded_world.tolist(),
                "fold_angle_deg": math.degrees(angle),
                "contact_gap_mm": float(np.max(np.abs(gap))),
            }
        )
    return result


def source_outward(project, surface_id, edge_id):
    profile, _, edge = edge_source(project, surface_id, edge_id)
    tangent = (edge[1] - edge[0]) / math.dist(*edge)
    outward = np.array([tangent[1], -tangent[0]])
    if signed_area(profile.points) < 0:
        outward = -outward
    if profile.id in project.surfaces[surface_id].hole_profile_ids:
        outward = -outward
    return tangent, outward
