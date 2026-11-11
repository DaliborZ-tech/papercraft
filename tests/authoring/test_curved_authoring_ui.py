"""Offscreen real widgets and public C producer; not a native or novice proof."""

import copy
import math
import threading
from uuid import uuid4

import pytest
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QDialog
from test_circular_shell import authored, circle
from test_workspace import window as _window_fixture

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, load_project
from archpapercraft.ui.author_curved_connectors import CurvedConnectorDialog

pytestmark = pytest.mark.ui
window = _window_fixture


@pytest.fixture(scope="module")
def source():
    project, owner, _ = authored(10, 10, 30)
    receiver = project.add_surface(circle(project, 10, 0))
    project.set_material_profile(thickness_mm=0.2, clearance_mm=0.01, bend_radius_mm=0)
    project.recompute()
    return project.to_dict(validate=False), owner, receiver


def restore(source):
    state, owner, receiver = source
    return AuthorProject.from_dict(copy.deepcopy(state)), owner, receiver


@pytest.fixture(scope="module")
def positive(source):
    project, owner, receiver = restore(source)
    cid = project.add_curved_connector(
        owner, "first", receiver, receiver_side="inside", nominal_base_mm=0.24, min_glue_area_mm2=1
    )
    record = project.curved_connectors[cid]
    project.set_curved_tab(cid, record.slot_ids[0], enabled=False)
    project.set_curved_tab(cid, record.slot_ids[1], tip_offset_mm=0.01)
    project.recompute()
    assert project.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE"
    return project.to_dict(validate=False), owner, receiver, cid


def make_dialog(qtbot, source, callback=None):
    project, owner, receiver = restore(source)
    widget = CurvedConnectorDialog(project, owner, preview_function=callback)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.receiver.setCurrentIndex(widget.receiver.findData(receiver))
    return project, widget


def unresolved(_clone, request):
    return {
        "status": "UNRESOLVED",
        "message": "Zkontrolujte skutečný materiál příjemce.",
        "can_confirm": False,
        "can_create_authored_intent": True,
        "request": copy.deepcopy(request),
        "slot_ids": request["source_slot_ids"]
        + [str(uuid4()) for _ in range(request["pool_count"] - len(request["source_slot_ids"]))],
    }


def finish(qtbot, widget):
    qtbot.waitUntil(lambda: widget._running is None, timeout=30000)


def test_real_producer_off_custom_tip_apply_stale_recompute_undo_save_open(qtbot, source, tmp_path):
    project, widget = make_dialog(qtbot, source)
    before = project.to_dict(validate=False)
    qtbot.mouseClick(
        widget.tab_enabled,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, widget.tab_enabled.height() // 2),
    )
    widget.tabs.setCurrentIndex(1)
    field = widget.tip.lineEdit()
    field.setFocus()
    field.selectAll()
    qtbot.keyClicks(field, "0" + widget.tip.locale().decimalPoint() + "01")
    qtbot.mouseClick(widget.compute, Qt.MouseButton.LeftButton)
    finish(qtbot, widget)
    assert widget._packet is not None, widget.feedback.text()
    assert widget._packet["status"] == "CERTIFIED_APPROXIMATE", widget.feedback.text()
    assert widget.apply_button.isEnabled()
    assert widget.paper_preview.scene().items()
    assert widget.assembly_preview.packet["geometry"]["display_is_proof"] is False
    assert not widget._packet["geometry"]["all_tabs"][0]["enabled"]
    assert widget._packet["geometry"]["all_tabs"][1]["tip_offset_mm"] == 0.01
    assert project.to_dict(validate=False) == before
    preview_ids = widget._packet["slot_ids"]
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    assert widget.result() == QDialog.DialogCode.Accepted
    controller = AuthorController()
    controller.project = project
    cid = controller.execute("Vlastní kruhové chlopně", widget.apply)
    record = project.curved_connectors[cid]
    ids = list(record.slot_ids)
    assert ids != preview_ids  # Intent uses new live UUIDs, not preview cache/proof injection.
    assert record.tab_overrides[ids[0]]["enabled"] is False
    assert record.tab_overrides[ids[1]]["tip_offset_mm"] == 0.01
    assert project.parts[project.part_for_surface(record.owner_surface_id)].stale
    assert project.curved_connector_status(cid)["status"] == "STALE"
    controller.undo()
    assert controller.project.to_dict(validate=False) == before
    controller.redo()
    project = controller.project
    assert project.curved_connectors[cid].slot_ids == ids
    controller.execute("Snížit počet", lambda p: p.update_curved_connector(cid, count=8))
    controller.execute("Obnovit počet", lambda p: p.update_curved_connector(cid, count=12))
    assert project.curved_connectors[cid].slot_ids == ids
    controller.recompute()
    assert project.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE"
    path = tmp_path / "author-curved.apcraft"
    project.save(path)
    reopened = load_project(path)
    assert reopened.curved_connectors[cid].slot_ids == ids
    assert reopened.curved_connectors[cid].tab_overrides[ids[1]]["tip_offset_mm"] == 0.01
    assert reopened.curved_connector_geometry(cid)["status"] == "CERTIFIED_APPROXIMATE"


def test_negative_real_wrong_contact_side_is_not_certified_and_can_retain_intent(qtbot, source):
    project, widget = make_dialog(qtbot, source)
    widget.receiver_side.setCurrentIndex(widget.receiver_side.findData("outside"))
    before = project.to_dict(validate=False)
    qtbot.mouseClick(widget.help_toggle, Qt.MouseButton.LeftButton)
    assert not widget.help.isVisible()
    qtbot.mouseClick(widget.compute, Qt.MouseButton.LeftButton)
    finish(qtbot, widget)
    assert widget._packet is not None
    assert widget._packet["status"] != "CERTIFIED_APPROXIMATE"
    assert not widget.apply_button.isEnabled() and widget.retain.isVisible()
    assert not widget.paper_preview.scene().items()
    assert widget.feedback.isVisible() and "není digitálně doložený" in widget.feedback.text()
    assert project.to_dict(validate=False) == before
    qtbot.mouseClick(widget.retain, Qt.MouseButton.LeftButton)
    assert widget.apply_button.isEnabled()
    qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
    cid = widget.apply(project)
    assert project.curved_connector_status(cid)["status"] == "STALE"


def test_pending_tip_is_bound_to_previous_slot_when_selection_changes(qtbot, source):
    _project, widget = make_dialog(qtbot, source, unresolved)
    field = widget.tip.lineEdit()
    field.setFocus()
    field.selectAll()
    qtbot.keyClicks(field, "0" + widget.tip.locale().decimalPoint() + "01")
    widget.tabs.setCurrentIndex(1)
    assert widget.overrides["0"]["tip_offset_mm"] == 0.01
    assert widget.tip.value() == 0 and widget.overrides.get("1", {}).get("tip_offset_mm", 0) == 0


def test_invalid_numeric_raw_survives_focus_out_and_blocks_preview(qtbot, source):
    project, widget = make_dialog(qtbot, source, unresolved)
    before = project.to_dict(validate=False)
    field = widget.fields["depth_mm"].lineEdit()
    field.setFocus()
    field.selectAll()
    qtbot.keyClick(field, Qt.Key.Key_Backspace)
    qtbot.mouseClick(widget.compute, Qt.MouseButton.LeftButton)
    assert widget._running is None and widget._packet is None
    assert "Opravte rozepsané" in widget.feedback.text()
    assert project.to_dict(validate=False) == before


@pytest.mark.parametrize("mutation", ["source", "draft", "cancel", "close"])
def test_slow_worker_does_not_freeze_gui_and_discards_obsolete_results(qtbot, source, mutation):
    entered, release = threading.Event(), threading.Event()

    def callback(project, request):
        entered.set()
        assert release.wait(5)
        return unresolved(project, request)

    project, widget = make_dialog(qtbot, source, callback)
    before = project.to_dict(validate=False)
    ticks = []
    timer = QTimer(widget)
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start()
    try:
        widget.request_preview()
        qtbot.waitUntil(entered.is_set)
        qtbot.waitUntil(lambda: len(ticks) >= 2)
        if mutation == "source":
            project.name = "Changed source without revision"
        elif mutation == "draft":
            widget.fields["relief_mm"].setValue(0.7)
        elif mutation == "cancel":
            qtbot.mouseClick(widget.cancel_compute, Qt.MouseButton.LeftButton)
        else:
            qtbot.keyClick(widget, Qt.Key.Key_Escape)
    finally:
        release.set()
    finish(qtbot, widget)
    assert widget._packet is None and not widget.apply_button.isEnabled()
    assert not widget.paper_preview.scene().items()
    if mutation != "source":
        assert project.to_dict(validate=False) == before


def test_source_change_after_acceptance_blocks_apply_even_if_revision_is_unchanged(qtbot, source):
    project, widget = make_dialog(qtbot, source, unresolved)
    widget.request_preview()
    finish(qtbot, widget)
    widget.retain.setChecked(True)
    widget.accept()
    assert widget.result() == QDialog.DialogCode.Accepted
    project.name = "Changed after accept"
    with pytest.raises(ValueError, match="aktuální nezměněný"):
        widget.apply(project)


def test_host_context_action_and_reset_preserve_legacy_selection(window, source):
    project, owner, receiver = restore(source)
    cid = project.add_curved_connector(
        owner, "first", receiver, receiver_side="inside", nominal_base_mm=0.24, min_glue_area_mm2=1
    )
    window.controller.project = project
    window.refresh()
    window.select_surface(owner)
    assert window.actions["curved_connector"].isEnabled()
    window.curved_panel.sets.setCurrentIndex(window.curved_panel.sets.findData(cid))
    assert window.selected_surface == owner
    assert window.viewport.relation == ("curved", cid)
    assert not window.viewport.relation_paths  # STALE cannot draw a certified glue patch.
    window.select_surface(receiver)
    assert window.curved_panel.current_id is None
    assert not window.actions["curved_connector"].isEnabled()
    assert window.paper.curved_overlay is None
    window.select_profile(project.surfaces[owner].profile_id)
    assert window.curved_panel.current_id is None


def test_current_slot_links_actual_paper_and_assembled_glue_and_undo_restores_it(window, positive):
    state, owner, _receiver, cid = positive
    window.controller.project = AuthorProject.from_dict(copy.deepcopy(state))
    window.refresh()
    window.select_surface(owner)
    panel = window.curved_panel
    panel.sets.setCurrentIndex(panel.sets.findData(cid))
    panel.tabs.setCurrentIndex(1)
    tab_id = panel.tabs.currentData()
    assert window.viewport.curved_tab_id == tab_id
    assert len(window.viewport.relation_paths) == 2
    assert window.paper.curved_overlay[0] == window.selected_part
    expected = window.project.curved_connector_geometry(cid)["all_tabs"][1]["paper_native_loop"]
    assert window.paper.curved_overlay[1] == expected
    panel.toggle_tab()
    assert window.project.curved_connectors[cid].tab_overrides[tab_id]["enabled"] is False
    assert not window.viewport.relation_paths and window.paper.curved_overlay is None
    window.actions["undo"].trigger()
    assert window.project.curved_connectors[cid].slot_ids[1] == tab_id
    assert window.project.curved_connectors[cid].tab_overrides[tab_id].get("enabled", True)
    assert len(window.viewport.relation_paths) == 2 and window.paper.curved_overlay


def test_existing_editor_retains_slot_uuid_pool_off_custom_tip_and_owner(qtbot, positive):
    state, owner, _receiver, cid = positive
    project = AuthorProject.from_dict(copy.deepcopy(state))
    ids = list(project.curved_connectors[cid].slot_ids)
    widget = CurvedConnectorDialog(project, owner, connector_id=cid, selected_tab=ids[1])
    qtbot.addWidget(widget)
    widget.show()
    assert not widget.rim.isEnabled() and widget.tabs.currentIndex() == 1
    assert widget.tip.value() == 0.01
    widget.count.setValue(8)
    widget.count.setValue(12)
    assert widget.source_slot_ids == ids and widget.overrides["0"]["enabled"] is False
    widget.request_preview()
    finish(qtbot, widget)
    assert widget._packet["status"] == "CERTIFIED_APPROXIMATE", widget.feedback.text()
    assert widget._packet["slot_ids"] == ids
    widget.reject()
    assert project.to_dict(validate=False) == state


def test_set_switch_moves_owner_tree_properties_and_subselection_without_changing_print_material(
    window, source
):
    project, first_owner, first_receiver = restore(source)
    first = project.add_curved_connector(
        first_owner,
        "first",
        first_receiver,
        receiver_side="inside",
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
    )
    a, b = project.surfaces[first_owner].source_profile_ids()
    second_a, second_b = circle(project, 10, 0), circle(project, 10, 30)
    second_owner = project.add_loft(
        second_a,
        second_b,
        correspondences=[
            {"first_segment_id": x.id, "second_segment_id": y.id}
            for x, y in zip(
                project.profiles[second_a].segments, project.profiles[second_b].segments
            )
        ],
    )
    second_receiver = project.add_surface(circle(project, 10, 0))
    project.set_transform(second_owner, [50, 0, 0], [0, 0, 0])
    project.set_transform(second_receiver, [50, 0, 0], [0, 0, 0])
    second = project.add_curved_connector(
        second_owner,
        "first",
        second_receiver,
        receiver_side="inside",
        nominal_base_mm=0.24,
        min_glue_area_mm2=1,
    )
    printable = project.material_part_ids()
    window.controller.project = project
    window.refresh()
    window.select_surface(first_owner)
    panel = window.curved_panel
    panel.sets.setCurrentIndex(panel.sets.findData(first))
    window.selected_edge = (first_owner, project.profiles[a].segments[0].id)
    window.selected_vertex = (a, project.profiles[a].vertices[0].id)
    window.current_joint = "previous-selected-relationship"
    panel.sets.setCurrentIndex(panel.sets.findData(second))
    assert window.selected_surface == second_owner
    assert window.selected_edge is None and window.current_joint is None
    assert window.selected_vertex[0] == second_a
    assert window.vertex_choice.currentData() == window.selected_vertex
    assert window.selected_profile == second_a
    assert window.viewport.selected_surfaces == {second_owner}
    assert window.viewport.related_surfaces == {second_owner, second_receiver}
    assert window.tree.currentItem().data(0, Qt.ItemDataRole.UserRole) == second_owner
    assert project.material_part_ids() == printable


def test_async_queue_keeps_one_latest_requested_draft(qtbot, source):
    entered, release = threading.Event(), threading.Event()
    calls = []

    def callback(project, request):
        calls.append(copy.deepcopy(request))
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        return unresolved(project, request)

    _project, widget = make_dialog(qtbot, source, callback)
    try:
        widget.request_preview()
        qtbot.waitUntil(entered.is_set)
        widget.fields["relief_mm"].setValue(0.7)
        widget.request_preview()
        widget.fields["relief_mm"].setValue(0.8)
        widget.request_preview()
        assert len(calls) == 1 and widget._pending is not None
    finally:
        release.set()
    finish(qtbot, widget)
    assert len(calls) == 2
    assert widget._packet["request"]["parameters"]["relief_mm"] == 0.8


@pytest.mark.parametrize("malformed", ["message", "status", "slot_pool"])
def test_bad_preview_cannot_enable_or_partly_publish_success(qtbot, source, malformed):
    def callback(project, request):
        result = unresolved(project, request)
        if malformed == "message":
            result["message"] = None
        elif malformed == "status":
            result["can_confirm"] = True
        else:
            result["slot_ids"] = []
        return result

    project, widget = make_dialog(qtbot, source, callback)
    before = project.to_dict(validate=False)
    widget.request_preview()
    finish(qtbot, widget)
    assert widget._packet is None and not widget.apply_button.isEnabled()
    assert project.to_dict(validate=False) == before


@pytest.mark.parametrize("problem", ["unknown_paper", "excessive_width"])
def test_real_material_or_width_problem_remains_a_repairable_unverified_draft(
    qtbot, source, problem
):
    project, owner, receiver = restore(source)
    if problem == "unknown_paper":
        project.set_material_profile(thickness_mm=None)
    widget = CurvedConnectorDialog(project, owner)
    qtbot.addWidget(widget)
    widget.show()
    widget.receiver.setCurrentIndex(widget.receiver.findData(receiver))
    if problem == "excessive_width":
        widget.fields["nominal_base_mm"].setValue(5)
    before = project.to_dict(validate=False)
    widget.request_preview()
    finish(qtbot, widget)
    assert widget._packet is not None, widget.feedback.text()
    assert widget._packet["status"] != "CERTIFIED_APPROXIMATE"
    assert not widget.apply_button.isEnabled() and widget.retain.isVisible()
    assert not widget.paper_preview.scene().items()
    assert "není digitálně doložený" in widget.feedback.text()
    assert project.to_dict(validate=False) == before


def test_main_window_action_creates_authored_intent_and_leaves_explicit_recompute(
    window, qtbot, source
):
    project, owner, receiver = restore(source)
    window.controller.project = project
    window.refresh()
    window.select_surface(owner)
    errors = []

    def complete_dialog():
        from PySide6.QtWidgets import QApplication

        widget = QApplication.activeModalWidget()
        try:
            assert isinstance(widget, CurvedConnectorDialog)
            widget.receiver.setCurrentIndex(widget.receiver.findData(receiver))
            widget.request_preview()
            finish(qtbot, widget)
            assert widget._packet["status"] == "CERTIFIED_APPROXIMATE", widget.feedback.text()
            qtbot.mouseClick(widget.apply_button, Qt.MouseButton.LeftButton)
        except BaseException as exc:
            errors.append(exc)
            widget.reject()

    QTimer.singleShot(0, complete_dialog)
    window.actions["curved_connector"].trigger()
    assert not errors
    assert len(project.curved_connectors) == 1
    cid = next(iter(project.curved_connectors))
    assert window.curved_panel.current_id == cid
    assert window.selected_surface == owner
    assert project.parts[project.part_for_surface(owner)].stale
    assert project.curved_connector_status(cid)["status"] == "STALE"
    assert window.paper.curved_overlay is None and not window.viewport.relation_paths


def test_material_link_is_staged_with_draft_and_cancel_preserves_whole_document(qtbot, source):
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.author_material import MaterialDialog

    project, widget = make_dialog(qtbot, source, unresolved)
    before = project.to_dict(validate=False)
    errors = []

    def choose_paper():
        dialog = QApplication.activeModalWidget()
        try:
            assert isinstance(dialog, MaterialDialog)
            dialog.fields["thickness_mm"].setValue(0.25)
            dialog.confirm()
        except BaseException as exc:
            errors.append(exc)
            dialog.reject()

    QTimer.singleShot(0, choose_paper)
    qtbot.mouseClick(widget.material_button, Qt.MouseButton.LeftButton)
    assert not errors
    assert widget.parameters()["material_profile"]["thickness_mm"] == 0.25
    assert project.to_dict(validate=False) == before
    widget.reject()
    assert project.to_dict(validate=False) == before


def test_unknown_paper_can_be_repaired_in_dialog_then_committed_with_intent_in_one_undo(
    qtbot, source
):
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.author_material import MaterialDialog

    project, owner, receiver = restore(source)
    project.set_material_profile(thickness_mm=None)
    before = project.to_dict(validate=False)
    widget = CurvedConnectorDialog(project, owner)
    qtbot.addWidget(widget)
    widget.show()
    widget.receiver.setCurrentIndex(widget.receiver.findData(receiver))

    def measured_paper():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, MaterialDialog)
        dialog.known.setChecked(True)
        dialog.fields["thickness_mm"].setValue(0.2)
        dialog.confirm()

    QTimer.singleShot(0, measured_paper)
    qtbot.mouseClick(widget.material_button, Qt.MouseButton.LeftButton)
    assert project.material_profile["thickness_mm"] is None
    widget.request_preview()
    finish(qtbot, widget)
    assert widget._packet["status"] == "CERTIFIED_APPROXIMATE", widget.feedback.text()
    widget.accept()
    controller = AuthorController()
    controller.project = project
    controller.execute("Papír a kruhové chlopně", widget.apply)
    assert project.material_profile["thickness_mm"] == 0.2
    assert len(project.curved_connectors) == 1
    controller.undo()
    assert controller.project.to_dict(validate=False) == before


def test_curved_issue_selects_exact_set_for_repair_without_current_geometry(window, source):
    project, owner, receiver = restore(source)
    cid = project.add_curved_connector(
        owner, "first", receiver, receiver_side="inside", nominal_base_mm=0.24, min_glue_area_mm2=1
    )
    window.controller.project = project
    window.refresh()
    item = next(
        window.issues.item(i)
        for i in range(window.issues.count())
        if window.issues.item(i).data(Qt.ItemDataRole.UserRole) == "curved:" + cid
    )
    window.select_issue(item)
    assert window.curved_panel.current_id == cid and window.selected_surface == owner
    assert window.curved_panel.edit.isEnabled()
    assert not window.viewport.relation_paths and window.paper.curved_overlay is None


@pytest.mark.parametrize(
    "r1,height,side",
    [
        (10, 30, "second"),
        (20, math.sqrt(800), "first"),
        (20, math.sqrt(800), "second"),
        (10.000001, 30, "first"),
    ],
)
def test_actual_dialog_supported_circular_bodies_and_both_rims_are_approximate_connectors(
    qtbot, r1, height, side
):
    project, owner, _part = authored(10, r1, height)
    radius, z = (10, 0) if side == "first" else (r1, height)
    receiver = project.add_surface(circle(project, radius, z))
    project.set_material_profile(thickness_mm=0.2, clearance_mm=0.01, bend_radius_mm=0)
    project.recompute()
    widget = CurvedConnectorDialog(project, owner)
    qtbot.addWidget(widget)
    widget.show()
    widget.rim.setCurrentIndex(widget.rim.findData(side))
    widget.receiver.setCurrentIndex(widget.receiver.findData(receiver))
    widget.receiver_side.setCurrentIndex(
        widget.receiver_side.findData("inside" if side == "first" else "outside")
    )
    widget.request_preview()
    finish(qtbot, widget)
    assert widget._packet is not None, widget.feedback.text()
    assert widget._packet["status"] == "CERTIFIED_APPROXIMATE", widget.feedback.text()
    geometry = widget._packet["geometry"]
    assert geometry["mode"] == "APPROXIMATE" and geometry["rim_side"] == side
    assert len(geometry["all_tabs"]) == 12
    assert geometry["all_tabs"][0]["assembled_display"]["hinge_world"][0][2] == pytest.approx(z)
    assert project.loft_status(owner)["status"] == "EXACT"


def two_authored_rim_sets(window, source):
    project, owner, receiver = restore(source)
    first = project.add_curved_connector(
        owner, "first", receiver, receiver_side="inside", nominal_base_mm=0.24, min_glue_area_mm2=1
    )
    top = project.add_surface(circle(project, 10, 30))
    second = project.add_curved_connector(
        owner, "second", top, receiver_side="outside", nominal_base_mm=0.24, min_glue_area_mm2=1
    )
    window.controller.project = project
    window.refresh()
    window.select_surface(owner)
    panel = window.curved_panel
    panel.sets.setCurrentIndex(panel.sets.findData(first))
    return project, panel, first, second


def invalid_vertex_input(window, qtbot):
    field = window.vertex_x.lineEdit()
    field.setFocus()
    field.selectAll()
    qtbot.keyClick(field, Qt.Key.Key_Backspace)
    assert not window.vertex_x.hasAcceptableInput()
    return field.text()


def test_failed_numeric_preflight_restores_set_choice_and_keeps_raw_input_owner_context(
    window, source, qtbot
):
    project, panel, first, second = two_authored_rim_sets(window, source)
    before = project.to_dict(validate=False)
    owner, selected_tab, relation = (
        window.selected_surface,
        panel.tabs.currentData(),
        window.viewport.relation,
    )
    tree = window.tree.currentItem()
    raw = invalid_vertex_input(window, qtbot)
    panel.sets.setCurrentIndex(panel.sets.findData(second))
    assert panel.current_id == panel.sets.currentData() == first
    assert project.to_dict(validate=False) == before
    assert window.selected_surface == owner and window.tree.currentItem() is tree
    assert panel.tabs.currentData() == selected_tab and window.viewport.relation == relation
    assert window.vertex_x.lineEdit().text() == raw
    assert not window.vertex_x.hasAcceptableInput()


def test_failed_numeric_preflight_restores_whole_set_checkbox_without_touching_authored_state(
    window, source, qtbot
):
    project, panel, first, _second = two_authored_rim_sets(window, source)
    before = project.to_dict(validate=False)
    owner, selected_tab, relation = (
        window.selected_surface,
        panel.tabs.currentData(),
        window.viewport.relation,
    )
    assert project.curved_connectors[first].enabled and panel.set_enabled.isChecked()
    raw = invalid_vertex_input(window, qtbot)
    panel.set_enabled.setChecked(False)
    assert panel.set_enabled.isChecked() is project.curved_connectors[first].enabled is True
    assert panel.current_id == panel.sets.currentData() == first
    assert project.to_dict(validate=False) == before
    assert window.selected_surface == owner and panel.tabs.currentData() == selected_tab
    assert window.viewport.relation == relation
    assert window.vertex_x.lineEdit().text() == raw and not window.vertex_x.hasAcceptableInput()


def test_current_circular_connector_guidance_matches_real_certification_and_next_step(
    window, positive
):
    state, owner, _receiver, cid = positive
    window.controller.project = AuthorProject.from_dict(copy.deepcopy(state))
    window.refresh()
    window.select_surface(owner)
    window.curved_panel.sets.setCurrentIndex(window.curved_panel.sets.findData(cid))
    window.update_guidance()
    assert window.project.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE"
    assert "digitálně doložená APROXIMACE" in window.hint.text()
    assert "zatím nemá ověřený spoj" not in window.hint.text()
    assert "Ctrl+R" in window.hint.text() and "P3" in window.hint.text()


def test_circular_guidance_does_not_grant_current_certification_to_stale_or_unresolved(
    window, positive, monkeypatch
):
    state, owner, _receiver, cid = positive
    window.controller.project = AuthorProject.from_dict(copy.deepcopy(state))
    window.refresh()
    window.select_surface(owner)
    window.curved_panel.sets.setCurrentIndex(window.curved_panel.sets.findData(cid))
    window.project.update_curved_connector(cid, nominal_base_mm=0.25)
    window.refresh()
    assert window.project.curved_connector_status(cid)["status"] == "STALE"
    assert "čekají na aktuální přepočet" in window.hint.text()
    assert "digitálně doložená" not in window.hint.text()
    # This last branch tests consuming an explicit public status, not geometry.
    monkeypatch.setattr(
        window.project, "curved_connector_status", lambda _cid: {"status": "UNRESOLVED"}
    )
    window.update_guidance()
    assert "není digitálně doložený" in window.hint.text()
    assert "digitálně doložená APROXIMACE" not in window.hint.text()
    assert "opravte" in window.hint.text() and "P3" in window.hint.text()


@pytest.mark.parametrize("running", [False, True])
def test_deleted_dialog_owner_invalidates_safely_and_discards_any_late_preview(
    qtbot, source, running
):
    entered, release = threading.Event(), threading.Event()

    def callback(project, request):
        entered.set()
        assert release.wait(5)
        return unresolved(project, request)

    project, widget = make_dialog(qtbot, source, callback if running else unresolved)
    depth = widget.fields["depth_mm"].value()
    try:
        if running:
            widget.request_preview()
            qtbot.waitUntil(entered.is_set)
        from archpapercraft.authoring.editing import delete_material_part

        delete_material_part(project, project.part_for_surface(widget.owner_id))
        widget._source_changed()
        assert not widget.compute.isEnabled() and not widget.apply_button.isEnabled()
        assert widget._packet is None and widget._pending is None
        assert "Zavřete tento návrh" in widget.feedback.text()
        assert widget.fields["depth_mm"].value() == depth
        assert widget.request_preview() is False
    finally:
        release.set()
    finish(qtbot, widget)
    assert widget._packet is None and not widget.compute.isEnabled()
    assert "Zavřete tento návrh" in widget.feedback.text()


@pytest.mark.parametrize("inactive", ["outside_count", "whole_set_disabled"])
def test_inactive_slot_action_explains_context_without_changing_latent_override(
    window, positive, inactive
):
    state, owner, _receiver, cid = positive
    project = AuthorProject.from_dict(copy.deepcopy(state))
    if inactive == "outside_count":
        project.update_curved_connector(cid, count=8)
        index = 10
    else:
        project.update_curved_connector(cid, enabled=False)
        index = 2
    window.controller.project = project
    window.refresh()
    window.select_surface(owner)
    panel = window.curved_panel
    panel.sets.setCurrentIndex(panel.sets.findData(cid))
    panel.tabs.setCurrentIndex(index)
    before = project.to_dict(validate=False)
    assert not panel.toggle.isEnabled()
    assert (
        "mimo aktuální počet" if inactive == "outside_count" else "sada je vypnutá"
    ) in panel.toggle.text()
    assert panel.toggle.toolTip()
    panel.toggle.click()
    panel.toggle_tab()  # The public handler also guards obsolete/action-disabled calls.
    assert project.to_dict(validate=False) == before
