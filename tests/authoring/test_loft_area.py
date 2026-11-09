"""Independent analytic expectations for intrinsic, not projected loft area."""

import json
import math
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_area import certify_loft_intrinsic_area
from archpapercraft.authoring.loft_geometry import LoftCorrespondence, LoftProfile, flatten_loft

PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628"
)


def _circle(radius, *, depth=0, prefix="a", sweep=180, basis=None, origin=None):
    angle = math.radians(sweep)
    end = (radius * math.cos(angle), radius * math.sin(angle))
    # Canonical exact endpoints avoid introducing extra binary discrepancies in
    # the positive homothety proof. Geometry is center/start/signed sweep.
    if abs(sweep) == 180:
        end = (-radius, 0)
    curve = Curve((radius, 0), end, "arc", {"center": (0, 0), "sweep_deg": sweep}, prefix)
    options = {} if basis is None else dict(u=basis[0], v=basis[1])
    return LoftProfile((curve,), origin=origin or (0, 0, depth), profile_id=prefix, **options)


def _refs(first, second, *, reverse=False):
    pairs = list(zip(first.curves, second.curves))
    if reverse:
        pairs.reverse()
    interval = (1, 0) if reverse else (0, 1)
    return tuple(
        LoftCorrespondence(a.segment_id, b.segment_id, interval, interval) for a, b in pairs
    )


def _bounds(result):
    assert result["status"] == "CERTIFIED", result
    lower, upper = Fraction(result["area_lower_exact"]), Fraction(result["area_upper_exact"])
    assert 0 < lower <= upper
    assert upper - lower <= Fraction(result["absolute_budget_mm2"])
    assert Fraction(result["area_lower_paper_mm2"]) <= lower
    assert Fraction(result["area_upper_paper_mm2"]) >= upper
    assert (
        result["proof"]["scope"] == "INTRINSIC_AREA_ONLY_NOT_A_FLATTENING_OR_TOPOLOGY_CERTIFICATE"
    )
    json.dumps(result, allow_nan=False)
    return lower, upper


def _contains(result, expected):
    lower, upper = _bounds(result)
    assert lower <= Fraction(expected) <= upper


@pytest.mark.parametrize("height", [200, -200])
@pytest.mark.parametrize("scale", [1, 0.01])
def test_normal_semicircle_area_is_analytic_4000pi_not_flat_rectangle(height, scale):
    first, second = _circle(20), _circle(20, depth=height, prefix="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=scale)
    with localcontext() as context:
        context.prec = 80
        expected = 4000 * PI * Decimal.from_float(float(scale)) ** 2
        _contains(result, expected)
    assert result["examined_nodes"] == 1


def test_ld02_actual_flat_rectangle_can_pass_position_and_length_but_fail_area():
    first, second = _circle(20), _circle(20, depth=200, prefix="b")
    development = flatten_loft(first, second, _refs(first, second), scale=1)
    assert development["status"] == "EXACT"
    assert development["representation_error_bound_paper_mm"] <= 0.005
    assert development["boundary_length_error_bound_paper_mm"] <= 0.005
    patch = development["patches"][0]
    old_native_rectangle_area = patch["flat_first_paper_mm"][-1][0] * 200
    analytic = 4000 * math.pi
    assert analytic - old_native_rectangle_area > max(0.01, analytic * 1e-6)
    assert analytic - old_native_rectangle_area == pytest.approx(0.0571386496, abs=1e-8)
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1)
    lower, _ = _bounds(result)
    assert lower - Fraction(old_native_rectangle_area) > Fraction("0.05")


@pytest.mark.parametrize("r0,r1,height", [(10, 20, 28), (20, 10, 28), (20, 24, -10)])
def test_circular_cone_half_frustum_slant_formula(r0, r1, height):
    first, second = _circle(r0), _circle(r1, depth=height, prefix="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1)
    with localcontext() as context:
        context.prec = 80
        slant = Decimal((r1 - r0) ** 2 + height**2).sqrt()
        _contains(result, PI * (r0 + r1) * slant / 2)


@pytest.mark.parametrize("reverse", [False, True])
def test_coplanar_concentric_band_exact_area_and_oriented_coverage(reverse):
    first, second = _circle(20), _circle(24, prefix="b")
    result = certify_loft_intrinsic_area(
        first, second, _refs(first, second, reverse=reverse), scale=1
    )
    with localcontext() as context:
        context.prec = 80
        _contains(result, PI * (24**2 - 20**2) / 2)
    assert result["coverage"]["first_profile_id"] == "a"
    assert result["coverage"]["second_profile_id"] == "b"
    assert result["coverage"]["correspondences"][0]["first_parameter_interval"] == (
        [1, 0] if reverse else [0, 1]
    )


def _gothic(prefix, *, large=False, xz=False):
    width, height, depth = (24, 36, 10) if large else (20, 30, 0)
    center = (height * height - width * width) / (2 * width)
    sweep = math.degrees(math.atan2(height, -center)) - 180
    curves = (
        Curve(
            (-width, 0),
            (0, height),
            "arc",
            {"center": (center, 0), "sweep_deg": sweep},
            prefix + "L",
        ),
        Curve(
            (0, height),
            (width, 0),
            "arc",
            {"center": (-center, 0), "sweep_deg": sweep},
            prefix + "R",
        ),
        Curve((width, 0), (-width, 0), segment_id=prefix + "B"),
    )
    return LoftProfile(
        curves,
        origin=(0, depth, 0) if xz else (0, 0, depth),
        v=(0, 0, 1) if xz else (0, 1, 0),
        profile_id=prefix,
        closed=True,
    )


def _gothic_oracle(sweep):
    """Independent rational half-angle integral, 80-digit Simpson enclosure.

    For one arc, radius R=32.5, center c=12.5, k-1=.2, H=10.
    t=tan(alpha/2) gives g(t)=65 sqrt(116+272t²+181t⁴)/(1+t²)²,
    t in [0,2/3]. This uses neither production cross products nor trig nodes.

    A deliberately loose M4=1e8 is valid: P=116+272t²+181t⁴ has
    |P'|<600, |P''|<1600, |P'''|<3000, |P''''|<4400 and sqrt(P)>10.
    The sqrt chain rule gives derivative bounds (18,30,170,1800,31000).
    For (1+t²)^-2 the bounds are (1,3,15,105,1000). Leibniz then gives
    65*(18000+4*30*105+6*170*15+4*1800*3+31000)<1e8.
    Independent atan series encloses the tiny difference between the intended
    endpoint t=2/3 and the actual binary source sweep; it is reserved separately.
    """
    with localcontext() as context:
        context.prec = 80
        count, terminal = 2048, Decimal(2) / 3
        step = terminal / count

        def value(t):
            square = t * t
            return 65 * (116 + 272 * square + 181 * square * square).sqrt() / (1 + square) ** 2

        total = value(Decimal(0)) + value(terminal)
        for i in range(1, count):
            total += (4 if i % 2 else 2) * value(i * step)
        integral = total * step / 3
        error = terminal / 180 * step**4 * Decimal(10**8)
        t, atan = Decimal(2) / 3, Decimal(0)
        for index in range(300):
            atan += (-1 if index % 2 else 1) * t ** (2 * index + 1) / (2 * index + 1)
        atan_error = t**601 / 601 + Decimal("1e-70")
        angle_error = abs(abs(Decimal.from_float(sweep)) * PI / 180 - 2 * atan) + 2 * atan_error
        # Per-arc angular integrand <= R sqrt(H²+s²(R+c)²)<500.
        error += 500 * angle_error + Decimal("1e-65")
        return Fraction(Decimal("1.1") * 2 * (integral - error) + 440), Fraction(
            Decimal("1.1") * 2 * (integral + error) + 440
        )


@pytest.mark.parametrize("xz", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_genuine_gothic_cone_against_independent_high_precision_interval_oracle(xz, reverse):
    first, second = _gothic("a", xz=xz), _gothic("b", large=True, xz=xz)
    result = certify_loft_intrinsic_area(
        first, second, _refs(first, second, reverse=reverse), scale=1
    )
    lower, upper = _bounds(result)
    oracle_low, oracle_high = _gothic_oracle(first.curves[0].data["sweep_deg"])
    assert lower <= oracle_low <= oracle_high <= upper
    assert upper - lower < Fraction("0.0001")
    assert result["examined_nodes"] < 1000
    assert len(result["coverage"]["correspondences"]) == 3


def _cubic_profiles(*, depth=12, count=1, genuine=False, k=1):
    curves_a, curves_b = [], []
    for index in range(count):
        if genuine:
            points = [(0, 0), (1, 2), (3, -1), (5, 4)]
        else:
            points = [
                (30 * index, 30 * index),
                (30 * index + 10, 30 * index),
                (30 * index + 20, 30 * index + 10),
                (30 * index + 30, 30 * index + 30),
            ]
        data = {"control1": points[1], "control2": points[2]}
        curves_a.append(Curve(points[0], points[3], "cubic", data, f"a{index}"))
        mapped = [tuple(k * x for x in point) for point in points]
        curves_b.append(
            Curve(
                mapped[0],
                mapped[3],
                "cubic",
                {"control1": mapped[1], "control2": mapped[2]},
                f"b{index}",
            )
        )
    return (
        LoftProfile(tuple(curves_a), profile_id="a"),
        LoftProfile(tuple(curves_b), origin=(0, 0, depth), profile_id="b"),
    )


@pytest.mark.parametrize("count,scale", [(1, 1), (2, 1), (2, 0.01)])
def test_cubic_normal_area_analytic_arclength_and_global_multipatch_budget(count, scale):
    first, second = _cubic_profiles(count=count)
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=scale)
    with localcontext() as context:
        context.prec = 80
        root = Decimal(5).sqrt()
        length = 15 * root + Decimal("7.5") * (2 + root).ln()
        _contains(result, count * 12 * length * Decimal.from_float(float(scale)) ** 2)
    assert result["examined_nodes"] > count


@pytest.mark.parametrize("k", [1, 2])
def test_genuine_cubic_against_explicit_independent_scalar_integral(k):
    first, second = _cubic_profiles(genuine=True, depth=7, k=k)
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1)
    lower, upper = _bounds(result)

    def integrand(t):
        x, y = 3 * t + 3 * t * t - t**3, 6 * t - 15 * t * t + 13 * t**3
        dx, dy = 3 + 6 * t - 3 * t * t, 6 - 30 * t + 39 * t * t
        return math.sqrt(49 * (dx * dx + dy * dy) + ((k - 1) * (dx * y - dy * x)) ** 2)

    expected, quadrature_error = quad(integrand, 0, 1, epsabs=1e-11, epsrel=1e-13)
    expected *= (1 + k) / 2
    assert quadrature_error < 1e-8
    assert float(lower) < expected < float(upper)


@pytest.mark.parametrize(
    "basis,normal",
    [
        (((1, 0, 0), (0, 1, 0)), (0, 0, 1)),
        (((1, 0, 0), (0, 0, 1)), (0, -1, 0)),
        (((0, 1, 0), (0, 0, 1)), (1, 0, 0)),
    ],
)
def test_world_origin_and_plane_orientation_do_not_change_intrinsic_area(basis, normal):
    origin = (1024, -512, 64)
    second_origin = tuple(x + 200 * n for x, n in zip(origin, normal))
    first = _circle(20, basis=basis, origin=origin)
    second = _circle(20, basis=basis, origin=second_origin, prefix="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1)
    with localcontext() as context:
        context.prec = 80
        _contains(result, 4000 * PI)


def test_actual_nonideal_world_basis_is_included_instead_of_assumed_unit_normal():
    factor = 1 + 2**-42  # accepted by the source plane precision validation
    basis = ((factor, 0, 0), (0, factor, 0))
    first = _circle(20, basis=basis)
    second = _circle(20, depth=200, prefix="b", basis=basis)
    result = certify_loft_intrinsic_area(
        first, second, _refs(first, second), scale=1, absolute_budget_mm2=1e-12
    )
    with localcontext() as context:
        context.prec = 80
        _contains(result, 4000 * PI * Decimal.from_float(factor))
        assert Fraction(result["area_lower_exact"]) > Fraction(4000 * PI)


def test_model_millimeters_and_paper_scale_are_applied_exactly_once():
    first, second = _circle(2000), _circle(2000, depth=20000, prefix="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=0.01)
    with localcontext() as context:
        context.prec = 80
        _contains(result, 40_000_000 * PI * Decimal.from_float(0.01) ** 2)


def test_source_records_and_curve_data_remain_unchanged():
    first, second = _gothic("a"), _gothic("b", large=True)

    def state(profile):
        return (
            profile.origin,
            profile.u,
            profile.v,
            profile.profile_id,
            [(c.start, c.end, c.kind, dict(c.data), c.segment_id) for c in profile.curves],
        )

    before = state(first), state(second)
    _bounds(certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1))
    assert before == (state(first), state(second))


@pytest.mark.parametrize(
    "options",
    [
        {"max_nodes": 1},
        {"max_depth": 0},
        {"absolute_budget_mm2": 1e-25},
    ],
)
def test_budget_exhaustion_never_returns_an_uncertified_area(options):
    first, second = _cubic_profiles()
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1, **options)
    assert result["status"] == "UNRESOLVED"
    assert "area_lower_exact" not in result
    assert "budget" in result["message"]


@pytest.mark.parametrize(
    "options",
    [
        {"scale": 0},
        {"scale": -1},
        {"scale": math.nan},
        {"scale": math.inf},
        {"scale": True},
        {"absolute_budget_mm2": 0},
        {"absolute_budget_mm2": math.nan},
        {"absolute_budget_mm2": True},
        {"max_nodes": 0},
        {"max_nodes": True},
        {"max_depth": -1},
        {"max_depth": True},
    ],
)
def test_malformed_numeric_settings_are_explicitly_unresolved(options):
    first, second = _circle(20), _circle(20, depth=200, prefix="b")
    settings = {"scale": 1, **options}
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), **settings)
    assert result["status"] == "UNRESOLVED"
    assert result["examined_nodes"] == 0


def test_incomplete_duplicate_and_partial_correspondences_are_not_area_coverage():
    first, second = _gothic("a"), _gothic("b", large=True)
    references = _refs(first, second)
    cases = (
        references[:-1],
        (*references, references[0]),
        (replace(references[0], first_interval=(0, 0.5)), *references[1:]),
    )
    for refs in cases:
        result = certify_loft_intrinsic_area(first, second, refs, scale=1)
        assert result["status"] == "UNRESOLVED", result


def test_nonhomothetic_negative_factor_and_twisted_basis_are_not_certified():
    first, second = _cubic_profiles(genuine=True)
    shifted = replace(second.curves[0], data={"control1": (1, 3), "control2": (3, -1)})
    cases = [replace(second, curves=(shifted,)), replace(second, u=(0, 1, 0), v=(-1, 0, 0))]
    negative = Curve((0, 0), (-5, -4), "cubic", {"control1": (-1, -2), "control2": (-3, 1)}, "b0")
    cases.append(replace(second, curves=(negative,)))
    for other in cases:
        result = certify_loft_intrinsic_area(first, other, _refs(first, other), scale=1)
        assert result["status"] == "UNRESOLVED", result


def test_area_certificate_does_not_approve_a_degenerate_surface():
    first, second = _circle(20), _circle(20, prefix="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1, max_nodes=1)
    assert result["status"] == "UNRESOLVED"
    assert "area_lower_exact" not in result


def test_opposite_arc_orientation_requires_analytic_proof_not_endpoint_proximity():
    first = _circle(20)
    reversed_source = Curve((-20, 0), (20, 0), "arc", {"center": (0, 0), "sweep_deg": -180}, "b")
    second = LoftProfile((reversed_source,), origin=(0, 0, 200), profile_id="b")
    reference = LoftCorrespondence("a", "b", (0, 1), (1, 0))
    result = certify_loft_intrinsic_area(first, second, (reference,), scale=1)
    assert result["status"] == "UNRESOLVED"
    assert "analytic endpoint proof" in result["message"]
    assert "Reverse both" in result["next_action"]


def test_common_reverse_uses_analytic_arc_start_not_rounded_stored_endpoint():
    # The source accepts a serialization discrepancy at the endpoint. Rebuilding
    # its reverse from that endpoint changes radius and therefore intrinsic area.
    curve = Curve((20, 0), (-20, 1e-8), "arc", {"center": (0, 0), "sweep_deg": 180}, "a")
    other = Curve(curve.start, curve.end, curve.kind, dict(curve.data), "b")
    first = LoftProfile((curve,), profile_id="a")
    second = LoftProfile((other,), origin=(0, 0, 200), profile_id="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second, reverse=True), scale=1)
    with localcontext() as context:
        context.prec = 80
        _contains(result, 4000 * PI)


@pytest.mark.parametrize("sweep", [-350, 350])
def test_nonconcentric_long_arc_sweep_has_certified_trigonometric_remainders(sweep):
    angle = math.radians(sweep)
    end = (5 + 10 * math.cos(angle), 10 * math.sin(angle))
    a = Curve((15, 0), end, "arc", {"center": (5, 0), "sweep_deg": sweep}, "a")
    b = Curve(
        (30, 0), tuple(2 * x for x in end), "arc", {"center": (10, 0), "sweep_deg": sweep}, "b"
    )
    first = LoftProfile((a,), profile_id="a")
    second = LoftProfile((b,), origin=(0, 0, 7), profile_id="b")
    result = certify_loft_intrinsic_area(first, second, _refs(first, second), scale=1)
    lower, upper = _bounds(result)
    # In polar source coordinates: |C' x d| dparameter is
    # r*sqrt(H²+(r+c*cos(theta))²) dtheta; independent scalar quadrature.
    expected, error = quad(
        lambda t: 15 * math.sqrt(49 + (10 + 5 * math.cos(t)) ** 2),
        0,
        abs(angle),
        epsabs=1e-10,
        epsrel=1e-13,
    )
    assert error < 1e-8
    assert float(lower) < expected < float(upper)


def test_invalid_source_plane_identity_and_boolean_interval_do_not_become_area_certificates():
    first, second = _circle(20), _circle(20, depth=200, prefix="b")
    for source in (
        replace(first, origin=(math.inf, 0, 0)),
        replace(first, profile_id=""),
        replace(first, closed="yes"),
    ):
        result = certify_loft_intrinsic_area(source, second, _refs(first, second), scale=1)
        assert result["status"] == "UNRESOLVED", result
    result = certify_loft_intrinsic_area(
        first, second, (LoftCorrespondence("a", "b", (False, True), (0, 1)),), scale=1
    )
    assert result["status"] == "UNRESOLVED"
