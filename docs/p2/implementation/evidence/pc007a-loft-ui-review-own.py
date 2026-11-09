"""Independent widget-only negative oracles; mocked geometry is not model B."""

import copy
import threading
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_loft import LoftProfilesDialog

pytestmark = pytest.mark.ui


def project():
    p = AuthorProject.new(scale=1)
    p.add_profile([[0, 0], [10, 0], [10, 10]], closed=False, name="Wall source")
    p.add_profile([[0, 0], [12, 0], [12, 12]], closed=False, name="Roof source")
    return p


def result(params):
    params = copy.deepcopy(params)
    for row in params["correspondences"]:
        row.setdefault("ruling_id", str(uuid4()))
    params.setdefault("end_ruling_id", str(uuid4()))
    return {"status": "EXACT", "family": "TEST_WIDGET_ONLY", "params": params}


def dialog(qtbot, p, callback):
    d = LoftProfilesDialog(p, preview_function=callback)
    qtbot.addWidget(d)
    d.show()
    qtbot.waitExposed(d)
    d.confirm_pairs.setChecked(True)
    return d


def run(qtbot, d):
    assert d.request_preview()
    qtbot.waitUntil(lambda: d._running_job is None)


def test_import_comes_from_exact_worktree():
    import archpapercraft.ui.author_loft as actual

    root = Path(__file__).resolve().parents[4]
    assert Path(actual.__file__).resolve() == root / "src/archpapercraft/ui/author_loft.py"


@pytest.mark.parametrize("mutation", ["order", "seam", "old_ruling", "old_end"])
def test_preview_preserves_authored_order_seam_and_persistent_identity(qtbot, mutation):
    p = project()

    def callback(_clone, _a, _b, **params):
        out = result(params)
        if mutation == "order":
            out["params"]["correspondences"].reverse()
        elif mutation == "seam":
            out["params"]["seam_patch_id"] = params["correspondences"][1]["id"]
        elif mutation == "old_ruling":
            out["params"]["correspondences"][0]["ruling_id"] = str(uuid4())
        else:
            out["params"]["end_ruling_id"] = str(uuid4())
        return out

    d = dialog(qtbot, p, callback)
    # A prior accepted preview has already issued these persistent identities.
    d.pair_rows[0]["ruling_id"] = str(uuid4())
    d._end_ruling_id = str(uuid4())
    before = p.to_dict(validate=False)
    run(qtbot, d)
    assert not d.apply_button.isEnabled()
    assert d.preview_result is None
    assert p.to_dict(validate=False) == before


def test_accept_guards_live_geometry_change_without_revision_or_timer(qtbot):
    p = project()
    d = dialog(qtbot, p, lambda _c, _a, _b, **params: result(params))
    run(qtbot, d)
    assert d.apply_button.isEnabled()
    first = p.profiles[d.first_profile.currentData()]
    first.vertices[0].point[0] += 0.125
    d.accept()  # Immediately, without delivering the 150ms source timer.
    assert d.result() != QDialog.DialogCode.Accepted
    assert d.result_parameters is None and not d.apply_button.isEnabled()


def test_cancel_drops_queued_work_and_late_result(qtbot):
    p = project()
    entered, release = threading.Event(), threading.Event()
    calls = []

    def callback(_c, _a, _b, **params):
        calls.append(params)
        entered.set()
        assert release.wait(5)
        return result(params)

    d = dialog(qtbot, p, callback)
    assert d.request_preview()
    qtbot.waitUntil(entered.is_set)
    try:
        d.tolerance.setValue(0.004)
        assert d.request_preview()
        assert d._pending_request is not None
        d.cancel_preview()
    finally:
        release.set()
    qtbot.waitUntil(lambda: d._running_job is None)
    assert len(calls) == 1
    assert d.preview_result is None and not d.apply_button.isEnabled()


def test_c05_invalid_maximum_keyboard_submit_is_not_silently_corrected(qtbot):
    p, calls = project(), []

    def callback(_c, _a, _b, **params):
        calls.append(params)
        return result(params)

    d = dialog(qtbot, p, callback)
    d.advanced.setChecked(True)
    field = d.max_segments.lineEdit()
    field.setFocus()
    field.selectAll()
    qtbot.keyClick(field, Qt.Key.Key_Backspace)
    # Invoke the public action immediately after actual typing, without Enter.
    assert d.request_preview() is False
    assert not calls and d._running_job is None
    assert "Opravte" in d.feedback.text()


def test_mutating_detached_clone_does_not_touch_original_and_cancel_remains_safe(qtbot):
    p = project()
    before = p.to_dict(validate=False)

    def callback(clone, _a, _b, **params):
        assert clone is not p
        clone.profiles[_a].vertices[0].point[0] += 100
        return result(params)

    d = dialog(qtbot, p, callback)
    run(qtbot, d)
    d.reject()
    assert p.to_dict(validate=False) == before
    assert d.result_parameters is None
