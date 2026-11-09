"""Independent preservation checks and actual offscreen dialogs, not novice evidence."""

import copy
from dataclasses import asdict

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel
from test_interior import wall_roof
from test_paper import two_panels

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import ValidationError, load_project
from archpapercraft.authoring.editing import (
    delete_material_part,
    part_deletion_impact,
    rename_author_entities,
)
from archpapercraft.ui.author_editing import DeletePartDialog, RenameDialog


def connected_component():
    project, a, b, ea, eb = two_panels()
    project.surfaces[a].name = "Západní stěna"
    project.surfaces[b].name = "Střecha"
    pid = project.part_for_surface(a)
    fold = project.connect_edges(a, ea, b, eb, mode="fold")
    pc = project.add_profile(
        [[20000, 0], [30000, 0], [30000, 4000], [20000, 4000]], name="Protikus"
    )
    c = project.add_surface(pc, name="Východní stěna")
    cut = project.connect_edges(
        b,
        project.profiles[project.surfaces[b].profile_id].segments[1].id,
        c,
        project.profiles[pc].segments[3].id,
    )
    project.set_tab(cut, owner=c, width_mm=2)
    cid = project.joints[cut].connector_id
    pd = project.add_profile(
        [[-1500, -2000], [11500, -2000], [11500, 8000], [-1500, 8000]], name="Půdorys"
    )
    d = project.add_surface(pd, name="Základna")
    attachment = project.attach_edge_to_surface(
        a, project.profiles[project.surfaces[a].profile_id].segments[0].id, d
    )
    ac = project.set_attachment_tab(attachment, width_mm=2)
    project.recompute()
    for index, part in enumerate(project.parts):
        page = project.pages[0].id if index == 0 else project.add_page()
        project.set_placement(part, page, 60, 60, 30, position_locked=True, rotation_locked=True)
    return project, pid, [a, b], [c, d], [fold, cut], attachment, [cid, ac]


def controller(project):
    result = AuthorController()
    result.project = project
    result._saved_digest = result.digest(project.to_dict())
    return result


def test_impact_is_read_only_and_names_exact_removed_relations_and_retained_profiles():
    p, pid, removed, others, joints, aid, connectors = connected_component()
    before = copy.deepcopy(p.to_dict())
    impact = part_deletion_impact(p, pid)
    assert p.to_dict() == before
    assert {s["id"] for s in impact["surfaces"]} == set(removed)
    assert {s["name"] for s in impact["surfaces"]} == {"Západní stěna", "Střecha"}
    assert {r["id"] for r in impact["joints"]} == set(joints)
    assert [r["id"] for r in impact["attachments"]] == [aid]
    assert {r["id"] for r in impact["connectors"]} == set(connectors)
    assert {r["id"] for r in impact["affected_parts"]} == {p.part_for_surface(s) for s in others}
    assert {r["id"] for r in impact["preserved_profiles"]} == {
        p.surfaces[s].profile_id for s in removed
    }


def test_delete_whole_fold_preserves_source_frames_layout_locks_counters_and_mate_material():
    p, pid, removed, others, joints, aid, connectors = connected_component()
    before = copy.deepcopy(p.to_dict())
    expected_profiles = copy.deepcopy(p.profiles)
    other_parts = {
        p.part_for_surface(s): copy.deepcopy(p.parts[p.part_for_surface(s)]) for s in others
    }
    delete_material_part(p, pid)
    assert set(p.surfaces) == set(others) and pid not in p.placements and pid not in p.parts
    assert not (set(joints) & set(p.joints)) and aid not in p.attachments
    assert not (set(connectors) & set(p.connectors))
    assert p.profiles == expected_profiles  # Editable source, including deleted material outlines.
    for other, old in other_parts.items():
        actual = copy.deepcopy(p.parts[other])
        assert actual.stale
        actual.stale = old.stale
        assert actual == old  # Every coordinate, frame, edge ID, label and cached path stays.
        assert asdict(p.placements[other]) == before["placements"][other]
    assert {s: asdict(p.surfaces[s]) for s in others} == {s: before["surfaces"][s] for s in others}
    for key in ("next_part_number", "next_joint_number", "next_attachment_number"):
        assert getattr(p, key) == before[key]
    assert p.revision == before["revision"] + 1
    assert not any(s in p.surfaces for s in removed)
    p.recompute()
    assert all(not part.stale for part in p.parts.values())


def test_band_removal_keeps_original_source_contact_and_other_real_material():
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof)
    original = copy.deepcopy(p.attachments[aid])
    band = p.add_glue_band(aid, width_mm=2)
    p.recompute()
    band_surfaces = set(p.parts[band].surface_ids)
    assert len(band_surfaces) == 2
    source_profiles = copy.deepcopy(p.profiles)
    impact = delete_material_part(p, band)
    assert len(impact["joints"]) == 1 and len(impact["attachments"]) == 2
    assert set(p.surfaces) == {wall, roof} and p.attachments == {aid: original}
    assert p.profiles == source_profiles and not p.joints
    assert all(s not in p.surfaces for s in band_surfaces)


def test_unrelated_unresolved_reference_does_not_block_delete_undo_redo_save_open(
    tmp_path, monkeypatch
):
    p, pid, *_ = connected_component()
    e = p.add_profile([[40000, 0], [41000, 0], [41000, 1000], [40000, 1000]])
    f = p.add_profile([[41000, 0], [42000, 0], [42000, 1000], [41000, 1000]])
    se, sf = p.add_surface(e), p.add_surface(f)
    joint = p.connect_edges(se, p.profiles[e].segments[1].id, sf, p.profiles[f].segments[3].id)
    p.update_profile(e, [[40000, 0], [41000, 0], [41000, 1200], [40000, 1200]])
    assert p.joints[joint].unresolved and p.parts[p.part_for_surface(se)].stale
    before = copy.deepcopy(p.to_dict())
    ctl = controller(p)
    # Recompute cannot resolve this author reference and is intentionally unavailable.
    monkeypatch.setattr(
        p, "recompute", lambda *a, **kw: pytest.fail("Deletion tried global recompute")
    )
    ctl.execute("Odstranit", lambda model: delete_material_part(model, pid))
    after = copy.deepcopy(ctl.project.to_dict())
    assert after["joints"][joint] == before["joints"][joint]
    assert after["profiles"][e] == before["profiles"][e]
    ctl.save(tmp_path / "edited.apcraft")
    assert load_project(tmp_path / "edited.apcraft").to_dict() == after
    ctl.undo()
    assert ctl.project.to_dict() == before
    ctl.redo()
    assert ctl.project.to_dict() == after


def test_delete_isolated_part_does_not_invalidate_unrelated_cached_work():
    p, wall, roof, _ = wall_roof()
    p.recompute()
    keep = p.part_for_surface(roof)
    retained = copy.deepcopy(p.parts[keep])
    delete_material_part(p, p.part_for_surface(wall))
    assert p.parts[keep] == retained and not p.parts[keep].stale


def test_deleted_material_profiles_and_holes_can_recreate_an_editable_new_part():
    p, wall, roof, _ = wall_roof()
    outer = p.surfaces[wall].profile_id
    hole = p.add_profile(
        [[2000, 1000], [3000, 1000], [3000, 2000], [2000, 2000]],
        name="Vlastní průhled",
        plane=p.profiles[outer].plane,
    )
    p.add_hole(wall, hole)
    p.recompute()
    profiles = copy.deepcopy(p.profiles)
    old_part = p.part_for_surface(wall)
    next_number = p.next_part_number
    impact = delete_material_part(p, old_part)
    assert {r["id"] for r in impact["preserved_profiles"]} == {outer, hole}
    assert p.profiles == profiles and roof in p.surfaces
    recreated = p.add_surface(outer, holes=[hole], name="Nová plocha ze zachovaných skic")
    assert recreated != wall and p.part_for_surface(recreated) != old_part
    assert p.parts[p.part_for_surface(recreated)].number == next_number
    assert p.surfaces[recreated].profile_id == outer and p.surfaces[recreated].hole_profile_ids == [
        hole
    ]
    assert len(p.part_geometry(p.part_for_surface(recreated))["polygons"][recreated]) == 2


def test_deletion_invalidates_indirect_cache_dependency_without_removing_that_relation():
    p, wall, roof, edge = wall_roof()
    attachment = p.attach_edge_to_surface(wall, edge, roof)
    roof_profile = p.profiles[p.surfaces[roof].profile_id]
    profile = p.add_profile(
        [[0, 0], [10800, 0], [10800, 1000], [0, 1000]], plane=roof_profile.plane
    )
    surface = p.add_surface(profile, name="Neodstraňovaný soused")
    joint = p.connect_edges(
        roof, roof_profile.segments[0].id, surface, p.profiles[profile].segments[0].id
    )
    p.recompute()
    retained_joint = copy.deepcopy(p.joints[joint])
    other_part = p.part_for_surface(surface)
    old_cache = copy.deepcopy(p.parts[other_part])
    delete_material_part(p, p.part_for_surface(wall))
    assert attachment not in p.attachments and p.joints[joint] == retained_joint
    assert p.parts[other_part].stale
    actual = copy.deepcopy(p.parts[other_part])
    actual.stale = old_cache.stale
    assert actual == old_cache


def test_postmutation_validation_failure_rolls_back_the_entire_delete(monkeypatch):
    p, pid, *_ = connected_component()
    before = p.to_dict()

    def fail():
        raise ValidationError("Validation refused the changed state")

    monkeypatch.setattr(p, "validate", fail)
    with pytest.raises(ValidationError, match="refused"):
        delete_material_part(p, pid)
    assert p.to_dict(validate=False) == before


@pytest.mark.parametrize("bad", [None, "missing", [], False])
def test_invalid_delete_is_typed_and_atomic(bad):
    p, *_ = wall_roof()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        delete_material_part(p, bad)
    assert p.to_dict() == before


def test_rename_changes_only_names_revision_and_needed_stale_markers():
    p, wall, roof, _ = wall_roof()
    p.recompute()
    pid = p.part_for_surface(wall)
    before = p.to_dict()
    rename_author_entities(
        p,
        project_name="Moje brána",
        surface_id=wall,
        surface_name="Čelní stěna",
        part_id=pid,
        part_name="Potištěný štít",
    )
    after = p.to_dict()
    assert p.name == "Moje brána" and p.surfaces[wall].name == "Čelní stěna"
    assert p.parts[pid].name == "Potištěný štít" and p.parts[pid].stale
    assert p.parts[p.part_for_surface(roof)].stale is False
    after["name"], after["revision"] = before["name"], before["revision"]
    after["surfaces"][wall]["name"] = before["surfaces"][wall]["name"]
    after["parts"][pid]["name"] = before["parts"][pid]["name"]
    after["parts"][pid]["stale"] = before["parts"][pid]["stale"]
    assert after == before


def test_equal_rename_is_a_true_controller_noop():
    p, wall, _, _ = wall_roof()
    ctl = controller(p)
    pid = p.part_for_surface(wall)
    before = p.to_dict()
    ctl.execute(
        "Stejné názvy",
        lambda model: rename_author_entities(
            model,
            project_name=model.name,
            surface_id=wall,
            surface_name=model.surfaces[wall].name,
            part_id=pid,
            part_name=model.parts[pid].name,
        ),
    )
    assert p.to_dict() == before and not ctl.can_undo and not ctl.dirty


@pytest.mark.parametrize(
    "changes",
    [
        {"project_name": ""},
        {"project_name": "  "},
        {"project_name": 5},
        {"project_name": "Valid", "surface_id": "missing", "surface_name": "Wall"},
        {"project_name": "Valid", "part_id": "missing", "part_name": "Roof"},
        {"project_name": "Valid", "surface_name": "Wall"},
        {"project_name": "Invalid\nname"},
    ],
)
def test_bad_rename_rejects_all_fields_atomically(changes):
    p, *_ = wall_roof()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        rename_author_entities(p, **changes)
    assert p.to_dict() == before


def test_delete_dialog_cancel_and_actual_confirm_bind_preview_to_one_undo_command(qtbot):
    p, pid, *_ = connected_component()
    before = p.to_dict()
    ctl = controller(p)
    dialog = DeletePartDialog(p, pid)
    qtbot.addWidget(dialog)
    dialog.show()
    assert (
        "Západní stěna" in dialog.details.toPlainText()
        and "Základna" in dialog.details.toPlainText()
    )
    assert "Zachované obrysové profily" in dialog.details.toPlainText()
    assert not any(s["id"] in dialog.details.toPlainText() for s in dialog.impact["surfaces"])
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel), Qt.MouseButton.LeftButton
    )
    with pytest.raises(ValidationError, match="potvrzeno"):
        dialog.apply(p)
    assert p.to_dict() == before
    dialog = DeletePartDialog(p, pid)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    assert dialog.result() == QDialog.DialogCode.Accepted and p.to_dict() == before
    result = ctl.execute("Odstranit díl", dialog.apply)
    assert result == dialog.impact and pid not in ctl.project.parts and len(ctl._undo) == 1
    ctl.undo()
    assert ctl.project.to_dict() == before


def test_delete_dialog_detects_changed_impact_instead_of_deleting_stale_preview(qtbot):
    p, wall, _, _ = wall_roof()
    pid = p.part_for_surface(wall)
    dialog = DeletePartDialog(p, pid)
    qtbot.addWidget(dialog)
    rename_author_entities(p, surface_id=wall, surface_name="Přejmenovaná stěna")
    dialog.accept()
    before = p.to_dict()
    with pytest.raises(ValidationError, match="náhledu"):
        dialog.apply(p)
    assert p.to_dict() == before


def test_rename_dialog_real_typing_cancel_noop_and_persistence_are_source_preserving(
    qtbot, tmp_path
):
    p, wall, _, _ = wall_roof()
    pid = p.part_for_surface(wall)
    ctl = controller(p)
    before = p.to_dict()
    dialog = RenameDialog(p, surface_id=wall, part_id=pid)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.surface_name.selectAll()
    qtbot.keyClicks(dialog.surface_name, "West gate")
    dialog.reject()
    assert p.to_dict() == before
    dialog = RenameDialog(p, surface_id=wall, part_id=pid)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    ctl.execute("Názvy beze změny", dialog.apply)
    assert not ctl.can_undo and not ctl.dirty
    dialog = RenameDialog(p, surface_id=wall, part_id=pid)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.surface_name.selectAll()
    qtbot.keyClicks(dialog.surface_name, "West gate")
    dialog.part_name.selectAll()
    qtbot.keyClicks(dialog.part_name, "Own printed panel")
    # No Return/focusOut needed before clicking OK: current visible QLineEdit text is authority.
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    assert p.to_dict() == before
    ctl.execute("Pojmenovat", dialog.apply)
    assert ctl.project.surfaces[wall].name == "West gate"
    assert ctl.project.parts[pid].name == "Own printed panel" and len(ctl._undo) == 1
    after = ctl.project.to_dict()
    ctl.save(tmp_path / "renamed.apcraft")
    assert load_project(tmp_path / "renamed.apcraft").to_dict() == after
    ctl.undo()
    assert ctl.project.to_dict() == before
    ctl.redo()
    assert ctl.project.to_dict() == after


def test_dialog_names_are_plain_text_and_invalid_empty_rename_cannot_confirm(qtbot):
    p, wall, _, _ = wall_roof()
    pid = p.part_for_surface(wall)
    rename_author_entities(
        p,
        project_name="<b>Own model</b>",
        surface_id=wall,
        surface_name="<i>Wall</i>",
        part_id=pid,
        part_name="<a>Panel</a>",
    )
    delete = DeletePartDialog(p, pid)
    qtbot.addWidget(delete)
    assert "<i>Wall</i>" in delete.details.toPlainText()
    assert "<a>Panel</a>" in " ".join(label.text() for label in delete.findChildren(QLabel))
    assert all(
        label.textFormat() == Qt.TextFormat.PlainText for label in delete.findChildren(QLabel)
    )
    rename = RenameDialog(p, surface_id=wall, part_id=pid)
    qtbot.addWidget(rename)
    assert rename.project_name.text() == "<b>Own model</b>"
    assert all(
        label.textFormat() == Qt.TextFormat.PlainText for label in rename.findChildren(QLabel)
    )
    rename.surface_name.setText(" ")
    assert not rename.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    rename.accept()
    assert rename.result() != QDialog.DialogCode.Accepted and rename.changes is None
