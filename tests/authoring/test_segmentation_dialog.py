"""Qt interactions with the real D preview/commands, not a novice/native proof."""

import copy
import threading

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_segmentation import SegmentedVariantDialog

pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def source_state():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [40, 0]], closed=False)
    b = p.add_profile(
        [[0, 0], [40, 20]],
        closed=False,
        plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    s = p.add_loft(
        a,
        b,
        correspondences=[
            dict(
                first_segment_id=p.profiles[a].segments[0].id,
                second_segment_id=p.profiles[b].segments[0].id,
                first_interval=[0, 1],
                second_interval=[0, 1],
            )
        ],
    )
    return p.to_dict(), s


def dialog(qtbot, source_state):
    state, sid = source_state
    p = AuthorProject.from_dict(copy.deepcopy(state))
    widget = SegmentedVariantDialog(p, sid)
    qtbot.addWidget(widget)
    widget.show()
    return widget, p, sid


def calculate(qtbot, widget):
    qtbot.mouseClick(widget.preview_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: widget._preview is not None and widget._running is None, timeout=60000)


def test_real_preview_explicit_confirmation_detached_geometry_and_single_undo(qtbot, source_state):
    w, p, sid = dialog(qtbot, source_state)
    before = p.to_dict()
    button = w.buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert not button.isEnabled() and "náhled" in w.feedback.text()
    qtbot.mouseClick(w.help_button, Qt.MouseButton.LeftButton)
    assert not w.guidance.isVisible()
    qtbot.mouseClick(w.help_button, Qt.MouseButton.LeftButton)
    assert w.guidance.isVisible()
    calculate(qtbot, w)
    assert p.to_dict() == before
    assert "64 samostatných" in w.feedback.text()
    assert "0.15625" in w.feedback.text() and "84 párovaných" in w.feedback.text()
    assert len(w.view.meshes[1]["triangles"]) == 64
    assert not button.isEnabled()
    # An altered display mesh cannot be injected as application geometry.
    w.view.meshes[1]["vertices"][0][0] = 999
    qtbot.mouseClick(w.confirm, Qt.MouseButton.LeftButton)
    assert button.isEnabled()
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert w.result() == QDialog.DialogCode.Accepted
    c = AuthorController()
    c.project = p
    variant = c.execute("Potvrdit odvozené díly", w.apply)
    assert p.segmented_variants[variant].target_surface_id == sid
    assert p.surfaces[sid].kind == "ruled_loft" and p.loft_status(sid)["status"] != "EXACT"
    assert all(
        abs(x) < 999
        for r in p.segmented_variants[variant].triangle_bindings
        for row in p.world_geometry(r["surface_id"])["vertices"]
        for x in row
    )
    c.undo()
    assert c.project.to_dict() == before
    c.redo()
    assert variant in c.project.segmented_variants


def test_uncommitted_numeric_input_invalidates_and_invalid_input_blocks(qtbot, source_state):
    w, p, _ = dialog(qtbot, source_state)
    calculate(qtbot, w)
    qtbot.mouseClick(w.confirm, Qt.MouseButton.LeftButton)
    edit = w.deviation.lineEdit()
    edit.setFocus()
    edit.selectAll()
    qtbot.keyClicks(edit, "0" + w.deviation.locale().decimalPoint() + "125")
    w.accept()  # No Enter or focus change before the command.
    assert w.result() != QDialog.DialogCode.Accepted and w._preview is None
    assert w.deviation.value() == 0.125
    edit.setText("-")
    w.request_preview()
    assert w._running is None and w._preview is None
    assert "neplatnou" in w.feedback.text() and not p.segmented_variants


def test_source_changed_after_preview_is_blocked_and_original_is_preserved(qtbot, source_state):
    w, p, sid = dialog(qtbot, source_state)
    calculate(qtbot, w)
    qtbot.mouseClick(w.confirm, Qt.MouseButton.LeftButton)
    p.set_transform(sid, [1, 0, 0], [0, 0, 0])
    changed = p.to_dict()
    w.accept()
    assert w.result() != QDialog.DialogCode.Accepted
    assert w._preview is None and "změnil" in w.feedback.text()
    assert p.to_dict() == changed and not p.segmented_variants


def test_hard_budget_failure_never_enables_confirm(qtbot, source_state):
    w, p, _ = dialog(qtbot, source_state)
    w.cells.setValue(1)
    w.deviation.setValue(0.000001)
    qtbot.mouseClick(w.preview_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: w._running is None, timeout=60000)
    assert w._preview is None and "Mez není doložená" in w.feedback.text()
    qtbot.mouseClick(w.confirm, Qt.MouseButton.LeftButton)
    assert not w.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert not p.segmented_variants


def test_cancel_running_worker_does_not_mutate_or_publish_and_latest_request_wins(
    qtbot, source_state, monkeypatch
):
    entered, release = threading.Event(), threading.Event()
    original = AuthorProject.preview_segmented_variant
    threads, calls = [], []

    def delayed(project, sid, **parameters):
        threads.append(threading.get_ident())
        calls.append(parameters)
        if len(calls) == 1:
            entered.set()
            assert release.wait(20)
        return original(project, sid, **parameters)

    monkeypatch.setattr(AuthorProject, "preview_segmented_variant", delayed)
    w, p, _ = dialog(qtbot, source_state)
    before = p.to_dict()
    w.request_preview()
    qtbot.waitUntil(entered.is_set)
    w.deviation.setValue(0.5)
    w.request_preview()
    w.deviation.setValue(0.25)
    w.request_preview()
    release.set()
    qtbot.waitUntil(lambda: w._preview is not None and w._running is None, timeout=60000)
    assert [c["max_deviation_mm"] for c in calls] == [0.25, 0.25]
    assert all(t != threading.get_ident() for t in threads)
    assert p.to_dict() == before
    w.request_preview()
    w.reject()
    qtbot.waitUntil(lambda: w._running is None, timeout=60000)
    assert w.result() == QDialog.DialogCode.Rejected and w._accepted is None
    assert p.to_dict() == before
