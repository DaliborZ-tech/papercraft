"""Actual authoring widgets and input; these are not novice-user observations."""

from copy import deepcopy

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QMessageBox,
)

from archpapercraft.ui.author_sketch import VertexHandle
from archpapercraft.ui.author_window import AuthorMainWindow

pytestmark = pytest.mark.ui


def switch_workspace(qtbot, window, context):
    qtbot.mouseClick(window.workspace_bar.buttons[context], Qt.MouseButton.LeftButton)
    qtbot.wait(5)


def test_profile_section_respects_collapse_across_surface_selection_and_refresh(window, qtbot):
    from PySide6.QtWidgets import QScrollArea

    first = arrange_rectangle(window)
    second = arrange_rectangle(window, name="Druha vlastni plocha")
    header, body = window.sections["Profil a křivky"]
    assert header.isVisible() and not header.isChecked() and not body.isVisible()
    window.select_surface(first)
    window.refresh()
    assert not header.isChecked() and not body.isVisible()
    window.properties_dock.findChild(QScrollArea).ensureWidgetVisible(header)
    qtbot.mouseClick(header, Qt.MouseButton.LeftButton)
    assert header.isChecked() and body.isVisible()
    window.select_surface(second)
    window.refresh()
    assert header.isChecked() and body.isVisible()
    window.properties_dock.findChild(QScrollArea).ensureWidgetVisible(header)
    qtbot.mouseClick(header, Qt.MouseButton.LeftButton)
    window.select_surface(first)
    window.refresh()
    assert not header.isChecked() and not body.isVisible()


def test_activity_context_preserves_document_selection_history_and_placements(window, qtbot):
    from pathlib import Path

    import archpapercraft.ui.author_window as module

    assert Path(module.__file__).resolve() == (
        Path(__file__).resolve().parents[2] / "src/archpapercraft/ui/author_window.py"
    )
    sid = arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    history = len(window.controller._undo)
    selection = (window.selected_surface, window.selected_profile, window.selected_vertex)
    window.resize(1366, 768)
    assert window.width() == 1366
    assert window.viewport.isVisible() and not window.sketch.isVisible()
    assert not window.paper.isVisible()
    for context in ("Spoje a rozvin", "Stránky", "Export", "Modelování"):
        switch_workspace(qtbot, window, context)
        assert window.workspace_context == context
        assert window.project.to_dict() == before
        assert len(window.controller._undo) == history
        assert (window.selected_surface, window.selected_profile,
                window.selected_vertex) == selection
        assert window.viewport.selected_surfaces == {sid}
        assert window.paper.selected_part == window.selected_part
    assert window.section_containers["Bod obrysu"].isVisible()
    assert not window.section_containers["Hrany, spoj a chlopeň"].isVisible()
    assert window.actions["export"].isVisible()  # Advanced menus remain available.
    assert not window.toolbar_actions["export"].isVisible()


@pytest.mark.parametrize("raw", ["", "-"])
def test_rejected_context_restores_visible_mode_and_raw_edit(window, qtbot, raw):
    arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    field = window.vertex_x
    field.setFocus()
    field.lineEdit().selectAll()
    field.lineEdit().setText(raw)
    assert not field.hasAcceptableInput()
    switch_workspace(qtbot, window, "Stránky")
    assert window.workspace_context == "Modelování"
    assert window.workspace_bar.buttons["Modelování"].isChecked()
    assert not window.workspace_bar.buttons["Stránky"].isChecked()
    assert field.lineEdit().text() == raw
    assert field.hasFocus()
    assert window.project.to_dict() == before
    assert window._test_warnings
    field.lineEdit().setText("0")  # Leave a valid field for teardown.


def test_switch_commits_valid_pending_edit_and_rejects_invalid_geometry(window, qtbot):
    sid = arrange_rectangle(window)
    window.vertex_choice.setCurrentIndex(1)
    vertex_id = window.selected_vertex[1]
    window.vertex_x.setFocus()
    window.vertex_x.lineEdit().selectAll()
    qtbot.keyClicks(window.vertex_x, "11")  # Default units are metres.
    switch_workspace(qtbot, window, "Stránky")
    assert profile_of(window, sid).vertex(vertex_id).point == [11000.0, 0.0]
    assert window.workspace_context == "Stránky"
    window.actions["undo"].trigger()
    assert profile_of(window, sid).vertex(vertex_id).point == [10000.0, 0.0]
    switch_workspace(qtbot, window, "Modelování")
    window.vertex_x.setFocus()
    window.vertex_x.lineEdit().selectAll()
    qtbot.keyClicks(window.vertex_x, "0")  # Coincident vertex is rejected by the command.
    switch_workspace(qtbot, window, "Export")
    assert window.workspace_context == "Modelování"
    assert window.vertex_x.lineEdit().text().startswith("0")
    assert profile_of(window, sid).vertex(vertex_id).point == [10000.0, 0.0]


def test_active_fit_and_refresh_preserve_other_cameras(window, qtbot):
    arrange_rectangle(window)
    switch_workspace(qtbot, window, "Stránky")
    window.paper.scale(1.7, 1.7)
    paper_transform = window.paper.transform()
    window.viewport.span = 12345
    window.viewport.pan[:] = [31, 42]
    window.refresh()
    qtbot.wait(5)
    assert window.paper.transform() == paper_transform
    assert window.viewport.span == 12345 and list(window.viewport.pan) == [31, 42]
    window.paper.setFocus()
    window.focus_all()
    assert window.paper.transform() != paper_transform
    assert window.viewport.span == 12345
    switch_workspace(qtbot, window, "Modelování")
    paper_transform = window.paper.transform()
    window.viewport.setFocus()
    window.focus_selection()
    assert window.viewport.span != 12345
    assert window.paper.transform() == paper_transform
    window.actions["draw"].trigger()
    assert window.sketch.isVisible() and window.sketch.drawing
    window.actions["cancel"].trigger()


def test_inline_surface_name_uses_history_and_context_validation(window, qtbot, tmp_path):
    sid = arrange_rectangle(window)
    original = window.project.surfaces[sid].name
    pid = window.selected_part
    original_part = window.project.parts[pid].name
    original_frame = deepcopy(window.project.parts[pid].frame)
    original_placement = deepcopy(window.project.placements[pid])
    window.selection_name.setFocus()
    window.selection_name.selectAll()
    qtbot.keyClicks(window.selection_name, "Vlastni severni stena")
    switch_workspace(qtbot, window, "Spoje a rozvin")
    assert window.project.surfaces[sid].name == "Vlastni severni stena"
    assert window.project.parts[pid].name == "P1 · Vlastni severni stena"
    assert window.problems._part_names[pid] == "P1 · Vlastni severni stena"
    window.actions["undo"].trigger()
    assert window.project.surfaces[sid].name == original
    assert window.project.parts[pid].name == original_part
    window.actions["redo"].trigger()
    assert window.project.surfaces[sid].name == "Vlastni severni stena"
    assert window.project.parts[pid].name == "P1 · Vlastni severni stena"
    window.selection_name.setFocus()
    window.selection_name.selectAll()
    qtbot.keyClick(window.selection_name, Qt.Key.Key_Backspace)
    switch_workspace(qtbot, window, "Export")
    assert window.workspace_context == "Spoje a rozvin"
    assert window.selection_name.text() == ""
    assert window.project.surfaces[sid].name == "Vlastni severni stena"
    window.selection_name.setText("Vlastni severni stena")
    path = tmp_path / "named-wall.apcraft"
    window.controller.save(path)
    window.controller.new()
    window.controller.open(path)
    assert window.project.surfaces[sid].name == "Vlastni severni stena"
    assert window.project.parts[pid].name == "P1 · Vlastni severni stena"
    assert window.project.parts[pid].frame == original_frame
    assert window.project.placements[pid] == original_placement


@pytest.mark.parametrize("separate_name", [False, True])
def test_inline_name_keeps_mixed_component_and_explicit_paper_name(window, qtbot, separate_name):
    from test_editing import connected_component

    from archpapercraft.authoring.editing import rename_author_entities

    if separate_name:
        sid = arrange_rectangle(window)
        pid = window.selected_part
        window.controller.execute("Own paper name", lambda p: rename_author_entities(
            p, part_id=pid, part_name="My printed wall"))
    else:
        project, pid, surfaces, *_ = connected_component()
        window.controller.project = project
        window.refresh()
        sid = surfaces[0]
        window.select_surface(sid)
        assert len(window.project.parts[pid].surface_ids) == 2
    original_part = window.project.parts[pid].name
    window.selection_name.setFocus()
    window.selection_name.selectAll()
    qtbot.keyClicks(window.selection_name, "New wall name")
    qtbot.keyClick(window.selection_name, Qt.Key.Key_Return)
    assert window.project.surfaces[sid].name == "New wall name"
    assert window.project.parts[pid].name == original_part


def test_problem_navigation_validates_raw_then_focuses_actual_unplaced_part(window, qtbot):
    sid = arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    switch_workspace(qtbot, window, "Stránky")  # Consume the initial page Fit All.
    switch_workspace(qtbot, window, "Modelování")
    window.vertex_x.setFocus()
    window.vertex_x.lineEdit().setText("-")
    qtbot.mouseClick(window.problems.primary, Qt.MouseButton.LeftButton)
    assert window.workspace_context == "Modelování"
    assert window.vertex_x.lineEdit().text() == "-"
    assert window.project.to_dict() == before
    window.vertex_x.lineEdit().setText("0")
    qtbot.keyClick(window, Qt.Key.Key_F8)
    assert window.issues.isVisible() and window.issues.hasFocus()
    qtbot.keyClick(window.issues, Qt.Key.Key_Return)
    assert window.workspace_context == "Stránky"
    assert window.selected_surface == sid
    assert window.project.to_dict() == before  # Navigation never packs or changes layout.
    qtbot.wait(5)
    visible = window.paper.mapToScene(window.paper.viewport().rect()).boundingRect()
    page = window.project.pages[0]
    origin = window.paper.page_origins[page.id]
    assert visible.contains(origin)
    assert visible.contains(origin + QPointF(page.width_mm, page.height_mm))
    assert visible.contains(window.paper.part_items[window.selected_part].sceneBoundingRect())


def test_responsive_properties_keep_complete_labels_and_values(window, qtbot):
    from PySide6.QtWidgets import QFormLayout, QScrollArea

    arrange_rectangle(window)
    window.resize(1366, 768)
    switch_workspace(qtbot, window, "Spoje a rozvin")
    scroll = window.properties_dock.findChild(QScrollArea)
    window.resizeDocks([window.properties_dock], [300], Qt.Orientation.Horizontal)
    qtbot.wait(10)
    scroll.ensureWidgetVisible(window.edge_choice)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert window.edge_choice.isVisible()
    label = window.edge_form.labelForField(window.edge_choice)
    assert label.wordWrap() and label.isVisible()
    assert scroll.viewport().rect().contains(label.mapTo(scroll.viewport(), QPoint(0, 0)))
    assert window.edge_form.rowWrapPolicy() == QFormLayout.RowWrapPolicy.WrapLongRows
    assert not window.section_containers["Profil a křivky"].isVisible()
    assert not window.sections["Autorské spoje a záložky"][1].isVisible()
    qtbot.mouseClick(window.sections["Autorské spoje a záložky"][0], Qt.MouseButton.LeftButton)
    qtbot.wait(5)
    assert window.sections["Autorské spoje a záložky"][1].isVisible()
    assert scroll.horizontalScrollBar().maximum() == 0


def test_two_walls_activity_edit_joint_tab_two_pages_save_open_and_vectors(
    window, qtbot, tmp_path, monkeypatch
):
    """Real dialog/widget commands and IO; no native or novice-user claim."""
    import re
    import xml.etree.ElementTree as ET

    from pypdf import PdfReader
    from PySide6.QtWidgets import QDoubleSpinBox

    from archpapercraft.authoring import load_project

    window.units.setCurrentIndex(window.units.findData(1))
    window.plane.setCurrentIndex(window.plane.findData("XZ"))

    def rectangle(width):
        def accept():
            dialog = QApplication.activeModalWidget()
            fields = dialog.findChildren(QDoubleSpinBox)
            fields[0].setValue(width)
            fields[1].setValue(6000)
            dialog.accept()
        QTimer.singleShot(0, accept)
        window.actions["rectangle"].trigger()
        return window.selected_surface

    first, second = rectangle(10000), rectangle(8000)
    assert len(window.project.surfaces) == 2
    window.select_surface(first)
    window.vertex_choice.setCurrentIndex(1)
    set_number(qtbot, window.vertex_x, "11000")
    assert profile_of(window, first).vertices[1].point == [11000, 0]
    window.actions["undo"].trigger()
    window.actions["redo"].trigger()
    # Keep both connecting vertical edges exactly 6000 mm long.
    window.vertex_choice.setCurrentIndex(2)
    set_number(qtbot, window.vertex_x, "11000")
    switch_workspace(qtbot, window, "Spoje a rozvin")
    window.select_edge(first, profile_of(window, first).segments[1].id)
    qtbot.mouseClick(window.connect_button, Qt.MouseButton.LeftButton)
    QTimer.singleShot(0, lambda: QApplication.activeModalWidget().accept())
    window.select_edge(second, profile_of(window, second).segments[3].id)
    assert len(window.project.joints) == 1
    joint_id = next(iter(window.project.joints))
    window.tab_owner.setCurrentIndex(window.tab_owner.findData(first))
    set_number(qtbot, window.tab_width, "3")
    assert window.project.joints[joint_id].connector_id
    window.actions["recompute"].trigger()
    assert all(not part.stale for part in window.project.parts.values())
    switch_workspace(qtbot, window, "Stránky")
    window.add_page()
    for index, sid in enumerate((first, second)):
        window.select_surface(sid)
        window.page_choice.setCurrentIndex(window.page_choice.findData(window.project.pages[index].id))
        set_number(qtbot, window.paper_x, "30")
        set_number(qtbot, window.paper_y, "40")
    assert len(window.project.pages) == 2
    path = tmp_path / "two-walls.apcraft"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(path), ""))
    assert window.save_project()
    saved = deepcopy(window.project.to_dict())
    window.new_project()
    assert not window.project.surfaces
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))
    window.open_project()
    assert window.project.to_dict() == saved == load_project(path).to_dict()
    qtbot.wait(10)
    # A new project is framed after Open, even when paper was hidden at load time.
    switch_workspace(qtbot, window, "Export")
    window.show_problems()
    for row in range(window.issues.count()):
        window.issues.setCurrentRow(row)
        if window.ack_button.isEnabled():
            qtbot.mouseClick(window.ack_button, Qt.MouseButton.LeftButton)
    for page_id in window.paper.page_origins:
        assert page_id in {page.id for page in window.project.pages}
    output = tmp_path / "vectors"
    output.mkdir()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(output))
    window.actions["export"].trigger()
    assert len(list(output.glob("*.svg"))) == 2, window._test_warnings
    assert len(list(output.glob("*.pdf"))) == 1
    ns = {"s": "http://www.w3.org/2000/svg"}
    areas, folds = [], []
    for svg in output.glob("*.svg"):
        root = ET.parse(svg).getroot()
        assert root.attrib["viewBox"] == "0 0 210 297"
        for path in root.findall(".//s:g[@data-role='CUT']/s:path", ns):
            values = list(map(float, re.findall(r"[-+]?\d+(?:\.\d+)?", path.attrib["d"])))
            points = list(zip(values[::2], values[1::2]))
            areas.append(abs(sum(a[0]*b[1] - a[1]*b[0]
                                 for a, b in zip(points, points[1:] + points[:1]))) / 2)
        for path in root.findall(".//s:g[@data-role='FOLD_MOUNTAIN']/s:path", ns):
            x1, y1, x2, y2 = map(float, re.findall(r"[-+]?\d+(?:\.\d+)?", path.attrib["d"]))
            folds.append(((x2-x1)**2 + (y2-y1)**2)**0.5)
    # Two own walls 110×60 and 80×60; tapered 3 mm tab has bases 60 and 36.
    assert sorted(areas) == pytest.approx([4800, 6600 + 3*(60+36)/2])
    assert folds == pytest.approx([60])
    pdf = PdfReader(output / "model.pdf")
    assert len(pdf.pages) == 2
    assert all(float(page.mediabox.width) * 25.4 / 72 == pytest.approx(210)
               for page in pdf.pages)
    assert not window._test_warnings


def test_contextual_delete_preserves_sketch_and_is_one_reversible_command(window, qtbot):
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.author_editing import DeletePartDialog

    assert not window.actions["delete_part"].isEnabled()
    sid = arrange_rectangle(window)
    profile_id = window.project.surfaces[sid].profile_id
    before = deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)

    def confirm():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, DeletePartDialog)
        qtbot.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok),
                         Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, confirm)
    window.actions["delete_part"].trigger()
    assert sid not in window.project.surfaces
    assert profile_id in window.project.profiles
    assert window.selected_surface is None and window.selected_part is None
    assert not window.actions["delete_part"].isEnabled()
    assert not window.delete_part_button.isEnabled()
    assert len(window.controller._undo) == depth + 1
    window.actions["undo"].trigger()
    assert window.project.to_dict() == before
    window.actions["redo"].trigger()
    assert not window.project.surfaces and profile_id in window.project.profiles


def test_delete_cancel_preserves_everything_and_does_not_capture_text_delete(window, qtbot):
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.author_editing import DeletePartDialog

    arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)

    def cancel():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, DeletePartDialog)
        dialog.reject()

    QTimer.singleShot(0, cancel)
    qtbot.mouseClick(window.delete_part_button, Qt.MouseButton.LeftButton)
    assert window.project.to_dict() == before and len(window.controller._undo) == depth
    assert window.actions["delete_part"].shortcut().isEmpty()
    window.clear_selection()
    assert not window.delete_part_button.isEnabled()


@pytest.mark.parametrize("action", ["rename", "delete_part"])
def test_edit_dialog_preflight_commits_visible_number_before_open(window, qtbot, action):
    from PySide6.QtWidgets import QApplication

    sid = arrange_rectangle(window)
    profile = profile_of(window, sid)
    identity = profile.vertices[1].id
    window.select_vertex(profile.id, identity)
    window.vertex_x.setFocus()
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.vertex_x, "11")  # No Enter before the action.
    observed = []

    def inspect_and_cancel():
        dialog = QApplication.activeModalWidget()
        observed.append(profile_of(window, sid).vertex(identity).point[0])
        dialog.reject()

    QTimer.singleShot(0, inspect_and_cancel)
    window.actions[action].trigger()
    assert observed == [11000.0]


@pytest.mark.parametrize("action", ["rename", "delete_part"])
def test_edit_dialog_invalid_pending_number_stops_before_dialog(window, qtbot, action, monkeypatch):
    import archpapercraft.ui.author_window as module

    sid = arrange_rectangle(window)
    profile = profile_of(window, sid)
    window.select_vertex(profile.id, profile.vertices[1].id)
    before = deepcopy(window.project.to_dict())
    window.vertex_x.setFocus()
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.vertex_x, "0")  # No Enter: preflight owns validation.

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid geometry must stop before opening the edit dialog")

    monkeypatch.setattr(module, "RenameDialog", unexpected)
    monkeypatch.setattr(module, "DeletePartDialog", unexpected)
    window.actions[action].trigger()
    assert window._test_warnings and window.project.to_dict() == before


def test_rename_from_empty_and_selected_workspace_survives_save_open(window, qtbot, tmp_path):
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.author_editing import RenameDialog

    def rename():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, RenameDialog)
        dialog.project_name.setText("My authored model")
        if dialog.surface_name is not None:
            dialog.surface_name.setText("North wall")
            dialog.part_name.setText("Wall with return")
        dialog.accept()

    QTimer.singleShot(0, rename)
    window.actions["rename"].trigger()
    assert window.project.name == "My authored model"
    sid = arrange_rectangle(window)
    pid = window.selected_part
    QTimer.singleShot(0, rename)
    window.actions["rename"].trigger()
    assert window.project.surfaces[sid].name == "North wall"
    assert window.project.parts[pid].name == "Wall with return"
    target = tmp_path / "named.apcraft"
    window.controller.save(target)
    window.controller.new()
    window.controller.open(target)
    assert window.project.surfaces[sid].name == "North wall"
    assert window.project.parts[pid].name == "Wall with return"


def test_empty_paper_click_clears_linked_selection_and_contextual_actions(window, qtbot):
    arrange_rectangle(window)
    assert window.actions["hole"].isEnabled()
    # Empty physical page, away from the tray part and calibration footer.
    page_origin = window.paper.page_origins[window.project.pages[0].id]
    point = window.paper.mapFromScene(page_origin + QPointF(80, 80))
    qtbot.mouseClick(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert window.selected_surface is None and window.selected_part is None
    assert not window.viewport.selected_surfaces
    assert window.paper.selected_part is None
    assert not window.tree.selectedItems()
    assert not window.actions["hole"].isEnabled()
    assert not window.sections["Díl na papíře"][0].isVisible()


def test_repeat_draw_keeps_draft_and_export_cannot_silently_omit_it(window, qtbot, monkeypatch):
    arrange_rectangle(window)
    window.actions["draw"].trigger()
    for point in [(0, 0), (3000, 0)]:
        qtbot.mouseClick(
            window.sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(point[0], -point[1])),
        )
    before = deepcopy(window.sketch.points)
    state = deepcopy(window.project.to_dict())
    window.actions["draw"].trigger()
    assert window.sketch.points == before
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: messages.append(a[2]))
    window.actions["export"].trigger()
    assert messages and "Rozpracované body" in messages[0]
    assert window.sketch.points == before and window.project.to_dict() == state


def test_hole_draft_stays_attached_to_original_surface_after_selection_change(window, qtbot):
    first = arrange_rectangle(window, name="Otvor patří sem")
    second = arrange_rectangle(window, name="Jiná stěna")
    window.select_surface(first)
    window.actions["hole"].trigger()
    for x, y in [(2000, 2000), (4000, 2000), (4000, 4000), (2000, 4000)]:
        qtbot.mouseClick(
            window.sketch.viewport(), Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(x, -y)),
        )
    window.select_surface(second)
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return)
    assert len(window.project.surfaces[first].hole_profile_ids) == 1
    assert window.project.surfaces[second].hole_profile_ids == []
    assert window.selected_surface == first


def test_keyboard_issue_activation_focuses_actual_part(window, qtbot):
    sid = arrange_rectangle(window)
    pid = window.selected_part
    window.clear_selection()
    window.issues.setCurrentRow(0)
    window.issues.setFocus()
    qtbot.keyClick(window.issues, Qt.Key.Key_Return)
    assert window.selected_part == pid and window.selected_surface == sid
    assert window.paper.selected_part == pid


@pytest.mark.parametrize("action", ["save", "export", "new"])
def test_pending_numeric_edit_is_committed_before_shortcuts(window, qtbot, tmp_path, action):
    from archpapercraft.authoring import load_project

    sid = arrange_rectangle(window)
    window.select_vertex(profile_of(window, sid).id, profile_of(window, sid).vertices[1].id)
    target = tmp_path / "pending-input.apcraft"
    window.controller.save(target)
    identity = profile_of(window, sid).vertices[1].id
    window.vertex_x.setFocus()
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.vertex_x, "11")
    assert profile_of(window, sid).vertex(identity).point[0] == 10000.0
    project_id = window.project.project_id
    key = {"save": Qt.Key.Key_S, "export": Qt.Key.Key_E, "new": Qt.Key.Key_N}[action]
    qtbot.keyClick(window, key, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)
    assert profile_of(window, sid).vertex(identity).point[0] == 11000.0
    if action == "save":
        loaded = load_project(target)
        assert loaded.profiles[profile_of(window, sid).id].vertex(identity).point[0] == 11000.0
        assert not window.controller.dirty
    elif action == "export":
        assert window.project.parts[window.selected_part].stale
        assert window._test_warnings  # Stale geometry must stop snapshot/export.
        assert window.controller.dirty
    else:
        assert window.project.project_id == project_id  # Dirty prompt answered Cancel.
        assert window.controller.dirty


def test_failed_pending_numeric_commit_cannot_save_or_replace(window, qtbot, tmp_path):
    sid = arrange_rectangle(window)
    profile = profile_of(window, sid)
    window.select_vertex(profile.id, profile.vertices[1].id)
    path = tmp_path / "unchanged.apcraft"
    window.controller.save(path)
    original = path.read_bytes()
    before = deepcopy(window.project.to_dict())
    window.vertex_x.setFocus()
    qtbot.keyClick(window.vertex_x, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.vertex_x, "0")  # Coincides with the first vertex: invalid.
    qtbot.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    assert window._test_warnings
    assert window.project.to_dict() == before and path.read_bytes() == original
    assert not window.controller.dirty


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "authoring-settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("tips_enabled", True)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args[2]))
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Cancel
    )
    item = AuthorMainWindow(settings=settings)
    item._test_warnings = warnings

    def safe_close(widget):
        widget.sketch.cancel_outline()
        widget.connect_source = None
        widget.controller._saved_digest = widget.controller.digest(widget.project.to_dict())

    qtbot.addWidget(item, before_close_func=safe_close)
    item.show()
    item.activateWindow()
    item.raise_()
    qtbot.waitExposed(item)
    qtbot.wait(35)
    return item


def sketch_points(qtbot, window, points, *, hole=False):
    window.actions["hole" if hole else "draw"].trigger()
    assert window.sketch.drawing
    for x, y in points:
        qtbot.mouseClick(
            window.sketch.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(x, -y)),
        )
    qtbot.keyClick(window.sketch, Qt.Key.Key_Return)
    qtbot.wait(20)


def arrange_rectangle(window, *, points=None, name="Vlastní stěna"):
    if points is None:
        points = [[0.0, 0.0], [10000.0, 0.0], [10000.0, 6000.0], [0.0, 6000.0]]

    def operation(project):
        pid = project.add_profile(points)
        return project.add_surface(pid, name=name)

    sid = window.controller.execute("Příprava kontrolního dílu", operation)
    window.select_surface(sid)
    window.focus_selection()
    return sid


def profile_of(window, sid):
    return window.project.profiles[window.project.surfaces[sid].profile_id]


def cached_geometry(payload):
    return {key: payload[key] for key in ("polygons", "paths", "labels", "edges")}


def set_number(qtbot, field, text):
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(field, str(text))
    qtbot.keyClick(field, Qt.Key.Key_Return)


def test_empty_workspace_creates_own_concave_polygon_by_actual_clicks_and_enter(window, qtbot):
    assert not window.project.surfaces and not window.project.parts
    assert not window.actions["hole"].isEnabled()
    assert "Začněte" in window.hint.text()
    points = [
        [0.0, 0.0],
        [10000.0, 0.0],
        [10000.0, 4000.0],
        [7000.0, 4000.0],
        [7000.0, 6000.0],
        [0.0, 6000.0],
    ]
    sketch_points(qtbot, window, points)
    assert len(window.project.surfaces) == len(window.project.parts) == 1
    sid = window.selected_surface
    assert profile_of(window, sid).points == points
    part = window.project.parts[window.selected_part]
    assert not part.stale and window.actions["hole"].isEnabled()
    polygon = np.array(window.project.part_geometry(part.id)["polygons"][sid][0])
    actual = (
        abs(
            np.sum(
                polygon[:, 0] * np.roll(polygon[:, 1], -1)
                - polygon[:, 1] * np.roll(polygon[:, 0], -1)
            )
        )
        / 2
    )
    assert actual == pytest.approx(5400.0)
    assert len(window.viewport.meshes) == 1 and part.id in window.paper.part_items
    assert window.controller.dirty
    assert window._test_warnings == []


def test_hole_draw_is_real_trim_and_old_paper_is_stale_until_explicit_recompute(window, qtbot):
    sid = arrange_rectangle(window)
    pid = window.selected_part
    cached = cached_geometry(window.project.part_geometry(pid))
    sketch_points(
        qtbot,
        window,
        [[2000.0, 2000.0], [4000.0, 2000.0], [4000.0, 4000.0], [2000.0, 4000.0]],
        hole=True,
    )
    assert len(window.project.surfaces[sid].hole_profile_ids) == 1
    assert window.project.parts[pid].stale
    assert cached_geometry(window.project.part_geometry(pid)) == cached
    qtbot.keyClick(window, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    qtbot.waitUntil(lambda: not window.project.parts[pid].stale)
    assert len(window.project.part_geometry(pid)["polygons"][sid]) == 2
    assert window._test_warnings == []


def test_invalid_hole_retains_editable_draft_and_escape_preserves_prior_project(window, qtbot):
    arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    sketch_points(
        qtbot, window, [[12000.0, 1000.0], [14000.0, 1000.0], [14000.0, 3000.0]], hole=True
    )
    assert window._test_warnings
    assert window.sketch.drawing and len(window.sketch.points) == 3
    assert window.project.to_dict() == before
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.sketch.drawing and window.project.to_dict() == before


def test_stable_vertex_drag_is_undoable_and_does_not_implicitly_recompute(window, qtbot):
    sid = arrange_rectangle(window)
    qtbot.mouseClick(window.workspace_bar.sketch_button, Qt.MouseButton.LeftButton)
    qtbot.wait(10)
    profile = profile_of(window, sid)
    vertex = profile.vertices[2]
    identity, pid = vertex.id, window.selected_part
    before = deepcopy(cached_geometry(window.project.part_geometry(pid)))
    handle = next(
        item
        for item in window.sketch.scene().items()
        if isinstance(item, VertexHandle) and item.vertex_id == identity
    )
    start = window.sketch.mapFromScene(handle.scenePos())
    end = start + QPoint(25, 0)
    qtbot.mousePress(window.sketch.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(window.sketch.viewport(), end, delay=20)
    qtbot.mouseRelease(window.sketch.viewport(), Qt.MouseButton.LeftButton, pos=end)
    qtbot.wait(20)
    assert profile_of(window, sid).vertex(identity).point != [10000.0, 6000.0]
    assert window.project.parts[pid].stale
    assert cached_geometry(window.project.part_geometry(pid)) == before
    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert profile_of(window, sid).vertex(identity).point == [10000.0, 6000.0]
    assert not window.project.parts[pid].stale
    assert cached_geometry(window.project.part_geometry(pid)) == before


def test_main_escape_and_ctrl_z_cancel_active_paper_drag_without_undoing_prior_command(
    window, qtbot
):
    arrange_rectangle(window)
    pid = window.selected_part
    page = window.project.pages[0].id
    window.controller.execute(
        "Umístit kontrolní díl",
        lambda p: p.set_placement(pid, page_id=page, x_mm=40.0, y_mm=50.0, rotation_deg=0.0),
    )
    window.paper.focus_part(pid)
    before = deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)
    for key, modifier in [
        (Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier),
    ]:
        item = window.paper.part_items[pid]
        origin = QPointF(item.pos())
        start = window.paper.mapFromScene(item.mapToScene(QPointF(10.0, 10.0)))
        end = start + QPoint(30, 15)
        qtbot.mousePress(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=start)
        qtbot.mouseMove(window.paper.viewport(), end, delay=20)
        assert item.pos() != origin
        qtbot.keyClick(window, key, modifier)
        qtbot.mouseRelease(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=end)
        qtbot.wait(20)
        assert window.project.to_dict() == before and len(window.controller._undo) == depth
        assert window.paper.part_items[pid].pos() == origin


def test_ctrl_z_reverts_uncommitted_sketch_point_even_with_no_command_history(window, qtbot):
    window.actions["draw"].trigger()
    for point in [(0.0, 0.0), (4000.0, 0.0)]:
        qtbot.mouseClick(
            window.sketch.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.sketch.mapFromScene(QPointF(point[0], -point[1])),
        )
    assert len(window.sketch.points) == 2
    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert len(window.sketch.points) == 1
    assert not window.project.surfaces and not window.controller.dirty


def test_actual_3d_click_through_hole_and_2d_selection_link_same_source(window, qtbot):
    below = arrange_rectangle(window, name="Spodní plocha")
    top = arrange_rectangle(window, name="Plocha s otvorem")

    def operation(project):
        hole = project.add_profile(
            [[2500.0, 1500.0], [7500.0, 1500.0], [7500.0, 4500.0], [2500.0, 4500.0]]
        )
        project.add_hole(top, hole)
        project.set_transform(top, [0.0, 0.0, 500.0], [0.0, 0.0, 0.0])
        project.recompute()

    window.controller.execute("Připravit prostorový kontrolní otvor", operation)
    window.viewport.yaw = window.viewport.pitch = 0.0
    window.viewport.focus_selection(all_surfaces=True)
    point = window.viewport.project_points([[5000.0, 3000.0, 500.0]])[0]
    qtbot.mouseClick(
        window.viewport, Qt.MouseButton.LeftButton, pos=QPoint(round(point[0]), round(point[1]))
    )
    assert window.selected_surface == below
    assert window.viewport.selected_surfaces == {below}
    assert window.paper.selected_part == window.project.surfaces[below].part_id
    point = window.viewport.project_points([[1000.0, 3000.0, 500.0]])[0]
    qtbot.mouseClick(
        window.viewport, Qt.MouseButton.LeftButton, pos=QPoint(round(point[0]), round(point[1]))
    )
    assert window.selected_surface == top
    pid = window.selected_part
    window.paper.focus_part(pid)
    paper_point = window.paper.mapFromScene(
        window.paper.part_items[pid].mapToScene(QPointF(10.0, 10.0))
    )
    window.select_surface(below)
    qtbot.mouseClick(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=paper_point)
    assert window.selected_surface == top and window.viewport.selected_surfaces == {top}
    assert window.tree.currentItem().data(0, Qt.ItemDataRole.UserRole) == top


@pytest.mark.parametrize(
    "unit,width,height", [(0, 10.0, 4.0), (1, 1000.0, 400.0), (2, 10000.0, 4000.0)]
)
def test_numeric_rectangle_unit_input_is_converted_once_to_100mm_paper_width(
    window, qtbot, unit, width, height
):
    window.units.setCurrentIndex(unit)

    def complete_dialog():
        dialog = QApplication.activeModalWidget()
        fields = dialog.findChildren(QDoubleSpinBox)
        fields[0].setValue(width)
        fields[1].setValue(height)
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()

    QTimer.singleShot(0, complete_dialog)
    window.actions["rectangle"].trigger()
    sid = window.selected_surface
    assert max(p[0] for p in profile_of(window, sid).points) == 10000.0
    polygon = np.array(window.project.part_geometry(window.selected_part)["polygons"][sid][0])
    assert np.ptp(polygon[:, 0]) == pytest.approx(100.0)
    assert np.ptp(polygon[:, 1]) == pytest.approx(40.0)


def test_focus_and_angle_only_edit_preserve_raw_decimal_source_and_placement(
    window, qtbot, tmp_path
):
    sid = arrange_rectangle(
        window,
        points=[
            [0.123456789, 0.987654321],
            [10000.123456789, 0.987654321],
            [10000.123456789, 4000.987654321],
            [0.123456789, 4000.987654321],
        ],
    )
    pid = window.selected_part
    window.controller.execute(
        "Umístit přesně",
        lambda p: p.set_placement(
            pid,
            page_id=p.pages[0].id,
            x_mm=40.123456789,
            y_mm=55.987654321,
            rotation_deg=13.333333333,
        ),
    )
    window.select_surface(sid)
    vertex = profile_of(window, sid).vertices[1]
    window.select_vertex(profile_of(window, sid).id, vertex.id)
    window.controller.save(tmp_path / "precision.apcraft")
    before = deepcopy(window.project.to_dict())
    for field in [
        window.vertex_x,
        window.vertex_y,
        window.paper_x,
        window.paper_y,
        window.paper_angle,
        window.scale_field,
        *window.transform_fields,
    ]:
        field.setFocus()
        qtbot.keyClick(field, Qt.Key.Key_Tab)
    assert window.project.to_dict() == before and not window.controller.dirty
    set_number(qtbot, window.paper_angle, "20")
    placement = window.project.placements[pid]
    assert (
        placement.x_mm == 40.123456789
        and placement.y_mm == 55.987654321
        and placement.rotation_deg == 20.0
    )
    assert profile_of(window, sid).vertex(vertex.id).point == [10000.123456789, 0.987654321]


def test_tips_repeat_off_and_direct_keyboard_route_do_not_change_project(window, qtbot):
    before = deepcopy(window.project.to_dict())
    window.tips_action.setChecked(False)
    assert not window.hint.isVisible()
    window.settings.sync()
    assert window.settings.value("tips_enabled", True, type=bool) is False
    qtbot.keyClick(window, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier)
    assert window.sketch.drawing and not window.hint.isVisible()
    qtbot.keyClick(window, Qt.Key.Key_F1)
    assert window.hint.isVisible() and window.tips_action.isChecked()
    window.tips_action.setChecked(False)
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.sketch.drawing and not window.hint.isVisible()
    assert window.project.to_dict() == before and not window.controller.dirty


def test_save_undo_branch_dirty_and_failed_save_preserve_original(
    window, qtbot, tmp_path, monkeypatch
):
    sid = arrange_rectangle(window)
    path = tmp_path / "Vlastní model.apcraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), "Papercraft")
    )
    qtbot.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    assert path.is_file() and not window.controller.dirty
    original = path.read_bytes()
    window.controller.undo()
    assert window.controller.dirty and not window.project.surfaces
    replacement = arrange_rectangle(window, name="Jiný díl při stejné hloubce historie")
    assert replacement != sid and window.controller.dirty

    def fail(path):
        raise OSError("Injected save failure")

    monkeypatch.setattr(window.project, "save", fail)
    assert window.save_project() is False
    assert window.controller.dirty and path.read_bytes() == original
    assert "Injected save failure" in window._test_warnings[-1]


def test_close_cancel_keeps_dirty_project_and_draft_cancel_is_explicit(window, qtbot):
    arrange_rectangle(window)
    before = deepcopy(window.project.to_dict())
    assert window.close() is False
    assert window.isVisible() and window.project.to_dict() == before and window.controller.dirty
    window.actions["draw"].trigger()
    qtbot.mouseClick(
        window.sketch.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.sketch.mapFromScene(QPointF(0.0, 0.0)),
    )
    assert window.close() is False and window.sketch.drawing and window.sketch.points
    assert window.project.to_dict() == before
