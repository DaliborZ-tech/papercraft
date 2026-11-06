"""Actual authoring widgets and input; these are not novice-user observations."""

from copy import deepcopy

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QMessageBox,
)

from archpapercraft.ui.author_sketch import VertexHandle
from archpapercraft.ui.author_window import AuthorMainWindow

pytestmark = pytest.mark.ui


def test_empty_paper_click_clears_linked_selection_and_contextual_actions(window, qtbot):
    arrange_rectangle(window)
    assert window.actions["hole"].isEnabled()
    # Empty physical page, away from the tray part and calibration footer.
    page_origin = window.paper.page_origins[window.project.pages[0].id]
    point = window.paper.mapFromScene(page_origin + QPointF(80, 80))
    qtbot.mouseClick(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert window.selected_surface is None and window.selected_part is None
    assert not window.viewport.selected_surfaces
    assert window.paper.selected_part is None
    assert not window.tree.selectedItems()
    assert not window.actions["hole"].isEnabled()
    assert not window.sections["Díl na papíře"][0].isVisible()


def test_repeat_draw_keeps_draft_and_export_cannot_silently_omit_it(window, qtbot, monkeypatch):
    arrange_rectangle(window)
    window.actions["draw"].trigger()
    for point in [(0, 0), (3000, 0)]:
        qtbot.mouseClick(
            window.sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(point[0], -point[1])),
        )
    before = deepcopy(window.sketch.points)
    state = deepcopy(window.project.to_dict())
    window.actions["draw"].trigger()
    assert window.sketch.points == before
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: messages.append(a[2]))
    window.actions["export"].trigger()
    assert messages and "Rozpracované body" in messages[0]
    assert window.sketch.points == before and window.project.to_dict() == state


def test_hole_draft_stays_attached_to_original_surface_after_selection_change(window, qtbot):
    first = arrange_rectangle(window, name="Otvor patří sem")
    second = arrange_rectangle(window, name="Jiná stěna")
    window.select_surface(first)
    window.actions["hole"].trigger()
    for x, y in [(2000, 2000), (4000, 2000), (4000, 4000), (2000, 4000)]:
        qtbot.mouseClick(
            window.sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(x, -y)),
        )
    window.select_surface(second)
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return)
    assert len(window.project.surfaces[first].hole_profile_ids) == 1
    assert window.project.surfaces[second].hole_profile_ids == []
    assert window.selected_surface == first


def test_keyboard_issue_activation_focuses_actual_part(window, qtbot):
    sid = arrange_rectangle(window)
    pid = window.selected_part
    window.clear_selection()
    window.issues.setCurrentRow(0)
    window.issues.setFocus()
    qtbot.keyClick(window.issues, Qt.Key.Key_Return)
    assert window.selected_part == pid and window.selected_surface == sid
    assert window.paper.selected_part == pid


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "authoring-settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("tips_enabled", True)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args[2]))
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Cancel
    )
    item = AuthorMainWindow(settings=settings)
    item._test_warnings = warnings

    def safe_close(widget):
        widget.sketch.cancel_outline()
        widget.connect_source = None
        widget.controller._saved_digest = widget.controller.digest(widget.project.to_dict())

    qtbot.addWidget(item, before_close_func=safe_close)
    item.show()
    item.activateWindow()
    item.raise_()
    qtbot.waitExposed(item)
    qtbot.wait(35)
    return item


def sketch_points(qtbot, window, points, *, hole=False):
    window.actions["hole" if hole else "draw"].trigger()
    assert window.sketch.drawing
    for x, y in points:
        qtbot.mouseClick(
            window.sketch.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(x, -y)),
        )
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return)
    qtbot.wait(20)


def arrange_rectangle(window, *, points=None, name="Vlastní stěna"):
    if points is None:
        points = [[0.0, 0.0], [10000.0, 0.0], [10000.0, 6000.0], [0.0, 6000.0]]

    def operation(project):
        pid = project.add_profile(points)
        return project.add_surface(pid, name=name)

    sid = window.controller.execute("Příprava kontrolního dílu", operation)
    window.select_surface(sid)
    window.focus_selection()
    return sid


def profile_of(window, sid):
    return window.project.profiles[window.project.surfaces[sid].profile_id]


def cached_geometry(payload):
    return {key: payload[key] for key in ("polygons", "paths", "labels", "edges")}


def set_number(qtbot, field, text):
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(field, str(text))
    qtbot.keyClick(field, Qt.Key.Key_Return)


def test_empty_workspace_creates_own_concave_polygon_by_actual_clicks_and_enter(window, qtbot):
    assert not window.project.surfaces and not window.project.parts
    assert not window.actions["hole"].isEnabled()
    assert "Začněte" in window.hint.text()
    points = [
        [0.0, 0.0],
        [10000.0, 0.0],
        [10000.0, 4000.0],
        [7000.0, 4000.0],
        [7000.0, 6000.0],
        [0.0, 6000.0],
    ]
    sketch_points(qtbot, window, points)
    assert len(window.project.surfaces) == len(window.project.parts) == 1
    sid = window.selected_surface
    assert profile_of(window, sid).points == points
    part = window.project.parts[window.selected_part]
    assert not part.stale and window.actions["hole"].isEnabled()
    polygon = np.array(window.project.part_geometry(part.id)["polygons"][sid][0])
    actual = (
        abs(
            np.sum(
                polygon[:, 0] * np.roll(polygon[:, 1], -1)
                - polygon[:, 1] * np.roll(polygon[:, 0], -1)
            )
        )
        / 2
    )
    assert actual == pytest.approx(5400.0)
    assert len(window.viewport.meshes) == 1 and part.id in window.paper.part_items
    assert window.controller.dirty
    assert window._test_warnings == []


def test_hole_draw_is_real_trim_and_old_paper_is_stale_until_explicit_recompute(window, qtbot):
    sid = arrange_rectangle(window)
    pid = window.selected_part
    cached = cached_geometry(window.project.part_geometry(pid))
    sketch_points(
        qtbot,
        window,
        [[2000.0, 2000.0], [4000.0, 2000.0], [4000.0, 4000.0], [2000.0, 4000.0]],
        hole=True,
    )
    assert len(window.project.surfaces[sid].hole_profile_ids) == 1
    assert window.project.parts[pid].stale
    assert cached_geometry(window.project.part_geometry(pid)) == cached
    qtbot.keyClick(window, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    qtbot.waitUntil(lambda: not window.project.parts[pid].stale)
    assert len(window.project.part_geometry(pid)["polygons"][sid]) == 2
    assert window._test_warnings == []


def test_invalid_hole_retains_editable_draft_and_escape_preserves_prior_project(window, qtbot):
    arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    sketch_points(
        qtbot, window, [[12000.0, 1000.0], [14000.0, 1000.0], [14000.0, 3000.0]], hole=True
    )
    assert window._test_warnings
    assert window.sketch.drawing and len(window.sketch.points) == 3
    assert window.project.to_dict() == before
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.sketch.drawing and window.project.to_dict() == before


def test_stable_vertex_drag_is_undoable_and_does_not_implicitly_recompute(window, qtbot):
    sid = arrange_rectangle(window)
    profile = profile_of(window, sid)
    vertex = profile.vertices[2]
    identity, pid = vertex.id, window.selected_part
    before = deepcopy(cached_geometry(window.project.part_geometry(pid)))
    handle = next(
        item
        for item in window.sketch.scene().items()
        if isinstance(item, VertexHandle) and item.vertex_id == identity
    )
    start = window.sketch.mapFromScene(handle.scenePos())
    end = start + QPoint(25, 0)
    qtbot.mousePress(window.sketch.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(window.sketch.viewport(), end, delay=20)
    qtbot.mouseRelease(window.sketch.viewport(), Qt.MouseButton.LeftButton, pos=end)
    qtbot.wait(20)
    assert profile_of(window, sid).vertex(identity).point != [10000.0, 6000.0]
    assert window.project.parts[pid].stale
    assert cached_geometry(window.project.part_geometry(pid)) == before
    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert profile_of(window, sid).vertex(identity).point == [10000.0, 6000.0]
    assert not window.project.parts[pid].stale
    assert cached_geometry(window.project.part_geometry(pid)) == before


def test_main_escape_and_ctrl_z_cancel_active_paper_drag_without_undoing_prior_command(
    window, qtbot
):
    arrange_rectangle(window)
    pid = window.selected_part
    page = window.project.pages[0].id
    window.controller.execute(
        "Umístit kontrolní díl",
        lambda p: p.set_placement(pid, page_id=page, x_mm=40.0, y_mm=50.0, rotation_deg=0.0),
    )
    window.paper.focus_part(pid)
    before = deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)
    for key, modifier in [
        (Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier),
    ]:
        item = window.paper.part_items[pid]
        origin = QPointF(item.pos())
        start = window.paper.mapFromScene(item.mapToScene(QPointF(10.0, 10.0)))
        end = start + QPoint(30, 15)
        qtbot.mousePress(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=start)
        qtbot.mouseMove(window.paper.viewport(), end, delay=20)
        assert item.pos() != origin
        qtbot.keyClick(window, key, modifier)
        qtbot.mouseRelease(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=end)
        qtbot.wait(20)
        assert window.project.to_dict() == before and len(window.controller._undo) == depth
        assert window.paper.part_items[pid].pos() == origin


def test_ctrl_z_reverts_uncommitted_sketch_point_even_with_no_command_history(window, qtbot):
    window.actions["draw"].trigger()
    for point in [(0.0, 0.0), (4000.0, 0.0)]:
        qtbot.mouseClick(
            window.sketch.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(point[0], -point[1])),
        )
    assert len(window.sketch.points) == 2
    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert len(window.sketch.points) == 1
    assert not window.project.surfaces and not window.controller.dirty


def test_actual_3d_click_through_hole_and_2d_selection_link_same_source(window, qtbot):
    below = arrange_rectangle(window, name="Spodní plocha")
    top = arrange_rectangle(window, name="Plocha s otvorem")

    def operation(project):
        hole = project.add_profile(
            [[2500.0, 1500.0], [7500.0, 1500.0], [7500.0, 4500.0], [2500.0, 4500.0]]
        )
        project.add_hole(top, hole)
        project.set_transform(top, [0.0, 0.0, 500.0], [0.0, 0.0, 0.0])
        project.recompute()

    window.controller.execute("Připravit prostorový kontrolní otvor", operation)
    window.viewport.yaw = window.viewport.pitch = 0.0
    window.viewport.focus_selection(all_surfaces=True)
    point = window.viewport.project_points([[5000.0, 3000.0, 500.0]])[0]
    qtbot.mouseClick(
        window.viewport, Qt.MouseButton.LeftButton, pos=QPoint(round(point[0]), round(point[1]))
    )
    assert window.selected_surface == below
    assert window.viewport.selected_surfaces == {below}
    assert window.paper.selected_part == window.project.surfaces[below].part_id
    point = window.viewport.project_points([[1000.0, 3000.0, 500.0]])[0]
    qtbot.mouseClick(
        window.viewport, Qt.MouseButton.LeftButton, pos=QPoint(round(point[0]), round(point[1]))
    )
    assert window.selected_surface == top
    pid = window.selected_part
    window.paper.focus_part(pid)
    paper_point = window.paper.mapFromScene(
        window.paper.part_items[pid].mapToScene(QPointF(10.0, 10.0))
    )
    window.select_surface(below)
    qtbot.mouseClick(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=paper_point)
    assert window.selected_surface == top and window.viewport.selected_surfaces == {top}
    assert window.tree.currentItem().data(0, Qt.ItemDataRole.UserRole) == top


@pytest.mark.parametrize(
    "unit,width,height", [(0, 10.0, 4.0), (1, 1000.0, 400.0), (2, 10000.0, 4000.0)]
)
def test_numeric_rectangle_unit_input_is_converted_once_to_100mm_paper_width(
    window, qtbot, unit, width, height
):
    window.units.setCurrentIndex(unit)

    def complete_dialog():
        dialog = QApplication.activeModalWidget()
        fields = dialog.findChildren(QDoubleSpinBox)
        fields[0].setValue(width)
        fields[1].setValue(height)
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()

    QTimer.singleShot(0, complete_dialog)
    window.actions["rectangle"].trigger()
    sid = window.selected_surface
    assert max(p[0] for p in profile_of(window, sid).points) == 10000.0
    polygon = np.array(window.project.part_geometry(window.selected_part)["polygons"][sid][0])
    assert np.ptp(polygon[:, 0]) == pytest.approx(100.0)
    assert np.ptp(polygon[:, 1]) == pytest.approx(40.0)


def test_focus_and_angle_only_edit_preserve_raw_decimal_source_and_placement(
    window, qtbot, tmp_path
):
    sid = arrange_rectangle(
        window,
        points=[
            [0.123456789, 0.987654321],
            [10000.123456789, 0.987654321],
            [10000.123456789, 4000.987654321],
            [0.123456789, 4000.987654321],
        ],
    )
    pid = window.selected_part
    window.controller.execute(
        "Umístit přesně",
        lambda p: p.set_placement(
            pid,
            page_id=p.pages[0].id,
            x_mm=40.123456789,
            y_mm=55.987654321,
            rotation_deg=13.333333333,
        ),
    )
    window.select_surface(sid)
    vertex = profile_of(window, sid).vertices[1]
    window.select_vertex(profile_of(window, sid).id, vertex.id)
    window.controller.save(tmp_path / "precision.apcraft")
    before = deepcopy(window.project.to_dict())
    for field in [
        window.vertex_x,
        window.vertex_y,
        window.paper_x,
        window.paper_y,
        window.paper_angle,
        window.scale_field,
        *window.transform_fields,
    ]:
        field.setFocus()
        qtbot.keyClick(field, Qt.Key.Key_Tab)
    assert window.project.to_dict() == before and not window.controller.dirty
    set_number(qtbot, window.paper_angle, "20")
    placement = window.project.placements[pid]
    assert (
        placement.x_mm == 40.123456789
        and placement.y_mm == 55.987654321
        and placement.rotation_deg == 20.0
    )
    assert profile_of(window, sid).vertex(vertex.id).point == [10000.123456789, 0.987654321]


def test_tips_repeat_off_and_direct_keyboard_route_do_not_change_project(window, qtbot):
    before = deepcopy(window.project.to_dict())
    window.tips_action.setChecked(False)
    assert not window.hint.isVisible()
    window.settings.sync()
    assert window.settings.value("tips_enabled", True, type=bool) is False
    qtbot.keyClick(window, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier)
    assert window.sketch.drawing and not window.hint.isVisible()
    qtbot.keyClick(window, Qt.Key.Key_F1)
    assert window.hint.isVisible() and window.tips_action.isChecked()
    window.tips_action.setChecked(False)
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.sketch.drawing and not window.hint.isVisible()
    assert window.project.to_dict() == before and not window.controller.dirty


def test_save_undo_branch_dirty_and_failed_save_preserve_original(
    window, qtbot, tmp_path, monkeypatch
):
    sid = arrange_rectangle(window)
    path = tmp_path / "Vlastní model.apcraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), "Papercraft")
    )
    qtbot.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    assert path.is_file() and not window.controller.dirty
    original = path.read_bytes()
    window.controller.undo()
    assert window.controller.dirty and not window.project.surfaces
    replacement = arrange_rectangle(window, name="Jiný díl při stejné hloubce historie")
    assert replacement != sid and window.controller.dirty

    def fail(path):
        raise OSError("Injected save failure")

    monkeypatch.setattr(window.project, "save", fail)
    assert window.save_project() is False
    assert window.controller.dirty and path.read_bytes() == original
    assert "Injected save failure" in window._test_warnings[-1]


def test_close_cancel_keeps_dirty_project_and_draft_cancel_is_explicit(window, qtbot):
    arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    assert window.close() is False
    assert window.isVisible() and window.project.to_dict() == before and window.controller.dirty
    window.actions["draw"].trigger()
    qtbot.mouseClick(
        window.sketch.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.sketch.mapFromScene(QPointF(0.0, 0.0)),
    )
    assert window.close() is False and window.sketch.drawing and window.sketch.points
    assert window.project.to_dict() == before
