"""Assembly-space conflicts must include every connector kind, independent of layout."""

import pytest
from shapely import Polygon

from archpapercraft.authoring import AuthorProject, ProjectFormatError, ValidationError


def mixed_connectors():
    project = AuthorProject.new(scale=1)
    receiver_profile = project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    receiver = project.add_surface(receiver_profile)
    wall_profile = project.add_profile([[0, 0], [100, 0], [100, 20], [0, 20]], plane="XZ")
    wall = project.add_surface(wall_profile)
    joint = project.connect_edges(
        receiver, project.profiles[receiver_profile].segments[0].id,
        wall, project.profiles[wall_profile].segments[0].id,
    )
    project.set_tab(joint, owner=wall, width_mm=7, taper=1)
    cid = project.joints[joint].connector_id
    other_profile = project.add_profile(
        [[20, 0], [60, 0], [60, 20], [20, 20]], plane="XZ"
    )
    other = project.add_surface(other_profile)
    attachment = project.attach_edge_to_surface(
        other, project.profiles[other_profile].segments[0].id, receiver, target_side="inside"
    )
    other_cid = project.set_attachment_tab(attachment, width_mm=5, taper=1)
    for index, part in enumerate(project.parts):
        page = project.pages[0].id if index == 0 else project.add_page()
        project.set_placement(part, page, 40, 50)
    return project, cid, other_cid, joint, receiver


def test_unknown_side_does_not_silently_miss_two_hundred_square_mm_overlap():
    project, cid, other_cid, *_ = mixed_connectors()
    a = project.connector_geometry(cid)["tabs"][0]["footprint_uv_mm"]
    b = project.connector_geometry(other_cid)["tabs"][0]["footprint_uv_mm"]
    # Independent rectangles 100×7 and40×5 intersect on[20,60]×[0,5].
    assert Polygon(a).intersection(Polygon(b)).area == pytest.approx(200)
    issues = project.validate_layout()
    unresolved = [issue for issue in issues if issue.code == "FOLDED_SIDE_UNRESOLVED"]
    assert len(unresolved) == 1 and unresolved[0].severity == "error"
    with pytest.raises(ValidationError):
        project.acknowledge(unresolved[0].id)
    for issue in issues:
        if issue.severity == "warning":
            project.acknowledge(issue.id)
    with pytest.raises(ValidationError):
        project.snapshot()


def test_explicit_side_changes_collision_and_owner_change_drops_previous_side():
    project, cid, _, joint, receiver = mixed_connectors()
    project.set_connector(cid, receiver_side="inside")
    assert any(i.code == "FOLDED_CONNECTOR_COLLISION" for i in project.validate_layout())
    project.set_connector(cid, receiver_side="outside")
    assert not any(i.code.startswith("FOLDED_") for i in project.validate_layout())
    restored = AuthorProject.from_dict(project.to_dict())
    assert restored.connectors[cid].receiver_side == "outside"
    # Changing the owner changes its receiver: no inherited author choice for another face.
    project.set_tab(joint, owner=receiver)
    assert project.connectors[cid].receiver_side == "unknown"


def test_disabling_conflicting_tab_resolves_collision_without_deleting_identity():
    project, cid, *_ = mixed_connectors()
    project.set_connector(cid, receiver_side="inside")
    ids = list(project.connectors[cid].tab_ids)
    project.set_connector(cid, enabled=False)
    assert not any(i.code.startswith("FOLDED_") for i in project.validate_layout())
    assert project.connectors[cid].tab_ids == ids
    project.set_connector(cid, enabled=True)
    assert any(i.code == "FOLDED_CONNECTOR_COLLISION" for i in project.validate_layout())


def test_invalid_side_and_missing_draft_schema_field_cannot_get_default_approval():
    project, cid, *_ = mixed_connectors()
    with pytest.raises(ValidationError):
        project.set_connector(cid, receiver_side="back-ish")
    data = project.to_dict()
    del data["connectors"][cid]["receiver_side"]
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(data)
