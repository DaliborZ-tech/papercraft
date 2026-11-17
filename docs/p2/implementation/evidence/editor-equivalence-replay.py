"""Replay recorded native editor path strings; never launches an editor."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "replay_editor_probe", ROOT / "tools/authoring/editor_probe.py"
    )
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    fixture = EVIDENCE / "editor-near-failed-5283632-paths.json"
    original_failure = EVIDENCE / "editor-near-original-failure.json"
    recorded = json.loads(fixture.read_text("utf-8"))
    started = time.perf_counter()
    proofs, totals = {}, {}
    for path in recorded["paths"]:
        proof = probe._same_path(path["before"], path["after"], output=proofs, identity=path["id"])
        role = path["id"].rsplit("-", 2)[1]
        total = totals.setdefault(role, {"length": Fraction(0), "area": Fraction(0)})
        total["length"] += Fraction(proof["global_length_difference_bound_mm_exact"])
        total["area"] += Fraction(proof["net_area_difference_bound_mm2_exact"])
    assert all(
        t["length"] <= Fraction(1, 100) and t["area"] <= Fraction(1, 100) for t in totals.values()
    )
    files = [
        ROOT / "tools/authoring/editor_curve_equivalence.py",
        ROOT / "tools/authoring/editor_probe.py",
        ROOT / "tests/authoring/test_editor_curve_equivalence.py",
        Path(__file__),
        fixture,
        original_failure,
    ]
    result = {
        "status": "RECORDED_PATH_REPLAY_PASS_NOT_NEW_NATIVE_EDITOR_RUN",
        "base_sha": "52836321810f7a8a0c6a8d43b801f98ed875bbde",
        "runtime_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "runtime_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ),
        "exact_source_content_sha256": {str(p.relative_to(ROOT)): digest(p) for p in files},
        "origin_recorded_svg_sha256": recorded["origin_files"],
        "path_count": len(proofs),
        "elapsed_seconds": time.perf_counter() - started,
        "part_role_totals_exact": {
            key: {k: str(v) for k, v in value.items()} for key, value in totals.items()
        },
        "linear_frames": [
            probe._equivalence_module().certify_linear_frame(p["before"], p["after"])
            for p in recorded["frames"]
        ],
        "physical_page_unchanged": all(a == b for a, b in recorded["physical_page"].values()),
        "curve_proofs": proofs,
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k in ("status", "path_count", "elapsed_seconds", "part_role_totals_exact")
            }
        )
    )


if __name__ == "__main__":
    main()
