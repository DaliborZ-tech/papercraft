"""Actual widget input for native curve drafting; not a novice-user study."""

import copy
import math

import pytest
from PySide6.QtCore import QLocale, QPoint, QPointF, QRectF, Qt
from PySide6.QtWidgets import QDialog

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_curves import CurveEditorDialog, CurveSketch

pytestmark = pytest.mark.ui


@pytest.fixture
def sketch(qtbot):
    widget = CurveSketch()
    widget.resize(720, 500)
    widget.grid_mm = 1
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.fitInView(QRectF(-5, -15, 45, 30), Qt.AspectRatioMode.KeepAspectRatio)
    return widget


def click(qtbot, sketch, x, y):
    qtbot.mouseClick(sketch.viewport(), Qt.MouseButton.LeftButton,
                     pos=sketch.mapFromScene(QPointF(x, -y)))


def test_line_only_sketch_keeps_original_finish_signal_and_direct_clicks(sketch, qtbot):
    results = []
    sketch.outline_finished.connect(lambda p, hole: results.append((p, hole)))
    sketch.start_outline()
    for p in ((0, 0), (10, 0), (10, 10)):
        click(qtbot, sketch, *p)
    qtbot.keyClick(sketch, Qt.Key.Key_Return)
    assert results == [([[0, 0], [10, 0], [10, 10]], False)]
    assert not sketch.drawing and not sketch.points


def test_three_actual_arc_clicks_create_native_open_source_and_keep_draft_until_host_accepts(
    sketch, qtbot
):
    results = []
    statuses = []
    sketch.curve_profile_finished.connect(lambda *args: results.append(args))
    sketch.status.connect(statuses.append)
    sketch.set_segment_mode("arc")
    sketch.start_outline()
    click(qtbot, sketch, 0, 0)
    assert "procházet" in statuses[-1]
    click(qtbot, sketch, 5, -5)
    assert "koncový" in statuses[-1]
    click(qtbot, sketch, 10, 0)
    qtbot.keyClick(sketch, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    specs, closed, hole = results[0]
    assert len(specs) == 1 and specs[0]["kind"] == "arc"
    assert specs[0]["data"]["center"] == pytest.approx([5, 0])
    assert specs[0]["data"]["sweep_deg"] == pytest.approx(180)
    assert not closed and not hole
    assert sketch.drawing and sketch.curve_segments
    sketch.complete_curve_draft()
    assert not sketch.drawing and not sketch.curve_segments and not sketch.pending_points


def test_mixed_native_segments_preserve_shared_corners_and_explicit_closure(sketch, qtbot):
    results = []
    sketch.curve_profile_finished.connect(lambda *args: results.append(args))
    sketch.start_outline()
    for point in ((0, 0), (10, 0)):
        click(qtbot, sketch, *point)
    sketch.set_segment_mode("arc")
    for point in ((15, -5), (20, 0)):
        click(qtbot, sketch, *point)
    sketch.set_segment_mode("cubic")
    for point in ((23, 4), (28, 4), (30, 0)):
        click(qtbot, sketch, *point)
    qtbot.keyClick(sketch, Qt.Key.Key_Return)
    specs, closed, _ = results[0]
    assert [s["kind"] for s in specs] == ["line", "arc", "cubic", "line"]
    assert all(a["end"] == b["start"] for a, b in zip(specs, specs[1:]))
    assert specs[-1]["end"] == specs[0]["start"] and closed
    assert specs[2]["data"] == {"control1": [23, 4], "control2": [28, 4]}


def test_pending_handles_block_mode_switch_and_finish_and_undo_restores_one_input(sketch, qtbot):
    results = []
    sketch.curve_profile_finished.connect(lambda *args: results.append(args))
    sketch.set_segment_mode("cubic")
    sketch.start_outline()
    for p in ((0, 0), (3, 4), (7, 4)):
        click(qtbot, sketch, *p)
    assert not sketch.set_segment_mode("arc") and sketch.segment_mode == "cubic"
    qtbot.keyClick(sketch, Qt.Key.Key_Return)
    assert not results and sketch.pending_points == [[3, 4], [7, 4]]
    qtbot.keyClick(sketch, Qt.Key.Key_Backspace)
    assert sketch.pending_points == [[3, 4]]
    qtbot.keyClick(sketch, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert not sketch.pending_points and sketch.points == [[0, 0]]
    assert sketch.set_segment_mode("arc")
    qtbot.keyClick(sketch, Qt.Key.Key_Escape)
    assert not sketch.drawing and not sketch.points and not sketch.curve_segments


def test_bad_arc_retains_correctable_middle_point_without_partial_source(sketch, qtbot):
    sketch.set_segment_mode("arc")
    sketch.start_outline()
    for p in ((0, 0), (5, 0), (10, 0)):
        click(qtbot, sketch, *p)
    assert sketch.points == [[0, 0]] and sketch.pending_points == [[5, 0]]
    assert not sketch.curve_segments
    sketch.undo_draft_point()
    click(qtbot, sketch, 5, -5)
    click(qtbot, sketch, 10, 0)
    assert len(sketch.curve_segments) == 1


def test_two_arcs_close_a_real_circle_without_extra_polygon_vertices(sketch, qtbot):
    results = []
    sketch.curve_profile_finished.connect(lambda *args: results.append(args))
    sketch.set_segment_mode("arc")
    sketch.start_outline(hole=True)
    for p in ((0, 0), (5, -5), (10, 0), (5, 5), (0, 0)):
        click(qtbot, sketch, *p)
    qtbot.keyClick(sketch, Qt.Key.Key_Return)
    specs, closed, hole = results[0]
    assert closed and hole and len(specs) == 2
    project = AuthorProject.new(scale=1)
    profile_id = project.add_profile(segments=specs, closed=closed)
    assert len(project.profiles[profile_id].vertices) == 2
    sid = project.add_surface(profile_id)
    assert len(project.parts[project.part_for_surface(sid)].polygons[sid][0]) > 20


def source_project(kind="line", *, angle=90):
    project = AuthorProject.new(scale=1)
    data = {}
    end = [10, 0]
    if kind == "arc":
        start = [10, 0]
        end = [10 * math.cos(math.radians(angle)), 10 * math.sin(math.radians(angle))]
        data = {"center": [0, 0], "sweep_deg": angle}
    else:
        start = [0, 0]
    if kind == "cubic":
        data = {"control1": [2.123456789, 4.123456789], "control2": [8.123456789, 4.123456789]}
    pid = project.add_profile(segments=[{"kind": kind, "start": start, "end": end,
                                         "data": data}], closed=False)
    return project, pid, project.profiles[pid].segments[0].id


def show_dialog(qtbot, project, pid, sid, **kwargs):
    dialog = CurveEditorDialog(project, pid, sid, **kwargs)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    dialog.refresh_preview(frame=True)
    return dialog


def test_staged_arc_pending_angle_commits_before_accept_without_enter(qtbot):
    project, pid, sid = source_project("arc")
    before = copy.deepcopy(project.to_dict())
    dialog = show_dialog(qtbot, project, pid, sid)
    dialog.details.setChecked(True)
    dialog.angle.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    dialog.angle.setFocus()
    qtbot.keyClick(dialog.angle, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(dialog.angle, "120")
    assert dialog.angle.value() == 90
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_spec["data"]["sweep_deg"] == 120
    assert project.to_dict() == before


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_noop_dialog_preserves_full_source_precision_and_cancel_is_inert(qtbot, kind):
    project, pid, sid = source_project(kind, angle=90.123456789)
    before = copy.deepcopy(project.to_dict())
    dialog = show_dialog(qtbot, project, pid, sid)
    dialog.accept()
    assert dialog.result_spec == {"kind": kind, "data": project.profiles[pid].segments[0].data}
    assert project.to_dict() == before
    cancelled = show_dialog(qtbot, project, pid, sid)
    cancelled.kind.setCurrentIndex(cancelled.kind.findData("line"))
    cancelled.reject()
    assert cancelled.result_spec is None and project.to_dict() == before


def test_invalid_pending_angle_stops_confirmation_and_keeps_source(qtbot):
    project, pid, sid = source_project("arc")
    before = copy.deepcopy(project.to_dict())
    dialog = show_dialog(qtbot, project, pid, sid)
    dialog.details.setChecked(True)
    dialog.angle.setFocus()
    qtbot.keyClick(dialog.angle, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(dialog.angle, Qt.Key.Key_Backspace)
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted and dialog.result_spec is None
    assert "rozepsaný" in dialog.feedback.text() and project.to_dict() == before


def test_actual_cubic_handle_drag_changes_staged_shape_and_cancel_preserves_live_project(qtbot):
    project, pid, sid = source_project("cubic")
    before = copy.deepcopy(project.to_dict())
    dialog = show_dialog(qtbot, project, pid, sid)
    handle = dialog.handles[0]
    old = QPointF(handle.pos())
    start = dialog.preview.mapFromScene(old)
    destination = start + QPoint(35, -30)
    qtbot.mousePress(dialog.preview.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(dialog.preview.viewport(), destination, delay=30)
    qtbot.mouseRelease(dialog.preview.viewport(), Qt.MouseButton.LeftButton, pos=destination)
    qtbot.wait(30)
    original = before["profiles"][pid]["segments"][0]["data"]["control1"]
    assert dialog.specification()["data"]["control1"] != original
    assert project.to_dict() == before
    dialog.reject()
    assert dialog.result_spec is None and project.to_dict() == before


def test_escape_during_handle_drag_restores_only_gesture_then_dialog_can_confirm(qtbot):
    project, pid, sid = source_project("cubic")
    dialog = show_dialog(qtbot, project, pid, sid)
    before = copy.deepcopy(dialog.specification())
    start = dialog.preview.mapFromScene(dialog.handles[0].pos())
    destination = start + QPoint(30, -25)
    qtbot.mousePress(dialog.preview.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(dialog.preview.viewport(), destination, delay=30)
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    qtbot.mouseRelease(dialog.preview.viewport(), Qt.MouseButton.LeftButton, pos=destination)
    qtbot.wait(20)
    assert dialog.isVisible() and dialog.specification() == before
    dialog.accept()
    assert dialog.result_spec == before


def test_actual_arc_bulge_handle_drag_updates_a_native_arc_with_the_same_endpoints(qtbot):
    from archpapercraft.authoring.curves import Curve, evaluate

    project, pid, sid = source_project("arc")
    original = copy.deepcopy(project.to_dict())
    dialog = show_dialog(qtbot, project, pid, sid)
    initial = copy.deepcopy(dialog.specification())
    start = dialog.preview.mapFromScene(dialog.handles[0].pos())
    destination = start + QPoint(0, -25)
    qtbot.mousePress(dialog.preview.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(dialog.preview.viewport(), destination, delay=30)
    qtbot.mouseRelease(dialog.preview.viewport(), Qt.MouseButton.LeftButton, pos=destination)
    qtbot.wait(30)
    assert dialog.specification() != initial
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    curve = Curve(tuple(dialog.start), tuple(dialog.end), **dialog.result_spec)
    assert evaluate(curve, 0) == tuple(dialog.start)
    assert evaluate(curve, 1) == tuple(dialog.end)
    assert project.to_dict() == original


def test_cubic_pending_numeric_input_uses_display_unit_exactly_once(qtbot):
    project, pid, sid = source_project("cubic")
    original = copy.deepcopy(project.to_dict())
    dialog = show_dialog(qtbot, project, pid, sid, unit_factor=10)
    dialog.details.setChecked(True)
    field = dialog.fields["control1_x"]
    field.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(field, "1.5")
    dialog.accept()
    assert dialog.result_spec["data"]["control1"][0] == 15
    assert dialog.result_spec["data"]["control1"][1] == 4.123456789
    assert project.to_dict() == original
