"""A hole boundary is a supported manufacturing detail, not only the outer loop."""

import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from archpapercraft.authoring import AuthorProject

rows = []
for width, height in ((0.1, 0.2), (0.49, 3.0), (0.5, 3.0), (0.6, 3.0)):
    p = AuthorProject.new(scale=1)
    outer = p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    hole = p.add_profile([[30, 30], [30 + width, 30], [30 + width, 30 + height], [30, 30 + height]])
    sid = p.add_surface(outer, [hole])
    p.set_placement(p.part_for_surface(sid), p.pages[0].id, 20, 20)
    codes = [i.code for i in p.issues]
    expected = min(width, height) < 0.5
    rows.append({"hole_width_mm": width, "hole_height_mm": height, "issue_codes": codes, "expected_small_detail": expected, "pass": ("SMALL_DETAIL" in codes) == expected})
result = {"source_sha": args.sha, "scope": "supported line-profile hole boundary; not advanced thin-web or material simulation", "results": rows, "pass": all(row["pass"] for row in rows)}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
raise SystemExit(0 if result["pass"] else 1)
