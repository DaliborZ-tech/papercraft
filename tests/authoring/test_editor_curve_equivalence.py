"""Independent editor oracles, including the recorded near-cylinder failure."""

import importlib.util
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "editor_probe_equivalence_test", ROOT / "tools/authoring/editor_probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
helper = probe._equivalence_module()


def compare(first, second, **budgets):
    return helper.certify_path_equivalence(
        probe._path_signature(first), probe._path_signature(second), **budgets
    )


def test_all_actual_recorded_near_paths_and_frames_have_bounded_equivalence():
    evidence = ROOT / "docs/p2/implementation/evidence"
    fixture = json.loads((evidence / "editor-near-failed-5283632-paths.json").read_text("utf-8"))
    assert len(fixture["paths"]) == 23
    totals = {}
    for pair in fixture["paths"]:
        proof = compare(pair["before"], pair["after"])
        assert proof["status"] == "CERTIFIED", proof
        assert Q(proof["max_position_bound_mm_exact"]) <= Q(1, 50000)
        role = pair["id"].rsplit("-", 2)[1]
        length, area = totals.get(role, (Q(0), Q(0)))
        totals[role] = (
            length + Q(proof["global_length_difference_bound_mm_exact"]),
            area + Q(proof["net_area_difference_bound_mm2_exact"]),
        )
    assert all(length <= Q(1, 100) and area <= Q(1, 100) for length, area in totals.values())
    for pair in fixture["frames"]:
        assert helper.certify_linear_frame(pair["before"], pair["after"])["status"] == (
            "CERTIFIED_TRANSLATION_ONLY"
        )
    assert all(a == b for a, b in fixture["physical_page"].values())
    original = json.loads((evidence / "editor-near-original-failure.json").read_text("utf-8"))
    assert original["status"] == "FAIL"


def test_large_radius_harmless_rounding_is_bounded_against_independent_decimal_sag():
    first = "M 0 0 A 30000000.0041217 30000000.0041217 0 0 1 15.70797898 0 Z"
    second = "M 0 0 A 30000000 30000000 0 0 1 15.70797898 0 Z"
    proof = compare(first, second)
    assert proof["status"] == "CERTIFIED", proof
    with localcontext() as ctx:
        ctx.prec = 110
        a, b, half = Decimal("30000000.0041217"), Decimal(30000000), Decimal("15.70797898") / 2
        actual = abs((a - (a * a - half * half).sqrt()) - (b - (b * b - half * half).sqrt()))
        bound = Q(proof["max_position_bound_mm_exact"])
        assert Q(actual) <= bound < Q("1.4125e-16")


def test_semicircle_small_operand_change_is_large_geometry_change():
    first = "M 0 0 A 10 10 0 0 1 20 0 Z"
    second = "M 0 0 A 10.00001 10.00001 0 0 1 20 0 Z"
    with localcontext() as ctx:
        ctx.prec = 70
        radius = Decimal("10.00001")
        drift = abs(radius - (radius * radius - 100).sqrt() - 10)
        assert drift > Decimal(".01413")
    assert compare(first, second)["status"] == "UNRESOLVED"
    assert compare(first, first)["status"] == "CERTIFIED"


def test_accumulated_length_cannot_reset_at_each_small_segment():
    count = 1001
    first = "M 0 0 " + " ".join(f"L {i}e-5 0" for i in range(1, count + 1))
    second = "M 0 0 " + " ".join(
        f"L {i}e-5 {'1e-5' if i % 2 else '-1e-5'}" for i in range(1, count + 1)
    )
    with localcontext() as ctx:
        ctx.prec = 60
        actual = (Decimal(2).sqrt() + (count - 1) * Decimal(5).sqrt() - count) / 100000
        assert actual > Decimal(".01")
    proof = compare(first, second)
    assert proof["status"] == "UNRESOLVED"
    assert Q(proof["max_position_bound_mm_exact"]) <= Q(".00002")
    assert Q(proof["global_length_difference_bound_mm_exact"]) > Q(".01")


def test_direct_area_blocks_long_rectangle_despite_position_and_length_passing():
    proof = compare(
        "M 0 0 L 1100 0 L 1100 10 L 0 10 Z",
        "M 0 0 L 1100 0 L 1100 10.00001 L 0 10.00001 Z",
    )
    assert proof["status"] == "UNRESOLVED"
    assert Q(proof["max_position_bound_mm_exact"]) == Q(".00001")
    assert Q(proof["global_length_difference_bound_mm_exact"]) < Q(".01")
    assert Q(proof["net_area_difference_bound_mm2_exact"]) >= Q(".011")


def test_native_cubic_positive_and_independent_midpoint_negative():
    first = "M 0 0 C 10 20 30 20 40 0 L 40 -10 L 0 -10 Z"
    good = "M 0 0 C 10 20.000001 30 20 40 0 L 40 -10 L 0 -10 Z"
    bad = "M 0 0 C 10 20.001 30 20 40 0 L 40 -10 L 0 -10 Z"
    assert compare(first, good)["status"] == "CERTIFIED"
    assert Q(3, 8) * Q(".001") > Q(".00002")  # exact cubic midpoint displacement
    assert compare(first, bad)["status"] == "UNRESOLVED"


def test_direct_cubic_green_matches_analytic_arch_integral():
    # x=3t²-2t³, y=3t-3t²; integral y dx = 3/5, clockwise signed Green -3/5.
    primitive = ("C", (Q(0), Q(0)), ("C", Q(0), Q(1), Q(1), Q(1), Q(1), Q(0)))
    assert helper._green(primitive) == (Q(-3, 5), Q(-3, 5))


def test_quarter_arc_green_encloses_independent_analytic_pi_interval():
    primitive = ("A", (Q(10), Q(0)), ("A", Q(10), Q(10), Q(0), Q(0), Q(1), Q(0), Q(10)))
    lower, upper = helper._green(primitive)
    # The chord contributes 50 and the circular segment 25π-50, net 25π.
    pi_lower = Q(
        "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899"
    )
    pi_upper = pi_lower + Q(1, 10**80)
    assert lower <= 25 * pi_upper and upper >= 25 * pi_lower
    assert upper - lower < Q(1, 10**70)


def test_quarter_circle_positive_and_native_flags_preserved():
    first = "M 10 0 A 10 10 0 0 1 0 10 Z"
    good = "M 10 0 A 10.0000001 10.0000001 0 0 1 0 10 Z"
    assert compare(first, good)["status"] == "CERTIFIED"
    for changed in (
        "M 10 0 A 10 10 0 0 0 0 10 Z",
        "M 10 0 A 10 10 0 1 1 0 10 Z",
        "M 10 0 A 10 11 0 0 1 0 10 Z",
    ):
        assert compare(first, changed)["status"] == "UNRESOLVED"


@pytest.mark.parametrize(
    "first,second",
    [
        (
            "M 0 0 L 1 0 L 1 .000005 L 0 .000005 Z",
            "M 0 0 L 1 0 L 1 -.000005 L 0 -.000005 Z",
        ),
        (
            "M 0 0 L 1 0 L 1 1 L 0 1 Z M .000001 .3 L .000005 .3 L .000005 .7 L .000001 .7 Z",
            "M 0 0 L 1 0 L 1 1 L 0 1 Z M -.000005 .3 L -.000001 .3 L -.000001 .7 L -.000005 .7 Z",
        ),
    ],
)
def test_small_metric_changes_do_not_approve_collapsing_or_escaping_material(first, second):
    proof = compare(first, second)
    assert proof["status"] == "UNRESOLVED", proof
    assert Q(proof["max_position_bound_mm_exact"]) <= Q(".00002")


@pytest.mark.parametrize(
    "budgets", [{"max_work": 1}, {"max_depth": 0}, {"max_commands": 1}, {"max_work": True}]
)
def test_finite_work_limits_fail_closed(budgets):
    assert (
        compare("M 0 0 L 1 0 L 1 1 Z", "M 0 0 L 1 0 L 1 1.000001 Z", **budgets)["status"]
        == "UNRESOLVED"
    )


@pytest.mark.parametrize(
    "changed", ["matrix(1 0 0 1 0 0)", "scale(1)", "skewX(0)", "rotate(17.0000001)"]
)
def test_linear_frame_does_not_hide_scale_skew_matrix_or_angle_change(changed):
    assert helper.certify_linear_frame("rotate(17)", changed)["status"] == "UNRESOLVED"


def test_unknown_path_characters_do_not_disappear_in_parser():
    with pytest.raises(AssertionError, match="Unknown SVG path syntax"):
        probe._same_path("M 0 0 L 10 0", "M 0 0 ! L 10 0")


@pytest.mark.parametrize("damage", ["nested_scale", "role", "units", "css", "extra_geometry"])
def test_actual_xml_frame_guard_rejects_hidden_operator_role_or_unit_changes(damage):
    root = ET.Element(
        "{" + probe.NS["s"] + "}svg",
        {"width": "210mm", "height": "297mm", "viewBox": "0 0 210 297"},
    )
    group = ET.SubElement(
        root,
        "{" + probe.NS["s"] + "}g",
        {"id": "part-a", "data-part-id": "a", "transform": "translate(55 90) rotate(17)"},
    )
    for role in probe.ROLES:
        role_group = ET.SubElement(
            group, "{" + probe.NS["s"] + "}g", {"id": role, "data-role": role}
        )
        ET.SubElement(role_group, "{" + probe.NS["s"] + "}path", {"id": "path-" + role})
    edited = deepcopy(root)
    edited[0].set("transform", "rotate(17,-285.55688,239.84301)")
    assert probe._part_frame_checks(root, edited)
    if damage == "nested_scale":
        edited[0][0].set("transform", "scale(1.000001)")
    elif damage == "role":
        edited[0][0][0].set("id", "path-other-role")
    elif damage == "units":
        edited.set("width", "210px")
    elif damage == "css":
        edited[0][0].set("style", "transform:scale(1)")
    else:
        ET.SubElement(edited, "{" + probe.NS["s"] + "}rect")
    with pytest.raises(AssertionError):
        probe._part_frame_checks(root, edited)
