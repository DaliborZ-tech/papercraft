"""Review archived native runs; exact lexical vector reader, no desktop replay."""

import hashlib
import io
import json
import math
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from fractions import Fraction as F
from pathlib import Path

from pypdf import PdfReader

from archpapercraft.authoring import load_project
from archpapercraft.authoring import project as module

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/p2/implementation/evidence"
PIN = "42dca6279f4fbabeb922f950a8480e305a7d8c55"
NATIVE_PIN = "696906954f3e6863a6c945a1afc0d62f9d60f769"
assert Path(module.__file__).resolve() == ROOT / "src/archpapercraft/authoring/project.py"
assert not subprocess.check_output(["git", "diff", "5415e2bc", PIN, "--", "src"])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record(path):
    return json.loads(path.read_text(encoding="utf-8"))


def polygon_area(points):
    return abs(sum(a[0] * b[1] - a[1] * b[0]
                   for a, b in zip(points, points[1:] + points[:1]))) / 2


def line_path(tokens, move="M", line="L", close="Z"):
    # The reviewed flattened bodies must remain a single four-line rectangle.
    assert len(tokens) == 13 and tokens[0] == move and tokens[-1] == close, tokens
    assert tokens[3] == tokens[6] == tokens[9] == line
    points = [(F(tokens[i + 1]), F(tokens[i + 2])) for i in (0, 3, 6, 9)]
    assert points[0] == (0, 0) and points[1][1] == 0
    assert points[2] == (points[1][0], F(10)) and points[3] == (0, F(10))
    return points


NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
MATRIX = re.compile(r"^(" + r"\s+".join([NUMBER] * 6) + r")\s+cm(?:\s|$)")


def pdf_body(reader, part_id):
    observed = []
    for page_index, page in enumerate(reader.pages):
        assert not page["/Resources"].get("/XObject")
        assert page.get("/UserUnit", 1) == 1 and page.get("/Rotate", 0) == 0
        matrix, stack, marks = tuple(map(F, (1, 0, 0, 1, 0, 0))), [], []
        pending = None
        # Read original decompressed numeric tokens. FloatObject conversion
        # would discard digits before this independent metric comparison.
        for raw_line in page.get_contents().get_data().decode("ascii").splitlines():
            text = raw_line.strip()
            if text == "q":
                stack.append(matrix)
            elif text == "Q":
                matrix = stack.pop()
            elif match := MATRIX.match(text):
                u, v, w, x, y, z = map(F, match[1].split())
                a, b, c, d, e, f = matrix
                matrix = (a*u+c*v, b*u+d*v, a*w+c*x, b*w+d*x, a*y+c*z+e, b*y+d*z+f)
            elif text.endswith(" BMC"):
                marks.append(text.split()[0])
            elif text == "EMC":
                marks.pop()
            elif f"/APPart_{part_id}" in marks and "/APRole_CUT" in marks:
                if text.startswith("n "):
                    tokens = text.split()[1:]
                    # PDF has postfix commands; convert exactly, retaining tokens.
                    assert tokens[-1] == "h" and len(tokens) == 13
                    prefix = []
                    for i in (0, 3, 6, 9):
                        prefix.extend([tokens[i + 2], tokens[i], tokens[i + 1]])
                    prefix.append("h")
                    pending = line_path(prefix, "m", "l", "h")
                elif text == "S":
                    assert pending is not None
                    a, b, c, d, _, _ = matrix
                    area_mm2 = polygon_area(pending) * abs(a*d-b*c) * F(127, 360)**2
                    observed.append((page_index, area_mm2, pending[1][0]))
                    pending = None
        assert not stack and not marks
    assert len(observed) == 1 and observed[0][0] == 1
    return observed[0][1:]


expected_sources = {}
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(
        ["git", "archive", NATIVE_PIN, "pyproject.toml", "src", "tools/authoring"]))) as archive:
    for member in archive:
        if member.isfile():
            raw = archive.extractfile(member).read().replace(b"\r\n", b"\n")
            expected_sources[member.name] = {sha(raw), sha(raw.replace(b"\n", b"\r\n"))}

results = {}
for kind, run in (("arc", "02"), ("cubic", "01")):
    directory = EVIDENCE / f"au13-{kind}-native-6969069-run{run}"
    log = record(directory / "results.json")
    assert log["status"] == "PASS_REQUESTED_FIXTURE" and not log["failures"]
    assert log["source_sha"] == NATIVE_PIN
    assert all(sha((directory / name).read_bytes()) == value
               for name, value in log["files_sha256"].items())
    assert all(value in expected_sources[name] for name, value in log["source_files_sha256"].items())
    assert len([d for d in log["dialogs"] if d.get("native_seen") and d.get("accepted")]) == 3
    body = directory / f"AU13-{kind}"
    path = body / f"AU13-{kind}.apcraft"
    raw = record(path)
    snapshot, manifest = record(body / "snapshot.json"), record(body / "export/.author-export.json")
    assert raw["schema_version"] == 9 and raw["scale"] == 0.01
    original_hash = sha(path.read_bytes())
    project = load_project(path)
    # The serialized contract uses JSON arrays; the in-memory topology proof
    # contains tuples. Normalize only the container representation explicitly.
    actual_snapshot = json.loads(json.dumps(project.snapshot(), allow_nan=False))
    assert not project.requires_save_as and actual_snapshot == snapshot
    assert sha(path.read_bytes()) == original_hash
    snapshot_digest = sha(json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8"))
    assert manifest["snapshot_digest"] == snapshot_digest
    loft = next(s for s in raw["surfaces"].values() if s["kind"] == "ruled_loft")
    part_id = loft["part_id"]
    assert raw["placements"][part_id]["x_mm"] == 55
    assert raw["placements"][part_id]["y_mm"] == 90
    assert raw["placements"][part_id]["rotation_deg"] == 17
    assert raw["placements"][part_id]["position_locked"] is True
    assert raw["placements"][part_id]["rotation_locked"] is True
    root_id = loft["params"]["correspondences"][0]["first_segment_id"]
    history = raw["profile_subdivisions"][root_id]["history"]
    split, merge = history["events"]
    assert split[0] == "split" and merge[0] == "merge" and merge[1] == split[3:5]
    active = raw["profiles"][loft["profile_id"]]["segments"][0]
    assert active["id"] == merge[2] and active["id"] not in [root_id, *split[3:5]]
    assert active["source_reference"]["source"] == history["source"]
    assert raw["parts"][part_id]["frame"]["axis_segment_id"] == root_id
    expected = 100 * math.pi if kind == "arc" else 800
    u = F(split[2])
    distance = 10 * math.pi * float(u) if kind == "arc" else float(80*u**3-120*u**2+120*u)
    assert abs(distance - (10 * math.pi / 3 if kind == "arc" else 20)) <= 0.0011
    svg_areas, widths, svg_ids = [], [], set()
    for svg in (body / "export").glob("*.svg"):
        doc = ET.parse(svg).getroot()
        assert doc.get("viewBox") == "0 0 210 297" and doc.get("width") == "210mm"
        assert doc.get("height") == "297mm" and doc.get("data-snapshot-digest") == snapshot_digest
        for group in doc:
            if group.get("data-part-id"):
                svg_ids.add(group.get("data-part-id"))
            if group.get("data-part-id") == part_id:
                assert group.get("transform") == "translate(55 90) rotate(17)"
                for role in group:
                    if role.get("data-role") == "CUT":
                        for node in role:
                            points = line_path(node.get("d").split())
                            svg_areas.append(polygon_area(points)); widths.append(points[1][0])
    assert len(svg_areas) == 1 and svg_ids == set(raw["parts"])
    pdf = PdfReader(body / "export/model.pdf")
    assert len(pdf.pages) == len(snapshot["pages"]) == 2
    assert snapshot_digest in pdf.metadata["/Subject"]
    pdf_area, pdf_width = pdf_body(pdf, part_id)
    for area in (svg_areas[0], pdf_area):
        assert abs(float(area) - expected) <= 0.01
    results[kind] = dict(
        native_results_sha256=sha((directory / "results.json").read_bytes()),
        original_project_sha256=original_hash, file_hashes_verified=len(log["files_sha256"]),
        native_source_hashes_bound_to_git=len(log["source_files_sha256"]),
        native_seconds=log["elapsed_seconds"], snapshot_matches_reopened_project=True,
        snapshot_digest=snapshot_digest, retired_root=root_id, current_piece=active["id"],
        expected_area_mm2=expected, svg_area_exact=str(svg_areas[0]), pdf_area_exact=str(pdf_area),
        svg_area_mm2=float(svg_areas[0]), pdf_area_mm2=float(pdf_area),
        svg_area_error_mm2=abs(float(svg_areas[0])-expected),
        pdf_area_error_mm2=abs(float(pdf_area)-expected),
        svg_width_original_token=str(widths[0]), pdf_width_original_token=str(pdf_width),
        independently_integrated_split_distance_paper_mm=distance,
    )

result = dict(reviewed_candidate=PIN, native_source=NATIVE_PIN, imported_project=module.__file__,
              results=results, scope="Independent review of archived actual native widget runs and files; no desktop replay",
              new_user="0/NOT_RUN", physical_P3="NOT_RUN", AC_AU19="NOT_RUN")
(EVIDENCE / "au13-native-artifact-review-42dca.json").write_text(
    json.dumps(result, indent=2)+"\n", encoding="utf-8")
print(json.dumps(result, indent=2))
