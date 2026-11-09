"""An exact straight cubic image needs no invented source-material uncertainty."""

import copy

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring.curve_material import surface_envelopes


def test_nonlinearly_parameterized_cubic_has_exact_line_material_and_keeps_source_identity():
    project = AuthorProject.new(scale=1)
    pid = project.add_profile(segments=[
        {"kind": "line", "start": [0, 0], "end": [10, 0]},
        {"kind": "line", "start": [10, 0], "end": [10, 20]},
        {"kind": "cubic", "start": [10, 20], "end": [0, 20],
         "data": {"control1": [9, 20], "control2": [8, 20]}},
        {"kind": "line", "start": [0, 20], "end": [0, 0]},
    ])
    sid = project.add_surface(pid)
    source = copy.deepcopy(project.to_dict())
    bounds = surface_envelopes(project, sid)
    assert bounds.is_exact and bounds.proxy.area == 200
    assert bounds.guaranteed.equals(bounds.proxy) and bounds.possible.equals(bounds.proxy)
    assert project.to_dict() == source
    assert project.profiles[pid].segments[2].kind == "cubic"
    part = project.parts[project.part_for_surface(sid)]
    assert any(command[0] == "C" for path in part.paths["CUT"]
               for command in path["commands"])


def test_tiny_real_cubic_bulge_is_not_classified_as_an_exact_straight_image():
    project = AuthorProject.new(scale=1)
    pid = project.add_profile(segments=[
        {"kind": "line", "start": [0, 0], "end": [10, 0]},
        {"kind": "line", "start": [10, 0], "end": [10, 20]},
        {"kind": "cubic", "start": [10, 20], "end": [0, 20],
         "data": {"control1": [9, 20+1e-10], "control2": [8, 20]}},
        {"kind": "line", "start": [0, 20], "end": [0, 0]},
    ])
    bounds = surface_envelopes(project, project.add_surface(pid))
    assert not bounds.is_exact
    assert not bounds.possible.equals(bounds.proxy)


def test_safe_fold_does_not_fail_conditioning_of_a_spurious_tube_around_a_straight_cubic():
    project = AuthorProject.new(scale=1)
    pid = project.add_profile([[20, 0], [60, 0], [60, 20], [20, 20]], plane={
        "origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1],
    })
    wall = project.add_surface(pid)
    base = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    profile = project.profiles[pid]
    aid = project.attach_edge_to_surface(wall, profile.segments[0].id, base,
                                         target_side="outside", glue_direction=-1)
    cid = project.set_attachment_tab(aid, width_mm=5, taper=1)
    project.set_material_profile(thickness_mm=0.2)
    project.set_profile_segment(profile.id, profile.segments[2].id, kind="cubic",
                                data={"control1": [50, 20], "control2": [30, 20]})
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "CLEAR", result
