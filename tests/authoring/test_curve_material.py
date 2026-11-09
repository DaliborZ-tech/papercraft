"""Analytic material witnesses must be bounded independently of chord proxies."""

import copy
import math

import pytest
from shapely import Point
from shapely.affinity import translate

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.curve_material import (
    _tube,
    part_envelopes,
    surface_envelopes,
)


def bulged_box(project, bulge=0.0015):
    profile = project.add_profile(segments=[
        {"kind": "line", "start": [0, 0], "end": [10, 0]},
        {"kind": "cubic", "start": [10, 0], "end": [10, 10],
         "data": {"control1": [10 + bulge, 3], "control2": [10 + bulge, 7]}},
        {"kind": "line", "start": [10, 10], "end": [0, 10]},
        {"kind": "line", "start": [0, 10], "end": [0, 0]},
    ])
    return project.add_surface(profile)


def circle(project, radius=2, center=(7, 7)):
    x, y = center
    return project.add_profile(segments=[
        {"kind": "arc", "start": [x + radius, y], "end": [x - radius, y],
         "data": {"center": [x, y], "sweep_deg": 180}},
        {"kind": "arc", "start": [x - radius, y], "end": [x + radius, y],
         "data": {"center": [x, y], "sweep_deg": 180}},
    ])


def test_p02_true_cubic_bulge_is_not_discarded_when_chord_proxy_is_a_rectangle():
    project = AuthorProject.new(scale=1)
    sid = bulged_box(project)
    bounds = surface_envelopes(project, sid)
    # Independent cubic midpoint: .125*10 + .375*10.0015*2 + .125*10.
    witness = Point(10 + 0.75 * 0.0015, 5)
    assert bounds.proxy.bounds == (0, 0, 10, 10)
    assert not bounds.proxy.covers(witness)
    assert bounds.possible.covers(witness)
    assert not bounds.guaranteed.covers(witness)
    assert bounds.guaranteed.covers(Point(9, 5))
    assert bounds.max_error >= 0.0015
    assert "not a proven collision" in bounds.proof


def test_p02_possible_layout_overlap_is_uncertain_and_must_not_be_declared_clear():
    project = AuthorProject.new(scale=1)
    sid = bulged_box(project)
    other = project.add_surface(project.add_profile([[0, 0], [2, 0], [2, 10], [0, 10]]))
    first = part_envelopes(project, project.parts[project.part_for_surface(sid)])
    second = part_envelopes(project, project.parts[project.part_for_surface(other)])
    original = translate(first.proxy, 40, 40)
    neighbor = translate(second.possible, 50.0005, 40)
    assert original.intersection(neighbor).is_empty
    assert translate(first.possible, 40, 40).intersection(neighbor).area > 0
    assert translate(first.guaranteed, 40, 40).intersection(neighbor).is_empty
    assert neighbor.covers(Point(50.001, 45))
    assert translate(first.possible, 40, 40).covers(Point(50.001, 45))


def test_curve_hole_uncertainty_removes_false_material_but_keeps_true_void():
    project = AuthorProject.new(scale=1)
    outer = project.add_profile([[0, 0], [20, 0], [20, 20], [0, 20]])
    hole = circle(project)
    sid = project.add_surface(outer, [hole])
    bounds = surface_envelopes(project, sid)
    certificate = project.profile_projection(hole)["curves"][0]
    theta = math.pi * certificate["parameters"][1] / 2
    radial = (2 + 2 * math.cos(theta)) / 2
    # This is inside the true radius-two hole, but outside its inscribed chord.
    witness = Point(7 + radial * math.cos(theta), 7 + radial * math.sin(theta))
    assert witness.distance(Point(7, 7)) < 2
    assert bounds.proxy.covers(witness)
    assert not bounds.guaranteed.covers(witness)
    assert bounds.possible.covers(witness)
    assert not bounds.guaranteed.covers(Point(7, 7))
    assert not bounds.possible.covers(Point(7, 7))
    assert len(bounds.possible.interiors) == len(bounds.guaranteed.interiors) == 1


def test_exact_receiving_line_far_from_curves_keeps_its_boundary_and_material():
    project = AuthorProject.new(scale=1)
    sid = bulged_box(project)
    bounds = surface_envelopes(project, sid)
    assert bounds.guaranteed.covers(Point(4, 0))
    assert not bounds.possible.covers(Point(4, -1e-8))
    assert bounds.guaranteed.covers(Point(0, 4))
    assert not bounds.possible.covers(Point(-1e-8, 4))


@pytest.mark.parametrize("scale,paper", [(1, False), (0.01, False), (0.01, True)])
def test_all_line_material_has_no_artificial_tolerance_reservation(scale, paper):
    project = AuthorProject.new(scale=scale)
    outer = project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    hole = project.add_profile([[20, 20], [30, 20], [30, 30], [20, 30]])
    sid = project.add_surface(outer, [hole])
    bounds = surface_envelopes(project, sid, paper=paper)
    assert bounds.proxy is bounds.guaranteed is bounds.possible
    assert bounds.is_exact and bounds.max_error == 0
    assert bounds.uncertainty_band.is_empty
    factor = scale if paper else 1
    assert bounds.possible.area == pytest.approx((10000 - 100) * factor * factor)


@pytest.mark.parametrize("angle", [0, 0.23, 1.1, 2.7])
def test_square_caps_contain_the_entire_euclidean_chord_neighborhood(angle):
    delta = 0.002
    start = (13.0, -7.0)
    end = (start[0] + 11 * math.cos(angle), start[1] + 11 * math.sin(angle))
    tube = _tube(start, end, delta)
    for center in (start, end, ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)):
        for index in range(97):
            theta = math.tau * index / 97
            point = Point(center[0] + delta * math.cos(theta),
                          center[1] + delta * math.sin(theta))
            assert tube.covers(point)


def test_circle_true_boundary_is_in_possible_and_guaranteed_points_are_inside_true_disk():
    project = AuthorProject.new(scale=1)
    sid = project.add_surface(circle(project, 20, (0, 0)))
    bounds = surface_envelopes(project, sid)
    assert bounds.guaranteed.covers(Point(0, 0))
    for i in range(103):
        theta = math.tau * i / 103
        assert bounds.possible.covers(Point(20 * math.cos(theta), 20 * math.sin(theta)))
        for radius in (19.997, 19.999, 20, 20.001, 20.003):
            point = Point(radius * math.cos(theta), radius * math.sin(theta))
            if bounds.guaranteed.covers(point):
                assert radius <= 20
    assert not bounds.possible.covers(Point(25, 0))


def test_curved_part_envelope_keeps_exact_straight_tab_material():
    project = AuthorProject.new(scale=1)
    profile = project.add_profile(segments=[
        {"kind": "line", "start": [0, 0], "end": [20, 0]},
        {"kind": "arc", "start": [20, 0], "end": [0, 0],
         "data": {"center": [10, 0], "sweep_deg": 180}},
    ])
    arch = project.add_surface(profile)
    receiver_profile = project.add_profile([[0, -10], [20, -10], [20, 0], [0, 0]])
    receiver = project.add_surface(receiver_profile)
    joint = project.connect_edges(arch, project.profiles[profile].segments[0].id,
                                   receiver, project.profiles[receiver_profile].segments[2].id)
    project.set_tab(joint, owner=arch, width_mm=2, taper=1)
    part = project.parts[project.part_for_surface(arch)]
    bounds = part_envelopes(project, part)
    assert bounds.proxy.covers(Point(10, -1))
    assert bounds.guaranteed.covers(Point(10, -1))
    assert bounds.possible.covers(Point(10, 10))
    assert not bounds.possible.covers(Point(10, -3))
    assert bounds.source_segment_ids == (project.profiles[profile].segments[1].id,)


def test_paper_scaling_and_curve_frame_preserve_boundary_coverage():
    project = AuthorProject.new(scale=0.01)
    profile = circle(project, 2000, (0, 0))
    sid = project.add_surface(profile)
    surface = surface_envelopes(project, sid, paper=True)
    part = part_envelopes(project, project.parts[project.part_for_surface(sid)])
    # The first diameter is the authored frame axis, reversing X about x=2000.
    for theta in (0.13, 0.7, 1.89, 3.31, 5.9):
        x, y = 20 * math.cos(theta), 20 * math.sin(theta)
        assert surface.possible.covers(Point(x, y))
        assert part.possible.covers(Point(20 - x, -y))
    assert surface.max_error < 0.003 and part.max_error < 0.003


def test_actual_source_geometry_and_cache_chords_invalidate_envelopes_without_global_revision():
    project = AuthorProject.new(scale=1)
    sid = bulged_box(project)
    original = surface_envelopes(project, sid)
    before = original.possible.wkb
    source = project.profiles[project.surfaces[sid].profile_id]
    # Deliberately no revision bump: the key must inspect actual source values.
    source.segments[1].data["control1"][0] = 10.1
    source.segments[1].data["control2"][0] = 10.1
    updated = surface_envelopes(project, sid)
    assert updated.possible.covers(Point(10.075, 5))
    assert not original.possible.covers(Point(10.075, 5))
    assert original.possible.wkb == before
    assert updated.source_segment_ids == original.source_segment_ids


def test_missing_curve_chord_and_stale_part_do_not_silently_claim_coverage():
    project = AuthorProject.new(scale=1)
    sid = bulged_box(project)
    part = project.parts[project.part_for_surface(sid)]
    changed = copy.deepcopy(part)
    curved = project.profiles[project.surfaces[sid].profile_id].segments[1].id
    changed.edges = [edge for edge in changed.edges if edge["edge_id"] != curved]
    with pytest.raises(ValidationError, match="nepokrývá"):
        part_envelopes(project, changed)
    changed = copy.deepcopy(part)
    changed.stale = True
    with pytest.raises(ValidationError, match="neaktuální"):
        part_envelopes(project, changed)


def test_reordered_reversed_curve_chords_are_supported_but_same_count_duplicates_are_rejected():
    project = AuthorProject.new(scale=1)
    sid = project.add_surface(circle(project, 20, (0, 0)))
    part = project.parts[project.part_for_surface(sid)]
    before = part_envelopes(project, part)
    reordered = copy.deepcopy(part)
    reordered.edges.reverse()
    for edge in reordered.edges:
        edge["start"], edge["end"] = edge["end"], edge["start"]
    after = part_envelopes(project, reordered)
    assert before.possible.equals(after.possible)
    assert before.guaranteed.equals(after.guaranteed)
    repeated = copy.deepcopy(part)
    repeated.edges[1] = copy.deepcopy(repeated.edges[0])
    with pytest.raises(ValidationError, match="opakovanou"):
        part_envelopes(project, repeated)
