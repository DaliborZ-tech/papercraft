import copy

import pytest

from archpapercraft.authoring import AuthorProject, UnsupportedOperationError, ValidationError


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


def test_curved_region_creation_is_explicitly_unsupported_in_first_cut():
    p = AuthorProject.new()
    pid = p.add_profile(
        segments=[
            {"kind": "arc", "start": [10, 0], "end": [0, 10], "center": [0, 0], "sweep_deg": 90},
            {"kind": "line", "start": [0, 10], "end": [0, 0]},
            {"kind": "line", "start": [0, 0], "end": [10, 0]},
        ]
    )
    before = p.to_dict()
    with pytest.raises(UnsupportedOperationError):
        p.add_surface(pid)
    assert p.to_dict() == before


def test_typed_unknown_source_reference_does_not_partially_create_a_surface():
    p = AuthorProject.new()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_surface("missing")
    assert p.to_dict() == before
