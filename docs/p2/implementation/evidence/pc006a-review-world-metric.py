"""Independent world-area and material-hole precision contract checks."""

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from archpapercraft.authoring import AuthorProject, ValidationError

rows = []
for kind, offset, with_hole in (("local", 1e12, False), ("local", 1e16, False), ("parent", 1e16, False), ("plane", 1e16, False), ("local", 1e16, True)):
    p = AuthorProject.new(scale=.01)
    width = 10000.0 if with_hole else 10000.5
    plane = {"origin": [offset, offset, 0], "u": [1, 0, 0], "v": [0, 1, 0]} if kind == "plane" else "XY"
    profile = p.add_profile([[0, 0], [width, 0], [width, 4000], [0, 4000]], plane=plane)
    holes = []
    if with_hole:
        holes = [p.add_profile([[300, 300], [300.5, 300], [300.5, 800], [300, 800]])]
    sid = None
    if kind != "plane":
        sid = p.add_surface(profile, holes)
    before = p.to_dict()
    accepted, error, world = False, None, None
    try:
        if kind == "plane":
            sid = p.add_surface(profile)
        elif kind == "parent":
            p.set_transform(sid, parent_transforms=[[[1, 0, 0, offset], [0, 1, 0, offset], [0, 0, 1, 0], [0, 0, 0, 1]]])
        else:
            p.set_transform(sid, [offset, offset, 0])
        accepted = True
        world = p.world_geometry(sid)
    except ValidationError as exc:
        error = str(exc)
    area = None
    expected = width * 4000 * .0001 - (250 * .0001 if with_hole else 0)
    if world is not None:
        vertices = np.array(world["vertices"])
        area = float(sum(np.linalg.norm(np.cross(vertices[t[1]] - vertices[t[0]], vertices[t[2]] - vertices[t[0]])) / 2 for t in world["triangles"]) * .0001)
    tolerance = max(.01, 1e-6 * expected)
    passed = (accepted and area is not None and abs(area - expected) <= tolerance) or (not accepted and before == p.to_dict())
    # The well-conditioned reference must succeed, not be rejected indiscriminately.
    if offset == 1e12:
        passed &= accepted and error is None
    rows.append({"kind": kind, "offset_mm": offset, "with_hole": with_hole, "command_accepted": accepted, "post_command_world_error": error, "actual_world_area_paper_mm2": area, "analytic_source_area_paper_mm2": expected, "area_tolerance_mm2": tolerance, "rolled_back_if_rejected": before == p.to_dict() if not accepted else None, "pass": bool(passed)})
result = {"source_sha": args.sha, "results": rows, "pass": all(row["pass"] for row in rows)}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
raise SystemExit(0 if result["pass"] else 1)
