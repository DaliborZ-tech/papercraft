"""Independent loss-prevention oracles; offscreen, never a novice/native proof."""

import copy
from uuid import uuid4

import pytest
from PySide6.QtCore import QSettings

import archpapercraft.authoring.recovery as store_module
from archpapercraft.ui.author_recovery import capture_ui
from archpapercraft.ui.author_window import AuthorMainWindow


@pytest.fixture
def windows(qtbot, tmp_path, monkeypatch):
    result = []
    for _ in range(2):
        host = AuthorMainWindow(settings=QSettings(str(tmp_path / "own.ini"), QSettings.IniFormat))
        qtbot.addWidget(host)
        monkeypatch.setattr(host, "_confirm_replace", lambda: True)
        host.show()
        result.append(host)
    qtbot.wait(10)
    yield result
    for host in result:
        host.recovery.finished_close()


def author(host, name):
    host.controller.execute("Own named outline", lambda p: p.add_profile(
        [[0, 0], [3000, 0], [3000, 2000], [0, 2000]], name=name))


def test_two_live_windows_never_offer_or_steal_each_others_drafts(windows):
    first, second = windows
    author(first, "First author")
    assert first.recovery.checkpoint()
    path = first.recovery.store.path(first.recovery.session_id)
    before = path.read_bytes()
    assert second.recovery.available() == []
    with pytest.raises(ValueError):
        second.recovery.restore(path)
    assert path.read_bytes() == before
    author(second, "Second author")
    assert second.recovery.checkpoint()
    assert first.recovery.available() == second.recovery.available() == []
    assert first.recovery.timer.isActive() and second.recovery.timer.isActive()


def test_invalid_selection_cannot_replace_live_work_or_erase_its_checkpoint(windows):
    host = windows[0]
    author(host, "Current work")
    assert host.recovery.checkpoint()
    own = host.recovery.store.path(host.recovery.session_id)
    own_bytes, state = own.read_bytes(), copy.deepcopy(host.project.to_dict())
    history = copy.deepcopy(host.controller._undo)
    ui = capture_ui(host)
    ui["selection"]["surface"] = str(uuid4())
    bad = host.recovery.store.write(uuid4(), state, ui)
    bad_bytes = bad.read_bytes()
    with pytest.raises(ValueError):
        host.recovery.restore(bad)
    assert host.project.to_dict() == state and host.controller._undo == history
    assert own.read_bytes() == own_bytes and bad.read_bytes() == bad_bytes


def test_failed_periodic_replace_keeps_original_previous_draft_and_history(windows, tmp_path,
                                                                       monkeypatch):
    host = windows[0]
    author(host, "Saved work")
    original = tmp_path / "author.apcraft"
    host.controller.save(original)
    original_bytes = original.read_bytes()
    host.controller.execute("Uncommitted-to-disk work", lambda p: setattr(p, "name", "New name"))
    assert host.recovery.checkpoint()
    path = host.recovery.store.path(host.recovery.session_id)
    old_draft = path.read_bytes()
    state, history = host.project.to_dict(), copy.deepcopy(host.controller._undo)
    monkeypatch.setattr(store_module.os, "replace", lambda *_: (_ for _ in ()).throw(
        OSError("simulated full disk")))
    assert not host.recovery.checkpoint()
    assert path.read_bytes() == old_draft and original.read_bytes() == original_bytes
    assert host.project.to_dict() == state and host.controller._undo == history
    assert host.controller.dirty and "simulated full disk" in host.statusBar().currentMessage()


def test_invalid_recovery_json_and_foreign_file_are_preserved(windows, tmp_path):
    host = windows[0]
    author(host, "Current")
    state = host.project.to_dict()
    bad = host.recovery.store.path(uuid4())
    bad.parent.mkdir(exist_ok=True)
    bad.write_bytes(b'{"document":NaN}')
    foreign = tmp_path / "unrelated.txt"
    foreign.write_bytes(b"unrelated content")
    for path in (bad, foreign):
        before = path.read_bytes()
        with pytest.raises(ValueError):
            host.recovery.restore(path)
        assert path.read_bytes() == before and host.project.to_dict() == state
