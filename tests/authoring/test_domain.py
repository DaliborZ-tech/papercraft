import copy

import pytest

from archpapercraft.authoring import AuthorProject, ValidationError


def rectangle(p, width=10000, height=4000):
    profile = p.add_profile(
        [[0, 0], [width, 0], [width, height], [0, height]], name="Vlastní stěna"
    )
    return profile, p.add_surface(profile, name="Vlastní plocha")


def test_empty_authoring_project_has_no_hidden_house_floor_or_parts():
    p = AuthorProject.new()
    assert not p.profiles and not p.surfaces and not p.parts and len(p.pages) == 1
    assert p.to_dict()["status"] == "experimental"
    with pytest.raises(ValidationError, match="žádný"):
        p.snapshot()


def test_move_vertex_preserves_source_and_material_identity_and_explicit_stale_cache():
    p = AuthorProject.new()
    profile_id, sid = rectangle(p)
    pid = p.part_for_surface(sid)
    before = copy.deepcopy(p.parts[pid])
    ids = [v.id for v in p.profiles[profile_id].vertices]
    segments = [e.id for e in p.profiles[profile_id].segments]
    p.move_vertex(profile_id, ids[2], [10000, 5000])
    assert p.part_for_surface(sid) == pid
    assert p.parts[pid].stale
    assert p.parts[pid].polygons == before.polygons
    assert [v.id for v in p.profiles[profile_id].vertices] == ids
    assert [e.id for e in p.profiles[profile_id].segments] == segments
    p.recompute()
    assert not p.parts[pid].stale
    assert p.parts[pid].polygons[sid][0][2] == [100, 50]


def test_replacement_uses_new_topology_and_requires_explicit_anchor_repair():
    p = AuthorProject.new()
    profile_id, sid = rectangle(p)
    pid = p.part_for_surface(sid)
    old_ids = {v.id for v in p.profiles[profile_id].vertices}
    p.update_profile(profile_id, [[0, 0], [10000, 0], [10000, 5000], [0, 5000]])
    assert old_ids.isdisjoint({v.id for v in p.profiles[profile_id].vertices})
    before = p.to_dict()
    with pytest.raises(ValidationError, match="ANCHOR_UNRESOLVED"):
        p.recompute()
    assert p.to_dict() == before
    p.set_anchor(pid, sid)
    assert not p.parts[pid].stale


def test_edit_that_moves_outer_boundary_over_hole_rejects_without_erasing_it():
    p = AuthorProject.new(scale=1)
    outer, sid = rectangle(p, 100, 80)
    hole = p.add_profile([[70, 20], [90, 20], [90, 40], [70, 40]])
    p.add_hole(sid, hole)
    p.recompute()
    before = p.to_dict()
    vertex_id = p.profiles[outer].vertices[1].id
    with pytest.raises(ValidationError):
        p.move_vertex(outer, vertex_id, [20, 0])
    assert p.to_dict() == before


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf"), True])
def test_bad_scale_is_transactional(scale):
    p = AuthorProject.new()
    rectangle(p)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_scale(scale)
    assert p.to_dict() == before


def test_open_profile_is_saved_but_cannot_be_filled_without_closing():
    p = AuthorProject.new()
    profile = p.add_profile([[0, 0], [100, 0], [100, 80]], closed=False)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="uzavřený"):
        p.add_surface(profile)
    assert p.to_dict() == before


@pytest.mark.parametrize(
    "kind,source",
    [
        ("arc", {"start": [10, 0], "end": [0, 10], "center": [0, 0], "sweep_deg": 90}),
        ("cubic", {"start": [0, 0], "end": [10, 0], "control1": [2, 4], "control2": [8, 4]}),
    ],
)
def test_analytic_curve_sources_roundtrip_without_pretending_material_support(kind, source):
    p = AuthorProject.new()
    pid = p.add_profile(segments=[{"kind": kind, **source}], closed=False)
    copy_p = AuthorProject.from_dict(p.to_dict())
    assert copy_p.to_dict() == p.to_dict()
    assert copy_p.profiles[pid].segments[0].kind == kind


def test_curved_region_has_native_material_but_curved_rigid_hinge_is_not_a_chord():
    p = AuthorProject.new()
    pid = p.add_profile(
        segments=[
            {"kind": "arc", "start": [10, 0], "end": [0, 10], "center": [0, 0], "sweep_deg": 90},
            {"kind": "line", "start": [0, 10], "end": [0, 0]},
            {"kind": "line", "start": [0, 0], "end": [10, 0]},
        ]
    )
    sid = p.add_surface(pid)
    assert any(c[0] == "A" for path in p.parts[p.part_for_surface(sid)].paths["CUT"]
               for c in path["commands"])
    from archpapercraft.authoring.attachments import edge_source

    before = p.to_dict()
    with pytest.raises(ValidationError, match="přímý ohyb"):
        edge_source(p, sid, p.profiles[pid].segments[0].id)
    assert p.to_dict() == before


def test_typed_unknown_source_reference_does_not_partially_create_a_surface():
    p = AuthorProject.new()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_surface("missing")
    assert p.to_dict() == before


def test_continue_then_close_open_source_preserves_all_existing_topology_ids():
    p = AuthorProject.new(scale=1)
    profile_id = p.add_profile([[0, 0], [100, 0]], closed=False)
    original_vertices = [v.id for v in p.profiles[profile_id].vertices]
    original_segments = [s.id for s in p.profiles[profile_id].segments]
    new_vertex = p.append_vertex(profile_id, [100, 80])
    assert [v.id for v in p.profiles[profile_id].vertices] == [*original_vertices, new_vertex]
    continued_segments = [s.id for s in p.profiles[profile_id].segments]
    assert continued_segments[:1] == original_segments
    revision = p.profiles[profile_id].revision
    p.close_profile(profile_id)
    profile = p.profiles[profile_id]
    assert profile.closed and profile.revision == revision + 1
    assert [v.id for v in profile.vertices] == [*original_vertices, new_vertex]
    assert [s.id for s in profile.segments][:-1] == continued_segments
    assert profile.segments[-1].start_vertex_id == new_vertex
    assert profile.segments[-1].end_vertex_id == original_vertices[0]
    no_op = p.to_dict()
    p.close_profile(profile_id)
    assert p.to_dict() == no_op
    with pytest.raises(ValidationError, match="již uzavřený"):
        p.append_vertex(profile_id, [0, 80])
    assert p.to_dict() == no_op


def test_open_profile_invalid_continuation_or_closure_is_transactional():
    p = AuthorProject.new()
    profile_id = p.add_profile([[0, 0], [100, 100]], closed=False)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="třetí"):
        p.close_profile(profile_id)
    assert p.to_dict() == before
    with pytest.raises(ValidationError):
        p.append_vertex(profile_id, [100, 100])
    assert p.to_dict() == before
    with pytest.raises(ValidationError):
        p.append_vertex(profile_id, [float("nan"), 100])
    assert p.to_dict() == before
    p.append_vertex(profile_id, [0, 100])
    p.append_vertex(profile_id, [100, 0])
    crossing = p.to_dict()
    with pytest.raises(ValidationError):
        p.close_profile(profile_id)
    assert p.to_dict() == crossing
    assert not p.profiles[profile_id].closed


def test_saved_open_profile_reopens_continues_closes_and_becomes_own_surface(tmp_path):
    p = AuthorProject.new(scale=0.01)
    profile_id = p.add_profile([[0, 0], [10000, 0]], closed=False, name="Moje rozpracovaná stěna")
    vertex_ids = [v.id for v in p.profiles[profile_id].vertices]
    edge_id = p.profiles[profile_id].segments[0].id
    path = tmp_path / "open-profile.apcraft"
    p.save(path)
    reopened = AuthorProject.load(path)
    assert reopened.to_dict() == p.to_dict()
    reopened.append_vertex(profile_id, [10000, 4000])
    reopened.append_vertex(profile_id, [0, 4000])
    reopened.close_profile(profile_id)
    sid = reopened.add_surface(profile_id)
    assert [v.id for v in reopened.profiles[profile_id].vertices][:2] == vertex_ids
    assert reopened.profiles[profile_id].segments[0].id == edge_id
    assert len(reopened.surfaces) == len(reopened.parts) == 1
    assert reopened.parts[reopened.part_for_surface(sid)].polygons[sid][0] == [
        [0, 0],
        [100, 0],
        [100, 40],
        [0, 40],
    ]
