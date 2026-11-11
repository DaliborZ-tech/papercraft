"""Real Qt and public-domain fault oracles, never a native/novice claim."""
import copy,threading
import pytest
from PySide6.QtCore import Qt,QTimer
from test_circular_shell import circle
from test_curved_authoring_ui import source as _source_fixture,positive as _positive_fixture,make_dialog,unresolved,finish,restore
from test_workspace import window as _window_fixture
source=_source_fixture;positive=_positive_fixture;window=_window_fixture

def two_rims(window,source):
 p,owner,receiver=restore(source)
 a=p.add_curved_connector(owner,'first',receiver,receiver_side='inside',nominal_base_mm=.24,min_glue_area_mm2=1)
 top=p.add_surface(circle(p,10,30))
 b=p.add_curved_connector(owner,'second',top,receiver_side='outside',nominal_base_mm=.24,min_glue_area_mm2=1)
 window.controller.project=p;window.refresh();window.select_surface(owner)
 panel=window.curved_panel;panel.sets.setCurrentIndex(panel.sets.findData(a))
 return p,panel,a,b

def invalid_main_number(window,qtbot):
 field=window.vertex_x.lineEdit();field.setFocus();field.selectAll();qtbot.keyClick(field,Qt.Key.Key_Backspace)
 assert not window.vertex_x.hasAcceptableInput()

def test_failed_c05_set_switch_keeps_combo_and_selected_set_consistent(window,source,qtbot):
 p,panel,a,b=two_rims(window,source);before=p.to_dict(validate=False)
 invalid_main_number(window,qtbot);panel.sets.setCurrentIndex(panel.sets.findData(b))
 assert p.to_dict(validate=False)==before and panel.current_id==a
 assert panel.sets.currentData()==a,'Failed numeric preflight left combo on another set while commands still own old set'

def test_failed_c05_whole_set_toggle_restores_visible_authored_state(window,source,qtbot):
 p,panel,a,_=two_rims(window,source);assert p.curved_connectors[a].enabled
 invalid_main_number(window,qtbot);panel.set_enabled.setChecked(False)
 assert p.curved_connectors[a].enabled
 assert panel.set_enabled.isChecked(),'Visible checkbox disagrees with unchanged authored enabled state after rejected preflight'

def test_current_certified_c_guidance_does_not_call_its_existing_connection_unverified(window,positive):
 p,owner,_receiver=restore(positive[:3]);a=positive[3]
 window.controller.project=p;window.refresh();window.select_surface(owner)
 panel=window.curved_panel;panel.sets.setCurrentIndex(panel.sets.findData(a));window.update_guidance()
 assert p.curved_connector_status(a)['status']=='CERTIFIED_APPROXIMATE'
 assert 'zat\u00edm nem\u00e1 ov\u011b\u0159en\u00fd spoj' not in window.hint.text(),window.hint.text()

def test_queued_preview_cancel_discards_pending_and_running_without_live_mutation(qtbot,source):
 entered,release=threading.Event(),threading.Event();calls=[]
 def callback(clone,request):
  calls.append(request);clone.name='Only worker clone changed';entered.set()
  assert release.wait(5)
  return unresolved(clone,request)
 p,w=make_dialog(qtbot,source,callback);before=p.to_dict(validate=False)
 try:
  w.request_preview();qtbot.waitUntil(entered.is_set)
  w.fields['relief_mm'].setValue(.75);w.request_preview();assert w._pending is not None
  w.cancel_preview();assert w._pending is None and not w.apply_button.isEnabled()
 finally:release.set()
 finish(qtbot,w)
 assert len(calls)==1 and w._packet is None and p.to_dict(validate=False)==before

def test_late_public_command_fault_rolls_back_staged_paper_intent_and_all_new_slots(qtbot,source,monkeypatch):
 from archpapercraft.authoring import AuthorProject
 from archpapercraft.application.author_controller import AuthorController
 p,w=make_dialog(qtbot,source,unresolved);before=p.to_dict(validate=False)
 w.material_override=dict(p.material_profile,thickness_mm=.35)
 w.tab_enabled.setChecked(False);w.request_preview();finish(qtbot,w);w.retain.setChecked(True);w.accept()
 original=AuthorProject.set_curved_tab
 def fail_after_actual_tab(self,*args,**kwargs):
  original(self,*args,**kwargs)
  raise RuntimeError('Independent late command fault')
 monkeypatch.setattr(AuthorProject,'set_curved_tab',fail_after_actual_tab)
 c=AuthorController();c.project=p;depth=len(c._undo)
 with pytest.raises(RuntimeError,match='Independent late'):c.execute('Staged paper and intent',w.apply)
 assert c.project.to_dict(validate=False)==before and len(c._undo)==depth

def test_receiver_mismatch_in_real_preview_cannot_publish_certified_display(qtbot,source):
 from archpapercraft.ui.author_curved_connectors import _preview
 def callback(clone,request):
  packet=_preview(clone,request)
  assert packet['status']=='CERTIFIED_APPROXIMATE'
  packet['geometry']['receiver_surface_id']='wrong-owner-response'
  return packet
 p,w=make_dialog(qtbot,source,callback);before=p.to_dict(validate=False)
 w.request_preview();finish(qtbot,w)
 assert w._packet is None and not w.apply_button.isEnabled() and not w.paper_preview.scene().items()
 assert p.to_dict(validate=False)==before

def test_deleted_preview_owner_becomes_repairable_obsolete_state_not_timer_exception(qtbot,source):
 from archpapercraft.authoring.editing import delete_material_part
 p,w=make_dialog(qtbot,source,unresolved);w.timer.stop()
 owner=w.owner_id;delete_material_part(p,p.part_for_surface(owner));after=p.to_dict(validate=False)
 try:
  w._source_changed()
  assert w._packet is None and not w.apply_button.isEnabled()
  assert p.to_dict(validate=False)==after
 finally:w.reject()

@pytest.mark.parametrize('reason',['outside_count','whole_set_disabled'])
def test_slot_toggle_label_matches_authored_override_and_does_not_change_print_eligibility(window,positive,qtbot,reason):
 p,owner,_receiver=restore(positive[:3]);cid=positive[3];record=p.curved_connectors[cid]
 index=10 if reason=='outside_count' else 2;slot=record.slot_ids[index]
 if reason=='outside_count':p.update_curved_connector(cid,count=8)
 else:p.update_curved_connector(cid,enabled=False)
 window.controller.project=p;window.refresh();window.select_surface(owner)
 panel=window.curved_panel;panel.sets.setCurrentIndex(panel.sets.findData(cid));panel.tabs.setCurrentIndex(panel.tabs.findData(slot))
 count,enabled=record.parameters['count'],record.enabled
 if not panel.toggle.isEnabled():return
 text=panel.toggle.text();assert text.startswith(('Zapnout','Vypnout'))
 requested_enabled=text.startswith('Zapnout')
 panel.toggle.click()
 actual=p.curved_connectors[cid]
 assert actual.parameters['count']==count and actual.enabled==enabled
 assert actual.tab_overrides.get(slot,{}).get('enabled',True)==requested_enabled,(text,actual.tab_overrides)
