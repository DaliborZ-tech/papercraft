"""Actual authored topology must supply the complete scene to bend clearance."""

import math

import numpy as np
import pytest
from shapely import Point, Polygon

from archpapercraft.authoring import AuthorProject


def own_wall_base():
    project = AuthorProject.new(scale=1)
    wall_profile = project.add_profile(
        [[20, 0], [60, 0], [60, 20], [20, 20]],
        plane={"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    wall = project.add_surface(wall_profile)
    base = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    aid = project.attach_edge_to_surface(
        wall, project.profiles[wall_profile].segments[0].id, base,
        target_side="outside", glue_direction=-1,
    )
    cid = project.set_attachment_tab(aid, width_mm=5, taper=1)
    return project, cid, wall, base


def add_between_pose_obstacle(project):
    profile = project.add_profile(
        [[25, -2.5], [55, -2.5], [55, -1.5], [25, -1.5]],
        plane={"origin": [0, 3, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    return project.add_surface(profile, name="Obstacle at the independent 45-degree witness")


def test_adapter_certifies_declared_material_and_records_local_reservations():
    project, cid, wall, base = own_wall_base()
    project.set_material_profile(thickness_mm=0.2, clearance_mm=0.02, bend_radius_mm=0.05)
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "CLEAR", result
    assert result["physical_build"] == "NOT_VERIFIED"
    assert len(result["tabs"]) == 1
    tab = result["tabs"][0]
    assert set(tab["checked_obstacle_ids"]) == {wall, base}
    assert tab["allowances"] and all(a["obstacle_id"] in (wall, base) for a in tab["allowances"])
    assert "analytic" in tab["proof_method"]


@pytest.mark.parametrize("known", [False, True])
def test_unconnected_mid_fold_obstacle_is_not_hidden_by_old_contact_or_cached_results(known):
    project, cid, *_ = own_wall_base()
    if known:
        project.set_material_profile(thickness_mm=0.2, clearance_mm=0.02, bend_radius_mm=0.05)
    initial = project.connector_bend_clearance(cid)
    assert initial["status"] == ("CLEAR" if known else "UNVERIFIED"), initial
    obstacle = add_between_pose_obstacle(project)
    result = project.connector_bend_clearance(cid)
    assert result["assembly_digest"] != initial["assembly_digest"]
    assert result["status"] == "COLLISION", result
    assert result["tabs"][0]["obstacle_id"] == obstacle
    # The checker may find another true angle before the known -45° witness.
    # Independently intersect its rotated tab ray with y=3: rho*sin(a)=2.
    angle = math.radians(abs(result["tabs"][0]["witness_angle_deg"]))
    rho, z = 2 / math.sin(angle), -2 / math.tan(angle)
    assert 0 < rho < 5 and -2.5 < z < -1.5
    assert set(result["tabs"][0]["checked_obstacle_ids"]) == set(project.surfaces)
    project.set_connector(cid, enabled=False)
    assert project.connector_bend_clearance(cid)["status"] == "NOT_APPLICABLE"


def test_existing_coplanar_edge_join_uses_the_static_clearance_path():
    project = AuthorProject.new(scale=1)
    receiver_profile = project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    receiver = project.add_surface(receiver_profile)
    source_profile = project.add_profile([[0, -20], [100, -20], [100, 0], [0, 0]])
    source = project.add_surface(source_profile)
    joint = project.connect_edges(
        source, project.profiles[source_profile].segments[2].id,
        receiver, project.profiles[receiver_profile].segments[0].id,
    )
    project.set_tab(joint, owner=source, width_mm=5, taper=1)
    project.set_material_profile(thickness_mm=0.2, clearance_mm=0.02, bend_radius_mm=0.05)
    result = project.connector_bend_clearance(project.joints[joint].connector_id)
    assert result["status"] == "CLEAR", result


def test_large_crease_reservation_cannot_make_the_check_vacuously_clear():
    project, cid, *_ = own_wall_base()
    project.set_material_profile(thickness_mm=0.2, crease_zone_mm=100)
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "UNRESOLVED"
    assert "příliš široký" in result["message"]
    assert any(i.code == "BEND_UNRESOLVED" for i in project.validate_layout())


def add_far_tab(project, base, side):
    profile = project.add_profile(
        [[70, 0], [90, 0], [90, 20], [70, 20]],
        plane={"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    source = project.add_surface(profile)
    attachment = project.attach_edge_to_surface(
        source, project.profiles[profile].segments[0].id, base,
        target_side=side, glue_direction=-1,
    )
    return project.set_attachment_tab(attachment, width_mm=5, taper=1)


def assert_complete_inventory(report):
    expected = set(report["expected_obstacle_ids"])
    checked = set(report["checked_obstacle_ids"])
    unresolved = set(report["unresolved_layer_obstacle_ids"])
    not_evaluated = set(report["not_evaluated_obstacle_ids"])
    assert not checked & unresolved and not checked & not_evaluated
    assert not unresolved & not_evaluated
    assert expected == checked | unresolved | not_evaluated


def test_siblings_and_other_connectors_are_material_and_disabled_tabs_are_absent():
    project, cid, _, base = own_wall_base()
    project.set_connector(cid, count=2, gap_mm=2)
    other = add_far_tab(project, base, "outside")
    project.set_material_profile(thickness_mm=0.2)
    tids = project.connectors[cid].tab_ids.copy()
    other_tid = project.connectors[other].tab_ids[0]
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "CLEAR", result
    assert result["assembly_scenario"] == "ONE_TAB_MOVES_ALL_OTHER_ACTIVE_TABS_ALREADY_FOLDED"
    for report in result["tabs"]:
        assert_complete_inventory(report)
        assert "tab:" + report["tab_id"] not in report["expected_obstacle_ids"]
        assert {"tab:" + tid for tid in [*tids, other_tid] if tid != report["tab_id"]} <= set(
            report["checked_obstacle_ids"]
        )
    project.set_connector_tab(cid, tids[1], enabled=False)
    project.set_connector(other, enabled=False)
    updated = project.connector_bend_clearance(cid)
    assert len(updated["tabs"]) == 1
    assert updated["tabs"][0]["tab_id"] == tids[0]
    assert all(not oid.startswith("tab:") for oid in updated["tabs"][0]["expected_obstacle_ids"])
    assert project.connectors[cid].tab_ids == tids


@pytest.mark.parametrize("known", [False, True])
def test_opposite_sides_explicitly_retain_unresolved_material_without_false_collision(known):
    project, cid, _, base = own_wall_base()
    other = add_far_tab(project, base, "inside")
    if known:
        project.set_material_profile(thickness_mm=0.2)
    result = project.connector_bend_clearance(cid)
    assert result["status"] == ("UNRESOLVED" if known else "UNVERIFIED"), result
    report = result["tabs"][0]
    assert_complete_inventory(report)
    assert report["unresolved_layer_obstacle_ids"] == [
        "tab:" + project.connectors[other].tab_ids[0]
    ]
    obstacle = add_between_pose_obstacle(project)
    collision = project.connector_bend_clearance(cid)
    assert collision["status"] == "COLLISION", collision
    assert collision["tabs"][0]["obstacle_id"] == obstacle
    assert_complete_inventory(collision["tabs"][0])
    assert collision["tabs"][0]["unresolved_layer_obstacle_ids"]


def test_concave_other_tab_keeps_its_actual_void_in_the_obstacle_triangulation():
    project, _, _, base = own_wall_base()
    other = add_far_tab(project, base, "outside")
    tid = project.connectors[other].tab_ids[0]
    # 20*5 rectangle minus the 10*3 open notch = 70 mm2, not its 100 mm2 hull.
    project.set_connector_tab(other, tid, shape="custom", outline_mm=[
        [0, 0], [20, 0], [20, 5], [15, 5], [15, 2], [5, 2], [5, 5], [0, 5],
    ])
    record = next(r for r in project._bend_tab_obstacles() if r["tab_id"] == tid)
    triangles = record["triangles"]
    area = sum(np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) / 2 for t in triangles)
    assert area == pytest.approx(70)
    # Final footprint: x=70..90, y=0..5; the notch is x=75..85, y=0..3.
    assert all(not Polygon(t[:, :2]).contains(Point(80, 1)) for t in triangles)
    assert any(Polygon(t[:, :2]).covers(Point(72, 1)) for t in triangles)


@pytest.mark.parametrize("known", [False, True])
def test_other_authored_tab_blocks_mid_motion_while_endpoint_planes_are_free(known):
    project, cid, *_ = own_wall_base()
    # Negative construction fixture: another authored tab bridges a receiver
    # opening, with insufficient glue support. Its actual material still must
    # obstruct this tab; missing glue does not make that paper disappear.
    plane = {"origin": [0, 3, 0], "u": [1, 0, 0], "v": [0, 0, 1]}
    outer = project.add_profile([[10, -6], [70, -6], [70, 2], [10, 2]], plane=plane)
    hole = project.add_profile([[19, -4.7], [61, -4.7], [61, 0.1], [19, 0.1]], plane=plane)
    receiver = project.add_surface(outer)
    source_profile = project.add_profile(
        [[25, 0], [55, 0], [55, 3], [25, 3]],
        plane={"origin": [0, 0, -4.9], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    source = project.add_surface(source_profile)
    attachment = project.attach_edge_to_surface(
        source, project.profiles[source_profile].segments[2].id, receiver,
        target_side="outside", glue_direction=-1,
    )
    other = project.set_attachment_tab(attachment, width_mm=4, taper=1)
    # Subsequent receiver editing invalidates existing glue support; the old
    # authored tab remains material until its author explicitly changes it.
    project.add_hole(receiver, hole)
    if known:
        project.set_material_profile(thickness_mm=0.1)
    result = project.connector_bend_clearance(cid)
    expected = "tab:" + project.connectors[other].tab_ids[0]
    assert result["status"] == "COLLISION", result
    report = result["tabs"][0]
    assert report["obstacle_id"] == expected, report
    assert -90 < report["witness_angle_deg"] < 0
    assert_complete_inventory(report)
    # Independently: folded obstacle y=3,z=-4.9..-0.9. Initial moving
    # tab is y=5 and final moving tab is z=0, each at least 0.9 mm away.
    triangles = next(r["triangles"] for r in project._bend_tab_obstacles()
                     if r["id"] == expected)
    assert np.allclose(triangles[:, :, 1], 3)
    assert np.max(triangles[:, :, 2]) == pytest.approx(-0.9)
    project.set_connector(other, enabled=False)
    cleared = project.connector_bend_clearance(cid)
    assert cleared["status"] == ("CLEAR" if known else "UNVERIFIED"), cleared


def test_unresolved_precision_failure_cannot_be_downgraded_by_unknown_opposite_layers():
    project, cid, _, base = own_wall_base()
    # Valid authoring coordinates beyond the bend kernel's supported digital
    # conditioning envelope must block, even with unknown paper thickness.
    far = project.add_profile(
        [[0, 0], [10, 0], [10, 10], [0, 10]],
        plane={"origin": [2000000, 0, 0], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    project.add_surface(far)
    before = project.connector_bend_clearance(cid)
    assert before["status"] == "UNRESOLVED", before
    assert "conditioning" in before["tabs"][0]["message"]
    other = add_far_tab(project, base, "inside")
    after = project.connector_bend_clearance(cid)
    assert after["status"] == "UNRESOLVED", after
    report = after["tabs"][0]
    assert "conditioning" in report["message"]
    assert report["checked_obstacle_ids"] == ()
    assert report["unresolved_layer_obstacle_ids"] == [
        "tab:" + project.connectors[other].tab_ids[0]
    ]
    assert set(report["not_evaluated_obstacle_ids"]) == set(project.surfaces)
    assert_complete_inventory(report)
    assert any(i.code == "BEND_UNRESOLVED"
               and i.joint_id == project.connectors[cid].attachment_id
               for i in project.validate_layout())
