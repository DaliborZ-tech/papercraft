"""Actual authored topology must supply the complete scene to bend clearance."""

import math

import pytest

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
