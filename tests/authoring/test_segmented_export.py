"""Independent actual-file D coverage, metric, source-closure and rollback."""

import copy
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from archpapercraft.authoring import load_project
from archpapercraft.exporter import author_export
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.segmented_output_validation import (
    _canonical_snapshot,
    validate_segmented_snapshot,
)

NS = "{http://www.w3.org/2000/svg}"
ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module", params=["line", "curved"])
def source(request):
    relative = {
        "line": "pc008-domain-95fa2c7/backend-fixture.apcraft",
        "curved": "pc008-curved-domain-518b91a/raw/gothic-backend.apcraft",
    }[request.param]
    p = load_project(ROOT / "docs/p2/implementation/evidence" / relative)
    return request.param, p.to_dict()


def project(source):
    from archpapercraft.authoring import AuthorProject

    return AuthorProject.from_dict(copy.deepcopy(source[1]))


@pytest.fixture(scope="module")
def bundle(source, tmp_path_factory):
    p = project(source)
    snapshot = p.snapshot()
    directory = tmp_path_factory.mktemp("segmented-export") / "bundle"
    author_export.export_all(snapshot, directory)
    return snapshot, directory


def hashes(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}


def test_line_and_curved_variants_without_planar_curve_registry_get_actual_guards(source, bundle):
    snapshot, directory = bundle
    assert snapshot["construction_checks"]["curve_profiles"] == {}
    manifest = json.loads((directory / ".author-export.json").read_text(encoding="utf8"))
    checks = manifest["actual_curve_output_checks"]
    assert checks["pdf"]["status"] == "VALID"
    result = checks["segmented_variants"]
    assert result["status"] == "VERIFIED"
    assert len(result["parts"]) == (64 if source[0] == "line" else 96)
    assert "NOT_EXACT_SMOOTH_TARGET_AREA" in result["area_scope"]
    # Independent bilinear S=(40u,20uv,30v), regular source grid8x4.
    # The first material triangle [0,0],[5,0],[5,20/32,30/4]
    # has area |[5,0,0]×[5,.625,7.5]|/2, not its XY projected area.
    first_pid = snapshot["pages"][0]["parts"][0]["id"]
    if source[0] == "line":
        expected = (5 * 5 * (0.625 * 0.625 + 7.5 * 7.5)) ** 0.5 / 2
        assert float(Fraction(result["parts"][first_pid]["source_material_area_exact"][0])) == (
            pytest.approx(expected)
        )
    for record in result["parts"].values():
        for actual in record["outputs"].values():
            assert Fraction(actual["source_material_to_actual_area_error_bound_exact"]) <= Fraction(
                record["allowed_material_area_error_exact"]
            )
            assert Fraction(
                actual["source_material_to_actual_position_error_bound_exact"]
            ) <= Fraction(1, 100)
            assert Fraction(
                actual["original_target_to_actual_position_error_bound_exact"]
            ) <= Fraction(1, 4)
    modes = json.loads(PdfReader(directory / "model.pdf").metadata["/Keywords"])[
        "segmented_variant_modes"
    ]
    assert set(modes.values()) == {"APPROXIMATE"}
    for path in directory.glob("*.svg"):
        root = ET.parse(path).getroot()
        groups = root.findall(f"{NS}g[@data-part-id]")
        assert all(g.get("data-flattening-mode") == "APPROXIMATE" for g in groups)
        assert all(g.get("data-segmented-triangle-id") for g in groups)


@pytest.mark.parametrize(
    "mutation",
    ["cut", "frame", "surface", "registry", "report", "reference", "missing", "status", "budget"],
)
def test_authoritative_source_closure_rejects_snapshot_or_material_substitution(source, mutation):
    data = project(source).snapshot()
    part = data["pages"][0]["parts"][0]
    report = next(iter(data["construction_checks"]["segmented_variants"].values()))
    if mutation == "cut":
        # Translation preserves net area and topology; source position still changed.
        for point in part["paths"]["CUT"][0]["points"]:
            point[0] += 0.1
    elif mutation == "frame":
        part["flattening"]["triangle_id"] = data["project_id"]
    elif mutation == "surface":
        part["surface_ids"] = data["coverage"]["reference_surface_ids"]
    elif mutation == "registry":
        data["coverage"]["expected_segmented_variant_ids"] = []
    elif mutation == "report":
        report["certificate"]["math"]["max_surface_deviation_paper_mm"] = 0
    elif mutation == "reference":
        data["coverage"]["reference_surface_ids"].append(part["surface_ids"][0])
    elif mutation == "missing":
        del data["construction_checks"]["segmented_source_project"]
    elif mutation == "status":
        report["status"] = "STALE"
    else:
        data["construction_checks"]["segmented_source_project"]["segmented_variants"][
            part["flattening"]["variant_id"]
        ]["parameters"]["max_deviation_mm"] = 0.01
    with pytest.raises(CurveOutputError):
        validate_segmented_snapshot(data)


def test_cache_uses_complete_source_content_and_keeps_detached_return_values(source):
    snapshot = project(source).snapshot()
    _canonical_snapshot.cache_clear()
    first = validate_segmented_snapshot(snapshot)
    assert _canonical_snapshot.cache_info().misses == 1
    first[next(iter(first))]["part"]["paths"]["CUT"][0]["points"][0][0] += 0.1
    # Caller mutations cannot contaminate the cached canonical source replay.
    with pytest.raises(CurveOutputError):
        validate_segmented_snapshot(snapshot)
    fresh = project(source).snapshot()
    assert validate_segmented_snapshot(fresh)
    assert _canonical_snapshot.cache_info().hits >= 2


def test_author_changed_stable_paper_frame_remains_exportable(source, tmp_path):
    p = project(source)
    variant = next(iter(p.segmented_variants.values()))
    row = variant.triangle_bindings[1]
    profile = p.profiles[row["profile_id"]]
    p.set_anchor(row["part_id"], row["surface_id"], profile.vertices[1].id, profile.segments[1].id)
    assert p.segmented_variant_status(variant.id)["status"] == "APPROXIMATE"
    snapshot = p.snapshot()
    author_export.export_all(snapshot, tmp_path / "changed-anchor")


@pytest.mark.parametrize("kind", ["svg_position", "svg_mode", "pdf_position", "pdf_mode"])
def test_actual_file_mutation_is_blocked_before_owned_or_foreign_bytes_change(
    bundle, kind, monkeypatch, tmp_path
):
    snapshot, original = bundle
    directory = tmp_path / "existing"
    shutil.copytree(original, directory)
    (directory / "foreign.txt").write_text("do not touch", encoding="utf8")
    before = hashes(directory)
    if kind.startswith("svg"):
        writer = author_export._svg

        def changed(*args, **kwargs):
            writer(*args, **kwargs)
            path = args[4]
            root = ET.parse(path).getroot()
            group = root.find(f"{NS}g[@data-part-id]")
            if group is None:
                return
            if kind == "svg_mode":
                group.set("data-flattening-mode", "EXACT")
            else:
                transform = group.get("transform")
                group.set(
                    "transform",
                    re.sub(
                        r"translate\(([^ ]+)",
                        lambda m: "translate(" + str(float(m[1]) + 0.1),
                        transform,
                    ),
                )
            ET.ElementTree(root).write(path, encoding="utf8", xml_declaration=True)

        monkeypatch.setattr(author_export, "_svg", changed)
    else:
        writer = author_export._pdf

        def changed(*args, **kwargs):
            bound = writer(*args, **kwargs)
            path = args[3]
            reader = PdfReader(path)
            result = PdfWriter()
            result.clone_document_from_reader(reader)
            if kind == "pdf_mode":
                metadata = json.loads(reader.metadata["/Keywords"])
                metadata["segmented_variant_modes"] = {}
                result.add_metadata({"/Keywords": json.dumps(metadata)})
            else:
                page = result.pages[0]
                stream = page.get_contents().get_data()
                # Translate all x operands of the first CUT path, preserving area.
                start = stream.index(b"/APRole_CUT BMC")
                end = stream.index(b"EMC", start)
                local = stream[start:end]
                local = re.sub(
                    rb"([+-]?[0-9.]+) ([+-]?[0-9.]+) ([ml])",
                    lambda m: str(float(m[1]) + 0.1).encode() + b" " + m[2] + b" " + m[3],
                    local,
                )
                content = DecodedStreamObject()
                content.set_data(stream[:start] + local + stream[end:])
                page[NameObject("/Contents")] = result._add_object(content)
            with open(path, "wb") as handle:
                result.write(handle)
            return bound

        monkeypatch.setattr(author_export, "_pdf", changed)
    with pytest.raises(CurveOutputError):
        author_export.export_all(snapshot, directory)
    assert hashes(directory) == before


def test_unrelated_material_cannot_be_excluded_by_forging_reference_coverage(source):
    p = project(source)
    surface = p.add_surface(p.add_profile([[0, 0], [5, 0], [0, 5]]))
    pid = p.part_for_surface(surface)
    p.set_placement(pid, p.pages[0].id, 180, 180)
    snapshot = p.snapshot()
    snapshot["pages"][0]["parts"] = [
        part for part in snapshot["pages"][0]["parts"] if part["id"] != pid
    ]
    snapshot["coverage"]["expected_part_ids"].remove(pid)
    snapshot["coverage"]["expected_surface_ids"].remove(surface)
    snapshot["coverage"]["reference_surface_ids"].append(surface)
    with pytest.raises(CurveOutputError):
        validate_segmented_snapshot(snapshot)


@pytest.mark.parametrize(
    "budget",
    [
        "MAX_SOURCE_BYTES",
        "MAX_SOURCE_NODES",
        "MAX_SOURCE_DEPTH",
        "MAX_SOURCE_PARTS",
        "MAX_SOURCE_VARIANTS",
        "MAX_SOURCE_PAGES",
    ],
)
def test_finite_source_budget_exhaustion_is_typed_unresolved(source, budget, monkeypatch):
    from archpapercraft.exporter import segmented_output_validation as guard

    snapshot = project(source).snapshot()
    _canonical_snapshot.cache_clear()
    monkeypatch.setattr(guard, budget, 0)
    with pytest.raises(CurveOutputError) as caught:
        validate_segmented_snapshot(snapshot)
    assert caught.value.report["status"] == "UNRESOLVED"


def test_legitimate_tab_union_keeps_the_certified_body_and_is_not_a_false_exact(tmp_path):
    p = load_project(
        ROOT / "docs/p2/implementation/evidence/pc008-domain-95fa2c7/backend-fixture.apcraft"
    )
    p.set_material_profile(crease_zone_mm=0.05)
    p.recompute()
    variant = next(iter(p.segmented_variants.values()))
    first, second = variant.paired_seams[0]["uses"]
    rows = {row["id"]: row for row in variant.triangle_bindings}
    a, b = rows[first["triangle_id"]], rows[second["triangle_id"]]
    joint = p.connect_edges(a["surface_id"], first["edge_id"], b["surface_id"], second["edge_id"])
    p.set_tab(joint, owner=a["surface_id"], width_mm=0.3, shape="triangle")
    issues = p.validate_layout()
    assert issues and all(issue.severity == "warning" for issue in issues)
    # This small regression fixture explicitly acknowledges the small tab and
    # unknown material; it makes no claim about physical folding/buildability.
    for issue in issues:
        p.acknowledge(issue.id)
    snapshot = p.snapshot()
    part = next(part for part in snapshot["pages"][0]["parts"] if part["id"] == a["part_id"])
    assert part["paths"]["TABS"]
    assert part["paths"]["FOLD_VALLEY"] or part["paths"]["FOLD_MOUNTAIN"]
    assert len(part["paths"]["CUT"][0]["points"]) == 4
    directory = tmp_path / "body-plus-tab"
    author_export.export_all(snapshot, directory)
    manifest = json.loads((directory / ".author-export.json").read_text(encoding="utf8"))
    record = manifest["actual_curve_output_checks"]["segmented_variants"]["parts"][a["part_id"]]
    assert record["mode"] == "APPROXIMATE" and set(record["outputs"]) == {"svg", "pdf"}
    # An invented extension has identical area to the legitimate tab union,
    # but the authoritative source recomputation still refuses its translation.
    forged = copy.deepcopy(snapshot)
    target = next(part for part in forged["pages"][0]["parts"] if part["id"] == a["part_id"])
    for point in target["paths"]["CUT"][0]["points"]:
        point[0] += 0.1
    with pytest.raises(CurveOutputError):
        validate_segmented_snapshot(forged)
