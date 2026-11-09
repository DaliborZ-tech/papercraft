"""Actual host/widget/core integration; offscreen checks are not novice proof."""

import copy

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from test_workspace import window as _window_fixture

from archpapercraft.authoring.editing import part_deletion_impact
from archpapercraft.ui.author_loft import LoftProfilesDialog

pytestmark = pytest.mark.ui
window = _window_fixture


def sources(window):
    def create(p):
        first = p.add_profile([[0, 0], [2000, 0], [2000, 1000]], closed=False)
        second = p.copy_profile(
            first,
            plane={
                "origin": [0, 0, 1000],
                "u": [1, 0, 0],
                "v": [0, 1, 0],
            },
        )
        return first, second

    return window.controller.execute("Two authored sources", create)


def accept_actual_preview(qtbot, monkeypatch):
    def execute(dialog):
        dialog.confirm_pairs.setChecked(True)
        assert dialog.request_preview()
        qtbot.waitUntil(lambda: dialog._running_job is None, timeout=30000)
        assert dialog.apply_button.isEnabled(), dialog.feedback.text()
        dialog.accept()
        return dialog.result()

    monkeypatch.setattr(LoftProfilesDialog, "exec", execute)


def test_actual_host_creates_loft_as_one_command_and_keeps_both_source_sketches(
    window,
    qtbot,
    monkeypatch,
):
    assert not window.actions["loft"].isEnabled()
    a, b = sources(window)
    window.select_profile(a)
    before = copy.deepcopy(window.project.to_dict())
    undo_depth = len(window.controller._undo)
    accept_actual_preview(qtbot, monkeypatch)
    window.actions["loft"].trigger()
    assert not window._test_warnings
    sid = window.selected_surface
    surface = window.project.surfaces[sid]
    assert surface.kind == "ruled_loft" and surface.source_profile_ids() == [a, b]
    assert len(window.controller._undo) == undo_depth + 1
    assert window.sketch.surface_id is None and window.sketch.profile_id == a
    assert a in window.viewport.profile_paths and b in window.viewport.profile_paths
    assert window.curve_choice.count() == 4
    assert not window.actions["hole"].isEnabled()
    assert window.actions["edit_loft"].isEnabled()
    assert window.actions["profile_plane"].isEnabled()
    root = window.tree.topLevelItem(0)
    assert root.childCount() == 2
    assert root.child(1).data(0, Qt.ItemDataRole.UserRole) == ("profile", b)
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before
    window.actions["redo"].trigger()
    assert sid in window.project.surfaces


def test_second_source_selection_and_cancelled_loft_edit_preserve_authored_work(
    window,
    qtbot,
    monkeypatch,
):
    a, b = sources(window)
    window.select_profile(a)
    accept_actual_preview(qtbot, monkeypatch)
    window.actions["loft"].trigger()
    sid = window.selected_surface
    segment = window.project.profiles[b].segments[0].id
    window.select_edge(sid, segment)
    assert window.selected_profile == b
    assert window.sketch.profile_id == b and window.sketch.surface_id is None
    assert window.curve_choice.currentData() == (b, segment)
    before = copy.deepcopy(window.project.to_dict())
    monkeypatch.setattr(LoftProfilesDialog, "exec", lambda d: QDialog.DialogCode.Rejected)
    window.actions["edit_loft"].trigger()
    assert window.project.to_dict() == before
    assert not window._test_warnings


def test_actual_existing_loft_preview_updates_without_duplicating_source_ids(
    window,
    qtbot,
    monkeypatch,
):
    a, _ = sources(window)
    window.select_profile(a)
    accept_actual_preview(qtbot, monkeypatch)
    window.actions["loft"].trigger()
    sid = window.selected_surface
    part_id = window.selected_part
    surface = copy.deepcopy(window.project.surfaces[sid])
    window.actions["edit_loft"].trigger()
    assert not window._test_warnings
    assert window.selected_surface == sid and window.selected_part == part_id
    assert window.project.surfaces[sid].params == surface.params
    assert len(window.project.surfaces) == 1
    impact = part_deletion_impact(window.project, part_id)
    assert {p["id"] for p in impact["preserved_profiles"]} == set(surface.source_profile_ids())
