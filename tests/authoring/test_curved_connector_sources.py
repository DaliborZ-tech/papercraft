"""Actual authored disk/holes/side/frame binding, distinct from transfer proof."""

import math
from fractions import Fraction

import pytest
from test_circular_shell import authored, circle

from archpapercraft.authoring.curved_connectors import CurvedConnectorError, _receiver_binding
from archpapercraft.authoring.curved_tabs import Limits, Rim, certify_tabs, periodic_tabs


def receiver_source(side="second", *, hole=None, r0=10, r1=10, height=30):
    p, owner, _ = authored(r0, r1, height)
    z = 0 if side == "first" else height
    outer = circle(p, r0 if side == "first" else r1, z)
    holes = []
    if hole is not None:
        x, y, radius = hole
        holes.append(
            p.add_profile(
                segments=[
                    {
                        "kind": "arc",
                        "start": [x + radius, y],
                        "end": [x - radius, y],
                        "data": {"center": [x, y], "sweep_deg": 180},
                    },
                    {
                        "kind": "arc",
                        "start": [x - radius, y],
                        "end": [x + radius, y],
                        "data": {"center": [x, y], "sweep_deg": 180},
                    },
                ],
                plane={"origin": [0, 0, z], "u": [1, 0, 0], "v": [0, 1, 0]},
            )
        )
    receiver = p.add_surface(outer, holes)
    cid = p.add_curved_connector(
        owner,
        side,
        receiver,
        receiver_side="inside" if side == "first" else "outside",
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
    )
    record = p.curved_connectors[cid]
    rim = p._circular_rim_binding(owner, side)
    return p, record, rim


@pytest.mark.parametrize("side,expected_y,printed", [("first", -2, False), ("second", 2, True)])
def test_receiver_binds_actual_hole_plane_source_ids_and_printed_face(side, expected_y, printed):
    p, record, rim = receiver_source(side, hole=(3, 2, 0.5))
    cap, evidence = _receiver_binding(p, record, rim)
    assert cap.part_id == record.receiver_surface_id and cap.radius_mm == 10
    assert len(cap.holes) == 1
    assert (cap.holes[0].x_mm, cap.holes[0].y_mm, cap.holes[0].radius_mm) == (
        3,
        expected_y,
        Fraction(1, 2),
    )
    source = evidence["source_binding"]
    assert len(source["profiles"]) == 2
    receiver = p.surfaces[record.receiver_surface_id]
    assert [profile["id"] for profile in source["profiles"]] == receiver.source_profile_ids()
    assert source["surface"]["id"] == receiver.id
    assert evidence["receiver_contact_is_printed_side"] is printed
    p.set_front_side(receiver.part_id, "inside")
    _, changed = _receiver_binding(
        p, record, p._circular_rim_binding(record.owner_surface_id, side)
    )
    assert changed["receiver_contact_is_printed_side"] is not printed
    assert changed["source_digest"] != evidence["source_digest"]


@pytest.mark.parametrize("mutation", ["pose", "plane", "wrong_side", "not_disk"])
def test_no_nominal_disk_replaces_an_unproved_actual_receiver(mutation):
    p, record, rim = receiver_source()
    receiver = p.surfaces[record.receiver_surface_id]
    if mutation == "pose":
        p.set_transform(receiver.id, [1, 0, 0], [0, 0, 0])
    elif mutation == "plane":
        p.profiles[receiver.profile_id].plane.origin[2] += 0.001
    elif mutation == "wrong_side":
        record.receiver_side = "inside"
    else:
        receiver.profile_id = p.add_profile(
            [[0, 0], [20, 0], [0, 20]], plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]}
        )
    with pytest.raises(CurvedConnectorError):
        _receiver_binding(p, record, rim)


@pytest.mark.parametrize("side", ["first", "second"])
def test_ordinary_surface_translation_matches_exact_source_plane_placement(side):
    p, record, rim = receiver_source(side, hole=(3, 2, .5), r1=20)
    original_cap, original = _receiver_binding(p, record, rim)
    receiver = p.surfaces[record.receiver_surface_id]
    # Preserve the same actual world geometry using the ordinary surface tool.
    shift = [4, -3, 30]
    for pid in receiver.source_profile_ids():
        profile = p.profiles[pid]
        profile.plane.origin = [value-delta for value, delta in zip(profile.plane.origin, shift)]
    p.set_transform(receiver.id, shift)
    actual_cap, actual = _receiver_binding(p, record, p._circular_rim_binding(
        record.owner_surface_id, side))
    assert actual_cap == original_cap
    for key in ("source_radial", "source_tangent", "source_outward",
                "receiver_contact_is_printed_side"):
        assert actual[key] == original[key]
    assert actual["source_binding"]["receiver_translation_in_owner_source_exact"] == [
        "4", "-3", "30"]
    # No tolerance or center snapping: even one representable step is rejected.
    p.set_transform(receiver.id, [4, -3, math.nextafter(30, math.inf)])
    with pytest.raises(CurvedConnectorError, match="středu"):
        _receiver_binding(p, record, p._circular_rim_binding(record.owner_surface_id, side))


def test_actual_authored_hole_dominates_otherwise_positive_scoped_pure_contact():
    angle = math.pi / 12
    p, record, binding = receiver_source(hole=(9 * math.cos(angle), 9 * math.sin(angle), 0.2))
    cap, _ = _receiver_binding(p, record, binding)
    rim = Rim(
        Fraction(binding["radius_exact"]),
        Fraction(binding["native_radial_slope_exact"]),
        binding["rim_id"],
        record.owner_surface_id,
    )
    tabs = periodic_tabs(
        rim,
        cap.part_id,
        count=12,
        nominal_base_mm=Fraction(6, 25),
        depth_mm=Fraction(19, 2),
        relief_mm=Fraction(3, 5),
    )
    limits = Limits(Fraction(1, 100), Fraction(1, 100), 1, Fraction(1, 5), Fraction(1, 100))
    # This is the independently reviewed pure scope, not an application-wide
    # approval; the authored cap/holes feeding it are the actual source records.
    result = certify_tabs(rim, tabs, cap, limits)
    assert result["status"] == "INVALID"
    assert any(
        problem[2] == "Actual receiver lacks required glue material"
        for problem in result["problems"]
    )
    assert cap.holes  # A guessed unperforated nominal disk would pass this case.
    from dataclasses import replace

    assert (
        certify_tabs(rim, tabs, replace(cap, holes=()), limits)["status"] == "CERTIFIED_APPROXIMATE"
    )


@pytest.mark.parametrize("side", ["first", "second"])
@pytest.mark.parametrize(
    "r0,r1,height", [(10, 10, 30), (10, 20, math.sqrt(800)), (10, 10.000001, 30)]
)
def test_actual_native_packets_and_source_transfer_have_matching_slot_coverage(
    side, r0, r1, height
):
    from archpapercraft.authoring.curved_connectors import _prepare_native_slots

    p, record, _ = receiver_source(side, r0=r0, r1=r1, height=height)
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    prepared = _prepare_native_slots(p, record)
    report = prepared["source_transfer"]
    assert report["status"] == "CERTIFIED_TRANSFER", report["problems"]
    assert set(report["checked_ids"]) == set(record.slot_ids)
    assert len(report["pairs"]) == 66
    assert all(
        slot["native_chart_certificate"]["status"] == "CERTIFIED_NATIVE_CHART"
        for slot in prepared["slots"]
    )
    assert all(slot["source_intervals"] for slot in prepared["slots"])
    assert all(
        slot["paper_shared_base_commands"][1][0] == ("L" if r0 == r1 else "A")
        for slot in prepared["slots"]
    )
    for slot in prepared["slots"]:
        assert slot["tab_id"] in record.slot_ids
        assert slot["source_digest"] == prepared["source_fingerprint"]
        assert Fraction(slot["source_material_area_bounds_exact"][0]) > 1
        assert slot["paper_apex"] == slot["paper_cut_side_commands"][1][-2:]


def test_publisher_source_context_rebuilds_exact_current_records_without_derived_cache(tmp_path):
    from dataclasses import asdict

    from archpapercraft.authoring import UnsupportedOperationError
    from archpapercraft.authoring.curved_connectors import (
        _prepare_native_slots,
        rebuild_curved_material_binding,
    )

    p, record, _ = receiver_source()
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    body = p.loft_status(record.owner_surface_id)["source_binding"]
    frame = asdict(p.parts[p.surfaces[record.owner_surface_id].part_id].frame)
    source = p.curved_connector_inputs(record.owner_surface_id)
    context = rebuild_curved_material_binding(body, frame, source)
    assert context.curved_connector_inputs(record.owner_surface_id) == source
    assert context.curved_connectors[record.id].certificate == {}
    assert context.curved_connectors[record.id].material == {}
    assert _prepare_native_slots(context, context.curved_connectors[record.id]) == (
        _prepare_native_slots(p, record)
    )
    with pytest.raises(UnsupportedOperationError):
        context.save(tmp_path / "not-an-author-project.apcraft")
    assert not (tmp_path / "not-an-author-project.apcraft").exists()


@pytest.mark.parametrize("mutation", ["owner", "frame", "cache", "receiver_conflict"])
def test_publisher_source_context_rejects_conflicting_body_frame_or_inserted_cache(mutation):
    from dataclasses import asdict

    from archpapercraft.authoring import ValidationError
    from archpapercraft.authoring.curved_connectors import rebuild_curved_material_binding

    p, record, _ = receiver_source()
    body = p.loft_status(record.owner_surface_id)["source_binding"]
    frame = asdict(p.parts[p.surfaces[record.owner_surface_id].part_id].frame)
    source = p.curved_connector_inputs(record.owner_surface_id)
    if mutation == "owner":
        source["surfaces"][record.owner_surface_id]["position_mm"][0] += 1
    elif mutation == "frame":
        frame["anchor_vertex_id"] = p.project_id
    elif mutation == "cache":
        source["curved_connectors"][record.id]["certificate"] = {"status": "CERTIFIED"}
    else:
        source["surfaces"][record.receiver_surface_id]["position_mm"][0] += 1
    with pytest.raises(ValidationError):
        rebuild_curved_material_binding(body, frame, source)
