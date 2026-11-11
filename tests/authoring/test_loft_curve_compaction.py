"""Known polynomial splits, unequal parameters and complete manufacturing budgets."""

import copy
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project, loft_surface
from archpapercraft.authoring.loft_curve_compaction import (
    coalesce_native_loft_boundaries,
    restrict_cubic,
    reverse_segment,
)


def polynomial(controls, t):
    """Independent polynomial evaluation, not de Casteljau from the product."""
    if len(controls) == 2:
        return [(1-t)*a+t*b for a, b in zip(*controls)]
    return [(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
            for a, b, c, d in zip(*controls)]


def split_known_polynomial(controls, a, b):
    # Endpoint positions and analytic polynomial derivatives independently
    # reconstruct an exact restricted polynomial on nonuniform intervals.
    a, b = Fraction(a), Fraction(b)
    points = [tuple(map(Fraction, p)) for p in controls]
    start, end = polynomial(points, a), polynomial(points, b)
    if len(points) == 2:
        return [start, end]
    derivatives = []
    for t in (a, b):
        derivatives.append([3*((1-t)**2*(q-p)+2*(1-t)*t*(r-q)+t*t*(s-r))
                            for p, q, r, s in zip(*points)])
    return [start, [p+(b-a)*d/3 for p, d in zip(start, derivatives[0])],
            [p-(b-a)*d/3 for p, d in zip(end, derivatives[1])], end]


def segment(controls, a, b, *, profile="p", source="curve"):
    values = [list(map(float, p)) for p in controls]
    return {"kind": "line" if len(values) == 2 else "cubic",
            "start": values[0], "end": values[-1],
            "data": {} if len(values) == 2 else {"control1": values[1], "control2": values[2]},
            "source": {"profile_id": profile, "segment_id": source, "feature_id": "surface",
                       "patch_id": "patch", "parameter_interval": [float(a), float(b)],
                       "loft_parameter_interval": [float(a), float(b)], "direction": 1}}


def synthetic_native(first, *, patches=1):
    result = {"status": "CERTIFIED_REPRESENTATION_ONLY", "patches": [],
              "position_error_bound_paper_mm": .001,
              "boundary_length_error_bound_paper_mm": .002,
              "both_profile_boundaries_length_error_bound_paper_mm": .004,
              "line_interpolant_deviation_bound_paper_mm": .0001,
              "native_boundary_length_excess_bound_paper_mm": {"first": .0002, "second": .0003}}
    for index in range(patches):
        sides = {}
        for side, shift in (("first", 0), ("second", 2)):
            chain = copy.deepcopy(first)
            for s in chain:
                s["source"]["profile_id"] = side
                s["source"]["patch_id"] = str(index)
                for point in [s["start"], s["end"], *s["data"].values()]:
                    point[1] += shift
            sides[side] = {"segments": chain, "line_interpolant_deviation_bound_paper_mm": .0001,
                           "length_excess_bound_paper_mm": .0002}
        rulings = [{"kind": "line", "start": sides["first"]["segments"][-1]["end"],
                    "end": sides["second"]["segments"][-1]["end"], "data": {},
                    "source": {"kind": "EXPLICIT_MATCHED_RULING", "ruling_id": "right"}},
                   {"kind": "line", "start": sides["second"]["segments"][0]["start"],
                    "end": sides["first"]["segments"][0]["start"], "data": {},
                    "source": {"kind": "EXPLICIT_MATCHED_RULING", "ruling_id": "left"}}]
        result["patches"].append({**sides, "join_before_kind": "FOLD_CREASE",
                                  "source_patch_boundary_policy": "NO_CROSS_PATCH_SMOOTHING",
                                  "closed_boundary_segments": rulings})
    return result


def exact_chain(controls, parameters=(0, .125, .5, .875, 1)):
    return [segment(split_known_polynomial(controls, a, b), a, b)
            for a, b in zip(parameters, parameters[1:])]


def test_exact_restriction_is_the_same_known_polynomial_on_whole_unequal_interval():
    controls = [(0, 0), (8, 16), (16, -8), (32, 0)]
    restricted = restrict_cubic(controls, Fraction(1, 8), Fraction(7, 8))
    assert restricted == tuple(tuple(x) for x in split_known_polynomial(
        controls, Fraction(1, 8), Fraction(7, 8)))
    for t in (Fraction(0), Fraction(1, 7), Fraction(1, 2), Fraction(1)):
        assert polynomial(restricted, t) == polynomial(controls, Fraction(1, 8)+t*Fraction(3, 4))


def test_known_cubic_unequal_splits_coalesce_to_original_actual_controls_and_provenance():
    controls = [(0, 0), (8, 16), (16, -8), (32, 0)]
    native = synthetic_native(exact_chain(controls))
    original = copy.deepcopy(native)
    result = coalesce_native_loft_boundaries(native)
    merged = result["patches"][0]["first"]["segments"]
    assert len(merged) == 1 and merged[0]["kind"] == "cubic"
    assert [merged[0]["start"], *merged[0]["data"].values(), merged[0]["end"]] == [
        list(p) for p in controls]
    assert merged[0]["source"]["subintervals"] == [s["source"] for s in
                                                  native["patches"][0]["first"]["segments"]]
    assert Fraction(result["coalescing"]["position_bound_exact"]) == 0
    assert native == original
    merged[0]["source"]["subintervals"][0]["segment_id"] = "poison"
    assert native == original  # Public result is fully detached.


def test_bounded_line_merge_preserves_line_and_reports_nonzero_whole_interval_error():
    parameters = [0, .125, .375, 1]
    points = [[0, 0], [.5, 1e-8], [1.5, -1e-8], [4, 0]]
    chain = [segment([a, b], u, v) for a, b, u, v in
             zip(points, points[1:], parameters, parameters[1:])]
    result = coalesce_native_loft_boundaries(synthetic_native(chain))
    merged = result["patches"][0]["first"]["segments"]
    assert len(merged) == 1 and merged[0]["kind"] == "line" and merged[0]["data"] == {}
    error = Fraction(result["coalescing"]["position_bound_exact"])
    assert Fraction(1e-8) <= error < Fraction(1e-7)
    for p, u in zip(points, parameters):
        assert math.dist(p, polynomial([merged[0]["start"], merged[0]["end"]], u)) <= float(error)
    assert result["patches"][0]["first"]["ideal_continuity"].endswith("NOT_C1_CLAIM")


def test_same_locus_with_different_parameter_speed_is_not_zero_error_coalescing():
    parameters = [0, .125, .5, 1]
    chain = [segment([[a*a, 0], [b*b, 0]], a, b)
             for a, b in zip(parameters, parameters[1:])]
    result = coalesce_native_loft_boundaries(synthetic_native(chain))
    assert len(result["patches"][0]["first"]["segments"]) == len(chain)


def perturbed_chain():
    chain = exact_chain([(0, 0), (1, 0), (2, 0), (3, 0)], (0, .25, .75, 1))
    chain[1]["data"]["control1"][1] = 1e-6
    chain[1]["data"]["control2"][1] = 1e-6
    return chain


def length_of_chain(chain):
    """Independent Simpson integration of actual polynomial speed."""
    total = 0
    for s in chain:
        if s["kind"] == "line":
            total += math.dist(s["start"], s["end"])
            continue
        controls = [s["start"], s["data"]["control1"], s["data"]["control2"], s["end"]]
        def speed(t):
            return math.hypot(*[3*((1-t)**2*(b-a)+2*(1-t)*t*(c-b)+t*t*(d-c))
                               for a, b, c, d in zip(*controls)])
        n = 256
        total += (speed(0)+speed(1)+sum((4 if i % 2 else 2)*speed(i/n)
                                      for i in range(1, n)))/(3*n)
    return total


def test_actual_interior_extremum_and_global_length_bound_include_all_patches_and_sides():
    native = synthetic_native(perturbed_chain(), patches=3)
    result = coalesce_native_loft_boundaries(native)
    error = Fraction(result["coalescing"]["position_bound_exact"])
    assert error >= Fraction(7.5e-7)  # Interior hump, despite zero endpoint error.
    assert Fraction(result["coalescing"]["length_bound_exact"]["first"]) > Fraction(0)
    for side in ("first", "second"):
        local = [Fraction(p[side]["coalescing"]["length_bound_exact"])
                 for p in result["patches"]]
        global_bound = Fraction(result["coalescing"]["length_bound_exact"][side])
        assert global_bound == sum(local) and global_bound > max(local)
        observed = sum(abs(length_of_chain(a[side]["segments"])-
                           length_of_chain(b[side]["segments"]))
                       for a, b in zip(native["patches"], result["patches"]))
        assert observed < float(global_bound)
    assert result["boundary_length_error_bound_paper_mm"] >= (
        .002+max(result["coalescing"]["length_bound_paper_mm"].values()))
    assert result["both_profile_boundaries_length_error_bound_paper_mm"] >= (
        .004+sum(result["coalescing"]["length_bound_paper_mm"].values()))


def test_source_corner_patch_and_kind_boundaries_are_not_smoothed_or_crossed():
    chain = exact_chain([(0, 0), (1, 0), (2, 0), (3, 0)])
    for s in chain[2:]:
        s["source"]["segment_id"] = "other-source-corner"
    chain[-1] = segment([chain[-1]["start"], chain[-1]["end"]], .875, 1, source="line-source")
    native = synthetic_native(chain, patches=2)
    result = coalesce_native_loft_boundaries(native)
    for patch in result["patches"]:
        segments = patch["first"]["segments"]
        assert len(segments) == 3
        assert [s["kind"] for s in segments] == ["cubic", "cubic", "line"]
        assert segments[0]["end"] == chain[1]["end"]
        assert patch["source_patch_boundary_policy"] == "NO_CROSS_PATCH_SMOOTHING"
        rulings = [s for s in patch["closed_boundary_segments"] if
                   s["source"].get("kind") == "EXPLICIT_MATCHED_RULING"]
        assert [s["source"]["ruling_id"] for s in rulings] == ["right", "left"]


def test_backtracking_line_and_short_corner_remain_in_the_bound():
    points = [[0, 0], [1, 0], [.2, 1e-3], [2, 0]]
    chain = [segment([a, b], u/3, (u+1)/3) for u, (a, b) in
             enumerate(zip(points, points[1:]))]
    result = coalesce_native_loft_boundaries(synthetic_native(chain))
    assert result["patches"][0]["first"]["segments"] == synthetic_native(chain)["patches"][0][
        "first"]["segments"]


def test_nested_provenance_reverse_swaps_every_interval_and_uses_actual_coarse_derivatives():
    result = coalesce_native_loft_boundaries(synthetic_native(perturbed_chain()))
    patch = result["patches"][0]
    original = copy.deepcopy(patch["second"]["segments"][-1])
    backward = patch["closed_boundary_segments"][-2]
    assert backward["start"] == original["end"]
    assert backward["source"]["parameter_interval"] == [1, 0]
    assert [s["parameter_interval"] for s in backward["source"]["subintervals"]] == [
        list(reversed(s["parameter_interval"]))
        for s in reversed(original["source"]["subintervals"])]
    assert all(s["direction"] == -1 for s in backward["source"]["subintervals"])
    assert reverse_segment(backward) == original
    assert patch["second"]["binary_control_derivative_jump_bound_paper_mm_per_u"] == 0


def test_derivative_jump_certificate_is_recomputed_for_actual_coarse_binary_controls():
    chain = []
    for controls, offset in (([(0, 0), (1, 0), (2, 0), (3, 0)], 0),
                             ([(3, 0), (3, 1), (3, 2), (3, 3)], .5)):
        for a, b in ((0, .5), (.5, 1)):
            chain.append(segment(split_known_polynomial(controls, a, b),
                                 offset+a/2, offset+b/2))
    result = coalesce_native_loft_boundaries(synthetic_native(chain))
    boundary = result["patches"][0]["first"]
    assert len(boundary["segments"]) == 2
    assert not boundary["exact_c1_of_binary_controls"]
    # Analytic tangent jumps (6,0) -> (0,6), in common global loft u.
    assert math.sqrt(72) <= boundary["binary_control_derivative_jump_bound_paper_mm_per_u"] < 8.49


@pytest.mark.parametrize("limit", ["max_candidates", "max_comparisons"])
def test_work_caps_return_original_proved_geometry_without_partial_certificate(limit):
    native = synthetic_native(perturbed_chain(), patches=3)
    result = coalesce_native_loft_boundaries(native, **{limit: 1})
    diagnostic = result.pop("coalescing")
    assert diagnostic["status"] == "NOT_APPLIED_WORK_BUDGET_EXHAUSTED"
    assert result == native


@pytest.mark.parametrize("limit", ["max_candidates", "max_comparisons", "max_segments"])
@pytest.mark.parametrize("bad", [0, -1, True])
def test_invalid_work_caps_are_not_certified(limit, bad):
    with pytest.raises(ValueError):
        coalesce_native_loft_boundaries(synthetic_native(perturbed_chain()), **{limit: bad})


@pytest.mark.parametrize("damage", ["u", "source", "direction", "profile", "source-gap"])
def test_invalid_intervals_or_source_identity_are_rejected(damage):
    native = synthetic_native(perturbed_chain())
    s = native["patches"][0]["first"]["segments"][1]
    if damage == "u":
        s["source"]["loft_parameter_interval"] = [.25, .2]
    elif damage == "source":
        s["source"]["parameter_interval"] = [.25, .25]
    elif damage == "direction":
        s["source"]["direction"] = True
    elif damage == "profile":
        s["source"]["profile_id"] = ""
    else:
        s["source"]["parameter_interval"][0] = .3
    with pytest.raises(ValueError):
        coalesce_native_loft_boundaries(native)


def test_input_cap_no_remaining_budget_and_repeat_call_do_not_silently_spend_again():
    native = synthetic_native(perturbed_chain())
    with pytest.raises(ValueError):
        coalesce_native_loft_boundaries(native, max_segments=2)
    no_budget = coalesce_native_loft_boundaries(native, position_budget_mm=.001)
    assert no_budget.pop("coalescing")["status"] == "NOT_APPLIED_NO_REMAINING_ERROR_BUDGET"
    assert no_budget == native
    result = coalesce_native_loft_boundaries(native)
    assert coalesce_native_loft_boundaries(result) == result


def test_larger_merge_reserve_is_clipped_to_original_total_budget_remainder():
    native = synthetic_native(perturbed_chain(), patches=3)
    result = coalesce_native_loft_boundaries(
        native, position_budget_mm=.001001, length_budget_mm=.00201)
    assert result["position_error_bound_paper_mm"] <= .001001
    assert result["boundary_length_error_bound_paper_mm"] <= .00201
    assert result["coalescing"]["effective_position_budget_paper_mm"] <= .000001000001
    assert result["coalescing"]["effective_global_side_length_budget_paper_mm"] <= .000010000001


@pytest.mark.parametrize("key", ["position_budget_mm", "length_budget_mm",
                                  "merge_position_budget_mm", "merge_length_budget_mm"])
@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf")])
def test_invalid_error_budgets_are_rejected(key, value):
    with pytest.raises(ValueError):
        coalesce_native_loft_boundaries(synthetic_native(perturbed_chain()), **{key: value})


@pytest.mark.parametrize("old_contract", [
    "ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_EXACT_COLLINEAR_CUT_V2",
    "ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_BOUNDED_COALESCED_CUT_V3",
])
def test_previous_cache_stales_preserving_raw_file_source_layout_frame(
    tmp_path, monkeypatch, old_contract
):
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [20, 0], [20, 10]], closed=False)
    b = p.copy_profile(a, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    sid = p.add_loft(a, b, correspondences=[
        {"first_segment_id": x.id, "second_segment_id": y.id}
        for x, y in zip(p.profiles[a].segments, p.profiles[b].segments)])
    pid = p.part_for_surface(sid)
    p.set_placement(pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    with monkeypatch.context() as old:
        old.setattr(loft_surface, "LOFT_PAPER_CONTRACT", old_contract)
        p.recompute()
    original = p.to_dict()
    source = tmp_path / "V2.apcraft"
    raw = json.dumps(original).encode()
    source.write_bytes(raw)
    loaded = load_project(source)
    assert loaded.parts[pid].stale and loaded.loft_status(sid)["paper_stale"]
    assert [i.code for i in loaded.validate_layout()] == ["STALE"]
    expected = copy.deepcopy(original)
    expected["parts"][pid]["stale"] = True
    assert loaded.to_dict() == expected
    with pytest.raises(ValidationError):
        loaded.snapshot()
    loaded.recompute()
    assert not loaded.parts[pid].stale and not loaded.validate_layout()
    assert loaded.parts[pid].frame == p.parts[pid].frame and loaded.placements == p.placements
    assert loaded.profiles == p.profiles and loaded.surfaces == p.surfaces
    assert source.read_bytes() == raw
    loaded.save(tmp_path / "V3-copy.apcraft")
    restored = load_project(tmp_path / "V3-copy.apcraft")
    assert restored.to_dict() == loaded.to_dict()
    assert restored.loft_status(sid)["paper_contract"].endswith("V4")


def replay_source_file(source, output):
    """Reproducible backend audit, explicitly NOT a native/editor/novice proof."""
    import subprocess
    import time
    from dataclasses import asdict

    started = time.perf_counter()
    source = Path(source)
    raw = source.read_bytes()
    p = load_project(source)
    sid = next(sid for sid, surface in p.surfaces.items() if surface.kind == "ruled_loft")
    pid = p.part_for_surface(sid)
    original = p.to_dict()
    assert p.parts[pid].stale and p.loft_status(sid)["paper_stale"]
    assert "STALE" in [i.code for i in p.validate_layout()]
    with pytest.raises(ValidationError):
        p.snapshot()
    report = loft_surface.analysis(p, p.surfaces[sid])
    native = report["native"]
    for patch in native["patches"]:
        for s in [*patch["first"]["segments"], *patch["second"]["segments"],
                  *patch["closed_boundary_segments"]]:
            for record in [s["source"], *s["source"].get("subintervals", [])]:
                assert record["feature_id"] == sid and record["patch_id"] == patch["patch_id"]
    p.recompute()
    state = p.to_dict()
    for key in ("profiles", "surfaces", "placements", "pages", "next_part_number",
                "next_joint_number", "next_attachment_number"):
        assert original[key] == state[key]
    assert original["parts"][pid]["frame"] == asdict(p.parts[pid].frame)
    assert not p.parts[pid].stale and not p.loft_status(sid)["paper_stale"]
    assert not p.validate_layout() and p.snapshot()
    assert source.read_bytes() == raw
    destination = Path(output).with_suffix(".apcraft")
    p.save(destination)
    assert load_project(destination).to_dict() == p.to_dict()
    # Equal-area cache translation under CURRENT V3 must remain a hard error.
    bad = AuthorProject.from_dict(state)
    for command in bad.parts[pid].paths["CUT"][0]["commands"]:
        for i in range(1, len(command), 2):
            command[i] += .1
    bad = AuthorProject.from_dict(bad.to_dict())
    assert not bad.parts[pid].stale
    assert "INVALID_CACHE" in [i.code for i in bad.validate_layout()]
    with pytest.raises(ValidationError):
        bad.snapshot()
    root = Path(__file__).resolve().parents[2]
    result = {"source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root)
              .decode().strip(),
              "module": loft_surface.__file__, "fixture": str(source.resolve()),
              "fixture_sha256": hashlib.sha256(raw).hexdigest(),
              "evidence_scope": "BACKEND_PROOF_NOT_NATIVE_EDITOR_NOVICE_OR_PHYSICAL",
              "old_commands": len(original["parts"][pid]["paths"]["CUT"][0]["commands"]),
              "new_commands": len(p.parts[pid].paths["CUT"][0]["commands"]),
              "source_and_frame_and_layout_unchanged": True, "original_file_unchanged": True,
              "previous_contract_loaded_stale": True, "current_contract_poison_rejected": True,
              "save_reopen": True, "coalescing": native["coalescing"],
              "position_bound_paper_mm": native["position_error_bound_paper_mm"],
              "length_bound_paper_mm": native["boundary_length_error_bound_paper_mm"],
              "area": report["area"], "native_topology": report["native_topology"],
              "seconds": time.perf_counter()-started}
    Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("area", "native_topology")},
                     indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=replay_source_file.__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    replay_source_file(args.source, args.output)
