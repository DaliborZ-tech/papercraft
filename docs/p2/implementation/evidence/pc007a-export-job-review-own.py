"""Independent lifecycle/transaction/UI error tests; all Qt is offscreen."""
import copy
import threading
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication,QDialog,QFileDialog,QMessageBox,QWidget
from test_workspace import window as _window_fixture

from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter import author_export as writer
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.ui import author_export_job as jobs,author_window

window=_window_fixture


def snapshot(*,curve=False):
    p=AuthorProject.new(scale=1)
    a=p.add_profile([[0,0],[50,0],[50,40],[0,40]])
    holes=[]
    if curve:
        holes=[p.add_profile(segments=[
            {'kind':'arc','start':[30,20],'end':[20,20],'data':{'center':[25,20],'sweep_deg':180}},
            {'kind':'arc','start':[20,20],'end':[30,20],'data':{'center':[25,20],'sweep_deg':180}}])]
    sid=p.add_surface(a,holes);p.set_placement(p.part_for_surface(sid),p.pages[0].id,30,30)
    return p.snapshot()


def files(path):return {p.name:p.read_bytes() for p in path.iterdir()}


@pytest.mark.parametrize('phase',['prepare','vectors','verify','publish'])
def test_actual_writer_cancel_at_each_boundary_preserves_owned_and_foreign_bytes(tmp_path,phase):
    data=snapshot(curve=True);directory=tmp_path/'bundle';writer.export_all(data,directory)
    (directory/'foreign.txt').write_bytes(b'author\x00private data');before=files(directory);seen=[]
    def checkpoint(current):
        seen.append(current)
        if current==phase:raise writer.ExportCancelledError('independent cancel '+phase)
    with pytest.raises(writer.ExportCancelledError):writer.export_all(data,directory,checkpoint=checkpoint)
    assert phase in seen and files(directory)==before
    assert not list(tmp_path.glob('.author-export-*'))


def test_cancel_before_queued_job_starts_acknowledges_without_any_writes(qtbot,tmp_path):
    data=snapshot();directory=tmp_path/'bundle';writer.export_all(data,directory)
    before=files(directory)
    dialog=jobs.ExportProgressDialog(data,directory);qtbot.addWidget(dialog)
    dialog.request_cancel();dialog.show()
    qtbot.waitUntil(lambda:dialog._finished,timeout=5000)
    assert dialog.cancelled and isinstance(dialog.error,writer.ExportCancelledError)
    assert dialog.result_paths is None and files(directory)==before


@pytest.mark.parametrize('close_kind',['escape','window_close'])
def test_close_requests_cancel_but_modal_survives_until_actual_writer_ack(qtbot,tmp_path,close_kind):
    entered=threading.Event();release=threading.Event();dialog=None
    data=snapshot(curve=True);directory=tmp_path/'bundle';writer.export_all(data,directory);before=files(directory)
    def paused(source,target,*,checkpoint):
        def boundary(phase):
            if phase=='verify':entered.set();assert release.wait(5)
            checkpoint(phase)
        return writer.export_all(source,target,checkpoint=boundary)
    dialog=jobs.ExportProgressDialog(data,directory,function=paused);qtbot.addWidget(dialog);dialog.show()
    try:
        qtbot.waitUntil(entered.is_set,timeout=5000)
        assert QApplication.activeModalWidget() is dialog
        if close_kind=='escape':qtbot.keyClick(dialog,Qt.Key.Key_Escape)
        else:assert dialog.close() is False
        assert dialog.isVisible() and not dialog._finished and dialog.job.cancel_requested.is_set()
        assert not dialog.cancel_button.isEnabled()
    finally:release.set()
    qtbot.waitUntil(lambda:dialog._finished,timeout=5000)
    assert dialog.cancelled and files(directory)==before


def test_mutating_original_after_constructor_cannot_change_worker_snapshot(qtbot,tmp_path):
    data=snapshot();original=copy.deepcopy(data);entered=threading.Event();release=threading.Event();seen={}
    def delayed(source,target,*,checkpoint):
        entered.set();assert release.wait(5);seen['source']=copy.deepcopy(source)
        return writer.export_all(source,target,checkpoint=checkpoint)
    dialog=jobs.ExportProgressDialog(data,tmp_path/'bundle',function=delayed);qtbot.addWidget(dialog);dialog.show()
    try:
        qtbot.waitUntil(entered.is_set)
        data['project_id']='changed';data['pages'][0]['parts'][0]['paths']['CUT'].clear()
    finally:release.set()
    qtbot.waitUntil(lambda:dialog._finished,timeout=5000)
    assert dialog.error is None and seen['source']==original


def test_cancel_after_first_atomic_replace_finishes_real_bundle_truthfully(qtbot,tmp_path,monkeypatch):
    data=snapshot();directory=tmp_path/'bundle';writer.export_all(data,directory)
    (directory/'foreign.txt').write_bytes(b'stay');started=threading.Event();release=threading.Event()
    original_replace=writer.os.replace;swaps=[]
    def paused_replace(source,target):
        result=original_replace(source,target);swaps.append((str(source),str(target)))
        if len(swaps)==1:started.set();assert release.wait(5)
        return result
    monkeypatch.setattr(writer.os,'replace',paused_replace)
    dialog=jobs.ExportProgressDialog(data,directory);qtbot.addWidget(dialog);dialog.show()
    try:
        qtbot.waitUntil(started.is_set,timeout=5000)
        dialog.request_cancel()
        assert not dialog._finished
    finally:release.set()
    qtbot.waitUntil(lambda:dialog._finished,timeout=5000)
    assert dialog.error is None and not dialog.cancelled and dialog.finished_during_cancel
    assert all(path.is_file() for path in dialog.result_paths)
    assert (directory/'foreign.txt').read_bytes()==b'stay'


def test_late_cancel_does_not_hide_atomic_publication_failure_and_rollback(qtbot,tmp_path,monkeypatch):
    data=snapshot();directory=tmp_path/'bundle';writer.export_all(data,directory)
    (directory/'foreign.txt').write_bytes(b'author owns this');before=files(directory)
    started=threading.Event();release=threading.Event();original_replace=writer.os.replace;count=0
    def failing_replace(source,target):
        nonlocal count
        count+=1
        if count==1:
            result=original_replace(source,target);started.set();assert release.wait(5);return result
        if count==2:raise OSError('independent publication IO failure')
        return original_replace(source,target)
    monkeypatch.setattr(writer.os,'replace',failing_replace)
    dialog=jobs.ExportProgressDialog(data,directory);qtbot.addWidget(dialog);dialog.show()
    try:
        qtbot.waitUntil(started.is_set,timeout=5000);dialog.request_cancel()
    finally:release.set()
    qtbot.waitUntil(lambda:dialog._finished,timeout=5000)
    assert isinstance(dialog.error,writer.ExportWriteError) and not isinstance(dialog.error,writer.ExportCancelledError)
    assert not dialog.cancelled and not dialog.finished_during_cancel and files(directory)==before


def host_fixture(window):
    def add(p):
        first=p.add_surface(p.add_profile([[0,0],[2000,0],[2000,1000],[0,1000]]))
        second=p.add_surface(p.add_profile([[0,0],[1000,0],[1000,1000],[0,1000]]))
        p.set_placement(p.part_for_surface(first),p.pages[0].id,30,30)
        p.set_placement(p.part_for_surface(second),p.pages[0].id,70,30)
        return first,second
    return window.controller.execute('unit host fixture',add)


def host_prompts(monkeypatch,tmp_path):
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path/'bundle'))
    messages=[];monkeypatch.setattr(QMessageBox,'information',lambda *a,**k:messages.append(a[2]));return messages


def test_real_modal_host_preserves_curve_error_identity_and_focus_for_repair(window,qtbot,tmp_path,monkeypatch):
    a,b=host_fixture(window);pid=window.project.part_for_surface(b);window.select_surface(a)
    error=CurveOutputError('independent exact geometry failure',part_id=pid,part_name='Target',page_index=0,report={'scope':'test'})
    seen=[];prompts=host_prompts(monkeypatch,tmp_path)
    def failing(source,target,*,checkpoint):checkpoint('verify');raise error
    def factory(*args,**kwargs):
        d=jobs.ExportProgressDialog(*args,**kwargs,function=failing);seen.append(d);return d
    monkeypatch.setattr(author_window,'ExportProgressDialog',factory)
    window.export_project()
    assert seen[0]._finished and seen[0].error is error
    assert window.selected_part==pid and window.selected_surface==b
    assert window._test_warnings==[str(error)] and not prompts


def test_host_cancel_is_status_only_and_parent_survives_nested_exec(window,qtbot,tmp_path,monkeypatch):
    a,b=host_fixture(window);before=copy.deepcopy(window.project.to_dict());prompts=host_prompts(monkeypatch,tmp_path)
    seen=[]
    def slow(source,target,*,checkpoint):
        checkpoint('vectors');time.sleep(.05);checkpoint('publish');return []
    def factory(*args,**kwargs):
        d=jobs.ExportProgressDialog(*args,**kwargs,function=slow);seen.append(d)
        QTimer.singleShot(0,d.request_cancel);return d
    monkeypatch.setattr(author_window,'ExportProgressDialog',factory)
    window.export_project()
    assert seen[0].cancelled and not prompts and not window._test_warnings
    assert window.isVisible() and window.project.to_dict()==before
    assert window.statusBar().currentMessage()


def test_unresolved_loft_guidance_offers_source_repair_before_recompute(window,qtbot):
    def add(p):
        a=p.add_profile([[0,0],[2000,0],[2000,1000]],closed=False)
        b=p.copy_profile(a,plane={'origin':[0,0,1000],'u':[1,0,0],'v':[0,1,0]})
        pairs=[{'first_segment_id':x.id,'second_segment_id':y.id,'first_interval':[0,1],'second_interval':[0,1]} for x,y in zip(p.profiles[a].segments,p.profiles[b].segments)]
        sid=p.add_loft(a,b,correspondences=pairs)
        import math
        angle=math.radians(17)
        p.set_profile_plane(b,origin=[0,0,1000],u=[math.cos(angle),math.sin(angle),0],v=[-math.sin(angle),math.cos(angle),0])
        return sid
    sid=window.controller.execute('unresolved source fixture',add);window.select_surface(sid)
    text=window.hint.text()
    assert '\u0055pravte tvar' in text and '\u0053amotn\u00fd p\u0159epo\u010det nezm\u011bn\u00ed' in text
    assert window.project.loft_status(sid)['status']!='EXACT'
