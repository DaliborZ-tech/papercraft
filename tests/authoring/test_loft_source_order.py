"""Source topology follows identity order independently of patch traversal."""

import copy
from fractions import Fraction

import pytest
from test_circular_shell import circle

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.loft_surface import _topology_profile


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("closed", [False, True])
def test_authored_source_order_survives_reverse_traversal_and_one_sided_split_merge(
    reverse, closed, tmp_path
):
    p = AuthorProject.new(scale=0.1)
    if closed:
        a, b = circle(p, 17, 0, quarters=True), circle(p, 7, -23, quarters=True)
    else:
        a = p.add_profile([[0, 0], [10, 0], [10, 10]], closed=False)
        b = p.copy_profile(a, plane=dict(origin=[0, 0, 10], u=[1, 0, 0], v=[0, 1, 0]))
    original = copy.deepcopy(p.profiles[a])
    pairs = list(zip(p.profiles[a].segments, p.profiles[b].segments))
    cut = p.split_profile_segment(a, pairs[0][0].id, Fraction(1, 3))
    if reverse:
        pairs.reverse()
    interval = [1, 0] if reverse else [0, 1]
    refs = [
        dict(
            first_segment_id=x.id,
            second_segment_id=y.id,
            first_interval=interval,
            second_interval=interval,
        )
        for x, y in pairs
    ]
    sid = p.add_loft(a, b, correspondences=refs)
    status = p.loft_status(sid)
    assert status["status"] == "EXACT"
    assert all(r["status"] == "VALID" for r in status["source_topology"].values())
    part = p.part_for_surface(sid)
    p.set_placement(part, p.pages[0].id, 67, 83, 30, position_locked=True, rotation_locked=True)
    paths, frame, layout = (
        copy.deepcopy(v) for v in (p.parts[part].paths, p.parts[part].frame, p.placements[part])
    )
    p.merge_profile_segments(a, cut["segment_ids"])
    p.recompute()
    assert p.parts[part].paths == paths
    assert p.parts[part].frame == frame and p.placements[part] == layout
    assert p.surfaces[sid].params["correspondences"] == status["patches"]
    assert original.vertices == p.profiles[a].vertices
    p.save(tmp_path / "ordered.apcraft")
    assert load_project(tmp_path / "ordered.apcraft").to_dict() == p.to_dict()


@pytest.mark.parametrize("closed", [False, True])
def test_true_source_crossing_is_rejected_atomically(closed):
    p = AuthorProject.new(scale=1)
    if closed:
        before = p.to_dict()
        with pytest.raises(ValidationError):
            p.add_profile([[0, 0], [10, 10], [0, 10], [10, 0]], closed=True)
        assert p.to_dict() == before
        return
    a = p.add_profile([[0, 0], [10, 10], [0, 10], [10, 0]], closed=closed)
    b = p.copy_profile(a, plane=dict(origin=[0, 0, 10], u=[1, 0, 0], v=[0, 1, 0]))
    assert _topology_profile(p.profiles[a])["status"] == "INVALID"
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_loft(
            a,
            b,
            correspondences=[
                dict(first_segment_id=x.id, second_segment_id=y.id)
                for x, y in zip(p.profiles[a].segments, p.profiles[b].segments)
            ],
        )
    assert p.to_dict() == before
