"""Independent consumer/composer review; excludes author's transfer-math claim."""

import copy
import hashlib
import json
import math
import re
import shutil
from fractions import Fraction as Q
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from pypdf import PdfReader

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.curved_connectors import _prepare_native_slots, _scene_clearance
from archpapercraft.exporter import author_export
from archpapercraft.exporter.curve_output_validation import CurveOutputError, read_pdf_cut_regions
from archpapercraft.exporter.loft_output_validation import (
    validate_loft_snapshot,
    validate_loft_vector_outputs,
)

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/p2/implementation/evidence"


def circle(p, r, z=0):
    xy = [(r, 0), (0, r), (-r, 0), (0, -r), (r, 0)]
    return p.add_profile(
        segments=[
            {"kind": "arc", "start": a, "end": b, "data": {"center": [0, 0], "sweep_deg": 90}}
            for a, b in zip(xy, xy[1:])
        ],
        closed=True,
        plane={"origin": [0, 0, z], "u": [1, 0, 0], "v": [0, 1, 0]},
    )


def model(*, r1=10, h=30, side="first", reverse=False, pose=False, hole=None):
    p = AuthorProject.new(scale=1)
    a, b = circle(p, 10), circle(p, r1, h)
    pairs = list(zip(p.profiles[a].segments, p.profiles[b].segments))
    if reverse:
        pairs.reverse()
    refs = [
        {
            "first_segment_id": x.id,
            "second_segment_id": y.id,
            "first_interval": [1, 0] if reverse else [0, 1],
            "second_interval": [1, 0] if reverse else [0, 1],
        }
        for x, y in pairs
    ]
    owner = p.add_loft(a, b, correspondences=refs)
    receiver_profile = circle(p, 10 if side == "first" else r1, 0 if side == "first" else h)
    holes = [circle(p, hole, 0 if side == "first" else h)] if hole else []
    receiver = p.add_surface(receiver_profile, holes)
    if pose:
        for sid in (owner, receiver):
            p.set_transform(sid, [107, -31, 59], [17, 23, -41])
    receiver_side = (
        ("inside" if h > 0 else "outside")
        if side == "first"
        else ("outside" if h > 0 else "inside")
    )
    cid = p.add_curved_connector(
        owner,
        side,
        receiver,
        receiver_side=receiver_side,
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
    )
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.recompute()
    return p, owner, receiver, cid


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def cubic_green(points):
    # Integrate exact power polynomials from the SERIALIZED PDF operands.
    # This does not call curve_area/native-area or the production PDF reader.
    axes = []
    for p0, p1, p2, p3 in zip(*points):
        axes.append((p0, 3 * (p1 - p0), 3 * (p0 - 2 * p1 + p2), -p0 + 3 * p1 - 3 * p2 + p3))
    x, y = axes
    return (
        sum((x[i] * j * y[j] - y[i] * j * x[j]) / Q(i + j) for i in range(4) for j in range(1, 4))
        / 2
    )


def raw_pdf_cut_areas(path):
    areas = {}
    num = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
    tokens = re.compile(num + r"|[A-Za-z*]+")
    for page in PdfReader(path).pages:
        det, stack, pid, role, total, current, start = Q(1), [], None, None, Q(0), None, None
        for raw in page.get_contents().get_data().splitlines():
            line = raw.decode("ascii", errors="strict").strip()
            if line.startswith("/APPart_") and line.endswith(" BMC"):
                pid = line[len("/APPart_") : -4]
            elif line.startswith("/APRole_") and line.endswith(" BMC"):
                role = line[len("/APRole_") : -4]
            elif line == "EMC":
                if role is not None:
                    role = None
                else:
                    pid = None
            elif line == "q":
                stack.append(det)
            elif line == "Q":
                det = stack.pop()
            elif line.endswith(" cm"):
                values = line[:-3].split()
                if len(values) == 6:
                    a, b, c, d, _, _ = map(Q, values)
                    det *= a * d - b * c
            elif role == "CUT":
                operands = []
                for token in tokens.findall(line):
                    if re.fullmatch(num, token):
                        operands.append(Q(token))
                        continue
                    if token == "n":
                        total, current, start = Q(0), None, None
                    elif token == "m":
                        current = start = tuple(operands)
                    elif token == "l":
                        end = tuple(operands)
                        total += cross(current, end) / 2
                        current = end
                    elif token == "c":
                        control = [
                            current,
                            tuple(operands[:2]),
                            tuple(operands[2:4]),
                            tuple(operands[4:]),
                        ]
                        total += cubic_green(control)
                        current = control[-1]
                    elif token == "h":
                        total += cross(current, start) / 2
                        current = start
                    elif token in ("S", "s"):
                        assert current == start
                        areas[pid] = abs(total * det) * Q(127, 360) ** 2
                    operands = []
    return areas


@pytest.mark.parametrize(
    "name", ["cylinder-first", "cone-first", "cone-second", "near-cylinder-first"]
)
def test_pinned_actual_pdf_green_area_and_native_svg_roles_against_analytic_source(name):
    directory = EVIDENCE / "pc007b-circular-material-67c44ae-run01" / name
    snapshot = json.loads((directory / "snapshot.json").read_text(encoding="utf-8"))
    report = next(iter(snapshot["construction_checks"]["lofts"].values()))
    pid = (
        report["part_id"]
        if "part_id" in report
        else next(
            part["id"]
            for page in snapshot["pages"]
            for part in page["parts"]
            if part["surface_ids"] == [report["feature_id"]]
        )
    )
    r0, r1, height = (
        (10, 10, 30)
        if name.startswith("cylinder")
        else ((10, 10.000001, 30) if name.startswith("near") else (10, 20, math.sqrt(800)))
    )
    body = math.pi * (r0 + r1) * math.hypot(r1 - r0, height)
    # Reference source area: straight-apex triangle less/plus circular segment.
    side = "second" if name == "cone-second" else "first"
    r = r0 if side == "first" else r1
    k = (r1 - r0) / math.hypot(r1 - r0, height) * (1 if side == "second" else -1)
    q = k * 0.24 / (4 * r)
    xe, fe = 0.12 / (1 + q * q), -k * 0.24**2 / (8 * r) / (1 + q * q)
    omega = 4 * math.atan(abs(q))
    segment = 0 if not k else (r / k) ** 2 * (omega - math.sin(omega)) / 2
    tab_area = xe * (9.5 - fe) - math.copysign(segment, k) if k else 0.24 * 9.5 / 2
    actual = raw_pdf_cut_areas(directory / "vectors/model.pdf")[pid]
    assert abs(float(actual) - (body + 12 * tab_area)) < 0.01
    for svg in (directory / "vectors").glob("*.svg"):
        root = ET.parse(svg).getroot()
        group = next((node for node in root if node.get("data-part-id") == pid), None)
        if group is None:
            continue
        roles = {node.get("data-role"): node for node in group}
        assert len(roles["GUIDES"]) == len(roles["TABS"]) == 12
        cut = roles["CUT"][0].get("d")
        assert "C" not in cut
        if not name.startswith("cylinder"):
            assert "A" in cut


def test_all_pinned_artifact_hashes_and_raw_media_boxes():
    for run in ("pc007b-circular-material-67c44ae-run01", "pc007b-domain-511805c-run01"):
        root = EVIDENCE / run
        manifest = json.loads((root / "results.json").read_text(encoding="utf-8"))
        for path, binding in manifest["files"].items():
            raw = (root / path).read_bytes()
            assert len(raw) == binding["bytes"]
            assert hashlib.sha256(raw).hexdigest() == binding["sha256"]
        for pdf in root.rglob("*.pdf"):
            boxes = re.findall(rb"/MediaBox\s*\[([^]]+)\]", pdf.read_bytes())
            assert boxes
            for box in boxes:
                a, b, x, y = [Q(value.decode()) for value in box.split()]
                assert (a, b) == (0, 0)
                assert abs(x * Q(127, 360) - 210) < Q(1, 10**11)
                assert abs(y * Q(127, 360) - 297) < Q(1, 10**11)


@pytest.mark.parametrize(
    "r1,h,side,reverse,pose",
    [
        (10, 30, "first", False, False),
        (20, math.sqrt(800), "second", True, True),
        (20, -math.sqrt(800), "first", False, True),
        (10.000001, 30, "first", True, False),
    ],
)
def test_fresh_native_material_exact_side_edges_ids_and_source_scope(r1, h, side, reverse, pose):
    p, owner, _, cid = model(r1=r1, h=h, side=side, reverse=reverse, pose=pose)
    assert p.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE"
    part = p.parts[p.part_for_surface(owner)]
    assert part.paths["FOLD_MOUNTAIN"] == part.paths["FOLD_VALLEY"] == []
    packet = _prepare_native_slots(p, p.curved_connectors[cid])
    current, cuts = None, []
    for cmd in part.paths["CUT"][0]["commands"]:
        if cmd[0] in ("M", "L", "A"):
            end = tuple(cmd[-2:])
            if current is not None and cmd[0] != "M":
                cuts.append((current, end, cmd[0]))
            current = end
    assert len(packet["slots"]) == 12
    assert {slot["tab_id"] for slot in packet["slots"]} == set(p.curved_connectors[cid].slot_ids)
    for slot in packet["slots"]:
        guide = slot["paper_shared_base_commands"]
        a, b, apex = tuple(guide[0][-2:]), tuple(guide[1][-2:]), tuple(slot["paper_apex"])
        assert sum({start, end} == {a, apex} and op == "L" for start, end, op in cuts) == 1
        assert sum({start, end} == {b, apex} and op == "L" for start, end, op in cuts) == 1
        assert not any({start, end} == {a, b} for start, end, _ in cuts)
    material = p.curved_connector_material_report(owner)
    assert material["source_native_strain"]["status"] == "SOURCE_NATIVE_STRAIN_CERTIFIED"
    assert material["source_native_strain"]["pdf_cubic_deformation"] == "NOT_CLAIMED"


def test_pool_shrink_off_custom_reopen_and_transaction_rejection(tmp_path):
    p, owner, _, cid = model()
    ids = p.curved_connectors[cid].slot_ids[:]
    p.set_curved_tab(cid, ids[8], tip_offset_mm=0.01, enabled=False)
    p.update_curved_connector(cid, count=6)
    p.recompute()
    path = tmp_path / "pool.apcraft"
    p.save(path)
    before = path.read_bytes()
    p = load_project(path)
    p.update_curved_connector(cid, count=12)
    assert p.curved_connectors[cid].slot_ids == ids
    assert p.curved_connectors[cid].tab_overrides[ids[8]] == {
        "enabled": False,
        "tip_offset_mm": 0.01,
    }
    p.recompute()
    assert len(p.parts[p.part_for_surface(owner)].paths["TABS"]) == 11
    unchanged = p.to_dict()
    with pytest.raises(ValidationError):
        p.update_curved_connector(cid, count=0)
    assert p.to_dict() == unchanged
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", ["hole", "pose", "source", "cache"])
def test_current_source_or_cache_fault_is_not_hidden_by_same_ids_or_revision(kind):
    p, owner, receiver, cid = model()
    if kind == "cache":
        p.curved_connectors[cid].certificate["status"] = "CLEAR"
    elif kind == "pose":
        p.surfaces[receiver].position_mm[0] = 0.00001
    elif kind == "source":
        profile = p.profiles[p.surfaces[owner].profile_id]
        profile.segments[0].data["sweep_deg"] = 89.999999999
    else:
        hole = circle(p, 9.8)
        p.surfaces[receiver].hole_profile_ids.append(hole)
    assert p.curved_connector_status(cid)["status"] != "CERTIFIED_APPROXIMATE"
    with pytest.raises(ValidationError):
        p.snapshot()


def test_cubic_foreign_material_uses_whole_control_hull_and_source_key():
    p, owner, _, cid = model()
    old = _prepare_native_slots(p, p.curved_connectors[cid])
    profile = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [200, 0],
                "end": [200, 1],
                "data": {"control1": [-100, 0], "control2": [-100, 1]},
            },
            {"kind": "line", "start": [200, 1], "end": [201, 1]},
            {"kind": "line", "start": [201, 1], "end": [201, 0]},
            {"kind": "line", "start": [201, 0], "end": [200, 0]},
        ],
        plane={"origin": [0, 0, 0], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    foreign = p.add_surface(profile)
    with pytest.raises(ValidationError):
        _scene_clearance(p, p.curved_connectors[cid], old)
    current = _scene_clearance(
        p, p.curved_connectors[cid], _prepare_native_slots(p, p.curved_connectors[cid])
    )
    assert current["status"] == "UNRESOLVED"
    assert foreign in current["unresolved_obstacle_ids"]
    row = next(row for row in current["checked"] if row["id"] == foreign)
    assert Q(row["bounds_exact"][0][0]) < -99


@pytest.mark.parametrize("damage", ["omit-source", "move-foreign", "same-area-cut"])
def test_full_snapshot_replay_rejects_complete_context_forgery(damage):
    root = EVIDENCE / "pc007b-domain-511805c-run01"
    snapshot = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    result = json.loads((root / "results.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(snapshot)
    if damage == "omit-source":
        bad["construction_checks"].pop("curved_source_project")
    elif damage == "move-foreign":
        bad["construction_checks"]["curved_source_project"]["surfaces"][
            result["foreign_surface_id"]
        ]["position_mm"][2] -= 100
    else:
        part = next(
            part
            for page in bad["pages"]
            for part in page["parts"]
            if part["id"] == result["part_id"]
        )
        for cmd in part["paths"]["CUT"][0]["commands"]:
            if cmd[0] in ("M", "L", "A"):
                cmd[-2] += 0.001
    with pytest.raises(CurveOutputError):
        validate_loft_snapshot(bad)


def test_raw_reader_retains_strict_role_contract_on_actual_artifact():
    pdf = EVIDENCE / "pc007b-domain-511805c-run01/vectors/model.pdf"
    for role, closed in (("CUT", False), ("TABS", False), ("BOGUS", True)):
        with pytest.raises(CurveOutputError):
            read_pdf_cut_regions(pdf, role=role, require_closed=closed)
    guides = read_pdf_cut_regions(pdf, role="GUIDES", require_closed=False)
    assert sum(len(part["loops"]) for part in guides["parts"].values()) == 11


def test_large_body_area_budget_excludes_tabs_and_atomic_bundle_is_retained(tmp_path, monkeypatch):
    # Independent numerical comparator: body=20000*pi, tabs=12*1.14. The fault
    # is halfway BETWEEN body-only and body+tabs relative thresholds.
    p = AuthorProject.new(scale=1)
    a, b = circle(p, 100), circle(p, 100, 100)
    owner = p.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": x.id,
                "second_segment_id": y.id,
                "first_interval": [0, 1],
                "second_interval": [0, 1],
            }
            for x, y in zip(p.profiles[a].segments, p.profiles[b].segments)
        ],
    )
    receiver = p.add_surface(circle(p, 100))
    p.add_curved_connector(
        owner, "first", receiver, receiver_side="inside", nominal_base_mm=0.24, min_glue_area_mm2=1
    )
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.recompute()
    pid = p.part_for_surface(owner)
    for page in p.pages:
        page.width_mm, page.height_mm = 800, 500
    second = p.add_page()
    p.pages[-1].width_mm, p.pages[-1].height_mm = 800, 500
    p.set_placement(pid, p.pages[0].id, 70, 200)
    p.set_placement(p.part_for_surface(receiver), second, 200, 200)
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    snapshot = p.snapshot()
    bundle = tmp_path / "bundle"
    author_export.export_all(snapshot, bundle)
    before = {path.name: path.read_bytes() for path in bundle.iterdir()}
    body_area, tabs_area = 20000 * math.pi, 12 * 0.24 * 9.5 / 2
    requested_error = (body_area + tabs_area / 2) / 1e6
    assert body_area / 1e6 < requested_error < (body_area + tabs_area) / 1e6
    move = requested_error / (200 * math.pi)
    original = author_export._svg

    def changed(*args, **kwargs):
        original(*args, **kwargs)
        path = args[4]
        tree = ET.parse(path)
        for group in tree.getroot():
            if group.get("data-part-id") != pid:
                continue
            role = next(node for node in group if node.get("data-role") == "CUT")
            tokens = role[0].get("d").split()
            i = 0
            while i < len(tokens):
                opcode = tokens[i]
                size = {"M": 2, "L": 2, "A": 7, "C": 6, "Z": 0}[opcode]
                if opcode in ("M", "L") and abs(float(tokens[i + 2]) + 100) < 1e-8:
                    tokens[i + 2] = repr(float(tokens[i + 2]) - move)
                i += size + 1
            role[0].set("d", " ".join(tokens))
        tree.write(path, encoding="utf-8", xml_declaration=True)

    monkeypatch.setattr(author_export, "_svg", changed)
    with pytest.raises(CurveOutputError, match="plocha|ploch"):
        author_export.export_all(snapshot, bundle)
    assert {path.name: path.read_bytes() for path in bundle.iterdir()} == before
    assert not list(bundle.glob(".author-export-*"))


@pytest.mark.parametrize("damage", ["omitted", "extra", "reversed", "moved", "ctm", "cross-role"])
def test_valid_utf8_actual_svg_guide_damage_is_geometry_fault_not_xml_parse(tmp_path, damage):
    run = EVIDENCE / "pc007b-domain-511805c-run01"
    snapshot = json.loads((run / "snapshot.json").read_text(encoding="utf-8"))
    data = json.loads((run / "results.json").read_text(encoding="utf-8"))
    expected = author_export._curve_output_expectations(snapshot)
    paths = []
    for page in snapshot["pages"]:
        name = f"page-{page['id']}.svg"
        target = tmp_path / name
        shutil.copy2(run / "vectors" / name, target)
        paths.append(target)
        tree = ET.parse(target)
        group = next(
            (node for node in tree.getroot() if node.get("data-part-id") == data["part_id"]), None
        )
        if group is None:
            continue
        guide = next(node for node in group if node.get("data-role") == "GUIDES")
        if damage == "omitted":
            guide.remove(guide[0])
        elif damage == "extra":
            extra = copy.deepcopy(guide[0])
            extra.set("id", extra.get("id") + "-extra")
            guide.append(extra)
        elif damage == "ctm":
            guide.set("transform", "translate(0.0001 0)")
        elif damage == "cross-role":
            guide.set("data-role", "ARTWORK")
        else:
            words = guide[0].get("d").split()
            assert words[0] == "M" and words[3] == "L"
            a, b = words[1:3], words[4:6]
            if damage == "reversed":
                a, b = b, a
            else:
                a = [str(float(a[0]) + 0.0001), a[1]]
                b = [str(float(b[0]) + 0.0001), b[1]]
            guide[0].set("d", "M " + " ".join(a) + " L " + " ".join(b))
        tree.write(target, encoding="utf-8", xml_declaration=True)
        ET.parse(target)  # Qualify the mutation BEFORE exercising product guards.
    with pytest.raises(CurveOutputError) as caught:
        validate_loft_vector_outputs(
            snapshot, paths, run / "vectors/model.pdf", expected_parts=expected
        )
    assert "not well-formed" not in str(caught.value)


def test_pdf_guide_inner_control_fault_is_not_hidden_by_unchanged_endpoints(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    p, sid, receiver, _ = model(r1=20, h=math.sqrt(800))
    pid = p.part_for_surface(sid)
    second = p.add_page()
    p.set_placement(pid, p.pages[0].id, 70, 100, 17)
    p.set_placement(p.part_for_surface(receiver), second, 70, 100, 11)
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    snapshot = p.snapshot()
    run = tmp_path / "fresh"
    author_export.export_all(snapshot, run)
    reader, writer = PdfReader(run / "model.pdf"), PdfWriter()
    changed = False
    for page in reader.pages:
        raw = page.get_contents().get_data()
        if f"/APPart_{pid} BMC".encode() in raw:
            before, tail = raw.split(b"/APRole_GUIDES BMC", 1)
            guide, after = tail.split(b"EMC", 1)
            # The endpoint and both other control operands remain byte-exact.
            pattern = rb"([-+0-9.]+) ([-+0-9.]+) ([-+0-9.]+) ([-+0-9.]+) ([-+0-9.]+) ([-+0-9.]+) c"
            match = re.search(pattern, guide)
            assert match
            first = float(match[1]) + 0.001
            replacement = repr(first).encode() + b" " + b" ".join(match.groups()[1:]) + b" c"
            guide = guide[: match.start()] + replacement + guide[match.end() :]
            stream = DecodedStreamObject()
            stream.set_data(before + b"/APRole_GUIDES BMC" + guide + b"EMC" + after)
            page[NameObject("/Contents")] = stream
            changed = True
        writer.add_page(page)
    assert changed
    pdf = tmp_path / "control.pdf"
    with pdf.open("wb") as handle:
        writer.write(handle)
    # The low-level role reader accepts a well-formed geometric cubic chain.
    read_pdf_cut_regions(pdf, role="GUIDES", require_closed=False)
    paths = [run / f"page-{page['id']}.svg" for page in snapshot["pages"]]
    with pytest.raises(CurveOutputError, match="tištěný GUIDES"):
        validate_loft_vector_outputs(
            snapshot, paths, pdf, expected_parts=author_export._curve_output_expectations(snapshot)
        )


@pytest.mark.parametrize("known", [False, True])
def test_actual_receiver_void_negative_stays_in_proof_beside_material_uncertainty(known):
    p, owner, _, cid = model(hole=9.8)
    if not known:
        p.set_material_profile(thickness_mm=None)
        p.recompute()
    material = p.curved_connector_material_report(owner)
    check = material["domain_connector_checks"][cid]
    # Independent geometry: final glue radii lie between .5 and <9.401;
    # the actual cap hole radius9.8 covers all of it, not just its centroid.
    assert check["source_transfer"]["native_status"] == "INVALID"
    assert any(
        "receiver lacks" in problem[2] for problem in check["source_transfer"]["native_problems"]
    )
    assert material["domain_status"] != "CERTIFIED_APPROXIMATE"
    assert p.curved_connector_status(cid)["status"] != "CERTIFIED_APPROXIMATE"
    with pytest.raises(ValidationError):
        p.snapshot()
