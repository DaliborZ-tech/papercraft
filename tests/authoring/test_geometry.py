"""Analytic material-region oracles, not expectations from the renderer."""

import math

import numpy as np
import pytest
from shapely import Point, Polygon

from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.geometry import material_polygon, signed_area, triangulate


def test_concave_hole_tessellation_does_not_fill_the_notch_or_hole():
    outer = [[0, 0], [100, 0], [100, 80], [70, 80], [70, 30], [0, 30]]
    hole = [[80, 10], [90, 10], [90, 20], [80, 20]]
    vertices, faces = triangulate(outer, [hole])
    triangles = [Polygon(vertices[f]) for f in faces]
    assert sum(t.area for t in triangles) == pytest.approx(4400)
    assert all(not t.contains(Point(50, 50)) for t in triangles)
    assert all(not t.contains(Point(85, 15)) for t in triangles)
    assert all(Polygon(outer, [hole]).covers(t) for t in triangles)


def test_rectangle_with_hole_has_analytic_area_and_no_hole_triangles():
    outer = [[0, 0], [100, 0], [100, 80], [0, 80]]
    hole = [[20, 20], [40, 20], [40, 50], [20, 50]]
    vertices, faces = triangulate(outer, [hole])
    assert sum(Polygon(vertices[f]).area for f in faces) == pytest.approx(7400)
    assert len(faces) == 8


@pytest.mark.parametrize(
    "outer,holes",
    [
        ([[0, 0], [10, 10], [0, 10], [10, 0]], []),
        ([[0, 0], [10, 0], [10, 10], [0, 10]], [[[0, 2], [2, 2], [2, 4], [0, 4]]]),
        ([[0, 0], [10, 0], [10, 10], [0, 10]], [[[11, 2], [13, 2], [13, 4], [11, 4]]]),
        (
            [[0, 0], [10, 0], [10, 10], [0, 10]],
            [[[2, 2], [4, 2], [4, 4], [2, 4]], [[4, 2], [6, 2], [6, 4], [4, 4]]],
        ),
    ],
)
def test_invalid_material_topology_is_rejected_without_repair(outer, holes):
    with pytest.raises(ValidationError):
        material_polygon(outer, holes)


def test_arbitrary_plane_and_parent_rotation_preserve_intrinsic_metric():
    p = AuthorProject.new(scale=0.01)
    profile = p.add_profile([[0, 0], [10000, 0], [10000, 4000], [0, 4000]], plane="XZ")
    sid = p.add_surface(profile)
    pid = p.part_for_surface(sid)
    before = p.part_geometry(pid)["polygons"]
    parent = [[0, -1, 0, 1234], [1, 0, 0, 5678], [0, 0, 1, 42], [0, 0, 0, 1]]
    p.set_transform(sid, [100, 200, 300], [20, 30, 40], parent_transforms=[parent])
    edges = p.world_geometry(sid)["boundary"]
    assert [np.linalg.norm(np.array(e["end"]) - e["start"]) for e in edges] == pytest.approx(
        [10000, 4000, 10000, 4000]
    )
    p.recompute()
    assert p.part_geometry(pid)["polygons"] == before
    assert Polygon(before[sid][0]).area == pytest.approx(4000)


@pytest.mark.parametrize(
    "matrix",
    [
        [[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        [[1, 0.2, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        [[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    ],
)
def test_nonrigid_parent_is_rejected_transactionally(matrix):
    p = AuthorProject.new()
    sid = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 80], [0, 80]]))
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_transform(sid, parent_transforms=[matrix])
    assert p.to_dict() == before


def test_missing_physical_precision_in_huge_translation_is_rejected():
    p = AuthorProject.new()
    sid = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 80], [0, 80]]))
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_transform(sid, [1e20, 1e20, 1e20])
    assert p.to_dict() == before


def test_wrong_plane_hole_is_rejected_instead_of_projected_silently():
    p = AuthorProject.new()
    outer = p.add_profile([[0, 0], [100, 0], [100, 80], [0, 80]], plane="XZ")
    hole = p.add_profile([[20, 20], [40, 20], [40, 50], [20, 50]], plane="XY")
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_surface(outer, [hole])
    assert p.to_dict() == before


def test_rotated_normal_is_unit_and_not_a_required_closed_volume():
    p = AuthorProject.new()
    sid = p.add_surface(p.add_profile([[0, 0], [100, 0], [100, 80], [0, 80]], plane="XZ"))
    assert p.world_geometry(sid)["normal"] == [0, -1, 0]
    p.set_transform(sid, rotation_deg=[0, 0, 45])
    normal = p.world_geometry(sid)["normal"]
    assert normal == pytest.approx([math.sqrt(0.5), -math.sqrt(0.5), 0])


def test_large_finite_profile_origin_keeps_area_winding_and_triangle_normals():
    points = [[1e12, 1e12], [1e12 + 100, 1e12], [1e12 + 100, 1e12 + 80], [1e12, 1e12 + 80]]
    assert signed_area(points) == pytest.approx(8000)
    vertices, faces = triangulate(points)
    assert all(signed_area(vertices[face]) > 0 for face in faces)
    p = AuthorProject.new()
    sid = p.add_surface(p.add_profile(points))
    assert p.world_geometry(sid)["normal"] == [0, 0, 1]


def test_ill_conditioned_sketch_plane_origin_rejects_lost_source_metric():
    p = AuthorProject.new()
    profile = p.add_profile(
        [[0, 0], [100, 0], [100, 80], [0, 80]],
        plane={"origin": [1e20, 1e20, 1e20], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    before = p.to_dict()
    with pytest.raises(ValidationError, match="přesnost"):
        p.add_surface(profile)
    assert p.to_dict() == before


@pytest.mark.parametrize("pose", ["local", "parent", "plane"])
def test_world_area_guard_rejects_pose_with_small_edge_error_but_large_area_loss(pose):
    p = AuthorProject.new(scale=0.01)
    profile = p.add_profile([[0, 0], [10000.5, 0], [10000.5, 4000], [0, 4000]])
    if pose == "plane":
        p.profiles[profile].plane.origin = [1e16, 1e16, 0]
        before = p.to_dict()
        with pytest.raises(ValidationError, match="plošnou přesnost"):
            p.add_surface(profile)
    else:
        sid = p.add_surface(profile)
        before = p.to_dict()
        kwargs = (
            {"position_mm": [1e16, 1e16, 0]}
            if pose == "local"
            else {
                "parent_transforms": [
                    [[1, 0, 0, 1e16], [0, 1, 0, 1e16], [0, 0, 1, 0], [0, 0, 0, 1]]
                ]
            }
        )
        with pytest.raises(ValidationError, match="plošnou přesnost"):
            p.set_transform(sid, **kwargs)
    assert p.to_dict() == before
    # Independent rectangle oracle: 10000.5*4000*0.01² = 4000.2 paper mm².
    assert 10000.5 * 4000 * 0.01 * 0.01 == pytest.approx(4000.2)


def test_well_represented_large_world_translation_preserves_area_including_holes():
    p = AuthorProject.new(scale=0.01)
    outer = p.add_profile([[0, 0], [10000.5, 0], [10000.5, 4000], [0, 4000]])
    hole = p.add_profile([[1000, 1000], [1200, 1000], [1200, 1400], [1000, 1400]])
    sid = p.add_surface(outer, [hole])
    p.set_transform(sid, [1e12, 1e12, 1e12])
    geometry = p.world_geometry(sid)
    vertices = np.asarray(geometry["vertices"])
    measured = (
        sum(
            np.linalg.norm(
                np.cross(vertices[f[1]] - vertices[f[0]], vertices[f[2]] - vertices[f[0]])
            )
            / 2
            for f in geometry["triangles"]
        )
        * 0.01
        * 0.01
    )
    assert measured == pytest.approx(3992.2, abs=0.01)


def test_commit_validation_rejects_a_collapsed_hole_before_later_render_call():
    p = AuthorProject.new(scale=1)
    outer = p.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    hole = p.add_profile([[30, 30], [30.1, 30], [30.1, 30.2], [30, 30.2]])
    sid = p.add_surface(outer, [hole])
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_transform(sid, [1e16, 1e16, 0])
    assert p.to_dict() == before
    assert len(p.world_geometry(sid)["triangles"]) == 8
