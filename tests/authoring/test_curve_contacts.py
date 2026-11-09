"""Curved contact bounds and straight hinges use actual material, not chords."""

import copy
import math

import numpy as np
import pytest
from shapely import LineString, Polygon

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.attachments import source_outward, surface_material
from archpapercraft.authoring.curve_material import surface_envelopes


def circle_profile(project, radius=10):
    return project.add_profile(segments=[
        {"kind": "arc", "start": [radius, 0], "end": [-radius, 0],
         "data": {"center": [0, 0], "sweep_deg": 180}},
        {"kind": "arc", "start": [-radius, 0], "end": [radius, 0],
         "data": {"center": [0, 0], "sweep_deg": 180}},
    ])


def receiver_with_round_hole():
    project = AuthorProject.new(scale=1)
    outer = project.add_profile([[-20, -20], [20, -20], [20, 20], [-20, 20]])
    hole = circle_profile(project)
    receiver = project.add_surface(outer, holes=[hole])
    points = np.asarray(project.profile_projection(hole)["curves"][0]["points"])
    midpoint = (points[0]+points[1])/2
    normal = midpoint/np.linalg.norm(midpoint)
    sagitta = 10-np.linalg.norm(midpoint)
    tangent = np.array([-normal[1], normal[0]])
    return project, receiver, midpoint, normal, tangent, sagitta


def small_source(project, center, tangent, normal, *, length=0.001, depth=0.02):
    a, b = center-length/2*tangent, center+length/2*tangent
    points = [a.tolist(), b.tolist(), (b+depth*normal).tolist(), (a+depth*normal).tolist()]
    profile = project.add_profile(points)
    return project.add_surface(profile), project.profiles[profile].segments[0].id, points


def test_chord_proxy_fills_real_round_hole_sliver_but_trace_cannot_claim_material_contact():
    project, receiver, midpoint, normal, tangent, sagitta = receiver_with_round_hole()
    center = midpoint+sagitta/2*normal
    source, edge, points = small_source(project, center, tangent, normal)
    trace = LineString(points[:2])
    bounds = surface_envelopes(project, receiver)
    assert bounds.proxy.covers(trace)  # Concrete old false-positive receiver.
    assert all(math.hypot(*p) < 10 for p in points[:2])  # Independently inside the true hole.
    assert not surface_material(project, receiver).covers(trace)
    before = copy.deepcopy(project.to_dict())
    with pytest.raises(ValidationError, match="CURVE_CONTACT_UNRESOLVED"):
        project.attach_edge_to_surface(source, edge, receiver)
    assert project.to_dict() == before


def test_folded_tab_tip_in_round_hole_sliver_is_not_safe_because_proxy_covers_it():
    project, receiver, midpoint, normal, tangent, sagitta = receiver_with_round_hole()
    center = 10.02*normal
    source, edge, points = small_source(project, center, tangent, normal)
    attachment = project.attach_edge_to_surface(source, edge, receiver, glue_direction=1)
    width = 0.02+sagitta/2
    region = Polygon([points[0], points[1], (np.asarray(points[1])-width*normal).tolist(),
                      (np.asarray(points[0])-width*normal).tolist()])
    assert surface_envelopes(project, receiver).proxy.covers(region)
    assert math.hypot(*(center-width*normal)) < 10
    before = copy.deepcopy(project.to_dict())
    with pytest.raises(ValidationError, match="CURVE_CONTACT_UNRESOLVED"):
        project.set_attachment_tab(attachment, width_mm=width, taper=1)
    assert project.to_dict() == before


def test_glue_area_in_curved_hole_uncertainty_is_not_certified_from_proxy_area():
    project, receiver, midpoint, normal, tangent, sagitta = receiver_with_round_hole()
    center = midpoint+sagitta/2*normal
    source, _, points = small_source(project, center, tangent, normal, depth=sagitta/4)
    assert surface_envelopes(project, receiver).proxy.covers(Polygon(points))
    with pytest.raises(ValidationError, match="CURVE_CONTACT_UNRESOLVED"):
        project.set_glue_region(source, receiver, points)


def test_known_trace_in_hole_remains_definitely_outside_despite_curved_uncertainty_elsewhere():
    project, receiver, _, _, _, _ = receiver_with_round_hole()
    source, edge, _ = small_source(project, np.array([0., 0.]), np.array([1., 0.]),
                                   np.array([0., 1.]), length=1, depth=1)
    with pytest.raises(ValidationError, match="TRACE_OUTSIDE_MATERIAL"):
        project.attach_edge_to_surface(source, edge, receiver)


def test_clear_margin_trace_and_explicit_glue_area_are_supported_on_curved_receiver():
    project, receiver, _, _, _, _ = receiver_with_round_hole()
    source, edge, points = small_source(project, np.array([15., 0.]), np.array([0., 1.]),
                                        np.array([1., 0.]), length=1, depth=1)
    aid = project.attach_edge_to_surface(source, edge, receiver)
    assert project.attachment_geometry(aid)["valid"]
    gid = project.set_glue_region(source, receiver, points)
    geometry = project.attachment_geometry(gid)
    assert geometry["valid"] and geometry["available_area_mm2"] == pytest.approx(1)


def upper_semidisk(project):
    return project.add_profile(segments=[
        {"kind": "arc", "start": [-10, 0], "end": [10, 0],
         "data": {"center": [0, 0], "sweep_deg": -180}},
        {"kind": "line", "start": [10, 0], "end": [-10, 0]},
    ])


def test_curved_profile_with_zero_endpoint_polygon_area_has_proven_correct_hinge_outward():
    project = AuthorProject.new(scale=1)
    profile = upper_semidisk(project)
    source = project.add_surface(profile)
    edge = project.profiles[profile].segments[1].id
    tangent, outward = source_outward(project, source, edge)
    assert tangent == pytest.approx([-1, 0])
    assert outward == pytest.approx([0, -1])  # Actual material is above the diameter.


def test_straight_diameter_of_curved_hole_points_out_of_material_into_the_hole():
    project = AuthorProject.new(scale=1)
    outer = project.add_profile([[-20, -20], [20, -20], [20, 20], [-20, 20]])
    hole = upper_semidisk(project)
    source = project.add_surface(outer, holes=[hole])
    edge = project.profiles[hole].segments[1].id
    _, outward = source_outward(project, source, edge)
    assert outward == pytest.approx([0, 1])


@pytest.mark.parametrize("angle", [37, 73])
def test_curved_straight_hinge_orientation_survives_rotation_and_translation(angle):
    project = AuthorProject.new(scale=1)
    origin = np.array([1234.5, 678.9])
    u = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
    a, b = origin-10*u, origin+10*u
    profile = project.add_profile(segments=[
        {"kind": "arc", "start": a.tolist(), "end": b.tolist(),
         "data": {"center": origin.tolist(), "sweep_deg": -180}},
        {"kind": "line", "start": b.tolist(), "end": a.tolist()},
    ])
    surface = project.add_surface(profile)
    _, outward = source_outward(project, surface, project.profiles[profile].segments[1].id)
    assert outward == pytest.approx([u[1], -u[0]])


def test_whole_curved_source_is_not_silently_shrunk_but_explicit_interior_area_is_supported():
    project = AuthorProject.new(scale=1)
    source = project.add_surface(circle_profile(project))
    target = project.add_surface(project.add_profile([[-20, -20], [20, -20], [20, 20], [-20, 20]]))
    with pytest.raises(ValidationError, match="CURVE_SOURCE_REGION_UNRESOLVED"):
        project.set_glue_region(source, target, [[-15, -15], [15, -15], [15, 15], [-15, 15]])
    rectangle = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
    aid = project.set_glue_region(source, target, rectangle, source_outline_uv=rectangle)
    assert project.attachment_geometry(aid)["available_area_mm2"] == pytest.approx(4)


def test_definite_bad_receiver_is_not_weakened_by_implicit_curved_source_uncertainty():
    project = AuthorProject.new(scale=1)
    source = project.add_surface(circle_profile(project))
    target = project.add_surface(project.add_profile([[20, 20], [30, 20], [30, 30], [20, 30]]))
    with pytest.raises(ValidationError, match="TARGET_GLUE_OUTSIDE"):
        project.set_glue_region(source, target, [[0, 0], [1, 0], [1, 1], [0, 1]])


def test_definite_source_gap_is_not_weakened_by_curved_receiver_uncertainty():
    project, receiver, midpoint, normal, tangent, sagitta = receiver_with_round_hole()
    source, _, points = small_source(project, midpoint+sagitta/2*normal, tangent, normal,
                                     depth=sagitta/4)
    project.set_transform(source, [0, 0, 1])
    with pytest.raises(ValidationError, match="ATTACHMENT_GAP"):
        project.set_glue_region(source, receiver, points)
