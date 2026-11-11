"""Real widget input, not a native Windows or new-modeler observation."""

import copy

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
from test_curve_bend import wall_base
from test_workspace import arrange_rectangle
from test_workspace import window as _window_fixture

from archpapercraft.ui.author_subdivision import SubdivisionDialog

pytestmark = pytest.mark.ui
window = _window_fixture


def test_line_split_and_inverse_merge_from_widgets_is_reversible_and_keeps_source_context(
    window, qtbot
):
    assert not window.actions["split_profile"].isEnabled()
    sid = arrange_rectangle(window)
    pid = window.project.surfaces[sid].profile_id
    before = window.project.to_dict()
    count = len(window.controller._undo)

    def accept_split():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SubdivisionDialog)
        dialog.distance.setFocus()
        qtbot.keyClick(dialog.distance, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        qtbot.keyClicks(dialog.distance, "3")
        # No Enter: distance is in the window's default displayed model unit.
        qtbot.mouseClick(
            dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
        )

    QTimer.singleShot(0, accept_split)
    window.actions["split_profile"].trigger()
    assert len(window.project.profiles[pid].vertices) == 5
    assert len(window.controller._undo) == count + 1
    assert window.selected_surface == sid
    assert window.selected_vertex[0] == pid
    assert window.selected_edge[0] == sid
    assert window.project.profiles[pid].vertex(window.selected_vertex[1]).point == [3000, 0]
    assert window.project.parts[window.selected_part].stale
    assert window.actions["merge_profile"].isEnabled()
    changed = window.project.to_dict()
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before
    window.actions["redo"].trigger()
    assert window.project.to_dict() == changed

    def accept_merge():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SubdivisionDialog) and dialog.joining
        assert len(dialog.choices.selectedItems()) == 2
        qtbot.mouseClick(
            dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
        )

    QTimer.singleShot(0, accept_merge)
    window.actions["merge_profile"].trigger()
    assert len(window.project.profiles[pid].vertices) == 4
    assert not window.actions["merge_profile"].isEnabled()
    assert not window._test_warnings


def test_invalid_distance_is_repairable_without_enter_and_dialog_never_mutates_document(
    window, qtbot
):
    sid = arrange_rectangle(window)
    profile = window.project.profiles[window.project.surfaces[sid].profile_id]
    before = copy.deepcopy(window.project.to_dict())
    dialog = SubdivisionDialog(
        window.project, profile.id, profile.segments[0].id, unit_factor=1000, parent=window
    )
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.distance.setValue(0)
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted and dialog.feedback.text()
    dialog.distance.setFocus()
    qtbot.keyClick(dialog.distance, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(dialog.distance, "2")
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_spec["parameter"] == 0.2
    assert window.project.to_dict() == before


def test_cancel_split_keeps_history_layout_and_source(window, qtbot):
    arrange_rectangle(window)
    before = window.project.to_dict()
    count = len(window.controller._undo)

    def cancel():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SubdivisionDialog)
        dialog.distance.setValue(0)
        dialog.reject()

    QTimer.singleShot(0, cancel)
    window.actions["split_profile"].trigger()
    assert window.project.to_dict() == before
    assert len(window.controller._undo) == count


def test_selected_existing_tab_refresh_survives_source_split(window):
    project, connector_id, wall, _ = wall_base(known=False)
    project.recompute()
    window.controller.project = project
    window.refresh()
    window.select_surface(wall)
    attachment_id = project.connectors[connector_id].attachment_id
    window.viewport.select_relation(("attachment", attachment_id))
    assert window.viewport.relation_paths
    profile = project.profiles[project.surfaces[wall].profile_id]
    window.controller.execute("Rozdělit zdroj s chlopní", lambda p:
        p.split_profile_segment(profile.id, profile.segments[0].id))
    assert window.viewport.relation_paths and not window._test_warnings
