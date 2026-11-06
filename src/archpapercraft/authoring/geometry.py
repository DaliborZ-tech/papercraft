"""Model-mm geometry with explicit material holes and constrained tessellation."""

from __future__ import annotations

import math

import numpy as np
from scipy.spatial.transform import Rotation
from shapely import Polygon, constrained_delaunay_triangles
from shapely.validation import explain_validity

from .errors import ValidationError


def number(value, label="Hodnota", *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label}: zadejte konečné číslo.")
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValidationError(f"{label}: neplatná číselná hodnota.")
    return value


def vector(value, count, label="Souřadnice"):
    if not isinstance(value, (list, tuple, np.ndarray)) or len(value) != count:
        raise ValidationError(f"{label}: očekáváno {count} souřadnic.")
    return [number(v, label) for v in value]


def material_polygon(outer, holes=()):
    """Reject bad topology; never repair by buffer(0), filling holes or hulls."""
    try:
        loops = [np.asarray([vector(p, 2) for p in loop], dtype=float) for loop in [outer, *holes]]
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Neplatný obrys: {exc}") from exc
    for loop in loops:
        if len(loop) < 3:
            raise ValidationError("Uzavřený obrys potřebuje alespoň tři body.")
        if any(np.linalg.norm(b - a) <= 1e-9 for a, b in zip(loop, np.roll(loop, -1, axis=0))):
            raise ValidationError("Obrys obsahuje nulovou hranu.")
    result = Polygon(loops[0], loops[1:])
    if (
        not result.is_valid
        or result.is_empty
        or not math.isfinite(result.area)
        or result.area <= 1e-12
    ):
        raise ValidationError(f"Obrys není platná materiálová plocha: {explain_validity(result)}")
    shell = Polygon(loops[0])
    for index, loop in enumerate(loops[1:]):
        hole = Polygon(loop)
        if not shell.contains(hole) or shell.boundary.intersects(hole.boundary):
            raise ValidationError("Otvor musí ležet uvnitř obrysu bez dotyku jeho hrany.")
        for previous in loops[1 : index + 1]:
            if hole.intersects(Polygon(previous)):
                raise ValidationError("Otvory se nesmějí překrývat ani dotýkat.")
    return result


def signed_area(points):
    points = np.asarray(points, dtype=float)
    points = points - points[0]
    return float(
        np.sum(points[:, 0] * np.roll(points[:, 1], -1) - points[:, 1] * np.roll(points[:, 0], -1))
        / 2
    )


def triangulate(outer, holes=()):
    polygon = material_polygon(outer, holes)
    triangles = list(constrained_delaunay_triangles(polygon).geoms)
    if not triangles or abs(sum(t.area for t in triangles) - polygon.area) > max(
        1e-8, polygon.area * 1e-12
    ):
        raise ValidationError("Triangulace nepokryla materiálovou oblast.")
    vertices, faces = [], []
    positive = signed_area(outer) > 0
    for triangle in triangles:
        coordinates = list(triangle.exterior.coords)[:-1]
        if (signed_area(coordinates) > 0) != positive:
            coordinates.reverse()
        if not polygon.covers(triangle):
            raise ValidationError("Triangulace zasahuje mimo materiál.")
        faces.append(list(range(len(vertices), len(vertices) + 3)))
        vertices.extend(coordinates)
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int)


def rigid_matrix(position=(0, 0, 0), rotation=(0, 0, 0)):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_euler(
        "xyz", vector(rotation, 3, "Úhel"), degrees=True
    ).as_matrix()
    result[:3, 3] = vector(position, 3, "Poloha")
    return result


def validate_rigid(matrix):
    try:
        matrix = np.asarray(matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Neplatná rodičovská transformace.") from exc
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValidationError("Transformace musí být konečná matice 4×4.")
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-12, rtol=0):
        raise ValidationError("Neplatná homogenní transformace.")
    linear = matrix[:3, :3]
    if not np.allclose(linear.T @ linear, np.eye(3), atol=1e-10, rtol=0) or not math.isclose(
        np.linalg.det(linear), 1, abs_tol=1e-10
    ):
        raise ValidationError(
            "Konstrukci lze rigidně umístit; měřítko, smyk a zrcadlení nejsou podporované."
        )
    return matrix


def page_points(points, placement):
    angle = math.radians(placement.rotation_deg)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    return np.asarray(points, dtype=float) @ rotation.T + [placement.x_mm, placement.y_mm]


def path(points, closed=False):
    return {"points": np.asarray(points, dtype=float).tolist(), "closed": bool(closed)}
