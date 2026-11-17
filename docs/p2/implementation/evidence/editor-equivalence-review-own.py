"""Independent reviewer oracles; no desktop, renderer or production math imports."""

import importlib.util
import xml.etree.ElementTree as ET
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "independent_editor_review", ROOT / "tools/authoring/editor_probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
helper = probe._equivalence_module()


def compare(a, b):
    return helper.certify_path_equivalence(probe._path_signature(a), probe._path_signature(b))


@pytest.mark.parametrize(
    "offset,expected", [(".00002", "CERTIFIED"), (".000020000000001", "UNRESOLVED")]
)
def test_exact_whole_curve_position_boundary(offset, expected):
    # Translation is exactly offset at EVERY point; length and Green area are unchanged.
    result = compare("M 0 0 L 4 0", f"M 0 {offset} L 4 {offset}")
    assert result["status"] == expected
    assert Q(result["max_position_bound_mm_exact"]) == Q(offset)
    assert Q(result["global_length_difference_bound_mm_exact"]) == 0


def test_cubic_between_endpoints_position_violation_is_not_hidden():
    # For x=t and y=3h*t(1-t), the midpoint moves by 3h/4=0.00003 mm.
    result = compare("M 0 0 C 0 0 1 0 1 0", "M 0 0 C 0 .00004 1 .00004 1 0")
    assert Q(3, 4) * Q(".00004") > Q(".00002")
    assert result["status"] == "UNRESOLVED"


def test_opposite_hole_area_changes_cannot_cancel_each_other():
    body = "M -1 -1 L 1101 -1 L 1101 31 L -1 31 Z "
    a = body + ("M 0 0 L 1100 0 L 1100 10 L 0 10 Z M 0 20 L 1100 20 L 1100 30 L 0 30 Z")
    b = body + (
        "M 0 0 L 1100 0 L 1100 10.00001 L 0 10.00001 Z "
        "M 0 20 L 1100 20 L 1100 29.99999 L 0 29.99999 Z"
    )
    result = compare(a, b)
    assert result["status"] == "UNRESOLVED"
    assert Q(result["net_area_difference_bound_mm2_exact"]) == Q(".022")
    assert Q(result["max_position_bound_mm_exact"]) == Q(".00001")


def test_disjoint_holes_becoming_tangent_fail_topology_despite_tiny_metric_error():
    prefix = "M 0 0 L 1 0 L 1 1 L 0 1 Z M .2 .2 L .3 .2 L .3 .3 L .2 .3 Z "
    a = prefix + "M .300001 .2 L .4 .2 L .4 .3 L .300001 .3 Z"
    b = prefix + "M .3 .2 L .4 .2 L .4 .3 L .3 .3 Z"
    result = compare(a, b)
    assert result["status"] == "UNRESOLVED"
    assert Q(result["max_position_bound_mm_exact"]) < Q(".00002")
    assert Q(result["global_length_difference_bound_mm_exact"]) < Q(".01")
    assert Q(result["net_area_difference_bound_mm2_exact"]) < Q(".01")
    assert "topology" in result["reason"].lower()


def test_global_length_is_accumulated_from_independent_pythagorean_oracle():
    count = 1200
    a = "M 0 0 " + " ".join(f"L {i}e-5 0" for i in range(1, count + 1))
    b = "M 0 0 " + " ".join(f"L {i}e-5 {'1e-5' if i % 2 else '-1e-5'}" for i in range(1, count + 1))
    with localcontext() as context:
        context.prec = 70
        true_difference = (Decimal(2).sqrt() + (count - 1) * Decimal(5).sqrt() - count) / 100000
    assert true_difference > Decimal(".01")
    result = compare(a, b)
    assert result["status"] == "UNRESOLVED"
    assert Q(result["global_length_difference_bound_mm_exact"]) >= Q(true_difference)


def test_semicircle_radius_precision_is_not_pointwise_precision():
    # The chord is a diameter before; changing R by 1e-8 moves its midpoint >0.00044 mm.
    with localcontext() as context:
        context.prec = 80
        radius = Decimal("10.00000001")
        midpoint_shift = Decimal(10) - (radius - (radius * radius - 100).sqrt())
    assert midpoint_shift > Decimal(".00044")
    assert (
        compare("M 0 0 A 10 10 0 0 1 20 0 Z", "M 0 0 A 10.00000001 10.00000001 0 0 1 20 0 Z")[
            "status"
        ]
        == "UNRESOLVED"
    )


@pytest.mark.parametrize(
    "command",
    ["A 10 10 0 1 1 0 10", "A 10 10 0 0 0 0 10", "A 10 11 0 0 1 0 10", "A 10 10 1 0 1 0 10"],
)
def test_native_arc_semantics_cannot_change_even_with_same_endpoints(command):
    assert compare("M 10 0 A 10 10 0 0 1 0 10 Z", f"M 10 0 {command} Z")["status"] == "UNRESOLVED"


def test_translation_and_rotate_list_proves_same_linear_frame_only():
    assert (
        helper.certify_linear_frame("rotate(12) translate(1 2) rotate(5)", "rotate(377,100,200)")[
            "status"
        ]
        == "CERTIFIED_TRANSLATION_ONLY"
    )
    assert (
        helper.certify_linear_frame("rotate(17)", "rotate(17.00000000000001)")["status"]
        == "UNRESOLVED"
    )


def xml_fixture():
    root = ET.Element(
        "{" + probe.NS["s"] + "}svg",
        {"width": "210mm", "height": "297mm", "viewBox": "0 0 210 297"},
    )
    part = ET.SubElement(root, "{" + probe.NS["s"] + "}g", {"id": "part-a", "data-part-id": "a"})
    for role in probe.ROLES:
        group = ET.SubElement(part, "{" + probe.NS["s"] + "}g", {"id": role, "data-role": role})
        ET.SubElement(
            group,
            "{" + probe.NS["s"] + "}path",
            {"id": "path-" + role, "d": "M 0 0 L 10 0 L 0 10 Z"},
        )
    return root


def test_stylesheet_transform_cannot_bypass_xml_frame_guard():
    original = xml_fixture()
    edited = deepcopy(original)
    # Rotation changes the triangle to its complementary half of the square.
    # All path d strings, linear frame attributes AND individual bboxes remain equal.
    style = ET.SubElement(edited, "{" + probe.NS["s"] + "}style")
    style.text = "#path-CUT {transform: rotate(180deg); transform-origin:5px 5px;}"
    source_vertices = ((0, 0), (10, 0), (0, 10))
    changed_vertices = tuple((10 - x, 10 - y) for x, y in source_vertices)

    def bounds(points):
        return tuple((min(p[i] for p in points), max(p[i] for p in points)) for i in (0, 1))

    assert bounds(source_vertices) == bounds(changed_vertices)
    assert (
        max(
            sum((a - b) ** 2 for a, b in zip(p, q))
            for p, q in zip(source_vertices, changed_vertices)
        )
        == 200
    )
    assert (
        probe._same_path(original[0][0][0].attrib["d"], edited[0][0][0].attrib["d"])["status"]
        == "CERTIFIED"
    )
    with pytest.raises(AssertionError):
        probe._part_frame_checks(original, edited)
