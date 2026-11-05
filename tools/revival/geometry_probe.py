r"""P0/P1 diagnostic experiments; no production patch and no expected failures hidden.

Run from the repository root:
  .venv\Scripts\python.exe tools/revival/geometry_probe.py
The JSON distinguishes a successfully reproduced defect from a runtime error.
An exit code of zero means the probe ran, NOT that the product is correct.
"""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from archpapercraft.core_geometry.backend import MeshBackend
from archpapercraft.core_geometry.primitives import (
    MeshData, make_box_mesh, make_cylinder_mesh, make_sphere_mesh,
)
from archpapercraft.core_geometry.stable_ids import part_hash
from archpapercraft.paper_analyzer.classifier import classify_surfaces
from archpapercraft.seam_editor.auto_seams import auto_seams
from archpapercraft.seam_editor.seam_graph import SeamGraph
from archpapercraft.tabs_generator.tabs import TabSettings, generate_tab, generate_tabs_for_part
from archpapercraft.unfolder.approx_unfold import unfold_all_parts
from archpapercraft.unfolder.exact_unfold import _compute_dihedral, unfold_part
from archpapercraft.unfolder.strategies import extract_revolution_profile, generate_rings


def mesh(vertices, faces):
    return MeshData(np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int32))


def cross2(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


def signed_area(poly):
    return 0.5 * sum(cross2(a, b) for a, b in zip(poly, np.roll(poly, -1, axis=0)))


def intersection_area(subject, clip):
    """Independent Sutherland-Hodgman convex polygon intersection oracle."""
    output = list(np.asarray(subject, dtype=float))
    clip = np.asarray(clip, dtype=float)
    if signed_area(clip) < 0:
        clip = clip[::-1]
    for a, b in zip(clip, np.roll(clip, -1, axis=0)):
        old, output = output, []
        if not old:
            break
        for p, q in zip(old, old[1:] + old[:1]):
            dp, dq = cross2(b - a, p - a), cross2(b - a, q - a)
            inside_p, inside_q = dp >= -1e-10, dq >= -1e-10
            if inside_p:
                output.append(p)
            if inside_p != inside_q:
                output.append(p + (q - p) * dp / (dp - dq))
    return abs(signed_area(np.array(output))) if len(output) >= 3 else 0.0


def part_metrics(source, part, seam_edges=frozenset()):
    triangles = part.vertices_2d[part.faces]
    area = sum(abs(signed_area(tri)) for tri in triangles)
    edge_occurrences = defaultdict(list)
    lengths = []
    for ids in part.faces:
        for i in range(3):
            ia, ib = int(ids[i]), int(ids[(i + 1) % 3])
            a, b = int(part.vert_map_3d[ia]), int(part.vert_map_3d[ib])
            lengths.append(abs(float(np.linalg.norm(part.vertices_2d[ib] - part.vertices_2d[ia]))
                               - float(np.linalg.norm(source.vertices[b] - source.vertices[a]))))
            key = tuple(sorted((a, b)))
            points = {a: part.vertices_2d[ia], b: part.vertices_2d[ib]}
            edge_occurrences[key].append(points)
    closure = []
    for key, occurrences in edge_occurrences.items():
        if len(occurrences) == 2:
            gap = max(float(np.linalg.norm(occurrences[0][v] - occurrences[1][v])) for v in key)
            if gap > 1e-8:
                closure.append({"edge": list(key), "endpoint_gap": gap, "explicit_seam": key in seam_edges})
    overlaps = []
    for i, a in enumerate(triangles):
        for j in range(i):
            value = intersection_area(a, triangles[j])
            if value > 1e-8:
                overlaps.append({"faces": [j, i], "intersection_area": value})
    return {
        "faces": len(part.faces), "triangle_area_sum": area,
        "max_edge_length_error": max(lengths, default=0.0),
        "fold_edges": len(part.fold_edges), "cut_edges": len(part.cut_edges),
        "noncoincident_shared_source_edges": closure,
        "unmarked_crack_count": sum(not edge["explicit_seam"] for edge in closure),
        "overlapping_triangle_pairs": overlaps,
    }


def panel():
    square = mesh([[0, 0, 0], [20, 0, 0], [20, 10, 0], [0, 10, 0]], [[0, 1, 2], [0, 2, 3]])
    direct = part_metrics(square, unfold_part(square, [0, 1]))
    sg = auto_seams(square, max_part_extent_mm=10000)
    automatic = unfold_all_parts(square, sg)[0]
    boundary = {(0, 1), (1, 2), (2, 3), (0, 3)}
    return {
        "expected": {"area_mm2": 200, "boundary_edges": 4, "internal_cut_diagonals": 0},
        "observed": {"direct_api": direct, "automatic_path": part_metrics(square, automatic, sg.seam_edges),
                     "automatic_boundary_pair_ids": auto_seams(square).compute_edge_match_ids(),
                     "boundary_edges_explicitly_supplied": len(boundary)},
        "status": "DEFECT_REPRODUCED" if direct["cut_edges"] != 4 else "PASS",
        "meaning": "Exact direct API omits physical boundary cuts; auto_seams supplies them. Coplanar triangulation diagonal is still a fold entry.",
    }


def box():
    box_mesh = make_box_mesh(10, 20, 30)
    direct = part_metrics(box_mesh, unfold_part(box_mesh, list(range(12))))
    sg = auto_seams(box_mesh, max_part_extent_mm=10000)
    automatic = [part_metrics(box_mesh, p, sg.seam_edges) for p in unfold_all_parts(box_mesh, sg)]
    return {
        "expected": {"area_mm2": 2200, "faces_covered": 12,
                     "uncut_closed_surface": "reject or introduce explicit seams; non-tree closure cannot be ignored"},
        "observed": {"uncut": direct, "automatic": automatic, "automatic_seam_count": len(sg.seam_edges)},
        "status": "DEFECT_REPRODUCED" if direct["noncoincident_shared_source_edges"] else "PASS",
        "meaning": "Triangle lengths and summed area can be exact while a closed surface has unreported cracks or overlaps.",
    }


def house():
    # Paper mm at 1:100. No floor, zero material thickness, roof meets wall/gable
    # at the same mathematical edges. These semantic fixtures are not an app feature.
    v = [[0, 0, 0], [60, 0, 0], [60, 100, 0], [0, 100, 0],
         [0, 0, 40], [60, 0, 40], [60, 100, 40], [0, 100, 40], [30, 0, 70], [30, 100, 70]]
    panels = {
        "side_left": ([0, 3, 7, 4], 4000.0), "side_right": ([1, 5, 6, 2], 4000.0),
        "front_wall": ([0, 4, 5, 1], 2400.0), "back_wall": ([3, 2, 6, 7], 2400.0),
        "front_gable": ([4, 8, 5], 900.0), "back_gable": ([7, 6, 9], 900.0),
        "roof_left": ([4, 7, 9, 8], 100 * math.sqrt(1800)),
        "roof_right": ([5, 8, 9, 6], 100 * math.sqrt(1800)),
    }
    results = {}
    for name, (indices, area) in panels.items():
        triangles = [[indices[0], indices[i], indices[i+1]] for i in range(1, len(indices)-1)]
        source = mesh(v, triangles)
        seams = {tuple(sorted((indices[i], indices[(i+1) % len(indices)]))) for i in range(len(indices))}
        m = part_metrics(source, unfold_part(source, list(range(len(triangles))), seams))
        m["area_error_mm2"] = abs(m["triangle_area_sum"] - area)
        m["expected_area_mm2"] = area
        results[name] = m
    total_expected = 14600 + 200 * math.sqrt(1800)
    return {
        "expected": {"body_perimeter_mm": 320, "roof_slope_mm": math.sqrt(1800),
                     "ridge_height_mm": 70, "total_area_mm2_without_floor_tabs": total_expected,
                     "faces": 14, "semantic_surfaces": 8},
        "observed": {"panels": results, "total_faces": sum(r["faces"] for r in results.values()),
                     "total_area_mm2": sum(r["triangle_area_sum"] for r in results.values()),
                     "max_edge_error_mm": max(r["max_edge_length_error"] for r in results.values())},
        "status": "PASS" if all(r["area_error_mm2"] <= .01 and r["max_edge_length_error"] <= .01 for r in results.values()) else "DEFECT_REPRODUCED",
        "meaning": "Independent semantic-panel fixture establishes attainable planar tolerances; not a GUI/identity/layout or physical house acceptance.",
    }


def csg():
    source = make_box_mesh(10, 10, 10)
    backend = MeshBackend()
    difference = backend.boolean_difference(source, source)
    intersection = backend.boolean_intersect(source, source)
    union = backend.boolean_union(source, source)
    return {"expected": {"difference_A_A": "empty or explicit unsupported", "union_A_A_faces": 12},
            "observed": {"supports_csg": backend.supports_csg, "difference_same_object": difference is source,
                         "difference_faces": difference.num_faces, "intersection_same_object": intersection is source,
                         "union_faces": union.num_faces},
            "status": "DEFECT_REPRODUCED" if difference.num_faces != 0 or union.num_faces != 12 else "PASS",
            "meaning": "Mesh API returns ordinary geometry despite unsupported CSG; callers must not report success."}


def cylinder():
    outline = generate_rings(np.array([[10., 0.], [10., 30.]]), num_rings=1)[0]
    source = make_cylinder_mesh(10, 30, segments=64)
    profile = extract_revolution_profile(source)
    return {"expected": {"width_mm": 20 * math.pi, "height_mm": 30, "area_mm2": 600 * math.pi},
            "observed": {"direct_analytic_profile_outline": outline.tolist(), "area_mm2": abs(signed_area(outline)),
                         "capped_mesh_extracted_profile": None if profile is None else profile.tolist()},
            "status": "DEFECT_REPRODUCED" if profile is None or abs(float(np.ptp(profile[:, 1])) - 30) > .01 else "PASS",
            "meaning": "Constant-radius ring formula is exact given a correct profile; mesh extraction bins shrink z extent and mix cap-centre radii."}


def cone_band():
    slant = 30.0
    outline = generate_rings(np.array([[10., 0.], [20., math.sqrt(800.)]]), num_rings=1)[0]
    # Similar triangles from cone apex: Rinner=slant*r1/(r2-r1), Router=60.
    # Arc theta*R equals circumference: theta=2*pi/3. A trapezoid can
    # coincidentally preserve area while stretching its joining radial edges.
    actual_sides = [float(np.linalg.norm(outline[1] - outline[2])), float(np.linalg.norm(outline[3] - outline[0]))]
    theta = 2 * math.pi / 3
    theta_samples = np.linspace(0, theta, 1025)
    analytic_prototype = np.vstack([np.column_stack([60*np.cos(theta_samples), 60*np.sin(theta_samples)]),
                                    np.column_stack([30*np.cos(theta_samples[::-1]), 30*np.sin(theta_samples[::-1])])])
    return {"expected": {"inner_radius_mm": 30, "outer_radius_mm": 60, "angle_rad": theta,
                         "joining_sides_mm": [slant, slant], "arcs_mm": [20*math.pi, 40*math.pi], "area_mm2": 900*math.pi},
            "observed": {"trapezoid": outline.tolist(), "joining_sides_mm": actual_sides, "area_mm2": abs(signed_area(outline)),
                         "analytic_sector_spike_samples": len(analytic_prototype),
                         "analytic_sector_polygon_area_mm2": abs(signed_area(analytic_prototype))},
            "status": "DEFECT_REPRODUCED" if max(abs(s-slant) for s in actual_sides) > .01 else "PASS",
            "meaning": "Area-only test misses the defect. Sector polyline is a throwaway illustration, not a production arc representation or exact kernel."}


def sphere():
    source = make_sphere_mesh(10, segments=64, rings=32)
    result = classify_surfaces(source)
    kinds = Counter({name: sum(len(p.face_indices) for p in result.patches if p.kind.name == name)
                     for name in ["FLAT", "DEVELOPABLE", "NON_DEVELOPABLE"]})
    angle_sums = np.zeros(source.num_vertices)
    for tri in source.faces:
        for i in range(3):
            center = source.vertices[tri[i]]
            a = source.vertices[tri[(i+1) % 3]] - center
            b = source.vertices[tri[(i+2) % 3]] - center
            angle_sums[tri[i]] += math.acos(float(np.clip(np.dot(a, b)/np.linalg.norm(a)/np.linalg.norm(b), -1, 1)))
    deficits = 2*math.pi-angle_sums
    return {"expected": {"smooth_gaussian_curvature_per_mm2": .01, "closed_polyhedron_total_angle_defect_rad": 4*math.pi,
                         "continuous_exact_unstrained_development": "impossible; must reject or explicitly approximate/cut into facets"},
            "observed": {"faces": source.num_faces, "patches": len(result.patches), "classified_face_counts": dict(kinds),
                         "total_angle_defect_rad": float(deficits.sum()), "min_vertex_angle_defect_rad": float(deficits.min()),
                         "max_patch_local_dihedral_deg": max(p.max_dihedral_deg for p in result.patches)},
            "status": "DEFECT_REPRODUCED" if kinds["DEVELOPABLE"] > 0 else "PASS",
            "meaning": "Small adjacent-normal angles on a fine triangulated sphere do not establish developability."}


def rigid_revolution():
    source = make_cylinder_mesh(10, 30, segments=64)
    rot = np.array([[1., 0, 0], [0, 0, -1], [0, 1, 0]])
    variants = {"local": source,
                "translated": MeshData(source.vertices + [100., 200., 300.], source.faces),
                "rotated_x_90": MeshData(source.vertices @ rot.T, source.faces),
                "rotated_and_translated": MeshData(source.vertices @ rot.T + [100., 200., 300.], source.faces)}
    output = {}
    reference_unfold = unfold_part(source, [0, 1]).vertices_2d
    for name, variant in variants.items():
        profile = extract_revolution_profile(variant)
        actual = unfold_part(variant, [0, 1]).vertices_2d
        output[name] = {"profile": None if profile is None else profile.tolist(),
                        "exact_triangle_pair_max_delta_mm": float(np.max(np.abs(actual-reference_unfold)))}
    return {"expected": {"local_profile_radius_mm": 10, "local_profile_height_mm": 30,
                         "rigid_invariant": True}, "observed": output,
            "status": "DEFECT_REPRODUCED" if any(v["profile"] is None or v["profile"] != output["local"]["profile"] for v in output.values()) else "PASS",
            "meaning": "Exact triangle distances are rigid invariant; profile extractor assumes global Z axis through origin. Local frame is required."}


def topology_adversaries():
    disconnected = mesh([[0,0,0], [10,0,0], [0,10,0], [20,0,0], [30,0,0], [20,10,0]], [[0,1,2], [3,4,5]])
    nonmanifold = mesh([[0,0,0], [10,0,0], [0,10,0], [0,0,10], [0,-10,0]], [[0,1,2], [1,0,3], [0,1,4]])
    p = unfold_part(disconnected, [0, 1])
    parts = unfold_all_parts(disconnected, SeamGraph(disconnected))
    n = unfold_part(nonmanifold, [0, 1, 2])
    return {"expected": {"disconnected_direct_api": "explicit rejection or complete coverage", "all_parts_faces": 2,
                         "nonmanifold_edge_three_faces": "reject or explicit unsupported"},
            "observed": {"disconnected_direct_faces": len(p.faces), "all_parts_faces": sum(len(p.faces) for p in parts),
                         "nonmanifold": part_metrics(nonmanifold, n)},
            "status": "DEFECT_REPRODUCED" if len(p.faces) != 2 or part_metrics(nonmanifold, n)["overlapping_triangle_pairs"] else "PASS",
            "meaning": "Direct unfold silently drops disconnected faces; wrapper splits them correctly. Non-manifold branching is accepted without validation."}


def tabs_and_polarity():
    square = np.array([[0.,0.], [20.,0.], [20.,20.], [0.,20.]])
    settings = TabSettings()
    forward = generate_tab(square[0], square[1], settings)
    reverse = generate_tab(square[1], square[0], settings)
    tabs_a = generate_tabs_for_part(square, [(0,1)], {(0,1): 1}, settings)
    tabs_b = generate_tabs_for_part(square, [(0,1)], {(0,1): 1}, settings)
    ridge = mesh([[0,0,0], [0,10,0], [-10,0,-10], [10,0,-10]], [[0,1,2], [0,3,1]])
    old_to_new = np.array([1, 0, 2, 3])
    reindexed = MeshData(ridge.vertices[old_to_new], old_to_new[ridge.faces])
    convex = _compute_dihedral(ridge, 0, 1, (0,1))
    convex_reindexed = _compute_dihedral(reindexed, 0, 1, (0,1))
    concave = MeshData(ridge.vertices * [1,1,-1], ridge.faces[:, ::-1])
    valley = _compute_dihedral(concave, 0, 1, (0,1))
    return {"expected": {"tab_material_overlap_area_mm2": 0, "tab_count_on_matched_joint": 1,
                         "ridge_front_outward": "mountain", "interior_corner_front_outward": "valley",
                         "reindexing_changes_polarity": False},
            "observed": {"forward_tab_overlap_mm2": intersection_area(forward.polygon, square),
                         "reverse_tab_overlap_mm2": intersection_area(reverse.polygon, square),
                         "two_separate_parts_tab_count_same_match": len(tabs_a)+len(tabs_b),
                         "ridge_angle_deg": convex, "ridge_reindexed_angle_deg": convex_reindexed,
                         "concave_angle_deg": valley},
            "status": "DEFECT_REPRODUCED" if intersection_area(forward.polygon, square) > .01 or len(tabs_a)+len(tabs_b) != 1 or convex*convex_reindexed < 0 else "PASS",
            "meaning": "Left-of-directed-edge is not necessarily outside material. Local seen_match does not coordinate ownership across parts. Sorted-index direction flips fold polarity."}


def identity_hash_collision():
    square = mesh([[-5,-5,0], [5,-5,0], [5,5,0], [-5,5,0]], [[0,1,2], [0,2,3]])
    rectangle = mesh([[-10,-2.5,0], [10,-2.5,0], [10,2.5,0], [-10,2.5,0]], [[0,1,2], [0,2,3]])
    square_id, rectangle_id = part_hash(square, [0,1]), part_hash(rectangle, [0,1])
    return {"expected": {"different_semantic_parts_share_entity_identity": False,
                         "square_area_mm2": 100, "rectangle_area_mm2": 100},
            "observed": {"square_hash": square_id, "rectangle_hash": rectangle_id,
                         "equal_hashes": square_id == rectangle_id},
            "status": "DEFECT_REPRODUCED" if square_id == rectangle_id else "PASS",
            "meaning": "Centroid+area+triangle count cannot identify an entity or its shape. Entity ID must be persisted independently of geometry."}


def oracle_self_check():
    unit = np.array([[0.,0.], [1.,0.], [1.,1.], [0.,1.]])
    assert abs(intersection_area(unit, unit)-1) < 1e-10
    assert abs(intersection_area(unit, unit + [1.,0.])) < 1e-10
    assert abs(intersection_area(unit, unit + [.5,0.])-.5) < 1e-10
    assert abs(intersection_area(unit[::-1], unit)-1) < 1e-10


def main():
    started = time.perf_counter()
    oracle_self_check()
    results = {}
    errors = 0
    for fn in [panel, box, house, csg, cylinder, cone_band, sphere, rigid_revolution,
               topology_adversaries, tabs_and_polarity, identity_hash_collision]:
        try:
            results[fn.__name__] = fn()
        except Exception as error:
            errors += 1
            results[fn.__name__] = {"status": "ERROR", "exception": repr(error)}
        print(f"{fn.__name__}: {results[fn.__name__]['status']}")
    # JSON keys must be strings; preserve seam-ID tuples in an explicit display map.
    ids = results.get("panel", {}).get("observed", {}).get("automatic_boundary_pair_ids")
    if ids is not None:
        results["panel"]["observed"]["automatic_boundary_pair_ids"] = {str(k): v for k,v in ids.items()}
    report = {"baseline_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
              "command": subprocess.list2cmdline([sys.executable, *sys.argv]),
              "elapsed_seconds": time.perf_counter()-started, "oracle_self_checks": "PASS (4 analytic intersection cases)",
              "runtime_errors": errors, "results": results}
    destination = ROOT / "docs/revival/evidence/geometry-results.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(f"Evidence: {destination}; runtime_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
