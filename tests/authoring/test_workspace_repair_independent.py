"""Independent UI repair expectations, never native or human usability proof."""

import json
import math
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_viewport import AuthorViewport
from archpapercraft.ui.author_window import AuthorMainWindow


@pytest.mark.parametrize("raw", ["South wall", "  South wall  "])
def test_inline_name_preserves_validated_text_and_second_rename(qtbot, tmp_path, raw):
    host = AuthorMainWindow(settings=QSettings(str(tmp_path / "own.ini"), QSettings.IniFormat))
    qtbot.addWidget(host)
    host._confirm_replace = lambda: True
    host.show()

    def prepare(project):
        profile = project.add_profile([[0, 0], [6000, 0], [6000, 4000], [0, 4000]])
        return project.add_surface(profile)

    sid = host.controller.execute("Independent rectangle", prepare)
    host.select_surface(sid)
    pid = host.project.surfaces[sid].part_id
    host.selection_name.setFocus()
    host.selection_name.selectAll()
    qtbot.keyClicks(host.selection_name, raw)
    qtbot.keyClick(host.selection_name, Qt.Key_Return)
    assert host.project.surfaces[sid].name == raw
    assert host.project.parts[pid].name == f"P1 · {raw}"
    host.selection_name.setFocus()
    host.selection_name.selectAll()
    qtbot.keyClicks(host.selection_name, "North wall")
    qtbot.keyClick(host.selection_name, Qt.Key_Return)
    assert host.project.parts[pid].name == "P1 · North wall"


@pytest.mark.parametrize("size", [(838, 444), (400, 220), (220, 600)])
@pytest.mark.parametrize("orbit", [(30, 55), (-120, 15), (80, -70)])
def test_actual_native_model_fit_all_is_inside_with_centered_screen_bounds(qtbot, size, orbit):
    path = (
        Path(__file__).resolve().parents[2]
        / "docs/p2/implementation/evidence/workspace-recovery-native/own-four-part-model.apcraft"
    )
    data = json.loads(path.read_text(encoding="utf8"))
    project = AuthorProject.from_dict(data)
    view = AuthorViewport()
    qtbot.addWidget(view)
    view.resize(*size)
    view.yaw, view.pitch = orbit
    view.set_project(project)
    view.focus_selection(all_surfaces=True)
    yaw, pitch = map(math.radians, orbit)
    points = [p for m in view.meshes.values() for p in m["vertices"]]
    points += [p for path in view.profile_paths.values() for p in path]
    projected = []
    for point in points:
        x, y, z = [point[i] - view.center[i] for i in range(3)]
        horizontal = math.cos(yaw) * x - math.sin(yaw) * y
        vertical = math.cos(pitch) * (math.sin(yaw) * x + math.cos(yaw) * y) + math.sin(pitch) * z
        projected.append(
            (
                size[0] / 2 + horizontal * size[1] / (2 * view.span),
                size[1] / 2 - vertical * size[1] / (2 * view.span),
            )
        )
    for axis in (0, 1):
        low, high = min(p[axis] for p in projected), max(p[axis] for p in projected)
        assert 0 <= low <= high <= size[axis]
        assert (low + high) / 2 == pytest.approx(size[axis] / 2, abs=1e-8)
    assert project.to_dict() == data
