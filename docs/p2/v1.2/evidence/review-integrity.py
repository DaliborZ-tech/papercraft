"""Reviewer-owned integrity checks; no changes to authoritative design files."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
BASE = "6eb8977011854b242ab1dac8ea929e262e3b9563"
ARCHIVE = "f9507e325c479c8b703e7f52c410de6847958720"
CODE = subprocess.check_output(["git", "rev-parse", "HEAD"],cwd=ROOT,text=True).strip()
SHORT = CODE[:7]
commands = []
def git(*args, cwd=ROOT):
    call = subprocess.run(["git", *map(str,args)], cwd=cwd, text=True, capture_output=True)
    commands.append(dict(args=list(map(str,args)), cwd=str(cwd), exit=call.returncode,
                         stdout=call.stdout.strip(), stderr=call.stderr.strip()))
    call.check_returncode()
    return call.stdout.strip()
def unique_object(pairs):
    result = {}
    for key,value in pairs:
        assert key not in result, f"Duplicate JSON key {key}"
        result[key]=value
    return result
checks=[]
def check(name, condition):
    checks.append(dict(name=name,passed=bool(condition)))
    assert condition, name
queue=json.loads((ROOT/"05_WORK_QUEUE.json").read_text(encoding="utf-8"),object_pairs_hook=unique_object,
                 parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
tickets={item["id"]:item for item in queue["tickets"]}
check("all_ticket_ids_unique",len(tickets)==len(queue["tickets"]))
graph={key:item["depends_on"]+item.get("completed_by",[]) for key,item in tickets.items()}
active,visited=set(),set()
def walk(name):
    assert name in graph and name not in active, name
    if name in visited:return
    active.add(name)
    for dep in graph[name]:walk(dep)
    active.remove(name);visited.add(name)
for name in graph:walk(name)
check("depends_and_completed_by_form_DAG",len(visited)==len(graph))
new_acs={f"AC-AU{n:02}" for n in range(1,19)}
mapping={ac:[] for ac in new_acs}
for name,item in tickets.items():
    for ac in item["acceptance"]:
        if ac in mapping:mapping[ac].append(name)
check("all_18_new_criteria_traced",all(mapping.values()))
check("all_new_product_criteria_NOT_RUN",all(state.startswith("NOT_RUN") for item in tickets.values()
    for ac,state in item.get("acceptance_state",{}).items() if ac in new_acs))
check("all_P2_production_unauthorized",all(item["execution_authorized_on_realization"] is False
    for item in tickets.values() if item["stage"]=="P2"))
check("only_current_design_authorized",queue["current_authorized_package"]=="PC-012" and
      tickets["PC-012"]["execution_authorized_on_realization"] is True)
check("first_author_release_A_has_both_children",tickets["PC-006"]["completed_by"]==["PC-006A","PC-006B"])
check("first_sketch_not_blocked_by_preset_parent",tickets["PC-006A"]["depends_on"]==["PC-012"])
check("physical_proof_is_P3", "AC-AU18" in tickets["PC-011"]["acceptance"] and tickets["PC-011"]["stage"]=="P3")
check("old_v11_acceptance_preserved",any(x["contract_version"]=="1.1" and x["accepted_by_owner"] is True
    for x in queue["product_gate_history"]))
check("new_gate_not_PO_accepted",queue["product_gate"]["contract_version"]=="1.2" and
      queue["product_gate"]["status"]=="PO_PENDING" and queue["product_gate"]["accepted_by_owner"] is False)
check("all_sixteen_epics_visible",all(f"| E{n:02} " in (ROOT/"docs/p2/v1.2/ROADMAP.md").read_text(encoding="utf-8") for n in range(1,17)))
changed=git("diff","--name-only",BASE,"HEAD").splitlines()
check("src_and_pyproject_unchanged",not any(x.startswith("src/") or x=="pyproject.toml" for x in changed))
git("diff","--check",BASE,"HEAD","--",".",":(exclude)docs/p2/v1.2/GEOMETRY_SPIKES.md")
git("diff","--check")
git("merge-base","--is-ancestor",BASE,"HEAD")
bundle=ROOT/"docs/p2/archive/p2-v11-prototype.bundle"
git("bundle","verify",bundle)
check("bundle_bytes_exact",hashlib.sha256(bundle.read_bytes()).hexdigest()=="9430a97e1668e3ba862ec720c8558a034034144af5d0b47c911956a1f2b5f769")
check("bundle_head_exact",git("bundle","list-heads",bundle).split()[0]==ARCHIVE)
restore=Path(tempfile.mkdtemp(prefix="papercraft-review-restore-"))
try:
    git("init","--bare",restore)
    git("fetch",ROOT,BASE,cwd=restore)
    git("fetch",bundle,"refs/heads/revival/p2:refs/heads/reviewer-archive",cwd=restore)
    check("independent_fresh_repository_restore",git("rev-parse","refs/heads/reviewer-archive",cwd=restore)==ARCHIVE)
    for path in ["src/archpapercraft/domain/project.py","src/archpapercraft/ui/panel_main_window.py",
                 "tests/panel/test_paper.py","tools/panel/p2_demo.py","docs/p2/evidence/house-editor-proof/editor-results.json"]:
        git("cat-file","-e",f"{ARCHIVE}:{path}",cwd=restore)
finally:
    # Disposable bare repository retained: Windows pack cleanup needs separate
    # handling. It is not a project checkout and has no working tree.
    pass

raw=json.loads((ROOT/f"docs/p2/v1.2/evidence/review-run-{SHORT}/geometry.json").read_text(encoding="utf-8"))
published=json.loads((ROOT/"docs/p2/v1.2/evidence/geometry-dr01-results.json").read_text(encoding="utf-8"))
check("reproduced_results_equal_published",raw["results"]==published["results"])
for path,digest in raw["source_files_sha256"].items():
    check("actual_spike_source_hash_"+path,hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest)
suite=ET.parse(ROOT/f"docs/p2/v1.2/evidence/review-tests-{SHORT}.xml").getroot().find("testsuite")
counts={key:int(suite.attrib[key]) for key in ["tests","failures","errors","skipped"]}
check("own_273_tests_no_fail_error_skip",counts==dict(tests=273,failures=0,errors=0,skipped=0))
result=dict(code_pin=git("rev-parse","HEAD"),base=BASE,checks=checks,acceptance_mapping=mapping,
            test_counts=counts,commands=commands,retained_disposable_bare_repository=str(restore),
            pass_count=len(checks),passed=all(x["passed"] for x in checks))
(Path(__file__).parent/f"review-integrity-{SHORT}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(code_pin=result["code_pin"],pass_count=len(checks),passed=result["passed"],test_counts=counts)))
