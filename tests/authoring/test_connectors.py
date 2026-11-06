import copy

import numpy as np
import pytest
from shapely import Polygon
from test_interior import wall_roof

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.geometry import page_points


def test_split_triangular_tabs_have_persistent_identity_and_rigid_receiver_contact():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid, width_mm=5, shape="triangle", count=4, gap_mm=1)
    connector = p.connectors[cid]
    ids = list(connector.tab_ids)
    geometry = p.connector_geometry(cid)
    assert len(geometry["tabs"]) == 4
    # Independent expectation: each base =100/4-1=24mm, height5; triangle60mm².
    for tab in geometry["tabs"]:
        assert tab["nominal_area_mm2"] == pytest.approx(60)
        assert tab["available_area_mm2"] == pytest.approx(60)
        assert tab["contact_gap_mm"] < 1e-8
        assert tab["fold_angle_deg"] == pytest.approx(-135)
        # Every folded point satisfies roof plane z-y=4000 in model millimetres.
        for x, y, z in tab["folded_world"]:
            assert z - y == pytest.approx(4000)
    p.set_connector_tab(cid, ids[1], enabled=False)
    p.set_connector_tab(cid, ids[2], width_mm=4)
    assert p.connectors[cid].tab_ids == ids
    assert [t["tab_id"] for t in p.connector_geometry(cid)["tabs"]] == [ids[0], ids[2], ids[3]]
    p.set_attachment_tab(aid, taper=0.4)  # A parameter edit preserves shape/count/gap/IDs.
    assert p.connectors[cid].shape == "triangle" and p.connectors[cid].count == 4
    assert p.connectors[cid].gap_mm == 1 and p.connectors[cid].tab_ids == ids
    restored = AuthorProject.from_dict(p.to_dict())
    assert restored.connectors[cid] == p.connectors[cid]
    assert restored.connector_geometry(cid) == p.connector_geometry(cid)


def test_custom_tab_outline_is_not_replaced_by_its_bounding_rectangle():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid, count=2, gap_mm=2)
    tab = p.connectors[cid].tab_ids[0]
    # Base100/2-2=48. The stepped author outline has area48*2+10*2=116.
    outline = [[0, 0], [48, 0], [48, 2], [29, 2], [29, 4], [19, 4], [19, 2], [0, 2]]
    p.set_connector_tab(cid, tab, shape="custom", outline_mm=outline)
    first = p.connector_geometry(cid)["tabs"][0]
    assert first["nominal_area_mm2"] == pytest.approx(116)
    actual = p.parts[p.part_for_surface(wall)].paths["TABS"][0]["points"]
    assert len(actual) == 8
    assert Polygon(actual).area == pytest.approx(116)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_connector_tab(cid, tab, outline_mm=[[0, 0], [48, 0], [0, 4], [48, 4]])
    assert p.to_dict() == before


def test_hole_off_trace_still_rejects_folded_glue_footprint_without_partial_mutation():
    p, wall, roof, edge = wall_roof()
    plane = p.profiles[p.surfaces[roof].profile_id].plane
    hole = p.add_profile([[1000, 300], [2000, 300], [2000, 500], [1000, 500]], plane=plane)
    p.add_hole(roof, hole)
    aid = p.attach_edge_to_surface(wall, edge, roof)
    assert p.attachment_geometry(aid)["valid"]  # Wall-top itself misses this hole.
    before = p.to_dict()
    with pytest.raises(ValidationError, match="FOLDED_GLUE_AREA_PARTIAL"):
        p.set_attachment_tab(aid, width_mm=5, taper=1)
    assert p.to_dict() == before


@pytest.mark.parametrize(
    "changes",
    [
        dict(count=0),
        dict(count=2.5),
        dict(count=True),
        dict(gap_mm=100),
        dict(gap_mm=-1),
        dict(width_mm=0),
    ],
)
def test_invalid_connector_parameters_roll_back(changes):
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_connector(cid, **changes)
    assert p.to_dict() == before


def test_individual_off_and_whole_off_preserve_ids_and_undo_snapshot():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid, count=3)
    saved = p.to_dict()
    ids = list(p.connectors[cid].tab_ids)
    p.set_connector(cid, enabled=False)
    assert p.connector_geometry(cid)["tabs"] == []
    assert p.connectors[cid].tab_ids == ids
    assert not p.parts[p.part_for_surface(wall)].paths["TABS"]
    p.set_connector(cid, enabled=True)
    assert len(p.connector_geometry(cid)["tabs"]) == 3
    undo = AuthorProject.from_dict(saved)
    assert undo.connectors[cid].tab_ids == ids
    assert (
        undo.part_geometry(undo.part_for_surface(wall))["paths"]
        == p.part_geometry(p.part_for_surface(wall))["paths"]
    )


def test_explicit_base_glue_region_limits_folded_footprint():
    p = AuthorProject.new(scale=1)
    wp = p.add_profile([[0, 0], [40, 0], [40, 20], [0, 20]], plane="XZ")
    wall = p.add_surface(wp)
    base = p.add_surface(p.add_profile([[-10, -10], [60, -10], [60, 30], [-10, 30]]))
    aid = p.set_glue_region(
        wall,
        base,
        [[0, 0], [40, 0], [40, 6], [0, 6]],
        source_edge_id=p.profiles[wp].segments[0].id,
        target_side="outside",
    )
    cid = p.set_attachment_tab(aid, width_mm=5, taper=1)
    assert p.connector_geometry(cid)["tabs"][0]["nominal_area_mm2"] == pytest.approx(200)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="PARTIAL"):
        p.set_connector(cid, width_mm=7)
    assert p.to_dict() == before


def test_standalone_glue_band_is_real_folded_material_with_two_real_receivers():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    wall_part = p.part_for_surface(wall)
    p.set_placement(
        wall_part, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True
    )
    placement = copy.deepcopy(p.placements[wall_part])
    before = page_points(p.parts[wall_part].polygons[wall][0], placement)
    band = p.add_glue_band(aid, width_mm=5)
    assert len(p.parts[band].surface_ids) == 2
    assert len(p.surfaces) == 4 and len(p.attachments) == 3
    assert sum(Polygon(v[0]).area for v in p.parts[band].polygons.values()) == pytest.approx(1000)
    assert p.placements[wall_part] == placement
    np.testing.assert_allclose(page_points(p.parts[wall_part].polygons[wall][0], placement), before)
    receivers = [a for a in p.attachments.values() if a.id != aid]
    assert {a.target_surface_id for a in receivers} == {wall, roof}
    for a in receivers:
        geometry = p.attachment_geometry(a.id)
        assert geometry["valid"], geometry
        assert geometry["available_area_mm2"] == pytest.approx(500)
    p.set_placement(band, p.pages[0].id, 20, 200, 17, position_locked=True, rotation_locked=True)
    restored = AuthorProject.from_dict(p.to_dict())
    assert restored.parts[band].surface_ids == p.parts[band].surface_ids
    assert restored.placements[band] == p.placements[band]
    assert restored.parts[band].frame == p.parts[band].frame


def test_inside_trace_cannot_fake_receiver_owned_flap_without_material_cut():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="bez řezu"):
        p.set_connector(cid, owner=roof)
    assert p.to_dict() == before


def test_flat_tab_collision_is_distinct_from_valid_folded_material_coverage():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid, count=2, taper=1)
    first = p.connectors[cid].tab_ids[0]
    before = p.to_dict()
    with pytest.raises(ValidationError, match="FLAT_CONNECTOR_COLLISION"):
        p.set_connector_tab(
            cid, first, shape="custom", outline_mm=[[0, 0], [50, 0], [60, 5], [0, 5]]
        )
    assert p.to_dict() == before


def test_distinct_flat_parts_can_collide_only_after_their_tabs_are_folded():
    p = AuthorProject.new(scale=1)
    target = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    for y in [30, 33]:
        profile = p.add_profile(
            [[20, 0], [60, 0], [60, 20], [20, 20]],
            plane={"origin": [0, y, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
        )
        source = p.add_surface(profile)
        aid = p.attach_edge_to_surface(source, p.profiles[profile].segments[0].id, target)
        p.set_attachment_tab(aid, width_mm=5, taper=1)
    issues = p.validate_layout()
    collision = [i for i in issues if i.code == "FOLDED_CONNECTOR_COLLISION"]
    assert collision and all(i.severity == "error" for i in collision)
    with pytest.raises(ValidationError):
        p.acknowledge(collision[0].id)


def test_removed_tab_identity_is_not_reused_when_count_grows_again():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid, count=3)
    original = list(p.connectors[cid].tab_ids)
    p.set_connector(cid, count=2)
    p.set_connector(cid, count=3)
    assert p.connectors[cid].tab_ids[:2] == original[:2]
    assert p.connectors[cid].tab_ids[2] not in original


def test_readonly_all_tabs_include_disabled_shape_and_core_calculated_base_length():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof, interval=[0.2, 0.8])
    cid = p.set_attachment_tab(aid, count=3, gap_mm=1, shape="triangle")
    tid = p.connectors[cid].tab_ids[1]
    p.set_connector_tab(cid, tid, enabled=False)
    before = p.to_dict()
    result = p.connector_geometry(cid)
    assert result["hinge_length_mm"] == pytest.approx(60)
    assert result["tab_length_mm"] == pytest.approx(19)
    assert len(result["all_tabs"]) == 3 and len(result["tabs"]) == 2
    selected = next(t for t in result["all_tabs"] if t["id"] == tid)
    assert not selected["enabled"] and selected["folded_contact"] is None
    np.testing.assert_allclose(selected["outline_mm"], [[0, 0], [19, 0], [9.5, 5]])
    np.testing.assert_allclose(selected["source_interval"], [0.405, 0.595])
    assert p.to_dict() == before


def test_remove_connector_and_bad_attachment_remain_possible_and_reversible():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid, count=2)
    saved = p.to_dict()
    p.set_transform(wall, [0, 0, 1])
    assert not p.connector_geometry(cid)["valid"]
    p.remove_connector(cid)
    assert cid not in p.connectors and p.attachments[aid].connector_id is None
    p.remove_attachment(aid)
    assert aid not in p.attachments
    p.recompute()
    undo = AuthorProject.from_dict(saved)
    assert cid in undo.connectors and aid in undo.attachments


@pytest.mark.parametrize("width", [float("inf"), float("nan"), True, "5"])
def test_nonfinite_or_nonnumeric_tab_size_is_typed_and_atomic(width):
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    cid = p.set_attachment_tab(aid)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_connector(cid, width_mm=width)
    assert p.to_dict() == before
