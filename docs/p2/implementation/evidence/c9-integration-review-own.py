"""Read final native/editor artifacts; never sends desktop input or writes source fixtures."""

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools/authoring"))

from circular_svg_oracle import svg_signed_area  # noqa: E402
from vector_curve_oracle import pdf_stroked_areas  # noqa: E402

from archpapercraft.authoring import load_project  # noqa: E402
from archpapercraft.authoring import project as project_module  # noqa: E402

assert Path(project_module.__file__).resolve() == ROOT / "src/archpapercraft/authoring/project.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text("utf-8"))


def unchanged_manifest(directory, values):
    assert all(sha(directory / file) == expected for file, expected in values.items())
    return len(values)


def expected_material(name):
    """Own fixed fixture dimensions; triangle area less the oriented circular segment."""
    r0, r1 = 10, 20 if name == "C-cone" else 10.00001 if name == "C-near" else 10
    # Cone depth entered through six model-mm decimals is 2828.427125 mm.
    height = 28.28427125 if name == "C-cone" else 30
    slant = math.hypot(r1 - r0, height)
    radius = r1 if name == "C-cone" else r0
    slope = (r0 - r1) / slant * (-1 if name == "C-cone" else 1)
    q = slope * 0.24 / (4 * radius)
    half_chord = 0.24 / (2 * (1 + q * q))
    sagitta = -slope * 0.24**2 / (8 * radius * (1 + q * q))
    angle = 4 * math.atan(abs(q))
    # No large-center subtraction and no theta - sin(theta) float cancellation.
    circular_segment = math.fsum(
        (-1) ** (n + 1) * angle ** (2 * n + 1) / math.factorial(2 * n + 1) for n in range(1, 12)
    )
    tab = half_chord * (9.5 - sagitta)
    if slope:
        tab -= math.copysign(1, slope) * (radius / slope) ** 2 * circular_segment / 2
    return math.pi * (r0 + r1) * slant + 11 * tab


spec = importlib.util.spec_from_file_location(
    "c9_review_editor_probe", ROOT / "tools/authoring/editor_probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
native_pin = "a5eedc9b3a345320b9ae07e9e44bc7387c5ef73b"
result = {
    "native_pin": native_pin,
    "import": str(project_module.__file__),
    "reviewed_candidate": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    "native": [],
    "editors": [],
    "historic_source_transfer": [],
    "no_desktop_input": True,
}
export_pages = set()

for directory in (
    EVIDENCE / "c-cylinder-qt150-a5eedc9-run02",
    EVIDENCE / "c-cone-native-a5eedc9-run01",
    EVIDENCE / "c-near-native-a5eedc9-run01",
):
    log = read(directory / "results.json")
    assert log["source_sha"] == native_pin and log["status"] == "PASS_REQUESTED_FIXTURE"
    assert not log["failures"] and not log.get("observed_command_exceptions")
    assert all(" docs/" in line for line in log["source_status_at_start"].splitlines())
    sources = unchanged_manifest(ROOT, log["source_files_sha256"])
    artifacts = unchanged_manifest(directory, log["files_sha256"])
    assert len([d for d in log["dialogs"] if d.get("native_seen") and d.get("accepted")]) == 3
    name = log["requested_fixture"]
    body = directory / name
    project_path = body / (name + ".apcraft")
    original = sha(project_path)
    project = load_project(project_path)
    snapshot = read(body / "snapshot.json")
    assert json.loads(json.dumps(project.snapshot(), allow_nan=False)) == snapshot
    assert not project.requires_save_as and sha(project_path) == original
    digest = hashlib.sha256(
        json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()
    assert read(body / "export/.author-export.json")["snapshot_digest"] == digest
    connector = next(iter(project.curved_connectors.values()))
    assert connector.tab_overrides[connector.slot_ids[0]]["enabled"] is False
    assert connector.tab_overrides[connector.slot_ids[1]]["tip_offset_mm"] == 0.01
    owner = project.part_for_surface(connector.owner_surface_id)
    placement = project.placements[owner]
    assert [placement.x_mm, placement.y_mm, placement.rotation_deg] == [55, 90, 17]
    assert placement.position_locked and placement.rotation_locked
    expected_step = next(
        s
        for s in log["steps"]
        if s["name"] == "C_independent_source_and_actual_vector_material_area"
    )
    expected = expected_material(name)
    assert abs(expected - expected_step["expected_union_mm2"]) < 1e-7
    pdf = PdfReader(body / "export/model.pdf")
    assert len(pdf.pages) == 2 and all(not p["/Resources"].get("/XObject") for p in pdf.pages)
    assert digest in pdf.metadata.subject
    svg_areas = []
    for svg in (body / "export").glob("*.svg"):
        export_pages.add(svg.resolve())
        root = ET.parse(svg).getroot()
        assert root.get("data-snapshot-digest") == digest
        for group in root:
            if group.get("data-part-id") == owner:
                role = next(n for n in group if n.get("data-role") == "CUT")
                assert len(role) == 1
                svg_areas.append(float(abs(svg_signed_area(role[0].get("d")))))
    pdf_areas = [value for page, value in pdf_stroked_areas(pdf) if page == 1]
    assert len(svg_areas) == len(pdf_areas) == 1
    assert abs(svg_areas[0] - expected) <= 0.01 and abs(pdf_areas[0] - expected) <= 0.01
    result["native"].append(
        dict(
            directory=directory.name,
            elapsed_seconds=log["elapsed_seconds"],
            source_hashes=sources,
            artifact_hashes=artifacts,
            snapshot_digest=digest,
            svg_area=svg_areas[0],
            pdf_area=pdf_areas[0],
            independent_analytic_expected_area=expected,
        )
    )

for report_file in EVIDENCE.glob("*/editor-results.json"):
    log = read(report_file)
    if log.get("source_sha") != native_pin:
        continue
    directory = report_file.parent
    assert log["status"] == "PASS"
    origin = Path(log["origin_source"])
    # Runtime paths name the root worktree. Resolve only the shared evidence suffix.
    origin = (
        EVIDENCE
        / origin.parent.parent.parent.name
        / origin.parent.parent.name
        / origin.parent.name
        / origin.name
    )
    assert origin.resolve() in export_pages
    assert log["script_sha256"] == sha(ROOT / "tools/authoring/editor_probe.py")
    assert log["curve_equivalence_helper_sha256"] == sha(
        ROOT / "tools/authoring/editor_curve_equivalence.py"
    )
    artifacts = unchanged_manifest(directory, log["files_sha256"])
    assert sha(origin) == sha(directory / "editor-original.svg")
    assert log["origin_bundle_preserved_after_run"] is True
    assert all(
        sha(origin.parent / file) == expected
        for file, expected in log["origin_bundle_sha256"].items()
    )
    before, after = (
        ET.parse(directory / file).getroot()
        for file in ("editor-original.svg", "editor-edited.svg")
    )
    frames = probe._part_frame_checks(before, after)
    originals = {p.get("id"): p.get("d") for p in before.findall(".//s:path[@id]", probe.NS)}
    finals = {p.get("id"): p.get("d") for p in after.findall(".//s:path[@id]", probe.NS)}
    assert originals.keys() <= finals.keys()
    for identity, value in originals.items():
        proof = probe._same_path(value, finals[identity])
        assert proof == log["curve_equivalence"][identity]
        assert Fraction(proof["max_position_bound_mm_exact"]) <= Fraction(1, 50000)
    for metrics in log["part_role_metric_totals"].values():
        assert Fraction(metrics["global_length_difference_bound_mm_exact"]) <= Fraction(1, 100)
        assert Fraction(metrics["net_area_difference_bound_mm2_exact"]) <= Fraction(1, 100)
    text_edit = log["native_gui_text_edit"]
    assert text_edit  # Exact actual saved label is independently compared below.
    before_text = {
        p.get("id"): "".join(p.itertext()) for p in before.findall(".//s:text", probe.NS)
    }
    after_text = {p.get("id"): "".join(p.itertext()) for p in after.findall(".//s:text", probe.NS)}
    changed_text = [key for key in before_text if before_text[key] != after_text[key]]
    assert len(changed_text) == 1
    assert (
        after_text[changed_text[0]] == "\u017dlu\u0165ou\u010dk\u00fd \u2013 vlastn\u00ed d\u00edl"
    )
    result["editors"].append(
        dict(
            directory=directory.name,
            artifacts=artifacts,
            compared_paths=len(originals),
            frames=len(frames),
            actual_saved_unicode=after_text[changed_text[0]],
        )
    )

assert len(result["native"]) == 3 and len(result["editors"]) == len(export_pages) == 6
for kind, run in (("arc", "02"), ("cubic", "01")):
    directory = EVIDENCE / f"au13-{kind}-native-6969069-run{run}"
    log = read(directory / "results.json")
    assert log["status"] == "PASS_REQUESTED_FIXTURE"
    artifacts = unchanged_manifest(directory, log["files_sha256"])
    body = directory / ("AU13-" + kind)
    path = body / ("AU13-" + kind + ".apcraft")
    before = sha(path)
    project = load_project(path)
    assert json.loads(json.dumps(project.snapshot(), allow_nan=False)) == read(
        body / "snapshot.json"
    )
    assert sha(path) == before
    result["historic_source_transfer"].append(
        dict(
            kind=kind,
            native_source=log["source_sha"],
            checked_artifacts=artifacts,
            current_snapshot_identical=True,
            new_native_run_claimed=False,
        )
    )
result["audit_diagnostics"] = [
    "Initial overly strict clean-tree guard encountered only earlier untracked docs evidence; "
    "actual runtime source hashes all matched.",
    "Own cone oracle initially used ideal sqrt800 instead of the actual six-decimal model-mm "
    "input2828.427125; entered depth is used without changing tolerances.",
]
(EVIDENCE / "c9-integration-review-f5-artifacts.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"native": len(result["native"]), "editor_pages": len(result["editors"])}))
