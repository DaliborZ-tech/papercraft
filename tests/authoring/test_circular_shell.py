"""Independent cylinder/frustum expectations, strict recognition and rim binding."""

import json
import math
from fractions import Fraction

import numpy as np
import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project, loft_surface
from archpapercraft.authoring.circular_shell import recognize, transform_native_commands
from archpapercraft.authoring.loft_geometry import LoftCorrespondence, LoftProfile


def circle(project, radius, z, *, quarters=False):
    points = [[radius, 0], [0, radius], [-radius, 0], [0, -radius], [radius, 0]]
    if not quarters:
        points = [points[0], points[2], points[4]]
    return project.add_profile(segments=[
        {"kind": "arc", "start": a, "end": b,
         "data": {"center": [0, 0], "sweep_deg": 90 if quarters else 180}}
        for a, b in zip(points, points[1:])], closed=True,
        plane={"origin": [0, 0, z], "u": [1, 0, 0], "v": [0, 1, 0]})


def authored(r0=10, r1=20, height=math.sqrt(800), *, reverse=False, quarters=False):
    p = AuthorProject.new(scale=1)
    a, b = circle(p, r0, 0, quarters=quarters), circle(p, r1, height, quarters=quarters)
    pairs = list(zip(p.profiles[a].segments, p.profiles[b].segments))
    if reverse:
        pairs.reverse()
    refs = [{"first_segment_id": x.id, "second_segment_id": y.id,
             "first_interval": [1, 0] if reverse else [0, 1],
             "second_interval": [1, 0] if reverse else [0, 1]} for x, y in pairs]
    sid = p.add_loft(a, b, correspondences=refs)
    pid = p.part_for_surface(sid)
    return p, sid, pid


@pytest.mark.parametrize("quarters", [False, True])
def test_manual_full_circle_cylinder_has_true_rectangle_width_and_no_fake_folds(quarters):
    p, sid, pid = authored(10, 10, 30, quarters=quarters)
    status = p.loft_status(sid)
    assert status["status"] == "EXACT"
    assert status["representation"]["circular_shell"]["family"] == "RIGHT_CIRCULAR_CYLINDER"
    commands = p.parts[pid].paths["CUT"][0]["commands"]
    assert {c[0] for c in commands} == {"M", "L", "Z"}
    points = [c[1:] for c in commands if c[0] != "Z"]
    assert max(x for x, _ in points)-min(x for x, _ in points) == pytest.approx(20*math.pi)
    assert max(y for _, y in points)-min(y for _, y in points) == 30
    assert status["area"]["actual_native"]["lower_paper_mm2"] == pytest.approx(600*math.pi)
    assert p.parts[pid].paths["FOLD_MOUNTAIN"] == p.parts[pid].paths["FOLD_VALLEY"] == []


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("height_sign", [-1, 1])
def test_frustum_native_arcs_have_independent_radii_area_and_outward_slopes(reverse, height_sign):
    p, sid, pid = authored(reverse=reverse, height=height_sign*math.sqrt(800))
    status = p.loft_status(sid)
    commands = p.parts[pid].paths["CUT"][0]["commands"]
    arcs = [c for c in commands if c[0] == "A"]
    assert len(arcs) == 8 and {c[1] for c in arcs} == {30, 60}
    assert all(c[1] == c[2] and c[3] == c[4] == 0 for c in arcs)
    assert not any(c[0] == "C" for c in commands)
    assert status["area"]["actual_native"]["lower_paper_mm2"] == pytest.approx(900*math.pi)
    assert status["area"]["maximum_error_bound_paper_mm2"] < .01
    assert status["native_topology"]["status"] == "VALID"
    assert p.parts[pid].paths["FOLD_MOUNTAIN"] == p.parts[pid].paths["FOLD_VALLEY"] == []
    for side, expected in (("first", Fraction(-1, 3)), ("second", Fraction(1, 3))):
        rim = p.circular_rim(sid, side, source_turn=.125)
        assert Fraction(rim["native_radial_slope_exact"]) == expected
        assert Fraction(rim["radius_exact"])/abs(expected) in (30, 60)
        outward = np.array(rim["world_frame"]["outward_z"])
        assert outward.tolist() == [0, 0, height_sign*(-1 if side == "first" else 1)]
        f = rim["world_frame"]
        matrix = np.column_stack([f[key] for key in ("radial", "tangent", "outward_z")])
        assert np.linalg.det(matrix) == pytest.approx(1)
        assert np.max(np.abs(matrix.T @ matrix-np.eye(3))) < 1e-14


def test_rim_pure_chart_circle_is_same_body_native_circle_after_reflection_and_paper_frame():
    p, sid, pid = authored()
    p.set_transform(sid, [10, 20, 30], [20, 30, 40])
    p.recompute()
    for side in ("first", "second"):
        rim = p.circular_rim(sid, side, source_turn=.31)
        radius, kappa = Fraction(rim["radius_exact"]), Fraction(rim["native_radial_slope_exact"])
        assert radius/abs(kappa) in (30, 60)
        # Exact shared-base identity from the separately specified pure chart.
        b = Fraction(2)
        q = kappa*b/(4*radius)
        xe, fe = b/2/(1+q*q), -kappa*b*b/(8*radius)/(1+q*q)
        assert xe*xe+(fe+radius/kappa)**2 == (radius/kappa)**2
        transform = rim["chart_to_canonical"]
        linear, shift = np.array(transform["matrix"]), np.array(transform["translation"])
        center = linear @ np.array([0, -float(radius/kappa)])+shift
        assert center == pytest.approx([0, 30], abs=1e-12)
        assert abs(np.linalg.det(linear)) == pytest.approx(1)
        actual = rim["paper_boundary_commands"]
        assert {c[1] for c in actual if c[0] == "A"} == {float(radius/abs(kappa))}
        ids = {s.id for s in p.profiles[rim["profile_id"]].segments}
        assert {s["segment_id"] for s in rim["source_intervals"]} == ids
        assert all(s["feature_id"] == sid for s in rim["source_intervals"])
        rim["source_intervals"][0]["segment_id"] = "poison"
        assert p.circular_rim(sid, side)["source_intervals"][0]["segment_id"] != "poison"


def test_rigid_native_transform_preserves_radius_flags_and_flips_sweep_only_for_reflection():
    commands = [["M", 0, 0], ["A", 30, 30, 0, 0, 1, 3, 4], ["Z"]]
    mapped = transform_native_commands(commands, [[0, -1], [1, 0]], [1, 2])
    assert mapped == [["M", 2., -1.], ["A", 30, 30, 0, 0, 1, -2., 2.], ["Z"]]
    reflected = transform_native_commands(commands, [[-1, 0], [0, 1]], [0, 0])
    assert reflected[1] == ["A", 30, 30, 0, 0, 0, -3., 4.]
    assert commands[1][5] == 1


def test_near_cylinder_is_a_native_cone_without_epsilon_reclassification():
    p, sid, _ = authored(10, 10.000001, 30)
    status = p.loft_status(sid)
    assert status["status"] == "EXACT"
    assert status["representation"]["circular_shell"]["family"] == "RIGHT_CIRCULAR_FRUSTUM"
    assert Fraction(p.circular_rim(sid)["native_radial_slope_exact"]) < 0
    assert status["area"]["maximum_error_bound_paper_mm2"] < .01
    assert status["representation"]["position_error_bound_paper_mm"] < .008


def test_giant_flat_radius_keeps_distinct_source_and_truthfully_falls_back_unresolved():
    radius = math.nextafter(10., math.inf)
    p, sid, _ = authored(10, radius, 30)
    assert p.profiles[p.surfaces[sid].params["second_profile_id"]].vertices[0].point[0] == radius
    assert p.loft_status(sid)["status"] == "UNRESOLVED"
    with pytest.raises(ValidationError):
        p.circular_rim(sid)
    with pytest.raises(ValidationError):
        p.snapshot()


def test_noncoaxial_or_inexact_basis_is_not_recognized_as_analytic_shell():
    p, sid, _ = authored()
    a, b = [LoftProfile.from_profile(p.profiles[pid])
            for pid in p.surfaces[sid].source_profile_ids()]
    references = [LoftCorrespondence(x.id, y.id) for x, y in
                  zip(p.profiles[a.profile_id].segments, p.profiles[b.profile_id].segments)]
    from dataclasses import replace

    assert recognize(a, replace(b, origin=(.001, 0, math.sqrt(800))), references, scale=1) is None
    assert recognize(replace(a, u=(1.000000000000001, 0, 0)), b, references, scale=1) is None


def test_current_cache_poison_is_not_accepted_by_rim_adapter():
    p, sid, pid = authored()
    for command in p.parts[pid].paths["CUT"][0]["commands"]:
        if command[0] == "A":
            command[-2] += .1
        elif command[0] in ("M", "L"):
            command[1] += .1
    restored = AuthorProject.from_dict(p.to_dict())
    assert not restored.parts[pid].stale
    with pytest.raises(ValidationError, match="INVALID_CACHE"):
        restored.circular_rim(sid)
    assert "INVALID_CACHE" in [i.code for i in restored.validate_layout()]


def test_old_v4_c_cache_recomputes_arcs_preserving_author_work(tmp_path, monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(loft_surface, "build_circular_shell", lambda *a, **kw: None)
        old.setattr(loft_surface, "LOFT_PAPER_CONTRACT",
                    "ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_BOUNDED_COALESCED_CUT_V4")
        p, sid, pid = authored()
        p.set_placement(pid, p.pages[0].id, 50, 60, 17,
                        position_locked=True, rotation_locked=True)
        assert any(c[0] == "C" for c in p.parts[pid].paths["CUT"][0]["commands"])
        raw = json.dumps(p.to_dict()).encode()
    # Simulate a new runtime, not a hot replacement of an in-memory producer.
    loft_surface._analyze.cache_clear()
    loft_surface._bound_analysis.cache_clear()
    loft_surface._world_mesh_json.cache_clear()
    source = tmp_path / "old-V4.apcraft"
    source.write_bytes(raw)
    loaded = load_project(source)
    assert loaded.parts[pid].stale and loaded.loft_status(sid)["paper_stale"]
    assert loaded.parts[pid].paths == p.parts[pid].paths
    assert [i.code for i in loaded.validate_layout()] == ["STALE"]
    loaded.recompute()
    assert any(c[0] == "A" for c in loaded.parts[pid].paths["CUT"][0]["commands"])
    assert loaded.placements == p.placements and loaded.parts[pid].frame == p.parts[pid].frame
    assert loaded.profiles == p.profiles and loaded.surfaces == p.surfaces
    assert not loaded.validate_layout() and loaded.snapshot()
    assert source.read_bytes() == raw
    loaded.save(tmp_path / "V5-copy.apcraft")
    assert load_project(tmp_path / "V5-copy.apcraft").to_dict() == loaded.to_dict()
    assert loaded.loft_status(sid)["paper_contract"].endswith("V5")


def test_material_envelope_covers_true_arc_between_display_nodes():
    from shapely.geometry import Point

    p, sid, pid = authored()
    result = loft_surface.analysis(p, p.surfaces[sid])
    n = len(result["solver"]["patches"][0]["parameters"])-1
    theta = math.pi*(.5/n)
    phase = -theta/3
    canonical = np.array([-60*math.sin(phase), -60*math.cos(phase)+30])
    rotation, origin = loft_surface._local_frame(p, p.parts[pid], result)
    point = Point(rotation @ (canonical-origin))
    envelope = loft_surface.material_envelopes(p, p.parts[pid])
    assert envelope.possible.covers(point)


def test_fraction_radius_below_binary_ulp_is_not_silently_cast_to_cylinder():
    p = AuthorProject.new(scale=1)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        circle(p, Fraction(10)+Fraction(1, 10**20), 30)
    assert p.to_dict() == before


def test_private_rim_binding_has_no_material_cache_recursion_and_exact_frame_intervals(monkeypatch):
    import archpapercraft.authoring.paper as paper

    p, sid, pid = authored()
    monkeypatch.setattr(paper, "part_input", lambda *_: pytest.fail("Recursive paper input"))
    rim = p._circular_rim_binding(sid, source_turn=.25, part_override=p.parts[pid])
    assert rim["paper_stale"] is None and not rim["material_cache_verified"]
    expected = {"radial": [0, 1, 0], "tangent": [1, 0, 0], "outward_z": [0, 0, -1]}
    for key, values in expected.items():
        for interval, value in zip(rim["source_world_frame_intervals"][key], values):
            assert Fraction(interval["lower_exact"]) <= value <= Fraction(interval["upper_exact"])
    assert Fraction(rim["world_frame_operator_error_bound_exact"]) >= 0
    assert Fraction(rim["source_native_kappa_error_bound_exact"]) > 0  # Actual binary H differs.
    assert rim["source_binding"]["surface"]["id"] == sid
