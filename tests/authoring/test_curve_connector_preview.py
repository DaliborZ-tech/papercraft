"""Regression of actual desktop failure: native CUT is not a points-only polygon."""

import copy

import pytest
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QDialogButtonBox
from test_connector_panel import Host

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_connectors import ConnectorEditDialog, MaterialPreview

pytestmark = pytest.mark.ui


def bezier_panel(project):
    pid = project.add_profile(segments=[
        {"kind": "cubic", "start": [0, 0], "end": [80, 0],
         "data": {"control1": [20, 30], "control2": [60, 30]}},
        {"kind": "line", "start": [80, 0], "end": [80, -10]},
        {"kind": "line", "start": [80, -10], "end": [0, -10]},
        {"kind": "line", "start": [0, -10], "end": [0, 0]},
    ])
    return project.add_surface(pid), project.profiles[pid].segments[2].id


def test_material_preview_draws_actual_native_bezier_instead_of_requiring_points(qtbot):
    project = AuthorProject.new(scale=1)
    sid, _ = bezier_panel(project)
    preview = MaterialPreview()
    qtbot.addWidget(preview)
    preview.show_part(project, project.part_for_surface(sid))
    paths = [item.path() for item in preview.scene().items() if hasattr(item, "path")]
    assert any(path.elementAt(i).type == QPainterPath.ElementType.CurveToElement
               for path in paths for i in range(path.elementCount()))
    assert preview.scene().itemsBoundingRect().height() > 30


def test_staged_tab_dialog_can_preview_and_accept_native_curve_source_without_mutation(qtbot):
    project = AuthorProject.new(scale=1)
    sid, edge = bezier_panel(project)
    receiver = project.add_surface(project.add_profile([[0, -20], [80, -20], [80, -10], [0, -10]]))
    aid = project.attach_edge_to_surface(sid, edge, receiver, glue_direction=1)
    original = copy.deepcopy(project.to_dict())
    host = Host(project, sid)
    qtbot.addWidget(host)
    dialog = ConnectorEditDialog(host, ("attachment", aid))
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.width.setValue(2)
    dialog.update_preview()
    assert dialog.preview_state is not None, dialog.status.text()
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert "128" in dialog.status.text()  # 80*2*(1+.6)/2, independently expected.
    dialog.accept()
    assert dialog.result_parameters["width_mm"] == 2
    assert project.to_dict() == original
    clone = AuthorProject.from_dict(original)
    cid = dialog.apply(clone)
    assert clone.connectors[cid].width_mm == 2
    assert project.to_dict() == original
