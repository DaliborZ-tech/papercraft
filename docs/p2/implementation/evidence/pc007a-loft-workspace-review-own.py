"""Independent host and detached source-binding oracles, not native/human proof."""
import copy
import hashlib
import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QDialogButtonBox
from test_workspace import window as _window_fixture

from archpapercraft.authoring import AuthorProject,load_project
from archpapercraft.authoring.editing import part_deletion_impact,delete_material_part
from archpapercraft.ui.author_loft import LoftProfilesDialog
from archpapercraft.ui.author_profile_placement import ProfilePlacementDialog

window=_window_fixture


def sources(window):
    def add(p):
        a=p.add_profile([[0,0],[2000,0],[2000,1000]],closed=False)
        b=p.copy_profile(a,plane={'origin':[0,0,1000],'u':[1,0,0],'v':[0,1,0]})
        return a,b
    return window.controller.execute('test setup authored source profiles',add)


def actual_preview(qtbot,monkeypatch,*,mutate=None):
    def execute(dialog):
        if mutate:mutate(dialog)
        dialog.confirm_pairs.setChecked(True)
        assert dialog.request_preview()
        qtbot.waitUntil(lambda:dialog._running_job is None,timeout=30000)
        assert dialog.apply_button.isEnabled(),dialog.feedback.text()
        dialog.accept();return dialog.result()
    monkeypatch.setattr(LoftProfilesDialog,'exec',execute)


def create(window,qtbot,monkeypatch):
    a,b=sources(window);window.select_profile(a);actual_preview(qtbot,monkeypatch)
    window.actions['loft'].trigger()
    assert not window._test_warnings
    return a,b,window.selected_surface,window.selected_part


def test_second_profile_tree_actual_selection_enables_live_plane_and_curve(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    child=window.tree.topLevelItem(0).child(1)
    window.tree.setCurrentItem(child)
    assert window.selected_profile==b and window.selected_surface is None
    assert window.sketch.profile_id==b and window.sketch.surface_id is None
    assert window.curve_choice.currentData()[0]==b
    assert window.actions['profile_plane'].isEnabled() and window.actions['edit_curve'].isEnabled()
    assert not window.actions['hole'].isEnabled() and not window.actions['edit_loft'].isEnabled()


def test_selecting_second_source_curve_keeps_loft_and_draws_correct_sketch(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    segment=window.project.profiles[b].segments[-1].id
    index=next(i for i in range(window.curve_choice.count()) if window.curve_choice.itemData(i)==(b,segment))
    window.curve_choice.setCurrentIndex(index)
    assert window.selected_surface==sid and window.selected_profile==b
    assert window.sketch.profile_id==b and window.sketch.surface_id is None
    assert window.selected_edge==(sid,segment)
    assert window.actions['profile_plane'].isEnabled() and window.actions['edit_loft'].isEnabled()


def test_noop_loft_edit_preserves_source_pair_ids_frame_placement_and_undo_depth(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    window.controller.execute('place and lock',lambda p:p.set_placement(pid,p.pages[0].id,42,53,27))
    before=copy.deepcopy(window.project.to_dict());undo=len(window.controller._undo)
    window.select_surface(sid);window.actions['edit_loft'].trigger()
    assert not window._test_warnings
    assert window.project.surfaces[sid].params==before['surfaces'][sid]['params']
    assert set(window.project.profiles)=={a,b} and window.selected_part==pid
    assert window.project.to_dict()['placements']==before['placements']
    assert window.project.to_dict()['parts'][pid]['frame']==before['parts'][pid]['frame']
    # A no-op can rebuild stale internals; it must not duplicate identity or author work.
    assert len(window.controller._undo)<=undo+1


def test_changed_loft_tolerance_one_command_preserves_anchors_and_undo_redo(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    window.controller.execute('place',lambda p:p.set_placement(pid,p.pages[0].id,42,53,27))
    before=copy.deepcopy(window.project.to_dict());undo=len(window.controller._undo)
    def mutate(dialog):dialog.tolerance.setValue(.003)
    actual_preview(qtbot,monkeypatch,mutate=mutate)
    window.select_surface(sid);window.actions['edit_loft'].trigger()
    assert not window._test_warnings
    assert window.project.surfaces[sid].params['tolerance_mm']==.003
    assert len(window.controller._undo)==undo+1
    assert window.project.to_dict()['placements']==before['placements']
    assert window.project.to_dict()['parts'][pid]['frame']==before['parts'][pid]['frame']
    after=copy.deepcopy(window.project.to_dict())
    window.actions['undo'].trigger();assert window.project.to_dict()==before
    window.actions['redo'].trigger();assert window.project.to_dict()==after


def test_cancel_profile_plane_from_second_source_has_no_mutation(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    edge=window.project.profiles[b].segments[0].id;window.select_edge(sid,edge)
    before=copy.deepcopy(window.project.to_dict());seen=[]
    def reject(dialog):
        seen.append(dialog);return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ProfilePlacementDialog,'exec',reject)
    window.actions['profile_plane'].trigger()
    assert seen and window.project.to_dict()==before and not window._test_warnings


def test_delete_actual_loft_dialog_preserves_both_profiles_and_restores_by_undo(window,qtbot,monkeypatch):
    from archpapercraft.ui.author_editing import DeletePartDialog
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    before=copy.deepcopy(window.project.to_dict())
    impact=part_deletion_impact(window.project,pid)
    assert {r['id'] for r in impact['preserved_profiles']}=={a,b}
    def accept(dialog):dialog.accept();return QDialog.DialogCode.Accepted
    monkeypatch.setattr(DeletePartDialog,'exec',accept)
    window.actions['delete_part'].trigger()
    assert not window._test_warnings
    assert not window.project.surfaces and set(window.project.profiles)=={a,b}
    window.actions['undo'].trigger();assert window.project.to_dict()==before


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def test_binding_detached_exact_hashes_scale_source_changes_and_coverage(tmp_path):
    p=AuthorProject.new(scale=1)
    a=p.add_profile([[0,0],[10,0],[10,5]],closed=False)
    b=p.copy_profile(a,plane={'origin':[0,0,7],'u':[1,0,0],'v':[0,1,0]})
    pairs=[{'first_segment_id':x.id,'second_segment_id':y.id,'first_interval':[0,1],'second_interval':[0,1]} for x,y in zip(p.profiles[a].segments,p.profiles[b].segments)]
    sid=p.add_loft(a,b,correspondences=pairs);pid=p.part_for_surface(sid)
    planar=p.add_surface(p.add_profile([[0,0],[2,0],[2,2],[0,2]]))
    p.set_placement(pid,p.pages[0].id,30,30);p.set_placement(p.part_for_surface(planar),p.pages[0].id,70,70)
    snapshot=p.snapshot();record=snapshot['construction_checks']['lofts'][sid];binding=record['source_binding'];state=p.to_dict()
    assert snapshot['coverage']['expected_loft_surface_ids']==[sid]
    assert set(snapshot['coverage']['expected_surface_ids'])=={sid,planar}
    assert binding['profiles']==[state['profiles'][a],state['profiles'][b]]
    assert binding['surface']==state['surfaces'][sid] and binding['scale']==1
    intrinsic={'profiles':binding['profiles'],'params':binding['surface']['params'],'scale':binding['scale']}
    assert digest(intrinsic)==record['intrinsic_source_digest']
    assert digest({'intrinsic_source_digest':digest(intrinsic),'surface':binding['surface']})==record['source_digest']
    snapshot['construction_checks']['lofts'].clear()
    assert snapshot['coverage']['expected_loft_surface_ids']==[sid]
    binding['surface']['params']['correspondences'][0]['first_interval'][0]=.125
    binding['profiles'][1]['plane']['origin'][2]=999
    assert p.to_dict()==state
    path=tmp_path/'loft.apcraft';p.save(path);reopened=load_project(path)
    assert reopened.snapshot()['construction_checks']['lofts'][sid]['source_binding']==p.snapshot()['construction_checks']['lofts'][sid]['source_binding']
    delete_material_part(reopened,pid)
    assert set(reopened.profiles)>={a,b} and reopened.snapshot()['coverage']['expected_loft_surface_ids']==[]


def test_stale_accepted_host_update_cannot_overwrite_concurrent_document_change(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    before=copy.deepcopy(window.project.to_dict());depth=len(window.controller._undo)
    def execute(dialog):
        dialog.confirm_pairs.setChecked(True);assert dialog.request_preview()
        qtbot.waitUntil(lambda:dialog._running_job is None,timeout=30000)
        assert dialog.apply_button.isEnabled();dialog.accept()
        window.controller.execute('concurrent valid document change',lambda p:setattr(p,'name','Concurrent author name'))
        return dialog.result()
    monkeypatch.setattr(LoftProfilesDialog,'exec',execute)
    window.actions['edit_loft'].trigger()
    assert window._test_warnings
    assert window.project.name=='Concurrent author name'
    assert window.project.to_dict()['surfaces']==before['surfaces']
    assert window.project.to_dict()['parts']==before['parts']
    assert len(window.controller._undo)==depth+1


def test_loft_edge_guidance_does_not_offer_disabled_planar_join(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    window.select_edge(sid,window.project.profiles[b].segments[0].id)
    assert not window.actions['attach_inside'].isEnabled() and not window.actions['glue_region'].isEnabled()
    assert '\u0070\u0159ipojit' not in window.hint.text(),window.hint.text()


def test_focused_actual_numeric_44_to_40_commits_after_tab_on_existing_loft(window,qtbot,monkeypatch):
    from PySide6.QtWidgets import QApplication
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    window.controller.execute('existing moved layout',lambda p:p.set_placement(pid,p.pages[0].id,44,60,17))
    window.select_surface(sid)
    for header,box in window.sections.values():
        if not box.isVisible():qtbot.mouseClick(header,Qt.MouseButton.LeftButton)
    window.activateWindow();window.raise_();window.paper_x.setFocus();qtbot.wait(30)
    focus=QApplication.focusWidget()
    assert QApplication.activeWindow() is window and (focus is window.paper_x or window.paper_x.isAncestorOf(focus))
    assert window.paper_x.value()==44
    qtbot.keyClick(window.paper_x,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(window.paper_x,'40')
    assert '40' in window.paper_x.text()
    qtbot.keyClick(window.paper_x,Qt.Key.Key_Tab)
    qtbot.waitUntil(lambda:window.project.placements[pid].x_mm==40,timeout=3000)
    assert window.paper_x.value()==40 and window.project.placements[pid].rotation_deg==17


def test_invalid_second_plane_remains_repairable_from_source_ui(window,qtbot,monkeypatch):
    a,b,sid,pid=create(window,qtbot,monkeypatch)
    window.controller.execute('place',lambda p:p.set_placement(pid,p.pages[0].id,42,53,27))
    before=copy.deepcopy(window.project.to_dict())
    window.select_edge(sid,window.project.profiles[b].segments[0].id)
    def change_angle(angle):
        def execute(dialog):
            dialog.fields['angle'].setValue(angle);dialog.accept();return dialog.result()
        monkeypatch.setattr(ProfilePlacementDialog,'exec',execute)
        window.actions['profile_plane'].trigger()
    change_angle(17)
    assert window.selected_profile==b and window.actions['profile_plane'].isEnabled()
    assert set(window.project.profiles)=={a,b} and set(window.project.surfaces)=={sid}
    assert window.project.surfaces[sid].params==before['surfaces'][sid]['params']
    assert window.project.to_dict()['parts'][pid]['frame']==before['parts'][pid]['frame']
    assert window.project.to_dict()['placements']==before['placements']

    assert window.project.loft_status(sid)['status']!='EXACT'
    change_angle(-17)
    window.actions['recompute'].trigger()
    assert window.project.loft_status(sid)['status']=='EXACT'
    assert set(window.project.profiles)=={a,b} and window.selected_profile==b
    assert window.project.to_dict()['placements']==before['placements']


def test_source_revision_and_current_plane_change_digest_and_detached_records():
    p=AuthorProject.new(scale=1)
    a=p.add_profile([[0,0],[12,0]],closed=False)
    b=p.copy_profile(a,plane={'origin':[0,0,5],'u':[1,0,0],'v':[0,1,0]})
    pair={'first_segment_id':p.profiles[a].segments[0].id,'second_segment_id':p.profiles[b].segments[0].id,'first_interval':[0,1],'second_interval':[0,1]}
    sid=p.add_loft(a,b,correspondences=[pair]);pid=p.part_for_surface(sid)
    p.set_placement(pid,p.pages[0].id,30,30)
    first=p.snapshot()['construction_checks']['lofts'][sid]
    p.set_profile_plane(b,origin=[0,0,9],u=[1,0,0],v=[0,1,0])
    current=p.loft_status(sid)
    assert current['paper_stale']
    assert current['source_binding']['profiles'][1]['plane']['origin']==[0,0,9]
    assert current['source_revisions'][b]==p.profiles[b].revision
    assert current['source_binding']['profiles'][1]['revision']==p.profiles[b].revision
    assert current['intrinsic_source_digest']!=first['intrinsic_source_digest']
    assert first['source_binding']['profiles'][1]['plane']['origin']==[0,0,5]
    p.recompute();result=p.snapshot()['construction_checks']['lofts'][sid]
    source=result['source_binding']
    assert digest({'profiles':source['profiles'],'params':source['surface']['params'],'scale':source['scale']})==result['intrinsic_source_digest']
