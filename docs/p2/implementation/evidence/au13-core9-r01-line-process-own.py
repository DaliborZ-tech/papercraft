"""Standalone LINE replay: deliberately no pytest/conftest import rewriting."""

import argparse
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring import project as project_module
from archpapercraft.authoring.project import ProjectFormatError

parser = argparse.ArgumentParser()
parser.add_argument("--source-pin", required=True)
parser.add_argument("--expect", choices=("accepted", "rejected"), required=True)
args = parser.parse_args()
root = Path.cwd().resolve()
assert Path(project_module.__file__).resolve() == root / "src/archpapercraft/authoring/project.py"
blob_hashes = {}
for name in ("project.py", "profile_subdivision.py", "model.py"):
    path = "src/archpapercraft/authoring/" + name
    raw = (root / path).read_bytes().replace(b"\r\n", b"\n")
    expected = subprocess.check_output(["git", "show", args.source_pin + ":" + path])
    assert raw == expected.replace(b"\r\n", b"\n")
    blob_hashes[path] = hashlib.sha256(raw).hexdigest()
results = {}
for retired in ("root", "left", "right"):
    p = AuthorProject.new(scale=0.1)
    pid = p.add_profile([[0, 0], [12, 0]], closed=False)
    source = p.profiles[pid].segments[0].id
    cut = p.split_profile_segment(pid, source, Fraction(1, 3))
    p.merge_profile_segments(pid, cut["segment_ids"])
    raw = p.to_dict()
    segment = raw["profiles"][pid]["segments"][0]
    assert segment["source_reference"] is None
    segment["id"] = dict(root=source, left=cut["segment_ids"][0],
                         right=cut["segment_ids"][1])[retired]
    try:
        AuthorProject.from_dict(raw)
    except ProjectFormatError:
        result = "rejected"
    else:
        result = "accepted"
    results[retired] = result
    assert result == args.expect, (retired, result, args.expect)
print(json.dumps(dict(
    source_pin=args.source_pin,
    actual_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    imported_project=project_module.__file__,
    worktree=str(root),
    source_blobs_lf_sha256=blob_hashes,
    results=results,
    pytest="not loaded; standalone Python process",
), indent=2))
