"""Independent transaction, old guard parity and truthfulness oracles."""
import copy
from collections import UserDict
from types import MappingProxyType

import pytest
from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject,ValidationError


def project():
    p=AuthorProject.new(scale=1);parts=[]
    for index in range(3):
        sid=p.add_surface(p.add_profile([[0,0],[6,0],[6,4],[0,4]]));parts.append(p.part_for_surface(sid))
    return p,parts


@pytest.mark.parametrize('bad',[
    {'page_id':False},{'x_mm':True},{'rotation_deg':float('nan')},{'y_mm':float('-inf')},
    {'page_id':'not-a-page'},{'position_locked':0},{'rotation_locked':1},
])
def test_single_guard_failure_and_batch_late_failure_match_without_partial_change(bad):
    p,ids=project();before=copy.deepcopy(p.to_dict())
    with pytest.raises(ValidationError) as single:p.set_placement(ids[1],**bad)
    assert p.to_dict()==before
    with pytest.raises(ValidationError) as batch:p.set_placements({ids[0]:{'x_mm':71.25},ids[1]:bad})
    assert str(single.value)==str(batch.value) and p.to_dict()==before


def test_locked_page_move_or_unlock_and_move_cannot_bypass_guard():
    p,ids=project();p.set_placement(ids[1],p.pages[0].id,20,30,17,position_locked=True,rotation_locked=True)
    before=copy.deepcopy(p.to_dict())
    for update in ({'page_id':None},{'position_locked':False,'page_id':None},{'rotation_locked':False,'rotation_deg':0}):
        with pytest.raises(ValidationError):p.set_placements({ids[0]:{'x_mm':99},ids[1]:update})
        assert p.to_dict()==before
    p.set_placements({ids[1]:{'position_locked':False}})
    assert not p.placements[ids[1]].position_locked and p.placements[ids[1]].rotation_locked
    p.set_placements({ids[1]:{'page_id':None,'x_mm':-13}})
    assert p.placements[ids[1]].page_id is None and p.placements[ids[1]].x_mm==-13


@pytest.mark.parametrize('mapping',[UserDict,MappingProxyType])
def test_nonplain_outer_and_inner_mappings_are_refused(mapping):
    p,ids=project();before=p.to_dict()
    with pytest.raises(ValidationError):p.set_placements(mapping({ids[0]:{'x_mm':1}}))
    assert p.to_dict()==before
    with pytest.raises(ValidationError):p.set_placements({ids[0]:{'x_mm':1},ids[1]:mapping({'y_mm':5})})
    assert p.to_dict()==before


def test_extra_fields_and_unknown_late_id_are_rollback_not_implicit_creation():
    p,ids=project();before=p.to_dict()
    for changes in ({ids[0]:{'x_mm':10},ids[1]:{'auto_pack':True}},{ids[0]:{'x_mm':10},'new-part':{'x_mm':20}}):
        with pytest.raises(ValidationError):p.set_placements(changes)
        assert p.to_dict()==before


def test_final_validation_failure_restores_all_updates_revision_and_private_state(monkeypatch):
    p,ids=project();before=p.to_dict();p._test_author_state={'values':[1]}
    def reject():
        p._test_author_state['values'].append(2)
        raise ValidationError('independent final domain constraint')
    monkeypatch.setattr(p,'validate',reject)
    with pytest.raises(ValidationError,match='independent final'):
        p.set_placements({ids[0]:{'x_mm':4},ids[1]:{'x_mm':8}})
    assert p.to_dict(validate=False)==before and p._test_author_state=={'values':[1]}


def test_batch_has_one_undo_and_failed_branch_retains_redo_and_input_is_not_mutated():
    p,ids=project();c=AuthorController();c.project=p;before=copy.deepcopy(p.to_dict())
    updates={ids[0]:{'page_id':p.pages[0].id,'x_mm':25.25,'y_mm':35,'rotation_deg':17},ids[1]:{'x_mm':-20,'rotation_locked':True}}
    source=copy.deepcopy(updates)
    c.execute('Explicit batch',lambda p:p.set_placements(updates));after=c.project.to_dict()
    assert len(c._undo)==1 and updates==source
    c.undo();assert c.project.to_dict()==before and c.can_redo
    with pytest.raises(ValidationError):c.execute('failed late',lambda p:p.set_placements({ids[0]:{'y_mm':66},ids[2]:{'rotation_locked':1}}))
    assert c.project.to_dict()==before and c.can_redo
    c.redo();assert c.project.to_dict()==after


def test_no_automatic_page_rotation_unlock_or_layout_repair_is_inferred():
    p,ids=project();before=p.to_dict();revision=p.revision
    p.set_placements({ids[0]:{'page_id':p.pages[0].id,'x_mm':-20,'y_mm':30,'rotation_deg':720},ids[1]:{}})
    assert p.revision==revision+1 and len(p.pages)==len(before['pages'])
    assert p.placements[ids[0]].x_mm==-20 and p.placements[ids[0]].rotation_deg==720
    assert p.to_dict()['placements'][ids[1]]==before['placements'][ids[1]]
    assert any(i.code=='PHYSICAL_OVERFLOW' and ids[0] in i.part_ids for i in p.validate_layout())


def test_noop_loaded_integer_coordinates_do_not_make_a_dirty_unrecorded_change():
    p,ids=project();data=p.to_dict()
    # Both int and float are valid persisted coordinates; preserve accepted raw precision.
    data['placements'][ids[0]].update(x_mm=1,y_mm=2,rotation_deg=3)
    p=AuthorProject.from_dict(data);c=AuthorController();c.project=p
    c._saved_digest=c.digest(p.to_dict());before=copy.deepcopy(p.to_dict());revision=p.revision
    c.execute('No-op explicit placement',lambda p:p.set_placements({ids[0]:{'x_mm':1,'y_mm':2,'rotation_deg':3}}))
    assert c.project.revision==revision and not c.can_undo
    assert not c.dirty and c.digest(c.project.to_dict())==c.digest(before)
