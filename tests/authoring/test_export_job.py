"""Responsive real worker lifecycle and cancellation before atomic publication."""

import copy
import threading

import pytest
from PySide6.QtCore import QTimer

from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter.author_export import ExportCancelledError, export_all
from archpapercraft.ui.author_export_job import ExportProgressDialog


def snapshot():
    p = AuthorProject.new()
    profile = p.add_profile([[0, 0], [2000, 0], [2000, 1000], [0, 1000]])
    sid = p.add_surface(profile)
    p.recompute()
    p.set_placement(p.part_for_surface(sid), p.pages[0].id, 30, 30)
    return p.snapshot()


def test_real_writer_cancel_preserves_owned_and_foreign_bytes(tmp_path):
    data = snapshot()
    export_all(data, tmp_path)
    (tmp_path / "foreign.txt").write_bytes(b"author's work")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}

    def cancel(phase):
        if phase == "publish":
            raise ExportCancelledError("cancel")

    with pytest.raises(ExportCancelledError):
        export_all(data, tmp_path, checkpoint=cancel)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    assert not list(tmp_path.parent.glob(".author-export-*"))


@pytest.mark.ui
def test_worker_is_detached_and_ui_heartbeat_continues_until_cancel(qtbot, tmp_path):
    data = snapshot()
    before = copy.deepcopy(data)
    started, release = threading.Event(), threading.Event()
    observations = {}

    def slow(source, directory, *, checkpoint):
        observations["thread"] = threading.get_ident()
        source["name"] = "worker copy"
        checkpoint("verify")
        started.set()
        assert release.wait(5)
        checkpoint("publish")
        raise AssertionError("cancelled worker cannot publish")

    dialog = ExportProgressDialog(data, tmp_path, function=slow)
    qtbot.addWidget(dialog)
    dialog.show()
    beats = []
    timer = QTimer(dialog)
    timer.timeout.connect(lambda: beats.append(1))
    timer.start(5)
    qtbot.waitUntil(started.is_set)
    qtbot.waitUntil(lambda: len(beats) >= 3)
    assert observations["thread"] != threading.get_ident()
    assert data == before
    dialog.reject()  # Esc/close requests cancellation; dialog remains pending.
    assert not dialog._finished and dialog.isVisible()
    assert not dialog.cancel_button.isEnabled()
    release.set()
    qtbot.waitUntil(lambda: dialog._finished)
    assert dialog.cancelled and dialog.result_paths is None


@pytest.mark.ui
def test_late_cancel_reports_completed_output_truthfully(qtbot, tmp_path):
    started, release = threading.Event(), threading.Event()

    def publishing(source, directory, *, checkpoint):
        checkpoint("publish")
        started.set()
        assert release.wait(5)
        return [directory / "model.pdf"]

    dialog = ExportProgressDialog(snapshot(), tmp_path, function=publishing)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(started.is_set)
    dialog.request_cancel()
    release.set()
    qtbot.waitUntil(lambda: dialog._finished)
    assert dialog.result_paths == [tmp_path / "model.pdf"]
    assert dialog.finished_during_cancel and not dialog.cancelled


@pytest.mark.ui
def test_real_worker_writes_vectors_from_the_original_snapshot(qtbot, tmp_path):
    data = snapshot()
    before = copy.deepcopy(data)
    dialog = ExportProgressDialog(data, tmp_path)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(lambda: dialog._finished, timeout=10000)
    assert dialog.error is None and len(dialog.result_paths) == 2
    assert all(p.is_file() for p in dialog.result_paths)
    assert data == before
