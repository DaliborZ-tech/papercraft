"""Actual PDF decimal/CTM/marked CUT proof, independent of source geometry helpers."""

import hashlib
import json
from fractions import Fraction

import pytest
from reportlab.pdfgen.canvas import Canvas

from archpapercraft.exporter.curve_output_validation import (
    CurveOutputError,
    read_pdf_cut_regions,
    validate_native_output_regions,
    validate_pdf_curve_geometry,
)


def rectangle(x, y, width, height):
    return [["M", x, y], ["L", x + width, y], ["L", x + width, y + height],
            ["L", x, y + height], ["Z"]]


def draw_loop(canvas, commands):
    path = canvas.beginPath()
    for command in commands:
        op, values = command[0], command[1:]
        if op == "M":
            path.moveTo(*values)
        elif op == "L":
            path.lineTo(*values)
        elif op == "C":
            path.curveTo(*values)
        elif op == "Z":
            path.close()
        else:
            raise AssertionError("Test fixture uses an unsupported native command")
    canvas.drawPath(path, stroke=1, fill=0)


def mark_part(canvas, identity, loops, *, role="CUT"):
    canvas._code.extend([f"/APPart_{identity} BMC", f"/APRole_{role} BMC"])
    for loop in loops:
        draw_loop(canvas, loop)
    canvas._code.extend(["EMC", "EMC"])


def pdf_file(tmp_path, *, parts=(), before=None, after=None, second_page=()):
    target = tmp_path / "actual.pdf"
    canvas = Canvas(str(target), pagesize=(360, 360), pageCompression=0)
    if before:
        before(canvas)
    for pid, loops in parts:
        mark_part(canvas, pid, loops)
    if after:
        after(canvas)
    if second_page:
        canvas.showPage()
        for pid, loops in second_page:
            mark_part(canvas, pid, loops)
    canvas.save()
    return target


def expected(*parts):
    return {pid: {"page_index": page, "loop_count": count, "name": "Model " + pid}
            for pid, page, count in parts}


def test_parser_uses_exact_pdf_decimals_and_serialized_composite_ctm(tmp_path):
    def before(canvas):
        canvas.saveState()
        canvas.translate(10, 20)
        canvas.transform(2, 0, 0, 3, 4, 5)

    target = pdf_file(tmp_path, parts=[("wall", [rectangle(0, 0, 10, 10)])],
                      before=before, after=lambda c: c.restoreState())
    parsed = read_pdf_cut_regions(target)
    loop = parsed["parts"]["wall"]["loops"][0]
    unit = Fraction(127, 360)
    assert loop == [["M", 14 * unit, 335 * unit], ["L", 34 * unit, 335 * unit],
                    ["L", 34 * unit, 305 * unit], ["L", 14 * unit, 305 * unit], ["Z"]]
    assert all(isinstance(v, Fraction) for cmd in loop for v in cmd[1:])
    assert parsed["pages"] == [{"page_index": 0, "width_mm": Fraction(127),
                                 "height_mm": Fraction(127)}]


def test_parser_collects_actual_cubic_controls_without_source_or_float_geometry(tmp_path):
    controls = [["M", 12.345678, 25.000001],
                ["C", 10.000001, 30.000002, 20.000003, 40.000004, 30.000005, 25.000001],
                ["L", 30.000005, 20], ["L", 12.345678, 20], ["Z"]]
    target = pdf_file(tmp_path, parts=[("curve", [controls])])
    loop = read_pdf_cut_regions(target)["parts"]["curve"]["loops"][0]
    unit = Fraction(127, 360)
    # ReportLab's real stream rounds these controls; assertions deliberately
    # target those actual decimals, not the unprinted input coordinates.
    assert loop[0] == ["M", Fraction("12.34568") * unit, (360 - 25) * unit]
    assert loop[1] == ["C", 10 * unit, (360 - 30) * unit,
                       20 * unit, (360 - 40) * unit,
                       Fraction("30.00001") * unit, (360 - 25) * unit]


def test_parser_ignores_other_named_roles_and_tracks_pages(tmp_path):
    def before(canvas):
        canvas._code.extend(["/APPart_a BMC", "/APRole_GUIDES BMC"])
        draw_loop(canvas, rectangle(0, 0, 100, 100))
        canvas._code.extend(["EMC", "/APRole_CUT BMC"])
        draw_loop(canvas, rectangle(10, 10, 20, 20))
        canvas._code.extend(["EMC", "EMC"])

    target = pdf_file(tmp_path, before=before, second_page=[("b", [rectangle(50, 50, 10, 10)])])
    parsed = read_pdf_cut_regions(target)
    assert set(parsed["parts"]) == {"a", "b"}
    assert len(parsed["parts"]["a"]["loops"]) == 1
    assert parsed["parts"]["a"]["page_index"] == 0
    assert parsed["parts"]["b"]["page_index"] == 1


@pytest.mark.parametrize("operator", ["0 0 10 10 re", "0 0 10 10 v", "BT /F1 10 Tf ET"])
def test_unsupported_cut_operators_are_not_ignored(tmp_path, operator):
    def before(canvas):
        canvas._code.extend(["/APPart_bad BMC", "/APRole_CUT BMC", operator,
                             "EMC", "EMC"])

    with pytest.raises(CurveOutputError, match="nepodporovaný"):
        read_pdf_cut_regions(pdf_file(tmp_path, before=before))


@pytest.mark.parametrize("bad", ["0 0 10 10 re W n", "0 0 0 1 0 0 cm", "Q"])
def test_unsupported_clipping_singular_matrices_and_stack_underflow_block(tmp_path, bad):
    target = pdf_file(tmp_path, parts=[("a", [rectangle(10, 10, 10, 10)])],
                      before=lambda c: c._code.append(bad))
    with pytest.raises(CurveOutputError):
        read_pdf_cut_regions(target)


def test_parser_refuses_actual_inline_raster_image(tmp_path):
    from PIL import Image

    target = pdf_file(tmp_path, parts=[("a", [rectangle(10, 10, 10, 10)])],
                      before=lambda c: c.drawInlineImage(Image.new("RGB", (1, 1)), 0, 0))
    with pytest.raises(CurveOutputError, match="rastrový"):
        read_pdf_cut_regions(target)


@pytest.mark.parametrize("ending,valid", [("S", False), ("s", True), ("h S", True)])
def test_parser_requires_closed_stroked_cut_loops(tmp_path, ending, valid):
    def before(canvas):
        canvas._code.extend(["/APPart_a BMC", "/APRole_CUT BMC",
                             "0 0 m 10 0 l 10 10 l 0 10 l " + ending, "EMC", "EMC"])

    target = pdf_file(tmp_path, before=before)
    if valid:
        assert read_pdf_cut_regions(target)["parts"]["a"]["loops"][0][-1] == ["Z"]
    else:
        with pytest.raises(CurveOutputError, match="neuzavřený"):
            read_pdf_cut_regions(target)


def test_parser_refuses_decoded_numeric_precision_loss(tmp_path):
    def before(canvas):
        canvas._code.extend(["/APPart_a BMC", "/APRole_CUT BMC",
                             "0.123456789012345678 0 m 10 0 l 10 10 l 0 10 l h S",
                             "EMC", "EMC"])

    with pytest.raises(CurveOutputError, match="přesnost"):
        read_pdf_cut_regions(pdf_file(tmp_path, before=before))


@pytest.mark.parametrize("wanted", [expected(("missing", 0, 1)),
                                     expected(("a", 0, 2)), expected(("a", 1, 1))])
def test_actual_part_and_hole_coverage_checks_precede_any_geometry_backend(tmp_path, wanted):
    target = pdf_file(tmp_path, parts=[("a", [rectangle(10, 10, 10, 10)])])
    with pytest.raises(CurveOutputError):
        validate_pdf_curve_geometry(target, wanted)


def test_actual_pdf_region_with_hole_and_disjoint_part_has_serializable_proof(tmp_path):
    target = pdf_file(tmp_path, parts=[
        ("wall", [rectangle(10, 10, 100, 100), rectangle(30, 30, 20, 20)]),
        ("roof", [rectangle(150, 10, 50, 50)]),
    ])
    report = validate_pdf_curve_geometry(target, expected(("wall", 0, 2), ("roof", 0, 1)))
    assert report["status"] == "VALID"
    assert report["separations"][0]["status"] == "DISJOINT"
    assert report["pdf_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    json.dumps(report, allow_nan=False)


def test_part_inside_true_hole_is_separate_even_when_outer_bounding_boxes_overlap(tmp_path):
    target = pdf_file(tmp_path, parts=[
        ("wall", [rectangle(10, 10, 100, 100), rectangle(30, 30, 40, 40)]),
        ("insert", [rectangle(40, 40, 10, 10)]),
    ])
    report = validate_pdf_curve_geometry(target, expected(("wall", 0, 2), ("insert", 0, 1)))
    assert report["status"] == "VALID"


@pytest.mark.parametrize("hole", [rectangle(150, 30, 10, 10), rectangle(5, 5, 20, 20)])
def test_hole_outside_or_crossing_real_outer_boundary_cannot_receive_valid_proof(tmp_path, hole):
    target = pdf_file(tmp_path, parts=[("wall", [rectangle(10, 10, 100, 100), hole])])
    with pytest.raises(CurveOutputError, match="Topologii") as exc:
        validate_pdf_curve_geometry(target, expected(("wall", 0, 2)))
    assert exc.value.part_name == "Model wall" and exc.value.report["status"] == "UNRESOLVED"


def test_actual_cubic_overlap_after_serialization_is_blocked_with_concrete_names(tmp_path):
    bulged = [["M", 0, 0], ["L", 10, 0],
              ["C", 10.0015, 3, 10.0015, 7, 10, 10],
              ["L", 0, 10], ["Z"]]
    target = pdf_file(tmp_path, parts=[("curve", [bulged]),
                                      ("neighbor", [rectangle(10.0005, 0, 2, 10)])])
    with pytest.raises(CurveOutputError, match="překrývají") as exc:
        validate_pdf_curve_geometry(target, expected(("curve", 0, 1), ("neighbor", 0, 1)))
    assert exc.value.part_name in ("Model curve", "Model neighbor")
    assert exc.value.report["separations"][0]["status"] in ("OVERLAP", "UNRESOLVED")


def test_explicitly_accepted_pair_does_not_implicitly_accept_a_new_pair(tmp_path):
    target = pdf_file(tmp_path, parts=[
        ("a", [rectangle(10, 10, 20, 20)]),
        ("b", [rectangle(20, 10, 20, 20)]),
    ])
    report = validate_pdf_curve_geometry(target, expected(("a", 0, 1), ("b", 0, 1)), [("a", "b")])
    assert report["status"] == "VALID"
    assert report["separations"][0]["status"] == "EXPLICIT_SOURCE_LAYOUT_OVERLAP_ACCEPTED"
    target = pdf_file(tmp_path, parts=[
        ("a", [rectangle(10, 10, 20, 20)]),
        ("b", [rectangle(20, 10, 20, 20)]),
        ("c", [rectangle(15, 15, 5, 5)]),
    ])
    with pytest.raises(CurveOutputError):
        validate_pdf_curve_geometry(target, expected(("a", 0, 1), ("b", 0, 1), ("c", 0, 1)),
                                     [("a", "b")])


def test_coincident_kissing_cuts_do_not_become_disjoint(tmp_path):
    target = pdf_file(tmp_path, parts=[("a", [rectangle(10, 10, 10, 10)]),
                                      ("b", [rectangle(20, 10, 10, 10)])])
    with pytest.raises(CurveOutputError, match="dotýkají"):
        validate_pdf_curve_geometry(target, expected(("a", 0, 1), ("b", 0, 1)))


def test_real_pdf_physical_overflow_is_blocked_and_control_hull_overflow_can_refine(tmp_path):
    target = pdf_file(tmp_path, parts=[("a", [rectangle(350, 10, 20, 10)])])
    with pytest.raises(CurveOutputError, match="fyzickou stránku"):
        validate_pdf_curve_geometry(target, expected(("a", 0, 1)))
    # Cubic control x=-1 lies outside the page, but its exact minimum x is positive.
    inside = [["M", 1, 10], ["C", -1, 15, 10, 20, 20, 10],
              ["L", 20, 5], ["L", 1, 5], ["Z"]]
    target = pdf_file(tmp_path, parts=[("a", [inside])])
    assert validate_pdf_curve_geometry(target, expected(("a", 0, 1)))["status"] == "VALID"


def test_local_svg_region_proof_explicitly_does_not_claim_placement_or_separation():
    loop = [["M", Fraction(10), Fraction(0)],
            ["A", 10, 10, 0, 0, 1, 0, 10],
            ["A", 10, 10, 0, 0, 1, -10, 0],
            ["A", 10, 10, 0, 0, 1, 0, -10],
            ["A", 10, 10, 0, 0, 1, 10, 0], ["Z"]]
    actual = {"pages": [{"page_index": 5}], "parts": {
        "a": {"page_index": 5, "loops": [loop]},
        "b": {"page_index": 5, "loops": [loop]},
    }}
    seed = {"kind": "ACTUAL_SVG_PART_LOCAL_NATIVE_TOPOLOGY", "svg_sha256": "explicit-test"}
    report = validate_native_output_regions(
        actual, expected(("a", 5, 1), ("b", 5, 1)), report=seed,
        check_page_bounds=False, check_separation=False,
    )
    assert report["status"] == "VALID" and not report["separations"]
    assert report["parts"]["a"]["page_bounds"]["status"] == "NOT_CHECKED"
    assert report["proof_scope"]["same_page_part_separation"] == "NOT_CHECKED_LOCAL_COORDINATES"
    assert report["proof_scope"]["physical_page_bounds"] == "NOT_CHECKED_LOCAL_COORDINATES"
    assert seed == {"kind": "ACTUAL_SVG_PART_LOCAL_NATIVE_TOPOLOGY", "svg_sha256": "explicit-test"}
    json.dumps(report, allow_nan=False)


def test_empty_expected_material_is_not_a_geometrical_pass(tmp_path):
    target = pdf_file(tmp_path)
    with pytest.raises(CurveOutputError, match="výrobní pokrytí"):
        validate_pdf_curve_geometry(target, {})


def test_real_author_writer_markers_and_actual_pdf_topology_are_verified(tmp_path):
    from archpapercraft.authoring import AuthorProject
    from archpapercraft.exporter.author_export import export_all

    project = AuthorProject.new(scale=1)
    profile = project.add_profile([[0, 0], [40, 0], [40, 40], [0, 40]])
    hole = project.add_profile(segments=[
        {"kind": "arc", "start": [25, 20], "end": [15, 20],
         "data": {"center": [20, 20], "sweep_deg": 180}},
        {"kind": "arc", "start": [15, 20], "end": [25, 20],
         "data": {"center": [20, 20], "sweep_deg": 180}},
    ])
    sid = project.add_surface(profile, [hole])
    pid = project.part_for_surface(sid)
    project.set_placement(pid, project.pages[0].id, 50, 60, 17)
    target = tmp_path / "actual-own-writer"
    export_all(project.snapshot(), target)
    parsed = read_pdf_cut_regions(target / "model.pdf")
    assert len(parsed["parts"][pid]["loops"]) == 2
    assert any(command[0] == "C" for loop in parsed["parts"][pid]["loops"] for command in loop)
    manifest = json.loads((target / ".author-export.json").read_text(encoding="utf8"))
    report = manifest["actual_curve_output_checks"]["pdf"]
    assert report["status"] == "VALID"
    assert report["proof_scope"]["physical_page_bounds"] == "CERTIFIED_ACTUAL_COMMANDS"
    assert report["pdf_sha256"] == hashlib.sha256((target / "model.pdf").read_bytes()).hexdigest()
