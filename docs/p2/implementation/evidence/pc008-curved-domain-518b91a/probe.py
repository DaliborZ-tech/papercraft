"""Reproducible public-backend bridge evidence; never a native UI/P3 proof."""

import hashlib
import json
import os
import runpy
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
import archpapercraft.authoring.segmented_surface as imported  # noqa: E402
from archpapercraft.authoring import load_project  # noqa: E402


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(exist_ok=False)
    harness = runpy.run_path(str(ROOT / "tests/authoring/test_segmented_surface_curves.py"))
    times = {}
    start = time.perf_counter()
    p, target, a, b = harness["gothic_target"]()
    times["create_target_s"] = time.perf_counter() - start
    start = time.perf_counter()
    preview = p.preview_segmented_variant(target)
    assert preview["can_confirm"], preview
    times["preview_cold_s"] = time.perf_counter() - start
    start = time.perf_counter()
    variant = p.add_segmented_variant(target, preview_digest=preview["preview_digest"])
    times["confirm_warm_s"] = time.perf_counter() - start
    start = time.perf_counter()
    p.add_page()
    p.set_placements(
        {
            row["part_id"]: {
                "page_id": p.pages[i // 48].id,
                "x_mm": 25 + i % 8 * 20,
                "y_mm": 25 + (i // 8) % 6 * 24,
                "rotation_deg": 0,
                "position_locked": i == 0,
                "rotation_locked": i == 0,
            }
            for i, row in enumerate(p.segmented_variants[variant].triangle_bindings)
        }
    )
    times["add_page_and_explicit_96_batch_s"] = time.perf_counter() - start
    assert not p.validate_layout()
    path = output / "gothic-backend.apcraft"
    p.save(path)
    reopened = load_project(path)
    assert reopened.to_dict() == p.to_dict()
    snapshot = reopened.snapshot()
    (output / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, allow_nan=False), encoding="utf8"
    )
    proof = reopened.segmented_variant_status(variant)
    report = proof["certificate"]["math"]
    assert reopened.loft_status(target)["status"] == "REJECTED"
    assert [len(page["parts"]) for page in snapshot["pages"]] == [48, 48]
    result = {
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "imported_module": imported.__file__,
        "proof_type": "PUBLIC_BACKEND_NOT_NATIVE_UI",
        "fixture": "independent Gothic profiles20/30 and18/25,depth10,scale1",
        "target_surface_id": target,
        "profile_ids": [a, b],
        "variant_id": variant,
        "original_target_status": "REJECTED",
        "material_mode": proof["status"],
        "counts": report["counts"],
        "embedding": proof["certificate"]["embedding"],
        "raw_position_bound_paper_mm": report["max_surface_deviation_paper_mm"],
        "material_position_bound_paper_mm": float(
            Fraction(
                proof["certificate"]["material_frame"][
                    "max_target_to_material_deviation_paper_mm_exact"
                ]
            )
        ),
        "manual_page_part_counts": [48, 48],
        "save_reopen_equal": True,
        "backend_runtime_seconds": times,
        "independent_bridge_review": "PENDING",
        "native_ui": "NOT_RUN",
        "vector_export": "NOT_RUN",
        "new_user": "NOT_RUN",
        "physical": "NOT_RUN",
        "file_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                Path(imported.__file__),
                ROOT / "tests/authoring/test_segmented_surface_curves.py",
                path,
                output / "snapshot.json",
            ]
        },
    }
    (output / "results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf8"
    )
    print(json.dumps({"status": "PASS", "times": times, "counts": report["counts"]}))


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
