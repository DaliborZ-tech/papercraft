"""Guaranteed/possible material prevents a chord proxy from proving fold clearance."""

import math

import numpy as np
import pytest
from shapely import MultiPolygon, Point, Polygon

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring.bend import _guaranteed_triangles


def wall_base(*, known=True, curved_wall=False):
    project = AuthorProject.new(scale=1)
    plane = {"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]}
    if curved_wall:
        profile = project.add_profile(segments=[
            {"kind": "line", "start": [20, 0], "end": [60, 0]},
            {"kind": "line", "start": [60, 0], "end": [60, 20]},
            {"kind": "cubic", "start": [60, 20], "end": [20, 20],
             "control1": [60, 30], "control2": [20, 30]},
            {"kind": "line", "start": [20, 20], "end": [20, 0]},
        ], plane=plane)
    else:
        profile = project.add_profile([[20, 0], [60, 0], [60, 20], [20, 20]], plane=plane)
    wall = project.add_surface(profile)
    base = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    aid = project.attach_edge_to_surface(
        wall, project.profiles[profile].segments[0].id, base,
        target_side="outside", glue_direction=-1,
    )
    cid = project.set_attachment_tab(aid, width_mm=5, taper=1)
    if known:
        project.set_material_profile(thickness_mm=0.2)
    return project, cid, wall, base


def circle_profile(project, center, *, radius=1, offset=math.pi/64, plane=None):
    cx, cy = center
    a = [cx+radius*math.cos(offset), cy+radius*math.sin(offset)]
    b = [cx-radius*math.cos(offset), cy-radius*math.sin(offset)]
    return project.add_profile(segments=[
        {"kind": "arc", "start": a, "end": b,
         "data": {"center": list(center), "sweep_deg": 180}},
        {"kind": "arc", "start": b, "end": a,
         "data": {"center": list(center), "sweep_deg": 180}},
    ], plane=plane)


def add_native_bulge(project, cx=None):
    epsilon = (1-math.cos(math.pi/64))/2
    if cx is None:
        cx = 19+epsilon
    profile = circle_profile(
        project, (cx, -2),
        plane={"origin": [0, 3, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    return project.add_surface(profile), profile, epsilon


@pytest.mark.parametrize("known", [False, True])
def test_native_circle_bulge_mid_fold_witness_cannot_be_erased_by_chord_proxy(known):
    project, cid, *_ = wall_base(known=known)
    obstacle, profile, epsilon = add_native_bulge(project)
    # Independent -45 degree witness: rho=sqrt(8)<5, x lies in the tab interval.
    witness_uv = (20+epsilon/2, -2)
    assert math.sqrt(8) < 5 and 20 < witness_uv[0] < 60
    assert (witness_uv[0]-(19+epsilon))**2 < 1
    proxy = Polygon(project.profile_outline(profile))
    assert not proxy.covers(Point(witness_uv))
    assert max(v[0] for v in project.world_geometry(obstacle)["vertices"]) < 20
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "UNRESOLVED", result
    envelopes = result["tabs"][0]["material_envelopes"]
    assert envelopes["possible_check"]["status"] in ("COLLISION", "UNRESOLVED")
    assert envelopes["guaranteed_check"]["status"] != "COLLISION"
    assert envelopes["bounds"][obstacle]["possible_material_fully_covered"]


@pytest.mark.parametrize("known", [False, True])
def test_guaranteed_curved_material_collision_is_still_a_certain_negative(known):
    project, cid, *_ = wall_base(known=known)
    obstacle, _, _ = add_native_bulge(project, cx=20.5)
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "COLLISION", result
    assert result["tabs"][0]["obstacle_id"] == obstacle
    assert result["tabs"][0]["material_envelopes"]["guaranteed_check"]["status"] == "COLLISION"


def test_unrelated_curved_uncertainty_does_not_erase_an_independent_guaranteed_collision():
    project, cid, *_ = wall_base()
    add_native_bulge(project)
    profile = project.add_profile(
        [[25, -2.5], [55, -2.5], [55, -1.5], [25, -1.5]],
        plane={"origin": [0, 3, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    certain = project.add_surface(profile)
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "COLLISION", result
    assert result["tabs"][0]["obstacle_id"] == certain


def test_far_curved_source_part_with_straight_hinge_still_has_a_clear_supported_fold():
    project, cid, source, _ = wall_base(curved_wall=True)
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "CLEAR", result
    envelopes = result["tabs"][0]["material_envelopes"]
    assert envelopes["possible_check"]["status"] == "CLEAR"
    assert source in envelopes["bounds"]
    pruning = envelopes["possible_check"]["broad_phase_pruning"]
    assert any(row["obstacle_id"] == source
               and row["interaction_inside_whole_fold_permission_triangles"] > 0
               for row in pruning)
    assert source in envelopes["possible_check"]["checked_obstacle_ids"]


def test_curved_hole_remains_void_in_both_three_dimensional_material_bounds():
    project, cid, *_ = wall_base()
    outer = project.add_profile([[-2, -2], [2, -2], [2, 2], [-2, 2]])
    hole = circle_profile(project, (0, 0))
    obstacle = project.add_surface(outer, holes=[hole])
    records, proof = project._bend_surface_bounds()
    _, lower, upper = next(record for record in records if record[0] == obstacle)
    assert proof[obstacle]["possible_material_fully_covered"]
    for triangles in (lower, upper):
        assert all(not Polygon(face[:, :2]).covers(Point(0, 0)) for face in triangles)
    assert project.connector_bend_clearance(cid)["status"] == "CLEAR"


def test_guaranteed_multipolygon_triangulation_preserves_every_component_and_hole():
    holed = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)],
                     [[(1, 1), (3, 1), (3, 3), (1, 3)]])
    separate = Polygon([(10, 0), (12, 0), (12, 2), (10, 2)])
    region = MultiPolygon([holed, separate])
    triangles, omitted = _guaranteed_triangles(region)
    assert omitted == 0
    assert sum(Polygon(face).area for face in triangles) == pytest.approx(16)
    assert all(not Polygon(face).covers(Point(2, 2)) for face in triangles)
    assert any(Polygon(face).covers(Point(11, 1)) for face in triangles)
    assert np.isfinite(triangles).all()
