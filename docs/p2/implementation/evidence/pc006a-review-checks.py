"""Independent component oracles; these are not a novice or desktop UI test."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))

import numpy as np
from pypdf import PdfReader
from pypdf.generic import ContentStream

import archpapercraft.authoring as domain
from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.geometry import page_points
from archpapercraft.exporter import author_export as exporter

assert Path(domain.__file__).resolve().is_relative_to((args.source / "src").resolve())
checks, facts = [], {}
started = time.perf_counter()
scratch = Path(tempfile.mkdtemp(prefix="pc006a-review-oracles-"))


def record(name, passed, observed=None):
    checks.append({"name": name, "pass": bool(passed), "observed": observed})


def area(points):
    points = np.asarray(points, float)
    points = points - points[0]
    return float(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(points, np.roll(points, -1, 0))) / 2)


def blocked(function):
    try:
        function()
    except ValidationError as error:
        return {"blocked": True, "type": type(error).__name__, "message": str(error)}
    except Exception as error:
        return {"blocked": False, "unexpected_type": type(error).__name__, "message": str(error)}
    return {"blocked": False}


def rectangle(project, x=0, y=0, width=129, height=87, name="Vlastní příčná stěna"):
    profile = project.add_profile(
        [[x, y], [x + width, y], [x + width, y + height], [x, y + height]], name=name
    )
    return profile, project.add_surface(profile, name=name)


def joined():
    project = AuthorProject.new(scale=0.1)
    pa, a = rectangle(project, width=1290, height=870)
    pb, b = rectangle(project, x=1290, width=790, height=870)
    edge_a, edge_b = project.profiles[pa].segments[1].id, project.profiles[pb].segments[3].id
    joint = project.connect_edges(a, edge_a, b, edge_b)
    return project, pa, pb, a, b, joint


def tree_points(part, placement):
    return {sid: page_points(loops[0], placement) for sid, loops in part.polygons.items()}


def pdf_strokes(page):
    # Parse PDF operators without using the writer's coordinate helper.
    matrix, stack, current, strokes = np.eye(3), [], [], []
    height = float(page.mediabox.height)
    for operands, op in ContentStream(page.get_contents(), page.pdf).operations:
        if op == b"q":
            stack.append(matrix.copy())
        elif op == b"Q":
            matrix = stack.pop()
        elif op == b"cm":
            a, b, c, d, e, f = map(float, operands)
            matrix = matrix @ np.array([[a, c, e], [b, d, f], [0, 0, 1]])
        elif op == b"m":
            current = [matrix @ [float(operands[0]), float(operands[1]), 1]]
        elif op == b"l":
            current.append(matrix @ [float(operands[0]), float(operands[1]), 1])
        elif op in (b"S", b"s", b"B", b"B*", b"b", b"b*"):
            strokes.append(np.array([[p[0] * 25.4 / 72, (height - p[1]) * 25.4 / 72] for p in current]))
            current = []
        elif op in (b"f", b"f*", b"n"):
            current = []
    return strokes


# A different oracle from the implementation's author tests: two unequal holes.
p = AuthorProject.new(scale=0.5)
outer, sid = rectangle(p)
holes = [
    p.add_profile([[10, 10], [23, 10], [23, 27], [10, 27]]),
    p.add_profile([[70, 50], [89, 50], [89, 61], [70, 61]]),
]
for hole in holes:
    p.add_hole(sid, hole)
p.recompute()
world = p.world_geometry(sid)
vertices = np.array(world["vertices"])
triangle_area = sum(abs(area(vertices[face, :2])) for face in world["triangles"])
record("two_holes_analytic_model_area", abs(triangle_area - 10793) < 1e-7, triangle_area)
pid = p.part_for_surface(sid)
loops = p.parts[pid].polygons[sid]
paper_area = abs(area(loops[0])) - sum(abs(area(h)) for h in loops[1:])
record("two_holes_scaled_paper_area", abs(paper_area - 2698.25) < 1e-8, paper_area)

unchanged = p.to_dict()
bad_hole = p.add_profile([[0, 10], [5, 10], [5, 20], [0, 20]])
before = p.to_dict()
result = blocked(lambda: p.add_hole(sid, bad_hole))
record("touching_hole_rejected_transactionally", result["blocked"] and p.to_dict() == before, result)

q = AuthorProject.new(scale=1)
contour = q.add_profile([[0, 0], [130, 0], [130, 90], [85, 90], [85, 35], [0, 35]])
hole = q.add_profile([[100, 10], [113, 10], [113, 27], [100, 27]])
surface = q.add_surface(contour, [hole])
geometry = q.world_geometry(surface)
verts = np.array(geometry["vertices"])
record("different_concave_cutout_area", abs(sum(abs(area(verts[f, :2])) for f in geometry["triangles"]) - 6804) < 1e-7)

translated = AuthorProject.new(scale=1)
_, translated_sid = rectangle(translated, x=-1e11, y=1e12)
translated_world = translated.world_geometry(translated_sid)
tri_verts = np.array(translated_world["vertices"])
translated_area = sum(abs(area(tri_verts[f, :2])) for f in translated_world["triangles"])
record("large_translated_origin_retains_winding_area", translated_area == 11223 and translated_world["normal"] == [0, 0, 1], translated_area)

# Original historical precision condition re-applied on a different polygon.
before = q.to_dict()
result = blocked(lambda: q.set_transform(surface, [1e22, -1e22, 0]))
record("lost_world_metric_rejected_without_mutation", result["blocked"] and q.to_dict() == before, result)

# Owner-only, parameter-only changes and C-01 reproduction on the pinned source.
owner_results = []
for parameter in ({"width_mm": 7}, {"taper": 0.35}, {"shape": "triangle"}):
    model, _, _, a, b, j = joined()
    model.set_tab(j, owner=b)
    connector_id = model.joints[j].connector_id
    model.set_tab(j, **parameter)
    connector = model.connectors[connector_id]
    owner_results.append({"parameter": parameter, "owner_stayed_B": connector.owner_surface_id == b, "connector_id_stable": model.joints[j].connector_id == connector_id})
record("C01_parameter_edit_preserves_B_owner", all(x["owner_stayed_B"] and x["connector_id_stable"] for x in owner_results), owner_results)

# Nonright dihedral, declared front side, shared-part frame and split lineage.
model = AuthorProject.new(scale=0.1)
pa, a = rectangle(model, width=1290, height=870)
pb, b = rectangle(model, width=1290, height=430)
j = model.place_and_connect_edges(a, model.profiles[pa].segments[0].id, b, model.profiles[pb].segments[0].id, angle_deg=37.5, mode="fold")
root = model.part_for_surface(a)
record("nonright_convex_fold_mark", len(model.parts[root].paths["FOLD_MOUNTAIN"]) == 1)
model.set_front_side(root, "inside")
record("inside_print_side_swaps_fold_mark", len(model.parts[root].paths["FOLD_VALLEY"]) == 1)
second_page = model.add_page()
model.set_placement(root, second_page, 60, 60, 30, position_locked=True, rotation_locked=True)
root_before = tree_points(model.parts[root], model.placements[root])
frame_before = copy.deepcopy(model.parts[root].frame)
cache_before = copy.deepcopy(model.parts[root].polygons)
model.move_vertex(pb, model.profiles[pb].vertices[2].id, [1290, 490])
record("whole_folded_part_stale_with_previous_geometry", model.parts[root].stale and model.parts[root].polygons == cache_before)
destination = scratch / "stale.apcraft"
model.save(destination)
loaded = load_project(destination)
record("stale_save_reopen_preserves_cache_frame_locks", loaded.to_dict() == model.to_dict() and loaded.parts[root].frame == frame_before and loaded.placements[root].position_locked and loaded.placements[root].rotation_locked)
stale_result = blocked(loaded.snapshot)
record("stale_export_blocks", stale_result["blocked"], stale_result)
loaded.recompute()
root_after = tree_points(loaded.parts[root], loaded.placements[root])
drift = float(np.max(abs(root_before[a] - root_after[a])))
record("all_unchanged_root_points_keep_rotated_page_position", drift < 1e-9, drift)
before_split = tree_points(loaded.parts[root], loaded.placements[root])
loaded.set_joint(j, mode="cut")
drifts = [float(np.max(abs(tree_points(loaded.parts[loaded.part_for_surface(s)], loaded.placements[loaded.part_for_surface(s)])[s] - before_split[s]))) for s in (a, b)]
record("cut_split_keeps_both_world_page_regions_and_locks", max(drifts) < 1e-9 and all(loaded.placements[loaded.part_for_surface(s)].position_locked and loaded.placements[loaded.part_for_surface(s)].rotation_locked for s in (a, b)), drifts)

# A second part entirely inside a real hole must not create a material collision.
model = AuthorProject.new(scale=1)
outer, s1 = rectangle(model, width=100, height=100)
hole = model.add_profile([[20, 20], [40, 20], [40, 50], [20, 50]])
model.add_hole(s1, hole)
model.recompute()
_, s2 = rectangle(model, width=10, height=10)
model.set_placement(model.part_for_surface(s1), model.pages[0].id, 20, 20)
model.set_placement(model.part_for_surface(s2), model.pages[0].id, 45, 45)
record("hole_material_is_void_for_layout_collision", not any(i.code == "MATERIAL_OVERLAP" for i in model.issues))
snapshot = model.snapshot()
original = copy.deepcopy(model.to_dict())
snap_before = copy.deepcopy(snapshot)
model.parts.pop(model.part_for_surface(s2))
coverage_result = blocked(model.snapshot)
record("missing_runtime_projection_cannot_hide_authoritative_surface", coverage_result["blocked"], coverage_result)
model = AuthorProject.from_dict(original)
pid = model.part_for_surface(s1)
model.parts[pid].paths["CUT"][0]["points"][0][0] += 1
record("tampered_cut_path_blocks_snapshot", blocked(model.snapshot)["blocked"])

# IO and actual on-disk rollback using a valid current source document.
model = AuthorProject.from_dict(original)
path = scratch / "rollback.apcraft"
model.save(path)
old = path.read_bytes()
with patch("archpapercraft.authoring.project.os.replace", side_effect=OSError("review fault")):
    try:
        model.save(path)
    except OSError:
        pass
record("atomic_save_failure_preserves_original_bytes", path.read_bytes() == old and not list(scratch.glob(".rollback.apcraft.*.tmp")))
for payload in ('{"application":1,"application":2}', '{"value":NaN}'):
    path.write_text(payload, encoding="utf-8")
    record("strict_json_reject_" + str(len(checks)), blocked(lambda: load_project(path))["blocked"])

# Export from the real authoring snapshot, with a rotation and true hole.
model = AuthorProject.new(scale=0.5)
outer, sid = rectangle(model, width=129, height=87, name="Žluťoučká vlastní stěna")
hole = model.add_profile([[10, 10], [23, 10], [23, 27], [10, 27]])
model.add_hole(sid, hole)
model.recompute()
pid = model.part_for_surface(sid)
model.set_placement(pid, model.pages[0].id, 60, 50, 30)
export_snapshot = model.snapshot()
export_dir = scratch / "export"
files = exporter.export_all(export_snapshot, export_dir)
record("export_does_not_mutate_snapshot", export_snapshot == model.snapshot())
svg = ET.parse(files[0]).getroot()
ns = {"s": "http://www.w3.org/2000/svg"}
part = svg.find(f"s:g[@id='part-{pid}']", ns)
record("svg_part_group_and_all_roles", part is not None and {g.attrib.get("data-role") for g in part.findall("s:g", ns)} == {"CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "LABELS", "ARTWORK", "GUIDES"})
record("svg_true_hole_has_own_cut_loop", len(part.findall("s:g[@data-role='CUT']/s:path", ns)) == 2)
pdf = PdfReader(files[-1])
record("pdf_a4_vector_unicode", abs(float(pdf.pages[0].mediabox.width) * 25.4 / 72 - 210) < 1e-4 and "Žluťoučká vlastní stěna" in pdf.pages[0].extract_text() and not pdf.pages[0]["/Resources"].get("/XObject"))
strokes = pdf_strokes(pdf.pages[0])
angle = math.pi / 6
rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
expected_loops = [np.asarray(loop["points"]) @ rotation.T + [60, 50] for loop in export_snapshot["pages"][0]["parts"][0]["paths"]["CUT"]]
distances = []
for expected in expected_loops:
    distances.append(min(float(np.max(abs(expected - path))) for path in strokes if path.shape == expected.shape))
record("pdf_cut_hole_positions_match_independent_rotation", max(distances) < 0.0002, distances)
calibration = [line for line in strokes if line.shape == (2, 2) and np.linalg.norm(line[1] - line[0]) > 99]
record("pdf_100mm_calibration", any(abs(float(np.linalg.norm(line[1] - line[0])) - 100) < 0.0001 for line in calibration))
before_files = {file.name: file.read_bytes() for file in export_dir.iterdir() if file.is_file()}
try:
    exporter.export_all(export_snapshot, export_dir, font_path=scratch / "missing-font.ttf")
except exporter.FontError:
    pass
record("font_failure_preserves_prior_bundle", before_files == {file.name: file.read_bytes() for file in export_dir.iterdir() if file.is_file()})
bad_snapshot = copy.deepcopy(export_snapshot)
bad_snapshot["pages"][0]["parts"] = []
try:
    exporter.export_all(bad_snapshot, scratch / "bad-export")
except exporter.SnapshotError:
    omitted_blocked = True
else:
    omitted_blocked = False
record("export_writer_rejects_missing_covered_part", omitted_blocked)
record("repeat_snapshot_stable_digest", exporter.canonical_digest(export_snapshot) == exporter.canonical_digest(copy.deepcopy(export_snapshot)))

facts.update(
    source_sha=args.sha,
    source_root=str(args.source),
    module_file=domain.__file__,
    scratch=str(scratch),
    elapsed_seconds=time.perf_counter() - started,
    classification="independent component math/IO/export checks; no desktop or novice proof",
    checks=checks,
    pass_count=sum(c["pass"] for c in checks),
    fail_count=sum(not c["pass"] for c in checks),
    source_files_sha256={str(p.relative_to(args.source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.source / "src/archpapercraft/authoring").glob("*.py")},
)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"pass": facts["pass_count"], "fail": facts["fail_count"], "scratch": str(scratch)}))
raise SystemExit(0 if facts["fail_count"] == 0 else 1)
