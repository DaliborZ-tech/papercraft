"""Independent offscreen B command checks; no OS input or novice substitution."""
import copy
import json
import os
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QGroupBox, QMessageBox

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.ui.author_attachment import AttachmentDialog, GlueRegionDialog
from archpapercraft.ui.author_connectors import ConnectorEditDialog, choose
from archpapercraft.ui.author_window import AuthorMainWindow
from archpapercraft.ui.author_paper import AuthorPaperView
import archpapercraft

assert Path(archpapercraft.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())

@pytest.fixture(autouse=True)
def close_owned_windows_without_dirty_prompt(monkeypatch):
    # These tests directly inspect the command result; no native/modal proof.
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Discard)
    monkeypatch.setattr(QMessageBox,'information',lambda *a,**kw:QMessageBox.StandardButton.Ok)

def construction():
    p=AuthorProject.new(scale=1)
    profile=p.add_profile([[0,0],[40,0],[40,20],[0,20]])
    source=p.add_surface(profile,name='Own wall')
    target=p.add_surface(p.add_profile([[0,0],[200,0],[200,200],[0,200]]),name='Own receiver')
    return p,source,target,p.profiles[profile].segments[0].id

def attachment(qtbot):
    p,s,t,e=construction();d=AttachmentDialog(p,(s,e),unit='mm',unit_factor=1)
    qtbot.addWidget(d);d.show();qtbot.wait(10)
    for field,value in zip(d.fields,[60,60,84,92]):field.setValue(value)
    d.numeric_trace()
    assert d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(),d.feedback.text()
    return p,s,t,e,d

def pending(qtbot,field,text):
    for parent in [field.parentWidget(),field.parentWidget().parentWidget()]:
        if isinstance(parent,QGroupBox):parent.setChecked(True)
    field.setFocus();qtbot.wait(2)
    # Use the widget's actual locale, rather than assuming an English decimal.
    field.lineEdit().setText(text.replace('.',field.locale().decimalPoint()))
    assert field.hasFocus() or field.lineEdit().hasFocus()

@pytest.mark.parametrize('index,value',[(0,108),(1,124),(2,36),(3,28)])
def test_pending_each_coordinate_is_used_before_result_spec(qtbot,index,value):
    p,s,t,e,d=attachment(qtbot);before=copy.deepcopy(p.to_dict())
    pending(qtbot,d.fields[index],str(value));d.confirm()
    assert d.result()==QDialog.DialogCode.Accepted,d.feedback.text()
    actual=sum(d.result_spec['trace'],[])
    expected=[60.,60.,84.,92.];expected[index]=value
    assert actual==expected
    aid=AttachmentDialog.apply(p,d.result_spec)
    assert p.attachment_geometry(aid)['material_length_mm']==pytest.approx(40)
    assert len(p.surfaces)==len(before['surfaces'])==2

@pytest.mark.parametrize('name,value,interval',[
    ('start_fraction','25',[.25,1]),('end_fraction','75',[0,.75]),('angle','37.5',[0,1])])
def test_pending_interval_and_angle(qtbot,name,value,interval):
    p,s,t,e,d=attachment(qtbot);field=getattr(d,name)
    pending(qtbot,field,value);d.confirm()
    assert d.result()==QDialog.DialogCode.Accepted,d.feedback.text()
    assert d.result_spec['interval']==interval
    aid=AttachmentDialog.apply(p,d.result_spec)
    assert p.attachment_geometry(aid)['material_length_mm']==pytest.approx(40*(interval[1]-interval[0]))
    if name=='angle':assert d.result_spec['angle_deg']==37.5

@pytest.mark.parametrize('name,text',[('angle','-'),('start_fraction','100'),('end_fraction','0')])
def test_invalid_pending_attachment_cannot_accept_or_mutate(qtbot,name,text):
    p,s,t,e,d=attachment(qtbot);before=copy.deepcopy(p.to_dict())
    pending(qtbot,getattr(d,name),text);d.confirm()
    assert d.result()!=QDialog.DialogCode.Accepted
    assert d.result_spec is None and p.to_dict()==before
    d.reject();assert p.to_dict()==before

def host(qtbot,tmp_path):
    p,s,t,e=construction();aid=p.place_and_attach_edge(s,e,t,[60,60],[100,60],angle_deg=90)
    cid=p.set_attachment_tab(aid,width_mm=6,taper=.5)
    w=AuthorMainWindow(settings=QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat))
    qtbot.addWidget(w);w.controller.project=p;w.controller._saved_digest=w.controller.digest(p.to_dict());w.refresh();w.select_surface(s)
    w.show();qtbot.wait(10)
    return w,aid,cid,s,t

@pytest.mark.parametrize('name,text,expected',[('width','7',7),('taper','.75',.75),('count','3',3),('gap','1.5',1.5)])
def test_connector_pending_inputs_apply_once_then_undo(qtbot,tmp_path,name,text,expected):
    w,aid,cid,s,t=host(qtbot,tmp_path);before=copy.deepcopy(w.project.to_dict())
    d=ConnectorEditDialog(w,('attachment',aid),connector_id=cid);qtbot.addWidget(d);d.show();qtbot.wait(5)
    d.advanced_body.setVisible(True)
    pending(qtbot,getattr(d,name),text);d.accept()
    assert d.result()==QDialog.DialogCode.Accepted,d.status.text()
    assert w.project.to_dict()==before
    w.controller.execute('Own tab edit',lambda p:d.apply(p))
    attr={'width':'width_mm','gap':'gap_mm'}.get(name,name)
    assert getattr(w.project.connectors[cid],attr)==expected
    assert len(w.controller._undo)==1
    w.controller.undo();assert w.project.to_dict()==before
    w.controller.redo();assert getattr(w.project.connectors[cid],attr)==expected

def test_invalid_tab_number_blocks_acceptance_and_cancel_is_pure(qtbot,tmp_path):
    w,aid,cid,s,t=host(qtbot,tmp_path);before=copy.deepcopy(w.project.to_dict())
    d=ConnectorEditDialog(w,('attachment',aid),connector_id=cid);qtbot.addWidget(d);d.show();qtbot.wait(5)
    pending(qtbot,d.width,'-');d.accept()
    assert d.result()!=QDialog.DialogCode.Accepted and d.result_parameters is None
    d.reject();assert w.project.to_dict()==before and not w.controller.can_undo

def test_receiving_hole_and_region_draft_are_not_silently_committed(qtbot):
    p,s,t,e,d=attachment(qtbot);d.reject()
    p.add_hole(t,p.add_profile([[70,65],[80,65],[80,90],[70,90]]))
    before=copy.deepcopy(p.to_dict());d=AttachmentDialog(p,(s,e),unit='mm',unit_factor=1);qtbot.addWidget(d)
    for f,v in zip(d.fields,[60,60,84,92]):f.setValue(v)
    d.numeric_trace();d.confirm()
    assert d.result()!=QDialog.DialogCode.Accepted and p.to_dict()==before
    assert 'MATERIAL' in d.feedback.text()

def test_schema1_source_survives_failed_operation_undo_and_saveas(qtbot,tmp_path):
    p,s,t,e=construction();data=p.to_dict();data.update(schema_version=1,writer_version='0.3.0-experimental');data.pop('attachments');data.pop('next_attachment_number')
    original=tmp_path/'old.apcraft';original.write_text(json.dumps(data),encoding='utf8');saved=original.read_bytes()
    c=AuthorController();c.open(original)
    with pytest.raises(ValidationError):c.execute('Invalid',lambda p:p.set_transform(s,[float('nan'),0,0]))
    assert c.copy_source_path==original and original.read_bytes()==saved
    c.execute('Own rename',lambda p:setattr(p,'name','Renamed'));c.undo();c.redo()
    with pytest.raises(ValueError):c.save(original)
    assert original.read_bytes()==saved
    c.save(tmp_path/'own-copy.apcraft');assert original.read_bytes()==saved
    with pytest.raises(ValueError):c.save(original)
    assert original.read_bytes()==saved

def test_glue_patch_cancel_is_pure_and_unfinished_region_blocks(qtbot):
    p=AuthorProject.new(scale=1);s=p.add_surface(p.add_profile([[20,20],[40,20],[40,40],[20,40]]));t=p.add_surface(p.add_profile([[0,0],[100,0],[100,100],[0,100]]))
    before=copy.deepcopy(p.to_dict());d=GlueRegionDialog(p,s,unit='mm',unit_factor=1);qtbot.addWidget(d)
    d.target_sketch.region=[[10,10],[50,10],[50,50],[10,50]];d.update_preview()
    assert d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    d.target_sketch.drawing=True;d.target_sketch.points=[[5,5]];d.update_preview();d.confirm()
    assert d.result()!=QDialog.DialogCode.Accepted and d.result_spec is None
    d.reject();assert p.to_dict()==before

@pytest.mark.parametrize('new_identity',[False,True])
def test_B04_open_fit_preserves_normal_refresh_camera(qtbot,new_identity):
    p,s,t,e=construction()
    for index,pid in enumerate(p.parts):
        page=p.pages[0].id if index==0 else p.add_page()
        p.set_placement(pid,page_id=page,x_mm=40,y_mm=60)
    v=AuthorPaperView();qtbot.addWidget(v);v.resize(700,450);v.show();v.set_project(p);qtbot.wait(15)
    v.resetTransform();v.scale(13,13);v.centerOn(9000,9000);qtbot.wait(5)
    matrix=v.transform();center=v.mapToScene(v.viewport().rect().center())
    clone=AuthorProject.from_dict(p.to_dict());v.set_project(clone);qtbot.wait(5)
    assert v.transform()==matrix
    assert (v.mapToScene(v.viewport().rect().center())-center).manhattanLength()<.1
    if new_identity:
        data=clone.to_dict();data['project_id']=AuthorProject.new().project_id
        clone=AuthorProject.from_dict(data)
        v.set_project(clone)
    else:v.set_project(clone,frame=True)
    qtbot.wait(15)
    visible=v.mapToScene(v.viewport().rect()).boundingRect()
    assert all(visible.contains(item.sceneBoundingRect().center()) for item in v.part_items.values())
    assert v.transform()!=matrix
