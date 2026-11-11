"""Readonly selection data and independent circle/triangle display expectations."""

import copy
import math

import pytest
from test_curved_connector_sources import receiver_source

from archpapercraft.authoring.curved_connectors import _prepare_native_slots


@pytest.mark.parametrize("side", ["first", "second"])
@pytest.mark.parametrize("scale", [1, 2])
def test_actual_source_hinge_and_glue_triangle_use_model_units_and_same_native_packet(side, scale):
    p, record, _ = receiver_source(side)
    p.set_scale(scale)
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.recompute()
    geometry = p.curved_connector_geometry(record.id)
    assert geometry["status"] == "CERTIFIED_APPROXIMATE"
    assert geometry["owner_surface_id"] == record.owner_surface_id
    assert geometry["receiver_surface_id"] == record.receiver_surface_id
    assert geometry["owner_part_id"] == p.part_for_surface(record.owner_surface_id)
    assert not geometry["display_is_proof"]
    native = _prepare_native_slots(p, record)["slots"]
    for row, slot in zip(geometry["all_tabs"], native, strict=True):
        assert row["id"] == slot["tab_id"]
        for key in ("paper_native_loop", "paper_shared_base_commands", "paper_cut_side_commands"):
            assert row[key] == slot[key]
        display = row["assembled_display"]
        assert display["scope"] == "DISPLAY_ONLY_ACTUAL_SOURCE_INTERVAL_MIDPOINTS_NOT_PROOF"
        assert display["units"] == "model_mm" and display["phase"] == 1
        assert not display["acceptance_uses_samples"]
        expected_z = 0 if side == "first" else 30
        for x, y, z in display["hinge_world"]:
            assert z == pytest.approx(expected_z, abs=1e-12)
            assert math.hypot(x, y) == pytest.approx(10, abs=1e-12)
        triangle = display["glue_patch_world"]
        assert len(triangle) == 4 and triangle[-1] == triangle[0]
        assert all(point[2] == pytest.approx(expected_z, abs=1e-12) for point in triangle)
        # Independent rigid glue region: radial 10-relief/scale at its base,
        # radial 10-depth/scale at its tip; width is similar triangles b(d-r)/d.
        base_length = 0.24 * (9.5 - 0.6) / 9.5 / scale
        assert math.dist(triangle[0], triangle[1]) == pytest.approx(base_length, abs=1e-12)
        assert math.hypot(*triangle[2][:2]) == pytest.approx(10 - 9.5 / scale, abs=1e-12)
        midpoint = [(triangle[0][axis] + triangle[1][axis]) / 2 for axis in range(2)]
        assert math.hypot(*midpoint) == pytest.approx(10 - 0.6 / scale, abs=1e-12)


def test_slot_pool_off_and_custom_tip_identity_are_preserved_in_detached_geometry():
    p, record, _ = receiver_source()
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.set_curved_tab(record.id, record.slot_ids[0], enabled=False)
    p.set_curved_tab(record.id, record.slot_ids[1], tip_offset_mm=0.01)
    p.update_curved_connector(record.id, count=8)
    p.recompute()
    before = p.to_dict()
    packet = p.curved_connector_geometry(record.id)
    assert packet["status"] == "CERTIFIED_APPROXIMATE"
    assert [row["id"] for row in packet["all_tabs"]] == record.slot_ids
    assert not packet["all_tabs"][0]["enabled"]
    assert packet["all_tabs"][0]["paper_native_loop"] is None
    assert packet["all_tabs"][1]["tip_offset_mm"] == 0.01
    assert all(not row["in_current_count"] for row in packet["all_tabs"][8:])
    assert sum(row["enabled"] for row in packet["all_tabs"]) == 7
    original = copy.deepcopy(packet)
    packet["all_tabs"][1]["paper_native_loop"][0][-1] += 1000
    packet["all_tabs"][1]["assembled_display"]["glue_patch_world"][0][0] += 1000
    assert p.curved_connector_geometry(record.id) == original
    assert p.to_dict() == before


def test_stale_unresolved_or_disabled_geometry_never_draws_a_current_certified_overlay():
    p, record, _ = receiver_source()
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.recompute()
    assert p.curved_connector_geometry(record.id)["status"] == "CERTIFIED_APPROXIMATE"
    p.surfaces[record.receiver_surface_id].position_mm[0] += 0.001
    stale = p.curved_connector_geometry(record.id)
    assert stale["status"] == "STALE" and stale["message"]
    assert all(row["assembled_display"] is None for row in stale["all_tabs"])
    assert all(row["paper_native_loop"] is None for row in stale["all_tabs"])
    p.update_curved_connector(record.id, enabled=False)
    off = p.curved_connector_geometry(record.id)
    assert off["status"] == "NOT_APPLICABLE"
    assert not any(row["enabled"] for row in off["all_tabs"])
    assert all(row["assembled_display"] is None for row in off["all_tabs"])


def test_source_native_strain_scope_does_not_claim_pdf_cubic_or_physical_deformation():
    p, record, _ = receiver_source()
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.recompute()
    report = p.curved_connector_material_report(record.owner_surface_id)
    strain = report["source_native_strain"]
    assert strain["status"] == "SOURCE_NATIVE_STRAIN_CERTIFIED"
    assert strain["scope"] == "CURRENT_SOURCE_TO_SAME_ACTUAL_NATIVE_A_L_WHOLE_COLLAR_CHART"
    assert strain["pdf_cubic_deformation"] == "NOT_CLAIMED"
    assert strain["physical_build"] == "NOT_VERIFIED"
