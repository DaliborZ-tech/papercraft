"""Read-only independent arithmetic and source binding for the actual UI files."""
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from fractions import Fraction as F
from pathlib import Path

from pypdf import PdfReader

OUT = Path(__file__).parent
ROOT = OUT.parents[4]
PIN = "d94f9b329c1e1e73241e8b66b76924a72bfac214"
events = [json.loads(line) for line in (OUT / "events.jsonl").read_text(encoding="utf8").splitlines()]
saved = json.loads((OUT / "own-four-part-model.apcraft").read_text(encoding="utf8"))
recovered = json.loads((OUT / "recovered-four-part-model.apcraft").read_text(encoding="utf8"))
reopened = json.loads((OUT / "observed.json").read_text(encoding="utf8"))
before_revert = json.loads((OUT / "recovered-before-user-revert.json").read_text(encoding="utf8"))
assert saved == reopened == before_revert == recovered
assert not json.loads((OUT / "after-new-empty.json").read_text(encoding="utf8"))["surfaces"]
timer = next(e for e in events if e.get("actual_timer_draft"))
assert timer["document"] == saved
assert timer["ui_draft"]["pending_name"]["text"] == "Rozepsana Stena"
restore = next(e for e in events if e.get("observation") == "recovery-restored-raw-name-positive")
assert restore["raw_name"] == "Rozepsana Stena" and restore["controller_dirty"] and restore["controller_path"] is None
assert any(p["position_locked"] and p["rotation_locked"] and p["rotation_deg"] == 15 for p in saved["placements"].values())

def area(points):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points, points[1:]+points[:1]))) / 2

svg_areas, digests = [], set()
for path in sorted((OUT / "export").glob("*.svg")):
    root = ET.parse(path).getroot()
    assert (root.attrib["width"], root.attrib["height"]) == ("210mm", "297mm")
    digests.add(root.attrib["data-snapshot-digest"])
    for group in root.iter():
        if group.attrib.get("data-role") == "CUT":
            for curve in group:
                data = curve.attrib["d"]
                assert re.sub(r"[MLZ\d.\s-]", "", data) == ""
                numbers = [F(n) for n in re.findall(r"-?\d+(?:\.\d+)?", data)]
                svg_areas.append(area(list(zip(numbers[::2], numbers[1::2]))))
pdf = PdfReader(OUT / "export/model.pdf")
pdf_areas = []
for page in pdf.pages:
    assert abs(F(str(page.mediabox.width))*F(127,360)-210) < F(1,10**10)
    assert abs(F(str(page.mediabox.height))*F(127,360)-297) < F(1,10**10)
    text = page.get_contents().get_data().decode("latin1")
    for body in re.findall(r"/APRole_CUT BMC(.*?)EMC", text, re.S):
        pairs = re.findall(r"(-?[\d.]+) (-?[\d.]+) [ml]", body)
        pdf_areas.append(area([(F(x),F(y)) for x,y in pairs]))
assert sorted(svg_areas) == sorted(pdf_areas) == [300,600,2520,7000]
assert len(digests) == 1 and len(pdf.pages) == 2
binding = {}
for rel in subprocess.check_output(["git","ls-tree","-r","--name-only",PIN,"src","tools"],cwd=ROOT,text=True).splitlines():
    expected = subprocess.check_output(["git","show",f"{PIN}:{rel}"],cwd=ROOT)
    actual = (ROOT / rel).read_bytes().replace(b"\r\n",b"\n")
    assert actual == expected, rel
    binding[rel] = hashlib.sha256(actual).hexdigest()
result = dict(runtime_pin=PIN,harness_pin="57efd391e5be1c625e9e7b68b1c2a54a8aec2910",
              process_starts=[e for e in events if e.get("start")],
              native_timer_crash_recovery=True,saved_reopened_recovered_equal=True,
              positive_both_locks=True,svg_cut_areas_mm2=list(map(str,svg_areas)),
              pdf_cut_areas_mm2=list(map(str,pdf_areas)),total_area_mm2="10420",
              pages=2,snapshot_digest=digests.pop(),source_lf_sha256=binding,
              original_file_sha256=hashlib.sha256((OUT/"own-four-part-model.apcraft").read_bytes()).hexdigest())
(OUT / "results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
print("PASS: source binding; original=reopened=timer document=recovered; two locks; SVG/PDF 10420 mm2, two A4")
