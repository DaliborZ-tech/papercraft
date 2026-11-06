"""Reviewer-owned adversarial re-review of global regularity, not UI approval."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.spikes.p2_v12_geometry import Loft, Profile, developability_evidence

pin = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
checks = []
def check(name, condition, details=None):
    checks.append(dict(name=name, passed=bool(condition), details=details))
    assert condition, checks[-1]

for kind in ["circle", "ellipse", "gothic"]:
    p = Profile(kind, 20, 30)
    for k in [.25, 1.4, 3.0]:
        for angle in [-180, 180, 540]:
            loft = Loft(p,p,k,0,angle)
            row = developability_evidence(loft)
            v_star = 1/(1+k)
            singular = loft.differential(.37,v_star)
            check(f"collapsed_{kind}_{k}_{angle}",
                  not singular["regular"] and row["verdict"]=="DEGENERATE_OR_SINGULAR",
                  dict(v_star=v_star,jacobian=singular["jacobian"],evidence=row))

# The zero determinant does not prove regularity: for a rotated planar circle,
# J(v) is affine up to orientation; its root follows analytically below.
p=Profile("circle",20,20)
for k,angle in [(1.4,60),(.5,80),(1.4,120),(1.0,17)]:
    c=math.cos(math.radians(angle))
    v_star=(1-k*c)/(1+k*k-2*k*c)
    assert 0<v_star<1
    loft=Loft(p,p,k,0,angle)
    row=developability_evidence(loft)
    check(f"general_planar_circle_singularity_{k}_{angle}",
          loft.differential(.37,v_star)["jacobian"]<1e-8 and
          row["verdict"]=="DEGENERATE_OR_SINGULAR",dict(v_star=v_star,evidence=row))

for kind in ["circle","ellipse"]:
    for k in [.7,1.5]:
        p=Profile(kind,20,30)
        row=developability_evidence(Loft(p,p,k,0))
        b=20 if kind=="circle" else 30
        oracle=min(1,k)*abs(k-1)*math.pi*20*b
        proof=row["regularity_proof"]
        check(f"proved_semianulus_{kind}_{k}", row["verdict"]=="EXACT_PLANAR" and
              abs(proof["analytic_jacobian_lower_bound_mm2"]-oracle)<1e-8 and
              proof["boundary_simple"] is True, row)

for kind in ["circle","ellipse","gothic"]:
    p=Profile(kind,20,30)
    exact=developability_evidence(Loft(p,p,1.4,15))
    check(f"spatial_proof_{kind}",exact["verdict"]=="EXACT_CONICAL" and
          exact["regularity_proof"]["analytic_jacobian_lower_bound_mm2"]>0)
    check(f"twisted_negative_{kind}",developability_evidence(Loft(p,p,1.4,15,25))["verdict"]=="NONDEVELOPABLE")
    check(f"negative_depth_not_false_exact_{kind}",not developability_evidence(Loft(p,p,1.4,-15))["verdict"].startswith("EXACT"))
check("unsupported_planar_gothic_no_certificate",
      developability_evidence(Loft(Profile("gothic",20,30),Profile("gothic",20,30),1.4,0))["verdict"]=="UNPROVEN")
check("finite_zeros_do_not_prove_family",
      developability_evidence(Loft(Profile("circle",20,20),Profile("circle",20,21),1.2,30))["verdict"]=="UNPROVEN")
result=dict(code_pin=pin, checks=checks, passed=len(checks), total=len(checks),
            reviewer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(Path(__file__).parent/f"review-final-checks-{pin[:7]}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(code_pin=pin,passed=len(checks),total=len(checks))))
