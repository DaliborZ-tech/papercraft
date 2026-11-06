"""An open author profile can become a printable surface through real widgets."""

import pytest
from PySide6.QtCore import QPointF, QSettings, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QFileDialog

from archpapercraft.ui.author_window import AuthorMainWindow

pytestmark = pytest.mark.ui


def test_open_profile_save_reopen_append_close_and_history_actions(qtbot, tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = AuthorMainWindow(settings=settings)

    def safe_close(widget):
        widget.sketch.cancel_outline()
        widget.controller._saved_digest = widget.controller.digest(widget.project.to_dict())

    qtbot.addWidget(window, before_close_func=safe_close)
    window.show()
    window.activateWindow()
    window.raise_()
    qtbot.waitExposed(window)
    qtbot.wait(40)
    window.actions["draw"].trigger()
    for x, y in [(0, 0), (4000, 0)]:
        qtbot.mouseClick(
            window.sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(x, -y)),
        )
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)
    profile_id = window.selected_profile
    profile = window.project.profiles[profile_id]
    original_vertices = [vertex.id for vertex in profile.vertices]
    original_edge = profile.segments[0].id
    assert not profile.closed and len(profile.points) == 2
    assert not window.project.surfaces and not window.project.parts
    assert not window.actions["profile_surface"].isEnabled()
    assert window.actions["append_profile"].isEnabled()
    assert not window.actions["hole"].isEnabled()
    path = tmp_path / "open-profile.apcraft"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: (str(path), ""))
    window.actions["save"].trigger()
    assert path.exists() and not window.controller.dirty
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(path), ""))
    window.actions["open"].trigger()
    item = next(
        window.tree.topLevelItem(index)
        for index in range(window.tree.topLevelItemCount())
        if window.tree.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole)
        == ("profile", profile_id)
    )
    window.tree.setCurrentItem(item)

    def accept_append():
        dialog = QApplication.activeModalWidget()
        assert dialog is not None
        buttons = dialog.findChild(QDialogButtonBox)
        buttons.button(QDialogButtonBox.StandardButton.Ok).click()

    QTimer.singleShot(40, accept_append)
    window.actions["append_profile"].trigger()
    profile = window.project.profiles[profile_id]
    assert len(profile.points) == 3 and not profile.closed
    assert profile.points[-1] == [4000, 1000]
    assert [vertex.id for vertex in profile.vertices[:2]] == original_vertices
    assert profile.segments[0].id == original_edge
    assert window.selected_vertex == (profile_id, profile.vertices[-1].id)
    assert window.actions["profile_surface"].isEnabled()
    window.actions["profile_surface"].trigger()
    profile = window.project.profiles[profile_id]
    assert profile.closed and len(window.project.surfaces) == 1
    assert window.project.surfaces[window.selected_surface].profile_id == profile_id
    assert profile.segments[0].id == original_edge
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)
    assert not window.project.surfaces
    assert not window.project.profiles[profile_id].closed
    assert window.actions["redo"].isEnabled()
    qtbot.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)
    assert len(window.project.surfaces) == 1 and window.actions["undo"].isEnabled()
