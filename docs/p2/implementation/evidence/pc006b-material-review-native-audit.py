"""Independent reading of the completed real native evidence and both vector formats."""

import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream

directory = Path(sys.argv[1]).resolve()
result = json.loads((directory / "results.json").read_text(encoding="utf8"))
cases = []


def record(name, condition, **details):
    cases.append(dict(name=name, pass_=bool(condition), **details))
    assert condition, (name, details)


def polygon_area(d):
    tokens = re.findall(r"[MLZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", d)
    assert not re.search(r"[ACHQVSTachqvst]", d), "This planar fixture expects actual line paths"
    total, points, index = 0.0, [], 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            total += (
                math.fsum(
                    a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])
                )
                / 2
            )
            points = []
        else:
            assert command in ("M", "L")
            points.append((float(tokens[index]), float(tokens[index + 1])))
            index += 2
    return abs(total)


def line_points(d):
    """Read equivalent SVG line/H/V syntax independently of application helpers."""
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", d)
    points, command, current, start, index = [], None, [0, 0], None, 0
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        assert command and command.upper() in ("M", "L", "H", "V", "Z")
        if command.upper() == "Z":
            current = start.copy()
            points.append(current.copy())
            command = None
            continue
        size = 1 if command.upper() in ("H", "V") else 2
        value = [float(v) for v in tokens[index : index + size]]
        index += size
        if command.upper() in ("M", "L"):
            current = [current[i] + value[i] if command.islower() else value[i] for i in range(2)]
        else:
            axis = 0 if command.upper() == "H" else 1
            current[axis] = current[axis] + value[0] if command.islower() else value[0]
        points.append(current.copy())
        if command.upper() == "M":
            start = current.copy()
            command = "l" if command.islower() else "L"
    return points


record("completed_native_flow", result["status"] == "PASS", pin=result["source_sha"])
record(
    "both_required_fixtures",
    all(
        result["fixture_status"][name] == "PASS_TECHNICAL_UI" for name in ("model-A", "mixed-part")
    ),
)
native_dialogs = [d for d in result["dialogs"] if "native_seen" in d]
record(
    "six_real_native_dialogs",
    len(native_dialogs) == 6 and all(d["native_seen"] and d["accepted"] for d in native_dialogs),
)
for relative, expected in result["files_sha256"].items():
    actual = hashlib.sha256((directory / relative).read_bytes()).hexdigest()
    assert actual == expected, relative
record("artifact_hashes_independently_read", True, count=len(result["files_sha256"]))
worktree = Path(__file__).resolve().parents[4]
for relative, expected in result["source_files_sha256"].items():
    assert hashlib.sha256((worktree / relative).read_bytes()).hexdigest() == expected, relative
record(
    "actual_source_files_match_pinned_native_run", True, count=len(result["source_files_sha256"])
)
record(
    "actual_import_bound_to_reviewed_worktree",
    Path(result["actual_application_module"]).resolve()
    == (worktree / "src/archpapercraft/ui/author_window.py").resolve(),
)

ns = "{http://www.w3.org/2000/svg}"
for name, page_count, part_count in (("model-A", 3, 9), ("mixed-part", 2, 2)):
    folder = directory / name
    project = json.loads((folder / f"{name}.apcraft").read_text(encoding="utf8"))
    snapshot = json.loads((folder / "snapshot.json").read_text(encoding="utf8"))
    export = folder / "export"
    manifest = json.loads((export / ".author-export.json").read_text(encoding="utf8"))
    checks = snapshot["construction_checks"]
    canonical = json.dumps(checks, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf8")).hexdigest()
    pdf = PdfReader(export / "model.pdf")
    record(
        name + "_counts",
        len(project["parts"]) == part_count
        and len(list(export.glob("*.svg"))) == len(pdf.pages) == page_count,
    )
    record(
        name + "_metadata_matches_manifest",
        checks == manifest["construction_checks"]
        and json.loads(pdf.metadata["/Keywords"])["construction_checks_digest"] == digest,
    )
    svg_parts, source_south_area, source_tab_areas = set(), None, []
    south = next(
        (s["part_id"] for s in project["surfaces"].values() if s["name"] == "South wall"), None
    )
    for svg in export.glob("*.svg"):
        root = ET.parse(svg).getroot()
        record(
            name + "_svg_report_" + svg.stem,
            root.attrib["data-construction-checks-digest"] == digest
            and json.loads(root.find(ns + "metadata[@id='construction-checks']").text) == checks,
        )
        for group in root.findall(ns + "g"):
            if "data-part-id" not in group.attrib:
                continue
            svg_parts.add(group.attrib["data-part-id"])
            roles = {r.attrib["data-role"] for r in group.findall(ns + "g")}
            assert roles == {
                "CUT",
                "FOLD_MOUNTAIN",
                "FOLD_VALLEY",
                "TABS",
                "GUIDES",
                "LABELS",
                "ARTWORK",
            }
            if group.attrib["data-part-id"] == south:
                source_south_area = sum(
                    polygon_area(p.attrib["d"])
                    for role in group.findall(ns + "g")
                    if role.attrib["data-role"] == "CUT"
                    for p in role.findall(ns + "path")
                )
                source_tab_areas = sorted(
                    polygon_area(p.attrib["d"])
                    for role in group.findall(ns + "g")
                    if role.attrib["data-role"] == "TABS"
                    for p in role.findall(ns + "path")
                )
        for text in root.iter(ns + "text"):
            assert text.attrib.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
    record(name + "_complete_role_material_coverage", svg_parts == set(project["parts"]))
    for page in pdf.pages:
        assert not page["/Resources"].get("/XObject")
        ops = ContentStream(page.get_contents(), pdf).operations
        assert any(op == b"l" for _, op in ops)
    record(name + "_pdf_vector_paths_no_raster", True)
    if south:
        record(
            "A_independent_actual_CUT_area",
            abs(source_south_area - 4320) < 0.01,
            actual=source_south_area,
            expected="100*40 + 56 + 60 + 60 + 144",
        )
        record(
            "A_independent_actual_tab_areas",
            len(source_tab_areas) == 4
            and all(abs(a - b) < 0.01 for a, b in zip(source_tab_areas, [56, 60, 60, 144])),
            actual=source_tab_areas,
        )

if len(sys.argv) > 2:
    editor_folder = Path(sys.argv[2]).resolve()
    editor = json.loads((editor_folder / "editor-results.json").read_text(encoding="utf8"))
    record(
        "editor_exact_same_source",
        editor["status"] == "PASS" and editor["source_sha"] == result["source_sha"],
    )
    for name, expected in editor["origin_bundle_sha256"].items():
        assert (
            hashlib.sha256((Path(editor["origin_source"]).parent / name).read_bytes()).hexdigest()
            == expected
        )
    record("editor_origin_bundle_preserved", True)
    for name, expected in editor["files_sha256"].items():
        assert hashlib.sha256((editor_folder / name).read_bytes()).hexdigest() == expected
    record("editor_artifacts_match_recorded_hashes", True)
    original = ET.parse(editor_folder / "editor-original.svg").getroot()
    edited = ET.parse(editor_folder / "editor-edited.svg").getroot()
    old_nodes = {node.attrib["id"]: node for node in original.iter() if "id" in node.attrib}
    new_nodes = {node.attrib["id"]: node for node in edited.iter() if "id" in node.attrib}
    lid = editor["actual_inkscape_action_edits"]["label_id"]
    record(
        "editor_actual_saved_unicode_and_spaces",
        "".join(new_nodes[lid].itertext()) == "Žluťoučký – vlastní díl",
    )
    record(
        "editor_other_text_objects_preserved",
        all(
            "".join(node.itertext()) == "".join(new_nodes[identity].itertext())
            for identity, node in old_nodes.items()
            if node.tag == ns + "text" and identity != lid
        ),
    )
    paths = [node for node in original.iter(ns + "path") if "id" in node.attrib]
    for path in paths:
        a = line_points(path.attrib["d"])
        b = line_points(new_nodes[path.attrib["id"]].attrib["d"])
        assert len(a) == len(b) and all(math.dist(x, y) < 0.00002 for x, y in zip(a, b))
    record("editor_path_local_coordinates_preserved", True, count=len(paths))
    record(
        "editor_A4_page_and_calibration_preserved",
        original.attrib["width"] == edited.attrib["width"]
        and original.attrib["height"] == edited.attrib["height"]
        and original.attrib["viewBox"] == edited.attrib["viewBox"],
    )

output = dict(status="PASS", source_sha=result["source_sha"], cases=cases)
Path(__file__).with_suffix(".json").write_text(json.dumps(output, indent=2), encoding="utf8")
print("PASS", len(cases), "independent native/export checks")
