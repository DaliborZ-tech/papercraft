"""Independent geometric oracles; no production or historical evidence writes."""

import hashlib
import math
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import pytest

import archpapercraft.authoring.curved_tabs as production
from archpapercraft.authoring.curved_tabs import (
    Cap,
    CircularHole,
    Limits,
    Rim,
    certify_tabs,
    evaluate_tab,
    periodic_tabs,
)

SOURCE_SHA256 = "e64ef4cd8b886735203d7b2a75fbf050af861c7863a27ee2fb026d7024ac9d3b"


def fixture(k=0, *, radius=10, narrow=True, seam=0):
    rim = Rim(radius, k, "source-rim", "source-body", seam)
    cap = Cap(radius, "receiver-disk")
    base, depth, relief = (Q(6, 25), Q(19, 2), Q(3, 5)) if narrow else (Q(2), Q(2), Q(1, 2))
    tabs = periodic_tabs(
        rim, cap.part_id, count=12, nominal_base_mm=base, depth_mm=depth, relief_mm=relief
    )
    limits = Limits(
        Q(1, 100) if narrow else Q(8, 100), Q(1, 100) if narrow else Q(1, 4), 1, Q(1, 5), Q(1, 100)
    )
    return rim, tabs, cap, limits


def decimal(value):
    value = Q(value)
    return Decimal(value.numerator) / Decimal(value.denominator)


def atan_half():
    # Independent alternating series at .5, outside production's _atan domain.
    with localcontext() as context:
        context.prec = 85
        return sum(
            ((-1 if j % 2 else 1) * Decimal(".5") ** (2 * j + 1) / (2 * j + 1) for j in range(180)),
            Decimal(0),
        )


def test_actual_frozen_module_and_exact_source_hash():
    root = Path(__file__).resolve().parents[4]
    path = Path(production.__file__).resolve()
    assert path == root / "src/archpapercraft/authoring/curved_tabs.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_SHA256


@pytest.mark.parametrize(
    "radius,k", [(10, 0), (10, Q(-1, 3)), (20, Q(1, 3)), (10, Q(1, 10**20)), (10, Q(-1, 10**20))]
)
def test_narrow_twelve_slots_exact_glue_and_native_circle_independent_oracle(radius, k):
    rim, tabs, cap, limits = fixture(k, radius=radius)
    report = certify_tabs(rim, tabs, cap, limits)
    assert report["status"] == "CERTIFIED_APPROXIMATE", report["problems"]
    assert len(report["checked_ids"]) == 12
    assert len(report["pairs"]) == report["expected_active_pair_count"] == 66
    assert report["requires_exact_shared_native_base_in_body_adapter"] is True
    assert "ONLY" in report["scope"]
    assert report["physical_status"] == "P3_NOT_RUN_NO_ELASTICITY_OR_ADHESIVE_CLAIM"
    for tab, row in zip(tabs, report["tabs"]):
        r, base, depth, relief = map(Q, (radius, tab.nominal_base_mm, tab.depth_mm, tab.relief_mm))
        parameter = Q(k) * base / (4 * r)
        # Rational circle parameter, independently deriving the flat endpoints.
        x = (r / Q(k)) * 2 * parameter / (1 + parameter**2) if k else base / 2
        y = -(r / Q(k)) * 2 * parameter**2 / (1 + parameter**2) if k else Q(0)
        assert (row["xe"], row["fe"]) == (x, y)
        if k:
            assert x * x + (y + r / Q(k)) ** 2 == (r / Q(k)) ** 2
            assert row["shared_base_commands"][1][0] == "A"
            assert row["shared_base_commands"][1][5] == int(k < 0)
        else:
            assert row["shared_base_commands"][1][0] == "L"
        # Cut at y=relief scales the triangle linearly. Area above that cut is
        # xe*(depth-relief)^2/(depth-fe), not nominal base*depth/2.
        glue = x * (depth - relief) ** 2 / (depth - y)
        assert row["actual_glue_area_bounds_mm2"] == (glue, glue)
        assert glue >= 1
        assert row["differential_deformation_bound"] < Q(1, 100)
        assert row["collar_injectivity_margin"] > 0
        assert all(command[0] != "A" for command in row["cut_side_commands"])


def test_wide_positive_is_only_technical_approximation_not_a_one_percent_claim():
    report = certify_tabs(*fixture(narrow=False))
    assert report["status"] == "CERTIFIED_APPROXIMATE"
    row = report["tabs"][0]
    assert row["actual_glue_area_bounds_mm2"] == (Q(9, 8), Q(9, 8))
    assert row["differential_deformation_bound"] > Q(1, 100)
    rim, tabs, cap, limits = fixture(narrow=False)
    stricter = certify_tabs(rim, tabs, cap, replace(limits, max_differential_deformation=Q(1, 100)))
    assert stricter["status"] == "UNRESOLVED"


@pytest.mark.parametrize("k", [Q(1, 3), Q(-1, 3)])
@pytest.mark.parametrize("t", [Q(-1, 2000), Q(1, 1200), Q(1, 800)])
def test_actual_cone_jacobian_in_unobserved_phase_has_strain_inside_bound(k, t):
    """Pythagorean source angles and cos(phi)=3/5,sin(phi)=4/5.

    k=+/-1/3 makes sin(theta),cos(theta) rational by the triple-angle
    identities. No production evaluator or numerical difference forms J.
    The selected phase lies strictly inside both cone fold intervals.
    """
    rim, tabs, cap, limits = fixture(k)
    report = certify_tabs(rim, tabs[:1], cap, limits)
    assert report["status"] == "CERTIFIED_APPROXIMATE"
    row = report["tabs"][0]
    sf, cf = 2 * t / (1 + t * t), (1 - t * t) / (1 + t * t)
    x = Q(10) * sf / k
    cosine = 4 * cf**3 - 3 * cf
    sine = (1 if k > 0 else -1) * (3 * sf - 4 * sf**3)
    f, fp = Q(10) / k * (cf - 1), -sf / cf
    assert abs(x) < row["xe"]
    with localcontext() as context:
        context.prec = 85
        h = (1 - decimal(k) ** 2).sqrt()
        ar = decimal(k) * Decimal(3) / 5 - h * Decimal(4) / 5
        az = h * Decimal(3) / 5 + decimal(k) * Decimal(4) / 5
        assert az > 0  # Not the generator or the final cap plane.
        rr, xx, ff, fprime, cc, ss = map(decimal, (10, x, f, fp, cosine, sine))
        relief = decimal(tabs[0].relief_mm)
        width = relief - ff
        defect = [rr * cc - rr - ff * ar, rr * ss - xx, -ff * az]
        dx_defect = [-ss / decimal(cf) - fprime * ar, cc / decimal(cf) - 1, -fprime * az]
        for fraction in (Q(1, 13), Q(4, 9), Q(12, 13)):
            alpha = 1 - decimal(fraction)
            alpha_x = alpha * fprime / width
            jx = [
                alpha * d + alpha_x * p + (1 if i == 1 else 0)
                for i, (d, p) in enumerate(zip(dx_defect, defect))
            ]
            jy = [ar - defect[0] / width, -defect[1] / width, az - defect[2] / width]
            aa = sum(z * z for z in jx)
            bb = sum(a * b for a, b in zip(jx, jy))
            ccg = sum(z * z for z in jy)
            discr = ((aa - ccg) ** 2 + 4 * bb * bb).sqrt()
            minimum, maximum = ((aa + ccg - discr) / 2).sqrt(), ((aa + ccg + discr) / 2).sqrt()
            actual = max(1 - minimum, maximum - 1)
            assert actual + Decimal("1e-60") < decimal(row["differential_deformation_bound"])
            assert minimum > 0


def test_cylinder_fold_body_lower_has_independent_all_phase_reference_argument():
    rim, tabs, cap, limits = fixture(narrow=False)
    row = certify_tabs(rim, tabs[:1], cap, limits)["tabs"][0]
    lower = float(row["body_distance_lower_mm"])
    # For generator-reference F=(R-y sin(phi))*r(theta)+y cos(phi)*z,
    # exact distance to the cylinder below z=0 is y at every phi. Thus the
    # proof's subtraction terms must dominate the actual G/F discrepancy.
    for phase in (math.sqrt(2) / 7, 1 / math.pi, math.sqrt(3) / 2):
        for fraction in (-0.91, -0.27, 0.38, 0.96):
            x = fraction * float(row["xe"])
            for y in (0.503, 0.71, 1.02):
                # These points are below the triangle's sides at this x.
                if y > 2 * (1 - abs(x)):
                    continue
                point = evaluate_tab(rim, tabs[0], x, y, phase)
                distance = math.hypot(math.hypot(*point[:2]) - 10, point[2])
                assert distance >= lower


def test_whole_glue_contact_against_exact_apex_hole_sector_area():
    rim, tabs, cap, limits = fixture(narrow=False)
    tab = replace(tabs[0], center_turn=Q(1, 4))
    cap = replace(cap, holes=(CircularHole(0, 8, Q(1, 10)),))
    result = certify_tabs(rim, (tab,), cap, limits)
    row = result["tabs"][0]
    # The radius .1 hole at the triangle apex cuts a wedge sector of area
    # .01*atan(.5). Its circle is inside the cap and cannot reach the far base.
    with localcontext() as context:
        context.prec = 80
        removed = Decimal(".01") * atan_half()
        contact = Decimal(9) / 8 - removed
        low, high = row["actual_glue_area_bounds_mm2"]
        assert decimal(low) < contact < decimal(high)
        assert 0 < decimal(row["proven_uncovered_glue_area_mm2"]) <= removed
        assert decimal(low) > 1  # minGlue alone passes, full support does not.
    assert result["status"] == "INVALID"
    duplicate = certify_tabs(rim, (tab,), replace(cap, holes=cap.holes + cap.holes), limits)
    assert duplicate["tabs"][0]["actual_glue_area_bounds_mm2"] == (low, high)
    assert (
        duplicate["tabs"][0]["proven_uncovered_glue_area_mm2"]
        == row["proven_uncovered_glue_area_mm2"]
    )


@pytest.mark.parametrize("seam", [Q(31, 97), Q(-7, 31), Q(5, 4)])
def test_arbitrary_periodic_seam_turn_keeps_all_slot_and_pair_coverage(seam):
    rim, tabs, cap, limits = fixture(seam=seam)
    result = certify_tabs(rim, tabs, cap, limits)
    assert result["status"] == "CERTIFIED_APPROXIMATE"
    assert len(result["pairs"]) == 66
    for row in result["tabs"]:
        relative = (row["center_turn"] - seam) % 1
        assert relative in {Q(2 * i + 1, 24) for i in range(12)}
    crossing = replace(tabs[0], center_turn=seam + Q(1, 10000))
    failed = certify_tabs(rim, (crossing,), cap, limits)
    assert failed["status"] == "INVALID"
    assert any("seam" in message for _, _, message in failed["problems"])


def test_actual_gap_is_an_interval_and_never_nominal_circumference_subtraction():
    rim, _, cap, limits = fixture(Q(1, 3), narrow=False)
    tabs = periodic_tabs(rim, cap.part_id, count=12, gap_mm=Q(17, 5), depth_mm=2, relief_mm=Q(1, 2))
    result = certify_tabs(rim, tabs, cap, limits)
    assert result["status"] == "CERTIFIED_APPROXIMATE", result["problems"]
    assert all(p["source_gap_bounds_mm"][0] >= Q(17, 5) for p in result["pairs"])
    for row in result["tabs"]:
        assert row["source_arc_length_bounds_mm"][1] < Q(tabs[0].nominal_base_mm)


def test_certain_collision_and_missing_cap_material_survive_unknowns_and_other_budgets():
    rim, tabs, cap, limits = fixture(narrow=False)
    duplicate = replace(tabs[1], center_turn=tabs[0].center_turn)
    report = certify_tabs(
        rim,
        (tabs[0], duplicate),
        cap,
        replace(limits, thickness_mm=None),
        max_cells=0,
        unresolved_obstacle_ids=("unresolved-beam",),
    )
    assert report["status"] == "INVALID"
    assert any("positive-area" in message for _, _, message in report["problems"])
    assert report["unresolved_obstacle_ids"] == ("unresolved-beam",)
    hole = replace(cap, holes=(CircularHole(0, 8, 1),))
    tab = replace(tabs[0], center_turn=Q(1, 4))
    missing = certify_tabs(
        rim,
        (tab,),
        hole,
        replace(limits, thickness_mm=None),
        unresolved_obstacle_ids=("unresolved-beam",),
    )
    assert missing["status"] == "INVALID"
    assert missing["tabs"][0]["proven_uncovered_glue_area_mm2"] > 0


def test_zero_pair_budget_unknown_thickness_and_nonzero_contact_gap_are_not_proofs():
    rim, tabs, cap, limits = fixture()
    assert certify_tabs(rim, tabs, cap, limits, max_pairs=0)["status"] == "UNRESOLVED"
    assert (
        certify_tabs(rim, tabs, cap, replace(limits, thickness_mm=None))["status"] == "UNVERIFIED"
    )
    assert (
        certify_tabs(rim, tabs[:1], replace(cap, plane_offset_mm=Q(1, 10**40)), limits)["status"]
        == "INVALID"
    )
    for args in ({"max_cells": True}, {"max_pairs": -1}, {"max_depth": 25}):
        with pytest.raises(ValueError):
            certify_tabs(rim, tabs, cap, limits, **args)


def test_inventory_off_override_and_source_records_remain_unchanged():
    rim, tabs, cap, limits = fixture()
    before = rim, tabs, cap, limits
    custom = list(tabs)
    custom[1] = replace(custom[1], enabled=False)
    custom[7] = replace(custom[7], tip_offset_mm=Q(1, 1000))
    result = certify_tabs(rim, custom, cap, limits)
    assert result["status"] == "CERTIFIED_APPROXIMATE", result["problems"]
    assert len(result["pairs"]) == 55
    assert set(result["checked_ids"]) == {t.tab_id for t in custom if t.enabled}
    assert result["expected_ids"] == tuple(t.tab_id for t in tabs)
    assert (rim, tabs, cap, limits) == before


def test_ci01_body_and_distinct_receiver_geometry_must_not_share_global_identity():
    rim, tabs, cap, limits = fixture()
    cap = replace(cap, part_id=rim.body_id)
    aliased = tuple(replace(tab, receiver_id=rim.body_id) for tab in tabs)
    result = certify_tabs(rim, aliased, cap, limits)
    assert result["status"] in ("INVALID", "UNRESOLVED"), result["status"]


@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("unknown", [False, True])
def test_ci01_delta_identity_negatives_dominate_unrelated_unknown_material(alias, unknown):
    rim, tabs, cap, limits = fixture()
    if alias:
        cap = replace(cap, part_id=rim.body_id)
        tabs = tuple(replace(tab, receiver_id=rim.body_id) for tab in tabs)
    if unknown:
        limits = replace(limits, thickness_mm=None)
    result = certify_tabs(rim, tabs, cap, limits)
    expected = "INVALID" if alias else "UNVERIFIED" if unknown else "CERTIFIED_APPROXIMATE"
    assert result["status"] == expected
    if alias:
        assert not result["checked_ids"]
        assert any("distinct entity identities" in message for _, _, message in result["problems"])
