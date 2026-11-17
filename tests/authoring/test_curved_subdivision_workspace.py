"""Offscreen AU13 components; neither native desktop nor novice-user evidence."""

import copy
import math
import threading
import time
from fractions import Fraction

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
from test_curve_workspace import circle
from test_workspace import arrange_rectangle
from test_workspace import window as _window_fixture

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_subdivision import SubdivisionDialog

pytestmark = pytest.mark.ui
window = _window_fixture


def source(kind="arc"):
    project = AuthorProject(scale=1)
    if kind == "arc":
        spec = {"kind": "arc", "start": [10, 0], "end": [-10, 0],
                "data": {"center": [0, 0], "sweep_deg": 180}}
    else:
        spec = {"kind": "cubic", "start": [0, 0], "end": [4, 0],
                "data": {"control1": [0, 4], "control2": [4, 4]}}
    pid = project.add_profile(segments=[spec], closed=False)
    return project, pid, project.profiles[pid].segments[0].id


def packet(project, pid, eid, request):
    """Scheduling dependency only; this does not claim a successful geometric split."""
    distance = request.get("distance") or 15
    return {"request": copy.deepcopy(request),
            "parameters": {"segment_id": eid, "parameter": Fraction(1, 2)},
            "profile": copy.deepcopy(project.profiles[pid]),
            "length": {"status": "CERTIFIED", "lower": 30, "upper": 30,
                       "units": "model_mm"},
            "distance": distance,
            "measurement": {"status": "CERTIFIED", "parameter": Fraction(1, 2),
                            "actual_error_bound_model_mm": 0,
                            "distance_bounds_model_mm": [distance, distance]},
            "split_point": [0, 10]}


def dialog(qtbot, project, pid, eid, callback=None):
    widget = SubdivisionDialog(project, pid, eid, preview_function=callback)
    qtbot.addWidget(widget)
    widget.show()
    return widget


def ready(qtbot, widget):
    qtbot.waitUntil(lambda: widget._running is None and widget._packet is not None, timeout=30000)


def test_curve_worker_keeps_gui_responsive_cancel_discards_late_result(qtbot):
    project, pid, eid = source()
    before = project.to_dict()
    entered, release = threading.Event(), threading.Event()

    def blocked(clone, profile_id, edge_id, request):
        assert clone is not project
        entered.set()
        release.wait(10)
        clone.profiles[profile_id].name = "Detached only"
        return packet(clone, profile_id, edge_id, request)

    widget = dialog(qtbot, project, pid, eid, blocked)
    try:
        qtbot.waitUntil(entered.is_set)
        heartbeat = []
        QTimer.singleShot(0, lambda: heartbeat.append(True))
        qtbot.waitUntil(lambda: bool(heartbeat), timeout=1000)
        started = time.monotonic()
        widget.reject()
        assert time.monotonic() - started < .5
        assert widget.result() == QDialog.DialogCode.Rejected
    finally:
        release.set()
        qtbot.waitUntil(lambda: widget._running is None, timeout=5000)
    assert widget._packet is None and widget.result_spec is None
    assert project.to_dict() == before


def test_curve_worker_retains_only_latest_request_and_never_accepts_obsolete_result(qtbot):
    project, pid, eid = source()
    entered, release = threading.Event(), threading.Event()
    requests = []

    def blocked(clone, profile_id, edge_id, request):
        requests.append(copy.deepcopy(request))
        if len(requests) == 1:
            entered.set()
            release.wait(10)
        return packet(clone, profile_id, edge_id, request)

    widget = dialog(qtbot, project, pid, eid, blocked)
    try:
        qtbot.waitUntil(entered.is_set)
        widget.distance.setValue(3)
        widget.preview()
        widget.distance.setValue(7)
        widget.preview()
        assert widget._packet is None
        assert not widget.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    finally:
        release.set()
    ready(qtbot, widget)
    assert len(requests) == 2 and requests[-1]["distance"] == 7
    assert widget.distance.value() == 7
    widget.reject()


def test_external_source_change_blocks_preview_and_late_apply(qtbot):
    project, pid, eid = source()
    entered, release = threading.Event(), threading.Event()

    def blocked(clone, profile_id, edge_id, request):
        entered.set()
        release.wait(10)
        return packet(clone, profile_id, edge_id, request)

    widget = dialog(qtbot, project, pid, eid, blocked)
    try:
        qtbot.waitUntil(entered.is_set)
        project.profiles[pid].name = "Source changed"
        widget._source_changed()
        assert not widget.compute.isEnabled()
        assert "znovu" in widget.feedback.text()
        widget.accept()
        assert widget.result_spec is None
    finally:
        release.set()
        qtbot.waitUntil(lambda: widget._running is None, timeout=5000)
    assert widget._packet is None
    widget.reject()


def test_raw_invalid_curve_distance_survives_focus_out_and_cancel(qtbot):
    project, pid, eid = source()
    before = project.to_dict()
    widget = dialog(qtbot, project, pid, eid, packet)
    ready(qtbot, widget)
    widget.distance.setFocus()
    widget.distance.lineEdit().selectAll()
    qtbot.keyClicks(widget.distance.lineEdit(), "-")
    widget.compute.setFocus()  # Qt may correct the displayed spinbox text.
    widget.accept()
    assert widget.result_spec is None
    assert widget.distance.lineEdit().text() == "-"
    assert "Opravte" in widget.feedback.text()
    widget.reject()
    assert project.to_dict() == before


def test_unresolved_length_remains_repairable_without_a_split_or_accept(qtbot):
    project, pid, eid = source("cubic")
    before = project.to_dict()

    def unresolved(*_args):
        raise ValueError("DISTANCE_UNRESOLVED: vyberte kratší úsek.")

    widget = dialog(qtbot, project, pid, eid, unresolved)
    qtbot.waitUntil(lambda: widget._running is None and "DISTANCE_UNRESOLVED" in
                   widget.feedback.text(), timeout=5000)
    assert not widget.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert widget.compute.isEnabled() and widget.distance.isEnabled()
    assert project.to_dict() == before
    widget.reject()


@pytest.mark.parametrize("fault", ["selection", "parameter", "length", "error"])
def test_malformed_response_does_not_enable_accept_or_publish_a_split(qtbot, fault):
    project, pid, eid = source()
    before = project.to_dict()

    def malformed(clone, profile_id, edge_id, request):
        result = packet(clone, profile_id, edge_id, request)
        if fault == "selection":
            result["parameters"]["segment_id"] = "wrong source"
        elif fault == "parameter":
            result["parameters"]["parameter"] = Fraction(1, 3)
        elif fault == "length":
            result["length"]["lower"] = float("nan")
        else:
            result["measurement"]["actual_error_bound_model_mm"] = 10
        return result

    widget = dialog(qtbot, project, pid, eid, malformed)
    qtbot.waitUntil(lambda: widget._running is None and "nelze použít" in
                   widget.feedback.text(), timeout=5000)
    assert widget._packet is None
    assert not widget.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert project.to_dict() == before
    widget.reject()


def test_curve_choice_failed_main_numeric_preflight_rolls_back_visible_and_owner_context(
    window, qtbot
):
    sid = circle(window, qtbot)
    pid = window.project.surfaces[sid].profile_id
    profile = window.project.profiles[pid]
    window.select_vertex(pid, profile.vertices[0].id)
    pair = window.curve_choice.currentData()
    selection = (window.selected_surface, window.selected_profile, window.selected_edge,
                 window.selected_vertex, window.tree.currentItem())
    before = window.project.to_dict()
    window.vertex_x.setFocus()
    window.vertex_x.lineEdit().setText("-")
    assert not window.vertex_x.hasAcceptableInput()
    window.curve_choice.setCurrentIndex(1)
    assert window.curve_choice.currentData() == pair
    assert (window.selected_surface, window.selected_profile, window.selected_edge,
            window.selected_vertex, window.tree.currentItem()) == selection
    assert window.vertex_x.lineEdit().text() == "-"
    assert window.project.to_dict() == before


def test_curve_choice_commits_valid_pending_number_then_keeps_requested_source(window, qtbot):
    sid = arrange_rectangle(window)
    pid = window.project.surfaces[sid].profile_id
    profile = window.project.profiles[pid]
    vertex_id = profile.vertices[0].id
    window.select_vertex(pid, vertex_id)
    requested = window.curve_choice.itemData(1)
    before = len(window.controller._undo)
    window.vertex_x.setFocus()
    window.vertex_x.lineEdit().selectAll()
    qtbot.keyClicks(window.vertex_x.lineEdit(), "1")
    window.curve_choice.setCurrentIndex(1)
    assert not window._test_warnings
    assert len(window.controller._undo) == before + 1
    assert window.project.profiles[pid].vertex(vertex_id).point[0] == 1000
    assert window.curve_choice.currentData() == requested, (
        requested, [window.curve_choice.itemData(i) for i in range(window.curve_choice.count())],
        window.selected_surface, window.selected_profile, window.selected_edge)
    assert window.selected_edge == (sid, requested[1])
    assert window.selected_vertex == (
        pid, window.project.profiles[pid].segment(requested[1]).start_vertex_id)


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_actual_public_core_curve_split_uses_measured_length_not_chord_fraction(qtbot, kind):
    project, pid, eid = source(kind)
    before = project.to_dict()
    widget = dialog(qtbot, project, pid, eid)
    ready(qtbot, widget)
    distance = math.pi * 10 / 3 if kind == "arc" else 2
    widget.distance.lineEdit().selectAll()
    qtbot.keyClicks(widget.distance.lineEdit(), widget.distance.locale().toString(
        float(distance), "f", widget.distance.decimals()))
    qtbot.mouseClick(widget.compute, Qt.MouseButton.LeftButton)  # No Return first: C05.
    ready(qtbot, widget)
    qtbot.mouseClick(widget.buttons.button(QDialogButtonBox.StandardButton.Ok),
                     Qt.MouseButton.LeftButton)
    assert widget.result() == QDialog.DialogCode.Accepted
    t = widget.result_spec["parameter"]
    assert isinstance(t, Fraction)
    if kind == "arc":
        assert float(t) == pytest.approx(1 / 3, abs=5e-7)
    else:
        # Independently integrated speed of this source: L(t)=8t³-12t²+12t.
        measured = 8 * float(t)**3 - 12 * float(t)**2 + 12 * float(t)
        assert measured == pytest.approx(2, abs=.0011 / project.scale)
        assert abs(float(t) - .25) > .03  # Distance / total length is not its parameter.
    assert project.to_dict() == before
    assert "Délka po obrysu" in widget.dimensions.text()
    if kind == "arc":
        assert "Poloměr" in widget.dimensions.text()


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_actual_host_split_inverse_merge_undo_recompute_and_save_open_keep_layout(
    window, qtbot, tmp_path, kind
):
    project, pid, _ = source(kind)
    first = project.profiles[pid].segments[0]
    original = project.profiles[pid]
    a = original.vertex(first.start_vertex_id).point
    b = original.vertex(first.end_vertex_id).point
    closing = ({"kind": "arc", "start": b, "end": a,
                "data": {"center": [0, 0], "sweep_deg": 180}}
               if kind == "arc" else {"kind": "line", "start": b, "end": a})
    profile_id = project.add_profile(segments=[{"kind": first.kind, "start": a, "end": b,
                                              "data": first.data}, closing], closed=True)
    sid = project.add_surface(profile_id)
    project.recompute()
    part_id = project.part_for_surface(sid)
    page = project.add_page()
    project.set_placement(part_id, page, 65, 70, 27, position_locked=True, rotation_locked=True)
    frame, layout = copy.deepcopy(project.parts[part_id].frame), copy.deepcopy(
        project.placements[part_id])
    window.controller.project = project
    window.refresh()
    window.select_surface(sid)
    assert window.actions["split_profile"].isEnabled()
    before = window.project.to_dict()
    undo_count = len(window.controller._undo)

    def split():
        current = QApplication.activeModalWidget()
        assert isinstance(current, SubdivisionDialog) and not current.joining
        current.distance.setValue((math.pi * 10 / 3 if kind == "arc" else 2) /
                                  window.unit_factor)
        current.preview()
        ready(qtbot, current)
        qtbot.mouseClick(current.buttons.button(QDialogButtonBox.StandardButton.Ok),
                         Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, split)
    window.actions["split_profile"].trigger()
    assert not window._test_warnings
    assert len(window.controller._undo) == undo_count + 1
    assert len(window.project.profiles[profile_id].segments) == 3
    assert window.selected_profile == profile_id
    assert window.project.parts[part_id].stale
    changed = window.project.to_dict()
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before
    window.actions["redo"].trigger()
    assert window.project.to_dict() == changed
    window.actions["recompute"].trigger()
    qtbot.waitUntil(lambda: not window.project.parts[part_id].stale, timeout=30000)
    assert window.project.parts[part_id].frame == frame
    assert window.project.placements[part_id] == layout
    path = tmp_path / f"curved-{kind}-split.apcraft"
    window.controller.save(path)
    saved = window.project.to_dict()
    window.controller.open(path)
    assert window.project.to_dict() == saved
    window.select_surface(sid)
    window.curve_choice.setCurrentIndex(0)
    assert window.actions["merge_profile"].isEnabled()

    def merge():
        current = QApplication.activeModalWidget()
        assert isinstance(current, SubdivisionDialog) and current.joining
        ready(qtbot, current)
        assert len(current.choices.selectedItems()) == 2
        qtbot.mouseClick(current.buttons.button(QDialogButtonBox.StandardButton.Ok),
                         Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, merge)
    window.actions["merge_profile"].trigger()
    assert not window._test_warnings
    assert len(window.project.profiles[profile_id].segments) == 2
    assert not window.actions["merge_profile"].isEnabled()
    assert window.project.placements[part_id] == layout


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_actual_public_core_cancel_during_new_preview_keeps_original_source(qtbot, kind):
    project, pid, eid = source(kind)
    before = project.to_dict()
    widget = dialog(qtbot, project, pid, eid)
    ready(qtbot, widget)
    widget.distance.setValue(2)
    assert widget.preview()
    widget.reject()
    qtbot.waitUntil(lambda: widget._running is None, timeout=30000)
    assert widget.result() == QDialog.DialogCode.Rejected
    assert widget.result_spec is None and widget._packet is None
    assert project.to_dict() == before


def test_actual_inverse_merge_rejects_nonadjacent_children_without_fitting_or_mutation(qtbot):
    project, pid, eid = source()
    result = project.split_profile_segment(pid, eid, Fraction(1, 3))
    project.split_profile_segment(pid, result["segment_ids"][1], Fraction(1, 2))
    first = project.profiles[pid].segments[0].id
    before = project.to_dict()
    widget = SubdivisionDialog(project, pid, first, joining=True)
    qtbot.addWidget(widget)
    widget.show()
    assert widget.choices.count() == 3
    widget.choices.item(1).setSelected(False)
    widget.preview()
    qtbot.waitUntil(lambda: widget._running is None and "nelze použít" in
                   widget.feedback.text(), timeout=30000)
    assert widget._packet is None
    assert not widget.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert widget.compute.isEnabled() and widget.choices.isEnabled()
    assert project.to_dict() == before
    widget.reject()
