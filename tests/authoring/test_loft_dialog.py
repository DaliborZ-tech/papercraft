"""Real Qt interaction for the dialog; injected math is not actual B proof."""

import copy
import threading
from uuid import uuid4

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QLineEdit

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_loft import LoftProfilesDialog

pytestmark = pytest.mark.ui


@pytest.fixture
def project():
    result = AuthorProject.new(scale=1)
    result.add_profile([[0, 0], [20, 0], [20, 20]], closed=False, name="Přední obrys")
    result.add_profile([[0, 0], [24, 0], [24, 24]], closed=False, name="Zadní obrys")
    result.add_profile([[0, 0], [18, 0], [18, 18]], closed=False, name="Jiný obrys")
    return result


def preview_result(parameters, status="EXACT", family="POSITIVE_HOMOTHETIC_CONE"):
    params = copy.deepcopy(parameters)
    for pair in params["correspondences"]:
        pair.setdefault("ruling_id", str(uuid4()))
    params.setdefault("end_ruling_id", str(uuid4()))
    params["reference_state"] = "BOUND"
    return {
        "status": status,
        "family": family,
        "message": "Testovací výsledek veřejného API.",
        "params": params,
        "surface_id": str(uuid4()),
        "part_id": str(uuid4()),
        "project_state": {"not_to_be_applied": True},
        "world_geometry": {},
    }


def successful(_clone, _first, _second, **params):
    return preview_result(params)


def dialog(qtbot, project, function=successful):
    result = LoftProfilesDialog(project, next(iter(project.profiles)), preview_function=function)
    qtbot.addWidget(result)
    result.show()
    qtbot.waitExposed(result)
    return result


def calculate(qtbot, widget):
    if not widget.confirm_pairs.isChecked():
        qtbot.mouseClick(widget.confirm_pairs, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(widget.calculate, Qt.MouseButton.LeftButton)


def wait_preview(qtbot, widget):
    qtbot.waitUntil(lambda: widget.preview_result is not None and widget._running_job is None)


def test_initial_flow_uses_friendly_source_names_native_preview_and_explicit_confirmation(
    qtbot, project
):
    calls = []

    def fake(*args, **kwargs):
        calls.append(kwargs)
        return successful(*args, **kwargs)

    widget = dialog(qtbot, project, fake)
    assert "Přední obrys" in widget.first_profile.currentText()
    assert "20 × 20 mm" in widget.first_profile.currentText()
    assert "úsečka" in widget.pair_rows[0]["first"].currentText()
    assert widget.comparison.scene().items()
    assert not widget.calculate.isEnabled() and not widget.apply_button.isEnabled()
    assert not calls and "pouze návrh" in widget.feedback.text()
    qtbot.mouseClick(widget.help_button, Qt.MouseButton.LeftButton)
    assert not widget.guidance.isVisible()
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert widget.apply_button.isEnabled() and len(calls) == 1
    assert widget.feedback.isVisible() and "přesný režim" in widget.feedback.text()
    qtbot.mouseClick(widget.help_button, Qt.MouseButton.LeftButton)
    assert widget.guidance.isVisible()


def test_worker_is_off_main_thread_and_never_mutates_live_project_or_injects_preview_state(
    qtbot, project, monkeypatch
):
    main_thread = threading.get_ident()
    records = []
    before = project.to_dict(validate=False)

    def fake(clone, first, second, **params):
        records.append(
            (threading.get_ident(), clone is project, first, second, copy.deepcopy(params))
        )
        clone.name = "Detached worker mutation"
        return preview_result(params)

    widget = dialog(qtbot, project, fake)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert records[0][0] != main_thread and records[0][1] is False
    assert project.to_dict(validate=False) == before
    expected = copy.deepcopy(widget._parameters_for_apply)
    applied = []
    monkeypatch.setattr(
        project,
        "add_loft",
        lambda a, b, **kw: applied.append((a, b, kw)) or "surface",
        raising=False,
    )
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    assert widget.result() == QDialog.DialogCode.Accepted
    assert widget.apply(project) == "surface"
    assert applied[0][0] == expected["first_profile_id"]
    assert applied[0][1] == expected["second_profile_id"]
    assert applied[0][2]["correspondences"] == expected["correspondences"]
    assert applied[0][2]["end_ruling_id"] == expected["end_ruling_id"]
    assert "reference_state" not in applied[0][2]
    assert project.to_dict(validate=False) == before


def test_gui_timer_and_controls_respond_while_preview_is_blocked(qtbot, project):
    entered, release = threading.Event(), threading.Event()

    def fake(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return successful(*args, **kwargs)

    widget = dialog(qtbot, project, fake)
    ticks = []
    timer = QTimer(widget)
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start()
    try:
        calculate(qtbot, widget)
        qtbot.waitUntil(entered.is_set)
        qtbot.waitUntil(lambda: len(ticks) >= 3)
        qtbot.mouseClick(widget.help_button, Qt.MouseButton.LeftButton)
        assert not widget.guidance.isVisible()
        assert not widget.apply_button.isEnabled()
    finally:
        release.set()
    wait_preview(qtbot, widget)


def test_changed_pairing_invalidates_preview_immediately_and_keyboard_does_not_apply_old_result(
    qtbot, project
):
    widget = dialog(qtbot, project)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert widget.apply_button.isEnabled()
    qtbot.mouseClick(widget.pair_rows[0]["reverse_second"], Qt.MouseButton.LeftButton)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert not widget.confirm_pairs.isChecked()
    qtbot.keyClick(widget, Qt.Key.Key_Return)
    assert widget.result() != QDialog.DialogCode.Accepted and widget.result_parameters is None


def test_changing_source_profile_discards_old_pairs_and_disables_apply(qtbot, project):
    widget = dialog(qtbot, project)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    old_ids = [r["id"] for r in widget.pair_rows]
    widget.second_profile.setFocus()
    qtbot.keyClick(widget.second_profile, Qt.Key.Key_End)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert [r["id"] for r in widget.pair_rows] != old_ids


def test_stale_generation_result_is_ignored_and_only_one_latest_pending_request_runs(
    qtbot, project
):
    entered, release = threading.Event(), threading.Event()
    calls = []

    def fake(_clone, _a, _b, **params):
        calls.append(copy.deepcopy(params))
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        return preview_result(params)

    widget = dialog(qtbot, project, fake)
    try:
        calculate(qtbot, widget)
        qtbot.waitUntil(entered.is_set)
        qtbot.mouseClick(widget.pair_rows[0]["reverse_first"], Qt.MouseButton.LeftButton)
        calculate(qtbot, widget)
        pending_token = widget._pending_request["token"]
        qtbot.mouseClick(widget.pair_rows[0]["reverse_second"], Qt.MouseButton.LeftButton)
        calculate(qtbot, widget)
        assert widget._pending_request["token"] > pending_token
        assert len(calls) == 1 and not widget.apply_button.isEnabled()
    finally:
        release.set()
    wait_preview(qtbot, widget)
    assert len(calls) == 2
    assert calls[-1]["correspondences"][0]["first_interval"] == [1, 0]
    assert calls[-1]["correspondences"][0]["second_interval"] == [1, 0]
    assert (
        widget._parameters_for_apply["correspondences"]
        == widget.preview_result["params"]["correspondences"]
    )


@pytest.mark.parametrize("change_revision", [False, True])
def test_live_source_change_rejects_late_result_even_without_revision_increment(
    qtbot, project, change_revision
):
    entered, release = threading.Event(), threading.Event()

    def fake(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return successful(*args, **kwargs)

    widget = dialog(qtbot, project, fake)
    try:
        calculate(qtbot, widget)
        qtbot.waitUntil(entered.is_set)
        project.name = "Live changed source"
        if change_revision:
            project.revision += 1
        assert not widget.apply_button.isEnabled()
    finally:
        release.set()
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert "změnil" in widget.feedback.text()


@pytest.mark.parametrize("close_dialog", [False, True])
def test_cancel_preview_and_escape_close_ignore_later_result(qtbot, project, close_dialog):
    entered, release = threading.Event(), threading.Event()

    def fake(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return successful(*args, **kwargs)

    widget = dialog(qtbot, project, fake)
    before = project.to_dict(validate=False)
    try:
        calculate(qtbot, widget)
        qtbot.waitUntil(entered.is_set)
        qtbot.mouseClick(widget.cancel_calculation, Qt.MouseButton.LeftButton)
        assert not widget.apply_button.isEnabled() and widget._pending_request is None
        if close_dialog:
            qtbot.keyClick(widget, Qt.Key.Key_Escape)
            assert widget.result() == QDialog.DialogCode.Rejected
    finally:
        release.set()
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and widget.result_parameters is None
    assert project.to_dict(validate=False) == before


@pytest.mark.parametrize("status", ["REJECTED", "UNRESOLVED"])
def test_b3_requires_explicit_choice_and_never_claims_exact_or_creates_half_command(
    qtbot, project, status
):
    def fake(_clone, _a, _b, **params):
        result = preview_result(params, status=status)
        result["message"] = "Profily nejsou doloženou přesně rozvinutelnou rodinou."
        return result

    before = project.to_dict(validate=False)
    widget = dialog(qtbot, project, fake)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert not widget.apply_button.isEnabled() and widget.keep_target.isVisible()
    assert "přesný režim s doloženou" not in widget.feedback.text()
    assert "bez tiskového dílu" in widget.feedback.text()
    assert project.to_dict(validate=False) == before
    qtbot.mouseClick(widget.keep_target, Qt.MouseButton.LeftButton)
    assert widget.apply_button.isEnabled()
    assert widget.apply_button.text() == "Uchovat konstrukční cíl"
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    assert (
        widget.result_parameters["correspondences"]
        == widget.preview_result["params"]["correspondences"]
    )


def test_crossed_or_disconnected_pair_error_stays_explanatory_and_read_only(qtbot, project):
    def fake(_clone, _a, _b, **_params):
        raise ValueError("Konce vybraných úseků nenavazují. Opravte směr druhé dvojice.")

    before = project.to_dict(validate=False)
    widget = dialog(qtbot, project, fake)
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert not widget.apply_button.isEnabled() and widget.preview_result is None
    assert "Opravte směr druhé dvojice" in widget.feedback.text()
    assert project.to_dict(validate=False) == before


def test_persistent_pair_and_ruling_ids_survive_recalculation_and_seam_choice(qtbot, project):
    widget = dialog(qtbot, project)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    first = copy.deepcopy(widget._parameters_for_apply)
    widget.seam.setCurrentIndex(1)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    second = widget._parameters_for_apply
    assert [x["id"] for x in first["correspondences"]] == [
        x["id"] for x in second["correspondences"]
    ]
    assert [x["ruling_id"] for x in first["correspondences"]] == [
        x["ruling_id"] for x in second["correspondences"]
    ]
    assert first["end_ruling_id"] == second["end_ruling_id"]
    assert second["seam_patch_id"] == widget.pair_rows[1]["id"]


def test_row_reordering_preserves_draft_ids_and_widgets_after_qt_event_delivery(qtbot, project):
    widget = dialog(qtbot, project)
    ids = [row["id"] for row in widget.pair_rows]
    widget.pairs.selectRow(0)
    widget.move_pair(1)
    qtbot.wait(10)
    assert [row["id"] for row in widget.pair_rows] == list(reversed(ids))
    assert widget.pair_rows[0]["first"].currentText()
    widget.remove_pair()
    qtbot.wait(10)
    assert len(widget.pair_rows) == 1 and widget.pair_rows[0]["first"].currentText()


def test_pending_budget_text_invalidates_old_preview_and_is_committed_before_recompute(
    qtbot, project
):
    widget = dialog(qtbot, project)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    qtbot.mouseClick(widget.advanced, Qt.MouseButton.LeftButton)
    field = widget.tolerance.findChild(QLineEdit)
    field.setFocus()
    field.selectAll()
    qtbot.keyClicks(field, "0" + widget.tolerance.locale().decimalPoint() + "004000")
    assert not widget.apply_button.isEnabled() and widget.preview_result is None
    qtbot.keyClick(widget, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    wait_preview(qtbot, widget)
    assert widget._parameters_for_apply["tolerance_mm"] == pytest.approx(0.004)
    assert widget.apply_button.isEnabled()


@pytest.mark.parametrize("mouse_submit", [False, True])
def test_invalid_pending_budget_stops_compute_and_project_remains_unchanged(
    qtbot, project, mouse_submit
):
    widget = dialog(qtbot, project)
    qtbot.mouseClick(widget.advanced, Qt.MouseButton.LeftButton)
    field = widget.tolerance.lineEdit()
    field.setFocus()
    field.selectAll()
    qtbot.keyClick(field, Qt.Key.Key_Backspace)
    assert not widget.tolerance.hasAcceptableInput()
    if mouse_submit:
        calculate(qtbot, widget)
    else:
        assert widget.request_preview() is False
    assert "Opravte rozepsanou" in widget.feedback.text()
    assert widget._running_job is None


def test_apply_refuses_source_change_after_acceptance(qtbot, project, monkeypatch):
    widget = dialog(qtbot, project)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    project.name = "Changed after acceptance"
    calls = []
    monkeypatch.setattr(project, "add_loft", lambda *a, **kw: calls.append((a, kw)), raising=False)
    with pytest.raises(ValueError, match="Projekt se od potvrzení změnil"):
        widget.apply(project)
    assert not calls


def test_b2_empty_loft_params_keep_explicit_mapping_without_inventing_3d_claim(qtbot, project):
    def fake(_clone, _a, _b, **_params):
        return {
            "status": "EXACT",
            "family": "PLANAR_REGION",
            "params": {},
            "message": "Rovinná oblast s vnitřním otvorem.",
        }

    widget = dialog(qtbot, project, fake)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert widget.apply_button.isEnabled() and "Rovinný pás" in widget.feedback.text()
    assert (
        widget._parameters_for_apply["correspondences"] == widget._parameters()["correspondences"]
    )


def test_native_arc_and_cubic_are_shown_as_actual_curves_with_true_extents(qtbot):
    project = AuthorProject.new()
    project.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [10, 0],
                "end": [-10, 0],
                "data": {"center": [0, 0], "sweep_deg": 180},
            }
        ],
        closed=False,
        name="Vlastní oblouk",
    )
    project.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [0, 0],
                "end": [20, 0],
                "data": {"control1": [5, 12], "control2": [15, -12]},
            }
        ],
        closed=False,
        name="Vlastní křivka",
    )
    widget = dialog(qtbot, project)
    assert "20 × 10 mm" in widget.first_profile.currentText()
    assert "kruhový oblouk" in widget.pair_rows[0]["first"].currentText()
    assert "Bézierova křivka" in widget.pair_rows[0]["second"].currentText()
    paths = [item.path() for item in widget.comparison.scene().items() if hasattr(item, "path")]
    assert any(path.elementCount() > 4 for path in paths)
    assert any(path.elementAt(i).isCurveTo() for path in paths for i in range(path.elementCount()))


def test_source_topology_replacement_refreshes_rows_and_requires_repair(qtbot, project):
    widget = dialog(qtbot, project)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    first_id = widget.first_profile.currentData()
    project.update_profile(first_id, [[0, 0], [30, 0], [30, 20]], closed=False)
    qtbot.waitUntil(lambda: not widget.apply_button.isEnabled())
    assert "30 × 20 mm" in widget.first_profile.currentText()
    assert widget.pair_rows[0]["first"].currentIndex() == -1
    assert not widget.confirm_pairs.isChecked()
    assert not widget.calculate.isEnabled()


def test_default_production_dispatch_uses_clones_public_preview_method(qtbot, project, monkeypatch):
    calls = []

    def public(self, first, second, **params):
        calls.append((self is project, first, second))
        return preview_result(params)

    monkeypatch.setattr(AuthorProject, "preview_loft", public, raising=False)
    widget = LoftProfilesDialog(project)
    qtbot.addWidget(widget)
    widget.show()
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert calls and calls[0][0] is False and widget.apply_button.isEnabled()


def test_preview_cannot_silently_replace_authored_pairing(qtbot, project):
    def fake(_clone, _first, _second, **params):
        params["correspondences"][0]["second_interval"] = [1, 0]
        return preview_result(params)

    widget = dialog(qtbot, project, fake)
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert "neodpovídá zadaným dvojicím" in widget.feedback.text()
