"""Independent real-core async UI invariants; offscreen is not native desktop proof."""

import math
import threading
from copy import deepcopy
from fractions import Fraction

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
from test_curve_workspace import circle
from test_curved_subdivision_workspace import dialog, ready, source
from test_workspace import window as _window_fixture

from archpapercraft.ui.author_subdivision import SubdivisionDialog, _curve_preview

pytestmark = pytest.mark.ui
window = _window_fixture


def measured_distance(kind, parameter):
    value = float(parameter)
    return math.pi * 10 * value if kind == "arc" else 8 * value**3 - 12 * value**2 + 12 * value


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_real_core_latest_accept_cannot_apply_the_initial_or_intermediate_request(qtbot, kind):
    project, pid, eid = source(kind)
    before = deepcopy(project.to_dict())
    entered, release = threading.Event(), threading.Event()
    requests = []

    def controlled(clone, profile_id, segment_id, request):
        assert clone is not project
        requests.append(deepcopy(request))
        if len(requests) == 1:
            entered.set()
            assert release.wait(20)
        return _curve_preview(clone, profile_id, segment_id, request)

    widget = dialog(qtbot, project, pid, eid, controlled)
    try:
        qtbot.waitUntil(entered.is_set)
        widget.distance.setValue(3)
        widget.preview()
        widget.distance.setValue(7)
        widget.preview()
        widget.accept()  # Explicit acceptance while the older detached solve is blocked.
        assert widget.result_spec is None
        assert not widget.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    finally:
        release.set()
    qtbot.waitUntil(lambda: widget.result() == QDialog.DialogCode.Accepted, timeout=30000)
    assert len(requests) == 2 and requests[0]["distance"] is None
    assert requests[1]["distance"] == 7
    assert isinstance(widget.result_spec["parameter"], Fraction)
    assert measured_distance(kind, widget.result_spec["parameter"]) == pytest.approx(7, abs=0.0011)
    assert project.to_dict() == before


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_real_core_cancel_keeps_heartbeat_and_discards_delayed_public_result(qtbot, kind):
    project, pid, eid = source(kind)
    before = deepcopy(project.to_dict())
    entered, release = threading.Event(), threading.Event()

    def controlled(clone, profile_id, segment_id, request):
        entered.set()
        assert release.wait(20)
        return _curve_preview(clone, profile_id, segment_id, request)

    widget = dialog(qtbot, project, pid, eid, controlled)
    try:
        qtbot.waitUntil(entered.is_set)
        heartbeat = []
        QTimer.singleShot(0, lambda: heartbeat.append(True))
        qtbot.waitUntil(lambda: bool(heartbeat), timeout=1000)
        qtbot.mouseClick(
            widget.buttons.button(QDialogButtonBox.StandardButton.Cancel), Qt.MouseButton.LeftButton
        )
        assert not widget.isVisible()
    finally:
        release.set()
    qtbot.waitUntil(lambda: widget._running is None, timeout=30000)
    assert widget.result() == QDialog.DialogCode.Rejected
    assert widget.result_spec is None and widget._packet is None
    assert project.to_dict() == before


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_real_core_rejects_typed_invalid_distance_after_valid_preview(qtbot, kind):
    project, pid, eid = source(kind)
    before = deepcopy(project.to_dict())
    widget = dialog(qtbot, project, pid, eid)
    ready(qtbot, widget)
    widget.distance.lineEdit().selectAll()
    qtbot.keyClicks(widget.distance.lineEdit(), "-")
    widget.compute.setFocus()
    widget.accept()
    assert widget.result_spec is None and widget._packet is None
    assert widget.distance.lineEdit().text() == "-"
    assert not widget.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert "Opravte" in widget.feedback.text()
    widget.reject()
    assert project.to_dict() == before


def test_second_arc_split_keeps_new_vertex_selected_in_host_and_visible_properties(window, qtbot):
    sid = circle(window, qtbot)
    pid = window.project.surfaces[sid].profile_id
    window.curve_choice.setCurrentIndex(1)
    profile = window.project.profiles[pid]
    before_vertices = {vertex.id for vertex in profile.vertices}
    selected = window.curve_choice.currentData()
    assert selected == (pid, profile.segments[1].id)

    def split_current():
        current = QApplication.activeModalWidget()
        assert isinstance(current, SubdivisionDialog)
        current.distance.setValue(1)
        current.preview()
        ready(qtbot, current)
        qtbot.mouseClick(
            current.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
        )

    QTimer.singleShot(0, split_current)
    window.actions["split_profile"].trigger()
    assert not window._test_warnings
    created = {vertex.id for vertex in window.project.profiles[pid].vertices} - before_vertices
    assert len(created) == 1
    new_vertex = created.pop()
    assert window.selected_vertex == (pid, new_vertex)
    assert window.vertex_choice.currentData() == (pid, new_vertex)
