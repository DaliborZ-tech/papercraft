"""Independent reviewer cases for exact component 60c7889; offscreen Qt only."""
import copy
import json

import pytest
from PySide6.QtWidgets import QDialog

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.editing import delete_material_part, rename_author_entities
from archpapercraft.ui.author_editing import DeletePartDialog, RenameDialog


def own_scene():
    p = AuthorProject.new(scale=1)
    ids = [p.add_surface(p.add_profile([[x, 0], [x+10, 0], [x+10, 10], [x, 10]]))
           for x in (0, 50, 100)]
    p.recompute()
    return p, ids


@pytest.mark.parametrize('action', ['rename', 'delete'])
def test_old_copy_protection_survives_undo_redo_failed_operation(tmp_path, action):
    p, ids = own_scene()
    old = p.to_dict()
    old['schema_version'] = 1
    old['writer_version'] = '0.3.0-experimental'
    old.pop('attachments')
    old.pop('next_attachment_number')
    source = tmp_path/'old.apcraft'
    source.write_text(json.dumps(old), encoding='utf8')
    original = source.read_bytes()
    c = AuthorController()
    c.open(source)
    assert c.copy_source_path == source
    pid = c.project.part_for_surface(ids[0])
    operation = (lambda m: rename_author_entities(m, part_id=pid, part_name='New own label')) if action == 'rename' else (lambda m: delete_material_part(m, pid))
    c.execute(action, operation)
    c.undo()
    c.redo()
    with pytest.raises(ValidationError):
        c.execute('Invalid', lambda m: delete_material_part(m, 'absent'))
    with pytest.raises(ValueError):
        c.save(source)
    assert source.read_bytes() == original
    target = tmp_path/'copy.apcraft'
    c.save(target)
    assert load_project(target).to_dict() == c.project.to_dict()


def test_remove_one_of_three_preserves_two_exact_snapshots_and_ordered_counters():
    p, ids = own_scene()
    before = p.to_dict()
    delete_material_part(p, p.part_for_surface(ids[1]))
    after = p.to_dict()
    for sid in (ids[0], ids[2]):
        pid = before['surfaces'][sid]['part_id']
        for key, identity in [('surfaces', sid), ('parts', pid), ('placements', pid)]:
            assert before[key][identity] == after[key][identity]
    for key in ['profiles', 'pages', 'next_part_number', 'next_joint_number', 'next_attachment_number']:
        assert before[key] == after[key]


def test_confirmed_delete_refuses_other_project_and_any_intervening_change(qtbot):
    p, ids = own_scene()
    dialog = DeletePartDialog(p, p.part_for_surface(ids[0]))
    qtbot.addWidget(dialog)
    dialog.accept()
    other = copy.deepcopy(p)
    other.project_id = AuthorProject.new().project_id
    for changed in (other, p):
        if changed is p:
            rename_author_entities(p, project_name='Changed after preview')
        before = changed.to_dict()
        with pytest.raises(ValidationError):
            dialog.apply(changed)
        assert changed.to_dict() == before


def test_confirmed_rename_refuses_another_project_and_deleted_target_atomically(qtbot):
    p, ids = own_scene()
    pid = p.part_for_surface(ids[0])
    dialog = RenameDialog(p, surface_id=ids[0], part_id=pid)
    qtbot.addWidget(dialog)
    dialog.project_name.setText('Also must not leak')
    dialog.surface_name.setText('Own renamed surface')
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    other = copy.deepcopy(p)
    other.project_id = AuthorProject.new().project_id
    with pytest.raises(ValidationError):
        dialog.apply(other)
    delete_material_part(p, pid)
    before = p.to_dict()
    with pytest.raises(ValidationError):
        dialog.apply(p)
    assert p.to_dict() == before


@pytest.mark.parametrize('bad', ['\t', '\r', '\x00', '\x1f', '\x7f', ' \n ', 0, [], {}])
def test_own_invalid_name_matrix_cannot_partially_rename(bad):
    p, ids = own_scene()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        rename_author_entities(p, project_name='No partial project rename', surface_id=ids[0], surface_name=bad)
    assert p.to_dict() == before


def test_own_richtext_like_names_roundtrip_without_html_interpretation(qtbot, tmp_path):
    p, ids = own_scene()
    label = '<b>& Own "wall" – Ž</b>'
    rename_author_entities(p, surface_id=ids[0], surface_name=label)
    dialog = DeletePartDialog(p, p.part_for_surface(ids[0]))
    qtbot.addWidget(dialog)
    assert label in dialog.details.toPlainText()
    target = tmp_path/'literal.apcraft'
    p.save(target)
    assert load_project(target).surfaces[ids[0]].name == label


def test_reproduce_minor_connectors_count_is_not_individual_tab_count(qtbot):
    p = AuthorProject.new(scale=1)
    pa = p.add_profile([[0, 0], [10, 0], [10, 10], [0, 10]])
    pb = p.add_profile([[10, 0], [20, 0], [20, 10], [10, 10]])
    a, b = p.add_surface(pa), p.add_surface(pb)
    joint = p.connect_edges(a, p.profiles[pa].segments[1].id, b, p.profiles[pb].segments[3].id)
    p.set_tab(joint, owner=a, width_mm=1)
    cid = p.joints[joint].connector_id
    p.set_connector(cid, count=4)
    dialog = DeletePartDialog(p, p.part_for_surface(a))
    qtbot.addWidget(dialog)
    # Demonstrates C-EDIT01, rather than granting a product behavior PASS.
    assert p.connectors[cid].count == 4
    assert len(dialog.impact['connectors']) == 1
    assert 'Odstraněné chlopně: 1.' in dialog.details.toPlainText()
