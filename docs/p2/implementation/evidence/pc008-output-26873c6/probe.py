"""Pinned backend actual-file proof; native UI, novice and physical NOT_RUN."""

import hashlib
import json
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
import archpapercraft.exporter.author_export as writer  # noqa: E402
from archpapercraft.authoring import load_project  # noqa: E402
from archpapercraft.authoring.segmented_surface import _candidate  # noqa: E402
from archpapercraft.exporter.segmented_output_validation import _canonical_snapshot  # noqa: E402


def hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(exist_ok=False)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if sha != "26873c6d0950af412ba531f01440c3506b3dd6b1":
        raise ValueError("Use the exact pinned production source for this archived proof.")
    reports = {}
    fixtures = {
        "line64": "pc008-domain-95fa2c7/backend-fixture.apcraft",
        "curved96": "pc008-curved-domain-518b91a/raw/gothic-backend.apcraft",
    }
    for label, relative in fixtures.items():
        project = load_project(ROOT / "docs/p2/implementation/evidence" / relative)
        start = time.perf_counter()
        snapshot = project.snapshot()
        snapshot_s = time.perf_counter() - start
        _canonical_snapshot.cache_clear()
        _candidate.cache_clear()
        # Immutable source content, not revision-only cache. No author source
        # is resampled, altered or written by the publisher.
        timings, counts = {}, {}
        for mode in ("cold", "warm"):
            start = time.perf_counter()
            directory = output / f"{label}-{mode}"
            writer.export_all(snapshot, directory)
            timings[mode] = time.perf_counter() - start
            counts[mode] = _canonical_snapshot.cache_info()._asdict()
        assert hashes(output / f"{label}-cold") == hashes(output / f"{label}-warm")
        manifest = json.loads(
            (output / f"{label}-cold/.author-export.json").read_text(encoding="utf8")
        )
        actual = manifest["actual_curve_output_checks"]["segmented_variants"]
        assert actual["status"] == "VERIFIED"
        expected = int(label[-2:])
        assert len(actual["parts"]) == expected
        records = [
            record for part in actual["parts"].values() for record in part["outputs"].values()
        ]
        files = list((output / f"{label}-cold").iterdir())
        reports[label] = {
            "snapshot_seconds": snapshot_s,
            "export_seconds": timings,
            "canonical_cache": counts,
            "cold_warm_all_bytes_equal": True,
            "source_binding_json_bytes": len(
                json.dumps(
                    snapshot["construction_checks"]["segmented_source_project"],
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                ).encode()
            ),
            "snapshot_json_bytes": len(
                json.dumps(
                    snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                ).encode()
            ),
            "actual_part_count": expected,
            "target_status": next(
                iter(snapshot["construction_checks"]["reference_targets"].values())
            )["status"],
            "actual_material_position_error_max_mm": max(
                float(Fraction(record["source_material_to_actual_position_error_bound_exact"]))
                for record in records
            ),
            "actual_material_area_error_max_mm2": max(
                float(Fraction(record["source_material_to_actual_area_error_bound_exact"]))
                for record in records
            ),
            "file_bytes": {p.name: p.stat().st_size for p in files},
            "bundle_bytes": sum(p.stat().st_size for p in files),
            "sha256": hashes(output / f"{label}-cold"),
        }
        print(json.dumps({label: reports[label]}), flush=True)
    files = [
        ROOT / "src/archpapercraft" / path
        for path in (
            "authoring/project.py",
            "exporter/author_export.py",
            "exporter/segmented_output_validation.py",
        )
    ]
    files.append(Path(__file__).resolve())
    result = {
        "source_sha": sha,
        "imported_writer": writer.__file__,
        "proof_type": "PINNED_PUBLIC_BACKEND_TO_ACTUAL_SVG_PDF; NOT_NATIVE_UI",
        "fixtures": reports,
        "source_file_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
        },
        "independent_review": "PENDING",
        "native_ui": "NOT_RUN",
        "async_export_and_cancel": "NOT_RUN_IN_THIS_BASE; ROOT_ASYNC_INTEGRATION_REQUIRED",
        "new_user": "NOT_RUN",
        "physical_build": "NOT_RUN",
    }
    (output / "results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf8"
    )


if __name__ == "__main__":
    main()
