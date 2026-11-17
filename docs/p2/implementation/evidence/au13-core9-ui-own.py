"""Independent measured-curve and late-worker UI review, with actual public core."""

import copy
import subprocess
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui import author_subdivision as module
from archpapercraft.ui.author_subdivision import SubdivisionDialog, _curve_preview

ROOT = Path(__file__).resolve().parents[4]
PIN = "5415e2bc45f0a073d202144f1281557377afbc61"
assert Path(module.__file__).resolve() == ROOT / "src/archpapercraft/ui/author_subdivision.py"
for name in ("ui/author_subdivision.py", "ui/author_window.py", "authoring/loft_surface.py",
             "authoring/profile_subdivision.py"):
    path = "src/archpapercraft/" + name
    assert (ROOT / path).read_bytes().replace(b"\r\n", b"\n") == subprocess.check_output(
        ["git", "-C", str(ROOT), "show", PIN + ":" + path]).replace(b"\r\n", b"\n")


def source():
    p = AuthorProject.new(scale=1)
    pid = p.add_profile(segments=[dict(kind="cubic", start=[0, 0], end=[12, 0],
        data=dict(control1=[0, 12], control2=[12, 12]))], closed=False)
    return p, pid, p.profiles[pid].segments[0].id


def ready(qtbot, dialog):
    qtbot.waitUntil(lambda: dialog._running is None and dialog._packet is not None, timeout=30000)


def type_distance(qtbot, dialog, distance):
    edit = dialog.distance.lineEdit()
    edit.selectAll()
    qtbot.keyClicks(edit, dialog.distance.locale().toString(float(distance), "f", 6))


def test_latest_real_cubic_request_discards_old_measurement_and_accepts_original_polynomial(qtbot):
    p, pid, eid = source()
    before = copy.deepcopy(p.to_dict())
    entered, release = threading.Event(), threading.Event()
    requests = []

    def delayed_actual_core(clone, profile_id, edge_id, request):
        requests.append(copy.deepcopy(request))
        if len(requests) == 1:
            entered.set()
            release.wait(10)
        return _curve_preview(clone, profile_id, edge_id, request)

    d = SubdivisionDialog(p, pid, eid, preview_function=delayed_actual_core)
    qtbot.addWidget(d)
    d.show()
    try:
        qtbot.waitUntil(entered.is_set)
        # Independently integrated original cubic: L(u)=24u³−36u²+36u.
        # L(1/4)=57/8. A length/total proxy would give19/64 instead of1/4.
        type_distance(qtbot, d, 57 / 8)
        qtbot.mouseClick(d.compute, Qt.MouseButton.LeftButton)
        assert d._packet is None
        assert not d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    finally:
        release.set()
    ready(qtbot, d)
    assert len(requests) == 2 and requests[-1]["distance"] == 57 / 8
    qtbot.mouseClick(d.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
    assert d.result() == QDialog.DialogCode.Accepted
    u = float(d.result_spec["parameter"])
    assert abs(24 * u**3 - 36 * u**2 + 36 * u - 57 / 8) <= 0.001
    assert abs(u - 1 / 4) < 1e-4
    assert p.to_dict() == before


def test_visible_invalid_distance_after_real_preview_cannot_reuse_previous_result(qtbot):
    p, pid, eid = source()
    before = p.to_dict()
    d = SubdivisionDialog(p, pid, eid)
    qtbot.addWidget(d)
    d.show()
    ready(qtbot, d)
    d.distance.lineEdit().selectAll()
    qtbot.keyClicks(d.distance.lineEdit(), "-")
    qtbot.mouseClick(d.compute, Qt.MouseButton.LeftButton)
    assert d._packet is None and d.result_spec is None
    assert not d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert "Opravte" in d.feedback.text()
    assert d.distance.lineEdit().text() == "-"
    d.reject()
    assert p.to_dict() == before


def test_geometry_edit_during_real_worker_prevents_late_apply(qtbot):
    p, pid, eid = source()
    entered, release = threading.Event(), threading.Event()

    def delayed_actual_core(clone, profile_id, edge_id, request):
        entered.set()
        release.wait(10)
        return _curve_preview(clone, profile_id, edge_id, request)

    d = SubdivisionDialog(p, pid, eid, preview_function=delayed_actual_core)
    qtbot.addWidget(d)
    d.show()
    try:
        qtbot.waitUntil(entered.is_set)
        data = copy.deepcopy(p.profiles[pid].segments[0].data)
        data["control1"][1] = 14
        p.set_profile_segment(pid, eid, kind="cubic", data=data)
        edited = p.to_dict()
    finally:
        release.set()
    qtbot.waitUntil(lambda: d._running is None, timeout=30000)
    assert d._packet is None
    assert "znovu" in d.feedback.text()
    d.accept()
    assert d.result_spec is None
    assert p.to_dict() == edited
    d.reject()
