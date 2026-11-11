"""Pinned backend fixture proof; this never claims an actual UI/user/physical run."""

import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "authoring"))

from test_circular_material_integration import constructed  # noqa: E402
from test_loft_export import assert_actual_reports  # noqa: E402

import archpapercraft  # noqa: E402
from archpapercraft.authoring import load_project  # noqa: E402
from archpapercraft.exporter.author_export import export_all  # noqa: E402


def dump(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8"
    )


def main():
    target = Path(sys.argv[1]).resolve()
    target.mkdir(parents=True, exist_ok=False)
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    module_path = Path(archpapercraft.__file__).resolve()
    if not module_path.is_relative_to(ROOT / "src"):
        raise RuntimeError("Proof imported a different checkout")
    results = {
        "source_sha": source_sha,
        "module_path": str(module_path),
        "python": platform.python_version(),
        "proof_kind": "BACKEND_REAL_DOMAIN_SAVE_REOPEN_ACTUAL_SVG_PDF_NOT_UI",
        "independent_review": "PENDING",
        "new_user_test": "NOT_RUN",
        "physical_build": "NOT_VERIFIED",
        "historical_pdf_failure": {
            "description": "Default MediaBox A4 rounding before the local precise-page fix",
            "actual_pdf_uniform_position_mm": 1.2777777743478062e-5,
            "actual_pdf_whole_cut_length_error_mm": 4.3388807972319406e-14,
            "required_tab_publication_budget_mm": 1e-6,
            "status": "CORRECTLY_BLOCKED_BEFORE_FIX; ACTUAL_FAILURE_NOT_A_PASS",
        },
        "cases": [],
    }
    for name, side, r1, height in [
        ("cylinder-first", "first", 10, 30),
        ("cone-first", "first", 20, math.sqrt(800)),
        ("cone-second", "second", 20, math.sqrt(800)),
        ("near-cylinder-first", "first", 10.000001, 30),
    ]:
        started = time.perf_counter()
        folder = target / name
        folder.mkdir()
        project, sid, pid, cid = constructed(side=side, r1=r1, height=height)
        path = folder / "authored.apcraft"
        project.save(path)
        original_bytes = path.read_bytes()
        reopened = load_project(path)
        if reopened.to_dict() != project.to_dict():
            raise AssertionError("Save/reopen changed the authored model")
        snapshot = reopened.snapshot()
        dump(folder / "snapshot.json", snapshot)
        export_all(snapshot, folder / "vectors")
        report = assert_actual_reports(folder / "vectors", sid, pid)
        material = snapshot["construction_checks"]["lofts"][sid]["curved_material"]
        # Independent analytic Green integral of each pure reference triangle.
        native_rim = reopened.circular_rim(sid, side)
        radius = float(Fraction(native_rim["radius_exact"]))
        k = float(Fraction(native_rim["native_radial_slope_exact"]))
        b, depth = 0.24, 9.5
        if k == 0:
            triangle = b * depth / 2
        else:
            q = k * b / (4 * radius)
            x = b / 2 / (1 + q * q)
            center = -radius / k
            triangle = abs(
                (-center * 2 * x + (radius / k) ** 2 * (-4 * math.atan(q)) + 2 * x * depth) / 2
            )
        expected = math.pi * (10 + r1) * math.hypot(r1 - 10, height) + 12 * triangle
        for output in report["outputs"].values():
            actual = sum(map(Fraction, output["area_exact"])) / 2
            if abs(float(actual) - expected) > 0.01:
                raise AssertionError("Actual output violated the independent analytic area")
        boxes = [
            [token.decode("ascii") for token in match.split()]
            for match in re.findall(
                rb"/MediaBox\s*\[([^]]+)\]", (folder / "vectors" / "model.pdf").read_bytes()
            )
        ]
        if path.read_bytes() != original_bytes:
            raise AssertionError("The old source file was overwritten during publication")
        results["cases"].append(
            {
                "name": name,
                "status": "PASS_IN_BACKEND_SCOPE",
                "surface_id": sid,
                "part_id": pid,
                "connector_id": cid,
                "side": side,
                "tab_ids": reopened.curved_connectors[cid].slot_ids,
                "source_frames_and_layout_preserved": reopened.placements == project.placements,
                "paper_contract": snapshot["construction_checks"]["lofts"][sid]["paper_contract"],
                "independent_expected_material_area_mm2": expected,
                "canonical_material_digest": material["canonical_material_digest"],
                "body_only_area_budget_exact": material["allowed_body_area_error_exact"],
                "native_area_error_exact": material["source_to_actual_area_error_exact"],
                "actual_pdf_media_boxes_original_tokens": boxes,
                "actual_output_checks": report["outputs"],
                "duration_seconds": time.perf_counter() - started,
            }
        )
    results["files"] = {
        str(path.relative_to(target)): {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in target.rglob("*")
        if path.is_file()
    }
    dump(target / "results.json", results)
    print(
        json.dumps(
            {
                "source_sha": source_sha,
                "cases": len(results["cases"]),
                "status": "PASS_IN_BACKEND_SCOPE",
                "target": str(target),
            }
        )
    )


if __name__ == "__main__":
    main()
