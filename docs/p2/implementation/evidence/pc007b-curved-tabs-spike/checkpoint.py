"""Exploratory C geometry only: floating experiments are NOT certificates."""

import json
import math
from pathlib import Path


def experiment(radius, slope, base=2.0, depth=2.0, relief=0.5, count=12):
    a = base / (2 * radius)
    h = math.sqrt(1 - slope*slope)
    if slope:
        edge_x = radius / slope * math.sin(slope*a)
        # Stable near the cylindrical limit; no subtraction of nearby cosines.
        edge_y = -2 * radius / slope * math.sin(slope*a/2)**2
    else:
        edge_x, edge_y = base/2, 0.0
    glue_half_base = edge_x * (depth-relief) / (depth-edge_y)
    glue_area = glue_half_base * (depth-relief)
    d0 = radius*a*a/2 + radius*(1+slope*slope)*a**3/6
    f = radius*abs(slope)*a*a/2
    collar_correction = d0 + f
    cos_lower = 1-(slope*a)**2/2
    fprime = abs(slope)*a/cos_lower
    collar_height_lower = relief-f
    dx = a/cos_lower + (1/cos_lower-1) + fprime
    dx += fprime*collar_correction/collar_height_lower
    dy = collar_correction/collar_height_lower
    strain_upper_candidate = math.hypot(dx, dy)
    body_distance_lower_candidate = relief*h - d0 - depth*a
    sector_half = edge_x/(radius-depth)
    angular_gap_lower_candidate = 2*math.pi/count - 2*sector_half
    t = angular_gap_lower_candidate/2
    neighbor_distance_lower_candidate = (
        2*(radius-depth)*(t-t**3/6)-2*collar_correction)
    beta = math.atan2(h, -slope)
    boundary_errors, transition_errors = [], []
    for phi in (0, beta/3, 2*beta/3, beta):
        radial = slope*math.cos(phi)-h*math.sin(phi)
        vertical = h*math.cos(phi)+slope*math.sin(phi)
        for fraction in (-1, -.5, 0, .5, 1):
            s = base/2*fraction
            angle = s/radius
            if slope:
                x = radius/slope*math.sin(slope*angle)
                f_at_x = -2*radius/slope*math.sin(slope*angle/2)**2
            else:
                x, f_at_x = s, 0
            true_base = (radius*math.cos(angle), radius*math.sin(angle), 0)
            rigid_base = (radius+f_at_x*radial, x, f_at_x*vertical)
            correction = tuple(a-b for a, b in zip(true_base, rigid_base))
            # P = G + ((relief-y)/(relief-f(x)))_+ D. At y=f, weight1;
            # at y=relief, weight0. Source is attached; glue above relief rigid.
            for y, errors, target in (
                (f_at_x, boundary_errors, true_base),
                (relief, transition_errors,
                 (radius+relief*radial, x, relief*vertical)),
            ):
                alpha = max(0, (relief-y)/(relief-f_at_x))
                rigid = (radius+y*radial, x, y*vertical)
                mapped = tuple(q+alpha*d for q, d in zip(rigid, correction))
                errors.append(math.dist(mapped, target))
    return {
        "radius_mm": radius, "signed_generator_radial_slope": slope,
        "base_source_arclength_mm": base, "depth_mm": depth,
        "relief_mm": relief, "count": count,
        "source_gap_mm": 2*math.pi*radius/count-base,
        "flat_base_endpoint_xy_mm": [edge_x, edge_y],
        "rigid_glue_triangle_area_mm2": glue_area,
        "radial_F_max_tangential_strain": depth/radius,
        "collar_correction_bound_candidate_mm": collar_correction,
        "collar_differential_strain_bound_candidate": strain_upper_candidate,
        "body_distance_outside_relief_lower_candidate_mm": body_distance_lower_candidate,
        "adjacent_full_phase_distance_lower_candidate_mm": neighbor_distance_lower_candidate,
        "glue_max_vertex_radius_mm": max(
            radius-depth, math.hypot(radius-relief, glue_half_base)),
        "sampled_contiguity_error_mm": max(boundary_errors),
        "sampled_relief_continuity_error_mm": max(transition_errors),
        "proof_status": "EXPLORATORY_UNREVIEWED_NOT_A_CERTIFICATE",
    }


if __name__ == "__main__":
    report = {
        "source_base": "b127fc550fc8401a8f8c8f066ca948e81184b246",
        "scope": "Early math spike; no production module, UI, export or physical proof",
        "cases": [experiment(10, 0), experiment(10, -1/3),
                  experiment(20, 1/3), experiment(10, 1e-9)],
        "negative_evidence": {
            "rigid_G_alone": "Disconnected from true curved base except midpoint",
            "radial_F_depth2_R10": "Tangential shortening up to20%; not elastic-paper proof",
            "collar": "Explicit differential deformation required, not rigid/EXACT",
            "finite_samples": "Continuity samples do not certify whole-domain regularity",
        },
    }
    target = Path(__file__).with_name("checkpoint.json")
    target.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
