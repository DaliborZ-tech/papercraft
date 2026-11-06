"""Reviewer-owned independent formulae and adversarial probe of the pinned spike."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.spikes import p2_v12_geometry as subject

checks = []
findings = []

def close(name, actual, oracle, tolerance=1e-8):
    passed = math.isfinite(float(actual)) and abs(float(actual) - oracle) <= tolerance
    checks.append(dict(name=name, actual=float(actual), oracle=oracle, tolerance=tolerance, passed=passed))
    assert passed, checks[-1]

def truth(name, condition, details=None):
    checks.append(dict(name=name, passed=bool(condition), details=details))
    assert condition, checks[-1]

# Compute exact dimensions/areas directly, without the subject's profile helpers.
cylinder = subject.cylinder_exact(10, 30)
close("cylinder_circumference", cylinder["width_mm"], 20 * math.pi)
close("cylinder_area", cylinder["area_mm2"], 600 * math.pi)
for r0, r1 in [(10, 20), (20, 10), (0, 20), (20, 0)]:
    row = subject.cone_exact(r0, r1, 30)
    close(f"cone_{r0}_{r1}_angle", row["angle_rad"], 2 * math.pi * abs(r1-r0) / 30)
    close(f"cone_{r0}_{r1}_area", row["area_mm2"], math.pi * (r0+r1) * 30)
    close(f"cone_{r0}_{r1}_inner", row["inner_radius_mm"], min(r0, r1)*30/abs(r1-r0))
    close(f"cone_{r0}_{r1}_outer", row["outer_radius_mm"], max(r0, r1)*30/abs(r1-r0))
    for u in [0, .2, .7, 1]:
        p0 = subject.stable_sector_flat(r0, r1, 30, u, 0)
        p1 = subject.stable_sector_flat(r0, r1, 30, u, 1)
        close(f"cone_{r0}_{r1}_ruling_{u}", math.dist(p0, p1), 30)
near = subject.stable_sector_flat(10, 10+1e-14, 30, 1, 1)
close("near_cylinder_end_x", near[0], 20*math.pi)
close("near_cylinder_end_y", near[1], 30)

# Circular ruled patch: differentiating both circles contributes pi squared.
p = subject.Profile("circle", 20, 20)
for angle in [30, -30, 90]:
    loft = subject.Loft(p, p, 1.2, 30, angle)
    oracle = -30 * 1.2 * 20**2 * math.pi**2 * math.sin(math.radians(angle))
    for u in [.11, .37, .83]:
        close(f"triple_{angle}_{u}", loft.differential(u, .43)["triple"], oracle, 1e-7)
    truth(f"nondevelopable_{angle}", subject.developability_evidence(loft)["verdict"] == "NONDEVELOPABLE")

# Rigid wall contact inside a roof z-y=40; overhang changes its UV origin only.
for overhang in [5, 8]:
    roof = subject.roof_attachment(eave_overhang=overhang)
    close(f"roof_uv_y_{overhang}", roof["attachment_uv_mm"][0][1], overhang*math.sqrt(2))
    close(f"roof_contact_{overhang}", roof["available_material_contact_mm2"], 500)
    truth(f"roof_world_unchanged_{overhang}", all(math.dist(a,b)<1e-9 for a,b in zip(roof["mapped_wall_line_world_mm"], [[0,0,40],[100,0,40]])))
close("roof_oversize_contact", subject.roof_attachment(tab_width=50)["available_material_contact_mm2"], 3000*math.sqrt(2))
close("roof_gap_has_no_contact", subject.roof_attachment(normal_gap=1)["available_material_contact_mm2"], 0)
base = subject.base_attachment()
close("base_nominal", base["nominal_glue_region_mm2"], 2*100*5+2*60*5)
close("base_hole_subtraction", base["actual_material_glue_region_mm2"], 2*100*5+2*60*5-20*5)

# Arc/chord, sagitta and usable target-triangle area are distinct quantities.
for n in [12,24,48]:
    row = subject.segmented_tabs(count=n)
    arc = 40*math.pi/n - .8
    chord = 40*math.sin(arc/40)
    sagitta = 20*(1-math.cos(arc/40))
    height = 5-sagitta
    target_area = chord*height/2
    flat_side = math.hypot(arc/2, 5)
    target_side = math.hypot(chord/2, height)
    close(f"tab_chord_{n}", row["base_chord_mm"], chord)
    close(f"tab_sagitta_{n}", row["hinge_sagitta_mm"], sagitta)
    close(f"tab_side_change_{n}", row["maximum_side_length_change_mm"], flat_side-target_side)
    close(f"tab_contact_relief_{n}", row["nominal_adhesion_excluding_bend_zone_mm2_per_tab"], target_area*(1-.5/height)**2)
    truth(f"tab_not_exact_{n}", "NOT proof" in row["certificate"])
truth("wide_tabs_collide", subject.segmented_tabs(width=25)["collision_pairs_over_1e_8_mm2"] > 0)

# Adversarial global regularity: antipodal coplanar profiles collapse at
# v=1/(1+k), away from the classifier's v samples 0,.5,1.
k = 1.4
collapsed = subject.Loft(p, p, k, 0, 180)
v_star = 1/(1+k)
degenerate = collapsed.differential(.37, v_star)
classification = subject.developability_evidence(collapsed)
truth("constructed_internal_singularity", not degenerate["regular"], degenerate)
findings.append(dict(id="DR-01", case="coplanar antipodal profiles", v_star=v_star,
    analytic="S=(1-(1+k)*v)*C0, so every u collapses at v=1/(1+k)",
    classifier=classification, differential=degenerate,
    observed_exact=classification["verdict"].startswith("EXACT")))

changed = subprocess.check_output(["git", "diff", "--name-only", "6eb8977011854b242ab1dac8ea929e262e3b9563", "HEAD"], cwd=ROOT, text=True).splitlines()
truth("production_sources_unchanged", not any(x.startswith("src/") or x=="pyproject.toml" for x in changed))
q = json.loads((ROOT/"05_WORK_QUEUE.json").read_text(encoding="utf-8"))
truth("v12_gate_pending", q["product_gate"]["status"]=="PO_PENDING" and q["product_gate"]["accepted_by_owner"] is False)

result = dict(code_pin=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    reviewer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), checks=checks,
    findings=findings, passed=sum(x["passed"] for x in checks), total=len(checks))
(Path(__file__).parent/"review-oracles-580e7bb.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(dict(code_pin=result["code_pin"],passed=result["passed"],total=result["total"],findings=findings),indent=2))
