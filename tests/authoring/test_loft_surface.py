"""Domain integration oracles: authored source, true mesh, persistent frames and truthful status."""

import copy
import hashlib
import json
import math

import numpy as np
import pytest

from archpapercraft.authoring import (
    AuthorProject,
    ProjectFormatError,
    ValidationError,
    load_project,
)
from archpapercraft.authoring.loft_geometry import sample_loft
from archpapercraft.authoring.loft_surface import _native_topology, analysis


def test_snapshot_loft_binding_can_be_verified_from_actual_source_records():
    p, a, b = extrusion()
    sid = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(sid)
    p.set_placement(pid, p.pages[0].id, 30, 30)
    snapshot = p.snapshot()
    assert snapshot["coverage"]["expected_loft_surface_ids"] == [sid]
    report = snapshot["construction_checks"]["lofts"][sid]
    binding = report["source_binding"]
    state = p.to_dict()
    assert binding["profiles"] == [state["profiles"][a], state["profiles"][b]]
    assert binding["surface"] == state["surfaces"][sid]
    intrinsic = {
        "profiles": binding["profiles"],
        "params": binding["surface"]["params"],
        "scale": binding["scale"],
    }
    digest = hashlib.sha256(
        json.dumps(intrinsic, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    assert digest == report["intrinsic_source_digest"]
    actual = {"intrinsic_source_digest": digest, "surface": binding["surface"]}
    assert (
        hashlib.sha256(json.dumps(actual, sort_keys=True, allow_nan=False).encode()).hexdigest()
        == report["source_digest"]
    )
    binding["profiles"][0]["name"] = "detached mutation"
    assert p.profiles[a].name != "detached mutation"


def refs(project, a, b):
    return [
        {
            "first_segment_id": x.id,
            "second_segment_id": y.id,
            "first_interval": [0, 1],
            "second_interval": [0, 1],
        }
        for x, y in zip(project.profiles[a].segments, project.profiles[b].segments)
    ]


def extrusion(*, cubic=False, depth=10):
    p = AuthorProject.new(scale=1)
    if cubic:
        a = p.add_profile(
            segments=[
                {
                    "kind": "cubic",
                    "start": [0, 0],
                    "end": [6, 0],
                    "data": {"control1": [1, 0], "control2": [3, 0]},
                }
            ],
            closed=False,
        )
    else:
        a = p.add_profile([[0, 0], [20, 0], [20, 10]], closed=False)
    b = p.copy_profile(a, plane={"origin": [0, 0, depth], "u": [1, 0, 0], "v": [0, 1, 0]})
    return p, a, b


def gothic(p, width=20, height=30, *, plane=None):
    center = (height * height - width * width) / (2 * width)
    sweep = math.degrees(math.atan2(height, -center)) - 180
    return p.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [-width, 0],
                "end": [0, height],
                "data": {"center": [center, 0], "sweep_deg": sweep},
            },
            {
                "kind": "arc",
                "start": [0, height],
                "end": [width, 0],
                "data": {"center": [-center, 0], "sweep_deg": sweep},
            },
            {"kind": "line", "start": [width, 0], "end": [-width, 0]},
        ],
        plane=plane,
    )


def test_exact_open_extrusion_snapshot_uses_both_live_profiles_and_real_material():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    p.set_placement(pid, p.pages[0].id, 30, 30)
    status = p.loft_status(s)
    assert status["status"] == "EXACT" and status["family"] == "NORMAL_EXTRUSION"
    assert status["source_profile_ids"] == [a, b]
    assert status["source_revisions"] == {a: 1, b: 1}
    assert not p.validate_layout()
    snapshot = p.snapshot()
    assert snapshot["coverage"]["expected_surface_ids"] == [s]
    assert snapshot["construction_checks"]["lofts"][s]["source_profile_ids"] == [a, b]
    assert not snapshot["construction_checks"]["curve_regions"]
    loop = p.part_geometry(pid)["polygons"][s][0]
    from shapely import Polygon

    assert Polygon(loop).area == pytest.approx((20 + 10) * 10)
    assert "normal" not in p.world_geometry(s)  # There is no single normal for an L-shaped strip.


def test_preview_is_detached_and_actual_add_adopts_patch_identities():
    p, a, b = extrusion()
    before = p.to_dict()
    preview = p.preview_loft(a, b, correspondences=refs(p, a, b))
    assert p.to_dict() == before and preview["project_state"]["surfaces"]
    params = preview["params"]
    s = p.add_loft(
        a,
        b,
        correspondences=params["correspondences"],
        seam_patch_id=params["seam_patch_id"],
        end_ruling_id=params["end_ruling_id"],
    )
    assert p.surfaces[s].params == params


def test_preview_math_reused_by_fresh_document_but_bound_to_actual_feature(monkeypatch):
    import json

    from archpapercraft.authoring import loft_surface

    calls = []
    original = loft_surface.flatten_loft

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(loft_surface, "flatten_loft", counted)
    loft_surface._analyze.cache_clear()
    loft_surface._bound_analysis.cache_clear()
    p, a, b = extrusion(cubic=True)
    initial = p.to_dict()
    preview = p.preview_loft(a, b, correspondences=refs(p, a, b))
    assert len(calls) == 1
    actual = AuthorProject.from_dict(initial)  # Same restore used by command transactions.
    parameters = {
        k: preview["params"][k]
        for k in (
            "correspondences",
            "seam_patch_id",
            "end_ruling_id",
            "tolerance_mm",
            "max_segments",
        )
    }
    sid = actual.add_loft(a, b, **parameters)
    assert sid != preview["surface_id"] and len(calls) == 1
    report = analysis(actual, actual.surfaces[sid])
    assert report["source_digest"] != preview["source_digest"]
    assert report["intrinsic_source_digest"] == preview["intrinsic_source_digest"]
    assert (
        report["feature_id"]
        == report["solver"]["feature_id"]
        == report["native"]["feature_id"]
        == sid
    )
    for patch in report["native"]["patches"]:
        for side in ("first", "second"):
            assert all(s["source"]["feature_id"] == sid for s in patch[side]["segments"])
        assert all(s["source"]["feature_id"] == sid for s in patch["closed_boundary_segments"])
    actual.set_placement(actual.part_for_surface(sid), actual.pages[0].id, 20, 20)
    assert preview["surface_id"] not in json.dumps(actual.snapshot())
    assert preview["surface_id"] not in json.dumps(actual.to_dict())
    first = copy.deepcopy(report["solver"]["patches"][0]["flat_first_paper_mm"][0])
    report["native"]["patches"][0]["first"]["segments"][0]["source"]["feature_id"] = "poison"
    report["solver"]["patches"][0]["flat_first_paper_mm"][0][0] = 99999
    clean = analysis(actual, actual.surfaces[sid])
    assert "poison" not in json.dumps(clean)
    assert clean["solver"]["patches"][0]["flat_first_paper_mm"][0] == first
    actual.set_profile_plane(b, origin=[0, 0, 12], u=[1, 0, 0], v=[0, 1, 0])
    assert len(calls) == 2 and actual.loft_status(sid)["paper_stale"]


def test_b1_gothic_20_30_to_24_36_depth10_preserves_roof_corner_native_c_and_layout(tmp_path):
    p = AuthorProject.new(scale=1)
    a = gothic(p)
    b = p.copy_profile(a, factor=1.2, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    status = p.loft_status(s)
    assert status["status"] == "EXACT" and status["family"] == "POSITIVE_HOMOTHETIC_CONE"
    assert status["native_topology"]["status"] == "VALID"
    assert status["representation"]["position_error_bound_paper_mm"] <= 0.008
    assert status["representation"]["boundary_length_error_bound_paper_mm"] <= 0.008
    # Clockwise gothic outline: tangent at apex turns from (30,12.5) to
    # (30,-12.5). Its C0->C1 ruling has positive z: signed turn is negative.
    assert len(p.parts[pid].paths["FOLD_VALLEY"]) == 2
    assert not p.parts[pid].paths["FOLD_MOUNTAIN"]
    assert all(c["signed_angle_deg"] < 0 for c in status["crease_geometry"])
    original_cut = copy.deepcopy(p.parts[pid].paths["CUT"])
    original_params = copy.deepcopy(p.surfaces[s].params)
    p.set_front_side(pid, "inside")
    p.recompute()
    assert len(p.parts[pid].paths["FOLD_MOUNTAIN"]) == 2
    assert not p.parts[pid].paths["FOLD_VALLEY"]
    assert p.parts[pid].paths["CUT"] == original_cut
    assert p.surfaces[s].params == original_params
    assert any(c[0] == "C" for c in p.parts[pid].paths["CUT"][0]["commands"])
    mesh = p.world_geometry(s)
    assert len(mesh["vertex_sources"]) == len(mesh["vertex_normals"]) == len(mesh["vertices"])
    assert len(mesh["triangle_sources"]) == len(mesh["triangles"])
    assert (
        "normal" not in mesh and len({tuple(np.round(n, 3)) for n in mesh["vertex_normals"]}) > 10
    )
    for point, source in zip(mesh["vertices"], mesh["vertex_sources"]):
        if source["u"] == 0 and source["v"] == 0:
            assert point[2] == 0
        if source["u"] == 0 and source["v"] == 1:
            assert point[2] == 10
    page = p.add_page()
    p.set_placement(pid, page, 60, 60, 30, position_locked=True, rotation_locked=True)
    before = p.to_dict()
    target = tmp_path / "own-gothic.apcraft"
    p.save(target)
    reopened = load_project(target)
    assert reopened.to_dict() == before
    assert reopened.surfaces[s].params == p.surfaces[s].params
    assert reopened.placements[pid] == p.placements[pid]
    assert reopened.parts[pid].frame == p.parts[pid].frame


def test_s_shaped_source_has_opposite_analytic_fold_polarities_and_print_side_flips():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [20, 0], [20, 10], [40, 10]], closed=False)
    b = p.copy_profile(a, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)

    # Tangents x,y,x give normals -y,+x,-y and ruling +z. Therefore
    # normal turns are +90,-90; cumulative paper coordinates are 20,30 mm.
    def fold_x(role):
        return [line["points"][0][0] for line in p.parts[pid].paths[role]]

    assert fold_x("FOLD_MOUNTAIN") == [20]
    assert fold_x("FOLD_VALLEY") == [30]
    assert [c["signed_angle_deg"] for c in p.loft_status(s)["crease_geometry"]] == [90, -90]
    cut, params = copy.deepcopy(p.parts[pid].paths["CUT"]), copy.deepcopy(p.surfaces[s].params)
    p.set_front_side(pid, "inside")
    assert fold_x("FOLD_MOUNTAIN") == [30]
    assert fold_x("FOLD_VALLEY") == [20]
    p.recompute()
    assert fold_x("FOLD_MOUNTAIN") == [30]
    assert fold_x("FOLD_VALLEY") == [20]
    assert p.parts[pid].paths["CUT"] == cut and p.surfaces[s].params == params


def test_pre_ld01_loft_cache_contract_requires_recompute_before_export(monkeypatch):
    from archpapercraft.authoring import paper

    # Reproduce the old engine's digest contract: source geometry and frame
    # existed, but no signed-crease algorithm version was included.
    digest = paper.digest
    with monkeypatch.context() as context:
        context.setattr(
            paper,
            "digest",
            lambda data: digest(
                {key: value for key, value in data.items() if key != "loft_paper_contract"}
            ),
        )
        p, a, b = extrusion()
        s = p.add_loft(a, b, correspondences=refs(p, a, b))
    restored = AuthorProject.from_dict(p.to_dict())
    assert restored.loft_status(s)["paper_stale"]
    assert "STALE" in [issue.code for issue in restored.validate_layout()]
    with pytest.raises(ValidationError, match="neaktuální"):
        restored.snapshot()
    restored.recompute()
    assert not restored.loft_status(s)["paper_stale"]


def test_reversed_gothic_source_orientation_reverses_fold_polarity():
    p = AuthorProject.new(scale=1)
    original = gothic(p)
    profile = p.profiles[original]
    descriptors = []
    for segment in reversed(profile.segments):
        data = copy.deepcopy(segment.data)
        if segment.kind == "arc":
            data["sweep_deg"] = -data["sweep_deg"]
        descriptors.append(
            {
                "kind": segment.kind,
                "start": profile.vertex(segment.end_vertex_id).point,
                "end": profile.vertex(segment.start_vertex_id).point,
                "data": data,
            }
        )
    a = p.add_profile(segments=descriptors)
    b = p.copy_profile(a, factor=1.2, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    part = p.parts[p.part_for_surface(s)]
    # Reversing u reverses both normals and the before/after ordering; around
    # the same +v ruling each formerly negative corner becomes positive.
    assert len(part.paths["FOLD_MOUNTAIN"]) == 2 and not part.paths["FOLD_VALLEY"]
    assert all(c["signed_angle_deg"] > 0 for c in p.loft_status(s)["crease_geometry"])


def test_b2_closed_gothic_profiles_make_true_planar_region_with_hole_and_native_arcs():
    p = AuthorProject.new(scale=1)
    a = gothic(p)
    b = p.copy_profile(a, factor=1.2, center=[0, 15])
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    surface = p.surfaces[s]
    assert surface.kind == "planar" and surface.profile_id == b and surface.hole_profile_ids == [a]
    assert surface.params == {} and p.loft_status(s)["family"] == "PLANAR_REGION"
    assert p.loft_status(s)["status"] == "EXACT"
    loops = p.part_geometry(surface.part_id)["polygons"][s]
    assert len(loops) == 2
    assert all(
        any(c[0] == "A" for c in path["commands"]) for path in p.parts[surface.part_id].paths["CUT"]
    )
    material = p._source_polygon(b, [a])
    from shapely import Point

    assert not material.contains(Point(0, 10)) and material.contains(Point(0, 32))


def test_b3_independent_twisted_profiles_persist_target_with_specific_witness_and_block_export(
    tmp_path,
):
    p, a, b = extrusion(cubic=True)
    angle = math.radians(25)
    p.set_profile_plane(
        b,
        origin=[0, 0, 10],
        u=[math.cos(angle), math.sin(angle), 0],
        v=[-math.sin(angle), math.cos(angle), 0],
    )
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    status = p.loft_status(s)
    assert status["status"] == "REJECTED" and status["family"] == "NONDEVELOPABLE"
    assert status["witness"]["first_segment_id"] == p.profiles[a].segments[0].id
    assert p.parts[p.part_for_surface(s)].stale and not p.parts[p.part_for_surface(s)].polygons
    before = p.to_dict()
    p.save(tmp_path / "intended-twist.apcraft")
    assert load_project(tmp_path / "intended-twist.apcraft").to_dict() == before
    mesh = p.world_geometry(s)
    assert mesh["status"] == "REJECTED" and mesh["vertices"]
    assert (
        "DISPLAY_ONLY" in mesh["mesh_role"] and "NOT_ANALYTIC_INVERSE" in mesh["source_evaluation"]
    )
    with pytest.raises(ValidationError):
        p.recompute()
    assert p.to_dict() == before
    assert any(i.code == "LOFT_REJECTED" for i in p.validate_layout())
    with pytest.raises(ValidationError):
        p.snapshot()


def test_bezier_extrusion_l01_keeps_nonlinear_parameter_and_straight_flat_locus():
    p, a, b = extrusion(cubic=True)
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    report = analysis(p, p.surfaces[s])["solver"]
    assert p.loft_status(s)["status"] == "EXACT"
    patch = report["patches"][0]
    assert len(patch["parameters"]) > 2
    for u in [0.137, 0.333, 0.5, 0.731]:
        value = sample_loft(report, 0, u, 0.417)
        expected = 3 * u + 3 * u * u
        assert (
            math.dist(value["world_model_mm"], [expected, 0, 4.17])
            <= report["representation_error_bound_paper_mm"]
        )
        assert (
            math.dist(value["flat_paper_mm"], [expected, 4.17])
            <= report["representation_error_bound_paper_mm"]
        )
        assert value["mode"] == "BOUNDED_PARAMETER_INTERPOLATION"
    assert all(c[0] != "C" for c in p.parts[p.part_for_surface(s)].paths["CUT"][0]["commands"])
    assert p.profiles[a].segments[0].kind == "cubic" and p.profiles[b].segments[0].kind == "cubic"


@pytest.mark.parametrize("which", ["first", "second"])
def test_either_source_edit_stales_and_rebinds_actual_revision_without_moving_locked_frame(which):
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    p.set_placement(pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    frame, place = copy.deepcopy(p.parts[pid].frame), copy.deepcopy(p.placements[pid])
    old = p.loft_status(s)["source_digest"]
    profile = a if which == "first" else b
    p.set_profile_plane(
        profile, origin=[0, 0, -2 if profile == a else 12], u=[1, 0, 0], v=[0, 1, 0]
    )
    assert p.parts[pid].stale and p.loft_status(s)["source_digest"] != old
    p.recompute()
    assert p.parts[pid].frame == frame and p.placements[pid] == place and not p.parts[pid].stale
    assert p.loft_status(s)["source_revisions"][profile] == p.profiles[profile].revision


def test_replacement_stays_unresolved_without_nearest_or_anchor_fallback():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    frame, mappings = (
        copy.deepcopy(p.parts[pid].frame),
        copy.deepcopy(p.surfaces[s].params["correspondences"]),
    )
    p.update_profile(a, [[0, 0], [20, 0], [20, 10]], closed=False)
    assert p.loft_status(s)["status"] == "UNRESOLVED"
    assert p.surfaces[s].params["correspondences"] == mappings and p.parts[pid].frame == frame
    assert not p.world_geometry(s)["vertices"]
    with pytest.raises(ValidationError):
        p.recompute()
    repaired = refs(p, a, b)
    for record, previous in zip(repaired, mappings):
        record.update(id=previous["id"], ruling_id=previous["ruling_id"])
    p.update_loft(s, correspondences=repaired)
    assert (
        p.parts[pid].frame == frame
    )  # Explicit new correspondence does not repair an absent anchor.
    with pytest.raises(ValidationError, match="ANCHOR_UNRESOLVED"):
        p.recompute()


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r[0].update(id=True),
        lambda r: r[0].update(first_segment_id=""),
        lambda r: r[0].update(ruling_id="not-a-uuid"),
        lambda r: r.pop(),
        lambda r: r[1].update(second_segment_id=r[0]["second_segment_id"]),
        lambda r: r[0].update(first_interval=[True, 1]),
        lambda r: r[0].update(second_interval=[0.1, 0.9]),
    ],
)
def test_bad_ids_or_incomplete_correspondence_are_atomic(change):
    p, a, b = extrusion()
    mappings = refs(p, a, b)
    before = p.to_dict()
    change(mappings)
    with pytest.raises(ValidationError):
        p.add_loft(a, b, correspondences=mappings)
    assert p.to_dict() == before


def test_new_zero_area_same_plane_target_is_rejected_atomically():
    p, a, _ = extrusion()
    b = p.copy_profile(a)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="nulovou"):
        p.add_loft(a, b, correspondences=refs(p, a, b))
    assert p.to_dict() == before


def test_native_loft_topology_broad_phase_keeps_exact_crossing_rejection():
    bow = [["M", 0, 0], ["L", 10, 10], ["L", 0, 10], ["L", 10, 0], ["Z"]]
    result = _native_topology(bow)
    assert result["status"] == "INVALID" and result["witness"]
    # Cubic height at t=.5 is7.5e-13, above the opposite line y=5e-13:
    # the two crossings are real even though a coarse display chord misses them.
    narrow = [
        ["M", 0, 0],
        ["C", 3, 1e-12, 7, 1e-12, 10, 0],
        ["L", 10, 5e-13],
        ["L", 0, 5e-13],
        ["Z"],
    ]
    assert _native_topology(narrow)["status"] != "VALID"


def test_strict_loft_schema_rejects_corrupted_patch_and_unknown_param():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    data = p.to_dict()
    data["surfaces"][s]["params"]["hidden_nearest_fallback"] = True
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)


def test_rigid_transform_area_precision_guard_is_atomic_for_loft():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    before = p.to_dict()
    with pytest.raises(ValidationError, match="přesnost"):
        p.set_transform(s, [1e18, 1e18, 1e18])
    assert p.to_dict() == before


@pytest.mark.parametrize("argument", ["seam_patch_id", "end_ruling_id"])
def test_false_is_not_an_implicit_default_identity(argument):
    p, a, b = extrusion()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_loft(a, b, correspondences=refs(p, a, b), **{argument: False})
    assert p.to_dict() == before


def test_identity_collision_is_rejected_before_the_mathematical_solver(monkeypatch):
    p, a, b = extrusion()
    mappings = refs(p, a, b)
    mappings[0]["id"] = a  # Valid UUID, but already the source profile's identity.
    before = p.to_dict()
    monkeypatch.setattr(
        "archpapercraft.authoring.loft_surface.flatten_loft",
        lambda *args, **kw: pytest.fail("Bad identity reached the numeric solver"),
    )
    with pytest.raises(ValidationError, match="koliduje"):
        p.add_loft(a, b, correspondences=mappings)
    assert p.to_dict() == before


def test_independent_rounding_does_not_become_an_epsilon_fitted_exact_homothety():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [17, 0], [17, 29]], closed=False)
    b = p.copy_profile(a, factor=1.2, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    source = copy.deepcopy(p.profiles)
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    assert p.loft_status(s)["status"] == "UNRESOLVED"
    assert p.profiles == source
    with pytest.raises(ValidationError):
        p.snapshot()


def test_retarget_second_profile_keeps_frame_and_replaces_only_live_dependency():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    frame = copy.deepcopy(p.parts[pid].frame)
    previous = copy.deepcopy(p.surfaces[s].params)
    other = p.copy_profile(a, plane={"origin": [0, 0, 20], "u": [1, 0, 0], "v": [0, 1, 0]})
    mappings = refs(p, a, other)
    for record, old in zip(mappings, previous["correspondences"]):
        record.update(id=old["id"], ruling_id=old["ruling_id"])
    p.update_loft(s, second_profile_id=other, correspondences=mappings)
    assert p.parts[pid].stale and p.parts[pid].frame == frame
    p.recompute()
    assert p.surfaces[s].params["seam_patch_id"] == previous["seam_patch_id"]
    assert p.surfaces[s].params["end_ruling_id"] == previous["end_ruling_id"]
    assert p.loft_status(s)["source_profile_ids"] == [a, other]
    digest = p.loft_status(s)["source_digest"]
    p.set_profile_plane(b, origin=[0, 0, 99], u=[1, 0, 0], v=[0, 1, 0])
    assert not p.parts[pid].stale and p.loft_status(s)["source_digest"] == digest
    assert b in p.profiles


@pytest.mark.parametrize(
    "field,value",
    [("role", "PLANAR"), ("parameter_interval", [False, 1]), ("profile_id", "not-a-uuid")],
)
def test_current_cached_loft_source_metadata_is_strictly_typed(field, value):
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    data = p.to_dict()
    data["parts"][p.part_for_surface(s)]["edges"][0]["source"][field] = value
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)


def test_loft_minimum_detail_is_a_warning_not_a_silent_skipped_check():
    p, a, b = extrusion(depth=0.1)
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    p.set_placement(p.part_for_surface(s), p.pages[0].id, 30, 30)
    warnings = [i for i in p.validate_layout() if i.code == "SMALL_DETAIL"]
    assert len(warnings) == 1 and warnings[0].severity == "warning"


def test_world_pose_binding_changes_without_inventing_a_new_intrinsic_family_proof():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    before = p.loft_status(s)
    p.set_transform(s, [100, 200, 300], [10, 20, 30])
    after = p.loft_status(s)
    assert before["intrinsic_source_digest"] == after["intrinsic_source_digest"]
    assert before["source_digest"] != after["source_digest"]
    assert before["feature_revision"] < after["feature_revision"] and after["paper_stale"]


def test_missing_source_and_malformed_update_are_typed_atomic_commands():
    from uuid import uuid4

    p, a, b = extrusion()
    original = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_loft(a, str(uuid4()), correspondences=refs(p, a, b))
    assert p.to_dict() == original
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    original = p.to_dict()
    for malformed in (False, {}, [], [False], [None]):
        with pytest.raises(ValidationError):
            p.update_loft(s, correspondences=malformed)
        assert p.to_dict() == original


def test_existing_loft_preview_updates_detached_identity_without_duplicate_patch_ids():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    p.set_placement(pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    other = p.copy_profile(a, plane={"origin": [0, 0, 12], "u": [1, 0, 0], "v": [0, 1, 0]})
    old = copy.deepcopy(p.surfaces[s].params)
    mapping = refs(p, a, other)
    for new, previous in zip(mapping, old["correspondences"]):
        new.update(id=previous["id"], ruling_id=previous["ruling_id"])
    before = p.to_dict()
    result = p.preview_loft_update(s, second_profile_id=other, correspondences=mapping)
    assert p.to_dict() == before
    assert result["surface_id"] == s and result["part_id"] == pid
    assert result["status"] == "EXACT" and result["paper_stale"]
    preview = AuthorProject.from_dict(result["project_state"])
    assert preview.parts[pid].frame == p.parts[pid].frame
    assert preview.placements[pid] == p.placements[pid]
    assert result["params"]["end_ruling_id"] == old["end_ruling_id"]
    assert [r["id"] for r in result["params"]["correspondences"]] == [
        r["id"] for r in old["correspondences"]
    ]
    assert max(v[2] for v in result["world_geometry"]["vertices"]) == 12
    p.update_loft(s, second_profile_id=other, correspondences=result["params"]["correspondences"])
    assert p.to_dict() == result["project_state"]
    p.recompute()
    assert not p.parts[pid].stale and p.placements[pid] == preview.placements[pid]


@pytest.mark.parametrize("new_capability", ["loft", "orphan_curve"])
def test_schema_three_copy_adapter_rejects_capabilities_it_never_defined(new_capability):
    p, a, b = extrusion(cubic=new_capability == "orphan_curve")
    if new_capability == "loft":
        p.add_loft(a, b, correspondences=refs(p, a, b))
    data = p.to_dict()
    data.update(schema_version=3, writer_version="0.3.0-pc006b-clearance-experimental")
    with pytest.raises(ProjectFormatError, match="Starší formát"):
        AuthorProject.from_dict(data)


def test_schema_three_copy_adapter_still_preserves_known_planar_sources_and_layout():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [20, 0], [20, 10], [0, 10]])
    s = p.add_surface(a)
    pid = p.part_for_surface(s)
    p.set_placement(pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True)
    data = p.to_dict()
    data.update(schema_version=3, writer_version="0.3.0-pc006b-clearance-experimental")
    restored = AuthorProject.from_dict(data)
    assert restored.profiles == p.profiles and restored.surfaces == p.surfaces
    assert restored.parts[pid].frame == p.parts[pid].frame
    assert restored.placements == p.placements and restored.parts[pid].stale


def test_open_loft_seam_must_remain_the_actual_first_patch_atomically_and_on_read():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    before = p.to_dict()
    second = p.surfaces[s].params["correspondences"][1]["id"]
    with pytest.raises(ValidationError, match="Šev"):
        p.update_loft(s, seam_patch_id=second)
    assert p.to_dict() == before
    data = copy.deepcopy(before)
    data["surfaces"][s]["params"]["seam_patch_id"] = second
    with pytest.raises(ProjectFormatError, match="Šev"):
        AuthorProject.from_dict(data)


def test_closed_loft_seam_update_reorders_live_patches_without_replacing_identity_or_frame():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [10, 0], [10, 10], [0, 10]])
    b = p.copy_profile(a, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    original = copy.deepcopy(p.surfaces[s].params["correspondences"])
    frame = copy.deepcopy(p.parts[pid].frame)
    p.update_loft(s, seam_patch_id=original[1]["id"])
    assert p.surfaces[s].params["correspondences"] == original[1:] + original[:1]
    p.recompute()
    assert p.parts[pid].frame == frame
    assert p.loft_status(s)["status"] == "EXACT"
    assert AuthorProject.from_dict(p.to_dict()).to_dict() == p.to_dict()


@pytest.mark.parametrize("scale,model_factor", [(1, 1), (0.01, 100)])
def test_long_semicircle_extrusion_refines_against_independent_intrinsic_area(
    tmp_path, scale, model_factor
):
    from fractions import Fraction

    from archpapercraft.authoring.curve_area import native_region_area_bounds

    p = AuthorProject.new(scale=scale)
    a = p.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [20 * model_factor, 0],
                "end": [-20 * model_factor, 0],
                "data": {"center": [0, 0], "sweep_deg": 180},
            }
        ],
        closed=False,
    )
    b = p.copy_profile(
        a, plane={"origin": [0, 0, 200 * model_factor], "u": [1, 0, 0], "v": [0, 1, 0]}
    )
    source = copy.deepcopy(p.profiles)
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    status = p.loft_status(s)
    assert status["status"] == "EXACT"
    assert p.profiles == source
    attempts = status["area"]["refinement_attempts"]
    assert len(attempts) > 1 and attempts[0]["status"] == "UNRESOLVED"
    assert attempts[-1]["status"] == "CERTIFIED"
    assert status["effective_tolerance_mm"] < status["requested_tolerance_mm"]
    pid = p.part_for_surface(s)
    p.set_placement(pid, p.pages[0].id, 25, 25)
    bounds = native_region_area_bounds([p.parts[pid].paths["CUT"][0]["commands"]])
    expected = 4000 * math.pi  # R20 semicircle's exact length 20pi times depth200.
    assert max(abs(float(value) - expected) for value in bounds) <= max(0.01, expected * 1e-6)
    assert Fraction(status["area"]["maximum_error_bound_exact"]) <= Fraction(
        status["area"]["allowed_error_exact"]
    )
    assert status["paper_frame_area"]["status"] == "CERTIFIED"
    assert not p.validate_layout()
    target = tmp_path / "long-curved-strip.apcraft"
    p.save(target)
    reopened = load_project(target)
    assert reopened.profiles == source
    assert reopened.snapshot()["construction_checks"]["lofts"][s]["area"]["status"] == "CERTIFIED"


def test_concentric_semicircle_frustum_uses_intrinsic_area_not_proxy_polygon():
    from archpapercraft.authoring.curve_area import native_region_area_bounds

    p = AuthorProject.new(scale=1)
    a = p.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [20, 0],
                "end": [-20, 0],
                "data": {"center": [0, 0], "sweep_deg": 180},
            }
        ],
        closed=False,
    )
    b = p.copy_profile(a, factor=1.2, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    status = p.loft_status(s)
    assert (
        status["status"] == "EXACT" and status["area"]["source_intrinsic"]["status"] == "CERTIFIED"
    )
    bounds = native_region_area_bounds([p.parts[p.part_for_surface(s)].paths["CUT"][0]["commands"]])
    expected = 22 * math.pi * math.sqrt(116)  # Half frustum: (r0+r1)/2 * angle * slant.
    assert max(abs(float(value) - expected) for value in bounds) <= 0.01


def test_unproved_intrinsic_area_preserves_target_and_blocks_exact_and_export(monkeypatch):
    from archpapercraft.authoring import loft_surface

    monkeypatch.setattr(
        loft_surface,
        "_source_intrinsic_area",
        lambda data: {
            "status": "UNRESOLVED",
            "message": "Deliberate independent area budget exhaustion",
        },
    )
    loft_surface._analyze.cache_clear()
    loft_surface._bound_analysis.cache_clear()
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    assert s in p.surfaces and p.profiles[a].segments and p.profiles[b].segments
    assert p.loft_status(s)["status"] == "UNRESOLVED"
    assert p.loft_status(s)["code"] == "LOFT_INTRINSIC_AREA_UNRESOLVED"
    assert AuthorProject.from_dict(p.to_dict()).surfaces[s] == p.surfaces[s]
    with pytest.raises(ValidationError, match="plocha"):
        p.snapshot()


def test_area_refinement_keeps_declared_node_cap_and_preserves_unresolved_target():
    p = AuthorProject.new(scale=1)
    a = p.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [20, 0],
                "end": [-20, 0],
                "data": {"center": [0, 0], "sweep_deg": 180},
            }
        ],
        closed=False,
    )
    b = p.copy_profile(a, plane={"origin": [0, 0, 200], "u": [1, 0, 0], "v": [0, 1, 0]})
    source = copy.deepcopy(p.profiles)
    s = p.add_loft(a, b, correspondences=refs(p, a, b), max_segments=512)
    status = p.loft_status(s)
    assert status["status"] == "UNRESOLVED" and status["code"] == "LOFT_AREA_UNRESOLVED"
    assert 1 < len(status["area"]["refinement_attempts"]) <= 5
    assert p.surfaces[s].params["max_segments"] == 512 and p.profiles == source
    assert AuthorProject.from_dict(p.to_dict()).surfaces[s] == p.surfaces[s]
    with pytest.raises(ValidationError, match="Plocha rozvinu"):
        p.snapshot()


def test_actual_cached_native_area_is_checked_against_source_not_only_proxy_polygon():
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    pid = p.part_for_surface(s)
    p.set_placement(pid, p.pages[0].id, 25, 25)
    original = copy.deepcopy(p.profiles)
    data = p.to_dict()
    # Keep the proxy polygons and all source/revision fields unchanged. Only
    # the actual manufactured cut becomes a valid strip of twice the area.
    for command in data["parts"][pid]["paths"]["CUT"][0]["commands"]:
        for index in range(1, len(command), 2):
            command[index] *= 2
    loaded = AuthorProject.from_dict(data)
    status = loaded.loft_status(s)
    assert status["status"] == "UNRESOLVED" and status["code"] == "LOFT_FRAME_AREA_UNRESOLVED"
    assert loaded.parts[pid].polygons == p.parts[pid].polygons and loaded.profiles == original
    with pytest.raises(ValidationError, match="plošnou přesnost"):
        loaded.snapshot()
    loaded.recompute()
    assert loaded.loft_status(s)["status"] == "EXACT"
    assert loaded.snapshot()["coverage"]["expected_part_ids"] == [pid]


def test_numeric_intrinsic_certificate_must_bind_to_the_actual_source_mapping(monkeypatch):
    from archpapercraft.authoring import loft_area, loft_surface

    original = loft_area.certify_loft_intrinsic_area

    def wrong_binding(*args, **kwargs):
        report = original(*args, **kwargs)
        assert report["status"] == "CERTIFIED"
        report["coverage"]["correspondences"][0]["first_parameter_interval"] = [1, 0]
        return report

    monkeypatch.setattr(loft_area, "certify_loft_intrinsic_area", wrong_binding)
    loft_surface._analyze.cache_clear()
    loft_surface._bound_analysis.cache_clear()
    p, a, b = extrusion()
    s = p.add_loft(a, b, correspondences=refs(p, a, b))
    assert p.loft_status(s)["status"] == "UNRESOLVED"
    assert p.loft_status(s)["code"] == "LOFT_INTRINSIC_AREA_UNRESOLVED"
    with pytest.raises(ValidationError, match="zdrojovým vazbám"):
        p.snapshot()
