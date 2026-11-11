"""Independent analytic source, metric, whole-phase and missing-proof oracles."""

import math
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as Q

import pytest

from archpapercraft.authoring.curved_tabs import (
    Cap,
    CircularHole,
    Limits,
    Rim,
    _sqrt,
    periodic_tabs,
)
from archpapercraft.authoring.curved_tabs_transfer import (
    ANGULAR_KIND,
    CHART_KIND,
    RECEIVER_KIND,
    ReceiverTransferBounds,
    SourceTransferBounds,
    certify_source_transfer,
)

I2 = ((1, 0), (0, 1))
I3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def fixture(radius=10, slope=0):
    rim = Rim(radius, slope, "rim", "body")
    cap = Cap(radius, "cap")
    tabs = periodic_tabs(
        rim, "cap", count=12, nominal_base_mm=Q(6, 25), depth_mm=Q(19, 2), relief_mm=Q(3, 5)
    )
    limits = Limits(Q(1, 100), Q(1, 100), 1, Q(1, 5), Q(1, 100))
    source = SourceTransferBounds(
        (radius, radius),
        (slope, slope),
        "rim",
        "body",
        ("profile-a", "profile-b", "shell"),
        "a" * 64,
        "b" * 64,
        I2,
        0,
        I3,
        0,
        0,
        CHART_KIND,
        ANGULAR_KIND,
        world_frame_position_error_mm=0,
    )
    receiver = ReceiverTransferBounds("cap", ("cap-profile",), "c" * 64, RECEIVER_KIND)
    return rim, tabs, cap, limits, source, receiver


def report(*args, **kwargs):
    result = certify_source_transfer(*args, **kwargs)
    return result


@pytest.mark.parametrize(
    "radius,slope",
    [(10, 0), (10, Q(-1, 3)), (20, Q(1, 3)), (10, Q(1, 10**20)), (10, Q(-1, 10**20))],
)
def test_exact_parameters_still_transfer_with_unchanged_one_percent_and_min_glue(radius, slope):
    result = report(*fixture(radius, slope))
    assert result["status"] == "CERTIFIED_TRANSFER", result["problems"]
    assert result["source_differential_deformation_total_bound"] < Q(1, 100)
    assert result["source_position_total_bound"] < Q(1, 100)
    assert len(result["pairs"]) == result["expected_active_pair_count"] == 66
    assert len(result["checked_ids"]) == 12
    assert result["physical_status"] == "P3_NOT_RUN_NO_ELASTICITY_OR_ADHESIVE_CLAIM"
    assert all(row["source_actual_glue_area_bounds_mm2"][0] >= 1 for row in result["tabs"])


@pytest.mark.parametrize("radius,sign", [(10, -1), (20, 1)])
def test_actual_binary_sqrt800_source_is_not_exact_native_slant30(radius, sign):
    args = list(fixture(radius, Q(sign, 3)))
    # The authored actual H is the exact binary float sqrt(800), not sqrt(800).
    height = Q(math.sqrt(800))
    square = 100 + height * height
    assert square != 900
    slant_low, slant_high = _sqrt(square)
    source_k = sorted((sign * Q(10) / slant_low, sign * Q(10) / slant_high))
    native_k = Q(sign, 3)
    assert not source_k[0] <= native_k <= source_k[1]
    # Independent high precision arithmetic checks the input enclosure.
    with localcontext() as context:
        context.prec = 85
        oracle = (
            Decimal(sign * 10) / (Decimal(square.numerator) / Decimal(square.denominator)).sqrt()
        )
        assert Decimal(source_k[0].numerator) / Decimal(source_k[0].denominator) <= oracle
        assert oracle <= Decimal(source_k[1].numerator) / Decimal(source_k[1].denominator)
    actual_radius = Q(radius * 100) * Q(0.01)
    args[4] = replace(
        args[4],
        radius_bounds_mm=(actual_radius, actual_radius),
        radial_slope_bounds=tuple(source_k),
    )
    args[5] = replace(args[5], radius_error_mm=abs(actual_radius - radius))
    result = report(*args)
    assert result["status"] == "CERTIFIED_TRANSFER", result["problems"]
    row = result["tabs"][0]
    assert 0 < row["source_parameter_delta_slope"] < Q(1, 10**15)
    assert row["source_jacobian_delta_operator_bound"] > 0
    assert row["source_actual_glue_area_bounds_mm2"][0] >= 1
    assert result["source_provenance"]["radial_slope_bounds"] != (native_k, native_k)


@pytest.mark.parametrize("slope", [0, Q(1, 3), Q(-1, 3), Q(1, 10**20)])
def test_tiny_source_chart_and_world_uncertainty_remain_positive(slope):
    args = list(fixture(slope=slope))
    error = Q(1, 10**17)
    args[4] = replace(
        args[4],
        radius_bounds_mm=(10 - error, 10 + error),
        radial_slope_bounds=(slope - error, slope + error),
        paper_chart_derivative_remainder=error,
        world_frame_operator_remainder=error,
        native_chart_position_error_mm=error,
    )
    args[5] = replace(
        args[5], center_error_mm=error, radius_error_mm=error, frame_position_error_mm=error
    )
    result = report(*args)
    assert result["status"] == "CERTIFIED_TRANSFER", result["problems"]
    assert result["source_differential_deformation_total_bound"] < Q(1, 100)


def test_reflected_rotated_paper_chart_uses_metric_not_distance_to_identity():
    args = list(fixture())
    # Exact rational orthogonal reflection and a world quarter turn.
    args[4] = replace(
        args[4],
        paper_chart_matrix=((Q(3, 5), Q(4, 5)), (Q(4, 5), Q(-3, 5))),
        world_frame_matrix=((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    )
    result = report(*args)
    assert result["status"] == "CERTIFIED_TRANSFER", result["problems"]
    assert result["paper_chart_gram_residual_bound"] == 0
    assert result["world_frame_gram_residual_bound"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("paper_chart_derivative_remainder", None),
        ("world_frame_operator_remainder", None),
        ("world_frame_position_error_mm", None),
        ("native_chart_position_error_mm", None),
        ("native_chart_kind", "POSITION_DELTA_ONLY"),
        ("source_angular_correspondence_kind", ""),
        ("source_digest", ""),
        ("source_ids", ()),
        ("rim_id", "wrong-rim"),
    ],
)
def test_missing_whole_derivative_or_binding_never_certified_even_with_zero_position(field, value):
    args = list(fixture())
    args[4] = replace(args[4], **{field: value})
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert result["problems"][-1][0] == "SOURCE_TRANSFER_INPUT_UNRESOLVED"


def test_absent_binding_has_safe_default_not_native_pass():
    result = report(*fixture()[:4])
    assert result["status"] == "UNRESOLVED"
    assert result["native_status"] == "CERTIFIED_APPROXIMATE"


@pytest.mark.parametrize(
    "field,matrix",
    [
        ("paper_chart_matrix", ((1, 0), (0, 0))),
        ("world_frame_matrix", ((1, 0, 0), (0, 1, 0), (0, 0, 0))),
    ],
)
def test_zero_jacobian_is_not_repaired_by_small_position_delta(field, matrix):
    args = list(fixture())
    args[4] = replace(args[4], **{field: matrix})
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert "regularity" in result["problems"][-1][1]


@pytest.mark.parametrize(
    "field,matrix",
    [
        ("paper_chart_matrix", ((2, 0), (0, 1))),
        ("world_frame_matrix", ((Q(11, 10), 0, 0), (0, 1, 0), (0, 0, 1))),
    ],
)
def test_derivative_distortion_cannot_pass_from_position_delta_zero(field, matrix):
    args = list(fixture())
    args[4] = replace(args[4], **{field: matrix})
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert any(
        p[0] in ("SOURCE_STRAIN_BUDGET", "SOURCE_TRANSFER_INPUT_UNRESOLVED")
        for p in result["problems"]
    )


@pytest.mark.parametrize("slope_interval", [(Q(-1), Q(0)), (Q(0), Q(1)), (Q(-99, 100), Q(99, 100))])
def test_large_or_singular_kappa_interval_explicit_unresolved(slope_interval):
    args = list(fixture())
    args[4] = replace(args[4], radial_slope_bounds=slope_interval)
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert result["problems"]


def test_cap_plane_uncertainty_is_not_projected_to_fake_contact():
    args = list(fixture())
    args[5] = replace(args[5], plane_offset_bounds_mm=(0, Q(1, 10**20)))
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert "coplanar" in result["problems"][-1][1]


def test_receiver_radius_and_hole_errors_erode_full_contact_without_changing_min_glue():
    args = list(fixture())
    args[2] = replace(args[2], holes=(CircularHole(0, 0, Q(1, 10)),))
    args[5] = replace(args[5], hole_radius_errors_mm=(0,), hole_center_errors_mm=(0,))
    good = report(*args)
    assert good["status"] == "CERTIFIED_TRANSFER"
    args[5] = replace(args[5], hole_radius_errors_mm=(10,))
    bad = report(*args)
    assert bad["status"] == "UNRESOLVED"
    assert any(p[0] == "SOURCE_FULL_GLUE_COVERAGE_OR_MINIMUM_UNPROVED" for p in bad["problems"])
    assert bad["tabs"][0]["source_actual_glue_area_bounds_mm2"][0] == 0
    assert bad["tabs"][0]["source_actual_glue_area_bounds_mm2"][1] >= 1


def test_large_receiver_frame_allowance_not_silently_dropped():
    args = list(fixture())
    args[5] = replace(args[5], frame_position_error_mm=10)
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert any(p[0] == "SOURCE_RECEIVER_EROSION_EXHAUSTED" for p in result["problems"])


def test_known_native_overlap_remains_visible_with_unrelated_unknown():
    args = list(fixture())
    args[1] = (args[1][0], replace(args[1][1], center_turn=args[1][0].center_turn))
    for unknown in ((), ("unknown-wall",)):
        result = report(*args, unresolved_obstacle_ids=unknown)
        assert result["status"] == "UNRESOLVED"
        assert result["native_status"] == "INVALID"
        assert any("overlap" in p[2] for p in result["native_problems"])
        assert (
            result["source_negative_witnesses"][0]["code"] == "COINCIDENT_POSITIVE_AREA_SOURCE_GLUE"
        )
        assert result["source_negative_witnesses"][0]["area_lower_mm2"] >= 1
        assert result["unresolved_obstacle_ids"] == unknown


def test_finite_budget_and_no_active_material_do_not_transfer():
    args = list(fixture())
    for kwargs in ({"max_cells": 0}, {"max_pairs": 0}):
        result = report(*args, **kwargs)
        assert result["status"] == "UNRESOLVED"
        assert result["total_cells_used"] <= 2 * kwargs.get("max_cells", 10000)
    args[1] = tuple(replace(tab, enabled=False) for tab in args[1])
    assert report(*args)["status"] == "UNRESOLVED"


def test_direction_transfer_inequality_against_independent_angle_identity_all_phases():
    # Analytic proof is |d_k|=(1-t)/sqrt(1-k^2). These off-grid values only
    # cross-check its implementation; positive decisions do NOT use sampling.
    args = list(fixture(slope=Q(1, 3)))
    delta = Q(1, 10**8)
    args[4] = replace(args[4], radial_slope_bounds=(Q(1, 3) - delta, Q(1, 3) + delta))
    bound = report(*args)["tabs"][0]["whole_phase_direction_delta_bound"]
    k0 = 1 / 3
    for k1 in (k0 - float(delta), k0 + float(delta)):
        for phase in (0, 0.019347, 0.381736, 0.731, 1):
            first = phase * math.pi + (1 - phase) * math.acos(k0)
            second = phase * math.pi + (1 - phase) * math.acos(k1)
            assert 2 * abs(math.sin((second - first) / 2)) <= float(bound) * (1 + 1e-7)
    # The final glue direction is exactly (-1,0), independent of k.
    assert math.pi + (1 - 1) * math.acos(k0) == math.pi


def test_source_regular_interval_below_arithmetic_resolution_is_typed_unresolved():
    args = list(fixture())
    k = 1 - Q(1, 10**100)
    args[4] = replace(args[4], radial_slope_bounds=(k, k))
    result = report(*args)
    assert result["status"] == "UNRESOLVED"
    assert result["problems"][-1][0] == "SOURCE_DIRECTION_REGULARITY_PRECISION_UNRESOLVED"


def test_source_derivative_column_bounds_enclose_independent_centerline_oracle():
    args = list(fixture(slope=Q(1, 3)))
    radius_delta, slope_delta = Q(1, 10**6), Q(1, 10**7)
    args[4] = replace(
        args[4],
        radius_bounds_mm=(10 + radius_delta, 10 + radius_delta),
        radial_slope_bounds=(Q(1, 3) + slope_delta, Q(1, 3) + slope_delta),
    )
    row = report(*args)["tabs"][0]
    # At x=0, y=relief/2, alpha=1/2 and f=f'=alpha_x=0:
    # partial_x(Psource-Pnative)=deltaR/(2*Rnative)*tangent.
    assert row["source_jacobian_delta_column_bounds"][0] >= radius_delta / 20
    # At phase0 the y-column is exactly d_source-d_native.
    k0, k1 = 1 / 3, float(Q(1, 3) + slope_delta)
    oracle = math.hypot(k1 - k0, math.sqrt(1 - k1 * k1) - math.sqrt(1 - k0 * k0))
    assert row["source_jacobian_delta_column_bounds"][1] >= Q(oracle) * (1 - Q(1, 10**8))
