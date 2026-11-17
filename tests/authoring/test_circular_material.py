"""Native shared-base union; independent triangle/arc area expectations."""

import copy
import json
import math
from dataclasses import asdict
from fractions import Fraction as Q
from uuid import uuid4

import pytest
from test_circular_shell import authored

from archpapercraft.authoring import ValidationError, load_project, loft_surface
from archpapercraft.authoring.circular_material import (
    _digest,
    _source_coverage,
    compose_circular_rim_tabs,
)
from archpapercraft.authoring.curve_area import native_region_area_bounds
from archpapercraft.authoring.curved_tabs import Rim, Tab, _geometry, _pi
from archpapercraft.authoring.curved_tabs_chart import certify_native_tab_chart
from archpapercraft.authoring.paper import part_input
from archpapercraft.exporter.circular_output_validation import coordinate_errors


def exact_json(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(child) for child in value]
    return value


def mapped(commands, chart):
    matrix = [[Q(x) for x in row] for row in chart["matrix"]]
    offset = list(map(Q, chart["translation"]))
    reflection = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0] < 0
    result = []
    for command in commands:
        if command[0] == "Z":
            result.append(["Z"])
            continue
        point = list(map(Q, command[-2:]))
        end = [
            float(sum(x * y for x, y in zip(row, point)) + shift)
            for row, shift in zip(matrix, offset)
        ]
        result.append(
            [
                "A",
                float(command[1]),
                float(command[2]),
                0,
                int(command[4]),
                int(command[5]) ^ reflection,
                *end,
            ]
            if command[0] == "A"
            else [command[0], *end]
        )
    return result


def fixture(*, cone=False, side="first", count=12, reverse=False, frame_rotation=0):
    """Unit interface fixture, not a domain/UI/source-transfer acceptance proof."""
    p, sid, pid = authored(10, 20 if cone else 10, math.sqrt(800) if cone else 30, reverse=reverse)
    if frame_rotation:
        p.parts[pid].frame.rotation_deg = frame_rotation
        p.recompute()
    part = p.parts[pid]
    cid, receiver = str(uuid4()), str(uuid4())
    ids = [str(uuid4()) for _ in range(count)]
    record = {
        "owner_surface_id": sid,
        "receiver_surface_id": receiver,
        "rim_side": side,
        "slot_ids": ids,
        "enabled": True,
        "tab_overrides": {},
        "parameters": {
            "count": count,
            "depth_mm": 3,
            "relief_mm": 0.5,
            "nominal_base_mm": 2,
            "publication_error_budget_mm": 1e-6,
        },
    }
    inputs = {"curved_connectors": {cid: record}}
    p.curved_connector_inputs = lambda _: copy.deepcopy(inputs)
    full_rim = p._circular_rim_binding(sid, side, part_override=part)
    rim = Rim(
        Q(full_rim["radius_exact"]),
        Q(full_rim["native_radial_slope_exact"]),
        full_rim["rim_id"],
        sid,
    )
    slots = []
    for i, tab_id in enumerate(ids):
        center = float(Q(2 * i + 1, 2 * count))
        turn = (Q(center) * full_rim["source_turn_direction"]) % 1
        tab = Tab(tab_id, turn, 2, 3, 0.5, sid, receiver)
        geometry = _geometry(rim, tab)
        chart = p._circular_rim_binding(sid, side, source_turn=center, part_override=part)[
            "chart_to_paper"
        ]
        loop = mapped(geometry["flat_native_loop"], chart)
        base = mapped(geometry["shared_base_commands"], chart)
        sides = mapped(geometry["cut_side_commands"], chart)
        half = geometry["half_angle"]
        lower, upper = half[0] / (2 * _pi()[1]), half[1] / (2 * _pi()[0])
        bounds = [[Q(center) - upper, Q(center) - lower], [Q(center) + lower, Q(center) + upper]]
        source_ids = sorted({sid, *p.surfaces[sid].source_profile_ids(), rim.rim_id, cid, *ids})
        certificate = certify_native_tab_chart(
            rim,
            tab,
            base,
            sides[1][-2:],
            chart["matrix"],
            chart["translation"],
            source_ids=source_ids,
            source_digest=_digest(inputs),
        )
        slots.append(
            {
                "connector_id": cid,
                "tab_id": tab_id,
                "enabled": True,
                "owner_surface_id": sid,
                "receiver_surface_id": receiver,
                "rim_id": rim.rim_id,
                "rim_side": side,
                "paper_native_loop": loop,
                "paper_shared_base_commands": base,
                "paper_cut_side_commands": sides,
                "paper_apex": sides[1][-2:],
                "source_turn": center,
                "source_turn_interval_bounds_exact": exact_json(bounds),
                "shared_base_source_direction": full_rim["source_turn_direction"],
                "source_digest": _digest(inputs),
                "rim_source_digest": full_rim["source_digest"],
                "chart_to_paper": chart,
                "source_intervals": _source_coverage(p, full_rim, bounds[0][0], bounds[1][1]),
                "native_chart_certificate": exact_json(certificate),
                "reference_tab": exact_json(asdict(tab)),
                "source_material_area_bounds_exact": list(
                    map(str, native_region_area_bounds([geometry["flat_native_loop"]]))
                ),
            }
        )
    return p, sid, pid, inputs, slots


@pytest.mark.parametrize("side", ["first", "second"])
@pytest.mark.parametrize("reverse", [False, True])
def test_cylinder_triangles_add_material_without_cutting_the_shared_base(side, reverse):
    p, _, pid, _, slots = fixture(side=side, reverse=reverse)
    before = copy.deepcopy(p.parts[pid])
    part = compose_circular_rim_tabs(p, before, slots)
    # Twelve independent triangles, base 2 and height 3, add 36 mm².
    area = native_region_area_bounds([part.paths["CUT"][0]["commands"]])
    assert float(area[0]) == pytest.approx(600 * math.pi + 36, abs=1e-10)
    assert len(part.paths["TABS"]) == len(part.paths["GUIDES"]) == 12
    assert part.paths["FOLD_MOUNTAIN"] == part.paths["FOLD_VALLEY"] == []
    assert p.parts[pid] == before  # public input is never mutated
    assert part.id == before.id and part.frame == before.frame
    assert (
        sum(x["kind"] == "TAB_CUT" for x in part._circular_material_report["cut_command_ownership"])
        == 24
    )
    # Base endpoints join sides in CUT, while each base is a separate guide.
    commands = part.paths["CUT"][0]["commands"]
    for guide in part.paths["GUIDES"]:
        a, b = guide["commands"]
        assert not any(
            x[-2:] == a[-2:] and y[-2:] == b[-2:]
            for x, y in zip(commands, commands[1:])
            if y[0] == "L"
        )


@pytest.mark.parametrize("side", ["first", "second"])
def test_cone_shared_native_arc_union_preserves_body_only_area_budget(side):
    p, _, pid, _, slots = fixture(cone=True, side=side)
    part = compose_circular_rim_tabs(p, p.parts[pid], slots)
    # Direct analytic Green integral, independent of region-area implementation.
    k = -1 / 3 if side == "first" else 1 / 3
    radius = 10 if side == "first" else 20
    b, h = 2, 3
    q = k * b / (4 * radius)
    x = b / 2 / (1 + q * q)
    center_y, flat_radius = -radius / k, abs(radius / k)
    sweep = -4 * math.atan(q)
    arc_integral = -center_y * 2 * x + flat_radius**2 * sweep
    tab_area = abs((arc_integral + 2 * x * h) / 2)
    area = native_region_area_bounds([part.paths["CUT"][0]["commands"]])
    assert float(area[0]) == pytest.approx(900 * math.pi + 12 * tab_area, abs=2e-10)
    report = part._circular_material_report
    assert Q(report["allowed_body_area_error_exact"]) == Q(1, 100)
    assert Q(report["body_trim_position_error_exact"]) <= Q(1, 1000000)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "source", "apex", "area", "ids"])
def test_packet_forgery_is_rejected_without_mutating_material(mutation):
    p, _, pid, _, slots = fixture(count=2, cone=True)
    before = copy.deepcopy(p.parts[pid])
    if mutation == "duplicate":
        slots.append(copy.deepcopy(slots[0]))
    elif mutation == "missing":
        slots.pop()
    elif mutation == "source":
        slots[0]["source_digest"] = "0" * 64
    elif mutation == "apex":
        slots[0]["paper_apex"][0] += 0.01
    elif mutation == "area":
        slots[0]["source_material_area_bounds_exact"] = ["10000", "10000"]
    else:
        slots[0]["reference_tab"]["owner_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        compose_circular_rim_tabs(p, before, slots)
    assert p.parts[pid] == before


def test_foreign_scene_connector_is_dependency_not_owner_inventory():
    p, _, pid, inputs, slots = fixture(count=2)
    foreign = copy.deepcopy(next(iter(inputs["curved_connectors"].values())))
    foreign["owner_surface_id"] = str(uuid4())
    foreign["slot_ids"] = [str(uuid4())]
    inputs["curved_connectors"][str(uuid4())] = foreign
    # Rebinding requires fresh packets after every actual input change.
    with pytest.raises(ValidationError, match="stale"):
        compose_circular_rim_tabs(p, p.parts[pid], slots)
    assert part_input(p, p.parts[pid]) != p.parts[pid].input_digest


def test_actual_serialized_line_details_keep_initial_endpoint_and_global_error():
    source = [["M", 0, 0], ["L", 1, 0], ["L", 0, 1], ["Z"]]
    actual = [["M", Q(1, 10**5), 0], ["L", 1, 0], ["L", 0, 1], ["Z"]]
    details = []
    position, length = coordinate_errors(source, actual, details=details)
    assert position == Q(1, 10**5) and length == Q(2, 10**5)
    assert details[1]["position"] == Q(1, 10**5)
    assert sum(x["length"] for x in details) == length


def test_old_v5_material_cache_is_stale_preserving_source_frame_and_layout(tmp_path, monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(
            loft_surface,
            "LOFT_PAPER_CONTRACT",
            "ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_CIRCULAR_NATIVE_A_L_V5",
        )
        p, sid, pid = authored()
        p.set_placement(pid, p.pages[0].id, 50, 60, 17, position_locked=True, rotation_locked=True)
        raw = json.dumps(p.to_dict()).encode()
    source = tmp_path / "V5.apcraft"
    source.write_bytes(raw)
    loaded = load_project(source)
    assert loaded.parts[pid].stale and loaded.loft_status(sid)["paper_stale"]
    assert loaded.profiles == p.profiles and loaded.surfaces == p.surfaces
    assert loaded.placements == p.placements and loaded.parts[pid].frame == p.parts[pid].frame
    loaded.recompute()
    assert not loaded.parts[pid].stale
    assert loaded.loft_status(sid)["paper_contract"].endswith("V6")
    assert source.read_bytes() == raw


def test_split_source_provenance_spans_two_native_patches_and_rejects_invented_ids():
    p, sid, pid, _, slots = fixture(count=2, cone=True)
    # Centre 1/4 crosses the native quarter-circle boundary within segment 0.
    first = slots[0]["source_intervals"]
    assert len(first) == 2
    assert {r["feature_id"] for r in first} == {sid}
    assert len({r["patch_id"] for r in first}) == 1
    assert first[0]["parameter_coverage_exact"][1] == "1/2"
    assert first[1]["parameter_coverage_exact"][0] == "1/2"
    compose_circular_rim_tabs(p, p.parts[pid], slots)
    slots[0]["source_intervals"][0]["patch_id"] = str(uuid4())
    with pytest.raises(ValidationError, match="provenance"):
        compose_circular_rim_tabs(p, p.parts[pid], slots)


def test_disabling_one_stable_tab_keeps_other_identities_and_original_material():
    p, _, pid, inputs, slots = fixture(count=2)
    record = next(iter(inputs["curved_connectors"].values()))
    disabled = slots[0]["tab_id"]
    record["tab_overrides"][disabled] = {"enabled": False}
    active = slots[1]
    active["source_digest"] = _digest(inputs)
    rim = p._circular_rim_binding(p.parts[pid].surface_ids[0], active["rim_side"])
    tab = Tab(**active["reference_tab"])
    native_rim = Rim(
        Q(rim["radius_exact"]), Q(rim["native_radial_slope_exact"]), rim["rim_id"], tab.owner_id
    )
    ids = sorted(
        {
            tab.owner_id,
            *p.surfaces[tab.owner_id].source_profile_ids(),
            rim["rim_id"],
            active["connector_id"],
            *record["slot_ids"],
        }
    )
    active["native_chart_certificate"] = exact_json(
        certify_native_tab_chart(
            native_rim,
            tab,
            active["paper_shared_base_commands"],
            active["paper_apex"],
            active["chart_to_paper"]["matrix"],
            active["chart_to_paper"]["translation"],
            source_ids=ids,
            source_digest=active["source_digest"],
        )
    )
    supplied = [
        {"tab_id": disabled, "connector_id": slots[0]["connector_id"], "enabled": False},
        active,
    ]
    part = compose_circular_rim_tabs(p, p.parts[pid], supplied)
    assert len(part.paths["TABS"]) == 1
    assert part._circular_material_report["active_tab_ids"] == [active["tab_id"]]
    assert record["slot_ids"] == [disabled, active["tab_id"]]
    area = native_region_area_bounds([part.paths["CUT"][0]["commands"]])
    assert float(area[0]) == pytest.approx(600 * math.pi + 3, abs=1e-10)
