"""Independent planar/solid witnesses for continuous paper-mm fold clearance."""

import math
from dataclasses import replace

import numpy as np
import pytest

from archpapercraft.authoring.clearance import (
    ContactAllowance,
    FoldSweep,
    MaterialObstacle,
    MaterialProfile,
    check_fold_clearance,
)


def quad(a, b, c, d):
    return [[a, b, c], [a, c, d]]


def box(x, y, z):
    return [[a, b, c] for a in x for b in y for c in z]


def scene():
    sweep = FoldSweep(
        patches_world_mm=[[[20, 5, 0], [60, 5, 0], [60, 5, -5], [20, 5, -5]]],
        hinge_start_mm=[20, 5, 0],
        hinge_end_mm=[60, 5, 0],
        angle_deg=-90,
        source_id="wall",
        receiver_id="base",
        initial_normal=[0, 1, 0],
        final_normal=[0, 0, -1],
        tab_id="authored-tab",
    )
    material = MaterialProfile(0.2, 0.02, 0.05)
    obstacles = [
        MaterialObstacle(
            "wall", quad([20, 5, 0], [60, 5, 0], [60, 5, 10], [20, 5, 10]), 0.2, "source"
        ),
        MaterialObstacle(
            "base", quad([0, 0, 0], [100, 0, 0], [100, 100, 0], [0, 100, 0]), 0.2, "receiver"
        ),
    ]
    allowances = [
        ContactAllowance(
            "wall",
            "hinge",
            box([19, 61], [4.5, 5.5], [-0.5, 0.5]),
            (-90, 0),
            "Shared finite crease and bend relief at source",
        ),
        ContactAllowance(
            "base",
            "hinge",
            box([19, 61], [4.5, 5.5], [-0.5, 0.5]),
            (-90, 0),
            "Shared finite crease relief at receiver",
        ),
        ContactAllowance(
            "base",
            "final_contact",
            box([19, 61], [-0.5, 5.5], [-0.25, 0.25]),
            (-90, -45),
            "Declared shallow glue contact on the receiving base",
        ),
    ]
    return sweep, material, obstacles, allowances


def check(sweep, material, obstacles, allowances, **kwargs):
    return check_fold_clearance(
        sweep,
        material,
        obstacles,
        expected_obstacle_ids=[o.id for o in obstacles],
        allowances=allowances,
        **kwargs,
    )


def test_right_angle_bend_is_certified_continuously_with_explicit_contacts():
    result = check(*scene())
    assert result.status == "CLEAR", result
    assert result.certified_intervals > 0
    assert result.tab_id == "authored-tab"
    assert len(result.allowances) == 3
    assert result.envelope_padding_mm > 0.02 + 0.05
    assert result.material_thickness_mm == 0.2
    assert "physical_build_and_strength_NOT_VERIFIED" in result.assumptions


def test_source_and_receiver_are_not_implicitly_ignored():
    sweep, material, obstacles, _ = scene()
    result = check(sweep, material, obstacles, [])
    assert result.status == "COLLISION"
    assert result.obstacle_id in {"wall", "base"}


def test_b02_independent_between_flat_and_final_obstacle_has_exact_45_degree_witness():
    sweep, material, obstacles, allowances = scene()
    # Reviewer B-02 oracle: at radius sqrt(8), theta=-45 degrees, direct x-axis
    # rotation of (40,5,-sqrt(8)) is (40,3,-2). This lies inside both shapes.
    assert 0 < math.sqrt(8) < 5
    obstacle = MaterialObstacle(
        "unconnected-obstacle",
        quad([25, 3, -2.5], [55, 3, -2.5], [55, 3, -1.5], [25, 3, -1.5]),
        0.2,
    )
    result = check(sweep, material, [*obstacles, obstacle], allowances)
    assert result.status == "COLLISION", result
    assert result.obstacle_id == "unconnected-obstacle"
    assert result.witness_angle_deg == pytest.approx(-45)
    # End poses alone miss it: flat has y5; folded has z0. Physical thickness
    # .2 cannot bridge either 2mm or 1.5mm endpoint separation.
    assert 5 - 3 > 0.2 and 1.5 > 0.2


@pytest.mark.parametrize("unknown", ["tab", "obstacle", "all"])
def test_b02_actual_midplane_crossing_is_blocked_even_with_unknown_material(unknown):
    sweep, material, obstacles, allowances = scene()
    obstacle = MaterialObstacle(
        "unconnected-obstacle",
        quad([25, 3, -2.5], [55, 3, -2.5], [55, 3, -1.5], [25, 3, -1.5]),
        None if unknown in ("obstacle", "all") else 0.2,
    )
    if unknown in ("tab", "all"):
        material = replace(material, thickness_mm=None)
    if unknown == "all":
        obstacles = [replace(o, thickness_mm=None) for o in obstacles]
    result = check(sweep, material, [*obstacles, obstacle], allowances)
    assert result.status == "COLLISION", result
    assert result.obstacle_id == "unconnected-obstacle"
    assert result.witness_angle_deg == pytest.approx(-45)
    x, y, z = result.witness_point_mm
    assert 25 < x < 55 and y == pytest.approx(3) and z == pytest.approx(-2)


def test_coplanar_unconnected_area_is_collision_with_unknown_material():
    sweep, material, obstacles, allowances = scene()
    other = MaterialObstacle(
        "coplanar", quad([30, 5, -4], [40, 5, -4], [40, 5, -2], [30, 5, -2]), None
    )
    result = check(sweep, replace(material, thickness_mm=None), [*obstacles, other], allowances)
    assert result.status == "COLLISION", result
    assert result.obstacle_id == "coplanar"
    assert result.witness_angle_deg == pytest.approx(0)


def test_numerically_ambiguous_zero_thickness_overlap_is_not_silently_accepted():
    sweep, material, obstacles, allowances = scene()
    other = MaterialObstacle(
        "ambiguous",
        quad([30, 5 + 1e-12, -4], [40, 5 + 1e-12, -4], [40, 5 + 1e-12, -2], [30, 5 + 1e-12, -2]),
        None,
    )
    result = check(sweep, replace(material, thickness_mm=None), [*obstacles, other], allowances)
    assert result.status == "UNRESOLVED", result


def test_distant_unconnected_material_is_in_registry_and_does_not_block():
    sweep, material, obstacles, allowances = scene()
    far = MaterialObstacle("distant", [[[10, -5, -10], [15, -5, -10], [10, -3, -10]]], 0.4)
    assert check(sweep, material, [*obstacles, far], allowances).status == "CLEAR"


def test_missing_unconnected_or_receiver_registry_never_produces_pass():
    sweep, material, obstacles, allowances = scene()
    result = check_fold_clearance(
        sweep,
        material,
        obstacles,
        expected_obstacle_ids=["wall", "base", "forgotten"],
        allowances=allowances,
    )
    assert result.status == "UNRESOLVED"
    assert "registry" in result.message
    assert check(sweep, material, obstacles[:1], allowances).status == "UNRESOLVED"


@pytest.mark.parametrize("owner", ["moving", "obstacle"])
def test_unknown_material_never_becomes_clear(owner):
    sweep, material, obstacles, allowances = scene()
    if owner == "moving":
        material = replace(material, thickness_mm=None)
    else:
        obstacles[0] = replace(obstacles[0], thickness_mm=None)
    assert check(sweep, material, obstacles, allowances).status == "UNVERIFIED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("thickness_mm", 0),
        ("thickness_mm", -0.1),
        ("clearance_mm", -1),
        ("bend_radius_mm", float("nan")),
    ],
)
def test_invalid_material_distances_are_unresolved(field, value):
    sweep, material, obstacles, allowances = scene()
    assert (
        check(sweep, replace(material, **{field: value}), obstacles, allowances).status
        == "UNRESOLVED"
    )


def test_foreign_material_cannot_be_exempted_by_an_allowance():
    sweep, material, obstacles, allowances = scene()
    obstacles.append(MaterialObstacle("other", [[[0, 0, 10], [1, 0, 10], [0, 1, 10]]], 0.2))
    allowances.append(
        ContactAllowance(
            "other",
            "hinge",
            box([-5, 100], [-5, 100], [-5, 100]),
            (-90, 0),
            "Wrong blanket foreign exemption",
        )
    )
    result = check(sweep, material, obstacles, allowances)
    assert result.status == "UNRESOLVED"
    assert "independent obstacle" in result.message


def test_final_orientation_is_checked_against_actual_signed_hinge_rotation():
    sweep, material, obstacles, allowances = scene()
    assert (
        check(replace(sweep, final_normal=[0, 0, 1]), material, obstacles, allowances).status
        == "UNRESOLVED"
    )


def test_concave_author_tab_is_supported_as_exact_material_triangle_patches():
    sweep, material, obstacles, allowances = scene()
    # Remove a 10x2 corner from the tab; convex patches describe exactly the
    # remaining L shape. A foreign small triangle occupies the missing corner
    # in every pose (x52..58), so a filled bounding hull would falsely block.
    patches = [
        [[20, 5, 0], [60, 5, 0], [60, 5, -3], [20, 5, -3]],
        [[20, 5, -3], [50, 5, -3], [50, 5, -5], [20, 5, -5]],
    ]
    # The material area oracle is 40*3+30*2=180 mm2, not hull area195.
    assert sum([40 * 3, 30 * 2]) == 180
    coordinate = 5 - 4.5 / math.sqrt(2)
    corner = MaterialObstacle(
        "notch-obstacle",
        quad(
            [54, coordinate, -3.3],
            [56, coordinate, -3.3],
            [56, coordinate, -3.1],
            [54, coordinate, -3.1],
        ),
        0.2,
    )
    actual = [*obstacles, corner]
    assert check(sweep, material, actual, allowances).status == "COLLISION"
    assert (
        check(replace(sweep, patches_world_mm=patches), material, actual, allowances).status
        == "CLEAR"
    )


def test_thin_obstacle_between_initial_angular_samples_is_not_a_false_pass():
    sweep, material, obstacles, allowances = scene()
    material = replace(material, thickness_mm=0.002, clearance_mm=0, bend_radius_mm=0)
    angle = math.radians(17)
    y, z = 5 - 4 * math.sin(angle), -4 * math.cos(angle)
    needle = MaterialObstacle(
        "between-samples",
        quad([39, y, z - 0.005], [41, y, z - 0.005], [41, y, z + 0.005], [39, y, z + 0.005]),
        0.002,
    )
    result = check(sweep, material, [*obstacles, needle], allowances, max_depth=0)
    assert result.status == "UNRESOLVED"  # A finite empty sample set is no certificate.
    refined = check(sweep, material, [*obstacles, needle], allowances)
    assert refined.status == "COLLISION", refined
    assert refined.obstacle_id == "between-samples"
    assert abs(refined.witness_angle_deg + 17) < 0.1


def test_declared_thickness_clearance_and_radius_affect_the_digital_envelope():
    sweep, material, obstacles, allowances = scene()
    side = MaterialObstacle(
        "near-side", quad([60.15, 0, -6], [60.15, 6, -6], [60.15, 6, 1], [60.15, 0, 1]), 0.1
    )
    actual = [*obstacles, side]
    thin = MaterialProfile(0.02, 0.01, 0)
    assert check(sweep, thin, actual, allowances).status == "CLEAR"
    # Side gap to the thick obstacle is .1mm. Expanding the required envelope
    # beyond that gap cannot remain a certified CLEAR, even though the nominal
    # surface itself never intersects. No arbitrary physical PASS is granted.
    assert (
        check(sweep, replace(thin, clearance_mm=0.2), actual, allowances, max_depth=1).status
        != "CLEAR"
    )
    assert (
        check(sweep, replace(thin, bend_radius_mm=0.2), actual, allowances, max_depth=1).status
        != "CLEAR"
    )


def test_slanted_35_degree_fold_with_explicit_finite_contact_is_supported():
    sweep, material, obstacles, allowances = scene()
    angle = math.radians(55)
    rotation = np.array(
        [[1, 0, 0], [0, math.cos(angle), -math.sin(angle)], [0, math.sin(angle), math.cos(angle)]]
    )
    origin = np.array([20, 5, 0])

    def rotated(values):
        return ((np.asarray(values) - origin) @ rotation.T + origin).tolist()

    obstacles[1] = replace(
        obstacles[1], triangles_world_mm=[rotated(t) for t in obstacles[1].triangles_world_mm]
    )
    allowances = [
        replace(
            allowances[0],
            vertices_world_mm=box([19, 61], [3, 7], [-2, 2]),
            angle_interval_deg=(-35, 0),
        ),
        replace(
            allowances[1],
            vertices_world_mm=rotated(box([19, 61], [3, 7], [-2, 2])),
            angle_interval_deg=(-35, 0),
        ),
        replace(
            allowances[2],
            vertices_world_mm=rotated(allowances[2].vertices_world_mm),
            angle_interval_deg=(-35, -17.5),
        ),
    ]
    slope = math.radians(35)
    sweep = replace(sweep, angle_deg=-35, final_normal=[0, math.cos(slope), -math.sin(slope)])
    assert check(sweep, material, obstacles, allowances).status == "CLEAR"


def test_unsplit_concave_or_nonplanar_tab_is_truthfully_unsupported():
    sweep, material, obstacles, allowances = scene()
    concave = [[[20, 5, 0], [60, 5, 0], [60, 5, -3], [50, 5, -3], [50, 5, -5], [20, 5, -5]]]
    assert (
        check(replace(sweep, patches_world_mm=concave), material, obstacles, allowances).status
        == "UNRESOLVED"
    )
    nonplanar = [[[20, 5, 0], [60, 5, 0], [60, 5.1, -5], [20, 5, -5]]]
    assert (
        check(replace(sweep, patches_world_mm=nonplanar), material, obstacles, allowances).status
        == "UNRESOLVED"
    )


def test_whole_scene_rotated_and_translated_is_same_digital_clearance():
    sweep, material, obstacles, allowances = scene()
    # Independent exact orthogonal matrix maps x->y, y->z, z->x; no checker
    # rotation helper is used to construct the expected invariant experiment.
    matrix = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])
    shift = np.array([7.0, -11.0, 13.0])

    def point(value):
        return (np.asarray(value) @ matrix.T + shift).tolist()

    moved = replace(
        sweep,
        patches_world_mm=[point(p) for p in sweep.patches_world_mm],
        hinge_start_mm=point(sweep.hinge_start_mm),
        hinge_end_mm=point(sweep.hinge_end_mm),
        initial_normal=(matrix @ np.array(sweep.initial_normal)).tolist(),
        final_normal=(matrix @ np.array(sweep.final_normal)).tolist(),
    )
    other = [
        replace(o, triangles_world_mm=[point(t) for t in o.triangles_world_mm]) for o in obstacles
    ]
    permits = [replace(a, vertices_world_mm=point(a.vertices_world_mm)) for a in allowances]
    assert check(moved, material, other, permits).status == "CLEAR"


@pytest.mark.parametrize("start,end", [([20, 5, -2], [60, 5, -2]), ([20, 5, 1], [60, 5, 1])])
def test_interior_or_disconnected_axis_is_not_accepted_as_a_material_hinge(start, end):
    sweep, material, obstacles, allowances = scene()
    result = check(
        replace(sweep, hinge_start_mm=start, hinge_end_mm=end), material, obstacles, allowances
    )
    assert result.status == "UNRESOLVED"
    assert "hinge" in result.message


def flat_scene():
    sweep, material, obstacles, allowances = scene()
    sweep = replace(sweep, angle_deg=0, final_normal=[0, 1, 0])
    obstacles[1] = MaterialObstacle(
        "base", quad([0, 5, -20], [100, 5, -20], [100, 5, 0], [0, 5, 0]), 0.2, "receiver"
    )
    allowances = [replace(a, angle_interval_deg=(0, 0)) for a in allowances]
    allowances[2] = replace(
        allowances[2], vertices_world_mm=box([19, 61], [4.75, 5.25], [-5.5, 0.5])
    )
    return sweep, material, obstacles, allowances


def test_zero_degree_join_has_real_static_clearance_not_an_empty_interval_pass():
    result = check(*flat_scene())
    assert result.status == "CLEAR", result
    assert result.certified_intervals == result.examined_intervals == 1


@pytest.mark.parametrize("unknown", [False, True])
def test_zero_degree_join_still_detects_an_independent_material_obstacle(unknown):
    sweep, material, obstacles, allowances = flat_scene()
    other = MaterialObstacle(
        "coplanar-obstacle",
        quad([30, 5, -4], [40, 5, -4], [40, 5, -2], [30, 5, -2]),
        None if unknown else 0.2,
    )
    if unknown:
        material = replace(material, thickness_mm=None)
    result = check(sweep, material, [*obstacles, other], allowances)
    assert result.status == "COLLISION", result
    assert result.obstacle_id == "coplanar-obstacle"
    assert result.witness_angle_deg == pytest.approx(0)


def test_zero_degree_join_without_known_material_does_not_claim_clearance():
    sweep, material, obstacles, allowances = flat_scene()
    assert (
        check(sweep, replace(material, thickness_mm=None), obstacles, allowances).status
        == "UNVERIFIED"
    )
