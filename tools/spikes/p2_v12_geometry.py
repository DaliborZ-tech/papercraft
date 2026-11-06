r"""Isolated P2 v1.2 geometry experiments. This is NOT a production API/schema.

Run: .venv\Scripts\python.exe tools/spikes/p2_v12_geometry.py
Coordinates are mm; classifications distinguish analytic proof from sampling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[2]


def require_positive(value, name):
    if isinstance(value, bool) or not math.isfinite(float(value)) or float(value) <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return float(value)


@dataclass(frozen=True)
class Profile:
    """Analytic open upper arch, u in [0,1], with explicit piecewise breaks."""

    kind: str
    a: float = 20.0
    b: float = 30.0

    def __post_init__(self):
        require_positive(self.a, "profile half-width")
        require_positive(self.b, "profile height")
        if self.kind not in ("circle", "ellipse", "gothic"):
            raise ValueError("unknown analytic profile")
        if self.kind == "gothic" and self.b < self.a:
            raise ValueError("pointed arch height must be at least its half-width")

    @property
    def breaks(self):
        return (0.5,) if self.kind == "gothic" else ()

    def _evaluate(self, u, derivative=False):
        if not 0 <= u <= 1:
            raise ValueError("profile parameter outside interval")
        if self.kind in ("circle", "ellipse"):
            theta = math.pi * (1 - u)
            height = self.a if self.kind == "circle" else self.b
            if derivative:
                return np.array(
                    [self.a * math.pi * math.sin(theta), -height * math.pi * math.cos(theta), 0.0]
                )
            return np.array([self.a * math.cos(theta), height * math.sin(theta), 0.0])
        center = (self.b**2 - self.a**2) / (2 * self.a)
        radius = self.a + center
        apex_angle = math.atan2(self.b, center)
        if u <= 0.5:
            theta = math.pi - 2 * u * apex_angle
            cx, speed = center, -2 * apex_angle
        else:
            theta = 2 * (1 - u) * apex_angle
            cx, speed = -center, -2 * apex_angle
        if derivative:
            return np.array(
                [-radius * math.sin(theta) * speed, radius * math.cos(theta) * speed, 0.0]
            )
        return np.array([cx + radius * math.cos(theta), radius * math.sin(theta), 0.0])

    def point(self, u):
        return self._evaluate(u)

    def derivative(self, u):
        return self._evaluate(u, True)


def integrate(function, start, end, breaks=()):
    points = [start, *[p for p in breaks if start < p < end], end]
    results = [quad(function, a, b, epsabs=1e-10, epsrel=1e-11) for a, b in zip(points, points[1:])]
    return sum(r[0] for r in results), sum(r[1] for r in results)


@dataclass(frozen=True)
class Loft:
    profile0: Profile
    profile1: Profile
    scale1: float = 1.0
    depth: float = 30.0
    twist_deg: float = 0.0

    def __post_init__(self):
        require_positive(self.scale1, "profile scale")
        if not math.isfinite(self.depth) or not math.isfinite(self.twist_deg):
            raise ValueError("nonfinite loft parameter")

    @property
    def rotation(self):
        theta = math.radians(self.twist_deg)
        c, s = math.cos(theta), math.sin(theta)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

    def components(self, u):
        base, derivative = self.profile0.point(u), self.profile0.derivative(u)
        other = self.rotation @ (self.profile1.point(u) * self.scale1) + [0, 0, self.depth]
        other_derivative = self.rotation @ (self.profile1.derivative(u) * self.scale1)
        return base, derivative, other - base, other_derivative - derivative

    def point(self, u, v):
        if not 0 <= v <= 1:
            raise ValueError("ruling parameter outside trim interval")
        base, _, direction, _ = self.components(u)
        return base + v * direction

    def metric(self, u, v):
        _, base_derivative, direction, direction_derivative = self.components(u)
        tangent = base_derivative + v * direction_derivative
        return np.array(
            [np.dot(tangent, tangent), np.dot(tangent, direction), np.dot(direction, direction)]
        )

    def differential(self, u, v):
        _, base_derivative, direction, direction_derivative = self.components(u)
        tangent = base_derivative + v * direction_derivative
        jacobian = float(np.linalg.norm(np.cross(tangent, direction)))
        triple = float(np.dot(base_derivative, np.cross(direction, direction_derivative)))
        normalizer = float(
            np.linalg.norm(base_derivative)
            * np.linalg.norm(direction)
            * np.linalg.norm(direction_derivative)
        )
        if jacobian <= 1e-10:
            return {
                "regular": False,
                "jacobian": jacobian,
                "triple": triple,
                "residual": None,
                "K": None,
            }
        return {
            "regular": True,
            "jacobian": jacobian,
            "triple": triple,
            "residual": abs(triple) / normalizer if normalizer else 0.0,
            "K": -(triple**2) / jacobian**4,
        }


def developability_evidence(loft):
    samples = [
        loft.differential(float(u), float(v))
        for u in np.linspace(0.007, 0.993, 53)
        if abs(u - 0.5) > 0.001
        for v in (0.0, 0.5, 1.0)
    ]
    regular = all(s["regular"] for s in samples)
    nonzero = max((s["residual"] or 0) for s in samples) > 1e-10
    identical_profiles = loft.profile0 == loft.profile1
    regularity = None
    singularities = []
    planar_circle_singularity = None
    if loft.depth == 0 and identical_profiles and loft.profile0.kind == "circle":
        cosine = math.cos(math.radians(loft.twist_deg))
        denominator = loft.scale1**2 - 2 * loft.scale1 * cosine + 1
        if denominator > 0:
            fraction = (1 - loft.scale1 * cosine) / denominator
            if 0 <= fraction <= 1:
                planar_circle_singularity = fraction
    if loft.depth == 0 and identical_profiles and loft.twist_deg % 360 == 180:
        verdict, proof = (
            "DEGENERATE_OR_SINGULAR",
            "analytic half-turn gives S=(1-(1+k)v)C0; its entire profile collapses "
            "at the interior ruling fraction v=1/(1+k)",
        )
        singularities = [{"kind": "collapsed_profile", "v": 1 / (1 + loft.scale1)}]
    elif loft.depth == 0 and identical_profiles and loft.twist_deg == 0 and loft.scale1 == 1:
        verdict, proof = (
            "DEGENERATE_OR_SINGULAR",
            "coincident profiles give a zero ruling on the entire parameter domain",
        )
        singularities = [{"kind": "zero_ruling", "v_interval": [0.0, 1.0]}]
    elif planar_circle_singularity is not None:
        verdict, proof = (
            "DEGENERATE_OR_SINGULAR",
            "analytic circular planar Jacobian vanishes at an interior ruling fraction",
        )
        singularities = [{"kind": "zero_jacobian", "v": planar_circle_singularity}]
    elif not regular:
        verdict, proof = "DEGENERATE_OR_SINGULAR", "sampled degeneracy; exact flattening forbidden"
    elif (
        loft.depth == 0
        and identical_profiles
        and loft.twist_deg == 0
        and loft.scale1 != 1
        and loft.profile0.kind in ("circle", "ellipse")
    ):
        verdict, proof = (
            "EXACT_PLANAR",
            "positive untwisted half-ellipse homothety has a strictly positive analytic "
            "Jacobian bound and a simple semi-annular boundary",
        )
        profile = loft.profile0
        a, b = profile.a, profile.a if profile.kind == "circle" else profile.b
        regularity = {
            "analytic_jacobian_lower_bound_mm2": (
                min(1.0, loft.scale1) * abs(loft.scale1 - 1) * math.pi * a * b
            ),
            "valid_domain": "u in [0,1], v in [0,1]",
            "corner_policy": "endpoints are boundary corners; profile is smooth",
            "boundary_simple": True,
            "boundary_proof": (
                "positive unequal radial factors and monotone theta in [0,pi] "
                "give an injective affine image of a semi-annulus; radial connectors "
                "at theta=0 and theta=pi are disjoint"
            ),
            "material_area_mm2": 0.5 * math.pi * a * b * abs(loft.scale1**2 - 1),
        }
    elif loft.depth == 0:
        verdict, proof = (
            "UNPROVEN",
            "planarity only proves zero Gaussian curvature where regular; "
            "global parameter regularity and a simple material boundary are not proved",
        )
    elif identical_profiles and loft.twist_deg == 0 and loft.depth > 0:
        verdict, proof = (
            "EXACT_CYLINDRICAL" if loft.scale1 == 1 else "EXACT_CONICAL",
            "analytic extrusion/homothety identity makes the scalar triple product "
            "identically zero on each smooth span",
        )
    elif nonzero:
        verdict, proof = (
            "NONDEVELOPABLE",
            "nonzero scalar triple product at a regular point disproves exact developability",
        )
    else:
        verdict, proof = "UNPROVEN", "finite zero samples are not an analytic certificate"
    if identical_profiles and loft.twist_deg == 0 and loft.depth > 0:
        p = loft.profile0
        min_speed = (
            2
            * (p.a + (p.b * p.b - p.a * p.a) / (2 * p.a))
            * math.atan2(p.b, (p.b * p.b - p.a * p.a) / (2 * p.a))
            if p.kind == "gothic"
            else math.pi * min(p.a, p.a if p.kind == "circle" else p.b)
        )
        regularity = {
            "analytic_jacobian_lower_bound_mm2": min(1.0, loft.scale1) * loft.depth * min_speed,
            "valid_domain": "u in each open smooth profile span, v in [0,1]",
            "corner_policy": "split at u=.5; preserve the ruling as a crease, not a smooth tangent"
            if p.breaks
            else "smooth profile",
        }
    if verdict.startswith("EXACT") and (
        regularity is None
        or not math.isfinite(regularity["analytic_jacobian_lower_bound_mm2"])
        or regularity["analytic_jacobian_lower_bound_mm2"] <= 0
    ):
        verdict = "UNPROVEN"
        proof = "no finite positive analytic regularity bound is available"
        regularity = None
    return {
        "verdict": verdict,
        "proof": proof,
        "sample_count": len(samples),
        "regularity_proof": regularity,
        "analytic_singularities": singularities,
        "trim_domain": {"u": [0.0, 1.0], "v": [0.0, 1.0]},
        "max_normalized_triple": max((s["residual"] or 0) for s in samples),
        "min_K_per_mm2": min((s["K"] for s in samples if s["K"] is not None), default=None),
        "minimum_sampled_jacobian": min(s["jacobian"] for s in samples),
        "corner_parameters": list(loft.profile0.breaks),
    }


def exact_homothetic_flat(loft, u, v):
    if loft.profile0 != loft.profile1 or loft.twist_deg != 0 or loft.depth <= 0:
        raise ValueError(
            "only proved regular normal extrusion / homothetic cones are supported by this spike"
        )
    profile, ratio = loft.profile0, loft.scale1
    if ratio == 1:
        distance, error = integrate(
            lambda t: np.linalg.norm(profile.derivative(t)), 0, u, profile.breaks
        )
        return np.array([distance, loft.depth * v]), error
    apex = np.array([0.0, 0.0, -loft.depth / (ratio - 1)])

    def angular_speed(t):
        ray = profile.point(t) - apex
        return float(np.linalg.norm(np.cross(ray, profile.derivative(t))) / np.dot(ray, ray))

    angle, error = integrate(angular_speed, 0, u, profile.breaks)
    radius = np.linalg.norm(profile.point(u) - apex) * (1 + v * (ratio - 1))
    return radius * np.array([math.cos(angle), math.sin(angle)]), error * radius


def flat_metric_error(loft):
    errors, integration_errors = [], []
    for u in (0.12, 0.27, 0.42, 0.58, 0.73, 0.88):
        for v in (0.2, 0.5, 0.8):
            delta = 1e-5
            pu, eu = exact_homothetic_flat(loft, u + delta, v)
            mu, em = exact_homothetic_flat(loft, u - delta, v)
            pv, ev = exact_homothetic_flat(loft, u, v + delta)
            mv, en = exact_homothetic_flat(loft, u, v - delta)
            du, dv = (pu - mu) / (2 * delta), (pv - mv) / (2 * delta)
            actual = np.array([np.dot(du, du), np.dot(du, dv), np.dot(dv, dv)])
            expected = loft.metric(u, v)
            errors.append(float(np.max(np.abs(actual - expected)) / max(expected[0], expected[2])))
            integration_errors.extend((eu, em, ev, en))
    return {
        "max_normalized_metric_error": max(errors),
        "max_quad_reported_position_error_mm": max(integration_errors),
        "finite_difference_step": 1e-5,
    }


def cylinder_exact(radius=10.0, height=30.0):
    require_positive(radius, "radius")
    require_positive(height, "height")
    return {
        "width_mm": 2 * math.pi * radius,
        "height_mm": height,
        "area_mm2": 2 * math.pi * radius * height,
    }


def cone_exact(radius0=10.0, radius1=20.0, slant=30.0):
    require_positive(slant, "slant")
    if any(not math.isfinite(r) or r < 0 for r in (radius0, radius1)) or max(radius0, radius1) == 0:
        raise ValueError("cone radii must be nonnegative and not both zero")
    dr = abs(radius1 - radius0)
    if dr >= slant:
        raise ValueError("a regular truncated cone requires slant > radius difference")
    if dr == 0:
        return {"mode": "CYLINDER", **cylinder_exact(radius0, slant)}
    return {
        "mode": "ANNULAR_SECTOR",
        "inner_radius_mm": min(radius0, radius1) * slant / dr,
        "outer_radius_mm": max(radius0, radius1) * slant / dr,
        "angle_rad": 2 * math.pi * dr / slant,
        "arc0_mm": 2 * math.pi * radius0,
        "arc1_mm": 2 * math.pi * radius1,
        "radial_edge_mm": slant,
        "area_mm2": math.pi * (radius0 + radius1) * slant,
        "singular_boundary": ["apex"] if min(radius0, radius1) == 0 else [],
    }


def stable_sector_flat(radius0, radius1, slant, u, v):
    """Local coordinates avoid subtracting enormous near-cylinder radii."""
    if not 0 <= u <= 1 or not 0 <= v <= 1:
        raise ValueError("parameter outside trimmed sector")
    data = cone_exact(radius0, radius1, slant)
    if data["mode"] == "CYLINDER":
        return np.array([2 * math.pi * radius0 * u, slant * v])
    inner = data["inner_radius_mm"]
    angle = data["angle_rad"] * u
    radial = slant * (v if radius1 > radius0 else 1 - v)
    return np.array(
        [
            (inner + radial) * math.sin(angle),
            radial - (inner + radial) * 2 * math.sin(angle / 2) ** 2,
        ]
    )


def approximate_facets(loft, n_u, n_v):
    if n_u < 2 or n_v < 1:
        raise ValueError("insufficient facet subdivisions")
    area, max_fit, max_normal = 0.0, 0.0, 0.0
    for i in range(n_u):
        for j in range(n_v):
            u, v = i / n_u, j / n_v
            a, b, c, d = (
                loft.point(u, v),
                loft.point(u + 1 / n_u, v),
                loft.point(u, v + 1 / n_v),
                loft.point(u + 1 / n_u, v + 1 / n_v),
            )
            area += 0.5 * (
                np.linalg.norm(np.cross(b - a, d - a)) + np.linalg.norm(np.cross(d - a, c - a))
            )
            for x, y in ((0.25, 0.25), (0.5, 0.5), (0.75, 0.75), (0.25, 0.75), (0.75, 0.25)):
                interpolated = (
                    (1 - x) * a + (x - y) * b + y * d
                    if y <= x
                    else (1 - y) * a + x * d + (y - x) * c
                )
                exact = loft.point(u + x / n_u, v + y / n_v)
                max_fit = max(max_fit, float(np.linalg.norm(exact - interpolated)))
                _, derivative, direction, direction_derivative = loft.components(u + x / n_u)
                normal = np.cross(derivative + (v + y / n_v) * direction_derivative, direction)
                faceted_normal = np.cross(b - a, d - a) if y <= x else np.cross(d - a, c - a)
                cosine = float(
                    np.dot(normal, faceted_normal)
                    / (np.linalg.norm(normal) * np.linalg.norm(faceted_normal))
                )
                max_normal = max(max_normal, math.degrees(math.acos(float(np.clip(cosine, -1, 1)))))
    exact_boundary = integrate(
        lambda u: np.linalg.norm(loft.profile0.derivative(u)), 0, 1, loft.profile0.breaks
    )[0]
    points = [loft.point(i / n_u, 0) for i in range(n_u + 1)]
    chord_length = sum(float(np.linalg.norm(b - a)) for a, b in zip(points, points[1:]))
    bound = None
    if loft.profile0.kind == "circle" and loft.profile0 == loft.profile1:
        # Curve-linear interpolation error <= Muu*du²/8. Replacing a bilinear
        # cell by either diagonal adds <= Muv*du*dv/4. Derivatives are bounded
        # analytically for this circular family; this is not a sampling bound.
        radius, ratio = loft.profile0.a, loft.scale1
        muu = math.pi**2 * radius * max(1.0, ratio)
        muv = (
            math.pi
            * radius
            * math.sqrt(ratio**2 + 1 - 2 * ratio * math.cos(math.radians(loft.twist_deg)))
        )
        bound = muu / (8 * n_u * n_u) + muv / (4 * n_u * n_v)
    return {
        "mode": "EXPLICIT_FACET_APPROXIMATION",
        "n_u": n_u,
        "n_v": n_v,
        "triangle_islands": 2 * n_u * n_v,
        "max_sampled_surface_distance_mm": max_fit,
        "sampling": "5 parameter samples per cell; NOT a certified Hausdorff maximum",
        "max_sampled_normal_angle_deg": max_normal,
        "normal_angle_global_bound": None,
        "analytic_global_same_parameter_distance_upper_bound_mm": bound,
        "mesh_area_mm2": float(area),
        "smooth_boundary_length_mm": exact_boundary,
        "boundary_chord_length_mm": chord_length,
        "boundary_shortening_mm": exact_boundary - chord_length,
        "assembly_policy": (
            "separate triangle islands with explicit cuts; "
            "no claim of coherent strain-free flattening of original smooth loft"
        ),
    }


def smooth_loft_area(loft):
    value, error = integrate(
        lambda u: quad(
            lambda v: np.linalg.norm(
                np.cross(loft.components(u)[1] + v * loft.components(u)[3], loft.components(u)[2])
            ),
            0,
            1,
            epsabs=1e-9,
        )[0],
        0,
        1,
        loft.profile0.breaks,
    )
    return {"area_mm2": value, "outer_integrator_reported_error_mm2": error}


def roof_attachment(
    eave_overhang=5.0, gable_overhang=3.0, slope=1.0, tab_width=5.0, normal_gap=0.0
):
    if (
        eave_overhang <= 0
        or gable_overhang < 0
        or tab_width <= 0
        or not all(
            math.isfinite(v) for v in (eave_overhang, gable_overhang, slope, tab_width, normal_gap)
        )
    ):
        raise ValueError("invalid roof fixture")
    origin = np.array([-gable_overhang, -eave_overhang, 40 - eave_overhang * slope])
    u_axis = np.array([1.0, 0, 0])
    v_axis = np.array([0.0, 1.0, slope]) / math.sqrt(1 + slope * slope)
    normal = np.cross(u_axis, v_axis)
    wall = np.array([[0.0, 0, 40], [100.0, 0, 40]]) + normal * normal_gap
    uv = np.column_stack([(wall - origin) @ u_axis, (wall - origin) @ v_axis])
    mapped = origin + np.outer(uv[:, 0], u_axis) + np.outer(uv[:, 1], v_axis)
    gap = float(np.max(np.linalg.norm(mapped - wall, axis=1)))
    width, height = 100 + 2 * gable_overhang, (30 + eave_overhang) * math.sqrt(1 + slope * slope)
    available = max(0.0, height - float(uv[0, 1]))
    contact_width = min(tab_width, available)
    return {
        "roof_uv_bounds_mm": [0.0, width, 0.0, height],
        "roof_origin_world_mm": origin.tolist(),
        "attachment_uv_mm": uv.tolist(),
        "mapped_wall_line_world_mm": mapped.tolist(),
        "maximum_contact_gap_mm": gap,
        "contact_valid_0_01mm": gap <= 0.01,
        "line_strictly_inside_surface": bool(
            (uv[:, 0] > 0).all()
            and (uv[:, 0] < width).all()
            and (uv[:, 1] > 0).all()
            and (uv[:, 1] < height).all()
        ),
        "fake_boundary_distance_mm": eave_overhang * math.sqrt(1 + slope * slope),
        "nominal_tab_footprint_mm2": 100 * tab_width,
        "available_material_contact_mm2": 100 * contact_width if gap <= 0.01 else 0.0,
        "complete_footprint_supported": gap <= 0.01 and contact_width == tab_width,
        "outside_boundary_unchanged": True,
    }


def base_attachment():
    # Base [-10,110]x[-10,70], independent of the open building shell.
    # Wall-bottom glue strips are interior regions, NOT base cutting boundaries.
    material = np.array([[-10.0, -10.0], [110.0, -10.0], [110.0, 70.0], [-10.0, 70.0]])
    hole = np.array([[40.0, -5.0], [60.0, -5.0], [60.0, 5.0], [40.0, 5.0]])
    glue = [
        np.array([[0.0, -5.0], [100.0, -5.0], [100.0, 0.0], [0.0, 0.0]]),
        np.array([[0.0, 60.0], [100.0, 60.0], [100.0, 65.0], [0.0, 65.0]]),
        np.array([[-5.0, 0.0], [0.0, 0.0], [0.0, 60.0], [-5.0, 60.0]]),
        np.array([[100.0, 0.0], [105.0, 0.0], [105.0, 60.0], [100.0, 60.0]]),
    ]
    nominal = sum(abs(area2(poly)) for poly in glue)
    removed = sum(clipped_area(poly, hole) for poly in glue)
    actual = sum(clipped_area(poly, material) - clipped_area(poly, hole) for poly in glue)
    wall = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]])
    base_origin = np.array([-10.0, -10.0, 0.0])
    uv = wall[:, :2] - base_origin[:2]
    mapped = np.column_stack([uv + base_origin[:2], np.zeros(2)])
    return {
        "base_bounds_mm": [-10.0, 110.0, -10.0, 70.0],
        "building_footprint_mm": [0.0, 100.0, 0.0, 60.0],
        "building_floor_inserted": False,
        "wall_bottom_contact_gap_mm": 0.0,
        "wall_contact_uv_mm": uv.tolist(),
        "evaluated_contact_gap_mm": float(np.linalg.norm(mapped - wall, axis=1).max()),
        "glue_footprints_world_xy": [poly.tolist() for poly in glue],
        "nominal_glue_region_mm2": nominal,
        "hole_bounds_mm": [40.0, 60.0, -5.0, 5.0],
        "hole_intersection_with_left_glue_mm2": removed,
        "actual_material_glue_region_mm2": actual,
        "hole_removes_wall_contact_interval_mm": 20.0,
        "complete_line_material_support": False,
        "attachment_is_cut_path": False,
    }


def area2(poly):
    p = np.asarray(poly, float)
    p = p - p[0]
    return 0.5 * sum(
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0])
        for a, b in zip(p, np.roll(p, -1, axis=0))
    )


def clipped_area(subject, clip):
    clip = np.asarray(clip, float)
    if area2(clip) < 0:
        clip = clip[::-1]
    result = list(np.asarray(subject, float))
    for a, b in zip(clip, np.roll(clip, -1, axis=0)):
        source, result = result, []
        if not source:
            return 0.0

        def side(p):
            return float(np.cross(np.append(b - a, 0), np.append(p - a, 0))[2])

        for p, q in zip(source, source[1:] + source[:1]):
            dp, dq = side(p), side(q)
            if dp >= 0:
                result.append(p)
            if (dp >= 0) != (dq >= 0):
                result.append(p + (q - p) * dp / (dp - dq))
    return abs(area2(result)) if len(result) >= 3 else 0.0


def segmented_tabs(radius=20.0, count=24, gap=0.8, width=5.0, bend_deg=90.0, bend_zone=0.5):
    require_positive(radius, "radius")
    require_positive(width, "tab width")
    if (
        type(count) is not int
        or count < 3
        or gap < 0
        or not math.isfinite(gap)
        or not 0 <= bend_zone < width
        or not math.isfinite(bend_deg)
    ):
        raise ValueError("invalid segmented-tab settings")
    pitch = 2 * math.pi * radius / count
    if gap >= pitch:
        raise ValueError("gap consumes the whole attachment interval")
    base_arc = pitch - gap
    alpha = base_arc / radius
    chord = 2 * radius * math.sin(alpha / 2)
    sagitta = radius * (1 - math.cos(alpha / 2))
    target_height = width - sagitta
    if target_height <= 0:
        raise ValueError("tab has no inward material contact height")
    polygons = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        polygons.append(
            np.array(
                [
                    [radius * math.cos(angle - alpha / 2), radius * math.sin(angle - alpha / 2)],
                    [radius * math.cos(angle + alpha / 2), radius * math.sin(angle + alpha / 2)],
                    [(radius - width) * math.cos(angle), (radius - width) * math.sin(angle)],
                ]
            )
        )
    collisions = [float(clipped_area(a, b)) for a, b in combinations(polygons, 2)]
    flat_area = 0.5 * base_arc * width
    target_area = 0.5 * chord * target_height
    adhesion = target_area * max(0.0, 1 - bend_zone / target_height) ** 2
    outside = sum(float(np.linalg.norm(poly, axis=1).max()) > radius + 1e-10 for poly in polygons)
    material_adhesion = adhesion
    clip_error = 0.0
    if outside:
        angles = np.linspace(0, 2 * math.pi, 1024, endpoint=False)
        cap = np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])
        first = polygons[0]
        tip = first[-1]
        factor = max(0.0, 1 - bend_zone / target_height)
        adhesive = np.array([tip + factor * (first[0] - tip), tip + factor * (first[1] - tip), tip])
        material_adhesion = clipped_area(adhesive, cap)
        clip_error = math.pi * radius**2 - 512 * radius**2 * math.sin(2 * math.pi / 1024)
    normal_error = abs(math.sin(math.radians(bend_deg - 90)))
    gap_at_tip = width * normal_error
    contact_band = min(target_height, 0.1 / normal_error) if normal_error else target_height
    contact_fraction = max(
        0.0, 2 * contact_band / target_height - (contact_band / target_height) ** 2
    )
    flat_side = math.hypot(base_arc / 2, width)
    target_side = math.hypot(chord / 2, target_height)
    return {
        "count": count,
        "radius_mm": radius,
        "gap_mm": gap,
        "width_mm": width,
        "base_arc_mm": base_arc,
        "base_chord_mm": chord,
        "arc_chord_mismatch_mm": base_arc - chord,
        "hinge_sagitta_mm": sagitta,
        "flat_triangle_area_mm2": flat_area,
        "target_cap_triangle_area_mm2": target_area,
        "maximum_side_length_change_mm": abs(flat_side - target_side),
        "nominal_adhesion_excluding_bend_zone_mm2_per_tab": adhesion,
        "material_limited_adhesion_mm2_per_tab": material_adhesion,
        "cap_clip_area_error_upper_bound_mm2_per_tab": clip_error,
        "footprints_extending_outside_cap": outside,
        "bend_deg": bend_deg,
        "tip_plane_gap_if_rigid_misbent_mm": gap_at_tip,
        "fraction_within_0_1mm_contact_band_before_bend_relief": contact_fraction,
        "collision_pairs_over_1e_8_mm2": sum(a > 1e-8 for a in collisions),
        "maximum_collision_mm2": max(collisions, default=0.0),
        "spike_bend_clearance_0_2mm_pass": sagitta <= 0.2,
        "spike_min_adhesion_8mm2_pass": adhesion >= 8,
        "certificate": (
            "APPROXIMATE_ATTACHMENT; target footprint is NOT proof "
            "that the curved hinge bends isometrically into a planar cap"
        ),
        "footprints": [p.tolist() for p in polygons],
    }


def experiments():
    circle = Profile("circle", 20, 20)
    planar = Loft(circle, circle, 1.5, 0)
    spatial = Loft(circle, circle, 1.5, 30)
    profiles = {}
    for profile in [circle, Profile("ellipse", 20, 30), Profile("gothic", 20, 30)]:
        exact = Loft(profile, profile, 1.4, 15)
        twisted = Loft(profile, profile, 1.4, 15, 25)
        profiles[profile.kind] = {
            "homothetic": developability_evidence(exact),
            "metric_check": flat_metric_error(exact),
            "twisted": developability_evidence(twisted),
        }
    twisted = Loft(circle, circle, 1.2, 30, 30)
    analytic_triple = -30 * 1.2 * 20**2 * math.sin(math.radians(30)) * math.pi**2
    approximations = [approximate_facets(twisted, n, n // 4) for n in (8, 16, 32, 64, 128)]
    smooth_area = smooth_loft_area(twisted)
    for row in approximations:
        row["mesh_area_error_mm2"] = row["mesh_area_mm2"] - smooth_area["area_mm2"]
    different_gothic = Loft(Profile("gothic", 20, 30), Profile("gothic", 18, 25), 1.0, 10.0)
    return {
        "planar_vs_spatial": {
            "planar": developability_evidence(planar),
            "planar_band_analytic_area_mm2": 0.5 * math.pi * (30**2 - 20**2),
            "spatial": developability_evidence(spatial),
            "spatial_metric": flat_metric_error(spatial),
        },
        "exact_cylinder": cylinder_exact(),
        "exact_cone": cone_exact(),
        "full_cone": cone_exact(0, 20, 30),
        "cylinder_limit": cone_exact(10, 10, 30),
        "near_cylinder": {
            "parameters": cone_exact(10, 10 + 1e-14, 30),
            "stable_outer_end": stable_sector_flat(10, 10 + 1e-14, 30, 1, 1).tolist(),
        },
        "profiles": profiles,
        "different_gothic": developability_evidence(different_gothic),
        "twisted_loft": {
            "evidence": developability_evidence(twisted),
            "triple_at_u0_37": twisted.differential(0.37, 0.5)["triple"],
            "independent_circle_triple_oracle": analytic_triple,
            "smooth_area_quadrature": smooth_area,
            "approximation": approximations,
        },
        "roof_interior_attachment": {
            "valid": roof_attachment(),
            "changed_overhang": roof_attachment(8),
            "gap_failure": roof_attachment(normal_gap=1),
            "oversize_tab": roof_attachment(tab_width=50),
        },
        "base_region_attachment": base_attachment(),
        "cylinder_segmented_tabs": {str(n): segmented_tabs(count=n) for n in (12, 24, 48)},
        "tab_failures": {
            "wide_collision": segmented_tabs(width=25),
            "wrong_bend": segmented_tabs(bend_deg=80),
        },
        "dr01_planar_counterexamples": {
            "half_turn_collapse": developability_evidence(Loft(circle, circle, 1.4, 0, 180)),
            "half_turn_jacobian_at_v_5_12": Loft(circle, circle, 1.4, 0, 180).differential(
                0.37, 5 / 12
            )["jacobian"],
            "equal_circle_rotated_30": developability_evidence(Loft(circle, circle, 1, 0, 30)),
            "unproved_planar_twist_25": developability_evidence(Loft(circle, circle, 1.4, 0, 25)),
            "unproved_planar_gothic": developability_evidence(
                Loft(Profile("gothic", 20, 30), Profile("gothic", 20, 30), 1.4, 0)
            ),
        },
    }


def write_tabs_svg(results, path):
    def plot(polygons, x, title):
        paths = []
        for poly in polygons:
            coords = " ".join(f"{x + 3 * p[0]:.4f},{95 - 3 * p[1]:.4f}" for p in poly)
            paths.append(
                f'<polygon points="{coords}" fill="#d5e9f7" stroke="#193b5a" stroke-width="0.6"/>'
            )
        return f'<text x="{x}" y="20" text-anchor="middle" font-size="13">{title}</text>' + "".join(
            paths
        )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="620" height="200" '
        'viewBox="0 0 620 200"><rect width="620" height="200" fill="white"/>'
    )
    svg += plot(
        results["cylinder_segmented_tabs"]["24"]["footprints"],
        155,
        "24 tabs, width 5 mm: target footprints",
    )
    svg += plot(
        results["tab_failures"]["wide_collision"]["footprints"],
        465,
        "24 tabs, width 25 mm: collisions",
    )
    path.write_text(svg + "</svg>\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/p2/v1.2/evidence/geometry-results.json"
    )
    args = parser.parse_args()
    started = time.perf_counter()
    results = experiments()
    report = {
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha_semantics": (
            "checkout parent HEAD only; uncommitted spike code is pinned by source_files_sha256"
        ),
        "source_files_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (Path(__file__), ROOT / "tests/spikes/test_p2_v12_geometry.py")
        },
        "date": "2026-11-06",
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "command": subprocess.list2cmdline([sys.executable, *sys.argv]),
        "elapsed_seconds": time.perf_counter() - started,
        "units": "mm; analytic and sampled/approximate certificates are separate",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    write_tabs_svg(
        results,
        args.output.with_name(args.output.stem.replace("results", "tab-footprints") + ".svg"),
    )
    print(f"Geometry spike evidence: {args.output}; {report['elapsed_seconds']:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
