"""Actual contacting material, including holes, shares the connector registry."""

import json
from pathlib import Path

import pytest
from shapely import Polygon

from archpapercraft.authoring import AuthorProject, ValidationError


def test_actual_native_roof_band_and_soffit_overlap_is_blocked_without_rewriting_evidence():
    path = (Path(__file__).resolve().parents[2] / "docs/p2/implementation/evidence/"
            "pc006b-desktop-5b1161c-run03/model-A/model-A.apcraft")
    raw = path.read_bytes()
    project = AuthorProject.from_dict(json.loads(raw))
    contacts = []
    for attachment in project.attachments.values():
        if attachment.source_edge_id is None:
            data = project.attachment_geometry(attachment.id)
            assert data["valid"]
            loops = data["target_loops_uv"]
            contacts.append((attachment, Polygon(loops[0], loops[1:])))
    overlaps = [
        first.intersection(second).area * project.scale**2
        for index, (a, first) in enumerate(contacts)
        for b, second in contacts[index + 1:]
        if a.target_surface_id == b.target_surface_id and a.target_side == b.target_side
    ]
    assert max(overlaps) == pytest.approx(20)
    assert any(i.code == "FOLDED_CONNECTOR_COLLISION" for i in project.validate_layout())
    with pytest.raises(ValidationError):
        project.snapshot()
    assert path.read_bytes() == raw


@pytest.mark.parametrize("cross_ring", [False, True])
def test_glue_material_hole_remains_free_for_an_independent_patch(cross_ring):
    project = AuthorProject.new(scale=1)
    base = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    outer = [[20, 20], [60, 20], [60, 60], [20, 60]]
    hole = project.add_profile([[30, 30], [50, 30], [50, 50], [30, 50]])
    ring = project.add_surface(project.add_profile(outer), holes=[hole])
    project.set_glue_region(ring, base, outer)
    outline = ([[25, 35], [40, 35], [40, 45], [25, 45]] if cross_ring else
               [[35, 35], [45, 35], [45, 45], [35, 45]])
    other = project.add_surface(project.add_profile(outline))
    project.set_glue_region(other, base, outline)
    project.recompute()
    for index, part in enumerate(project.parts):
        page = project.pages[0].id if index == 0 else project.add_page()
        project.set_placement(part, page, 40, 50)
    issues = project.validate_layout()
    assert any(i.code == "FOLDED_CONNECTOR_COLLISION" for i in issues) is cross_ring
    for issue in issues:
        if issue.severity == "warning":
            project.acknowledge(issue.id)
    if cross_ring:
        with pytest.raises(ValidationError):
            project.snapshot()
    else:
        assert len(project.snapshot()["pages"]) == 3
