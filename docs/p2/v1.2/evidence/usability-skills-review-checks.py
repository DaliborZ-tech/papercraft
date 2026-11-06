"""Independent pinned checks; agent exercises are not a novice usability study."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
PIN = "9a7dc15c87dac4fe19745154f18bc77e04ee0abf"
BASE = "a2d15fb1272a3fd8f539e003a13ade645abc0dae"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(path, pin=PIN):
    return git("show", f"{pin}:{path}")


def strict_json(path, pin=PIN):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(blob(path, pin), object_pairs_hook=unique)


def main():
    assert git("rev-parse", "HEAD").decode().strip() == PIN
    queue = strict_json("05_WORK_QUEUE.json")
    baseline = strict_json("05_WORK_QUEUE.json", BASE)
    lessons = strict_json("docs/p2/SKILL_IMPROVEMENTS.json")
    validation = strict_json("docs/p2/v1.2/evidence/usability-skills-validation.json")
    tickets = {ticket["id"]: ticket for ticket in queue["tickets"]}
    old_tickets = {ticket["id"]: ticket for ticket in baseline["tickets"]}
    registry = queue["project_skills"]["registry"]
    checks = {}
    checks["strict_json_three_artifacts"] = True
    checks["four_distinct_skills"] = len(registry) == 4
    checks["ticket_ids_stages_and_dependencies_unchanged"] = (
        set(tickets) == set(old_tickets)
        and all(
            all(ticket.get(key) == old_tickets[name].get(key)
                for key in ("stage", "depends_on", "completed_by", "parent"))
            for name, ticket in tickets.items()
        )
    )
    checks["gate_and_all_execution_authorizations_unchanged"] = (
        queue["product_gate"] == baseline["product_gate"]
        and all(ticket["execution_authorized_on_realization"]
                == old_tickets[name]["execution_authorized_on_realization"]
                for name, ticket in tickets.items())
    )
    checks["original_AC_and_states_preserved"] = all(
        set(old_tickets[name]["acceptance"]) <= set(ticket["acceptance"])
        and all(ticket["acceptance_state"].get(ac) == state
                for ac, state in old_tickets[name]["acceptance_state"].items())
        for name, ticket in tickets.items()
    )
    checks["all_ticket_skill_maps_and_applications_match"] = all(
        ticket["skills"] and set(ticket["skills"]) <= registry.keys()
        and len(ticket["skills"]) == len(set(ticket["skills"]))
        and sorted(ticket["skills"]) == sorted(item["skill"] for item in ticket["skill_application"])
        for ticket in tickets.values()
    )
    checks["historical_usage_not_invented"] = all(
        application["status"] == "HISTORICAL_NOT_APPLIED"
        and application["decision"] is None and not application["evidence"]
        for ticket in tickets.values() if ticket["stage"] in ("P0", "P1")
        for application in ticket["skill_application"]
    )
    checks["future_product_skill_application_not_invented"] = all(
        application["status"] == "NOT_RUN" and application["decision"] is None
        for ticket in tickets.values() if ticket["stage"] in ("P2", "P3")
        for application in ticket["skill_application"]
    )
    checks["current_addendum_application_has_concrete_evidence"] = all(
        application["status"] == "APPLIED_TO_CURRENT_ADDENDUM_ONLY"
        and application["decision"] and application["evidence"]
        and all((ROOT / path).is_file() for path in application["evidence"])
        for application in tickets["PC-012"]["skill_application"]
    )
    universal = {f"AC-US{n:02}" for n in range(1, 8)}
    checks["seven_usability_AC_in_each_P2_ticket"] = all(
        universal <= set(ticket["acceptance"])
        and all(ticket["acceptance_state"][ac].startswith("NOT_RUN") for ac in universal)
        and ticket["usability"]["implementation_in_this_slice"] is True
        and ticket["usability"]["defer_to_visual_redesign"] is False
        for ticket in tickets.values() if ticket["stage"] == "P2"
    )
    checks["first_author_study_attached_without_new_phase"] = all(
        "AC-US08" in tickets[name]["acceptance"]
        and tickets[name]["acceptance_state"]["AC-US08"].startswith("NOT_RUN")
        for name in ("PC-006", "PC-006B", "PC-010")
    ) and queue["cross_cutting_usability"]["participants_observed"] == 0
    checks["all_untried_lesson_effectiveness_pending"] = all(
        entry["effectiveness"] == "PENDING_NEXT_USE"
        and entry["next_use"]["status"] == "NOT_RUN"
        and entry["skill"] in registry
        and entry["reason"] and entry["cause"] and entry["product_correction"]
        and entry["skill_change"] and entry["usage_example"]
        and entry["verification"] and entry["independent_review"]
        for entry in lessons["entries"]
    )
    checks["ordinary_UI_rework_authorized_without_PO_fabrication"] = (
        queue["ui_ux_authority"]["existing_screens_panels_menus_interactions_binding"] is False
        and queue["ui_ux_authority"]["ordinary_in_scope_changes"] == "AUTONOMOUS"
        and queue["ui_ux_authority"]["whole_v12_contract_acceptance_implied"] is False
    )
    changes = git("diff", "--name-only", BASE, PIN).decode().splitlines()
    checks["no_runtime_algorithms_tests_or_schema_changed"] = not any(
        path.startswith(("src/", "tests/", "tools/")) or path == "pyproject.toml"
        for path in changes
    )
    diff = subprocess.run(["git", "diff", "--check", BASE, PIN], cwd=ROOT,
                          text=True, capture_output=True)
    checks["pinned_diff_whitespace_valid"] = diff.returncode == 0
    copied_skills = Path(tempfile.mkdtemp(prefix="papercraft-skill-review-pinned-"))
    env = dict(os.environ, PYTHONUTF8="1",
               PYTHONPATH=validation["temporary_validation_dependencies"])
    form_results = []
    missing_links = []
    for name, source in registry.items():
        contents = blob(source)
        folder = copied_skills / name
        folder.mkdir()
        (folder / "SKILL.md").write_bytes(contents)
        result = subprocess.run([sys.executable, validation["validator"], str(folder)],
                                env=env, capture_output=True, text=True)
        form_results.append({"name": name, "source_sha256": hashlib.sha256(contents).hexdigest(),
                             "exit_code": result.returncode, "stdout": result.stdout,
                             "stderr": result.stderr})
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", contents.decode("utf-8")):
            if target.startswith(("https://", "http://", "#")):
                continue
            resolved = (ROOT / source).parent / target.split("#", 1)[0]
            if not resolved.is_file():
                missing_links.append(source + ": " + target)
    checks["official_quick_validate_four_current_skills"] = all(
        result["exit_code"] == 0 for result in form_results
    )
    checks["skill_specification_and_AC_references_exist"] = not missing_links
    # A fresh analytical decision example with a singular fraction outside the old sampling grid.
    spec = importlib.util.spec_from_file_location("review_spike", ROOT / "tools/spikes/p2_v12_geometry.py")
    spike = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = spike
    spec.loader.exec_module(spike)
    radius, ratio, angle = 20.0, 1.8, math.radians(70)
    singular_v = (1-ratio*math.cos(angle))/(1+ratio**2-2*ratio*math.cos(angle))
    loft = spike.Loft(spike.Profile("circle", radius, radius),
                      spike.Profile("circle", radius, radius), ratio, 0, 70)
    verdict = spike.developability_evidence(loft)
    differential = loft.differential(.23, singular_v)
    checks["verification_skill_new_unsampled_singularity_decision"] = (
        0 < singular_v < .5 and differential["jacobian"] < 1e-9
        and not verdict["verdict"].startswith("EXACT")
    )
    geometry = strict_json("docs/p2/v1.2/evidence/geometry-dr01-results.json")["results"]
    roof = geometry["roof_interior_attachment"]
    checks["construction_skill_contact_not_UV_overlap_decision"] = (
        roof["valid"]["line_strictly_inside_surface"] is True
        and roof["valid"]["fake_boundary_distance_mm"] > 7
        and roof["gap_failure"]["maximum_contact_gap_mm"] > .99
        and roof["gap_failure"]["available_material_contact_mm2"] == 0
        and geometry["base_region_attachment"]["building_floor_inserted"] is False
    )
    suites = ET.fromstring(blob("docs/p2/evidence/paper-review-tests.xml")).findall("testsuite")
    failure_count = sum(int(suite.attrib["failures"]) for suite in suites)
    total_count = sum(int(suite.attrib["tests"]) for suite in suites)
    checks["delivery_skill_pinned_failure_not_worktree_claim_decision"] = (
        total_count == 90 and failure_count == 1
    )
    report = {"reviewed_source_sha": PIN, "base_sha": BASE,
              "scope": "independent document/skill decisions and integrity; no new person or physical proof",
              "checks": checks, "pass": all(checks.values()), "forms": form_results,
              "missing_skill_links": missing_links,
              "new_analytical_case": {"radius": radius, "ratio": ratio, "twist_deg": 70,
                                      "singular_v": singular_v, "jacobian": differential["jacobian"],
                                      "classification": verdict["verdict"]},
              "paper_pinned_suite": {"tests": total_count, "failures": failure_count},
              "participants_observed": 0, "physical_tests_run": 0,
              "skill_effectiveness_in_future_delivery": "PENDING_NEXT_USE",
              "temporary_pinned_skill_copy": str(copied_skills),
              "quick_validate_script": validation["validator"],
              "temporary_validation_dependencies": validation["temporary_validation_dependencies"]}
    output = ROOT / "docs/p2/v1.2/evidence/usability-skills-review-results.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
