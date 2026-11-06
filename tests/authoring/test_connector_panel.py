"""Actual offscreen widgets and commands; not a novice or native desktop study."""

from __future__ import annotations

import copy

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)
from test_folded_registry import mixed_connectors
from test_interior import wall_roof
from test_paper import two_panels

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.ui.author_connectors import ConnectorPanel, choose


class Host(QWidget):
    def __init__(self, project, selected):
        super().__init__()
        self.selected_surface, self.selected_edge = selected, None
        self.errors, self.preflights = [], 0
        self.pending_operation, self.last_pending_value = None, None
        self.controller = AuthorController(self.changed)
        self.controller.project = project
        self.controller._saved_digest = self.controller.digest(project.to_dict())
        self.units = QComboBox()
        self.units.addItem("m", 1000)
        self.pending_field = QDoubleSpinBox()
        self.pending_field.setRange(0, 100)
        self.pending_field.setKeyboardTracking(False)
        self.pending_field.editingFinished.connect(self.commit_number)
        self.panel = ConnectorPanel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.pending_field)
        layout.addWidget(self.panel)

    @property
    def project(self):
        return self.controller.project

    @property
    def unit_factor(self):
        return self.units.currentData()

    def changed(self):
        if hasattr(self, "panel"):
            self.panel.refresh()

    def run(self, operation):
        try:
            return operation()
        except Exception as exc:
            self.errors.append(str(exc))
            return None

    def select_surface(self, sid):
        self.selected_surface = sid
        self.panel.refresh()

    def commit_number(self):
        if (
            self.pending_operation is not None
            and self.pending_field.value() != self.last_pending_value
        ):
            value = self.pending_field.value()
            before = len(self.errors)
            self.run(
                lambda: self.controller.execute(
                    "Upravit rozměr", lambda p: self.pending_operation(p, value)
                )
            )
            if len(self.errors) == before:
                self.last_pending_value = value

    def _commit_pending_input(self):
        self.preflights += 1
        field = QApplication.focusWidget()
        while field is not None and not isinstance(field, QAbstractSpinBox):
            field = field.parentWidget()
        if field is not self.pending_field:
            return True
        if not field.hasAcceptableInput():
            return False
        before = len(self.errors)
        field.interpretText()
        field.editingFinished.emit()
        field.clearFocus()
        return len(self.errors) == before


def host_fixture(qtbot, *, tab=True):
    project, wall, roof, edge = wall_roof()
    aid = project.attach_edge_to_surface(wall, edge, roof)
    cid = project.set_attachment_tab(aid) if tab else None
    host = Host(project, wall)
    qtbot.addWidget(host)
    host.resize(440, 640)
    host.show()
    qtbot.wait(5)
    return host, aid, cid, wall, roof


def modal(qtbot, launch, action):
    errors, dialogs = [], []

    def operate():
        dialog = QApplication.activeModalWidget()
        dialogs.append(dialog)
        try:
            assert isinstance(dialog, QDialog)
            action(dialog)
            assert not dialog.isVisible(), "Dialog must accept or cancel in this test."
        except BaseException as exc:
            errors.append(exc)
            if dialog:
                dialog.reject()

    QTimer.singleShot(20, operate)
    launch()
    qtbot.wait(5)
    if errors:
        raise errors[0]
    assert dialogs
    return dialogs[0]


def test_context_receiver_and_invalid_attachment_removal_are_real_undo_commands(qtbot):
    host, aid, cid, wall, roof = host_fixture(qtbot)
    assert host.panel.current_relation == ("attachment", aid)
    assert "Střecha" in host.panel.receiver.text()
    host.panel.show_receiver.click()
    assert host.selected_surface == roof
    assert "stěna" in host.panel.receiver.text().lower()
    host.select_surface(wall)
    host.project.set_transform(wall, [0, 0, 1])
    host.panel.refresh()
    assert "GAP" in host.panel.status.text()
    assert host.panel.remove_relation.isEnabled()
    host.panel.remove_relation.click()
    assert aid not in host.project.attachments and cid not in host.project.connectors
    host.controller.undo()
    assert aid in host.project.attachments and cid in host.project.connectors
    assert not host.errors


def test_global_clone_preview_cancel_changes_neither_document_nor_history(qtbot):
    host, *_ = host_fixture(qtbot)
    before = copy.deepcopy(host.project.to_dict())

    def action(dialog):
        dialog.count.setValue(4)
        dialog.gap.setValue(1)
        choose(dialog.shape, "triangle")
        assert dialog.preview_state is not None
        assert host.project.to_dict() == before
        dialog.reject()

    modal(qtbot, host.panel.edit_connector, action)
    assert host.project.to_dict() == before and not host.controller.can_undo


def test_pending_dialog_width_without_enter_and_global_count_apply_once_with_undo(qtbot):
    host, aid, cid, *_ = host_fixture(qtbot)

    def action(dialog):
        dialog.count.setValue(4)
        dialog.gap.setValue(1)
        choose(dialog.shape, "triangle")
        dialog.width.setFocus()
        dialog.width.lineEdit().selectAll()
        dialog.width.lineEdit().setText("4")
        dialog.accept()  # Text is pending; no Enter/focusOut occurred first.

    modal(qtbot, host.panel.edit_connector, action)
    connector = host.project.connectors[cid]
    assert connector.width_mm == 4 and connector.count == 4
    assert connector.shape == "triangle" and connector.gap_mm == 1
    assert host.project.attachments[aid].connector_id == cid
    assert len(host.panel.tabs.currentData()) > 10  # Semantic UUID, not combo index.
    assert len(host.controller._undo) == 1
    host.controller.undo()
    assert host.project.connectors[cid].width_mm == 5 and host.project.connectors[cid].count == 1


def test_individual_uuid_off_keeps_other_tabs_and_reopens_after_undo(qtbot):
    host, _, cid, *_ = host_fixture(qtbot)
    host.project.set_connector(cid, count=3)
    host.panel.refresh()
    ids = list(host.project.connectors[cid].tab_ids)
    choose(host.panel.tabs, ids[1])

    def action(dialog):
        assert dialog.tab_id == ids[1]
        dialog.enabled.setChecked(False)
        dialog.accept()

    modal(qtbot, host.panel.edit_individual, action)
    assert host.project.connectors[cid].tab_ids == ids
    assert [t["tab_id"] for t in host.project.connector_geometry(cid)["tabs"]] == [ids[0], ids[2]]
    host.controller.undo()
    assert len(host.project.connector_geometry(cid)["tabs"]) == 3


def test_custom_outline_is_drawn_in_paper_mm_with_immutable_base(qtbot):
    host, _, cid, *_ = host_fixture(qtbot)
    host.project.set_connector(cid, count=2, gap_mm=2)
    host.panel.refresh()
    tid = host.project.connectors[cid].tab_ids[0]
    choose(host.panel.tabs, tid)

    def action(dialog):
        choose(dialog.shape, "custom")
        dialog.draw.click()
        assert dialog.canvas.points == [[0, 0], [48, 0]]
        for x, y in [(48, 3), (29, 3), (29, 5), (19, 5), (19, 3), (0, 3)]:
            qtbot.mouseClick(
                dialog.canvas.viewport(),
                Qt.MouseButton.LeftButton,
                pos=dialog.canvas.mapFromScene(QPointF(x, -y)),
            )
        qtbot.keyClick(dialog.canvas, Qt.Key.Key_Return)
        assert dialog.preview_state is not None, dialog.status.text()
        assert dialog.canvas.points[:2] == [[0, 0], [48, 0]]
        dialog.accept()

    modal(qtbot, host.panel.edit_individual, action)
    connector = host.project.connectors[cid]
    assert connector.tab_overrides[tid]["shape"] == "custom"
    assert len(connector.tab_overrides[tid]["outline_mm"]) == 8
    assert connector.tab_overrides[tid]["outline_mm"][:2] == [[0, 0], [48, 0]]
    assert not host.errors


def test_bad_geometry_has_error_and_cancel_preserves_document(qtbot):
    host, *_ = host_fixture(qtbot)
    before = host.project.to_dict()

    def action(dialog):
        dialog.width.setValue(20)
        assert dialog.preview_state is None
        assert "PARTIAL" in dialog.status.text()
        assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
        dialog.reject()

    modal(qtbot, host.panel.edit_connector, action)
    assert host.project.to_dict() == before


def test_band_is_independent_material_selected_from_real_command_and_undo(qtbot):
    host, _, _, *_ = host_fixture(qtbot, tab=False)
    parts = set(host.project.parts)
    assert host.panel.band.isEnabled()

    def action(dialog):
        dialog.width.setValue(4)
        assert dialog.preview_state is not None, dialog.status.text()
        dialog.accept()

    modal(qtbot, host.panel.add_band, action)
    new_part = next(iter(set(host.project.parts) - parts))
    assert len(host.project.parts[new_part].surface_ids) == 2
    assert host.selected_surface in host.project.parts[new_part].surface_ids
    host.controller.undo()
    assert set(host.project.parts) == parts


def test_c05_host_pending_dimension_commits_before_dialog_clone_and_cancel(qtbot):
    host, _, _, wall, *_ = host_fixture(qtbot)
    profile = host.project.profiles[host.project.surfaces[wall].profile_id]
    vertex = profile.vertices[2].id
    host.last_pending_value = 10
    host.pending_field.setValue(10)
    host.pending_operation = lambda p, value: p.move_vertex(
        profile.id, vertex, [value * 1000, 4000]
    )
    host.pending_field.setFocus()
    host.pending_field.lineEdit().setText("11")

    def action(dialog):
        point = next(
            v for v in dialog.state["profiles"][profile.id]["vertices"] if v["id"] == vertex
        )
        assert point["point"] == [11000, 4000]
        dialog.reject()

    modal(qtbot, host.panel.edit_connector, action)
    assert host.project.profiles[profile.id].vertex(vertex).point == [11000, 4000]
    assert len(host.controller._undo) == 1


def test_c05_failed_host_numeric_commit_prevents_opening_dialog(qtbot, monkeypatch):
    host, _, _, wall, *_ = host_fixture(qtbot)
    profile = host.project.profiles[host.project.surfaces[wall].profile_id]
    vertex = profile.vertices[2].id
    host.last_pending_value = 10
    host.pending_field.setValue(10)
    host.pending_operation = lambda p, value: p.move_vertex(
        profile.id, vertex, [value * 1000, 4000]
    )
    host.pending_field.setFocus()
    host.pending_field.lineEdit().setText("0")  # Coincides with upper-left corner: invalid.
    before = host.project.to_dict()
    opened = []
    monkeypatch.setattr(
        "archpapercraft.ui.author_connectors.ConnectorEditDialog.exec",
        lambda _self: opened.append(True),
    )
    host.panel.edit_connector()
    assert not opened and host.errors
    assert host.project.to_dict() == before


def test_empty_selection_has_no_actions_and_clears_relation_highlight(qtbot):
    host, *_ = host_fixture(qtbot)
    emitted = []
    host.panel.relation_changed.connect(emitted.append)
    host.panel.refresh()
    assert emitted[-1] == host.panel.current_relation
    host.select_surface(None)
    assert not host.panel.edit.isEnabled() and not host.panel.show_receiver.isEnabled()
    assert "Vyberte" in host.panel.receiver.text()
    assert emitted[-1] is None


def test_unchanged_dialog_does_not_round_dimensions_dirty_document_or_add_undo(qtbot):
    host, _, cid, *_ = host_fixture(qtbot)
    host.project.set_connector(cid, width_mm=4.123456789, taper=0.6123456789, gap_mm=0.123456789)
    before = host.project.to_dict()
    modal(qtbot, host.panel.edit_connector, lambda dialog: dialog.accept())
    assert host.project.to_dict() == before
    assert not host.controller.can_undo and not host.errors


def test_count_edit_keeps_unedited_dimensions_at_full_source_precision(qtbot):
    host, _, cid, *_ = host_fixture(qtbot)
    host.project.set_connector(cid, width_mm=4.123456789, taper=0.6123456789, gap_mm=0.123456789)

    def action(dialog):
        dialog.count.setValue(3)
        dialog.accept()

    modal(qtbot, host.panel.edit_connector, action)
    connector = host.project.connectors[cid]
    assert connector.count == 3
    assert connector.width_mm == 4.123456789
    assert connector.taper == 0.6123456789 and connector.gap_mm == 0.123456789
    assert len(host.controller._undo) == 1


def test_precise_custom_vertex_pending_input_preserves_other_coordinate_and_fixed_base(qtbot):
    host, _, cid, *_ = host_fixture(qtbot)
    host.project.set_connector(cid, count=2, gap_mm=2)
    tid = host.project.connectors[cid].tab_ids[0]
    outline = [[0, 0], [48, 0], [47.123456789, 3.123456789], [1, 3]]
    host.project.set_connector_tab(cid, tid, shape="custom", outline_mm=outline)
    host.panel.refresh()
    choose(host.panel.tabs, tid)

    def action(dialog):
        choose(dialog.vertex, 2)
        dialog.vertex_y.setFocus()
        dialog.vertex_y.lineEdit().setText("4")
        dialog.accept()

    modal(qtbot, host.panel.edit_individual, action)
    actual = host.project.connectors[cid].tab_overrides[tid]["outline_mm"]
    assert actual[:2] == outline[:2]
    assert actual[2] == [47.123456789, 4]
    assert actual[3] == outline[3] and not host.errors


def test_edgepair_receiver_side_owner_and_fold_context_use_same_core_authority(qtbot):
    project, cid, _, jid, receiver = mixed_connectors()
    host = Host(project, receiver)
    qtbot.addWidget(host)
    host.show()
    choose(host.panel.relationship, ("joint", jid))
    assert "stran" in host.panel.status.text().lower()
    assert not host.panel.remove_relation.isEnabled()

    def side(dialog):
        choose(dialog.receiver_side, "outside")
        dialog.accept()

    modal(qtbot, host.panel.edit_connector, side)
    assert host.project.connectors[cid].receiver_side == "outside"
    assert not any(i.code.startswith("FOLDED_") for i in host.project.validate_layout())

    def owner(dialog):
        choose(dialog.owner, receiver)
        assert dialog.receiver_side.currentData() == "unknown"
        choose(dialog.receiver_side, "inside")
        assert "Protikus" in dialog.receiver_label.text()
        dialog.accept()

    modal(qtbot, host.panel.edit_connector, owner)
    assert host.project.connectors[cid].owner_surface_id == receiver
    assert host.project.connectors[cid].receiver_side == "inside"
    host.controller.undo()
    assert host.project.connectors[cid].receiver_side == "outside"
    folded, a, b, ea, eb = two_panels()
    fold = folded.connect_edges(a, ea, b, eb, mode="fold")
    host.controller.project = folded
    host.selected_surface = a
    host.panel.refresh()
    assert host.panel.current_relation == ("joint", fold)
    assert not host.panel.edit.isEnabled() and not host.panel.edit_tab.isEnabled()
    assert not host.errors
