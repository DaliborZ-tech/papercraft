"""Actual A SVG/C PDF against independently known circular areas and metrics."""

import copy
import json
import math
from fractions import Fraction as Q
from xml.etree import ElementTree

import pytest
from test_circular_shell import authored
from test_loft_export import assert_actual_reports

from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.circular_output_validation import _cubic_length, coordinate_errors
from archpapercraft.exporter.curve_output_validation import CurveOutputError, read_pdf_cut_regions
from archpapercraft.exporter.loft_output_validation import validate_loft_snapshot


@pytest.mark.parametrize("r1,height,expected", [(10, 30, 600*math.pi),
                                               (20, math.sqrt(800), 900*math.pi),
                                               (10.000001, 30, math.pi*20.000001*30)])
def test_native_body_full_vector_bundle_preserves_arc_kind_and_same_source_norms(
    tmp_path, r1, height, expected
):
    p, sid, pid = authored(10, r1, height)
    p.set_placement(pid, p.pages[0].id, 40, 70, 17)
    bundle = tmp_path / "vectors"
    files = export_all(p.snapshot(), bundle)
    evidence = assert_actual_reports(bundle, sid, pid)
    assert evidence["part_id"] == pid
    svg = next(path for path in files if path.suffix == ".svg")
    root = ElementTree.parse(svg).getroot()
    path = next(e for e in root.iter() if e.attrib.get("id") == f"path-{pid}-CUT-0")
    if r1 != 10:
        assert " A " in path.attrib["d"] and " C " not in path.attrib["d"]
    else:
        assert " A " not in path.attrib["d"]
    actual_pdf = read_pdf_cut_regions(bundle / "model.pdf")["parts"][pid]
    if r1 != 10:
        assert any(c[0] == "C" for c in actual_pdf["loops"][0])
    for kind in ("svg", "pdf"):
        area = list(map(Q, evidence["outputs"][kind]["area_exact"]))
        assert abs(float(sum(area)/2)-expected) < .01
    manifest = json.loads((bundle / ".author-export.json").read_text(encoding="utf8"))
    assert manifest["actual_curve_output_checks"]["lofts"]["status"] == "VERIFIED"


def test_snapshot_native_arc_geometry_cannot_be_relabelled_or_equal_area_translated():
    p, sid, pid = authored()
    p.set_placement(pid, p.pages[0].id, 40, 70)
    original = p.snapshot()
    altered = copy.deepcopy(original)
    commands = altered["pages"][0]["parts"][0]["paths"]["CUT"][0]["commands"]
    for command in commands:
        if command[0] == "A":
            command[-2] += .1
        elif command[0] in ("M", "L"):
            command[1] += .1
    with pytest.raises(CurveOutputError):
        validate_loft_snapshot(altered)
    altered = copy.deepcopy(original)
    altered["construction_checks"]["lofts"][sid]["paper_contract"] = (
        "ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_BOUNDED_COALESCED_CUT_V4")
    with pytest.raises(CurveOutputError):
        validate_loft_snapshot(altered)
    altered = copy.deepcopy(original)
    del altered["construction_checks"]["lofts"][sid]["representation"]["circular_shell"]
    with pytest.raises(CurveOutputError):
        validate_loft_snapshot(altered)


def quarter_source(sweep=1):
    return [["M", 10, 0], ["A", 10, 10, 0, 0, sweep, 0, 10 if sweep else -10], ["Z"]]


def quarter_pdf(sweep=1):
    sign = 1 if sweep else -1
    result = [["M", 10, 0]]
    for i in range(3):
        a, b = sign*math.pi*i/6, sign*math.pi*(i+1)/6
        h = b-a
        p, q = [10*math.cos(a), 10*math.sin(a)], [10*math.cos(b), 10*math.sin(b)]
        result.append(["C", p[0]-h*10*math.sin(a)/3, p[1]+h*10*math.cos(a)/3,
                       q[0]+h*10*math.sin(b)/3, q[1]-h*10*math.cos(b)/3, *q])
    return [*result, ["Z"]]


@pytest.mark.parametrize("sweep", [0, 1])
def test_actual_cubic_chain_has_a_whole_interval_position_and_true_length_bound(sweep):
    position, length = coordinate_errors(quarter_source(sweep), quarter_pdf(sweep))
    assert 0 < position < Q(1, 100)
    assert 0 < length < Q(1, 100)
    poisoned = quarter_pdf(sweep)
    poisoned[1][1] += 1  # Endpoint/area alone cannot certify an interior handle.
    position, _ = coordinate_errors(quarter_source(sweep), poisoned)
    assert position > Q(1, 100)


def test_exact_decimal_native_arc_difference_is_not_lost_to_float():
    original = quarter_source()
    changed = copy.deepcopy(original)
    changed[1][-2] = Q(1, 10**17)
    position, length = coordinate_errors(original, changed)
    assert position > 0 and length > 0
    assert position < Q(1, 1000000)


@pytest.mark.parametrize("damage", ["reverse", "large", "line", "extra"])
def test_native_arc_flags_kind_and_total_coverage_remain_guarded(damage):
    changed = quarter_source()
    if damage == "reverse":
        changed[1][5] = 0
    elif damage == "large":
        changed[1][4] = 1
    elif damage == "line":
        changed[1] = ["L", 0, 10]
    else:
        changed.insert(-1, ["L", 1, 10])
    with pytest.raises(ValueError):
        coordinate_errors(quarter_source(), changed)


def test_actual_cubic_length_budget_exhaustion_is_not_certified():
    with pytest.raises(ValueError, match="budget"):
        _cubic_length(((Q(0), Q(0)), (Q(0), Q(1)), (Q(1), Q(1)), (Q(1), Q(0))),
                      Q(1, 10**30), [99999])
