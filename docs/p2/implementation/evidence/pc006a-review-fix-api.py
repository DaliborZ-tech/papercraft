"""Independent supplemental C02/C03/C04 and open-profile checks, exact source only."""
import argparse
import copy
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.exporter.author_export import SnapshotError, export_all
import archpapercraft.authoring as imported

assert Path(imported.__file__).resolve().is_relative_to(args.source.resolve())
scratch = Path(tempfile.mkdtemp(prefix="pc006a-review-fix-api-"))
results = []


def check(name, passed, detail=None):
    results.append({"name": name, "pass": bool(passed), "detail": detail})


def rejected_without_change(project, operation):
    before = copy.deepcopy(project.to_dict())
    try:
        operation()
    except ValidationError:
        return project.to_dict() == before
    return False


p = AuthorProject.new(scale=1)
profile_id = p.add_profile([[-4, -3], [53, -3]], closed=False)
vertices = [v.id for v in p.profiles[profile_id].vertices]
first_edge = p.profiles[profile_id].segments[0].id
check("two-point-close-typed-atomic", rejected_without_change(p, lambda: p.close_profile(profile_id)))
for point in ([53, 41], [20, 41], [20, 16]):
    p.append_vertex(profile_id, point)
p.save(scratch / "half-profile.apcraft")
p = AuthorProject.load(scratch / "half-profile.apcraft")
check("open-profile-reopen-retains-source-topology", [v.id for v in p.profiles[profile_id].vertices][:2] == vertices and p.profiles[profile_id].segments[0].id == first_edge)
before_last = [s.id for s in p.profiles[profile_id].segments]
check("duplicate-append-typed-atomic", rejected_without_change(p, lambda: p.append_vertex(profile_id, [20, 16])))
check("infinite-append-typed-atomic", rejected_without_change(p, lambda: p.append_vertex(profile_id, [math.inf, 16])))
p.append_vertex(profile_id, [-4, 16])
all_vertices = [v.id for v in p.profiles[profile_id].vertices]
all_open_edges = [s.id for s in p.profiles[profile_id].segments]
p.close_profile(profile_id)
check("append-close-retains-every-old-vertex-and-segment", [v.id for v in p.profiles[profile_id].vertices] == all_vertices and [s.id for s in p.profiles[profile_id].segments][:-1] == all_open_edges and all_open_edges[:len(before_last)] == before_last)
state = p.to_dict()
p.close_profile(profile_id)
check("already-closed-is-idempotent", p.to_dict() == state)
check("closed-append-typed-atomic", rejected_without_change(p, lambda: p.append_vertex(profile_id, [-4, 0])))
sid = p.add_surface(profile_id)
world = p.world_geometry(sid)
points = np.asarray(world["vertices"])
area = sum(np.linalg.norm(np.cross(points[b] - points[a], points[c] - points[a])) / 2 for a, b, c in world["triangles"])
check("continued-concave-surface-area-independent-1908", abs(area - 1908) < 1e-9, {"actual_mm2": float(area), "analytic_mm2": 57*44-24*25})
crossing = p.add_profile([[0, 0], [30, 0], [0, 20], [30, 20]], closed=False)
check("crossing-closure-typed-atomic", rejected_without_change(p, lambda: p.close_profile(crossing)))

p = AuthorProject.new(scale=1)
outer = p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
hole = p.add_profile([[30, 30], [30.1, 30], [30.1, 32], [30, 32]])
sid = p.add_surface(outer, holes=[hole])
pid = p.part_for_surface(sid)
p.set_placement(pid, page_id=p.pages[0].id, x_mm=20, y_mm=20)
issue = next(i for i in p.validate_layout() if i.code == "SMALL_DETAIL")
p.acknowledge(issue.id)
check("small-hole-warning-can-be-acknowledged", any(i.code == "SMALL_DETAIL" and i.acknowledged for i in p.validate_layout()))
hole_vertices = [v.id for v in p.profiles[hole].vertices]
p.move_vertex(hole, hole_vertices[1], [30.2, 30])
p.move_vertex(hole, hole_vertices[2], [30.2, 32])
p.recompute()
updated = [i for i in p.validate_layout() if i.code == "SMALL_DETAIL"]
check("small-hole-source-edit-invalidates-old-ack", len(updated) == 1 and not updated[0].acknowledged and updated[0].digest != issue.digest, {"old_issue_id": issue.id, "new_issue_id": updated[0].id if updated else None, "old_digest": issue.digest, "new_digest": updated[0].digest if updated else None, "note": "Stable issue identity is valid; acknowledgement is bound to the changed source-state digest."})

p = AuthorProject.new(scale=.01)
outer = p.add_profile([[0, 0], [10000.5, 0], [10000.5, 4000], [0, 4000]])
hole = p.add_profile([[1000, 1000], [2500, 1000], [2500, 2000], [1000, 2000]])
sid = p.add_surface(outer, holes=[hole])
p.set_transform(sid, position_mm=[1e12, -1e12, 1e12], rotation_deg=[0, 0, 0])
world = p.world_geometry(sid)
points = np.asarray(world["vertices"])
area = sum(np.linalg.norm(np.cross(points[b] - points[a], points[c] - points[a])) / 2 for a, b, c in world["triangles"]) * .01**2
check("well-conditioned-world-hole-translation-remains-valid", abs(area - 3850.2) < 1e-8, {"actual_paper_mm2": float(area), "analytic_paper_mm2": (10000.5*4000-1500*1000)*.01**2})

snapshot = {"project_id": "fix-review", "revision": 1, "scale_label": "1:1", "pages": [{"id": "page", "width_mm": 210, "height_mm": 297, "parts": [{"id": "part", "name": "Review", "placement": {"x_mm": 40, "y_mm": 40, "rotation_deg": 0}, "paths": {"CUT": [{"points": [[0, 0], [30, 0], [15, 20]], "closed": True}]}, "labels": []}]}]}
bundle = scratch / "bundle"
export_all(snapshot, bundle)
before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in bundle.iterdir() if f.is_file()}
bad = copy.deepcopy(snapshot)
part = bad["pages"][0]["parts"][0]
offset = 1e8
part["placement"]["x_mm"] = -offset + 40
part["paths"]["CUT"][0]["points"] = [[offset+.237, 0], [offset+30.237, 0], [offset+15.237, 20]]
try:
    export_all(bad, bundle)
    rejected = False
except SnapshotError as exc:
    rejected = "serialization" in str(exc)
after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in bundle.iterdir() if f.is_file()}
check("inaccurate-serialized-pdf-rejected-prior-bundle-identical", rejected and before == after and not list(scratch.glob(".author-export-*")))

result = {"source_sha": args.sha, "source_root": str(args.source), "scratch": str(scratch), "results": results, "pass": sum(r["pass"] for r in results), "fail": sum(not r["pass"] for r in results)}
args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(1 if result["fail"] else 0)
