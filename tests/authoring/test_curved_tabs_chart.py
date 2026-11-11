"""Independent affine identities and actual endpoint-native-arc transfer cases."""

import math
from dataclasses import replace
from fractions import Fraction as Q

import pytest
from test_curved_tabs_transfer import I2, fixture

from archpapercraft.authoring.curved_tabs import _geometry
from archpapercraft.authoring.curved_tabs import _sqrt as sqrt_bounds
from archpapercraft.authoring.curved_tabs_chart import certify_native_tab_chart
from archpapercraft.authoring.curved_tabs_transfer import TabChartBounds, certify_source_transfer


def packet(rim, tab, matrix=I2, translation=(0, 0), *, rounded=False):
    g = _geometry(rim, tab)

    def point(p):
        result = tuple(
            sum(Q(matrix[i][j]) * p[j] for j in range(2)) + translation[i] for i in range(2)
        )
        return tuple(map(float, result)) if rounded else result

    start = point((-g["xe"], g["fe"]))
    end = point((g["xe"], g["fe"]))
    apex = point((g["offset"], g["depth"]))
    det = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
    if g["slope"]:
        radius = abs(g["radius"] / g["slope"])
        if rounded:
            radius = float(radius)
        sweep = int(g["slope"] < 0) if det > 0 else int(g["slope"] >= 0)
        draw = ("A", radius, radius, 0, 0, sweep, *end)
    else:
        draw = ("L", *end)
    return (("M", *start), draw), apex


def certify(rim, tab, commands, apex, matrix=I2, translation=(0, 0)):
    return certify_native_tab_chart(
        rim,
        tab,
        commands,
        apex,
        matrix,
        translation,
        source_ids=("shell", "rim", tab.tab_id),
        source_digest="a" * 64,
    )


def test_exact_cylinder_fan_is_identity_everywhere_not_just_on_base():
    rim, tabs, *_ = fixture()
    commands, apex = packet(rim, tabs[0])
    result = certify(rim, tabs[0], commands, apex)
    assert result["status"] == "CERTIFIED_NATIVE_CHART", result["problems"]
    assert result["paper_chart_derivative_remainder"] == 0
    assert result["native_chart_position_error_mm"] == 0
    assert result["reference_fan_jacobian_lower"] == Q(6, 25) * Q(19, 2)


@pytest.mark.parametrize("slope", [Q(1, 3), Q(-1, 3), Q(1, 10**20), Q(-1, 10**20)])
@pytest.mark.parametrize("reflection", [False, True])
def test_actual_circular_endpoint_arc_has_whole_fan_proof_including_reflection(slope, reflection):
    rim, tabs, *_ = fixture(slope=slope)
    matrix = ((Q(3, 5), Q(-4, 5)), (Q(4, 5), Q(3, 5)))
    if reflection:
        matrix = (matrix[0], tuple(-v for v in matrix[1]))
    translation = Q(123, 10), Q(456, 10)
    commands, apex = packet(rim, tabs[0], matrix, translation, rounded=True)
    result = certify(rim, tabs[0], commands, apex, matrix, translation)
    assert result["status"] == "CERTIFIED_NATIVE_CHART", result["problems"]
    assert 0 < result["paper_chart_derivative_remainder"] < Q(1, 10**8)
    assert result["actual_fan_jacobian_lower"] > 0
    assert result["actual_fan_halfplane_margin_mm"] > 0
    assert len(result["native_chart_digest"]) == 64


def test_nonzero_apex_shift_derivative_has_independent_affine_oracle():
    rim, tabs, *_ = fixture()
    tab = tabs[0]
    commands, apex = packet(rim, tab)
    epsilon = Q(1, 1000)
    # Base y=0 fixed, apex translated in x. The WHOLE map is the exact shear
    # chi(x,y)=(x+epsilon*y/depth,y), whose operator error is epsilon/depth.
    result = certify(rim, tab, commands, (apex[0] + epsilon, apex[1]))
    assert result["status"] == "CERTIFIED_NATIVE_CHART", result["problems"]
    exact_operator = epsilon / Q(tab.depth_mm)
    assert result["paper_chart_derivative_remainder"] >= exact_operator
    assert result["native_chart_position_error_mm"] == epsilon
    assert result["paper_chart_derivative_remainder"] < Q(1, 100)


@pytest.mark.parametrize("slope", [0, Q(1, 3), Q(-1, 3)])
def test_actual_slot_native_chart_packet_drives_positive_source_transfer(slope):
    args = list(fixture(slope=slope))
    rim, tabs = args[:2]
    charts = []
    for tab in tabs:
        turn = float(tab.center_turn)
        angle = 2 * math.pi * turn / 3 if slope else 0
        # Binary paper frame is handled as its actual exact matrix, then the
        # ACTUAL rounded SVG endpoints get their own fan derivative reserve.
        matrix = ((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle)))
        translation = 123.125, 77.75
        commands, apex = packet(rim, tab, matrix, translation, rounded=True)
        chart = certify(rim, tab, commands, apex, matrix, translation)
        assert chart["status"] == "CERTIFIED_NATIVE_CHART", chart["problems"]
        charts.append(
            TabChartBounds(
                tab.tab_id,
                chart["paper_chart_matrix"],
                chart["paper_chart_derivative_remainder"],
                chart["native_chart_position_error_mm"],
                chart["native_chart_digest"],
            )
        )
    args[4] = replace(
        args[4],
        paper_chart_matrix=(),
        paper_chart_derivative_remainder=None,
        native_chart_position_error_mm=None,
        tab_charts=tuple(charts),
    )
    result = certify_source_transfer(*args)
    assert result["status"] == "CERTIFIED_TRANSFER", result["problems"]
    assert result["source_differential_deformation_total_bound"] < Q(1, 100)
    assert all(row["source_actual_glue_area_bounds_mm2"][0] >= 1 for row in result["tabs"])
    # Losing a single slot's actual-material proof must block the aggregate.
    args[4] = replace(args[4], tab_charts=tuple(charts[:-1]))
    assert certify_source_transfer(*args)["status"] == "UNRESOLVED"


@pytest.mark.parametrize("change", ["side", "semicircle", "ellipse", "collapsed_apex", "cubic"])
def test_wrong_or_unsupported_actual_material_not_given_fake_chart_proof(change):
    rim, tabs, *_ = fixture(slope=Q(1, 3))
    tab = tabs[0]
    commands, apex = packet(rim, tab)
    commands = list(commands)
    if change == "side":
        draw = list(commands[1])
        draw[5] = 1 - draw[5]
        commands[1] = tuple(draw)
    elif change == "semicircle":
        commands[1] = ("A", Q(1, 10), Q(1, 10), 0, 0, 0, *commands[1][-2:])
    elif change == "ellipse":
        draw = list(commands[1])
        draw[2] += 1
        commands[1] = tuple(draw)
    elif change == "cubic":
        commands[1] = ("C", 0, 1, 1, 1, 2, 0)
    else:
        apex = commands[0][1:]
    result = certify(rim, tab, commands, apex)
    assert result["status"] == "UNRESOLVED"
    assert result["problems"]


def test_source_provenance_and_actual_native_commands_bound_chart_digest():
    rim, tabs, *_ = fixture()
    commands, apex = packet(rim, tabs[0])
    first = certify(rim, tabs[0], commands, apex)
    shifted = certify(rim, tabs[0], commands, (apex[0] + Q(1, 1000), apex[1]))
    assert first["native_chart_digest"] != shifted["native_chart_digest"]
    assert first["source_ids"] == ("shell", "rim", tabs[0].tab_id)


@pytest.mark.parametrize("radius,sign", [(10, -1), (20, 1)])
def test_actual_binary_slant30_and_all_actual_slot_arcs_transfer_together(radius, sign):
    args = list(fixture(radius, Q(sign, 3)))
    rim, tabs = args[:2]
    charts = []
    for tab in tabs:
        angle = 2 * math.pi * float(tab.center_turn) / 3
        matrix = ((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle)))
        commands, apex = packet(rim, tab, matrix, (123.125, 77.75), rounded=True)
        chart = certify(rim, tab, commands, apex, matrix, (123.125, 77.75))
        assert chart["status"] == "CERTIFIED_NATIVE_CHART"
        charts.append(
            TabChartBounds(
                tab.tab_id,
                chart["paper_chart_matrix"],
                chart["paper_chart_derivative_remainder"],
                chart["native_chart_position_error_mm"],
                chart["native_chart_digest"],
            )
        )
    h = Q(math.sqrt(800))
    low, high = sqrt_bounds(100 + h * h)
    actual_k = tuple(sorted((sign * Q(10) / low, sign * Q(10) / high)))
    actual_r = Q(radius * 100) * Q(0.01)
    args[4] = replace(
        args[4],
        radius_bounds_mm=(actual_r, actual_r),
        radial_slope_bounds=actual_k,
        tab_charts=tuple(charts),
        world_frame_operator_remainder=Q(1, 10**16),
    )
    args[5] = replace(args[5], radius_error_mm=abs(actual_r - radius))
    result = certify_source_transfer(*args)
    assert result["status"] == "CERTIFIED_TRANSFER", result["problems"]
    assert len(result["native_tab_chart_provenance"]) == 12
    assert all(row["source_actual_glue_area_bounds_mm2"][0] >= 1 for row in result["tabs"])
    assert result["source_differential_deformation_total_bound"] < Q(1, 100)
    assert result["source_provenance"]["native_radial_slope"] == Q(sign, 3)
    assert result["source_provenance"]["radial_slope_bounds"] == actual_k
