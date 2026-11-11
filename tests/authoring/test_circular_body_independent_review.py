"""Root review of f793346: independent source identities and unsafe inputs.

Decimal intrinsic expectations do not call the producer's interval helpers.
These are component tests, not a native C or physical proof.
"""

import copy
import math
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest
from test_circular_shell import authored

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.exporter.circular_output_validation import coordinate_errors

PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208998")


def dec_q(value):
    value = Fraction(value)
    return Decimal(value.numerator) / Decimal(value.denominator)


@pytest.mark.parametrize("r0,r1,h,reverse", [
    (7., 7., 13., False), (7., 17., 23., False),
    (17., 7., -23., True), (10., 20., math.sqrt(800), False),
    (20., 10., -math.sqrt(800), True), (10., 10.000001, 30., False),
])
def test_true_binary_source_area_and_slope_enclosed_independently(r0, r1, h, reverse):
    project, sid, _ = authored(r0, r1, h, reverse=reverse, quarters=True)
    status = project.loft_status(sid)
    assert status["status"] == "EXACT"
    with localcontext() as context:
        context.prec = 90
        a, b, height = map(Decimal.from_float, (r0, r1, h))
        slant = ((a-b)**2+height**2).sqrt()
        source = PI*(a+b)*slant
        shell = status["representation"]["circular_shell"]
        slope = (a-b)/slant
        source_bounds = shell["source_first_kappa_bounds"]
        assert dec_q(source_bounds["lower_exact"]) <= slope <= dec_q(source_bounds["upper_exact"])
        # Actual manufactured area is independently close to the intrinsic
        # binary-source area; the native source is not rounded to slant=30.
        native = status["area"]["actual_native"]
        actual = (dec_q(native["lower_exact"])+dec_q(native["upper_exact"]))/2
        assert abs(actual-source) < Decimal(".01")
        for side, sign in (("first", 1), ("second", -1)):
            rim = project.circular_rim(sid, side, source_turn=.375)
            bounds = rim["source_radial_slope_bounds"]
            assert dec_q(bounds["lower_exact"]) <= sign*slope <= dec_q(bounds["upper_exact"])
            assert rim["scope"].endswith("NOT_CONNECTOR_OR_CONTACT_CERTIFICATE")
            assert rim["chart_to_paper"]["map_kind"].startswith("AFFINE_REFERENCE_CHART")


@pytest.mark.parametrize("turn", [True, False, -.01, 1.01, float("nan"), float("inf"), "0.5"])
def test_unsafe_seam_parameters_fail_without_mutation(turn):
    project, sid, _ = authored(10, 10, 30)
    before = project.to_dict()
    with pytest.raises(ValidationError):
        project.circular_rim(sid, source_turn=turn)
    assert project.to_dict() == before


def test_returned_source_packet_is_detached_and_no_connector_approval():
    project, sid, _ = authored()
    before = project.to_dict()
    rim = project.circular_rim(sid)
    rim["source_binding"]["profiles"][0]["vertices"][0]["point"][0] += 100
    rim["paper_boundary_commands"][0][1] += 100
    rim["source_world_frame_intervals"]["radial"][0]["lower_exact"] = "-999"
    assert project.to_dict() == before
    assert project.circular_rim(sid) != rim
    restored = AuthorProject.from_dict(copy.deepcopy(before))
    assert restored.circular_rim(sid) == project.circular_rim(sid)


@pytest.mark.parametrize("damage", ["sweep", "radius", "missing", "extra"])
def test_serialized_circle_changes_are_measured_or_rejected(damage):
    source = [["M", 10, 0], ["A", 10, 10, 0, 0, 1, 0, 10], ["Z"]]
    actual = copy.deepcopy(source)
    if damage == "sweep":
        actual[1][5] = 0
    elif damage == "radius":
        actual[1][1:3] = [11, 11]
    elif damage == "missing":
        actual.pop(1)
    else:
        actual.insert(-1, ["L", 1, 9])
    try:
        position, length = coordinate_errors(source, actual)
    except ValueError:
        return
    assert max(position, length) > Fraction(1, 100)
