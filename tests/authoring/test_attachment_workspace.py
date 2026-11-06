"""Real Qt commands and preview, distinct from native proof and novice evidence."""

import copy
import json

import numpy as np
import pytest
from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QMessageBox
from test_folded_registry import mixed_connectors

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, load_project
from archpapercraft.ui.author_attachment import AttachmentDialog, GlueRegionDialog
from archpapercraft.ui.author_viewport import AuthorViewport
from archpapercraft.ui.author_window import AuthorMainWindow

pytestmark = pytest.mark.ui


def construction():
    project = AuthorProject.new(scale=1)
    profile = project.add_profile([[0, 0], [40, 0], [40, 20], [0, 20]])
    source = project.add_surface(profile, name="Wall")
    target = project.add_surface(
        project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]), name="Base"
    )
    return project, source, target, project.profiles[profile].segments[0].id


def dialog_for(qtbot, project, source, target, edge):
    dialog = AttachmentDialog(project, (source, edge), unit="mm", unit_factor=1)
    qtbot.addWidget(dialog)
    dialog.receiver.setCurrentIndex(dialog.receiver.findData(target))
    dialog.show()
    qtbot.wait(50)
    return dialog


def draw_trace(qtbot, dialog, points):
    qtbot.mouseClick(dialog.draw_line, Qt.MouseButton.LeftButton)
    for x, y in points:
        qtbot.mouseClick(
            dialog.sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=dialog.sketch.mapFromScene(QPointF(x, -y)),
        )
    qtbot.keyClick(dialog.sketch, Qt.Key.Key_Return)


def test_draw_receiving_line_preview_cancel_and_apply_roundtrip(qtbot, tmp_path):
    project, source, target, edge = construction()
    before = copy.deepcopy(project.to_dict())
    dialog = dialog_for(qtbot, project, source, target, edge)
    # Snap grid is model-scaled in the normal workspace; this fixture is paper mm.
    dialog.sketch.grid_mm = 1
    draw_trace(qtbot, dialog, [(20, 30), (60, 30)])
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(), (
        dialog.feedback.text(), dialog.sketch.trace, dialog.sketch.points
    )
    assert project.to_dict() == before  # Drawing/preview never moves the original wall.
    dialog.reject()
    assert project.to_dict() == before and dialog.result_spec is None

    dialog = dialog_for(qtbot, project, source, target, edge)
    dialog.sketch.grid_mm = 1
    draw_trace(qtbot, dialog, [(20, 30), (60, 30)])
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    assert dialog.result() == QDialog.DialogCode.Accepted
    controller = AuthorController()
    controller.new()
    controller.project = project
    aid = controller.execute("Attach", lambda p: AttachmentDialog.apply(p, dialog.result_spec))
    contact = project.attachment_geometry(aid)
    # Clicks have finite pixel resolution; the edge still has its exact original length.
    assert contact["material_length_mm"] == pytest.approx(40)
    np.testing.assert_allclose(contact["source_world"][0], [20, 30, 0], atol=0.5)
    assert len(project.surfaces) == 2 and len(project.attachments) == 1
    controller.save(tmp_path / "own-interior.apcraft")
    assert load_project(controller.file_path).attachments[aid].source_edge_id == edge
    controller.undo()
    assert controller.project.to_dict() == before
    controller.redo()
    assert controller.project.attachment_geometry(aid)["valid"]


def test_receiver_hole_blocks_contact_preview_without_mutating_project(qtbot):
    project, source, target, edge = construction()
    hole = project.add_profile([[30, 20], [50, 20], [50, 40], [30, 40]])
    project.add_hole(target, hole)
    before = copy.deepcopy(project.to_dict())
    dialog = dialog_for(qtbot, project, source, target, edge)
    for field, value in zip(dialog.fields, [20, 30, 60, 30]):
        field.setValue(value)
    dialog.numeric_trace()
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert "OUTSIDE_MATERIAL" in dialog.feedback.text()
    dialog.confirm()
    assert dialog.result() != QDialog.DialogCode.Accepted and project.to_dict() == before


def test_pending_angle_before_confirmation_matches_preview(qtbot):
    project, source, target, edge = construction()
    dialog = dialog_for(qtbot, project, source, target, edge)
    for field, value in zip(dialog.fields, [20, 30, 60, 30]):
        field.setValue(value)
    dialog.numeric_trace()
    dialog.angle.setFocus()
    qtbot.keyClick(dialog.angle, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(dialog.angle, "45")
    dialog.confirm()  # No Return/focusOut before the snapshot.
    assert dialog.result_spec["angle_deg"] == 45
    clone = AuthorProject.from_dict(project.to_dict())
    aid = AttachmentDialog.apply(clone, dialog.result_spec)
    assert clone.attachment_geometry(aid)["valid"]


def test_schema_one_copy_policy_survives_command_undo_and_failed_save(tmp_path):
    project, *_ = construction()
    data = project.to_dict()
    data.update(schema_version=1, writer_version="0.3.0-experimental")
    data.pop("attachments")
    data.pop("next_attachment_number")
    data.pop("material_profile")
    origin = tmp_path / "author-v1.apcraft"
    origin.write_text(json.dumps(data), encoding="utf8")
    original = origin.read_bytes()
    controller = AuthorController()
    controller.open(origin)
    assert controller.copy_source_path == origin and controller.file_path is None
    controller.execute("Rename", lambda p: setattr(p, "name", "Own copy"))
    controller.undo()
    controller.redo()
    with pytest.raises(ValueError, match="kopii"):
        controller.save(origin)
    assert origin.read_bytes() == original and controller.copy_source_path == origin
    target = tmp_path / "author-v2-copy.apcraft"
    controller.save(target)
    assert origin.read_bytes() == original and controller.file_path == target
    assert controller.copy_source_path is None and load_project(target).name == "Own copy"


def test_drawn_glue_region_is_contact_area_not_a_cutout_and_rejects_hole(qtbot):
    project = AuthorProject.new(scale=1)
    source = project.add_surface(
        project.add_profile([[20, 20], [40, 20], [40, 40], [20, 40]])
    )
    target = project.add_surface(
        project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]])
    )
    before = copy.deepcopy(project.to_dict())
    dialog = GlueRegionDialog(project, source, unit="mm", unit_factor=1)
    qtbot.addWidget(dialog)
    dialog.receiver.setCurrentIndex(dialog.receiver.findData(target))
    dialog.show()
    qtbot.wait(50)
    dialog.target_sketch.grid_mm = 1
    qtbot.mouseClick(dialog.draw_target, Qt.MouseButton.LeftButton)
    for x, y in [(10, 10), (50, 10), (50, 50), (10, 50)]:
        qtbot.mouseClick(
            dialog.target_sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=dialog.target_sketch.mapFromScene(QPointF(x, -y)),
        )
    qtbot.keyClick(dialog.target_sketch, Qt.Key.Key_Return)
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(), (
        dialog.feedback.text(), dialog.target_sketch.region
    )
    assert project.to_dict() == before
    dialog.confirm()
    aid = GlueRegionDialog.apply(project, dialog.result_spec)
    geometry = project.attachment_geometry(aid)
    assert geometry["available_area_mm2"] == pytest.approx(400)
    assert not project.surfaces[target].hole_profile_ids
    assert len(project.parts[project.part_for_surface(target)].polygons[target]) == 1
    # A new opening removes actual adhesive material despite unchanged plan outline.
    project.add_hole(target, project.add_profile([[25, 25], [30, 25], [30, 30], [25, 30]]))
    assert not project.attachment_geometry(aid)["valid"]
    assert any(i.code == "ATTACHMENT_CONTACT" for i in project.validate_layout())


def test_partial_edge_interval_stays_explicit_in_the_authoring_command(qtbot):
    project, source, target, edge = construction()
    dialog = dialog_for(qtbot, project, source, target, edge)
    for field, value in zip(dialog.fields, [20, 30, 60, 30]):
        field.setValue(value)
    dialog.numeric_trace()
    dialog.start_fraction.setValue(25)
    dialog.end_fraction.setValue(75)
    dialog.interval_changed()
    dialog.confirm()
    assert dialog.result_spec["interval"] == [0.25, 0.75]
    aid = AttachmentDialog.apply(project, dialog.result_spec)
    geometry = project.attachment_geometry(aid)
    assert geometry["material_length_mm"] == pytest.approx(20)
    np.testing.assert_allclose(geometry["source_world"], [[20, 30, 0], [40, 30, 0]])


def test_linked_receiver_overlay_shows_actual_folded_material_and_hides_invalid_contact(qtbot):
    project, source, target, edge = construction()
    aid = project.place_and_attach_edge(source, edge, target, [20, 30], [60, 30])
    project.set_attachment_tab(aid, width_mm=4, taper=1)
    viewport = AuthorViewport()
    qtbot.addWidget(viewport)
    viewport.set_project(project)
    viewport.select_relation(("attachment", aid))
    assert len(viewport.relation_paths) == 2  # Hinge and actual folded outline.
    np.testing.assert_allclose(viewport.relation_paths[0][0], [[20, 30, 0], [60, 30, 0]])
    np.testing.assert_allclose(
        viewport.relation_paths[1][0],
        [[20, 30, 0], [60, 30, 0], [60, 34, 0], [20, 34, 0]], atol=1e-10,
    )
    project.set_transform(source, [0, 0, 1])
    viewport.set_project(project)
    assert viewport.relation_paths == [] and "opravu" in viewport.relation_status
    viewport.select_relation(None)
    assert viewport.relation_paths == [] and viewport.relation_status == ""


def test_upgrade_workspace_explains_copy_and_offers_a_new_filename(qtbot, tmp_path, monkeypatch):
    project, *_ = construction()
    data = project.to_dict()
    data.update(schema_version=1, writer_version="0.3.0-experimental")
    del data["attachments"], data["next_attachment_number"], data["material_profile"]
    origin = tmp_path / "original-author.apcraft"
    origin.write_text(json.dumps(data), encoding="utf8")
    original = origin.read_bytes()
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = AuthorMainWindow(settings=settings)
    qtbot.addWidget(window)
    messages, offered = [], []
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(origin), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: messages.append(a[2]))
    window.open_project()
    assert window.controller.file_path is None and window.controller.copy_source_path == origin
    assert any("Původní soubor" in text for text in messages)
    target = tmp_path / "original-author-copy.apcraft"

    def save_dialog(*args, **kwargs):
        offered.append(args[2])
        return str(target), ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", save_dialog)
    assert window.save_project()
    assert offered == [str(target)]
    assert origin.read_bytes() == original and target.is_file()
    assert load_project(target).name == project.name


def test_relationship_selection_and_issue_repair_target_are_shared_between_panels(qtbot, tmp_path):
    project, _, other_cid, joint, receiver = mixed_connectors()
    aid = project.connectors[other_cid].attachment_id
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = AuthorMainWindow(settings=settings)
    qtbot.addWidget(window)
    window.controller.project = project
    window.controller._saved_digest = window.controller.digest(project.to_dict())
    window.refresh()
    window.select_surface(receiver)
    window.show()
    qtbot.wait(40)
    choice = window.connectors_panel.relationship
    choice.setFocus()
    qtbot.keyClick(choice, Qt.Key.Key_End)
    assert choice.currentData() == ("attachment", aid) and window.current_joint is None
    assert window.joint_choice.currentIndex() == -1
    assert not window.edge_form.isRowVisible(window.tab_owner)
    assert window.viewport.relation == ("attachment", aid)
    assert window.viewport.related_surfaces == {
        project.attachments[aid].source_surface_id, receiver
    }
    qtbot.keyClick(choice, Qt.Key.Key_Home)
    assert choice.currentData() == ("joint", joint) and window.current_joint == joint
    assert window.joint_choice.currentData() == joint
    assert window.edge_form.isRowVisible(window.tab_owner)
    issue = next(i for i in project.validate_layout() if i.code == "FOLDED_SIDE_UNRESOLVED")
    item = next(
        window.issues.item(index) for index in range(window.issues.count())
        if window.issues.item(index).data(Qt.ItemDataRole.UserRole) == issue.id
    )
    window.select_issue(item)
    assert window.connectors_panel.current_relation == ("attachment", aid)
    assert window.viewport.relation == ("attachment", aid) and window.current_joint is None
    window.clear_selection()
    assert window.connectors_panel.current_relation is None
    assert window.viewport.related_surfaces == set() and window.viewport.relation is None
    window.viewport.center = np.array([700.0, 800.0, 900.0])
    window.viewport.setFocus()
    qtbot.keyClick(window.viewport, Qt.Key.Key_Home)
    np.testing.assert_allclose(window.viewport.center, [50, 50, 10])
    assert not window.controller.dirty  # Selection and repair navigation never edit the model.
