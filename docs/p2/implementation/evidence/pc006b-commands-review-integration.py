"""Independent UI delta checks; run with bend-integration source/config."""
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from test_workspace import arrange_rectangle, profile_of, window  # noqa: F401

import archpapercraft.ui.author_window as module
from archpapercraft.ui.author_editing import DeletePartDialog, RenameDialog


def test_source_is_integration_not_earlier_component():
    assert 'papercraft-bend-integration' in str(Path(module.__file__).resolve())


def test_real_F2_commits_pending_coordinate_then_cancel_retains_that_edit(window, qtbot):
    sid = arrange_rectangle(window)
    profile = profile_of(window, sid)
    vid = profile.vertices[1].id
    window.select_vertex(profile.id, vid)
    window.vertex_x.setFocus()
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.vertex_x, '12')
    observed = []

    def inspect():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, RenameDialog)
        observed.append(profile_of(window, sid).vertex(vid).point[0])
        dialog.reject()

    QTimer.singleShot(0, inspect)
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_F2)
    assert observed == [12000.0]
    assert profile_of(window, sid).vertex(vid).point[0] == 12000


def test_sidebar_delete_targets_selected_second_part_with_undo_and_confirmed_plain_text(window, qtbot):
    first = arrange_rectangle(window)
    second = arrange_rectangle(window, points=[[20000, 0], [30000, 0], [30000, 4000], [20000, 4000]])
    window.select_surface(first)
    first_pid = window.project.part_for_surface(first)
    before = deepcopy(window.project.to_dict())
    window.select_surface(second)
    observed = []

    def confirm():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, DeletePartDialog)
        observed.append(dialog.part_id)
        assert 'Odstraněné spojovací prvky s chlopněmi: 0.' in dialog.details.toPlainText()
        qtbot.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, confirm)
    qtbot.mouseClick(window.delete_part_button, Qt.MouseButton.LeftButton)
    assert observed == [before['surfaces'][second]['part_id']]
    assert second not in window.project.surfaces and first in window.project.surfaces
    assert window.project.to_dict()['parts'][first_pid] == before['parts'][first_pid]
    assert window.project.to_dict()['placements'][first_pid] == before['placements'][first_pid]
    window.actions['undo'].trigger()
    assert window.project.to_dict() == before


def test_clear_selection_changes_delete_availability_but_keeps_project_rename(window, qtbot):
    arrange_rectangle(window)
    window.clear_selection()
    assert not window.actions['delete_part'].isEnabled()
    assert not window.delete_part_button.isEnabled()
    assert window.actions['rename'].isEnabled() and window.rename_button.isEnabled()
    observed = []

    def inspect():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, RenameDialog)
        observed.append(dialog.surface_name is None and dialog.part_name is None)
        dialog.reject()

    QTimer.singleShot(0, inspect)
    qtbot.mouseClick(window.rename_button, Qt.MouseButton.LeftButton)
    assert observed == [True]
