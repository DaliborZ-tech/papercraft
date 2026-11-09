"""A bend obstruction must identify actual author-editable material in the UI.

These domain/Qt regressions are not native-desktop or novice-user evidence.
"""

import pytest
from PySide6.QtCore import QSettings, Qt

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_window import AuthorMainWindow


def scene(*, obstacle_tab=False, opposite_side=False, known=False):
    project = AuthorProject.new(scale=1)
    wp = project.add_profile(
        [[20, 0], [60, 0], [60, 20], [20, 20]],
        plane={"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    wall = project.add_surface(wp, name="Moving wall")
    base = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    aid = project.attach_edge_to_surface(
        wall, project.profiles[wp].segments[0].id, base,
        target_side="outside", glue_direction=-1,
    )
    cid = project.set_attachment_tab(aid, width_mm=5, taper=1)
    if obstacle_tab:
        plane = {"origin": [0, 3, 0], "u": [1, 0, 0], "v": [0, 0, 1]}
        outer = project.add_profile([[10, -6], [70, -6], [70, 2], [10, 2]], plane=plane)
        hole = project.add_profile([[19, -4.7], [61, -4.7], [61, 0.1], [19, 0.1]], plane=plane)
        receiver = project.add_surface(outer)
        op = project.add_profile(
            [[25, 0], [55, 0], [55, 3], [25, 3]],
            plane={"origin": [0, 0, -4.9], "u": [1, 0, 0], "v": [0, 1, 0]},
        )
        edge_index = 2
    else:
        receiver = base
        op = project.add_profile(
            [[70, 0], [90, 0], [90, 20], [70, 20]],
            plane={"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
        )
        edge_index = 0
    source = project.add_surface(op, name="Brace flange")
    other_aid = project.attach_edge_to_surface(
        source, project.profiles[op].segments[edge_index].id, receiver,
        target_side="inside" if opposite_side else "outside", glue_direction=-1,
    )
    other_cid = project.set_attachment_tab(other_aid, width_mm=4, taper=1)
    if obstacle_tab:
        project.add_hole(receiver, hole)
    if known:
        project.set_material_profile(thickness_mm=0.1)
    part = project.part_for_surface(source)
    project.parts[part].name = "Roof brace"
    return project, cid, other_cid, part


@pytest.mark.parametrize("known", [False, True])
def test_tab_collision_names_actual_obstacle_and_includes_its_part(known):
    project, cid, other_cid, part = scene(obstacle_tab=True, known=known)
    aid = project.connectors[cid].attachment_id
    result = project.connector_bend_clearance(cid)
    assert result["status"] == "COLLISION"
    assert result["tabs"][0]["obstacle_id"] == "tab:" + project.connectors[other_cid].tab_ids[0]
    diagnostic = next(i for i in project.validate_layout()
                      if i.code == "BEND_COLLISION" and i.joint_id == aid)
    assert part in diagnostic.part_ids
    assert "chlopně 1" in diagnostic.message
    assert "Roof brace" in diagnostic.message and "Brace flange" in diagnostic.message
    assert "do plochy modelu" not in diagnostic.message
    assert all(tid not in diagnostic.message
               for c in project.connectors.values() for tid in c.tab_ids)


@pytest.mark.parametrize("known", [False, True])
def test_uncertain_layers_remain_truthful_and_known_blocker_names_the_other_part(known):
    project, cid, _, part = scene(opposite_side=True, known=known)
    assert project.connector_bend_clearance(cid)["status"] == (
        "UNRESOLVED" if known else "UNVERIFIED"
    )
    diagnostics = [i for i in project.validate_layout()
                   if i.joint_id == project.connectors[cid].attachment_id
                   and i.code.startswith("BEND_")]
    if known:
        assert len(diagnostics) == 1 and diagnostics[0].code == "BEND_UNRESOLVED"
        assert part in diagnostics[0].part_ids
        assert "Neurčené vrstvy" in diagnostics[0].message
        assert "Roof brace" in diagnostics[0].message
    else:
        assert not diagnostics  # Unknown material remains a warning, never a false CLEAR.


@pytest.mark.ui
def test_keyboard_activation_opens_moving_connector_and_passes_obstacle_to_highlight(
    qtbot, tmp_path, monkeypatch,
):
    project, cid, _, obstacle_part = scene(obstacle_tab=True)
    settings = QSettings(str(tmp_path / "diagnostic.ini"), QSettings.Format.IniFormat)
    window = AuthorMainWindow(settings=settings)
    qtbot.addWidget(window)
    window.controller.project = project
    window.controller._saved_digest = window.controller.digest(project.to_dict())
    window.refresh()
    shown = []
    monkeypatch.setattr(window.paper, "show_issue", shown.append)
    aid = project.connectors[cid].attachment_id
    issue = next(i for i in project.validate_layout()
                 if i.code == "BEND_COLLISION" and i.joint_id == aid)
    item = next(window.issues.item(n) for n in range(window.issues.count())
                if window.issues.item(n).data(Qt.ItemDataRole.UserRole) == issue.id)
    window.show()
    window.issues.setCurrentItem(item)
    window.issues.setFocus()
    qtbot.keyClick(window.issues, Qt.Key.Key_Return)
    assert shown and obstacle_part in shown[-1].part_ids
    assert window.connectors_panel.relationship.currentData() == ("attachment", aid)
    owner = project.connectors[cid].owner_surface_id
    assert window.selected_part == project.part_for_surface(owner)
