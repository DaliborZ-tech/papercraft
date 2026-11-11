"""Conditional whole-material native-tab -> actual circular-source transfer.

The binder MUST prove the declared shared native chart and angular identity.
Position closeness is never promoted to a derivative/strain proof. All numeric
bounds below are rational and cover every material point and normalized phase.
No cache report, source mesh, physical-paper or whole-scene claim is accepted.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from .curved_tabs import Cap, CircularHole, _area, _contact, _geometry, _pi, _q, _sqrt, certify_tabs

CHART_KIND = "BOUNDED_NATIVE_SHARED_BASE_CHART"
ANGULAR_KIND = "SAME_ORIENTED_SOURCE_TURN_BY_NATIVE_CHART"
RECEIVER_KIND = "EXACT_COMMON_FRAME_COPLANAR"


def _freeze(value):
    return tuple(_freeze(item) for item in value) if isinstance(value, (list, tuple)) else value


@dataclass(frozen=True)
class TabChartBounds:
    tab_id: str
    paper_chart_matrix: tuple
    paper_chart_derivative_remainder: object
    native_chart_position_error_mm: object
    native_chart_digest: str

    def __post_init__(self):
        object.__setattr__(self, "paper_chart_matrix", _freeze(self.paper_chart_matrix))


@dataclass(frozen=True)
class SourceTransferBounds:
    radius_bounds_mm: tuple
    radial_slope_bounds: tuple
    rim_id: str
    body_id: str
    source_ids: tuple = ()
    source_digest: str = ""
    native_chart_digest: str = ""
    paper_chart_matrix: tuple = ()
    paper_chart_derivative_remainder: object = None
    world_frame_matrix: tuple = ()
    world_frame_operator_remainder: object = None
    native_chart_position_error_mm: object = None
    native_chart_kind: str = ""
    source_angular_correspondence_kind: str = ""
    tab_charts: tuple = ()
    world_frame_position_error_mm: object = None

    def __post_init__(self):
        for name in (
            "radius_bounds_mm",
            "radial_slope_bounds",
            "source_ids",
            "paper_chart_matrix",
            "world_frame_matrix",
            "tab_charts",
        ):
            object.__setattr__(self, name, _freeze(getattr(self, name)))


@dataclass(frozen=True)
class ReceiverTransferBounds:
    part_id: str
    source_ids: tuple = ()
    source_digest: str = ""
    common_frame_kind: str = ""
    plane_offset_bounds_mm: tuple = (0, 0)
    radius_error_mm: object = 0
    center_error_mm: object = 0
    frame_position_error_mm: object = 0
    hole_radius_errors_mm: tuple = ()
    hole_center_errors_mm: tuple = ()

    def __post_init__(self):
        for name in (
            "source_ids",
            "plane_offset_bounds_mm",
            "hole_radius_errors_mm",
            "hole_center_errors_mm",
        ):
            object.__setattr__(self, name, _freeze(getattr(self, name)))


def _interval(value):
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("A complete outward exact interval is required")
    low, high = map(_q, value)
    if low > high:
        raise ValueError("An interval lower endpoint exceeds its upper endpoint")
    return low, high


def _nonnegative(value):
    if value is None:
        raise ValueError("A whole-domain derivative/position bound is missing")
    result = _q(value)
    if result < 0:
        raise ValueError("An uncertainty bound cannot be negative")
    return result


def _identity(ids, digest):
    if (
        not isinstance(ids, tuple)
        or not ids
        or len(set(ids)) != len(ids)
        or any(not isinstance(item, str) or not item for item in ids)
    ):
        raise ValueError("Qualified actual-source identities are required")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise ValueError("A canonical actual-source SHA-256 digest is required")


def _metric(matrix, dimension, remainder):
    """Singular bounds: exact Gram row norm, then Weyl for the supplied reserve."""
    if (
        not isinstance(matrix, tuple)
        or len(matrix) != dimension
        or any(not isinstance(row, tuple) or len(row) != dimension for row in matrix)
    ):
        raise ValueError("A complete actual native/world chart matrix is required")
    matrix = tuple(tuple(_q(item) for item in row) for row in matrix)
    error = max(
        sum(
            abs(sum(matrix[k][i] * matrix[k][j] for k in range(dimension)) - int(i == j))
            for j in range(dimension)
        )
        for i in range(dimension)
    )
    reserve = _nonnegative(remainder)
    lower = max(Fraction(0), _sqrt(max(Fraction(0), 1 - error))[0] - reserve)
    upper = _sqrt(1 + error)[1] + reserve
    return lower, upper, error


def _binding(rim, tabs, cap, source, receiver):
    if not isinstance(source, SourceTransferBounds) or not isinstance(
        receiver, ReceiverTransferBounds
    ):
        raise ValueError("Actual source and actual receiver transfer proofs are required")
    if (
        source.rim_id != rim.rim_id
        or source.body_id != rim.body_id
        or receiver.part_id != cap.part_id
    ):
        raise ValueError("Actual source/rim/body/receiver identity does not match")
    _identity(source.source_ids, source.source_digest)
    _identity(receiver.source_ids, receiver.source_digest)
    _identity(("native-chart",), source.native_chart_digest)
    if source.native_chart_kind != CHART_KIND:
        raise ValueError("Native shared-base chart proof is missing or unsupported")
    if source.source_angular_correspondence_kind != ANGULAR_KIND:
        raise ValueError("Oriented source angular correspondence is unproved")
    if receiver.common_frame_kind != RECEIVER_KIND:
        raise ValueError("Actual receiver common-frame coplanarity is unproved")
    if _interval(receiver.plane_offset_bounds_mm) != (0, 0):
        raise ValueError("A projected receiver is not a proved coplanar contact")
    radius = _interval(source.radius_bounds_mm)
    slope = _interval(source.radial_slope_bounds)
    if radius[0] <= 0 or max(abs(value) for value in slope) >= 1:
        raise ValueError("Actual source radius/regular cone interval is not proved")
    charts = {}
    if source.tab_charts:
        enabled_ids = {tab.tab_id for tab in tabs if tab.enabled}
        for chart in source.tab_charts:
            if not isinstance(chart, TabChartBounds) or chart.tab_id in charts:
                raise ValueError("Unique per-tab whole-material chart proofs are required")
            _identity((chart.tab_id,), chart.native_chart_digest)
            metric = _metric(chart.paper_chart_matrix, 2, chart.paper_chart_derivative_remainder)
            if metric[0] <= 0:
                raise ValueError("Actual per-tab paper chart regularity is not proved")
            charts[chart.tab_id] = metric, _nonnegative(chart.native_chart_position_error_mm)
        if set(charts) != enabled_ids:
            raise ValueError("Per-tab charts must cover precisely all active tab identities")
    else:
        paper = _metric(source.paper_chart_matrix, 2, source.paper_chart_derivative_remainder)
        if paper[0] <= 0:
            raise ValueError("Actual paper/source chart regularity is not proved")
        charts = {
            tab.tab_id: (paper, _nonnegative(source.native_chart_position_error_mm))
            for tab in tabs
            if tab.enabled
        }
    world = _metric(source.world_frame_matrix, 3, source.world_frame_operator_remainder)
    _nonnegative(source.world_frame_position_error_mm)
    if world[0] <= 0:
        raise ValueError("Actual paper/source chart regularity is not proved")
    for value in (
        receiver.radius_error_mm,
        receiver.center_error_mm,
        receiver.frame_position_error_mm,
    ):
        _nonnegative(value)
    if len(receiver.hole_radius_errors_mm) != len(cap.holes) or len(
        receiver.hole_center_errors_mm
    ) != len(cap.holes):
        raise ValueError("Every actual receiver hole needs its own uncertainty bound")
    for value in (*receiver.hole_radius_errors_mm, *receiver.hole_center_errors_mm):
        _nonnegative(value)
    return radius, slope, charts, world


def certify_source_transfer(
    rim,
    tabs,
    cap,
    limits,
    binding=None,
    receiver=None,
    *,
    max_cells=10000,
    max_depth=14,
    max_pairs=10000,
    unresolved_obstacle_ids=(),
):
    """CERTIFIED_TRANSFER is conditional on the explicit current binder proofs.

    The chart derivative remainder bounds D(chi)-A over the ENTIRE tab material;
    chi must be the proved bijective shared-base chart onto actual native paper.
    Its position reserve is a separate geometric allowance, never a strain bound.
    Q's remainder bounds the actual source-frame linear operator, not samples.
    Receiver allowances are in-plane in the SAME exact coplanar source frame.
    Caller must establish these identities against source/native commands; this
    math component records their IDs/digests but cannot inspect a project registry.
    """
    tabs, unknown = tuple(tabs), tuple(unresolved_obstacle_ids)
    baseline = certify_tabs(
        rim,
        tabs,
        cap,
        limits,
        max_cells=max_cells,
        max_depth=max_depth,
        max_pairs=max_pairs,
        unresolved_obstacle_ids=unknown,
    )
    result = {
        "status": "UNRESOLVED",
        "native_status": baseline["status"],
        "method": "WHOLE_MATERIAL_SOURCE_PARAMETER_AND_CHART_WEYL_TRANSFER",
        "scope": baseline["scope"],
        "physical_status": baseline["physical_status"],
        "fold_scope": "ALL_NORMALIZED_PHASES_T_IN_0_1_INDEPENDENT_FOR_EACH_TAB",
        "conditions": (CHART_KIND, ANGULAR_KIND, RECEIVER_KIND),
        "binder_identity_check": "CALLER_MUST_PROVE_CURRENT_SOURCE_AND_NATIVE_SHARED_BASE",
        "native_problems": baseline["problems"],
        "source_negative_witnesses": [],
        "problems": [],
        "tabs": [],
        "pairs": [],
        "unresolved_obstacle_ids": unknown,
        "expected_ids": baseline["expected_ids"],
        "checked_ids": (),
        "cells_used": 0,
        "native_cells_used": baseline["cells_used"],
    }
    # Native known negatives remain visible even if an unrelated binder is
    # absent. They are not silently relabelled as proved actual-source witnesses.
    if baseline["status"] != "CERTIFIED_APPROXIMATE":
        result["problems"].append(("NATIVE_PROOF_NOT_POSITIVE", baseline["status"]))
    try:
        radius, slope, charts, world = _binding(rim, tabs, cap, binding, receiver)
    except (ValueError, TypeError, OverflowError) as exc:
        result["problems"].append(("SOURCE_TRANSFER_INPUT_UNRESOLVED", str(exc)))
        return result
    result["source_provenance"] = {
        "source_ids": binding.source_ids,
        "source_digest": binding.source_digest,
        "native_chart_digest": binding.native_chart_digest,
        "receiver_source_ids": receiver.source_ids,
        "receiver_source_digest": receiver.source_digest,
        "radius_bounds_mm": radius,
        "radial_slope_bounds": slope,
        "native_radius_mm": _q(rim.radius_mm),
        "native_radial_slope": _q(rim.radial_slope),
    }
    result["native_tab_chart_provenance"] = (
        tuple((chart.tab_id, chart.native_chart_digest) for chart in binding.tab_charts)
        if binding.tab_charts
        else tuple((tab.tab_id, binding.native_chart_digest) for tab in tabs if tab.enabled)
    )
    result["paper_chart_singular_bounds"] = {
        identity: data[0][:2] for identity, data in charts.items()
    }
    result["world_frame_singular_bounds"] = world[:2]
    result["paper_chart_gram_residual_bound"] = max(
        (data[0][2] for data in charts.values()), default=0
    )
    result["world_frame_gram_residual_bound"] = world[2]
    native_r, native_k = _q(rim.radius_mm), _q(rim.radial_slope)
    dr = max(abs(value - native_r) for value in radius)
    dk = max(abs(value - native_k) for value in slope)
    max_k = max(abs(value) for value in (*slope, native_k))
    h = _sqrt(1 - max_k * max_k)[0]
    if h <= 0:
        result["problems"].append(("SOURCE_DIRECTION_REGULARITY_PRECISION_UNRESOLVED", None))
        return result
    # d(k,t)=(cos[t*pi+(1-t)*acos(k)],sin[...]); |partial_k d|=(1-t)/h.
    dd = dk / h
    budget = [max_cells]
    geometries = {}
    for tab in tabs:
        if not tab.enabled:
            result["tabs"].append({"tab_id": tab.tab_id, "status": "OFF"})
            continue
        try:
            g = _geometry(rim, tab)
        except ValueError:
            continue  # Full native typed failure is already retained above.
        paper, chart_position = charts[tab.tab_id]
        a = g["half_angle"][1]
        cosine = 1 - (native_k * a) ** 2 / 2
        f = native_r * abs(native_k) * a * a / 2
        fp = abs(native_k) * a / cosine
        collar = g["relief"] - f
        dx = dr * (fp * a / collar + 1 / (native_r * cosine)) + fp * (1 + f / collar) * dd
        dy = dr * a / collar + (1 + f / collar) * dd
        derivative = _sqrt(dx * dx + dy * dy)[1]
        native_strain = g["differential_deformation_bound"]
        minimum = world[0] * max(Fraction(0), 1 - native_strain - derivative) / paper[1]
        maximum = world[1] * (1 + native_strain + derivative) / paper[0]
        strain = max(1 - minimum, maximum - 1)
        source_displacement = g["position_bound_mm"] + dr * a + f * dd
        # Position and derivative reserves remain separate all the way through.
        pose_position = _nonnegative(binding.world_frame_position_error_mm) + _nonnegative(
            binding.world_frame_operator_remainder
        ) * (radius[1] + g["depth"] + g["xe"] + f)
        position = world[1] * source_displacement + chart_position * maximum + pose_position
        transfer_delta = (
            world[1] * (dr + g["depth"] * dd) + chart_position * maximum + pose_position
        )
        source_tangent_defect = dr * a + (radius[1] + native_r * native_k * native_k) * a**3 / 6
        body = (
            world[0]
            * (g["relief"] * h - radius[1] * a * a / 2 - source_tangent_defect - g["depth"] * a)
            - chart_position * maximum
        )
        tx_min = min(Fraction(1), radius[0] * (1 - a * a / 2) / native_r)
        injectivity = tx_min * (
            1 - radius[1] * a * a / (2 * g["relief"])
        ) - source_tangent_defect / g["relief"] * radius[1] * a / (native_r * cosine)
        row = {
            "tab_id": tab.tab_id,
            "native_center_turn": _q(tab.center_turn) % 1,
            "native_source_half_angle_bounds_radians": g["half_angle"],
            "coverage": "ENTIRE_NATIVE_TAB_MATERIAL_AND_ALL_NORMALIZED_FOLD_PHASES",
            "source_parameter_delta_radius_mm": dr,
            "source_parameter_delta_slope": dk,
            "native_chart_position_error_mm": chart_position,
            "whole_phase_direction_delta_bound": dd,
            "source_jacobian_delta_column_bounds": (dx, dy),
            "source_jacobian_delta_operator_bound": derivative,
            "source_singular_value_bounds": (minimum, maximum),
            "source_differential_deformation_total_bound": strain,
            "source_position_total_bound": position,
            "source_to_native_map_position_delta_bound": transfer_delta,
            "source_world_pose_position_allowance_mm": pose_position,
            "source_body_distance_lower_mm": body,
            "source_final_collar_injectivity_margin": injectivity,
            "status": "BOUNDED",
        }
        result["tabs"].append(row)
        geometries[tab.tab_id] = (g, _q(tab.center_turn) % 1, source_displacement, row)
        required = (
            (_q(limits.thickness_mm) if limits.thickness_mm is not None else 0)
            + _q(limits.clearance_mm)
            + 2 * _q(limits.bend_radius_mm)
        )
        for condition, valid in (
            ("SOURCE_RADIUS_DOES_NOT_CLEAR_MATERIAL", radius[0] > g["depth"]),
            ("SOURCE_STRAIN_BUDGET", strain <= _q(limits.max_differential_deformation)),
            ("SOURCE_POSITION_BUDGET", position <= _q(limits.max_position_mm)),
            ("SOURCE_REGULARITY", minimum > 0),
            ("SOURCE_GLOBAL_COLLAR_INJECTIVITY", injectivity > 0),
            ("SOURCE_BODY_SEPARATION", body > required),
            (
                "SOURCE_RECEIVER_FOLD_ENVELOPE",
                g["relief"] * h * world[0]
                > (_q(limits.thickness_mm) if limits.thickness_mm is not None else 0)
                * max(Fraction(0), slope[1])
                * world[1],
            ),
        ):
            if not valid:
                result["problems"].append((condition, tab.tab_id))
        # At t=1 d=-r0 EXACTLY for every source k. The rigid glue differs
        # only by dr*r0, never by an out-of-plane projection or a k rotation.
        erosion = (
            dr
            + chart_position * maximum / world[0]
            + _nonnegative(receiver.center_error_mm)
            + _nonnegative(receiver.frame_position_error_mm)
        )
        outer = _q(cap.radius_mm) - _nonnegative(receiver.radius_error_mm) - erosion
        holes = tuple(
            CircularHole(
                hole.x_mm,
                hole.y_mm,
                _q(hole.radius_mm) + erosion + _nonnegative(re) + _nonnegative(ce),
            )
            for hole, re, ce in zip(
                cap.holes, receiver.hole_radius_errors_mm, receiver.hole_center_errors_mm
            )
        )
        row["contact_erosion_allowance_mm"] = erosion
        if outer <= 0:
            result["problems"].append(("SOURCE_RECEIVER_EROSION_EXHAUSTED", tab.tab_id))
            continue
        robust = Cap(outer, cap.part_id, holes)
        low, high, outside = _contact(
            g["glue_triangle_local"],
            _q(tab.center_turn) % 1,
            robust,
            budget,
            max_depth,
            _q(limits.area_uncertainty_mm2),
        )
        full_area = _area(g["glue_triangle_local"])
        area = low * world[0] * world[0], full_area * world[1] * world[1]
        row["source_actual_glue_area_bounds_mm2"] = area
        row["nominal_area_not_robustly_covered_mm2"] = outside
        row["contact_area_erosion_budget_mm2"] = full_area - low
        if low != high or outside or area[0] < _q(limits.min_glue_area_mm2):
            result["problems"].append(("SOURCE_FULL_GLUE_COVERAGE_OR_MINIMUM_UNPROVED", tab.tab_id))
        circumference = 2 * _pi()[0] - 2 * a
        row["source_period_gap_lower_mm"] = world[0] * radius[0] * circumference
        if row["source_period_gap_lower_mm"] < _q(tab.requested_min_gap_mm):
            result["problems"].append(("SOURCE_PERIOD_GAP_UNPROVED", tab.tab_id))
    for first, second in combinations(geometries, 2):
        if len(result["pairs"]) >= max_pairs:
            result["problems"].append(("SOURCE_SIBLING_PAIR_BUDGET", None))
            break
        g1, turn1, ds1, _ = geometries[first]
        g2, turn2, ds2, _ = geometries[second]
        if turn1 == turn2 and g1["glue_triangle_local"] == g2["glue_triangle_local"]:
            result["source_negative_witnesses"].append(
                {
                    "code": "COINCIDENT_POSITIVE_AREA_SOURCE_GLUE",
                    "tab_ids": (first, second),
                    "area_lower_mm2": _area(g1["glue_triangle_local"]) * world[0] * world[0],
                    "proof": "Same final source maps for all common R/k; Q is regular",
                }
            )
        distance = min(abs(turn1 - turn2), 1 - abs(turn1 - turn2))

        def sector(g):
            f = native_r * abs(native_k) * g["half_angle"][1] ** 2 / 2
            if radius[0] <= max(f, g["depth"]):
                return None
            return max(g["xe"] / (radius[0] - f), abs(g["offset"]) / (radius[0] - g["depth"]))

        sectors = sector(g1), sector(g2)
        if None in sectors:
            result["problems"].append(("SOURCE_SIBLING_RADIUS_UNPROVED", (first, second)))
            continue
        delta = 2 * _pi()[0] * distance - sum(sectors)
        rmin = radius[0] - max(g1["depth"], g2["depth"])
        lower = (
            (2 * rmin * (delta / 2 - (delta / 2) ** 3 / 6) if delta > 0 else Fraction(0))
            - ds1
            - ds2
        )
        lower = world[0] * lower - sum(
            geometries[identity][3]["native_chart_position_error_mm"]
            * geometries[identity][3]["source_singular_value_bounds"][1]
            for identity in (first, second)
        )
        angular_gap = 2 * _pi()[0] * distance - g1["half_angle"][1] - g2["half_angle"][1]
        gap = (radius[0] if angular_gap >= 0 else radius[1]) * angular_gap
        gap *= world[0] if gap >= 0 else world[1]
        pair = {
            "tab_ids": (first, second),
            "source_whole_phase_distance_lower_mm": lower,
            "source_gap_lower_mm": gap,
        }
        result["pairs"].append(pair)
        requested = max(
            _q(tab.requested_min_gap_mm) for tab in tabs if tab.tab_id in (first, second)
        )
        if lower <= required or gap < requested:
            result["problems"].append(("SOURCE_SIBLING_DISTANCE_OR_GAP_UNPROVED", (first, second)))
    result["checked_ids"] = tuple(geometries)
    result["expected_active_pair_count"] = len(geometries) * (len(geometries) - 1) // 2
    result["cells_used"] = max_cells - budget[0]
    result["total_cells_used"] = result["cells_used"] + result["native_cells_used"]
    enabled = [row for row in result["tabs"] if row["status"] != "OFF"]
    if enabled:
        result["source_position_total_bound"] = max(
            row["source_position_total_bound"] for row in enabled
        )
        result["source_differential_deformation_total_bound"] = max(
            row["source_differential_deformation_total_bound"] for row in enabled
        )
    if not result["problems"]:
        result["status"] = "CERTIFIED_TRANSFER"
    return result
