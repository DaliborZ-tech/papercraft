"""Independent actual-writer authority replay in an isolated Python process."""

import argparse
import copy
import hashlib
import json
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring import project as project_module
from archpapercraft.authoring.loft_surface import _bound_analysis
from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.curve_output_validation import CurveOutputError

parser = argparse.ArgumentParser()
parser.add_argument("--source-pin", required=True)
parser.add_argument("--expect", choices=("accepted", "rejected"), required=True)
args = parser.parse_args()
root = Path.cwd().resolve()
assert Path(project_module.__file__).resolve() == root / "src/archpapercraft/authoring/project.py"
blob_hashes = {}
for name in ("project.py", "profile_subdivision.py", "loft_surface.py"):
    path = "src/archpapercraft/authoring/" + name
    raw = (root / path).read_bytes().replace(b"\r\n", b"\n")
    expected = subprocess.check_output(["git", "show", args.source_pin + ":" + path])
    assert raw == expected.replace(b"\r\n", b"\n")
    blob_hashes[path] = hashlib.sha256(raw).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def files(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}


def make_project(mode):
    p = AuthorProject.new(scale=0.1)
    ids = []
    for z in (0, 10):
        plane = dict(origin=[0, 0, z], u=[1, 0, 0], v=[0, 1, 0])
        pid = p.add_profile(segments=[dict(kind="cubic", start=[0, 0], end=[4, 0],
            data=dict(control1=[0, 4], control2=[4, 4]))], closed=False, plane=plane)
        if mode != "legacy":
            cut = p.split_profile_segment(pid, p.profiles[pid].segments[0].id, Fraction(2, 7))
            p.merge_profile_segments(pid, cut["segment_ids"])
        if mode == "orphan":
            p.update_profile(pid, [[0, 0], [4, 0]], closed=False)
        ids.append(pid)
    a, b = ids
    sid = p.add_loft(a, b, correspondences=[dict(
        first_segment_id=p.profiles[a].segments[0].id,
        second_segment_id=p.profiles[b].segments[0].id)])
    p.set_placement(p.part_for_surface(sid), p.pages[0].id, 60, 70, 23,
                    position_locked=True, rotation_locked=True)
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    return p, sid


results = {}
with tempfile.TemporaryDirectory(prefix="core9-independent-writer-") as temp:
    for mode in ("legacy", "orphan", "qualified"):
        p, sid = make_project(mode)
        snapshot = p.snapshot()
        directory = Path(temp) / mode
        export_all(snapshot, directory)
        assert (directory / "model.pdf").is_file()
        assert list(directory.glob("page-*.svg"))
        results[mode] = "genuine SVG/PDF accepted"
        if mode != "qualified":
            continue
        project_before = p.to_dict()
        for omission in ("empty", "missing"):
            forged = copy.deepcopy(snapshot)
            report = forged["construction_checks"]["lofts"][sid]
            binding = report["source_binding"]
            assert binding["profile_subdivisions"]
            if omission == "empty":
                binding["profile_subdivisions"] = {}
            else:
                del binding["profile_subdivisions"]
            intrinsic = dict(profiles=binding["profiles"],
                             params=binding["surface"]["params"], scale=binding["scale"])
            report["intrinsic_source_digest"] = digest(intrinsic)
            report["source_digest"] = digest(dict(
                intrinsic_source_digest=report["intrinsic_source_digest"], surface=binding["surface"]))
            # This constructs an internally consistent adversarial claim. The
            # source analyzer is setup, never the oracle for writer permission.
            result = _bound_analysis(json.dumps(intrinsic, sort_keys=True),
                                     json.dumps(binding["surface"], sort_keys=True))
            assert result["status"] == "EXACT"
            report["representation"] = copy.deepcopy(result["representation"])
            output = Path(temp) / omission
            export_all(snapshot, output)
            (output / "unrelated.txt").write_text("Do not overwrite unrelated work.", encoding="utf-8")
            before = files(output)
            try:
                export_all(forged, output)
            except (CurveOutputError, ValueError) as exc:
                observed = "rejected"
                assert files(output) == before
                error = str(exc)
            else:
                observed, error = "accepted", None
                assert (output / "model.pdf").is_file()
            assert observed == args.expect, (omission, observed, args.expect, error)
            assert p.to_dict() == project_before
            results[omission] = dict(observed=observed, error=error,
                                    previous_bundle_preserved=files(output) == before)
print(json.dumps(dict(
    source_pin=args.source_pin,
    actual_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    imported_project=project_module.__file__, worktree=str(root),
    source_blobs_lf_sha256=blob_hashes, results=results,
    pytest="not loaded; standalone Python process", desktop="NOT_RUN",
), indent=2))
