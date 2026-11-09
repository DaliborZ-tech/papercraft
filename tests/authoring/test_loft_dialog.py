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


def existing_params(project):
    first, second = list(project.profiles.values())[:2]
    rows = [
        {
            "id": str(uuid4()),
            "ruling_id": str(uuid4()),
            "first_segment_id": a.id,
            "second_segment_id": b.id,
            "first_interval": [0, 1],
            "second_interval": [0, 1],
        }
        for a, b in zip(first.segments, second.segments)
    ]
    return first.id, {
        "second_profile_id": second.id,
        "correspondences": rows,
        "seam_patch_id": rows[1]["id"],
        "end_ruling_id": str(uuid4()),
        "tolerance_mm": 0.004,
        "max_segments": 8192,
        "reference_state": "BOUND",
    }


def test_load_existing_mapping_preserves_ids_seam_orientation_and_current_source_fence(
    qtbot, project, monkeypatch
):
    first_id, params = existing_params(project)
    for row in params["correspondences"]:
        row["first_interval"] = row["second_interval"] = [1, 0]
    params["correspondences"].reverse()
    before = project.to_dict(validate=False)
    widget = dialog(qtbot, project)
    assert widget.load_parameters(first_id, params, existing_surface_id=str(uuid4()))
    assert widget.load_error is None and not widget.first_profile.isEnabled()
    assert widget.confirm_pairs.isChecked() and widget.calculate.isEnabled()
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert widget._parameters()["correspondences"] == params["correspondences"]
    assert widget.seam.currentData() == params["seam_patch_id"]
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert widget.apply_button.text() == "Použít změnu plochy"
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    assert widget.check_source(project)
    assert widget.result_parameters["correspondences"] == params["correspondences"]
    assert widget.result_parameters["end_ruling_id"] == params["end_ruling_id"]
    assert widget.result_parameters["first_profile_id"] == first_id
    assert project.to_dict(validate=False) == before
    calls = []
    monkeypatch.setattr(project, "add_loft", lambda *a, **kw: calls.append((a, kw)), raising=False)
    with pytest.raises(ValueError, match="Existující plochu upravte"):
        widget.apply(project)
    assert not calls
    project.name = "Changed after edit acceptance"
    with pytest.raises(ValueError, match="Projekt se od potvrzení změnil"):
        widget.check_source(project)


def test_loaded_second_profile_retarget_preserves_rows_and_requires_explicit_new_segment_choices(
    qtbot, project
):
    first_id, params = existing_params(project)
    widget = dialog(qtbot, project)
    widget.load_parameters(first_id, params, existing_surface_id=str(uuid4()))
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    old_ids = [(r["id"], r["ruling_id"]) for r in widget.pair_rows]
    widget.second_profile.setFocus()
    qtbot.keyClick(widget.second_profile, Qt.Key.Key_End)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert not widget.confirm_pairs.isChecked()
    assert [(r["id"], r["ruling_id"]) for r in widget.pair_rows] == old_ids
    assert all(r["second"].currentIndex() == -1 for r in widget.pair_rows)
    assert widget.first_profile.currentData() == first_id and not widget.first_profile.isEnabled()
    assert widget.seam.currentData() == params["seam_patch_id"]
    for index, row in enumerate(widget.pair_rows):
        row["second"].setFocus()
        qtbot.keyClick(row["second"], Qt.Key.Key_Home)
        if index:
            qtbot.keyClick(row["second"], Qt.Key.Key_Down)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert widget._parameters_for_apply["second_profile_id"] == widget.second_profile.currentData()
    assert widget._parameters_for_apply["correspondences"] != params["correspondences"]
    assert [(r["id"], r["ruling_id"]) for r in widget.pair_rows] == old_ids


def test_loaded_source_replacement_keeps_all_unmatched_rows_even_after_reordering(qtbot, project):
    first_id, params = existing_params(project)
    widget = dialog(qtbot, project)
    widget.load_parameters(first_id, params, existing_surface_id=str(uuid4()))
    project.update_profile(params["second_profile_id"], [[0, 0], [30, 0], [30, 20]], closed=False)
    qtbot.waitUntil(lambda: widget.load_error is not None)
    assert widget.load_error["code"] == "LOFT_SOURCE_SEGMENT_MISSING"
    assert len(widget.pair_rows) == len(params["correspondences"])
    assert all(row["second"].currentIndex() == -1 for row in widget.pair_rows)
    assert not widget.calculate.isEnabled() and not widget.apply_button.isEnabled()
    widget.pairs.selectRow(0)
    widget.move_pair(1)
    qtbot.wait(1)
    assert all(row["second"].currentIndex() == -1 for row in widget.pair_rows)
    assert {row["id"] for row in widget.pair_rows} == {
        row["id"] for row in params["correspondences"]
    }


@pytest.mark.parametrize("missing", ["first", "second", "segment", "seam"])
def test_load_missing_references_are_typed_and_never_replaced_by_index_fallback(
    qtbot, project, missing
):
    first_id, params = existing_params(project)
    if missing == "first":
        first_id = str(uuid4())
    elif missing == "second":
        params["second_profile_id"] = str(uuid4())
    elif missing == "segment":
        params["correspondences"][0]["second_segment_id"] = str(uuid4())
    else:
        params["seam_patch_id"] = str(uuid4())
    widget = dialog(qtbot, project)
    assert not widget.load_parameters(first_id, params, existing_surface_id=str(uuid4()))
    assert widget.load_error is not None
    assert not widget.confirm_pairs.isChecked() and not widget.calculate.isEnabled()
    assert len(widget.pair_rows) == 2
    if missing == "first":
        assert widget.first_profile.currentIndex() == -1 and not widget.first_profile.isEnabled()
    elif missing == "second":
        assert widget.second_profile.currentIndex() == -1
    elif missing == "segment":
        assert widget.pair_rows[0]["second"].currentIndex() == -1
    else:
        assert widget.seam.currentIndex() == -1
        widget.pairs.selectRow(0)
        widget.move_pair(1)
        assert widget.seam.currentIndex() == -1


def test_default_loaded_preview_uses_public_update_api_and_omits_immutable_inputs(
    qtbot, project, monkeypatch
):
    first_id, params = existing_params(project)
    surface_id, calls = str(uuid4()), []

    def public_update(self, actual_surface_id, **kwargs):
        calls.append((self is project, actual_surface_id, copy.deepcopy(kwargs)))
        result = preview_result(kwargs)
        result["params"]["end_ruling_id"] = params["end_ruling_id"]
        return result

    monkeypatch.setattr(AuthorProject, "preview_loft_update", public_update, raising=False)
    widget = LoftProfilesDialog(project)
    qtbot.addWidget(widget)
    widget.show()
    assert widget.load_parameters(first_id, params, existing_surface_id=surface_id)
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert calls[0][0] is False and calls[0][1] == surface_id
    assert "end_ruling_id" not in calls[0][2] and "first_profile_id" not in calls[0][2]
    assert calls[0][2]["second_profile_id"] == params["second_profile_id"]
    assert widget._parameters_for_apply["end_ruling_id"] == params["end_ruling_id"]


@pytest.mark.parametrize(
    "mutation", ["order", "seam", "old_ruling", "old_end", "missing_old_ruling", "missing_old_end"]
)
def test_preview_must_preserve_exact_order_seam_and_existing_identity(qtbot, project, mutation):
    def fake(_clone, _a, _b, **params):
        result = preview_result(params)
        actual = result["params"]
        if mutation == "order":
            actual["correspondences"].reverse()
        elif mutation == "seam":
            actual["seam_patch_id"] = params["correspondences"][1]["id"]
        elif mutation == "old_ruling":
            actual["correspondences"][0]["ruling_id"] = str(uuid4())
        elif mutation == "old_end":
            actual["end_ruling_id"] = str(uuid4())
        elif mutation == "missing_old_ruling":
            actual["correspondences"][0].pop("ruling_id")
        else:
            actual.pop("end_ruling_id")
        return result

    widget = dialog(qtbot, project, fake)
    known_ruling, known_end = str(uuid4()), str(uuid4())
    widget.pair_rows[0]["ruling_id"] = known_ruling
    widget._end_ruling_id = known_end
    before = project.to_dict(validate=False)
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert widget.pair_rows[0]["ruling_id"] == known_ruling
    assert widget._end_ruling_id == known_end
    assert "Návrh nelze použít" in widget.feedback.text()
    assert project.to_dict(validate=False) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_ruling",
        "missing_end",
        "invalid_ruling",
        "invalid_end",
        "duplicate_ruling",
        "duplicate_patch",
    ],
)
def test_new_preview_identities_must_be_present_valid_unique_and_adopted_atomically(
    qtbot, project, mutation
):
    def fake(_clone, _a, _b, **params):
        result = preview_result(params)
        actual = result["params"]
        if mutation == "missing_ruling":
            actual["correspondences"][1].pop("ruling_id")
        elif mutation == "missing_end":
            actual.pop("end_ruling_id")
        elif mutation == "invalid_ruling":
            actual["correspondences"][1]["ruling_id"] = "invalid"
        elif mutation == "invalid_end":
            actual["end_ruling_id"] = None
        elif mutation == "duplicate_ruling":
            actual["end_ruling_id"] = actual["correspondences"][0]["ruling_id"]
        else:
            actual["correspondences"][1]["ruling_id"] = actual["correspondences"][0]["id"]
        return result

    widget = dialog(qtbot, project, fake)
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert all(not row.get("ruling_id") for row in widget.pair_rows)
    assert widget._end_ruling_id is None


def test_closed_seam_choice_visibly_rotates_the_authored_request_before_preview(qtbot):
    project = AuthorProject.new()
    project.add_profile([[0, 0], [20, 0], [20, 10], [0, 10]])
    project.add_profile([[0, 0], [24, 0], [24, 12], [0, 12]])
    widget = dialog(qtbot, project)
    original = [row["id"] for row in widget.pair_rows]
    widget.seam.setFocus()
    qtbot.keyClick(widget.seam, Qt.Key.Key_Down)
    expected = original[1:] + original[:1]
    assert [row["id"] for row in widget.pair_rows] == expected
    assert (
        widget.pairs.cellWidget(0, 0).currentData()
        == project.profiles[widget.first_profile.currentData()].segments[1].id
    )
    assert widget.seam.currentData() == expected[0]
    assert not widget.confirm_pairs.isChecked()
    calculate(qtbot, widget)
    wait_preview(qtbot, widget)
    assert [row["id"] for row in widget._parameters_for_apply["correspondences"]] == expected
    assert widget._parameters_for_apply["seam_patch_id"] == expected[0]


def test_closed_row_move_requires_a_visible_first_seam_and_reselection_repairs_it(qtbot):
    project = AuthorProject.new()
    for scale in (1, 1.2):
        project.add_profile([[0, 0], [20 * scale, 0], [20 * scale, 10 * scale], [0, 10 * scale]])
    widget = dialog(qtbot, project)
    seam = widget.seam.currentData()
    widget.pairs.selectRow(0)
    widget.move_pair(1)
    assert widget.pair_rows[0]["id"] != seam and widget.seam.currentData() == seam
    assert "první dvojicí" in widget.feedback.text()
    assert not widget.calculate.isEnabled()
    widget.seam.showPopup()
    view = widget.seam.view()
    rectangle = view.visualRect(view.currentIndex())
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rectangle.center())
    assert widget.pair_rows[0]["id"] == seam
    assert widget.seam.currentData() == seam


def test_empty_nonplanar_preview_params_cannot_fall_back_to_unverified_request(qtbot, project):
    widget = dialog(
        qtbot,
        project,
        lambda *_args, **_kw: {
            "status": "EXACT",
            "family": "POSITIVE_HOMOTHETIC_CONE",
            "params": {},
        },
    )
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()


@pytest.mark.parametrize("bad_field", ["message", "family", "tolerance_mm", "max_segments"])
def test_malformed_response_is_rejected_before_any_new_draft_identity_is_adopted(
    qtbot, project, bad_field
):
    def fake(_clone, _a, _b, **params):
        result = preview_result(params)
        if bad_field in ("message", "family"):
            result[bad_field] = None
        else:
            result["params"][bad_field] = None
        return result

    widget = dialog(qtbot, project, fake)
    before = copy.deepcopy(widget._parameters())
    document = project.to_dict(validate=False)
    published = []
    widget.preview_changed.connect(published.append)
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None)
    assert widget.preview_result is None and not widget.apply_button.isEnabled()
    assert widget._parameters() == before
    assert all(result is None for result in published)
    assert project.to_dict(validate=False) == document


@pytest.mark.skipif(
    not hasattr(AuthorProject, "preview_loft_update"),
    reason="Actual domain API is integrated by the owner in a separate source.",
)
def test_closed_seam_actual_public_api_creation_and_edit_preserve_exact_requested_identity(qtbot):
    """Actual domain+widget API smoke; fixture creation is not the model B UI proof."""
    project = AuthorProject.new()
    first = project.add_profile([[0, 0], [20, 0], [20, 10], [0, 10]])
    project.copy_profile(first, plane={"origin": [0, 0, 12], "u": [1, 0, 0], "v": [0, 1, 0]})
    before = project.to_dict(validate=False)
    widget = LoftProfilesDialog(project, first)
    qtbot.addWidget(widget)
    widget.show()
    original = [row["id"] for row in widget.pair_rows]
    widget.seam.setFocus()
    qtbot.keyClick(widget.seam, Qt.Key.Key_Down)
    expected = original[1:] + original[:1]
    assert [row["id"] for row in widget.pair_rows] == expected
    calculate(qtbot, widget)
    qtbot.waitUntil(lambda: widget._running_job is None, timeout=30000)
    assert widget.preview_result is not None, widget.feedback.text()
    assert widget.preview_result["status"] == "EXACT", widget.feedback.text()
    assert [row["id"] for row in widget.preview_result["params"]["correspondences"]] == expected
    assert project.to_dict(validate=False) == before
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    surface_id = widget.apply(project)
    original_params = copy.deepcopy(project.surfaces[surface_id].params)
    assert project.loft_status(surface_id)["status"] == "EXACT"
    editing = LoftProfilesDialog(project)
    qtbot.addWidget(editing)
    editing.show()
    assert editing.load_parameters(first, original_params, existing_surface_id=surface_id)
    editing.seam.setFocus()
    qtbot.keyClick(editing.seam, Qt.Key.Key_Down)
    requested = editing._parameters()
    calculate(qtbot, editing)
    qtbot.waitUntil(lambda: editing._running_job is None, timeout=30000)
    assert editing.preview_result is not None, editing.feedback.text()
    assert editing.preview_result["status"] == "EXACT", editing.feedback.text()
    assert editing._parameters_for_apply["correspondences"] == requested["correspondences"]
    assert editing._parameters_for_apply["end_ruling_id"] == original_params["end_ruling_id"]
    qtbot.mouseClick(editing.apply_button, Qt.MouseButton.LeftButton)
    assert editing.check_source(project)
    parameters = copy.deepcopy(editing.result_parameters)
    parameters.pop("first_profile_id")
    parameters.pop("end_ruling_id")
    project.update_loft(surface_id, **parameters)
    assert project.surfaces[surface_id].params["correspondences"] == requested["correspondences"]
    assert project.surfaces[surface_id].params["seam_patch_id"] == requested["seam_patch_id"]
    assert project.loft_status(surface_id)["status"] == "EXACT"
