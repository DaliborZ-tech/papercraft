"""Conservative digital clearance of straight-hinge, rigid planar tab patches.

All coordinates, thicknesses and distances are PAPER millimetres. This checks
the declared swept envelope against complete material geometry, including the
source and receiver. It does not certify material strain, strength or assembly.
Only explicitly bounded hinge/contact volumes may be excluded, and every such
exclusion is returned in the result. Unknown material never produces CLEAR.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from scipy.spatial import ConvexHull, QhullError
from shapely.geometry import Polygon

Status = Literal["CLEAR", "COLLISION", "UNRESOLVED", "UNVERIFIED"]


@dataclass(frozen=True)
class MaterialProfile:
    thickness_mm: float | None
    clearance_mm: float = 0.0
    bend_radius_mm: float = 0.0


@dataclass(frozen=True)
class MaterialObstacle:
    id: str
    triangles_world_mm: object
    thickness_mm: float | None
    role: str = "other"


@dataclass(frozen=True)
class FoldSweep:
    """One authored tab, optionally triangulated into same-material patches.

    Each patch must be convex and planar; patches may form a concave tab. They
    are checked separately, never replaced by a filled bounding box. Patches
    need not individually touch the hinge. initial_normal and final_normal
    describe the same oriented material side before and after the signed fold.
    """

    patches_world_mm: object
    hinge_start_mm: object
    hinge_end_mm: object
    angle_deg: float
    source_id: str
    receiver_id: str
    initial_normal: object
    final_normal: object
    tab_id: str = "tab"


@dataclass(frozen=True)
class ContactAllowance:
    """A finite convex permitted volume, not an ignored obstacle identity.

    Root/controller derives this volume from the explicitly authored hinge or
    receiving contact geometry. The interval uses signed fold degrees; it may
    be ascending or descending. Removing an entire source/receiver without
    such geometry is not supported. Permission is never allowed for a third
    unconnected obstacle. The result records every declared allowance.
    """

    obstacle_id: str
    kind: Literal["hinge", "final_contact"]
    vertices_world_mm: object
    angle_interval_deg: tuple[float, float]
    reason: str


@dataclass(frozen=True)
class ClearanceResult:
    status: Status
    message: str
    tab_id: str
    obstacle_id: str | None = None
    witness_angle_deg: float | None = None
    witness_point_mm: tuple[float, float, float] | None = None
    certified_intervals: int = 0
    examined_intervals: int = 0
    numerical_guard_mm: float = 0.0
    envelope_padding_mm: float = 0.0
    material_thickness_mm: float | None = None
    clearance_mm: float = 0.0
    bend_radius_mm: float = 0.0
    allowances: tuple[dict, ...] = ()
    checked_obstacle_ids: tuple[str, ...] = ()
    search_interval_limit: int | None = None
    search_depth_limit: int | None = None
    search_budget_exhausted: bool = False
    search_depth_limit_reached: bool = False
    coarse_intervals_examined: int = 0
    witness_angles_examined: int = 0
    proof_method: str = "analytic_continuous_sinusoid_projection_intervals_and_convex_SAT"
    assumptions: tuple[str, ...] = field(
        default_factory=lambda: (
            "complete_registry_of_planar_material_triangles",
            "straight_hinge_rigid_motion_of_declared_convex_patches",
            "bend_radius_is_a_conservative_displacement_envelope_not_material_mechanics",
            "explicit_finite_hinge_and_contact_volumes_only",
            "physical_build_and_strength_NOT_VERIFIED",
        )
    )


def _vector(value, size=3):
    result = np.asarray(value, dtype=float)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError("Expected a finite vector")
    return result


def _normal(value):
    result = _vector(value)
    norm = float(np.linalg.norm(result))
    if norm < 1e-10:
        raise ValueError("Normal or hinge direction is degenerate")
    return result / norm


def _number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected a finite number in paper millimetres")
    value = float(value)
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError("Material distances must be finite and nonnegative")
    return value


def _hull(vertices):
    points = np.asarray(vertices, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("Expected finite 3D material vertices")
    points = np.unique(points, axis=0)
    if len(points) < 4 or np.linalg.matrix_rank(points[1:] - points[0], tol=1e-11) < 3:
        return None
    try:
        hull = ConvexHull(points)
    except QhullError as exc:
        raise ValueError("Numerically unresolved material polyhedron") from exc
    return points, hull


def _edges(polyhedron):
    points, hull = polyhedron
    return {
        tuple(sorted((int(a), int(b))))
        for face in hull.simplices
        for a, b in zip(face, np.roll(face, -1))
    }


def _clip(polyhedron, normal, offset, *, inside=True):
    """Clip a convex solid, retaining actual thick material after permission.

    Halfspaces are n.x <= offset; their intersections are constructed from all
    convex hull edges. Allowance planes are already shrunk by the guard.
    """
    points, _ = polyhedron
    distances = points @ normal - offset
    if not inside:
        distances = -distances
    kept = list(points[distances <= 0])
    for a, b in _edges(polyhedron):
        da, db = distances[a], distances[b]
        if (da < 0 < db) or (db < 0 < da):
            kept.append(points[a] + (points[b] - points[a]) * (da / (da - db)))
    return _hull(kept) if len(kept) >= 4 else None


def _subtract(polyhedron, equations, guard):
    """Partition P minus a (slightly shrunk) finite convex permitted volume."""
    outside, remaining = [], polyhedron
    for equation in equations:
        if remaining is None:
            break
        normal, offset = equation[:3], -equation[3] - guard
        piece = _clip(remaining, normal, offset, inside=False)
        if piece is not None:
            outside.append(piece)
        remaining = _clip(remaining, normal, offset)
    return outside


def _patch(value, initial_normal, guard):
    points = np.asarray(value, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 3:
        raise ValueError("A tab patch needs at least three finite planar vertices")
    if not np.isfinite(points).all():
        raise ValueError("Nonfinite tab patch")
    if np.max(abs((points - points[0]) @ initial_normal)) > guard:
        raise ValueError("Tab patches must lie in the declared initial plane")
    turns = [
        float(np.dot(np.cross(b - a, c - b), initial_normal))
        for a, b, c in zip(points, np.roll(points, -1, axis=0), np.roll(points, -2, axis=0))
    ]
    if max(turns) <= guard**2 and min(turns) >= -(guard**2):
        raise ValueError("Degenerate tab patch")
    if any(t > guard**2 for t in turns) and any(t < -(guard**2) for t in turns):
        raise ValueError("Concave tab must be supplied as convex material patches")
    for a, b in zip(points, np.roll(points, -1, axis=0)):
        if np.linalg.norm(b - a) <= guard:
            raise ValueError("Duplicate/degenerate tab patch edge")
        sides = np.cross(b - a, points - a) @ initial_normal
        if sides.min() < -(guard**2) and sides.max() > guard**2:
            raise ValueError("Patch is self-intersecting or not convex in boundary order")
    return points


def _rotate(points, axis, angle):
    cosine, sine = math.cos(angle), math.sin(angle)
    return (
        points * cosine
        + np.cross(axis, points) * sine
        + np.outer(points @ axis, axis) * (1 - cosine)
    )


def _sinusoid_range(a, b, lo, hi):
    values = [a * math.cos(lo) + b * math.sin(lo), a * math.cos(hi) + b * math.sin(hi)]
    phase = math.atan2(b, a)
    first = math.ceil((lo - phase) / math.pi)
    last = math.floor((hi - phase) / math.pi)
    for k in range(first, last + 1):
        theta = phase + k * math.pi
        values.append(a * math.cos(theta) + b * math.sin(theta))
    return min(values), max(values)


def _projection_interval(points, axis, direction, lo, hi, padding):
    """Extrema over ALL angles and all convex combinations of patch vertices."""
    axial = np.outer(points @ axis, axis)
    radial, tangent = points - axial, np.cross(axis, points)
    offsets, cosine, sine = axial @ direction, radial @ direction, tangent @ direction
    low, high = math.inf, -math.inf
    for offset, a, b in zip(offsets, cosine, sine):
        a0, a1 = _sinusoid_range(float(a), float(b), lo, hi)
        low, high = min(low, offset + a0), max(high, offset + a1)
    return low - padding, high + padding


def _axes(patch, obstacle, axis, lo, hi, initial_normal):
    points, hull = obstacle
    choices = [*np.eye(3), *hull.equations[:, :3]]
    obstacle_edges = [points[b] - points[a] for a, b in _edges(obstacle)]
    for angle in (lo, (lo + hi) / 2, hi):
        rotated = _rotate(patch, axis, angle)
        normal = _rotate(np.array([initial_normal]), axis, angle)[0]
        choices.append(normal)
        for edge in np.roll(rotated, -1, axis=0) - rotated:
            choices.append(np.cross(edge, normal))
            choices.extend(np.cross(edge, other) for other in obstacle_edges)
        # Extruded tab prisms also have edges along the rotated normal.
        choices.extend(np.cross(normal, other) for other in obstacle_edges)
    normalized = []
    for candidate in choices:
        length = float(np.linalg.norm(candidate))
        if length > 1e-12:
            normalized.append(candidate / length)
    return normalized


def _separated(patch, obstacle, axis, lo, hi, normal, thickness, padding, guard):
    # Thickness rotates with the material normal. A ball t/2 would falsely
    # expand the tab sideways beyond its actual finite contact footprint.
    envelope_vertices = np.vstack([patch - normal * thickness / 2, patch + normal * thickness / 2])
    for direction in _axes(patch, obstacle, axis, lo, hi, normal):
        low, high = _projection_interval(envelope_vertices, axis, direction, lo, hi, padding)
        projected = obstacle[0] @ direction
        if high < projected.min() - guard or low > projected.max() + guard:
            return True
    return False


def _static_collision(patch, obstacle, axis, theta, normal, thickness, guard):
    rotated = _rotate(patch, axis, theta)
    rotated_normal = _rotate(np.array([normal]), axis, theta)[0]
    solid = _hull(
        np.vstack(
            [rotated - rotated_normal * thickness / 2, rotated + rotated_normal * thickness / 2]
        )
    )
    if solid is None:
        return False
    # Complete convex-polyhedron SAT: both face normals and all edge cross axes.
    axes = [*solid[1].equations[:, :3], *obstacle[1].equations[:, :3]]
    edges_a = [solid[0][b] - solid[0][a] for a, b in _edges(solid)]
    edges_b = [obstacle[0][b] - obstacle[0][a] for a, b in _edges(obstacle)]
    axes.extend(np.cross(a, b) for a in edges_a for b in edges_b)
    for direction in axes:
        length = float(np.linalg.norm(direction))
        if length < 1e-12:
            continue
        direction = direction / length
        first, second = solid[0] @ direction, obstacle[0] @ direction
        # Require strict penetration on every SAT axis; tangency/near contact
        # is unresolved, never labelled a certified collision or free space.
        overlap = min(first.max(), second.max()) - max(first.min(), second.min())
        if overlap <= guard:
            return False
    return True


def _clip_face(points, equations, guard):
    """Convex planar polygon inside an expanded permitted contact solid."""
    result = list(points)
    for equation in equations:
        output = []
        if not result:
            break
        for a, b in zip(result, [*result[1:], result[0]]):
            da, db = (
                np.dot(equation[:3], a) + equation[3] - guard,
                np.dot(equation[:3], b) + equation[3] - guard,
            )
            if da <= 0:
                output.append(a)
            if (da < 0 < db) or (db < 0 < da):
                output.append(a + (b - a) * (da / (da - db)))
        result = output
    return result


def _inside_face(point, polygon, normal, guard):
    centre = polygon.mean(axis=0)
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        inward = _normal(np.cross(normal, b - a))
        if np.dot(inward, centre - a) < 0:
            inward = -inward
        if np.dot(inward, point - a) <= guard:
            return False
    return True


def _outside_permissions(point, permissions, guard):
    return all(
        np.max(equations[:, :3] @ point + equations[:, 3]) > 2 * guard for equations in permissions
    )


def _zero_collision(patch, triangle, normal, permissions, guard):
    """A strict original-midplane intersection witness, never a proxy prism.

    Proper transverse intersections and exactly coplanar positive-area
    intersections are supported. Near-coplanarity/tangency is not a witness.
    Finite samples may find a collision but cannot establish absence of one.
    """
    distances = (triangle - patch[0]) @ normal
    if np.max(abs(distances)) <= guard:
        ambiguous = not np.all(distances == 0)
        u = _normal(patch[1] - patch[0])
        v = np.cross(normal, u)
        origin = patch[0]

        def uv(points):
            return np.column_stack([(points - origin) @ u, (points - origin) @ v])

        first, second = Polygon(uv(patch)), Polygon(uv(triangle))
        overlap = first.intersection(second)
        if overlap.geom_type != "Polygon" or overlap.area <= guard**2:
            return None
        original_overlap = overlap
        for equations in permissions:
            face = np.array(
                [origin + x * u + y * v for x, y in list(original_overlap.exterior.coords)[:-1]]
            )
            clipped = _clip_face(face, equations, guard)
            if len(clipped) >= 3:
                overlap = overlap.difference(Polygon(uv(np.array(clipped))))
        if overlap.is_empty or overlap.area <= guard**2:
            return None
        point = overlap.representative_point()
        if (
            first.boundary.distance(point) <= 4 * guard
            or second.boundary.distance(point) <= 4 * guard
        ):
            return None
        witness = origin + point.x * u + point.y * v
        if not _outside_permissions(witness, permissions, guard):
            return None
        return ("NEAR_COPLANAR", witness) if ambiguous else witness
    if distances.min() >= -guard or distances.max() <= guard:
        return None
    intersections = []
    for a, b, da, db in zip(
        triangle, np.roll(triangle, -1, axis=0), distances, np.roll(distances, -1)
    ):
        if da == 0:
            intersections.append(a)
        if (da < 0 < db) or (db < 0 < da):
            intersections.append(a + (b - a) * (da / (da - db)))
    if len(intersections) < 2:
        return None
    a, b = max(
        ((a, b) for a in intersections for b in intersections),
        key=lambda p: np.linalg.norm(p[1] - p[0]),
    )
    direction = b - a
    length = float(np.linalg.norm(direction))
    low, high = 0.0, 1.0
    centre = patch.mean(axis=0)
    for start, end in zip(patch, np.roll(patch, -1, axis=0)):
        inward = _normal(np.cross(normal, end - start))
        if np.dot(inward, centre - start) < 0:
            inward = -inward
        value = np.dot(inward, a - start) - 2 * guard
        slope = np.dot(inward, direction)
        if slope == 0:
            if value < 0:
                return None
        elif slope > 0:
            low = max(low, -value / slope)
        else:
            high = min(high, -value / slope)
    if high <= low:
        return None
    unpermitted = [(low, high)]
    for equations in permissions:
        start, end = low, high
        for equation in equations:
            value = np.dot(equation[:3], a) + equation[3] - guard
            slope = np.dot(equation[:3], direction)
            if slope == 0:
                if value > 0:
                    start, end = 1.0, 0.0
                    break
            elif slope > 0:
                end = min(end, -value / slope)
            else:
                start = max(start, -value / slope)
        if start <= end:
            pieces = []
            for lo, hi in unpermitted:
                if end < lo or start > hi:
                    pieces.append((lo, hi))
                else:
                    if lo < start:
                        pieces.append((lo, start))
                    if end < hi:
                        pieces.append((end, hi))
            unpermitted = pieces
    triangle_normal = _normal(np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0]))
    for lo, hi in unpermitted:
        if (hi - lo) * length <= 4 * guard:
            continue
        witness = a + direction * ((lo + hi) / 2)
        if _inside_face(witness, triangle, triangle_normal, guard) and _outside_permissions(
            witness, permissions, guard
        ):
            return witness
    return None


def _face_solid_collision(face, normal, solid, permissions, guard):
    """A strict lower-bound witness: an original midplane inside known solid.

    Unknown thickness still contains its own zero-thickness midplane. Preserve
    the other material's known thickness rather than globally discarding it.
    The solid is shrunk and permissions expanded before choosing a witness.
    """
    clipped = _clip_face(face, solid[1].equations, -2 * guard)
    if len(clipped) < 3:
        return None
    origin = face[0]
    u = _normal(face[1] - origin)
    v = np.cross(normal, u)

    def uv(points):
        return np.column_stack([(points - origin) @ u, (points - origin) @ v])

    original = Polygon(uv(face))
    overlap = Polygon(uv(np.asarray(clipped)))
    for equations in permissions:
        allowed = _clip_face(np.asarray(clipped), equations, 2 * guard)
        if len(allowed) >= 3:
            overlap = overlap.difference(Polygon(uv(np.asarray(allowed))))
    if overlap.is_empty or overlap.area <= 16 * guard**2:
        return None
    point = overlap.representative_point()
    witness = origin + point.x * u + point.y * v
    if (
        original.boundary.distance(point) <= 4 * guard
        or np.max(solid[1].equations[:, :3] @ witness + solid[1].equations[:, 3]) >= -guard
        or not _outside_permissions(witness, permissions, 2 * guard)
    ):
        return None
    return witness


def _bounds_disjoint(first, second, guard):
    """Only prune demonstrably separated static bounds; never certify a sweep."""
    return bool(
        np.any(first.max(axis=0) < second.min(axis=0) - guard)
        or np.any(second.max(axis=0) < first.min(axis=0) - guard)
    )


def _unknown_witness_search(
    patches,
    axis,
    normal,
    thickness,
    items,
    triangles,
    solids,
    planes,
    intervals,
    origin,
    guard,
    base,
    max_depth,
    max_intervals,
):
    """Bounded search only; no amount of empty samples certifies absence."""
    base = dict(
        base,
        proof_method="bounded_breadth_first_material_lower_bound_collision_witness_search",
        search_interval_limit=max_intervals,
        search_depth_limit=max_depth,
    )
    examined = coarse = 0
    depth_reached = False
    ambiguous = False
    sampled = set()
    real_solids = {o.id: [] for o in items}
    known_thickness = {o.id: o.thickness_mm for o in items}
    for identity, solid in solids:
        actual = known_thickness[identity]
        if actual is not None:
            if actual >= 4 * guard:
                real_solids[identity].append(solid)
            else:
                # An artificial pruning proxy must NEVER become a negative
                # collision witness for sub-precision known thickness either.
                ambiguous = True
    clipped_cache = {}

    def finish(status, message, **witness):
        return ClearanceResult(
            status,
            message,
            examined_intervals=examined,
            coarse_intervals_examined=coarse,
            witness_angles_examined=len(sampled),
            search_depth_limit_reached=depth_reached,
            **base,
            **witness,
        )

    def probe(sample):
        nonlocal ambiguous
        if sample in sampled:
            return None
        sampled.add(sample)
        active = tuple(i for i, (_, a, b, _) in enumerate(planes) if a <= sample <= b)
        for patch in patches:
            rotated = _rotate(patch, axis, sample)
            rotated_normal = _rotate(np.array([normal]), axis, sample)[0]
            moving = None
            if thickness >= 4 * guard:
                moving = _hull(
                    np.vstack(
                        [
                            rotated - rotated_normal * thickness / 2,
                            rotated + rotated_normal * thickness / 2,
                        ]
                    )
                )
                if moving is None:
                    ambiguous = True
            elif thickness > 0:
                ambiguous = True
            for obstacle in items:
                permissions = [planes[i][3] for i in active if planes[i][0] == obstacle.id]
                # First keep exact original-midplane witnesses, including B02.
                # Near-coplanarity cannot stop the pass before a later definite
                # collision with this or any other material has been searched.
                for triangle in triangles[obstacle.id]:
                    if _bounds_disjoint(rotated, triangle, guard):
                        continue
                    witness = _zero_collision(rotated, triangle, rotated_normal, permissions, guard)
                    if isinstance(witness, tuple):
                        ambiguous = True
                    elif witness is not None:
                        return finish(
                            "COLLISION",
                            "Original material midplanes intersect during the fold",
                            obstacle_id=obstacle.id,
                            witness_angle_deg=math.degrees(sample),
                            witness_point_mm=tuple(float(v) for v in witness + origin),
                        )
                if obstacle.thickness_mm is not None:
                    if moving is not None:
                        key = (obstacle.id, active)
                        if key not in clipped_cache:
                            pieces = real_solids[obstacle.id]
                            for equations in permissions:
                                pieces = [
                                    piece
                                    for current in pieces
                                    for piece in _subtract(current, equations, -2 * guard)
                                ]
                            clipped_cache[key] = pieces
                        for solid in clipped_cache[key]:
                            if _bounds_disjoint(moving[0], solid[0], guard):
                                continue
                            if _static_collision(
                                patch, solid, axis, sample, normal, thickness, guard
                            ):
                                return finish(
                                    "COLLISION",
                                    "Known material solids intersect during the fold",
                                    obstacle_id=obstacle.id,
                                    witness_angle_deg=math.degrees(sample),
                                )
                    else:
                        for solid in real_solids[obstacle.id]:
                            if _bounds_disjoint(rotated, solid[0], guard):
                                continue
                            witness = _face_solid_collision(
                                rotated,
                                rotated_normal,
                                solid,
                                permissions,
                                guard,
                            )
                            if witness is not None:
                                return finish(
                                    "COLLISION",
                                    "Original tab midplane penetrates known thick material",
                                    obstacle_id=obstacle.id,
                                    witness_angle_deg=math.degrees(sample),
                                    witness_point_mm=tuple(float(v) for v in witness + origin),
                                )
                elif moving is not None:
                    for triangle in triangles[obstacle.id]:
                        if _bounds_disjoint(triangle, moving[0], guard):
                            continue
                        face_normal = _normal(
                            np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
                        )
                        witness = _face_solid_collision(
                            triangle, face_normal, moving, permissions, guard
                        )
                        if witness is not None:
                            return finish(
                                "COLLISION",
                                "Original obstacle midplane penetrates known thick tab",
                                obstacle_id=obstacle.id,
                                witness_angle_deg=math.degrees(sample),
                                witness_point_mm=tuple(float(v) for v in witness + origin),
                            )
        return None

    def visit(lo, hi):
        try:
            for sample in (lo, (lo + hi) / 2, hi):
                result = probe(sample)
                if result is not None:
                    return result
        except ValueError as exc:
            return finish("UNRESOLVED", "Numerically unresolved witness geometry: " + str(exc))
        return None

    if len(intervals) > max_intervals:
        return finish(
            "UNRESOLVED",
            "Interval budget cannot cover the mandatory complete coarse witness pass",
            search_budget_exhausted=True,
        )
    # Complete every original phase interval before any refinement. A tangent
    # branch can therefore never consume the budget ahead of a coarse witness.
    pending = deque()
    for lo, hi, _ in intervals:
        examined += 1
        coarse += 1
        result = visit(lo, hi)
        if result is not None:
            return result
        if lo < hi:
            if max_depth:
                mid = (lo + hi) / 2
                pending.extend([(lo, mid, 1), (mid, hi, 1)])
            else:
                depth_reached = True
    while pending and examined < max_intervals:
        lo, hi, depth = pending.popleft()
        examined += 1
        result = visit(lo, hi)
        if result is not None:
            return result
        if depth < max_depth:
            mid = (lo + hi) / 2
            pending.extend([(lo, mid, depth + 1), (mid, hi, depth + 1)])
        else:
            depth_reached = True
    limited = bool(pending)
    message = (
        "Bounded collision-witness search found no definite intersection; "
        "absence of collision has NOT been proved and material clearance remains unverified"
    )
    if limited:
        message += "; interval budget exhausted"
    elif depth_reached:
        message += "; requested search depth reached"
    return finish(
        "UNRESOLVED" if ambiguous else "UNVERIFIED",
        "Material overlap or thickness lies in the numeric uncertainty band; " + message
        if ambiguous
        else message,
        search_budget_exhausted=limited,
    )


def check_fold_clearance(
    sweep: FoldSweep,
    material: MaterialProfile,
    obstacles: object,
    *,
    expected_obstacle_ids: object,
    allowances: object = (),
    max_depth: int | None = None,
    max_intervals: int | None = None,
) -> ClearanceResult:
    """Certify a rigid digital sweep, or truthfully return why it is not proven.

    CLEAR means the complete continuous inflated sweep avoids every supplied
    material solid OUTSIDE the recorded permitted volumes. COLLISION has an
    actual angle witness with intersecting known-thickness solids, original
    midplanes, or an original midplane strictly inside known-thickness material.
    Unknown material uses bounded witness search, never an absence certificate.
    Default depth/interval budgets are 8/128 for any unknown material and remain
    12/4096 for the continuous all-known certification branch.
    A hull overlap or exhausted subdivision is UNRESOLVED, not collision/PASS.
    Radius is conservatively added to the whole sweep's displacement envelope;
    no inference of strain, material bendability, or automatic compensation is made.
    """
    base = {"tab_id": sweep.tab_id}
    try:
        unknown = material.thickness_mm is None
        thickness = 0.0 if unknown else _number(material.thickness_mm, positive=True)
        clearance, radius = _number(material.clearance_mm), _number(material.bend_radius_mm)
        items, permitted = list(obstacles), list(allowances)
        identifiers = [o.id for o in items]
        if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(
            expected_obstacle_ids
        ):
            raise ValueError("Complete obstacle registry does not match expected identities")
        if not {sweep.source_id, sweep.receiver_id} <= set(identifiers):
            raise ValueError("Source and receiver material must both be in the obstacle registry")
        unknown = unknown or any(o.thickness_mm is None for o in items)
        max_depth = (8 if unknown else 12) if max_depth is None else max_depth
        max_intervals = (128 if unknown else 4096) if max_intervals is None else max_intervals
        if (
            type(max_depth) is not int
            or max_depth < 0
            or type(max_intervals) is not int
            or max_intervals < 1
        ):
            raise ValueError(
                "Search depth must be a nonnegative integer and interval budget a positive integer"
            )
        origin, end = _vector(sweep.hinge_start_mm), _vector(sweep.hinge_end_mm)
        hinge_length = float(np.linalg.norm(end - origin))
        axis, normal = _normal(end - origin), _normal(sweep.initial_normal)
        angle = float(sweep.angle_deg)
        if not math.isfinite(angle) or abs(angle) > 180:
            raise ValueError("Supported signed fold angle is at most 180 degrees")
        if abs(np.dot(axis, normal)) > 1e-9:
            raise ValueError("The straight hinge must lie in the tab plane")
        theta = math.radians(angle)
        if (
            np.linalg.norm(
                _rotate(np.array([normal]), axis, theta)[0] - _normal(sweep.final_normal)
            )
            > 1e-8
        ):
            raise ValueError("Final material normal does not match the declared signed fold")
        arrays = [np.asarray(p, dtype=float) for p in sweep.patches_world_mm]
        arrays.extend(np.asarray(o.triangles_world_mm, dtype=float).reshape(-1, 3) for o in items)
        arrays.extend(np.asarray(a.vertices_world_mm, dtype=float) for a in permitted)
        if not arrays or not all(np.isfinite(a).all() for a in arrays):
            raise ValueError("Incomplete or nonfinite geometry")
        magnitude = max(
            [float(np.max(abs(a))) for a in arrays if a.size] + [float(np.max(abs(origin)))]
        )
        reach = max(float(np.max(np.linalg.norm(a - origin, axis=-1))) for a in arrays if a.size)
        # Include input face conditioning, not just the hinge length. Very
        # thin sliver triangles or almost flat permission solids can amplify
        # normal/intersection arithmetic; they must not obtain a tiny guard.
        condition = 1.0
        conditioning_inputs = [(np.asarray(p, dtype=float), 2) for p in sweep.patches_world_mm]
        conditioning_inputs.extend(
            (np.asarray(t, dtype=float), 2) for o in items for t in o.triangles_world_mm
        )
        conditioning_inputs.extend(
            (np.asarray(a.vertices_world_mm, dtype=float), 3) for a in permitted
        )
        for points, rank in conditioning_inputs:
            singular = np.linalg.svd(points - points.mean(axis=0), compute_uv=False)
            if len(singular) < rank or singular[rank - 1] <= 0:
                raise ValueError("Degenerate material face or contact permission")
            condition = max(condition, float(singular[0] / singular[rank - 1]))
        guard = max(
            1e-9,
            4096 * np.finfo(float).eps * (1 + magnitude) * (1 + reach / hinge_length + condition),
        )
        if magnitude > 1e6 or guard > 1e-4:
            raise ValueError("Coordinate conditioning exceeds the supported digital precision")
        patches = [_patch(p - origin, normal, guard) for p in sweep.patches_world_mm]
        if not patches or any(abs(np.dot(p[0], normal)) > guard for p in patches):
            raise ValueError("All tab patches and the hinge must share one initial plane")
        # A rigid tab belongs on one side of its actual boundary crease.
        all_points = np.vstack(patches)
        across = all_points @ np.cross(normal, axis)
        if across.min() < -guard and across.max() > guard:
            raise ValueError("Tab material straddles the hinge instead of meeting a boundary")
        on_hinge = all_points[abs(across) <= guard] @ axis
        if len(on_hinge) < 2 or np.ptp(on_hinge) <= guard:
            raise ValueError("Tab material has no nonzero connection to the declared hinge")
        if on_hinge.min() < -guard or on_hinge.max() > hinge_length + guard:
            raise ValueError("Tab connection lies outside the finite declared hinge interval")
        low, high = sorted((0.0, theta))
        planes, cuts, allowance_records = [], {low, high}, []
        for permission in permitted:
            if permission.obstacle_id not in (sweep.source_id, sweep.receiver_id):
                raise ValueError("No blanket permission for an independent obstacle is allowed")
            if permission.kind not in ("hinge", "final_contact") or not permission.reason.strip():
                raise ValueError("Every contact permission requires a kind and explicit reason")
            if permission.kind == "final_contact" and permission.obstacle_id != sweep.receiver_id:
                raise ValueError("Final-contact permission must refer to the actual receiver")
            hull = _hull(np.asarray(permission.vertices_world_mm, dtype=float) - origin)
            if hull is None:
                raise ValueError("Contact permission must be a finite nonzero convex volume")
            a, b = sorted(math.radians(float(v)) for v in permission.angle_interval_deg)
            if not math.isfinite(a + b) or a < low - 1e-12 or b > high + 1e-12 or a > b:
                raise ValueError("Contact permission angle interval lies outside this fold")
            a, b = max(a, low), min(b, high)
            planes.append((permission.obstacle_id, a, b, hull[1].equations))
            cuts.update((a, b))
            allowance_records.append(
                {
                    "obstacle_id": permission.obstacle_id,
                    "kind": permission.kind,
                    "reason": permission.reason,
                    "angle_interval_deg": [math.degrees(a), math.degrees(b)],
                    "vertices_world_mm": np.asarray(
                        permission.vertices_world_mm, dtype=float
                    ).tolist(),
                }
            )
        solids, original_triangles = [], {}
        for obstacle in items:
            t = (
                0.0
                if obstacle.thickness_mm is None
                else _number(obstacle.thickness_mm, positive=True)
            )
            triangles = np.asarray(obstacle.triangles_world_mm, dtype=float)
            if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or len(triangles) == 0:
                raise ValueError("Every obstacle needs its real nonempty triangle registry")
            for triangle in triangles - origin:
                original_triangles.setdefault(obstacle.id, []).append(triangle)
                face_normal = _normal(
                    np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
                )
                proxy_thickness = max(t, 4 * guard)
                hull = _hull(
                    np.vstack(
                        [
                            triangle - face_normal * proxy_thickness / 2,
                            triangle + face_normal * proxy_thickness / 2,
                        ]
                    )
                )
                if hull is None:
                    raise ValueError("Obstacle triangle prism is degenerate")
                solids.append((obstacle.id, hull))
    except (ValueError, TypeError, IndexError, AttributeError, ZeroDivisionError) as exc:
        return ClearanceResult("UNRESOLVED", str(exc), **base)

    padding = clearance + radius + guard
    base.update(
        numerical_guard_mm=guard,
        envelope_padding_mm=padding,
        allowances=tuple(allowance_records),
        checked_obstacle_ids=tuple(identifiers),
        material_thickness_mm=material.thickness_mm,
        clearance_mm=clearance,
        bend_radius_mm=radius,
    )
    cuts = sorted(cuts)
    intervals = [(a, b, 0) for a, b in zip(cuts, cuts[1:])] if len(cuts) > 1 else [(low, high, 0)]
    if unknown:
        return _unknown_witness_search(
            patches,
            axis,
            normal,
            thickness,
            items,
            original_triangles,
            solids,
            planes,
            intervals,
            origin,
            guard,
            base,
            max_depth,
            max_intervals,
        )
    examined, certified, uncertain = 0, 0, False
    cache = {}

    def chunks_for(active):
        if active not in cache:
            chunks = []
            for obstacle_id, solid in solids:
                pieces = [solid]
                for index in active:
                    identity, _, _, equations = planes[index]
                    if identity == obstacle_id:
                        pieces = [
                            piece
                            for current in pieces
                            for piece in _subtract(current, equations, guard)
                        ]
                chunks.extend((obstacle_id, piece) for piece in pieces)
            cache[active] = chunks
        return cache[active]

    stack = intervals[:]
    while stack:
        lo, hi, depth = stack.pop()
        examined += 1
        if examined > max_intervals:
            uncertain = True
            break
        active = tuple(i for i, (_, a, b, _) in enumerate(planes) if a <= lo and hi <= b)
        try:
            interval_chunks = chunks_for(active)
        except ValueError as exc:
            return ClearanceResult(
                "UNRESOLVED",
                str(exc),
                certified_intervals=certified,
                examined_intervals=examined,
                **base,
            )
        interval_clear = True
        for obstacle_id, solid in interval_chunks:
            for patch in patches:
                if _separated(patch, solid, axis, lo, hi, normal, thickness, padding, guard):
                    continue
                interval_clear = False
                for sample in (lo, (lo + hi) / 2, hi):
                    # At a permission's exact phase boundary, include every
                    # permission active at that point, not only those valid
                    # throughout this whole interval. Otherwise an authorized
                    # endpoint contact could become a false collision witness.
                    point_active = tuple(
                        i for i, (_, a, b, _) in enumerate(planes) if a <= sample <= b
                    )
                    for point_id, point_solid in chunks_for(point_active):
                        if point_id == obstacle_id and _static_collision(
                            patch, point_solid, axis, sample, normal, thickness, guard
                        ):
                            return ClearanceResult(
                                "COLLISION",
                                "Thick material intersects during the fold",
                                obstacle_id=obstacle_id,
                                witness_angle_deg=math.degrees(sample),
                                certified_intervals=certified,
                                examined_intervals=examined,
                                **base,
                            )
        if interval_clear:
            certified += 1
        elif depth < max_depth and lo < hi:
            mid = (lo + hi) / 2
            stack.extend([(lo, mid, depth + 1), (mid, hi, depth + 1)])
        else:
            # A single unproven leaf already prevents a continuous CLEAR.
            # Do not spend thousands of further cells re-proving that the
            # same unresolved tangency is unresolved in the UI thread.
            return ClearanceResult(
                "UNRESOLVED",
                "Continuous clearance has an unresolved interval",
                certified_intervals=certified,
                examined_intervals=examined,
                **base,
            )
    if uncertain:
        return ClearanceResult(
            "UNRESOLVED",
            "Continuous clearance could not be certified at this budget",
            certified_intervals=certified,
            examined_intervals=examined,
            **base,
        )
    return ClearanceResult(
        "CLEAR",
        "Continuous swept envelope is separated outside declared contacts",
        certified_intervals=certified,
        examined_intervals=examined,
        **base,
    )
