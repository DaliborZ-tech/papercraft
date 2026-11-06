"""Regression from real Windows band creation; no replacement for the UI rerun."""

import copy
import json
import math
from pathlib import Path

import pytest
from shapely import Polygon

from archpapercraft.authoring import AuthorProject, ValidationError


def actual_failed_ui_state():
    source = (Path(__file__).resolve().parents[2] / "docs/p2/implementation/evidence/"
              "pc006b-desktop-d83429c-run02/FAIL-partial-observed-state.json")
    project = AuthorProject.from_dict(json.loads(source.read_text(encoding="utf8")))
    aid = max(project.attachments.values(), key=lambda a: a.number).id
    return project, aid


def test_actual_rounded_ui_roof_accepts_band_without_trimming_source_material():
    project, aid = actual_failed_ui_state()
    receiver = project.attachments[aid].target_surface_id
    source_profile = project.profiles[project.surfaces[receiver].profile_id]
    roof_points = copy.deepcopy(source_profile.points)
    contact = project.attachment_geometry(aid)
    assert contact["target_uv"][0][1] == pytest.approx(4949.747468305833, abs=1e-9)
    assert max(point[1] for point in roof_points) == 4949.747468
    band = project.add_glue_band(aid, width_mm=2)
    # Two2mm flanges along the independently known diagonal sqrt(30²+30²).
    area = sum(Polygon(loops[0]).area for loops in project.parts[band].polygons.values())
    assert area == pytest.approx(4 * math.hypot(30, 30), abs=1e-7)
    assert source_profile.points == roof_points
    band_surfaces = set(project.parts[band].surface_ids)
    receivers = [a for a in project.attachments.values() if a.source_surface_id in band_surfaces]
    assert len(receivers) == 2
    for attachment in receivers:
        result = project.attachment_geometry(attachment.id)
        assert result["valid"] and result["contact_tolerance_model_mm"] * project.scale <= 0.01
        assert result["available_area_mm2"] == pytest.approx(2 * math.hypot(30, 30), abs=1e-7)


def test_real_overflow_stays_rejected_after_subnanometre_rounding_fix():
    project, aid = actual_failed_ui_state()
    receiver = project.attachments[aid].target_surface_id
    profile = project.profiles[project.surfaces[receiver].profile_id]
    for vertex in profile.vertices:
        if vertex.point[1] == 4949.747468:
            project.move_vertex(profile.id, vertex.id, [vertex.point[0], 4949.647468])
    before = project.to_dict()
    with pytest.raises(ValidationError, match="OUTSIDE"):
        project.add_glue_band(aid, width_mm=2)
    assert project.to_dict() == before


def test_model_space_floor_cannot_exceed_the_digital_paper_contact_budget():
    project = AuthorProject.new(scale=1e6)
    source_profile = project.add_profile([[0, 0], [1, 0], [1, 1], [0, 1]])
    source = project.add_surface(source_profile)
    target = project.add_surface(project.add_profile([[-1, -1], [2, -1], [2, 2], [-1, 2]]))
    project.set_transform(source, [0, 0, 2e-8])  #0.02paper mm, despite tiny model-space gap.
    before = project.to_dict()
    with pytest.raises(ValidationError, match="GAP"):
        project.attach_edge_to_surface(
            source, project.profiles[source_profile].segments[0].id, target
        )
    assert project.to_dict() == before
