"""Own UI oracles with real detached D computation; not a native or novice proof."""
import copy
import threading
from fractions import Fraction

import pytest
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from archpapercraft.authoring import AuthorProject
from archpapercraft.application.author_controller import AuthorController
from archpapercraft.ui.author_segmentation import SegmentedVariantDialog, _digest, _state
from archpapercraft.ui.author_manual_layout import ManualGridDialog
from archpapercraft.ui.author_window import AuthorMainWindow


@pytest.fixture(scope='module')
def fixture_state():
    # Exact independent target S(u,v)=(16u,8uv,12v), not the author's 40mm fixture.
    p=AuthorProject.new(scale=1)
    a=p.add_profile([[0,0],[16,0]],closed=False)
    b=p.add_profile([[0,0],[16,8]],closed=False,
        plane=dict(origin=[0,0,12],u=[1,0,0],v=[0,1,0]))
    s=p.add_loft(a,b,correspondences=[dict(first_segment_id=p.profiles[a].segments[0].id,
        second_segment_id=p.profiles[b].segments[0].id,first_interval=[0,1],second_interval=[0,1])])
    preview=p.preview_segmented_variant(s,max_deviation_mm=.26)
    assert preview['status']=='APPROXIMATE'
    assert preview['certificate']['math']['counts']['triangles']==16
    return p.to_dict(),s,preview


def project(fixture_state):
    state,s,_=fixture_state
    return AuthorProject.from_dict(copy.deepcopy(state)),s


def widget(qtbot,fixture_state):
    p,s=project(fixture_state)
    w=SegmentedVariantDialog(p,s);qtbot.addWidget(w);w.show()
    w.deviation.setValue(.26)
    return w,p,s


def compute(qtbot,w):
    qtbot.mouseClick(w.preview_button,Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda:w._running is None,timeout=30000)
    assert w._preview is not None,w.feedback.text()


def generation(fixture_state):
    p,s=project(fixture_state)
    v=p.add_segmented_variant(s,max_deviation_mm=.26,
        preview_digest=fixture_state[2]['preview_digest'])
    return p,s,v


def test_analytic_target_real_preview_then_changed_live_source_before_apply(qtbot,fixture_state):
    w,p,s=widget(qtbot,fixture_state);before=p.to_dict();compute(qtbot,w)
    preview=w._preview
    assert len(preview['preview_geometry']['triangles'])==16
    bound=Fraction(preview['certificate']['material_frame']['max_target_to_material_deviation_paper_mm_exact'])
    assert Fraction(1,4)<=bound<=Fraction('.26')
    # Actual generated display points stay on the hand-derived bilinear target.
    for x,y,z in preview['preview_geometry']['vertices']:
        assert abs(y-x*z/24)<1e-11
    assert p.to_dict()==before
    qtbot.mouseClick(w.confirm,Qt.MouseButton.LeftButton);w.accept()
    assert w.result()==QDialog.DialogCode.Accepted
    p.set_transform(s,[1,0,0],[0,0,0]);changed=p.to_dict()
    with pytest.raises(ValueError,match='změnil'):w.apply(p)
    assert p.to_dict()==changed


@pytest.mark.parametrize('field,value',[('target_surface_id','wrong'),('status','EXACT'),
    ('can_confirm',False),('parameters',{}),('preview_digest','')])
def test_wrong_response_cannot_be_confirmed(qtbot,fixture_state,field,value):
    w,p,_=widget(qtbot,fixture_state);compute(qtbot,w)
    valid=copy.deepcopy(w._preview);request=copy.deepcopy(w._request)
    valid[field]=value;source=p.world_geometry(w.target_id);w._invalidate()
    try:w._publish(valid,source,request)
    except ValueError:pass
    assert w._preview is None
    w.confirm.setChecked(True)
    assert not w.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert not p.segmented_variants


@pytest.mark.parametrize('bad', ['excess_bound','negative_length','invalid_angle','bad_vertex','bad_face','wrong_count'])
def test_invalid_limits_and_display_geometry_cannot_be_confirmed(qtbot,fixture_state,bad):
    w,p,_=widget(qtbot,fixture_state);compute(qtbot,w)
    valid=copy.deepcopy(w._preview);request=copy.deepcopy(w._request)
    metrics=valid['certificate']['material_frame']
    if bad=='excess_bound':metrics['max_target_to_material_deviation_paper_mm_exact']='27/100'
    elif bad=='negative_length':metrics['max_source_edge_to_flat_length_difference_bound_paper_mm_exact']='-1'
    elif bad=='invalid_angle':metrics['max_material_normal_angle_deg_exact']='181'
    elif bad=='bad_vertex':valid['preview_geometry']['vertices'][0][0]=float('nan')
    elif bad=='bad_face':valid['preview_geometry']['triangles'][0][0]=999999
    elif bad=='wrong_count':valid['preview_geometry']['triangles'].pop()
    w._invalidate()
    with pytest.raises((ValueError,TypeError)):w._publish(valid,p.world_geometry(w.target_id),request)
    assert w._preview is None and not p.segmented_variants


def test_async_latest_only_timer_keeps_running_close_ignores_detached_result(qtbot,fixture_state,monkeypatch):
    # Delay only to expose lifecycle ordering; every result is the real domain API result.
    entered,release=threading.Event(),threading.Event();calls=[]
    original=AuthorProject.preview_segmented_variant
    def delayed(p,s,**params):
        calls.append((threading.get_ident(),params['max_deviation_mm']))
        if len(calls)==1:entered.set();assert release.wait(10)
        return original(p,s,**params)
    monkeypatch.setattr(AuthorProject,'preview_segmented_variant',delayed)
    w,p,_=widget(qtbot,fixture_state);before=p.to_dict();ticks=[]
    timer=QTimer(w);timer.timeout.connect(lambda:ticks.append(1));timer.start(10)
    w.request_preview();qtbot.waitUntil(entered.is_set)
    w.deviation.setValue(.5);w.request_preview()
    w.deviation.setValue(.26);w.request_preview()
    qtbot.waitUntil(lambda:len(ticks)>=3)
    assert p.to_dict()==before and len(calls)==1
    release.set();qtbot.waitUntil(lambda:w._running is None and w._preview is not None,timeout=30000)
    assert [c[1] for c in calls]==[.26,.26]
    assert all(t!=threading.get_ident() for t,_ in calls)
    w.request_preview();w.close()
    qtbot.waitUntil(lambda:w._running is None,timeout=30000)
    assert w._accepted is None and w._preview is None
    assert p.to_dict()==before and not p.segmented_variants


def test_preview_source_race_while_worker_runs_discards_result(qtbot,fixture_state,monkeypatch):
    entered,release=threading.Event(),threading.Event();original=AuthorProject.preview_segmented_variant
    def delayed(p,s,**params):
        entered.set();assert release.wait(10);return original(p,s,**params)
    monkeypatch.setattr(AuthorProject,'preview_segmented_variant',delayed)
    w,p,s=widget(qtbot,fixture_state);w.request_preview();qtbot.waitUntil(entered.is_set)
    p.set_transform(s,[1,0,0],[0,0,0]);changed=p.to_dict();release.set()
    qtbot.waitUntil(lambda:w._running is None,timeout=30000)
    assert w._preview is None and 'změnil' in w.feedback.text()
    assert p.to_dict()==changed


def test_grid_late_rotation_lock_then_c05_then_atomic_undo(qtbot,fixture_state):
    p,_,v=generation(fixture_state);ids=[r['part_id'] for r in p.segmented_variants[v].triangle_bindings]
    p.add_page();p.set_placement(ids[1],rotation_deg=27,rotation_locked=True)
    before=p.to_dict();w=ManualGridDialog(p,ids);qtbot.addWidget(w);w.show()
    for i in (0,1):w.parts.item(i).setSelected(True)
    w.page.setCurrentIndex(1);w.rotate.setChecked(True);w.angle.setValue(12);w.preview()
    assert w._preview_updates is None and 'zamčený' in w.feedback.text() and p.to_dict()==before
    w.rotate.setChecked(False);w.preview();assert w._preview_updates
    w.x.lineEdit().setFocus();w.x.lineEdit().selectAll();qtbot.keyClicks(w.x.lineEdit(),'44')
    w.accept();assert w.result()!=QDialog.DialogCode.Accepted and w._preview_updates is None
    w.preview();w.accept();assert w.result()==QDialog.DialogCode.Accepted
    c=AuthorController();c.project=p;c.execute('grid',w.apply)
    assert p.placements[ids[0]].x_mm==44 and p.placements[ids[1]].rotation_deg==27
    assert all(p.to_dict()['placements'][i]==before['placements'][i] for i in ids[2:])
    c.undo();assert c.project.to_dict()==before
    c.redo();assert c.project.placements[ids[0]].x_mm==44


def test_grid_confirm_then_source_changed_fails_before_any_placement(qtbot,fixture_state):
    p,_,v=generation(fixture_state);ids=[r['part_id'] for r in p.segmented_variants[v].triangle_bindings]
    w=ManualGridDialog(p,ids);qtbot.addWidget(w)
    w.parts.item(0).setSelected(True);w.page.setCurrentIndex(0);w.preview();w.accept()
    p.add_page();before=p.to_dict()
    with pytest.raises(ValueError,match='změnil'):w.apply(p)
    assert p.to_dict()==before


def test_host_inactive_generation_reference_safety_and_old_plain_panel(qtbot,fixture_state,tmp_path):
    p,s,v=generation(fixture_state)
    # .5 exactly exhausts the raw geometric bound before floating-frame reserve.
    preview=p.preview_segmented_variant(s,max_deviation_mm=.51)
    assert preview['can_confirm'],preview['message']
    new=p.update_segmented_variant(v,max_deviation_mm=.51,preview_digest=preview['preview_digest'])
    old=p.segmented_variants[v].triangle_bindings;current=p.segmented_variants[new].triangle_bindings
    w=AuthorMainWindow(settings=QSettings(str(tmp_path/'ui.ini'),QSettings.Format.IniFormat))
    qtbot.addWidget(w);w.controller.project=p;w.refresh()
    w.select_surface(old[0]['surface_id'])
    assert w.selected_generation==v and w.select_generation_button.isEnabled()
    assert w.viewport.selected_surfaces=={old[0]['surface_id']}
    assert set(w.paper.part_items)=={r['part_id'] for r in current}
    assert not w.paper_x.isEnabled() and not w.page_choice.isEnabled()
    before=_digest(_state(p));w.clear_selection();assert _digest(_state(p))==before
    assert set(w.viewport.meshes)=={r['surface_id'] for r in current}
    w.select_surface(s);w.restore_target()
    assert set(w.paper.part_items)=={p.surfaces[s].part_id}
    w.controller.undo();assert p is not w.project # Controller replaces state, host follows it.
    assert set(w.paper.part_items)=={r['part_id'] for r in current}
    w.controller._saved_digest=w.controller.digest(w.project.to_dict())


def test_generation_combo_cannot_claim_a_different_generation_than_selected_child(qtbot,fixture_state,tmp_path):
    p,s,v=generation(fixture_state)
    preview=p.preview_segmented_variant(s,max_deviation_mm=.51)
    new=p.update_segmented_variant(v,max_deviation_mm=.51,preview_digest=preview['preview_digest'])
    w=AuthorMainWindow(settings=QSettings(str(tmp_path/'select.ini'),QSettings.Format.IniFormat))
    qtbot.addWidget(w);w.controller.project=p;w.refresh()
    old_sid=p.segmented_variants[v].triangle_bindings[0]['surface_id']
    w.select_surface(old_sid)
    assert w.selected_generation==v
    before=p.to_dict()
    w.generation_choice.setCurrentIndex(w.generation_choice.findData(new))
    w.controller._saved_digest=w.controller.digest(w.project.to_dict())
    assert w.selected_generation==new and p.to_dict()==before
    owning=next((variant.id for variant in p.segmented_variants.values()
        if any(row['surface_id']==w.selected_surface for row in variant.triangle_bindings)),None)
    # Selecting a generation may show its target or a member, but cannot retain a
    # highlighted child from another generation while claiming the new one.
    assert owning in (None,w.selected_generation),dict(
        selected_generation=w.selected_generation,selected_surface=w.selected_surface,
        actual_owning_generation=owning,viewport_ids=list(w.viewport.meshes),
        combo=w.generation_choice.currentText(),feedback=w.segmentation_status.text())
    w.controller._saved_digest=w.controller.digest(w.project.to_dict())
