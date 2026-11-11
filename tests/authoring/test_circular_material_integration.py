"""Backend source → native material → persistence/publication, never UI proof."""

import copy
import math
from fractions import Fraction as Q

import pytest
from test_circular_shell import authored, circle
from test_loft_export import assert_actual_reports

from archpapercraft.authoring import ValidationError, load_project
from archpapercraft.authoring.curve_area import native_region_area_bounds
from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.loft_output_validation import validate_loft_snapshot


def constructed(*, side="first", r1=10, height=30):
    p, sid, pid = authored(10, r1, height)
    cap_profile = circle(p, 10 if side == "first" else r1, 0 if side == "first" else height)
    receiver = p.add_surface(cap_profile)
    cid = p.add_curved_connector(
        sid,
        side,
        receiver,
        receiver_side="inside" if side == "first" else "outside",
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
    )
    p.set_material_profile(thickness_mm=0.2, clearance_mm=0.01)
    p.recompute()
    second = p.add_page()
    p.set_placement(pid, p.pages[0].id, 70, 100, 17, position_locked=True, rotation_locked=True)
    p.set_placement(p.part_for_surface(receiver), second, 70, 100, 11)
    assert not [issue for issue in p.validate_layout() if issue.severity == "error"]
    # Digital geometry has no hard errors. Only physical/printing advisories
    # actually produced by this fixture are acknowledged by their identity.
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    return p, sid, pid, cid


@pytest.mark.parametrize("side", ["first", "second"])
def test_actual_callbacks_save_reopen_keep_material_ids_frame_layout_and_source(side, tmp_path):
    p, sid, pid, cid = constructed(side=side)
    status = p.curved_connector_status(cid)
    assert status["status"] == "CERTIFIED_APPROXIMATE"
    before = p.to_dict()
    source = tmp_path / "source.apcraft"
    p.save(source)
    raw = source.read_bytes()
    reopened = load_project(source)
    assert reopened.to_dict() == before
    assert reopened.parts[pid].frame == p.parts[pid].frame
    assert reopened.placements == p.placements
    assert reopened.curved_connectors[cid].slot_ids == p.curved_connectors[cid].slot_ids
    snapshot = reopened.snapshot()
    validate_loft_snapshot(snapshot)
    report = snapshot["construction_checks"]["lofts"][sid]["curved_material"]
    assert len(report["active_tab_ids"]) == 12
    actual_area = native_region_area_bounds([reopened.parts[pid].paths["CUT"][0]["commands"]])
    # Source independent: twelve triangles, b=.24 and h=9.5, body600π.
    assert float(actual_area[0]) == pytest.approx(600 * math.pi + 12 * 0.24 * 9.5 / 2, abs=1e-9)
    assert source.read_bytes() == raw


@pytest.mark.parametrize("mutation", ["cut", "fill", "guide", "receiver", "scene", "report"])
def test_full_source_and_native_material_publication_cannot_be_forged(mutation):
    p, sid, pid, cid = constructed()
    if mutation == "scene":
        sketch = p.add_profile([[0, 0], [5, 0], [5, 5], [0, 5]])
        far = p.add_surface(sketch)
        p.set_transform(far, [1000, 1000, 0])
        p.recompute()
        p.set_placement(p.part_for_surface(far), p.add_page(), 50, 50)
    snapshot = p.snapshot()
    bad = copy.deepcopy(snapshot)
    part = next(part for page in bad["pages"] for part in page["parts"] if part["id"] == pid)
    source = bad["construction_checks"]["curved_source_project"]
    if mutation in ("cut", "fill", "guide"):
        role = {"cut": "CUT", "fill": "TABS", "guide": "GUIDES"}[mutation]
        command = next(c for c in part["paths"][role][0]["commands"] if c[0] == "M")
        command[-2] += 0.001
    elif mutation == "receiver":
        receiver = p.curved_connectors[cid].receiver_surface_id
        source["surfaces"][receiver]["position_mm"][0] += 0.001
    elif mutation == "scene":
        source["surfaces"][far]["position_mm"][0] += 0.001
    else:
        report = bad["construction_checks"]["lofts"][sid]["curved_material"]
        report["source_material_area"]["area_lower_exact"] = "1"
    with pytest.raises(CurveOutputError):
        validate_loft_snapshot(bad)


def test_current_cache_equal_area_translation_is_invalid_and_direct_source_edit_stales():
    p, sid, pid, cid = constructed()
    raw = p.to_dict()
    for command in p.parts[pid].paths["CUT"][0]["commands"]:
        if command[0] in ("M", "L", "A"):
            command[-2] += 0.001
    assert "INVALID_CACHE" in [issue.code for issue in p.validate_layout()]
    with pytest.raises(ValidationError):
        p.snapshot()
    p = type(p).from_dict(raw)
    receiver = p.curved_connectors[cid].receiver_surface_id
    # Same UUID/revision does not excuse a different actual source matrix.
    p.surfaces[receiver].position_mm[0] += 0.01
    assert p.loft_status(sid)["paper_stale"]
    with pytest.raises(ValidationError):
        p.snapshot()


@pytest.mark.parametrize(
    "side,r1,height",
    [
        ("first", 10, 30),
        ("first", 20, math.sqrt(800)),
        ("second", 20, math.sqrt(800)),
        ("first", 10.000001, 30),
    ],
)
def test_actual_svg_pdf_preserve_source_union_body_norm_and_tiny_tab_reserve(
    tmp_path,
    side,
    r1,
    height,
):
    p, sid, pid, _ = constructed(side=side, r1=r1, height=height)
    directory = tmp_path / "bundle"
    export_all(p.snapshot(), directory)
    result = assert_actual_reports(directory, sid, pid)
    for output in result["outputs"].values():
        assert Q(output["tab_cut_position_error_exact"]) <= Q(1, 10**6)
        assert Q(output["tab_cut_global_length_error_exact"]) <= Q(1, 10**6)
        for role in ("guides", "tabs"):
            assert Q(output[role+"_position_error_exact"]) <= Q(1, 10**6)
            assert Q(output[role+"_global_length_error_exact"]) <= Q(1, 10**6)
        assert Q(output["source_to_actual_area_error_bound_exact"]) <= Q(1, 100)
