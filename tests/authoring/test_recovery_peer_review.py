"""Independent DATA01 probes on the integrated workspace; no production changes."""

import copy
from pathlib import Path
from uuid import uuid4

import pytest
import test_recovery_workspace as workspace_cases
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QMessageBox
from test_workspace import arrange_rectangle

import archpapercraft.authoring.recovery as store_module
import archpapercraft.ui.author_recovery as adapter
from archpapercraft.authoring.recovery import RecoveryStore

window = workspace_cases.window


@pytest.fixture(autouse=True)
def peer_modals(monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *_args: QMessageBox.StandardButton.Ok)


def test_peer_adapter_import_identity():
    assert Path(adapter.__file__).resolve() == (
        Path(__file__).resolve().parents[2] / "src/archpapercraft/ui/author_recovery.py"
    )


def test_recovery_preserves_unfinished_hole_on_existing_wall(window, qtbot):
    arrange_rectangle(window)
    before = copy.deepcopy(window.project.to_dict())
    assert window.recovery.checkpoint()
    path = window.recovery.store.path(window.recovery.session_id)
    previous = path.read_bytes()
    window.actions["hole"].trigger()
    for x, y in ((1000, 1000), (2000, 1000)):
        qtbot.mouseClick(window.sketch.viewport(), Qt.MouseButton.LeftButton,
                         pos=window.sketch.mapFromScene(QPointF(x, -y)))
    assert window.sketch.drawing and window.sketch.hole and len(window.sketch.points) == 2
    assert window.project.to_dict() == before
    plane = copy.deepcopy(window.draft_plane)
    checkpointed = window.recovery.checkpoint()
    if not checkpointed:
        assert path.read_bytes() == previous
    assert checkpointed, window.statusBar().currentMessage()
    assert path.read_bytes() != previous
    stored = window.recovery.store.read(path)
    assert stored["document"] == before
    assert stored["ui_draft"]["sketch"]["hole"]
    candidate = workspace_cases.released(window)
    window.sketch.cancel_outline()
    window.controller.new()
    assert window.recovery.restore(candidate)
    assert window.project.to_dict() == before
    assert window.sketch.hole and window.sketch.drawing
    assert len(window.sketch.points) == 2
    assert window.draft_plane == plane


@pytest.mark.parametrize("raw_name", ["Brana pending", ""])
def test_clean_document_with_unconfirmed_inline_name_is_checkpointed(window, qtbot, raw_name):
    arrange_rectangle(window)
    window.controller._saved_digest = window.controller.digest(window.project.to_dict())
    before = copy.deepcopy(window.project.to_dict())
    history = copy.deepcopy(window.controller._undo)
    window.selection_name.setFocus()
    window.selection_name.selectAll()
    qtbot.keyClick(window.selection_name, Qt.Key.Key_Backspace)
    qtbot.keyClicks(window.selection_name, raw_name)
    assert window.project.to_dict() == before and not window.controller.dirty
    checkpointed = window.recovery.checkpoint()
    if not checkpointed:
        # Do not leave an intentionally invalid name to open a modal at teardown.
        window.selection_name.blockSignals(True)
        window.selection_name.setText(window.project.surfaces[window.selected_surface].name)
        window.selection_name.clearFocus()
        window.selection_name.blockSignals(False)
    assert checkpointed, "Pending inline name has no separate draft"
    assert window.project.to_dict() == before and window.controller._undo == history
    assert window.selection_name.text() == raw_name
    candidate = workspace_cases.released(window)
    window.selection_name.blockSignals(True)
    window.selection_name.setText(window.project.surfaces[window.selected_surface].name)
    window.selection_name.clearFocus()
    window.selection_name.blockSignals(False)
    window.controller.new()
    assert window.recovery.restore(candidate)
    assert window.project.to_dict() == before and window.controller.dirty
    assert window.selection_name.text() == raw_name and window.selection_name.hasFocus()


def test_fsync_failure_preserves_last_valid_draft_original_and_cleans_temp(tmp_path, monkeypatch):
    store = RecoveryStore(tmp_path / "drafts")
    identifier = uuid4()
    original = tmp_path / "original.apcraft"
    original.write_bytes(b"user-owned-original")
    path = store.write(identifier, {"name": "last checkpoint"}, {}, original)
    previous = path.read_bytes()

    def fail(_descriptor):
        raise OSError("injected fsync failure")

    monkeypatch.setattr(store_module.os, "fsync", fail)
    with pytest.raises(OSError, match="injected fsync failure"):
        store.write(identifier, {"name": "later state"}, {}, original)
    assert path.read_bytes() == previous
    assert original.read_bytes() == b"user-owned-original"
    assert list(store.directory.iterdir()) == [path]
