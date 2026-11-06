"""Optional measured-paper UI, with safe pending input and no precision drift."""

import copy

import pytest
from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QDialog

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_material import MaterialDialog

pytestmark = pytest.mark.ui


def test_material_dialog_pending_number_and_cancel_do_not_mutate_live_project(qtbot):
    project = AuthorProject.new()
    before = copy.deepcopy(project.to_dict())
    dialog = MaterialDialog(project)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.known.setChecked(True)
    field = dialog.fields["thickness_mm"]
    field.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(field, "0.35")
    dialog.confirm()  # Deliberately no Return/focusOut before snapshotting dialog input.
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_profile["thickness_mm"] == 0.35
    assert project.to_dict() == before
    cancelled = MaterialDialog(project)
    qtbot.addWidget(cancelled)
    cancelled.fields["crease_zone_mm"].setValue(3)
    cancelled.reject()
    assert cancelled.result_profile is None and project.to_dict() == before


def test_material_noop_preserves_unrounded_values_and_invalid_pending_number_stops(qtbot):
    project = AuthorProject.new()
    project.set_material_profile(thickness_mm=0.123456789, clearance_mm=0.000001234567,
                                 bend_radius_mm=0.000002345678, crease_zone_mm=0.765432109)
    before = copy.deepcopy(project.to_dict())
    dialog = MaterialDialog(project)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.confirm()
    assert dialog.result_profile == project.material_profile
    project.set_material_profile(**dialog.result_profile)
    assert project.to_dict() == before
    invalid = MaterialDialog(project)
    qtbot.addWidget(invalid)
    invalid.show()
    field = invalid.fields["clearance_mm"]
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(field, Qt.Key.Key_Backspace)
    invalid.confirm()
    assert invalid.result() != QDialog.DialogCode.Accepted
    assert invalid.result_profile is None and project.to_dict() == before
    assert invalid.feedback.text()
