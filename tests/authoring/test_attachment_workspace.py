"""Real Qt commands and preview, distinct from native proof and novice evidence."""

import copy
import json

import numpy as np
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, load_project
from archpapercraft.ui.author_attachment import AttachmentDialog

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
