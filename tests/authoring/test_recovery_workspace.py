"""Offscreen real author widgets: raw edits and drafts remain separate from geometry."""

import copy
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtCore import QSettings, QSignalBlocker, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QMessageBox, QPushButton
from test_workspace import arrange_rectangle

from archpapercraft.ui.author_recovery import capture_ui, setup_recovery
from archpapercraft.ui.author_window import AuthorMainWindow

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "test.ini"), QSettings.Format.IniFormat)
    widget = AuthorMainWindow(settings=settings)
    # Hook patch is delivered separately to the workspace owner; no parallel layout edits.
    if not hasattr(widget, "recovery"):
        widget.recovery = setup_recovery(widget)
    qtbot.addWidget(widget)
    monkeypatch.setattr(widget, "_confirm_replace", lambda: True)
    widget.show()
    qtbot.wait(10)
    yield widget
    widget.recovery.finished_close()


def edit_raw(window, qtbot, text):
    sid = arrange_rectangle(window)
    profile = window.project.profiles[window.project.surfaces[sid].profile_id]
    window.select_vertex(profile.id, profile.vertices[1].id)
    window.vertex_x.setFocus()
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.vertex_x, text)
    return sid


def released(window):
    path = window.recovery.store.path(window.recovery.session_id)
    window.recovery.lease.unlock()
    window.recovery.lease = None
    window.recovery.session_id = str(uuid4())
    return path


@pytest.mark.parametrize("text", ["11", "-"])
def test_timer_preserves_focus_raw_text_model_history_and_saved_original(window, qtbot, tmp_path,
                                                                       text):
    sid = edit_raw(window, qtbot, text)
    # A clean model may still contain a pending numeric edit.
    window.controller._saved_digest = window.controller.digest(window.project.to_dict())
    before = copy.deepcopy(window.project.to_dict())
    history = copy.deepcopy(window.controller._undo)
    focus = QApplication.focusWidget()
    assert window.recovery.timer.interval() == 30000
    assert window.recovery.checkpoint()
    draft = window.recovery.store.read(window.recovery.store.path(window.recovery.session_id))
    assert draft["document"] == before
    assert draft["ui_draft"]["pending_number"] == {"field": "vertex_x", "text": text}
    assert draft["ui_draft"]["selection"]["surface"] == sid
    assert QApplication.focusWidget() is focus
    assert window.vertex_x.lineEdit().text() == text
    assert window.project.to_dict() == before and window.controller._undo == history
    assert not window.controller.dirty


def test_restore_raw_input_same_exact_selection_and_unsaved_copy(window, qtbot, tmp_path):
    sid = edit_raw(window, qtbot, "-")
    ui = capture_ui(window)
    before = copy.deepcopy(window.project.to_dict())
    assert window.recovery.checkpoint()
    path = released(window)
    # Programmatic replacement avoids committing the deliberately invalid text during setup.
    with QSignalBlocker(window.vertex_x):
        window.vertex_x.lineEdit().setText("0")
    window.controller.new()
    assert window.recovery.restore(path)
    assert window.project.to_dict() == before
    assert window.selected_surface == sid
    assert list(window.selected_vertex) == list(ui["selection"]["vertex"])
    assert window.vertex_x.lineEdit().text() == "-"
    assert QApplication.focusWidget() in (window.vertex_x, window.vertex_x.lineEdit())
    assert window.controller.dirty and window.controller.file_path is None
    assert not window.controller.can_undo


def test_unfinished_cubic_draft_recovers_handles_plane_and_backspace(window, qtbot):
    window.plane.setCurrentIndex(window.plane.findData("XZ"))
    window.start_outline()
    window.sketch.set_segment_mode("cubic")
    for point in ([0, 0], [0, 10], [10, 10], [10, 0], [20, -10]):
        window.sketch._add_point(point)
    before = capture_ui(window)
    assert not window.project.profiles and not window.controller.dirty
    assert window.recovery.checkpoint()
    path = released(window)
    window.sketch.cancel_outline()
    window.controller.new()
    assert window.recovery.restore(path)
    assert not window.project.profiles
    assert window.sketch.drawing and window.draft_plane == "XZ"
    assert window.sketch.pending_points == [[20, -10]]
    assert window.sketch.curve_segments == before["sketch"]["curve_segments"]
    assert window.sketch.undo_draft_point()
    assert window.sketch.pending_points == [] and window.sketch.points[-1] == [10, 0]


def test_live_other_window_draft_excluded_until_released(window, qtbot, tmp_path):
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    other = AuthorMainWindow(settings=window.settings)
    if not hasattr(other, "recovery"):
        other.recovery = setup_recovery(other)
    qtbot.addWidget(other)
    assert other.recovery.available() == []
    path = released(window)
    assert [row[0] for row in other.recovery.available()] == [path]
    other.recovery.finished_close()
    other._confirm_replace = lambda: True


def test_failed_write_keeps_draft_and_does_not_change_saved_state(window, monkeypatch):
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    path = window.recovery.store.path(window.recovery.session_id)
    before = path.read_bytes()
    state = window.project.to_dict()

    def fail(*_args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(window.recovery.store, "write", fail)
    assert not window.recovery.checkpoint()
    assert path.read_bytes() == before and window.project.to_dict() == state
    assert window.controller.dirty
    assert "disk unavailable" in window.statusBar().currentMessage()


def test_successful_save_replacement_and_explicit_clean_close_remove_only_own_draft(window,
                                                                                 tmp_path):
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    own = window.recovery.store.path(window.recovery.session_id)
    foreign = window.recovery.store.write(uuid4(), {"name": "Other crash"}, {})
    foreign_bytes = foreign.read_bytes()
    window.controller.save(tmp_path / "own.apcraft")
    assert not own.exists() and foreign.read_bytes() == foreign_bytes
    window.controller.execute("Name", lambda p: setattr(p, "name", "New name"))
    assert window.recovery.checkpoint()
    window.controller.new()
    assert not own.exists() and foreign.read_bytes() == foreign_bytes
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    window.recovery.finished_close()
    assert not own.exists() and foreign.read_bytes() == foreign_bytes
    assert not window.recovery.timer.isActive()


def test_invalid_selection_is_rejected_before_replacing_live_work(window):
    arrange_rectangle(window)
    state, ui = window.project.to_dict(), capture_ui(window)
    ui["selection"]["surface"] = "retired-surface"
    path = window.recovery.store.write(uuid4(), state, ui)
    before = window.project.to_dict()
    with pytest.raises(ValueError, match="Vybraný prvek"):
        window.recovery.restore(path)
    assert window.project.to_dict() == before and path.exists()


def test_failed_discard_cleanup_blocks_new_open_and_clean_close(window, monkeypatch, tmp_path):
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    path = window.recovery.store.path(window.recovery.session_id)
    before, raw = window.project.to_dict(), path.read_bytes()
    other = tmp_path / "other.apcraft"
    window.project.save(other)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))

    def denied(_path):
        raise OSError("delete denied")

    with monkeypatch.context() as context:
        context.setattr(window.recovery.store, "discard", denied)
        assert window.controller.new() is None
        assert window.controller.open(other) is None
        assert not window.recovery.finished_close()
        assert not window.recovery.closed and window.recovery.timer.isActive()
    assert len(warnings) == 3 and all("delete denied" in text for text in warnings)
    assert window.project.to_dict() == before and path.read_bytes() == raw


def test_startup_discovers_only_sandboxed_drafts_and_preserves_later(window, monkeypatch):
    path = window.recovery.store.write(uuid4(), window.project.to_dict(), capture_ui(window))
    offered = []
    monkeypatch.setattr(window.recovery, "offer", lambda **kw: offered.append(kw))
    window.recovery._startup()
    assert offered == [{"startup": True}] and path.exists()
    assert window.recovery.store.directory == Path(window.settings.fileName()).parent / "recovery"


def test_restore_cancel_preserves_live_work_and_both_drafts(window, monkeypatch):
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    own = window.recovery.store.path(window.recovery.session_id)
    before = window.project.to_dict()
    candidate = window.recovery.store.write(uuid4(), before, capture_ui(window))
    monkeypatch.setattr(window, "_confirm_replace", lambda: False)
    assert not window.recovery.restore(candidate)
    assert own.exists() and candidate.exists()
    assert window.project.to_dict() == before


def test_actual_periodic_timeout_saves_without_focus_or_undo_change(window, qtbot):
    edit_raw(window, qtbot, "11")
    before = window.project.to_dict()
    history = copy.deepcopy(window.controller._undo)
    focus = QApplication.focusWidget()
    path = window.recovery.store.path(window.recovery.session_id)
    window.recovery.timer.setInterval(10)
    qtbot.waitUntil(path.exists, timeout=1000)
    window.recovery.timer.stop()
    assert window.project.to_dict() == before and window.controller._undo == history
    assert QApplication.focusWidget() is focus
    assert window.recovery.store.read(path)["ui_draft"]["pending_number"]["text"] == "11"


@pytest.mark.parametrize("button", ["Později", "Zahodit koncept", "Obnovit kopii"])
def test_real_recovery_dialog_later_discard_restore_are_distinct(window, qtbot, button):
    arrange_rectangle(window)
    window.controller.execute("Name", lambda p: setattr(p, "name", "Saved crash draft"))
    state = window.project.to_dict()
    ui = capture_ui(window)
    path = window.recovery.store.write(uuid4(), state, ui)
    window.controller.new("Current unsaved work")

    def choose():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QDialog)
        listing = dialog.findChild(QListWidget)
        assert listing.count() == 1 and "Saved crash draft" in listing.item(0).text()
        selected = next(b for b in dialog.findChildren(QPushButton) if b.text() == button)
        qtbot.mouseClick(selected, Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, choose)
    window.recovery.offer(startup=True)
    assert path.exists() == (button != "Zahodit koncept")
    if button == "Obnovit kopii":
        assert window.project.to_dict() == state and window.controller.recovered
    else:
        assert window.project.name == "Current unsaved work"


def test_corrupt_recovery_dialog_allows_explicit_discard_without_loading(window, qtbot):
    path = window.recovery.store.path(uuid4())
    path.parent.mkdir(exist_ok=True)
    path.write_text("broken json", encoding="utf-8")
    state = window.project.to_dict()

    def choose():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QDialog)
        buttons = {b.text(): b for b in dialog.findChildren(QPushButton)}
        assert not buttons["Obnovit kopii"].isEnabled()
        qtbot.mouseClick(buttons["Zahodit koncept"], Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, choose)
    window.recovery.offer(startup=True)
    assert not path.exists() and window.project.to_dict() == state


def test_actual_confirm_cancel_keeps_draft_and_ui_work(window, monkeypatch):
    arrange_rectangle(window)
    assert window.recovery.checkpoint()
    path = window.recovery.store.path(window.recovery.session_id)
    before = window.project.to_dict()
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Cancel)
    assert not AuthorMainWindow._confirm_replace(window)
    assert path.exists() and window.project.to_dict() == before


def test_actual_c_recovery_preserves_all_ids_frame_layout_slots_and_origin(window, tmp_path):
    from archpapercraft.authoring import load_project

    source = Path(__file__).resolve().parents[2] / (
        "docs/p2/implementation/evidence/c-cylinder-qt150-a5eedc9-run02/"
        "C-cylinder/C-cylinder.apcraft")
    original = tmp_path / "author.apcraft"
    original.write_bytes(source.read_bytes())
    loaded = load_project(original)
    window.controller.restore_recovery(loaded.to_dict(), original)
    owner = next(iter(loaded.curved_connectors.values())).owner_surface_id
    window.select_surface(owner)
    before = loaded.to_dict()
    raw = original.read_bytes()
    assert window.recovery.checkpoint()
    path = released(window)
    window.controller.new()
    assert window.recovery.restore(path)
    assert window.project.to_dict() == before and window.selected_surface == owner
    assert window.controller.copy_source_path == original
    assert original.read_bytes() == raw
    with pytest.raises(ValueError):
        window.controller.save(original)


def test_fresh_current_d_recovery_preserves_generation_and_two_page_locks(window, tmp_path):
    from test_segmented_surface import target

    project, sid, _, _ = target()
    preview = project.preview_segmented_variant(sid)
    assert preview["can_confirm"]
    vid = project.add_segmented_variant(sid, preview_digest=preview["preview_digest"])
    project.add_page()
    row = project.segmented_variants[vid].triangle_bindings[0]
    project.set_placement(row["part_id"], project.pages[1].id, 55, 90, 17,
                          position_locked=True, rotation_locked=True)
    window.controller.restore_recovery(project.to_dict())
    window.selected_generation = vid
    window.select_surface(sid)
    state = window.project.to_dict()
    assert window.recovery.checkpoint()
    path = released(window)
    window.controller.new()
    assert window.recovery.restore(path)
    assert window.project.to_dict() == state
    assert window.selected_generation == vid and window.selected_surface == sid


def test_second_loft_source_vertex_is_restored_exactly_without_nearest_id(window):
    from test_segmented_surface import target

    project, sid, a, b = target()
    window.controller.restore_recovery(project.to_dict())
    window.select_surface(sid)
    vertex = window.project.profiles[b].vertices[1].id
    window.select_vertex(b, vertex)
    selection = capture_ui(window)["selection"]
    assert selection["profile"] == a and selection["vertex"] == (b, vertex)
    assert window.recovery.checkpoint()
    path = released(window)
    window.controller.new()
    assert window.recovery.restore(path)
    assert capture_ui(window)["selection"] == selection
    assert window.vertex_choice.currentData() == (b, vertex)


def test_actual_crashed_author_window_recovers_valid_model_and_unconfirmed_number(window, tmp_path):
    script = """
import os, sys
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import archpapercraft.ui.author_window as module
from archpapercraft.ui.author_window import AuthorMainWindow
from archpapercraft.ui.author_recovery import setup_recovery
assert Path(module.__file__).resolve().is_relative_to(Path(os.environ['PYTHONPATH']).resolve())
app = QApplication([])
host = AuthorMainWindow(settings=QSettings(sys.argv[1], QSettings.Format.IniFormat))
if not hasattr(host, 'recovery'):
    host.recovery = setup_recovery(host)
host.show()
app.processEvents()
pid = host.controller.execute('Draw profile', lambda p:
    p.add_profile([[0,0],[2000,0]], closed=False))
host.select_profile(pid)
host.select_vertex(pid, host.project.profiles[pid].vertices[1].id)
host.vertex_x.setFocus()
app.processEvents()
host.vertex_x.lineEdit().setText('-')
assert host.recovery.checkpoint()
os._exit(0)
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
                       QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-c", script, window.settings.fileName()],
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    available = window.recovery.available()
    assert len(available) == 1
    assert window.recovery.restore(available[0][0])
    assert len(window.project.profiles) == 1
    profile = next(iter(window.project.profiles.values()))
    assert profile.vertices[1].point == [2000, 0]
    assert window.selected_vertex == (profile.id, profile.vertices[1].id)
    assert window.vertex_x.lineEdit().text() == "-"
    assert window.controller.recovered and window.controller.file_path is None
