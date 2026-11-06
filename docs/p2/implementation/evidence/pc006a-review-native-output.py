"""Independent XML/PDF audit of a completed native UI run; no writer helpers."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from pypdf import PdfReader
from pypdf.generic import ContentStream

parser = argparse.ArgumentParser()
parser.add_argument("--run", type=Path, required=True)
parser.add_argument("--sha", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
run = args.run
report = json.loads((run / "results.json").read_text(encoding="utf-8"))
snapshot = json.loads((run / "snapshot.json").read_text(encoding="utf-8"))
project = json.loads((run / "own-model.apcraft").read_text(encoding="utf-8"))
manifest = json.loads((run / "export/.author-export.json").read_text(encoding="utf-8"))
results = []
def check(name, condition, detail=None):
    results.append({"name": name, "pass": bool(condition), "detail": detail})
def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1])))/2
def polyline(d):
    tokens = re.findall(r"[MLZ]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    points, index = [], 0
    while index < len(tokens):
        op = tokens[index]
        index += 1
        if op == "Z":
            return points, True
        assert op in ("M", "L"), tokens
        points.append([float(tokens[index]), float(tokens[index+1])])
        index += 2
    return points, False
check("native-source-and-pass", report["source_sha"] == args.sha and report["status"] == "PASS")
canonical = dict(snapshot)
canonical.pop("metadata", None)
digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
check("independent-snapshot-digest", digest == manifest["snapshot_digest"])
expected_ids = set(snapshot["coverage"]["expected_part_ids"])
check("complete-coverage-matches-source", expected_ids == set(project["parts"]) and set(snapshot["coverage"]["expected_surface_ids"]) == set(project["surfaces"]))
all_ids, svg_areas, tab_areas = set(), [], []
ns = {"s": "http://www.w3.org/2000/svg"}
role_names = {"CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "LABELS", "ARTWORK", "GUIDES"}
for filename in manifest["files"]:
    if not filename.endswith(".svg"):
        continue
    root = ET.parse(run/"export"/filename).getroot()
    check("svg-page-units-"+filename, root.attrib["width"] == "210mm" and root.attrib["height"] == "297mm" and root.attrib["viewBox"] == "0 0 210 297")
    check("svg-snapshot-digest-"+filename, root.attrib["data-snapshot-digest"] == digest)
    calibration = [p for p in root.findall(".//s:path", ns) if p.attrib.get("data-calibration-mm") == "100"]
    check("svg-100mm-calibration-"+filename, len(calibration) == 1 and math.dist(*polyline(calibration[0].attrib["d"])[0]) == 100)
    page_areas = []
    for part in root.findall("s:g", ns):
        pid = part.attrib.get("data-part-id")
        if pid is None:
            continue
        all_ids.add(pid)
        groups = {g.attrib["data-role"]:g for g in part.findall("s:g", ns)}
        check("svg-editable-native-roles-"+pid, set(groups) == role_names and not part.findall(".//s:image", ns) and bool(groups["LABELS"].findall("s:text", ns)))
        for path in groups["CUT"].findall("s:path", ns):
            points, closed = polyline(path.attrib["d"])
            if closed:
                page_areas.append(area(points))
        tab_paths = groups["TABS"].findall("s:path", ns)
        for path in tab_paths:
            points, closed = polyline(path.attrib["d"])
            assert closed
            tab_areas.append(area(points))
        if tab_paths:
            tab_points = polyline(tab_paths[0].attrib["d"])[0]
            edges = [(a,b) for a,b in zip(tab_points,tab_points[1:]+tab_points[:1])]
            base = next((a,b) for a,b in edges if abs(math.dist(a,b)-30)<1e-8)
            def same(a,b,c,d):
                return (np.allclose(a,c,atol=1e-8) and np.allclose(b,d,atol=1e-8)) or (np.allclose(a,d,atol=1e-8) and np.allclose(b,c,atol=1e-8))
            counts = {}
            for role in ("CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY"):
                count = 0
                for path in groups[role].findall("s:path", ns):
                    pts, closed = polyline(path.attrib["d"])
                    for a,b in zip(pts,pts[1:]+(pts[:1] if closed else [])):
                        count += same(a,b,*base)
                counts[role] = count
            check("tab-base-hinge-not-double-cut", counts["CUT"] == 0 and counts["FOLD_MOUNTAIN"]+counts["FOLD_VALLEY"] == 1 and groups["TABS"].attrib["stroke"] == "none", counts)
    svg_areas.append(sorted(page_areas))
check("all-svg-part-coverage", all_ids == expected_ids)
check("svg-own-numeric-areas-and-hole", svg_areas == [[225.,3600.],[468.]] and tab_areas == [168.], {"closed_cut_areas_mm2":svg_areas,"tab_areas_mm2":tab_areas,"oracle":"A=3300+0.5*10*60, hole=15*15; B=10*30+7*(30+18)/2"})
pdf = PdfReader(run/"export/model.pdf")
check("pdf-shared-snapshot-and-pages", digest in pdf.metadata.subject and len(pdf.pages)==2)
pdf_areas, calibrations, used_fonts = [], [], []
for page in pdf.pages:
    matrix, stack, points, closed = np.eye(3), [], [], False
    page_closed, page_calibrations, font_names = [], [], set()
    def mapped(x,y):
        p=matrix@np.array([float(x),float(y),1.])
        return [p[0]*25.4/72,(float(page.mediabox.height)-p[1])*25.4/72]
    for operands,op in ContentStream(page.get_contents(),pdf).operations:
        if op==b"q": stack.append(matrix.copy())
        elif op==b"Q": matrix=stack.pop()
        elif op==b"cm":
            a,b,c,d,e,f=map(float,operands);matrix=matrix@np.array([[a,c,e],[b,d,f],[0,0,1]])
        elif op==b"m": points=[mapped(*operands)];closed=False
        elif op==b"l": points.append(mapped(*operands))
        elif op==b"h": closed=True
        elif op==b"S":
            if closed and len(points)>=3: page_closed.append(area(points))
            elif len(points)==2 and abs(points[0][1]-282)<1e-3 and abs(points[0][0]-10)<1e-3:
                page_calibrations.append(math.dist(*points))
        elif op==b"Tf": font_names.add(str(operands[0]))
    pdf_areas.append(sorted(page_closed));calibrations.append(page_calibrations)
    fonts=page["/Resources"]["/Font"]
    embedded=[name for name in font_names if fonts[name].get_object().get("/FontDescriptor") and fonts[name].get_object()["/FontDescriptor"].get_object().get("/FontFile2")]
    used_fonts.append({"used":sorted(font_names),"embedded":embedded})
    check("pdf-physical-page-and-no-images-"+str(len(pdf_areas)), abs(float(page.mediabox.width)*25.4/72-210)<1e-3 and abs(float(page.mediabox.height)*25.4/72-297)<1e-3 and not page["/Resources"].get("/XObject",{}))
check("pdf-independent-world-areas", len(pdf_areas)==2 and all(np.allclose(actual, expected,atol=.01,rtol=0) for actual,expected in zip(pdf_areas,[[225,3600],[468]])), pdf_areas)
check("pdf-calibration-and-unicode-font", all(len(c)==1 and abs(c[0]-100)<.01 for c in calibrations) and all(f["embedded"] for f in used_fonts) and all("Měřítko" in p.extract_text() for p in pdf.pages), {"calibrations_mm":calibrations,"fonts":used_fonts})
places=list(project["placements"].values())
check("saved-manual-layout-and-independent-locks", any(p["x_mm"]==60 and p["y_mm"]==50 and p["rotation_deg"]==30 and p["position_locked"] and p["rotation_locked"] for p in places) and any(p["x_mm"]==50 and p["y_mm"]==60 and p["rotation_deg"]==0 for p in places))
acks=report["digital_only_acknowledgements"]
check("only-explicit-digital-caveat-acknowledged", len(acks)==1 and acks[0]["code"]=="MATERIAL_CLEARANCE_UNVERIFIED" and project["acknowledgements"].get(acks[0]["id"])==acks[0]["digest"] and report["physical_build"]==report["new_user"]=="NOT_RUN")
native=[d for d in report["dialogs"] if "native_seen" in d]
check("three-real-native-path-observations", len(native)==3 and all(d["native_seen"] and d["accepted"] for d in native) and [d["title"] for d in native]==["Uložit model","Otevřít model","Vyberte složku pro SVG a PDF"])
result={"source_sha":args.sha,"run":str(run),"kind":"independent_XML_actual_PDF_and_saved_project_read_no_writer_helpers","results":results,"pass":sum(r["pass"] for r in results),"fail":sum(not r["pass"] for r in results)}
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(1 if result["fail"] else 0)
