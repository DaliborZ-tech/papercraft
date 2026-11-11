"""Actual host/grid widgets and real domain commands; no desktop/human claim."""

import copy

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItemIterator

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_manual_layout import ManualGridDialog
from archpapercraft.ui.author_window import AuthorMainWindow

pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def generation():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [40, 0]], closed=False)
    b = p.add_profile(
        [[0, 0], [40, 20]], closed=False, plane=dict(origin=[0, 0, 30], u=[1, 0, 0], v=[0, 1, 0])
    )
    target = p.add_loft(
        a,
        b,
        correspondences=[
            dict(
                first_segment_id=p.profiles[a].segments[0].id,
                second_segment_id=p.profiles[b].segments[0].id,
                first_interval=[0, 1],
                second_interval=[0, 1],
            )
        ],
    )
    preview = p.preview_segmented_variant(target)
    vid = p.add_segmented_variant(target, preview_digest=preview["preview_digest"])
    p.add_page()
    return p.to_dict(), target, vid


def restore(generation):
    state, target, vid = generation
    return AuthorProject.from_dict(copy.deepcopy(state)), target, vid


def grid(qtbot, p, ids):
    w = ManualGridDialog(p, ids)
    qtbot.addWidget(w)
    w.show()
    return w


def test_manual_grid_explicit_subset_page_pitch_keeps_other_layout_and_one_undo(qtbot, generation):
    p, _, vid = restore(generation)
    ids = [r["part_id"] for r in p.segmented_variants[vid].triangle_bindings]
    p.set_placement(ids[0], p.pages[0].id, 70, 80, 30, rotation_locked=True)
    before = p.to_dict()
    w = grid(qtbot, p, ids)
    assert w.page.currentData() is None and not w.parts.selectedItems()
    assert not w.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    # Pick in reverse click order; grid order remains the displayed list order.
    for i in (2, 1, 0):
        w.parts.item(i).setSelected(True)
    w.page.setCurrentIndex(1)
    w.columns.setValue(2)
    w.x.setValue(25)
    w.y.setValue(35)
    w.pitch_x.setValue(17)
    w.pitch_y.setValue(22)
    qtbot.mouseClick(w.preview_button, Qt.MouseButton.LeftButton)
    assert w._preview_updates == {
        ids[0]: dict(page_id=p.pages[1].id, x_mm=25.0, y_mm=35.0),
        ids[1]: dict(page_id=p.pages[1].id, x_mm=42.0, y_mm=35.0),
        ids[2]: dict(page_id=p.pages[1].id, x_mm=25.0, y_mm=57.0),
    }
    assert w.view.scene().items() and p.to_dict() == before
    qtbot.mouseClick(
        w.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    assert w.result() == QDialog.DialogCode.Accepted
    c = AuthorController()
    c.project = p
    c.execute("Ruční rozmístění", w.apply)
    assert p.placements[ids[0]].rotation_deg == 30 and p.placements[ids[0]].rotation_locked
    assert all(p.to_dict()["placements"][pid] == before["placements"][pid] for pid in ids[3:])
    c.undo()
    assert c.project.to_dict() == before
    c.redo()
    assert c.project.placements[ids[2]].x_mm == 25


def test_grid_locked_piece_invalid_number_and_changed_source_block_without_mutation(
    qtbot, generation
):
    p, _, vid = restore(generation)
    ids = [r["part_id"] for r in p.segmented_variants[vid].triangle_bindings]
    p.set_placement(ids[0], position_locked=True)
    w = grid(qtbot, p, ids)
    before = p.to_dict()
    w.parts.item(0).setSelected(True)
    w.page.setCurrentIndex(0)
    w.preview()
    assert w._preview_updates is None and "zamčená" in w.feedback.text()
    assert p.to_dict() == before
    w.parts.item(0).setSelected(False)
    w.parts.item(1).setSelected(True)
    w.preview()
    assert w._preview_updates is not None
    w.x.lineEdit().setText("-")
    w.accept()
    assert w.result() != QDialog.DialogCode.Accepted and "neplatnou" in w.feedback.text()
    w.x.setValue(30)
    w.preview()
    p.add_page()
    changed = p.to_dict()
    w.accept()
    assert w.result() != QDialog.DialogCode.Accepted and "změnil" in w.feedback.text()
    assert p.to_dict() == changed


def test_grid_typed_without_enter_cannot_apply_old_preview_and_cancel_is_safe(qtbot, generation):
    p, _, vid = restore(generation)
    ids = [r["part_id"] for r in p.segmented_variants[vid].triangle_bindings]
    w = grid(qtbot, p, ids)
    w.parts.item(0).setSelected(True)
    w.page.setCurrentIndex(0)
    w.preview()
    before = p.to_dict()
    w.x.lineEdit().setFocus()
    w.x.lineEdit().selectAll()
    qtbot.keyClicks(w.x.lineEdit(), "37")
    w.accept()
    assert w.result() != QDialog.DialogCode.Accepted and w.x.value() == 37
    assert w._preview_updates is None and p.to_dict() == before
    w.reject()
    with pytest.raises(ValueError, match="potvrďte"):
        w.apply(p)


def test_host_reference_print_selection_nested_tree_and_3d_paper_link(qtbot, generation, tmp_path):
    p, target, vid = restore(generation)
    w = AuthorMainWindow(
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    qtbot.addWidget(w)
    w.controller.project = p
    w.refresh()
    rows = p.segmented_variants[vid].triangle_bindings
    child = rows[7]
    assert set(w.paper.part_items) == p.material_part_ids()
    assert p.surfaces[target].part_id not in w.paper.part_items
    w.select_surface(child["surface_id"])
    assert w.selected_generation == vid
    assert w.paper.selected_part == child["part_id"]
    assert w.viewport.selected_surfaces == {child["surface_id"]}
    assert set(w.viewport.meshes) == set(p.print_material_view().surfaces)
    assert w.tree.currentItem().data(0, Qt.ItemDataRole.UserRole) == child["surface_id"]
    assert w.page_choice.isEnabled() and w.actions["segment"].isEnabled()
    # Original target can be inspected without appearing as extra paper material.
    w.select_surface(target)
    assert target in w.viewport.meshes and not w.page_choice.isEnabled()
    assert "netiskne" in w.segmentation_status.text()
    assert not any(r["surface_id"] in w.viewport.meshes for r in rows)
    w.restore_target()
    assert target in w.viewport.meshes and set(w.paper.part_items) == {p.surfaces[target].part_id}
    assert p.segmented_variants[vid].print_selected is False
    assert w.select_generation_button.isEnabled()
    w.use_generation()
    assert p.segmented_variants[vid].print_selected
    assert set(w.paper.part_items) == {r["part_id"] for r in rows}
    # Actual nested variant selection resolves its precise registry target.
    iterator = QTreeWidgetItemIterator(w.tree)
    while iterator.value():
        item = iterator.value()
        if item.data(0, Qt.ItemDataRole.UserRole) == ("variant", vid):
            w.tree.setCurrentItem(item)
            break
        iterator += 1
    assert w.selected_generation == vid and w.selected_surface == target
    w.controller._saved_digest = w.controller.digest(p.to_dict())


def test_grid_reference_ids_rejected(qtbot, generation):
    p, target, _ = restore(generation)
    with pytest.raises(ValueError, match="tiskové"):
        grid(qtbot, p, [p.surfaces[target].part_id])
