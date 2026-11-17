"""Pinned backend author edits and whole-source closure, explicitly NOT UI proof."""

import argparse
import hashlib
import json
import math
import platform
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

import archpapercraft.authoring.project as project_module  # noqa: E402
from archpapercraft.authoring import load_project  # noqa: E402
from archpapercraft.exporter.author_export import export_all  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "RUNNING",
        "proof_kind": "BACKEND_PUBLIC_COMMANDS_SOURCE_CLOSURE_ACTUAL_SVG_PDF_NOT_UI",
        "independent_review": "PENDING",
        "native_ui": "NOT_RUN",
        "external_editor": "NOT_RUN",
        "new_user": "NOT_RUN",
        "physical_build": "NOT_VERIFIED",
    }
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if sha != args.expected_sha:
            raise RuntimeError("Actual checkout differs from the required source pin")
        module_path = Path(project_module.__file__).resolve()
        if not module_path.is_relative_to(ROOT / "src"):
            raise RuntimeError("The proof imported another worktree")
        changed = subprocess.check_output(
            ["git", "diff", "HEAD", "--name-only", "--", "src", "tests", "tools"],
            cwd=ROOT,
            text=True,
        ).strip()
        if changed:
            raise RuntimeError("Runtime/test sources are not frozen: " + changed)
        result.update(
            source_sha=sha,
            module_path=str(module_path),
            python=platform.python_version(),
            source_hashes={
                str(path.relative_to(ROOT)): digest(path)
                for path in sorted((ROOT / "src").rglob("*.py"))
            },
            driver_sha256=digest(Path(__file__)),
        )
        timings = {}
        start = time.perf_counter()
        p, sid, pid, cid = constructed(side="second")
        timings["initial_public_fixture_s"] = time.perf_counter() - start
        record = p.curved_connectors[cid]
        slot_ids = record.slot_ids[:]
        original_frame = p.parts[pid].frame
        original_placement = p.placements[pid]
        start = time.perf_counter()
        p.set_curved_tab(cid, slot_ids[0], enabled=False)
        p.set_curved_tab(cid, slot_ids[1], tip_offset_mm=0.01)
        foreign_profile = p.add_profile(
            [[-2, -2], [2, -2], [2, 2], [-2, 2]],
            plane={"origin": [0, 0, 100], "u": [1, 0, 0], "v": [0, 1, 0]},
        )
        foreign = p.add_surface(foreign_profile, name="Actual unconnected far material")
        p.recompute()
        p.set_placement(p.part_for_surface(foreign), p.add_page(), 50, 50)
        for issue in p.validate_layout():
            if issue.severity == "error":
                raise AssertionError("Actual layout/geometry error: " + issue.message)
            if issue.severity == "warning":
                p.acknowledge(issue.id)
        timings["author_edits_recompute_and_layout_s"] = time.perf_counter() - start
        if p.parts[pid].frame != original_frame or p.placements[pid] != original_placement:
            raise AssertionError("Authored source edits moved the saved frame/locked placement")
        path = target / "authored.apcraft"
        start = time.perf_counter()
        p.save(path)
        source_bytes = path.read_bytes()
        timings["save_s"] = time.perf_counter() - start
        start = time.perf_counter()
        p = load_project(path)
        timings["reopen_s"] = time.perf_counter() - start
        if p.curved_connectors[cid].slot_ids != slot_ids:
            raise AssertionError("Save/reopen changed stable authored slot identities")
        for name in ("cold", "warm"):
            start = time.perf_counter()
            snapshot = p.snapshot()
            timings["snapshot_" + name + "_s"] = time.perf_counter() - start
        dump(target / "snapshot.json", snapshot)
        start = time.perf_counter()
        geometry = p.curved_connector_geometry(cid)
        timings["readonly_geometry_s"] = time.perf_counter() - start
        if sum(row["enabled"] for row in geometry["all_tabs"]) != 11:
            raise AssertionError("Actual command packet lost the explicit off slot")
        if geometry["all_tabs"][1]["tip_offset_mm"] != 0.01:
            raise AssertionError("Actual command packet lost the explicit custom tip")
        dump(target / "readonly-geometry.json", geometry)
        reports = {}
        for name in ("cold", "warm"):
            start = time.perf_counter()
            export_all(snapshot, target / "vectors")
            timings["export_" + name + "_s"] = time.perf_counter() - start
            report = assert_actual_reports(target / "vectors", sid, pid)
            expected = 600 * math.pi + 11 * 0.24 * 9.5 / 2
            for output in report["outputs"].values():
                actual = sum(map(Fraction, output["area_exact"])) / 2
                if abs(float(actual) - expected) > 0.01:
                    raise AssertionError("Actual vector output violates independent analytic area")
            reports[name] = report
        if path.read_bytes() != source_bytes:
            raise AssertionError("Publication changed the old authored source bytes")
        material = snapshot["construction_checks"]["lofts"][sid]["curved_material"]
        result.update(
            status="PASS_IN_BACKEND_SCOPE",
            timings_seconds=timings,
            surface_id=sid,
            part_id=pid,
            connector_id=cid,
            foreign_surface_id=foreign,
            slot_ids=slot_ids,
            disabled_slot_id=slot_ids[0],
            custom_tip_slot_id=slot_ids[1],
            construction_status=p.curved_connector_status(cid),
            source_native_strain=material["source_native_strain"],
            scene_checks=material["domain_connector_checks"][cid]["scene_clearance"],
            actual_output_reports=reports,
            independent_analytic_expected_body_and_eleven_tabs_mm2=expected,
            source_bytes_unchanged=True,
            geometry_display_is_proof=False,
            measurements_scope="This process and fixture only; no UI latency/novice/physical claim",
            numeric_limits={
                "curved_registry_entries": 64,
                "slot_pool_per_record": 1000,
                "canonical_source_context_bytes": 32 * 1024 * 1024,
                "native_source_cache_entries": 4,
                "canonical_snapshot_cache_entries": 2,
                "topology_max_pairs": 400000,
            },
        )
        result["files"] = {
            str(file.relative_to(target)): {"bytes": file.stat().st_size, "sha256": digest(file)}
            for file in sorted(target.rglob("*"))
            if file.is_file()
        }
    except Exception as exc:
        result.update(status="FAIL", error_type=type(exc).__name__, error=str(exc))
        dump(target / "results.json", result)
        raise
    dump(target / "results.json", result)
    print(json.dumps({"source_sha": sha, "status": result["status"], "timings": timings}))


if __name__ == "__main__":
    main()
