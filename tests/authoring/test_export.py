"""Independent XML/PDF checks for the panel snapshot writers and publication."""

import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from pypdf import PdfReader
from pypdf.generic import ContentStream

from archpapercraft.exporter import author_export as exporter

NS = {"s": exporter.SVG_NS}


@pytest.fixture
def snapshot():
    def part(pid, angle):
        return {
            "id": pid,
            "name": "Čelní stěna",
            "placement": {"x_mm": 40.0, "y_mm": 55.0, "rotation_deg": angle},
            "paths": {
                "CUT": [
                    {"points": [[0.0, 0.0], [30.0, 0.0], [30.0, 20.0], [0.0, 20.0]], "closed": True}
                ],
                "FOLD_MOUNTAIN": [{"points": [[0.0, 10.0], [30.0, 10.0]], "closed": False}],
                "FOLD_VALLEY": [{"points": [[15.0, 0.0], [15.0, 20.0]], "closed": False}],
                "TABS": [
                    {"points": [[0.0, 0.0], [30.0, 0.0], [25.0, -5.0], [5.0, -5.0]], "closed": True}
                ],
            },
            "labels": [
                {"text": "Příliš žluťoučký kůň — střecha", "x": 2.0, "y": 7.0, "size_mm": 2.5}
            ],
        }

    return {
        "project_id": "reference-house",
        "revision": 7,
        "scale_label": "1:100",
        "pages": [
            {"id": "front", "width_mm": 210.0, "height_mm": 297.0, "parts": [part("wall-a", 30.0)]},
            {"id": "back", "width_mm": 297.0, "height_mm": 210.0, "parts": [part("wall-b", -30.0)]},
        ],
    }


def file_bytes(directory):
    return {file.name: file.read_bytes() for file in directory.iterdir() if file.is_file()}


def pdf_stroke_paths(page):
    """Apply PDF affine operators independently and return top-left paper mm."""
    matrix = np.eye(3)
    stack = []
    current = []
    strokes = []
    height = float(page.mediabox.height)
    for operands, operator in ContentStream(page.get_contents(), page.pdf).operations:
        if operator == b"q":
            stack.append(matrix.copy())
        elif operator == b"Q":
            matrix = stack.pop()
        elif operator == b"cm":
            a, b, c, d, e, f = map(float, operands)
            matrix = matrix @ np.array([[a, c, e], [b, d, f], [0, 0, 1]])
        elif operator == b"m":
            current = [matrix @ np.array([float(operands[0]), float(operands[1]), 1.0])]
        elif operator == b"l":
            current.append(matrix @ np.array([float(operands[0]), float(operands[1]), 1.0]))
        elif operator in (b"S", b"s", b"B", b"B*", b"b", b"b*"):
            strokes.append([[p[0] * 25.4 / 72, (height - p[1]) * 25.4 / 72] for p in current])
            current = []
        elif operator in (b"f", b"f*", b"n"):
            current = []
    return strokes


def test_xml_roles_grouping_editable_text_and_snapshot_immutability(snapshot, tmp_path):
    original = deepcopy(snapshot)
    files = exporter.export_all(snapshot, tmp_path / "bundle")
    assert snapshot == original
    assert [file.name for file in files] == ["page-front.svg", "page-back.svg", "model.pdf"]
    root = ET.parse(files[0]).getroot()
    assert root.attrib["width"] == "210mm" and root.attrib["height"] == "297mm"
    part = root.find("s:g[@id='part-wall-a']", NS)
    assert part.attrib["transform"] == "translate(40 55) rotate(30)"
    groups = part.findall("s:g", NS)
    assert tuple(group.attrib["data-role"] for group in groups) == exporter.ROLES
    assert len(part.findall(".//s:path", NS)) == 4
    text = part.find("s:g[@data-role='LABELS']/s:text", NS)
    assert text.text == "Příliš žluťoučký kůň — střecha"
    assert part.find("s:g[@data-role='TABS']", NS).attrib["stroke"] == "none"
    assert root.find("s:g[@id='page-GUIDES']/s:path", NS).attrib["data-calibration-mm"] == "100"


def test_pdf_rotation_page_sizes_czech_embedding_and_vector_content(snapshot, tmp_path):
    files = exporter.export_all(snapshot, tmp_path / "bundle")
    pdf = PdfReader(files[-1])
    assert len(pdf.pages) == 2
    for index, page in enumerate(pdf.pages):
        expected_size = [[210, 297], [297, 210]][index]
        actual_size = [
            float(page.mediabox.width) * 25.4 / 72,
            float(page.mediabox.height) * 25.4 / 72,
        ]
        assert np.allclose(actual_size, expected_size, atol=0.0001)
        assert "Příliš žluťoučký kůň — střecha" in page.extract_text()
        assert "Tisk 100 % / skutečná velikost" in page.extract_text()
        resources = page["/Resources"]
        assert not resources.get("/XObject", {})
        fonts = [item.get_object() for item in resources["/Font"].values()]
        assert any("/FontFile2" in font.get("/FontDescriptor", {}) for font in fonts)
        actual_path = pdf_stroke_paths(page)[0]
        angle = math.radians(30 if index == 0 else -30)
        expected = [
            [
                40 + math.cos(angle) * x - math.sin(angle) * y,
                55 + math.sin(angle) * x + math.cos(angle) * y,
            ]
            for x, y in [[0, 0], [30, 0], [30, 20], [0, 20]]
        ]
        assert np.allclose(actual_path, expected, atol=0.0001)
        calibration = pdf_stroke_paths(page)[-1]
        assert abs(math.dist(*calibration) - 100) < 0.0001


def test_page_footer_uses_human_numbering_and_keeps_stable_id_metadata(snapshot, tmp_path):
    identities = [
        "8845125f-700f-45cd-b41e-4bf541cf460b",
        "517a9b44-b4c8-4552-bcd9-20e16429454e",
    ]
    for page, identity in zip(snapshot["pages"], identities):
        page["id"] = identity
    files = exporter.export_all(snapshot, tmp_path / "bundle")
    pdf = PdfReader(files[-1])
    for index, identity in enumerate(identities):
        root = ET.parse(files[index]).getroot()
        visible_svg_text = "\n".join(node.text or "" for node in root.findall(".//s:text", NS))
        visible_pdf_text = pdf.pages[index].extract_text()
        footer = f"Měřítko modelu 1:100 · Strana {index + 1} / 2"
        assert footer in visible_svg_text
        assert footer in visible_pdf_text
        assert all(
            item not in visible_svg_text and item not in visible_pdf_text for item in identities
        )
        assert root.attrib["data-page-id"] == identity
        assert files[index].name == f"page-{identity}.svg"
        assert root.find("s:g[@data-part-id]", NS) is not None


def test_repeated_bundle_and_canonical_digest_are_deterministic(snapshot, tmp_path):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    first = file_bytes(bundle)
    exporter.export_all(snapshot, bundle)
    assert file_bytes(bundle) == first
    with_metadata = deepcopy(snapshot)
    with_metadata["metadata"] = {"created_at": "tomorrow", "author": "Someone"}
    assert exporter.canonical_digest(snapshot) == exporter.canonical_digest(with_metadata)
    with_metadata["pages"][0]["parts"][0]["placement"]["x_mm"] += 1
    assert exporter.canonical_digest(snapshot) != exporter.canonical_digest(with_metadata)


def test_missing_font_leaves_every_previous_output_unchanged(snapshot, tmp_path):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    before = file_bytes(bundle)
    with pytest.raises(exporter.FontError):
        exporter.export_all(snapshot, bundle, font_path=tmp_path / "missing.ttf")
    assert file_bytes(bundle) == before


def test_invalid_font_is_typed_and_leaves_previous_bundle(snapshot, tmp_path):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    before = file_bytes(bundle)
    invalid = tmp_path / "invalid.ttf"
    invalid.write_bytes(b"invalid TrueType file")
    with pytest.raises(exporter.FontError):
        exporter.export_all(snapshot, bundle, font_path=invalid)
    assert file_bytes(bundle) == before


def test_font_restricting_embedding_is_refused(snapshot, tmp_path):
    import struct

    system_font = Path("C:/Windows/Fonts/arial.ttf")
    if not system_font.exists():
        system_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    assert system_font.exists(), (
        "A known system Unicode font is needed for the embedding restriction fixture"
    )
    binary = bytearray(system_font.read_bytes())
    table_count = struct.unpack_from(">H", binary, 4)[0]
    os2_offset = None
    for index in range(table_count):
        record = 12 + 16 * index
        if binary[record : record + 4] == b"OS/2":
            os2_offset = struct.unpack_from(">I", binary, record + 8)[0]
    assert os2_offset is not None
    struct.pack_into(">H", binary, os2_offset + 8, 0x0002)
    restricted = tmp_path / "restricted.ttf"
    restricted.write_bytes(binary)
    with pytest.raises(exporter.FontError, match="license flags"):
        exporter.export_all(snapshot, tmp_path / "bundle", font_path=restricted)
    assert not (tmp_path / "bundle").exists()


def test_staging_write_fault_preserves_previous_outputs(snapshot, tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    before = file_bytes(bundle)
    original = exporter._pdf

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("Injected failure after staged PDF write")

    monkeypatch.setattr(exporter, "_pdf", fail)
    with pytest.raises(exporter.ExportWriteError):
        exporter.export_all(snapshot, bundle)
    assert file_bytes(bundle) == before
    assert not list(tmp_path.glob(".author-export-*"))


def test_mid_publication_fault_rolls_back_all_files(snapshot, tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    before = file_bytes(bundle)
    snapshot["revision"] = 8
    snapshot["pages"][0]["parts"][0]["placement"]["x_mm"] += 3
    replace = exporter.os.replace
    calls = [0]

    def fail_once(source, target):
        calls[0] += 1
        if calls[0] == 2:
            raise OSError("Injected second publication failure")
        return replace(source, target)

    monkeypatch.setattr(exporter.os, "replace", fail_once)
    with pytest.raises(exporter.ExportWriteError):
        exporter.export_all(snapshot, bundle)
    assert file_bytes(bundle) == before


def test_obsolete_owned_pages_removed_but_unrelated_files_preserved(snapshot, tmp_path):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    unrelated = bundle / "my-notes.txt"
    unrelated.write_text("Author notes", encoding="utf-8")
    snapshot["pages"] = snapshot["pages"][:1]
    exporter.export_all(snapshot, bundle)
    assert not (bundle / "page-back.svg").exists()
    assert unrelated.read_text(encoding="utf-8") == "Author notes"


def test_unknown_manifest_preserves_previous_bundle(snapshot, tmp_path):
    bundle = tmp_path / "bundle"
    exporter.export_all(snapshot, bundle)
    manifest = bundle / ".author-export.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["schema_version"] = 999
    manifest.write_text(json.dumps(data), encoding="utf-8")
    before = file_bytes(bundle)
    with pytest.raises(exporter.ExportWriteError, match="manifest"):
        exporter.export_all(snapshot, bundle)
    assert file_bytes(bundle) == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(stale=True),
        lambda s: s.update(issues=[{"severity": "ERROR", "accepted": True}]),
        lambda s: s["pages"][0]["parts"][0]["placement"].update(x_mm=float("nan")),
        lambda s: s["pages"][0]["parts"][0]["placement"].update(x_mm=-100.0),
        lambda s: s["pages"][0].update(id="../escape"),
        lambda s: s["pages"][1]["parts"][0].update(id="wall-a"),
        lambda s: s["pages"][1].update(id="FRONT"),
        lambda s: s.update(partial="no"),
        lambda s: s["pages"][0]["parts"][0]["labels"][0].update(text="invalid\x00text"),
    ],
)
def test_invalid_integrity_never_creates_bundle(snapshot, tmp_path, mutation):
    mutation(snapshot)
    with pytest.raises(exporter.SnapshotError):
        exporter.export_all(snapshot, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def test_explicit_partial_keeps_offpage_geometry_and_marks_both_outputs(snapshot, tmp_path):
    snapshot["partial"] = True
    snapshot["pages"][0]["parts"][0]["placement"]["x_mm"] = -100
    files = exporter.export_all(snapshot, tmp_path / "bundle")
    assert "translate(-100 55)" in files[0].read_text(encoding="utf-8")
    assert "ČÁSTEČNÝ VÝSTUP" in PdfReader(files[-1]).pages[0].extract_text()


@pytest.mark.ui
def test_pdf_renders_using_independent_qt_reader(snapshot, tmp_path, qapp):
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument

    files = exporter.export_all(snapshot, tmp_path / "bundle")
    reader = QPdfDocument()
    assert reader.load(str(files[-1])) == QPdfDocument.Error.None_
    render = reader.render(0, QSize(840, 1188))
    assert not render.isNull()
    assert reader.getAllText(0).text().count("žluťoučký") == 1
    reader.close()


def single_part(snapshot):
    snapshot["pages"] = snapshot["pages"][:1]
    part = snapshot["pages"][0]["parts"][0]
    part["paths"] = {"CUT": []}
    part["labels"] = []
    return part


def pdf_curves(page):
    """Read actual PDF paths and compose its affine operators independently."""
    matrix, stack, current = np.eye(3), [], None
    height = float(page.mediabox.height)
    curves = []

    def mapped(point):
        p = matrix @ np.array([*map(float, point), 1.0])
        return np.array([p[0] * 25.4 / 72, (height - p[1]) * 25.4 / 72])

    for values, op in ContentStream(page.get_contents(), page.pdf).operations:
        if op == b"q":
            stack.append(matrix.copy())
        elif op == b"Q":
            matrix = stack.pop()
        elif op == b"cm":
            a, b, c, d, e, f = map(float, values)
            matrix = matrix @ np.array([[a, c, e], [b, d, f], [0, 0, 1]])
        elif op == b"m":
            current = mapped(values)
        elif op == b"l":
            current = mapped(values)
        elif op == b"c":
            controls = [mapped(values[i : i + 2]) for i in (0, 2, 4)]
            curves.append(np.array([current, *controls]))
            current = controls[-1]
    return curves


def test_native_cubic_is_editable_and_pdf_preserves_all_control_points(snapshot, tmp_path):
    part = single_part(snapshot)
    part["paths"]["CUT"] = [
        {"commands": [["M", 0.0, 0.0], ["C", 3.0, 12.0, 17.0, 8.0, 30.0, 0.0]], "closed": False}
    ]
    files = exporter.export_all(snapshot, tmp_path / "curves")
    svg = ET.parse(files[0]).getroot()
    assert svg.find(".//s:g[@data-role='CUT']/s:path", NS).attrib["d"] == "M 0 0 C 3 12 17 8 30 0"
    actual = pdf_curves(PdfReader(files[-1]).pages[0])[0]
    c, s = math.cos(math.pi / 6), math.sin(math.pi / 6)
    expected = [
        [40 + c * x - s * y, 55 + s * x + c * y] for x, y in [(0, 0), (3, 12), (17, 8), (30, 0)]
    ]
    np.testing.assert_allclose(actual, expected, atol=1e-5)


def test_native_circle_svg_and_pdf_cubics_respect_declared_global_error_bound(snapshot, tmp_path):
    part = single_part(snapshot)
    part["paths"]["CUT"] = [
        {
            "commands": [
                ["M", 10.0, 0.0],
                ["A", 10.0, 10.0, 0.0, 0, 1, -10.0, 0.0],
                ["A", 10.0, 10.0, 0.0, 0, 1, 10.0, 0.0],
                ["Z"],
            ],
            "closed": True,
        }
    ]
    files = exporter.export_all(snapshot, tmp_path / "curves")
    svg = ET.parse(files[0]).getroot()
    native = svg.find(".//s:g[@data-role='CUT']/s:path", NS).attrib["d"]
    assert native.count(" A ") == 2 and " C " not in native and " L " not in native
    manifest = json.loads((files[0].parent / ".author-export.json").read_text(encoding="utf-8"))
    bound = manifest["pdf_arc_approximation"]["max_position_error_mm"]
    assert 0 < bound <= 0.001
    assert float(svg.attrib["data-pdf-arc-position-error-bound-mm"]) == pytest.approx(bound)
    pdf = PdfReader(files[-1])
    assert "arc_position_error_bound_mm=" in pdf.metadata.subject
    curves = pdf_curves(pdf.pages[0])
    assert len(curves) >= 8
    maximum = 0.0
    for index, curve in enumerate(curves):
        for t in np.linspace(0, 1, 41):
            actual = sum(
                (1 - t) ** (3 - i) * t**i * (1, 3, 3, 1)[i] * p for i, p in enumerate(curve)
            )
            angle = 2 * math.pi * (index + t) / len(curves) + math.pi / 6
            expected = np.array([40 + 10 * math.cos(angle), 55 + 10 * math.sin(angle)])
            maximum = max(maximum, float(np.linalg.norm(actual - expected)))
    # Sampling is only this independent regression check. The declared global
    # bound derives from the fourth derivative Hermite remainder, not samples.
    assert maximum <= bound + 1e-5


def test_rotated_ellipse_arc_extrema_are_checked_beyond_endpoints(snapshot, tmp_path):
    part = single_part(snapshot)
    # Endpoint pair is inside the page; upper semicircle bulges through y=0.
    part["placement"].update(x_mm=40.0, y_mm=5.0, rotation_deg=0.0)
    part["paths"]["CUT"] = [
        {"commands": [["M", 0.0, 0.0], ["A", 10.0, 10.0, 0.0, 0, 1, 20.0, 0.0]], "closed": False}
    ]
    with pytest.raises(exporter.SnapshotError, match="physical page"):
        exporter.export_all(snapshot, tmp_path / "curves")
    # Full ellipse rotated locally30° and by its placement17°.
    phi = math.radians(30)
    x, y = 20 * math.cos(phi), 20 * math.sin(phi)
    part["placement"].update(x_mm=75.0, y_mm=75.0, rotation_deg=17.0)
    path = {
        "commands": [
            ["M", x, y],
            ["A", 20.0, 8.0, 30.0, 0, 1, -x, -y],
            ["A", 20.0, 8.0, 30.0, 0, 1, x, y],
        ],
        "closed": True,
    }
    bounds = exporter._bounds(path, part["placement"])
    angle = math.radians(47)
    ex = math.hypot(20 * math.cos(angle), 8 * math.sin(angle))
    ey = math.hypot(20 * math.sin(angle), 8 * math.cos(angle))
    np.testing.assert_allclose(bounds, [75 - ex, 75 - ey, 75 + ex, 75 + ey], atol=1e-9)


def test_cubic_true_extrema_allow_outside_controls_but_refuse_outside_material(snapshot, tmp_path):
    part = single_part(snapshot)
    part["placement"].update(x_mm=40.0, y_mm=220.0, rotation_deg=0.0)
    part["paths"]["CUT"] = [
        {"commands": [["M", 0.0, 0.0], ["C", 0.0, 100.0, 30.0, 100.0, 30.0, 0.0]], "closed": False}
    ]
    # Analytic max y is75 (t=.5), even though both controls are at100.
    exporter.export_all(snapshot, tmp_path / "curves")
    part["placement"]["y_mm"] = 230.0
    with pytest.raises(exporter.SnapshotError, match="physical page"):
        exporter.export_all(snapshot, tmp_path / "other")


@pytest.mark.ui
def test_compound_material_hole_stays_hole_in_svg_and_rendered_vector_pdf(snapshot, tmp_path, qapp):
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument

    part = single_part(snapshot)
    part["placement"].update(x_mm=40.0, y_mm=55.0, rotation_deg=0.0)
    compound = {
        "commands": [
            ["M", 0.0, 0.0],
            ["L", 30.0, 0.0],
            ["L", 30.0, 30.0],
            ["L", 0.0, 30.0],
            ["Z"],
            ["M", 10.0, 10.0],
            ["L", 20.0, 10.0],
            ["L", 20.0, 20.0],
            ["L", 10.0, 20.0],
            ["Z"],
        ],
        "closed": True,
        "fill_rule": "evenodd",
    }
    part["paths"] = {"CUT": [compound], "TABS": [compound]}
    files = exporter.export_all(snapshot, tmp_path / "holes")
    svg = ET.parse(files[0]).getroot()
    for role in ("CUT", "TABS"):
        path = svg.find(f".//s:g[@data-role='{role}']/s:path", NS)
        assert path.attrib["d"].count("M ") == 2 and path.attrib["fill-rule"] == "evenodd"
    reader = QPdfDocument()
    assert reader.load(str(files[-1])) == QPdfDocument.Error.None_
    image = reader.render(0, QSize(840, 1188))
    hole = image.pixelColor(55 * 4, 70 * 4)
    material = image.pixelColor(45 * 4, 60 * 4)
    # QtPdf may leave unpainted paper transparent; both representations must
    # expose the empty hole rather than paint it with the tab material.
    assert hole.alpha() == 0 or min(hole.red(), hole.green(), hole.blue()) > 250
    assert material.red() > material.blue() + 10
    pdf = PdfReader(files[-1])
    assert any(op == b"f*" for _, op in ContentStream(pdf.pages[0].get_contents(), pdf).operations)
    assert not pdf.pages[0]["/Resources"].get("/XObject", {})
    reader.close()


@pytest.mark.parametrize(
    "commands",
    [
        [["L", 0, 0]],
        [["M", 0, 0], ["Q", 5, 5, 10, 0]],
        [["M", 0, 0], ["C", 5, 5, 10]],
        [["M", 0, 0], ["A", 0, 10, 0, 0, 1, 20, 0]],
        [["M", 0, 0], ["A", 10, 10, 0, 2, 1, 20, 0]],
        [["M", 0, 0], ["A", 10, 10, 0, 0, 1, 0, 0]],
        [["M", 0, 0], ["L", float("inf"), 0]],
        [["M", 0, 0], [[], 0, 0]],
        [["M", 0, 0], ["Z"]],
    ],
)
def test_malformed_native_paths_are_typed_and_never_publish(snapshot, tmp_path, commands):
    part = single_part(snapshot)
    part["paths"]["CUT"] = [{"commands": commands, "closed": False}]
    with pytest.raises(exporter.SnapshotError):
        exporter.export_all(snapshot, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def with_coverage(snapshot):
    parts = [part for page in snapshot["pages"] for part in page["parts"]]
    for i, part in enumerate(parts):
        part["surface_ids"] = [f"feature-{i}:surface"]
        part["source_revision"] = 4
    snapshot["coverage"] = {
        "expected_part_ids": [p["id"] for p in parts],
        "expected_surface_ids": [p["surface_ids"][0] for p in parts],
        "source_revisions": {p["id"]: 4 for p in parts},
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s["pages"][1].update(parts=[]),
        lambda s: s["pages"][0]["parts"][0].update(surface_ids=["other"]),
        lambda s: s["pages"][0]["parts"][0].update(source_revision=5),
        lambda s: s["pages"][0]["parts"][0].pop("source_revision"),
        lambda s: s["coverage"]["expected_part_ids"].append("wall-a"),
        lambda s: s["coverage"]["expected_surface_ids"].append("extra"),
        lambda s: s["coverage"]["source_revisions"].pop("wall-a"),
    ],
)
def test_authoritative_coverage_and_source_revision_mismatch_block_export(
    snapshot, tmp_path, mutation
):
    with_coverage(snapshot)
    exporter.export_all(snapshot, tmp_path / "existing")
    before = file_bytes(tmp_path / "existing")
    mutation(snapshot)
    with pytest.raises(exporter.SnapshotError):
        exporter.export_all(snapshot, tmp_path / "existing")
    assert file_bytes(tmp_path / "existing") == before


def test_unrelated_collision_and_another_project_bundle_are_preserved(snapshot, tmp_path):
    directory = tmp_path / "bundle"
    directory.mkdir()
    (directory / "model.pdf").write_bytes(b"author original")
    with pytest.raises(exporter.ExportWriteError, match="unrelated"):
        exporter.export_all(snapshot, directory)
    assert file_bytes(directory) == {"model.pdf": b"author original"}
    another = tmp_path / "another"
    exporter.export_all(snapshot, another)
    before = file_bytes(another)
    snapshot["project_id"] = "different-project"
    with pytest.raises(exporter.ExportWriteError, match="another project"):
        exporter.export_all(snapshot, another)
    assert file_bytes(another) == before


def test_extreme_finite_rotation_is_normalized_equally_in_svg_and_pdf(snapshot, tmp_path):
    part = single_part(snapshot)
    part["placement"]["rotation_deg"] = 1e308
    part["paths"]["CUT"] = [{"points": [[0.0, 0.0], [30.0, 0.0]], "closed": False}]
    files = exporter.export_all(snapshot, tmp_path / "rotation")
    angle = math.remainder(1e308, 360.0)
    group = ET.parse(files[0]).getroot().find("s:g[@data-part-id]", NS)
    assert f"rotate({angle:g})" in group.attrib["transform"]
    line = pdf_stroke_paths(PdfReader(files[-1]).pages[0])[0]
    np.testing.assert_allclose(
        line,
        [
            [40.0, 55.0],
            [40 + 30 * math.cos(math.radians(angle)), 55 + 30 * math.sin(math.radians(angle))],
        ],
        atol=1e-5,
    )


@pytest.mark.parametrize("value", ["bad\ud800text", "bad\ufffetext", "bad\ufffftext"])
def test_invalid_xml_unicode_is_rejected_before_any_output(snapshot, tmp_path, value):
    snapshot["name"] = value
    with pytest.raises(exporter.SnapshotError):
        exporter.export_all(snapshot, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()
