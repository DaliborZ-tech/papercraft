"""Independent reversal/seam oracle; source order is not correspondence order."""

import copy
import math
from fractions import Fraction as Q
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring import loft_surface as module

ROOT = Path(__file__).resolve().parents[4]
assert Path(module.__file__).resolve() == ROOT / "src/archpapercraft/authoring/loft_surface.py"


def quarters(p, radius, z):
    xy = [[radius, 0], [0, radius], [-radius, 0], [0, -radius], [radius, 0]]
    return p.add_profile(segments=[dict(kind="arc", start=a, end=b,
        data=dict(center=[0, 0], sweep_deg=90)) for a, b in zip(xy, xy[1:])], closed=True,
        plane=dict(origin=[0, 0, z], u=[1, 0, 0], v=[0, 1, 0]))


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("seam", [0, 1])
def test_quarters_keep_independent_cone_metrics_and_authored_identity_under_reverse_seam(
        reverse, seam, tmp_path):
    p = AuthorProject.new(scale=0.1)
    a, b = quarters(p, 13, 0), quarters(p, 5, -17)
    original_a, original_b = copy.deepcopy(p.profiles[a]), copy.deepcopy(p.profiles[b])
    pairs = list(zip(p.profiles[a].segments, p.profiles[b].segments))
    if reverse:
        pairs.reverse()
    pairs = pairs[seam:] + pairs[:seam]
    interval = [1, 0] if reverse else [0, 1]
    refs = [dict(first_segment_id=x.id, second_segment_id=y.id,
                 first_interval=interval[:], second_interval=interval[:]) for x, y in pairs]
    sid = p.add_loft(a, b, correspondences=refs)
    part = p.part_for_surface(sid)
    status = p.loft_status(sid)
    assert status["status"] == "EXACT"
    assert all(t["status"] == "VALID" for t in status["source_topology"].values())
    commands = p.parts[part].paths["CUT"][0]["commands"]
    arcs = [c for c in commands if c[0] == "A"]
    slant = math.sqrt(353)
    assert len(arcs) == 8
    radii = sorted({c[1] for c in arcs})
    assert radii == pytest.approx([5 * slant / 80, 13 * slant / 80], abs=1e-12)
    # Independent lateral frustum area: pi(r1+r2)*sqrt((r1-r2)^2+h^2).
    area = status["area"]["source_intrinsic"]
    target = math.pi * 18 * slant * 0.01
    assert float(Q(area["area_lower_exact"])) <= target <= float(Q(area["area_upper_exact"]))
    p.set_placement(part, p.pages[0].id, 61, 87, 31,
                    position_locked=True, rotation_locked=True)
    authored = copy.deepcopy(p.surfaces[sid].params)
    frame, paths, layout = map(copy.deepcopy, (p.parts[part].frame, p.parts[part].paths,
                                             p.placements[part]))
    root = original_a.segments[0].id
    cut = p.split_profile_segment(a, root, Q(2, 7))
    p.recompute()
    assert p.parts[part].paths == paths
    p.merge_profile_segments(a, cut["segment_ids"])
    p.recompute()
    assert p.parts[part].paths == paths and p.parts[part].frame == frame
    assert p.placements[part] == layout and p.surfaces[sid].params == authored
    assert p.profiles[a].vertices == original_a.vertices
    assert p.profiles[b] == original_b
    assert p.profiles[a].segments[0].id not in [root, *cut["segment_ids"]]
    saved = tmp_path / "reversed.apcraft"
    p.save(saved)
    q = load_project(saved)
    assert q.to_dict() == p.to_dict()
    assert q.loft_status(sid)["status"] == "EXACT"


def test_crossed_correspondence_cannot_be_repaired_by_source_sorting():
    p = AuthorProject.new(scale=0.1)
    a, b = quarters(p, 13, 0), quarters(p, 5, -17)
    pairs = list(zip(p.profiles[a].segments, p.profiles[b].segments))
    pairs[1], pairs[2] = pairs[2], pairs[1]
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_loft(a, b, correspondences=[dict(first_segment_id=x.id, second_segment_id=y.id)
                                         for x, y in pairs])
    assert p.to_dict() == before
