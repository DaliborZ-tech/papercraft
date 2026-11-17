"""Separate crash drafts, atomic failures and unsaved-copy controller restoration."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

import archpapercraft.authoring.recovery as recovery_module
from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring.recovery import RecoveryStore


def test_recovery_import_is_from_own_checkout():
    assert Path(recovery_module.__file__).resolve() == (
        Path(__file__).resolve().parents[2] / "src/archpapercraft/authoring/recovery.py")
    root = Path(__file__).resolve().parents[2] / "src"
    for name, module in list(sys.modules.items()):
        if name.startswith("archpapercraft") and getattr(module, "__file__", None):
            assert Path(module.__file__).resolve().is_relative_to(root), (name, module.__file__)


def test_atomic_replace_failure_keeps_last_draft_origin_and_foreign(tmp_path, monkeypatch):
    store = RecoveryStore(tmp_path / "drafts")
    identifier = uuid4()
    original, foreign = tmp_path / "model.apcraft", tmp_path / "foreign.json"
    original.write_bytes(b"last valid user file")
    foreign.write_bytes(b"unrelated")
    path = store.write(identifier, {"name": "Last draft"}, {}, original)
    before = path.read_bytes()

    def fail(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(recovery_module.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        store.write(identifier, {"name": "New edit"}, {}, original)
    assert path.read_bytes() == before
    assert original.read_bytes() == b"last valid user file"
    assert foreign.read_bytes() == b"unrelated"
    assert list(store.directory.iterdir()) == [path]


def test_bad_serialization_and_foreign_paths_preserve_all_files(tmp_path):
    store = RecoveryStore(tmp_path / "drafts")
    identifier = uuid4()
    path = store.write(identifier, {"name": "valid"}, {})
    before = path.read_bytes()
    with pytest.raises(ValueError):
        store.write(identifier, {"number": float("nan")}, {})
    foreign = tmp_path / (str(uuid4()) + ".recovery.json")
    foreign.write_bytes(b"foreign")
    for operation in (store.read, store.discard):
        with pytest.raises(ValueError):
            operation(foreign)
    assert foreign.read_bytes() == b"foreign" and path.read_bytes() == before


@pytest.mark.parametrize("content", ['{"application":"x"}', '{"a":1,"a":2}',
                                     '{"a":NaN}', '{"a":Infinity}', '{'])
def test_corrupt_draft_is_rejected_and_preserved(tmp_path, content):
    store = RecoveryStore(tmp_path)
    path = store.path(uuid4())
    path.write_text(content, encoding="utf-8")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        store.read(path)
    assert path.read_text("utf-8") == content


def test_restore_unsaved_copy_retains_geometry_layout_ids_and_original(tmp_path):
    controller = AuthorController()
    controller.new()
    pid = controller.execute("Profile", lambda p: p.add_profile([[0, 0], [20, 0]], closed=False))
    original = tmp_path / "own.apcraft"
    controller.save(original)
    old_bytes = original.read_bytes()
    controller.execute("Name", lambda p: setattr(p, "name", "Recovered edit"))
    state = controller.project.to_dict()
    controller.new()
    controller.restore_recovery(state, original)
    assert controller.project.to_dict() == state and pid in controller.project.profiles
    assert controller.dirty and controller.file_path is None and controller.recovered
    assert not controller.can_undo and not controller.can_redo
    with pytest.raises(ValueError):
        controller.save(original)
    assert original.read_bytes() == old_bytes
    controller.save(tmp_path / "recovered-copy.apcraft")
    assert not controller.dirty and not controller.recovered
    assert original.read_bytes() == old_bytes


def test_invalid_restore_does_not_replace_current_work():
    controller = AuthorController()
    controller.new("Keep this work")
    controller.execute("Name", lambda p: setattr(p, "name", "New work"))
    before = controller.project.to_dict()
    with pytest.raises(ValueError):
        controller.restore_recovery({"application": "broken"})
    assert controller.project.to_dict() == before and controller.can_undo


def test_document_events_only_after_success(tmp_path):
    controller = AuthorController()
    events = []
    controller.on_document_event = events.append
    controller.new()
    assert events == ["replaced"]
    with pytest.raises(ValueError):
        controller.save()
    with pytest.raises(OSError):
        controller.open(tmp_path / "missing.apcraft")
    assert events == ["replaced"]
    controller.save(tmp_path / "own.apcraft")
    controller.open(tmp_path / "own.apcraft")
    assert events == ["replaced", "saved", "replaced"]


def test_crashed_process_leaves_readable_draft_and_reclaimable_dead_lock(tmp_path):
    from PySide6.QtCore import QLockFile

    identifier = str(uuid4())
    script = """
import os, sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QLockFile
import archpapercraft.authoring.recovery as module
from archpapercraft.authoring.recovery import RecoveryStore
assert Path(module.__file__).resolve().is_relative_to(Path(os.environ['PYTHONPATH']).resolve())
app=QCoreApplication([])
store=RecoveryStore(sys.argv[1])
store.directory.mkdir(parents=True, exist_ok=True)
lock=QLockFile(str(store.path(sys.argv[2]))+'.lock')
lock.setStaleLockTime(0)
assert lock.tryLock(0)
store.write(sys.argv[2], {'name':'crash survived'}, {})
os._exit(0)
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), identifier],
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    store = RecoveryStore(tmp_path)
    assert store.read(store.path(identifier))["document"]["name"] == "crash survived"
    lock = QLockFile(str(store.path(identifier)) + ".lock")
    lock.setStaleLockTime(0)
    assert lock.tryLock(0)
    lock.unlock()
