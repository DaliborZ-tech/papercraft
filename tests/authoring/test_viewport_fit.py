"""Independent orthographic projection of asymmetrical authored material."""

import math

import numpy as np
import pytest

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_viewport import AuthorViewport


def asymmetric_project():
    project = AuthorProject.new()
    surfaces = []
    for width, height, plane, position in (
        (10000, 7000, "XY", [0, 0, 0]),
        (6000, 4000, "XZ", [2000, 2000, 0]),
        (2000, 1500, "XZ", [0, 0, 0]),
        (2000, 3000, "XZ", [-700, -1300, 200]),
    ):
        profile = project.add_profile([[0, 0], [width, 0], [width, height], [0, height]],
                                      plane=plane)
        surface = project.add_surface(profile)
        project.set_transform(surface, position, [0, 0, 0])
        surfaces.append(surface)
    return project, surfaces


def independent_pixels(viewport, points):
    """Scalar yaw then negative-pitch rotation, without camera/project_points."""
    yaw, pitch = math.radians(viewport.yaw), math.radians(viewport.pitch)
    result = []
    aspect = viewport.width() / viewport.height()
    for point in points:
        dx, dy, dz = [point[i] - viewport.center[i] for i in range(3)]
        x = math.cos(yaw)*dx - math.sin(yaw)*dy
        y0 = math.sin(yaw)*dx + math.cos(yaw)*dy
        y = math.cos(pitch)*y0 + math.sin(pitch)*dz
        result.append([viewport.width()/2 * (1 + (x + viewport.pan[0]) / (viewport.span*aspect)),
                       viewport.height()/2 * (1 - (y + viewport.pan[1]) / viewport.span)])
    return np.asarray(result)


def assert_centered_and_visible(viewport, points):
    pixels = independent_pixels(viewport, points)
    low, high = pixels.min(axis=0), pixels.max(axis=0)
    assert np.all(low >= -1e-8)
    assert high[0] <= viewport.width() + 1e-8
    assert high[1] <= viewport.height() + 1e-8
    np.testing.assert_allclose((low + high)/2, [viewport.width()/2, viewport.height()/2],
                               atol=1e-8, rtol=0)


@pytest.mark.parametrize("size", [(838, 444), (300, 700), (1400, 250)])
@pytest.mark.parametrize("yaw,pitch", [(30, 55), (-75, 80), (145, -20), (0, 90), (180, 0)])
def test_fit_all_centers_actual_rotated_material_for_aspect_and_orbit(qtbot, size, yaw, pitch):
    project, _ = asymmetric_project()
    before = project.to_dict()
    viewport = AuthorViewport()
    qtbot.addWidget(viewport)
    viewport.resize(*size)
    viewport.yaw, viewport.pitch = yaw, pitch
    viewport.pan[:] = [17, -23]
    viewport.set_project(project)
    viewport.focus_selection(all_surfaces=True)
    points = [point for mesh in viewport.meshes.values() for point in mesh["vertices"]]
    assert_centered_and_visible(viewport, points)
    assert project.to_dict() == before


def test_fit_selection_keeps_the_selected_material_scope_and_profile_scope(qtbot):
    project, surfaces = asymmetric_project()
    profile = project.add_profile([[0, 0], [200, 100]], closed=False,
                                  plane={"origin": [1e6, -2e6, 3e6],
                                         "u": [1, 0, 0], "v": [0, 1, 0]})
    viewport = AuthorViewport()
    qtbot.addWidget(viewport)
    viewport.resize(838, 444)
    viewport.set_project(project)
    viewport.select(surfaces[:2])
    viewport.focus_selection()
    selected = [point for sid in surfaces[:2] for point in viewport.meshes[sid]["vertices"]]
    assert_centered_and_visible(viewport, selected)
    distant = independent_pixels(viewport, viewport.profile_paths[profile])
    assert np.any(distant[:, 0] > viewport.width()) or np.any(distant[:, 1] < 0)
    viewport.select_profile(profile)
    viewport.focus_selection()
    assert_centered_and_visible(viewport, viewport.profile_paths[profile])
