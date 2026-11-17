"""Read actual native artifacts independently of production geometry helpers."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from fractions import Fraction as F
from pathlib import Path

from pypdf import PdfReader

OUT = Path(__file__).parent
ROOT = OUT.parents[4]
HOUSE = ROOT.parent / "integration/docs/p2/implementation/evidence/workspace-house-191d24e-run01"
report = json.loads((HOUSE / "results.json").read_text(encoding="utf8"))
permanent, ephemeral = [], []
for rel, expected in report["files_sha256"].items():
    path = HOUSE / rel
    if rel.endswith(".recovery.json.lock"):
        assert not path.exists()
        ephemeral.append(rel)
    else:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, rel
        permanent.append(rel)
assert len(permanent) == 36 and len(ephemeral) == 1
house = json.loads((HOUSE / "model-A/model-A.apcraft").read_text(encoding="utf8"))
snapshot = json.loads((HOUSE / "model-A/snapshot.json").read_text(encoding="utf8"))
assert (len(house["surfaces"]),len(house["parts"]),len(house["pages"])) == (11,9,2)
locked = [house["placements"][pid] for pid,p in house["parts"].items() if p["name"] == "Jizni stena s chlopnemi"]
assert len(locked) == 1 and locked[0]["position_locked"] and locked[0]["rotation_locked"]

def polygon_area(points):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points, points[1:]+points[:1]))) / 2

def read_output(folder):
    manifest = json.loads((folder / ".author-export.json").read_text(encoding="utf8"))
    svg_areas = []
    labels = []
    for path in folder.glob("*.svg"):
        root = ET.parse(path).getroot()
        assert root.attrib["data-snapshot-digest"] == manifest["snapshot_digest"]
        assert (root.attrib["width"],root.attrib["height"]) == ("210mm","297mm")
        labels.extend(e.text for e in root.iter() if e.tag.endswith("text"))
        for group in root.iter():
            if group.attrib.get("data-role") == "CUT":
                for path in group:
                    assert not re.sub(r"[MLZ\d.\s-]", "", path.attrib["d"])
                    numbers = [F(n) for n in re.findall(r"-?\d+(?:\.\d+)?",path.attrib["d"])]
                    svg_areas.append(polygon_area(list(zip(numbers[::2],numbers[1::2]))))
    pdf = PdfReader(folder / "model.pdf")
    assert manifest["snapshot_digest"] in str(pdf.metadata.subject)
    pdf_areas = []
    for page in pdf.pages:
        for body in re.findall(r"/APRole_CUT BMC(.*?)EMC",page.get_contents().get_data().decode("latin1"),re.S):
            for curve in re.findall(r"n (.*?)\bh\b",body,re.S):
                pdf_areas.append(polygon_area([(F(x),F(y)) for x,y in re.findall(r"(-?[\d.]+) (-?[\d.]+) [ml]",curve)]))
    assert len(pdf_areas) == len(svg_areas)
    deltas = [abs(a-b) for a,b in zip(sorted(svg_areas),sorted(pdf_areas))]
    assert all(delta < F(1,100) for delta in deltas)
    return manifest,labels,pdf,dict(cut_contours=len(svg_areas),max_contour_area_difference_mm2=str(max(deltas)),snapshot_digest=manifest["snapshot_digest"])

manifest,labels,pdf,house_output = read_output(HOUSE / "model-A/export")
digest = hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
assert digest == manifest["snapshot_digest"] and len(pdf.pages) == 2
fresh = json.loads((OUT / "fresh-named-wall.apcraft").read_text(encoding="utf8"))
assert [p["name"] for p in fresh["parts"].values()] == ["P1 · Jizni stena"]
_,labels,pdf,fresh_output = read_output(OUT / "export")
assert "P1 · Jizni stena" in labels and "Jizni stena" in pdf.pages[0].extract_text()
assert len(pdf.pages) == 1
events = [json.loads(line) for line in (OUT / "events.jsonl").read_text(encoding="utf8").splitlines()]
start = next(event for event in events if event.get("start"))
assert Path(start["source"]).resolve() == ROOT / "src/archpapercraft/ui/author_window.py"
binding = json.loads((OUT.parent / "workspace-repair-final-binding.json").read_text(encoding="utf8"))
for rel,expected in binding["source_lf_sha256"].items():
    assert hashlib.sha256((ROOT/rel).read_bytes().replace(b"\r\n",b"\n")).hexdigest() == expected
result = dict(source_pin=binding["pin"],harness_pin="9449bac903418d3b03bcea726303a8f060bb3595",actual_process=start,
              house_permanent_files_verified=permanent,house_ephemeral_lease_removed=ephemeral,
              house_shape=dict(surfaces=11,parts=9,pages=2),house_both_locks=True,
              house_output=house_output,fresh_native_output=fresh_output,
              fresh_name_in_saved_document_svg_pdf=True,three_prior_native_findings_closed=True,
              new_bottom_dock_height_finding="CONFIRMED; narrow repair pending")
(OUT / "results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
print("PASS: 36 permanent house files; 1 removed lease; house locks and snapshot digest; actual named SVG/PDF; native source binding")
