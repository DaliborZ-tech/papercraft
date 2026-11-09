"""Independent offscreen preview delta checks, never a native/novice proof."""
import copy
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QWidget,QDialogButtonBox,QDialog

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_connectors import MaterialPreview,ConnectorEditDialog


def preview(qtbot,source):
    state={'paths':{'CUT':[source]}}
    before=copy.deepcopy(state)
    p=SimpleNamespace(part_geometry=lambda pid:state)
    widget=MaterialPreview()
    qtbot.addWidget(widget)
    widget.show_part(p,'own')
    assert state==before
    return [item.path() for item in widget.scene().items() if hasattr(item,'path')][0]


def test_own_native_bezier_controls_and_endpoints_preserve_legacy_y_flip(qtbot):
    path=preview(qtbot,{'commands':[['M',2,3],['C',4,9,6,9,8,3],['L',8,-1],['L',2,-1],['Z']],'closed':True})
    assert path.elementAt(0).x==2 and path.elementAt(0).y==-3
    assert path.elementAt(1).type==QPainterPath.ElementType.CurveToElement
    assert (path.elementAt(1).x,path.elementAt(1).y)==(4,-9)
    assert (path.elementAt(2).x,path.elementAt(2).y)==(6,-9)
    assert (path.elementAt(3).x,path.elementAt(3).y)==(8,-3)


def test_own_native_quarter_arc_is_curved_and_reflected_not_a_straight_chord(qtbot):
    path=preview(qtbot,{'commands':[['M',1,0],['A',1,1,0,0,1,0,1],['L',0,0],['Z']],'closed':True})
    assert any(path.elementAt(i).type==QPainterPath.ElementType.CurveToElement for i in range(path.elementCount()))
    assert path.contains(QPointF(0.3,-0.3))
    assert not path.contains(QPointF(0.8,-0.8))
    box=path.boundingRect()
    assert box.left()==pytest.approx(0) and box.right()==pytest.approx(1)
    assert box.top()==pytest.approx(-1) and box.bottom()==pytest.approx(0)


def test_own_compound_native_path_retains_actual_odd_even_hole(qtbot):
    commands=[['M',0,0],['L',10,0],['L',10,10],['L',0,10],['Z'],
              ['M',3,3],['L',7,3],['L',7,7],['L',3,7],['Z']]
    path=preview(qtbot,{'commands':commands,'closed':True,'fill_rule':'evenodd'})
    assert path.fillRule()==Qt.FillRule.OddEvenFill
    assert path.contains(QPointF(1,-1))
    assert not path.contains(QPointF(5,-5))


def test_own_legacy_points_remain_supported_without_mutating_geometry(qtbot):
    path=preview(qtbot,{'points':[[2,3],[5,3],[5,7],[2,7]],'closed':True})
    assert path.contains(QPointF(3,-4))
    assert not path.contains(QPointF(3,4))


def test_own_curved_connector_dialog_cancel_then_confirm_preserves_source_and_replays_clone(qtbot):
    p=AuthorProject.new(scale=1)
    pid=p.add_profile(segments=[{'kind':'cubic','start':[0,0],'end':[20,0],'control1':[0,12],'control2':[20,12]},
                               {'kind':'line','start':[20,0],'end':[20,-5]},
                               {'kind':'line','start':[20,-5],'end':[0,-5]},
                               {'kind':'line','start':[0,-5],'end':[0,0]}])
    source=p.add_surface(pid)
    receiver=p.add_surface(p.add_profile([[0,-10],[20,-10],[20,-5],[0,-5]]))
    aid=p.attach_edge_to_surface(source,p.profiles[pid].segments[2].id,receiver,glue_direction=1)
    host=QWidget();host.project=p
    qtbot.addWidget(host)
    original=p.to_dict()
    canceled=ConnectorEditDialog(host,('attachment',aid))
    qtbot.addWidget(canceled)
    canceled.show()
    canceled.width.setValue(2)
    canceled.update_preview()
    assert canceled.preview_state is not None,canceled.status.text()
    qtbot.mouseClick(canceled.buttons.button(QDialogButtonBox.StandardButton.Cancel),Qt.MouseButton.LeftButton)
    assert p.to_dict()==original
    accepted=ConnectorEditDialog(host,('attachment',aid))
    qtbot.addWidget(accepted)
    accepted.show()
    accepted.width.setValue(2)
    qtbot.mouseClick(accepted.buttons.button(QDialogButtonBox.StandardButton.Ok),Qt.MouseButton.LeftButton)
    assert accepted.result()==QDialog.DialogCode.Accepted,accepted.status.text()
    assert p.to_dict()==original
    clone=AuthorProject.from_dict(original)
    cid=accepted.apply(clone)
    contacts=clone.connector_geometry(cid)['tabs']
    assert sum(t['available_area_mm2'] for t in contacts)==pytest.approx(32)
    assert p.to_dict()==original and clone.connectors[cid].width_mm==2
