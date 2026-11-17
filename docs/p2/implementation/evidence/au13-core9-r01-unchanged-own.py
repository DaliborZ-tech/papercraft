"""Independent application provenance checks, pinned to the reviewed worktree."""
import copy
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring import project as project_module
from archpapercraft.authoring.project import ProjectFormatError

ROOT = Path(__file__).resolve().parents[4]
PIN = '6064f222dfa87f6c46837f11ed9da5c04a6523cb'
assert Path(project_module.__file__).resolve() == ROOT/'src/archpapercraft/authoring/project.py'
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip() == PIN
for name in ('project.py','profile_subdivision.py','loft_surface.py','model.py','profile_source_views.py'):
    path = 'src/archpapercraft/authoring/'+name
    expected = subprocess.check_output(['git','-C',str(ROOT),'show',PIN+':'+path])
    assert (ROOT/path).read_bytes().replace(b'\r\n',b'\n') == expected.replace(b'\r\n',b'\n')

def make_profile(p, kind, height=0, closed=False):
    a,b = ([20,0],[-20,0]) if kind=='arc' else ([0,0],[4,0])
    data = {'center':[0,0],'sweep_deg':180} if kind=='arc' else {'control1':[0,4],'control2':[4,4]}
    segments = [dict(kind=kind,start=a,end=b,data=data)]
    if closed:
        segments.append(dict(kind='line',start=b,end=a,data={}))
    return p.add_profile(segments=segments,closed=closed,
        plane=dict(origin=[0,0,height],u=[1,0,0],v=[0,1,0]))

@pytest.mark.parametrize('kind',['arc','cubic'])
@pytest.mark.parametrize('retired',['root','left','right'])
def test_retired_piece_cannot_be_resurrected_as_active_qualified_descriptor(kind,retired,tmp_path):
    p=AuthorProject.new(scale=.1)
    pid=make_profile(p,kind)
    root=p.profiles[pid].segments[0].id
    cut=p.split_profile_segment(pid,root,Q(1,3))
    merged=p.merge_profile_segments(pid,cut['segment_ids'])
    raw=p.to_dict()
    bad_id={'root':root,'left':cut['segment_ids'][0],'right':cut['segment_ids'][1]}[retired]
    segment=raw['profiles'][pid]['segments'][0]
    segment['id']=bad_id
    segment['source_reference']['piece_id']=bad_id
    witness=tmp_path/'retired-active-descriptor.apcraft'
    witness.write_text(json.dumps(raw,indent=2),encoding='utf-8')
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(raw)

@pytest.mark.parametrize('kind',['arc','cubic'])
def test_drop_history_with_qualified_active_pieces_is_rejected(kind):
    p=AuthorProject.new(scale=.1); pid=make_profile(p,kind)
    p.split_profile_segment(pid,p.profiles[pid].segments[0].id,Q(1,3))
    raw=p.to_dict(); raw['profile_subdivisions']={}
    with pytest.raises(ProjectFormatError): AuthorProject.from_dict(raw)

@pytest.mark.parametrize('field',['profile_id','history_id','piece_id','generation','parameter_interval'])
def test_active_descriptor_identity_must_equal_actual_history(field):
    p=AuthorProject.new(scale=.1); pid=make_profile(p,'cubic')
    p.split_profile_segment(pid,p.profiles[pid].segments[0].id,Q(2,7))
    raw=p.to_dict(); ref=raw['profiles'][pid]['segments'][0]['source_reference']
    ref[field] = p.project_id if field.endswith('_id') else 7 if field=='generation' else ['0','1/3']
    with pytest.raises(ProjectFormatError): AuthorProject.from_dict(raw)

def test_cubic_nonuniform_nested_distance_is_original_polynomial_not_child_proxy(tmp_path):
    p=AuthorProject.new(scale=.1); pid=make_profile(p,'cubic')
    root=p.profiles[pid].segments[0].id
    first=p.split_profile_segment(pid,root,Q(2,7))
    second=p.split_profile_segment(pid,first['segment_ids'][1],Q(3,5))
    # Independent arc length for this particular cubic: L(u)=8u^3-12u^2+12u.
    L=lambda u: 8*u**3-12*u**2+12*u
    cuts=[Q(0),Q(2,7),Q(5,7),Q(1)]
    assert len(p.profiles[pid].segments)==3
    for s,a,b in zip(p.profiles[pid].segments,cuts,cuts[1:]):
        bound=p.profile_segment_length(pid,s.id,tolerance_model_mm=1e-5)
        expected=float(L(b)-L(a))
        assert bound['lower'] <= expected <= bound['upper']
        distance=float((L(b)-L(a))*Q(2,5))
        inverse=p.profile_segment_parameter_at_length(pid,s.id,distance,tolerance_model_mm=1e-4)
        global_u=a+(b-a)*inverse['parameter']
        assert abs(float(L(global_u)-L(a))-distance) <= inverse['actual_error_bound_model_mm']
    p.save(tmp_path/'nested.apcraft')
    assert load_project(tmp_path/'nested.apcraft').to_dict()==p.to_dict()

@pytest.mark.parametrize('kind',['arc','cubic'])
def test_nonuniform_inverse_merge_preserves_original_loft_and_authored_layout(kind,tmp_path):
    p=AuthorProject.new(scale=.1); a,b=make_profile(p,kind),make_profile(p,kind,10)
    x,y=p.profiles[a].segments[0].id,p.profiles[b].segments[0].id
    sid=p.add_loft(a,b,correspondences=[dict(first_segment_id=x,second_segment_id=y)])
    part=p.part_for_surface(sid)
    p.set_placement(part,p.pages[0].id,67,83,30,position_locked=True,rotation_locked=True)
    before=copy.deepcopy(p.parts[part]); layout=copy.deepcopy(p.placements[part]); params=copy.deepcopy(p.surfaces[sid].params)
    first=p.split_profile_segment(a,x,Q(2,7))
    second=p.split_profile_segment(a,first['segment_ids'][1],Q(3,5))
    p.recompute()
    assert p.loft_status(sid)['status']=='EXACT' and p.parts[part].paths==before.paths
    assert p.parts[part].frame==before.frame and p.placements[part]==layout
    p.merge_profile_segments(a,second['segment_ids'])
    p.merge_profile_segments(a,[s.id for s in p.profiles[a].segments]); p.recompute()
    assert p.parts[part].paths==before.paths and p.surfaces[sid].params==params
    p.save(tmp_path/'loft.apcraft'); assert load_project(tmp_path/'loft.apcraft').to_dict()==p.to_dict()
