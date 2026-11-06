"""Check design-package integrity; this cannot grant product acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def validate(root: Path) -> dict:
    queue = json.loads((root / "05_WORK_QUEUE.json").read_text(encoding="utf-8"))
    checks = {}
    gate = queue["product_gate"]
    checks["new_gate_not_falsely_accepted"] = (
        gate["contract_version"] == "1.2"
        and gate["status"] == "PO_PENDING"
        and gate["accepted_by_owner"] is False
    )
    checks["actual_v11_acceptance_preserved"] = any(
        item["contract_version"] == "1.1" and item["accepted_by_owner"] is True
        for item in queue["product_gate_history"]
    )
    tickets = queue["tickets"]
    by_id = {item["id"]: item for item in tickets}
    checks["unique_ticket_ids"] = len(tickets) == len(by_id)
    checks["existing_ticket_ids_preserved"] = all(f"PC-{n:03}" in by_id for n in range(13))
    dependencies = {
        name: item["depends_on"] + item.get("completed_by", []) for name, item in by_id.items()
    }
    visiting, done = set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError(f"Ticket dependency cycle at {name}")
        if name in done:
            return
        if name not in dependencies:
            raise ValueError(f"Unknown dependency {name}")
        visiting.add(name)
        for target in dependencies[name]:
            visit(target)
        visiting.remove(name)
        done.add(name)

    for name in dependencies:
        visit(name)
    checks["completion_and_dependency_DAG"] = True
    acs = {f"AC-AU{n:02}" for n in range(1, 19)}
    traced = {ac for item in tickets for ac in item["acceptance"]}
    checks["all_new_AC_have_tickets"] = acs <= traced
    active_p2_acs = {ac for item in tickets if item["stage"] == "P2" for ac in item["acceptance"]}
    checks["promoted_original_AC_explicitly_traced"] = {
        "AC-G06",
        "AC-C08",
        "AC-R01",
        "AC-R02",
        "AC-R03",
        "AC-R04",
        "AC-R05",
    } <= active_p2_acs
    checks["no_new_product_AC_claimed_PASS"] = all(
        state.startswith("NOT_RUN")
        for item in tickets
        for ac, state in item.get("acceptance_state", {}).items()
        if ac in acs
    )
    checks["first_author_version_has_no_preset_dependency"] = (
        by_id["PC-006A"]["depends_on"] == ["PC-012"]
        and by_id["PC-006B"]["depends_on"] == ["PC-006A"]
        and by_id["PC-006"]["completed_by"] == ["PC-006A", "PC-006B"]
    )
    checks["physical_acceptance_separate"] = (
        "AC-AU18" in by_id["PC-011"]["acceptance"]
        and by_id["PC-011"]["execution_authorized_on_realization"] is False
        and queue["p2_digital_delivery"].startswith("NOT_RUN")
    )
    checks["current_package_authorized"] = (
        queue["current_authorized_package"] == "PC-012"
        and by_id["PC-012"]["execution_authorized_on_realization"] is True
    )
    checks["new_production_scope_not_falsely_authorized"] = all(
        item["execution_authorized_on_realization"] is False
        for item in tickets
        if item["stage"] == "P2"
    )
    roadmap = (root / "docs/p2/v1.2/ROADMAP.md").read_text(encoding="utf-8")
    checks["all_16_epics_retained"] = all(f"| E{n:02} " in roadmap for n in range(1, 17))
    missing_links = []
    for document in (root / "docs/p2/v1.2").glob("*.md"):
        body = document.read_text(encoding="utf-8")
        for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body):
            if href.startswith(("https://", "http://", "#")):
                continue
            target = href.split("#", 1)[0]
            if not (document.parent / target).exists():
                missing_links.append(f"{document.name}: {href}")
    checks["local_document_links_exist"] = not missing_links
    bundle = root / queue["preserved_prototype"]["bundle"]
    verified = subprocess.run(
        ["git", "bundle", "verify", str(bundle)], cwd=root, capture_output=True, text=True
    )
    checks["preservation_bundle_valid"] = verified.returncode == 0
    checks["preservation_bundle_exact_bytes"] = hashlib.sha256(bundle.read_bytes()).hexdigest() == (
        "9430a97e1668e3ba862ec720c8558a034034144af5d0b47c911956a1f2b5f769"
    )
    changed = subprocess.run(
        ["git", "diff", "--name-only", "6eb8977011854b242ab1dac8ea929e262e3b9563", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    checks["no_production_pipeline_or_schema_changes"] = not any(
        path.startswith("src/") or path == "pyproject.toml" for path in changed
    )
    return {"checks": checks, "missing_links": missing_links, "pass": all(checks.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.root.resolve())
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
