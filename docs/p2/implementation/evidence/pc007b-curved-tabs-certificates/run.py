"""Reproduce the pinned pure-math examples; no UI/physical/owner approval."""

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))

from archpapercraft.authoring import curved_tabs  # noqa: E402
from archpapercraft.authoring.curved_tabs import (  # noqa: E402
    Cap,
    CircularHole,
    Limits,
    Rim,
    certify_tabs,
    periodic_tabs,
)


def summary(report):
    return {
        "status": report["status"], "scope": report["scope"],
        "physical_status": report["physical_status"], "problems": report["problems"],
        "expected_ids": report["expected_ids"], "checked_ids": report["checked_ids"],
        "pair_count": len(report["pairs"]),
        "expected_active_pair_count": report["expected_active_pair_count"],
        "whole_phase_min_pair_distance_lower_mm": min(
            (p["whole_phase_distance_lower_mm"] for p in report["pairs"]), default=None),
        "cells_used": report["cells_used"], "first_tab": report["tabs"][0],
    }


def run():
    module = Path(curved_tabs.__file__).resolve()
    if module != ROOT / "src/archpapercraft/authoring/curved_tabs.py":
        raise RuntimeError("Wrong worktree module import")
    cases = {}
    for narrow in (False, True):
        for label, radius, slope in (("cylinder", 10, 0), ("cone_lower", 10, Fraction(-1, 3)),
                                     ("cone_upper", 20, Fraction(1, 3)),
                                     ("near_positive", 10, Fraction(1, 10**20)),
                                     ("near_negative", 10, Fraction(-1, 10**20))):
            rim = Rim(radius, slope, "rim", "body")
            cap = Cap(radius, "cap")
            base, depth, relief = ((Fraction(6, 25), Fraction(19, 2), Fraction(3, 5))
                                   if narrow else (2, 2, Fraction(1, 2)))
            tabs = periodic_tabs(rim, "cap", count=12, nominal_base_mm=base,
                                 depth_mm=depth, relief_mm=relief)
            limits = Limits(Fraction(1, 100) if narrow else Fraction(8, 100),
                            Fraction(1, 100) if narrow else Fraction(1, 4),
                            1, Fraction(1, 5), Fraction(1, 100))
            report = certify_tabs(rim, tabs, cap, limits)
            cases[f"{'narrow' if narrow else 'wide'}_{label}"] = summary(report)
    # Concrete distinct negative causes; none may be erased by an unknown barrier.
    rim = Rim(10, 0, "rim", "body")
    cap = Cap(10, "cap")
    tabs = periodic_tabs(rim, "cap", count=12, nominal_base_mm=2, depth_mm=2,
                         relief_mm=Fraction(1, 2))
    limits = Limits(Fraction(8, 100), Fraction(1, 4), 1, Fraction(1, 5), Fraction(1, 100))
    cases["finite_budget"] = summary(certify_tabs(rim, tabs, cap, limits, max_cells=0))
    cases["unknown_material"] = summary(certify_tabs(
        rim, tabs, cap, replace(limits, thickness_mm=None)))
    # This disk hole contains the entire slot0 glue triangle.
    cap = replace(cap, holes=(CircularHole(Fraction(87, 10), Fraction(23, 10), 2),))
    cases["certain_hole_plus_unknown_barrier"] = summary(certify_tabs(
        rim, tabs[:1], cap, limits, unresolved_obstacle_ids=("unresolved-beam",)))
    result = {
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "module_path": str(module),
        "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "proof_kind": "PURE_MATH_COMPONENT_ONLY_INDEPENDENT_REVIEW_PENDING",
        "cases": cases,
    }
    target = Path(__file__).with_name("results.json")
    target.write_text(json.dumps(result, indent=2, default=lambda q: {
        "exact_fraction": str(q), "display_float": float(q)})+"\n", encoding="utf-8")
    print(json.dumps({name: value["status"] for name, value in cases.items()}, indent=2))


if __name__ == "__main__":
    run()
