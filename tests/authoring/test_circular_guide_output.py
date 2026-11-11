"""Actual printed hinge paths, exact raw roles, and transactional rejection."""

import copy
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from xml.etree import ElementTree as ET

import pytest
from reportlab.pdfgen.canvas import Canvas
from test_circular_material_integration import constructed

from archpapercraft.exporter import author_export
from archpapercraft.exporter.circular_output_validation import coordinate_errors
from archpapercraft.exporter.curve_output_validation import CurveOutputError, read_pdf_cut_regions

NS = "{http://www.w3.org/2000/svg}"


def raw_pdf(path, role, commands):
    canvas = Canvas(str(path), invariant=1)
    canvas._code.extend(["/APPart_material BMC", f"/APRole_{role} BMC", commands, "EMC", "EMC"])
    canvas.showPage()
    canvas.save()


def test_open_guide_and_closed_tab_fill_use_same_exact_token_ctm_reader(tmp_path):
    path = tmp_path / "roles.pdf"
    raw_pdf(path, "GUIDES", "q 1 0 0 1 1.00000000000000001 2 cm n 0 0 m 1 0 l S Q")
    result = read_pdf_cut_regions(path, role="GUIDES", require_closed=False)
    commands = result["parts"]["material"]["loops"][0]
    assert commands[0][1] == Q("1.00000000000000001") * Q(127, 360)
    assert [command[0] for command in commands] == ["M", "L"]
    raw_pdf(path, "TABS", "n 0 0 m 1 0 l 0 1 l h f*")
    result = read_pdf_cut_regions(path, role="TABS")
    assert [c[0] for c in result["parts"]["material"]["loops"][0]] == ["M", "L", "L", "Z"]


@pytest.mark.parametrize(
    "role,closed,commands",
    [
        ("CUT", True, "n 0 0 m 1 0 l S"),
        ("CUT", False, "n 0 0 m 1 0 l S"),
        ("UNKNOWN", False, "n 0 0 m 1 0 l S"),
        ("TABS", True, "n 0 0 m 1 0 l 0 1 l f"),
        ("GUIDES", False, "n 0 0 m 1 0 l f"),
    ],
)
def test_reader_refuses_half_open_cut_unknown_role_and_wrong_paint(
    tmp_path, role, closed, commands
):
    path = tmp_path / "bad.pdf"
    raw_pdf(path, role, commands)
    with pytest.raises(CurveOutputError):
        read_pdf_cut_regions(path, role=role, require_closed=closed)


def test_near_straight_arc_position_uses_proven_homogeneous_curve_not_large_center_delta():
    radius, change = 10**12, 10**6
    source = [["M", 0, 0], ["A", radius, radius, 0, 0, 1, 1, 0]]
    target = [["M", 0, 0], ["A", radius + change, radius + change, 0, 0, 1, 1, 0]]
    position, _ = coordinate_errors(source, target)
    # Independent 90-digit sagitta difference at the arc midpoint. Centers
    # differ by ~10^6, while the entire unit-chord arcs differ by ~1.25e-19.
    with localcontext() as context:
        context.prec = 90

        def sagitta(r):
            return Decimal(r) - (Decimal(r) ** 2 - Decimal(1) / 4).sqrt()

        actual = abs(sagitta(radius) - sagitta(radius + change))
    assert Q(actual) <= position < Q(1, 10**15)
    target = [["M", Q(1, 100000), 0], ["A", radius, radius, 0, 0, 1, 1 + Q(1, 100000), 0]]
    position, _ = coordinate_errors(source, target)
    assert Q(1, 100000) <= position < Q(11, 10**6)


@pytest.mark.parametrize("mutation", ["omitted", "extra", "reversed", "moved", "ctm", "cross_role"])
def test_actual_svg_guide_fault_never_replaces_previous_bundle(tmp_path, monkeypatch, mutation):
    p, _, pid, _ = constructed()
    snapshot = p.snapshot()
    directory = tmp_path / "bundle"
    author_export.export_all(snapshot, directory)
    original_bytes = {path.name: path.read_bytes() for path in directory.iterdir()}
    original = author_export._svg

    def altered(*args, **kwargs):
        original(*args, **kwargs)
        path = args[4]
        tree = ET.parse(path)
        group = tree.find(f"{NS}g[@data-part-id='{pid}']")
        if group is None:
            return
        guide = group.find(f"{NS}g[@data-role='GUIDES']")
        if mutation == "omitted":
            guide.remove(guide[0])
        elif mutation == "extra":
            extra = copy.deepcopy(guide[0])
            extra.set("id", f"path-{pid}-GUIDES-{len(guide)}")
            guide.append(extra)
        elif mutation == "cross_role":
            guide[0].set("id", f"path-{pid}-CUT-0")
        elif mutation == "ctm":
            group.set("transform", "translate(70.00001 100) rotate(17)")
        else:
            tokens = guide[0].get("d").split()
            a, b = list(map(Q, tokens[1:3])), list(map(Q, tokens[4:6]))
            if mutation == "reversed":
                a, b = b, a
            else:
                a[0] += Q(1, 100000)
                b[0] += Q(1, 100000)
            guide[0].set(
                "d",
                "M "
                + " ".join(str(float(x)) for x in a)
                + " L "
                + " ".join(str(float(x)) for x in b),
            )
        tree.write(path, encoding="utf8", xml_declaration=True)

    monkeypatch.setattr(author_export, "_svg", altered)
    with pytest.raises(CurveOutputError):
        author_export.export_all(snapshot, directory)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == original_bytes
    assert not list(directory.glob(".author-export-*"))


@pytest.mark.parametrize("mutation", ["omitted", "cross_role", "moved"])
def test_actual_pdf_guide_fault_is_not_hidden_by_unchanged_cut(tmp_path, monkeypatch, mutation):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    p, _, pid, _ = constructed()
    snapshot = p.snapshot()
    directory = tmp_path / "bundle"
    author_export.export_all(snapshot, directory)
    original_bytes = {path.name: path.read_bytes() for path in directory.iterdir()}
    original = author_export._pdf

    def altered(*args, **kwargs):
        bound = original(*args, **kwargs)
        path = args[3]
        reader, writer = PdfReader(path), PdfWriter()
        for page in reader.pages:
            content = page.get_contents().get_data()
            if f"/APPart_{pid} BMC".encode() in content:
                before, rest = content.split(b"/APRole_GUIDES BMC", 1)
                guide, after = rest.split(b"EMC", 1)
                if mutation == "omitted":
                    guide = b"\n"
                elif mutation == "moved":
                    guide = b"\nq 1 0 0 1 0.00001 0 cm\n" + guide + b"\nQ\n"
                tag = b"/APRole_ARTWORK BMC" if mutation == "cross_role" else b"/APRole_GUIDES BMC"
                stream = DecodedStreamObject()
                stream.set_data(before + tag + guide + b"EMC" + after)
                page[NameObject("/Contents")] = stream
            writer.add_page(page)
        with path.open("wb") as handle:
            writer.write(handle)
        return bound

    monkeypatch.setattr(author_export, "_pdf", altered)
    with pytest.raises(CurveOutputError):
        author_export.export_all(snapshot, directory)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == original_bytes
