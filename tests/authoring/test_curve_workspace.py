"""The host must turn actual curve gestures into reversible authored material."""

import copy

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from test_workspace import window as _window_fixture

from archpapercraft.ui.author_curves import CurveEditorDialog

pytestmark = pytest.mark.ui
window = _window_fixture


def prepare(window):
    window.curve_mode.setCurrentIndex(window.curve_mode.findData("arc"))
    window.actions["draw"].trigger()
    window.sketch.fitInView(QRectF(-500, -2500, 5000, 5000),
                            Qt.AspectRatioMode.KeepAspectRatio)


def point(window, qtbot, x, y):
    qtbot.mouseClick(window.sketch.viewport(), Qt.MouseButton.LeftButton,
                     pos=window.sketch.mapFromScene(QPointF(x, -y)))


def circle(window, qtbot):
    prepare(window)
    for p in ((0, 0), (2000, -2000), (4000, 0), (2000, 2000), (0, 0)):
        point(window, qtbot, *p)
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return)
    assert not window._test_warnings
    return window.selected_surface


def test_actual_two_arc_gesture_is_material_with_two_source_edges_and_single_undo(window, qtbot):
    before = copy.deepcopy(window.project.to_dict())
    sid = circle(window, qtbot)
    profile = window.project.profiles[window.project.surfaces[sid].profile_id]
    assert len(profile.vertices) == len(profile.segments) == 2
    assert all(s.kind == "arc" for s in profile.segments)
    assert window.edge_choice.count() == 2  # Not hundreds of display chords.
    assert window.curve_choice.count() == 2
    part = window.project.parts[window.selected_part]
    assert len(part.edges) > 100 and all("commands" in p for p in part.paths["CUT"])
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before
    window.actions["redo"].trigger()
    assert sid in window.project.surfaces


def test_pending_arc_point_has_visible_next_step_and_undo_then_can_finish(window, qtbot):
    prepare(window)
    point(window, qtbot, 0, 0)
    assert "procházet" in window.context.text()
    point(window, qtbot, 2000, -2000)
    assert "koncový" in window.context.text()
    assert not window.actions["finish"].isEnabled()
    window.actions["undo"].trigger()
    assert not window.sketch.pending_points
    assert "procházet" in window.context.text()
    point(window, qtbot, 2000, -2000)
    point(window, qtbot, 4000, 0)
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert len(window.project.profiles) == 1 and not window.project.surfaces
    profile = next(iter(window.project.profiles.values()))
    assert not profile.closed and profile.segments[0].kind == "arc"
    assert profile.id in window.viewport.profile_paths
    assert window.viewport.selected_profile == profile.id


def test_curve_editor_is_one_staged_command_and_cancellation_preserves_source(window, qtbot):
    sid = circle(window, qtbot)
    profile_id = window.project.surfaces[sid].profile_id
    segment_id = window.project.profiles[profile_id].segments[0].id
    index = next(i for i in range(window.curve_choice.count())
                 if window.curve_choice.itemData(i) == (profile_id, segment_id))
    window.curve_choice.setCurrentIndex(index)
    before = copy.deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)

    def cancel():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, CurveEditorDialog)
        dialog.kind.setCurrentIndex(dialog.kind.findData("cubic"))
        dialog.reject()

    QTimer.singleShot(0, cancel)
    window.actions["edit_curve"].trigger()
    assert window.project.to_dict() == before and len(window.controller._undo) == depth

    def accept():
        dialog = QApplication.activeModalWidget()
        dialog.kind.setCurrentIndex(dialog.kind.findData("cubic"))
        qtbot.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok),
                         Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, accept)
    window.actions["edit_curve"].trigger()
    assert window.project.profiles[profile_id].segment(segment_id).kind == "cubic"
    assert window.project.parts[window.project.part_for_surface(sid)].stale
    assert len(window.controller._undo) == depth + 1
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before


def test_straight_connection_commands_do_not_treat_curved_edge_as_chord(window, qtbot):
    sid = circle(window, qtbot)
    edge = window.project.profiles[window.project.surfaces[sid].profile_id].segments[0].id
    window.select_edge(sid, edge)
    assert not window.connect_button.isEnabled()
    assert not window.attach_inside_button.isEnabled()
    assert window.curve_edit_button.isEnabled()
    assert "tětivu" in window.connect_button.toolTip()


def test_second_native_curve_selection_survives_property_refresh(window, qtbot):
    sid = circle(window, qtbot)
    pid = window.project.surfaces[sid].profile_id
    segment = window.project.profiles[pid].segments[1].id
    window.curve_choice.setCurrentIndex(1)
    assert window.curve_choice.currentData() == (pid, segment)
    assert window.selected_edge == (sid, segment)
    window.refresh()
    assert window.curve_choice.currentData() == (pid, segment)


def test_actual_cubic_input_is_saved_as_native_open_profile_without_a_fake_material(window, qtbot):
    prepare(window)
    window.curve_mode.setCurrentIndex(window.curve_mode.findData("cubic"))
    for p in ((0, 0), (1000, 2000), (3000, 2000), (4000, 0)):
        point(window, qtbot, *p)
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert not window.project.surfaces and len(window.project.profiles) == 1
    profile = next(iter(window.project.profiles.values()))
    assert not profile.closed and profile.segments[0].kind == "cubic"
    assert profile.segments[0].data == {"control1": [1000, 2000], "control2": [3000, 2000]}
    assert window.viewport.profile_paths[profile.id]


def test_invalid_circular_hole_keeps_draft_and_original_material_until_cancel(window, qtbot):
    sid = circle(window, qtbot)
    before = copy.deepcopy(window.project.to_dict())
    window.actions["hole"].trigger()
    window.sketch.fitInView(QRectF(-1000, -7000, 15000, 10000),
                            Qt.AspectRatioMode.KeepAspectRatio)
    for p in ((8000, 0), (10000, -2000), (12000, 0), (10000, 2000), (8000, 0)):
        point(window, qtbot, *p)
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return)
    assert window._test_warnings
    assert window.project.to_dict() == before
    assert window.sketch.drawing and window.sketch.curve_segments
    qtbot.keyClick(window.sketch, Qt.Key.Key_Escape)
    assert not window.sketch.drawing and window.selected_surface == sid
    assert window.project.to_dict() == before


def test_profile_copy_to_depth_is_independent_visible_and_one_undo_command(window, qtbot):
    from archpapercraft.ui.author_profile_placement import ProfilePlacementDialog

    sid = circle(window, qtbot)
    original_id = window.project.surfaces[sid].profile_id
    source = copy.deepcopy(window.project.profiles[original_id])
    before = copy.deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)

    def accept():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, ProfilePlacementDialog)
        field = dialog.fields["depth"]
        field.setFocus()
        qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        qtbot.keyClicks(field, "1")  # Current m units; no Return before dialog confirmation.
        dialog.accept()

    QTimer.singleShot(0, accept)
    window.actions["copy_profile"].trigger()
    target_id = window.selected_profile
    target = window.project.profiles[target_id]
    assert target.id != original_id and target.plane.origin == [0, 0, 1000]
    assert target.points[1] == [4800, 0]
    assert window.project.profiles[original_id] == source
    assert target_id in window.viewport.profile_paths
    assert window.viewport.selected_profile == target_id
    assert len(window.controller._undo) == depth + 1
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before


def test_profile_placement_cancel_and_unchanged_confirm_preserve_source_precision(qtbot):
    from archpapercraft.authoring import AuthorProject
    from archpapercraft.ui.author_profile_placement import ProfilePlacementDialog

    project = AuthorProject.new()
    pid = project.add_profile([[0, 0], [10, 0]], closed=False,
                              plane={"origin": [0.000000123456789, 0, 0],
                                     "u": [1, 0, 0], "v": [0, 1, 0]})
    before = copy.deepcopy(project.to_dict())
    dialog = ProfilePlacementDialog(project, pid, unit_factor=1000, unit_label="m")
    qtbot.addWidget(dialog)
    dialog.accept()
    project.set_profile_plane(pid, **dialog.result_spec["plane"])
    assert project.to_dict() == before
    cancelled = ProfilePlacementDialog(project, pid, copying=True)
    qtbot.addWidget(cancelled)
    cancelled.fields["factor"].setValue(2)
    cancelled.reject()
    assert cancelled.result_spec is None and project.to_dict() == before


def test_unresolvable_construction_profile_is_preserved_without_crashing_the_view(window):
    pid = window.controller.execute("Large source curve", lambda p: p.add_profile(segments=[{
        "kind": "cubic", "start": [1e14, 0], "end": [1e14 + 100, 0],
        "control1": [1e14 + 20, 30], "control2": [1e14 + 80, 30],
    }], closed=False))
    window.select_profile(pid)
    assert pid in window.project.profiles
    assert pid in window.viewport.profile_problems and pid not in window.viewport.profile_paths
    assert window.actions["edit_curve"].isEnabled()
