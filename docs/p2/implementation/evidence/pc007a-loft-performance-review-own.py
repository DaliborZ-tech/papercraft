"""Independent actual-source/cache/compaction tests; no native desktop proof."""
import copy
from dataclasses import asdict
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import random

import numpy as np
import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring import loft_surface as actual
from archpapercraft.authoring.paper import part_input

assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())
HERE=Path(__file__).parent
REAL803=Path(r'C:\Users\dalib\projects\papercraft-loft-integration\docs\p2\implementation\evidence\pc007a-loft-Bezier-desktop-23ce202-run01\loft-Bezier\loft-Bezier.apcraft')


def model():
    p=AuthorProject.new(scale=1);a=p.add_profile([[0,0],[8,0],[8,4],[12,4]],closed=False)
    b=p.copy_profile(a,plane={'origin':[0,0,5],'u':[1,0,0],'v':[0,1,0]})
    s=p.add_loft(a,b,correspondences=[dict(first_segment_id=x.id,second_segment_id=y.id) for x,y in zip(p.profiles[a].segments,p.profiles[b].segments)])
    pid=p.part_for_surface(s);p.set_placement(pid,p.pages[0].id,40,40,0,position_locked=True,rotation_locked=True)
    return p,s,pid,a,b


def test_actual_imports_and_finite_cache_limits():
    out={}
    for name in ['loft_surface','paper','project']:
        m=__import__('archpapercraft.authoring.'+name,fromlist=['x']);f=Path(m.__file__).resolve();assert f.is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve());out[name]={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    for cache in [actual._world_mesh_json,actual._loft_material_json]:assert cache.cache_parameters()['maxsize']==8
    (HERE/('pc007a-loft-performance-review-imports-'+os.environ.get('PC_REVIEW_LABEL','source')+'.json')).write_text(json.dumps(out,indent=2),encoding='utf8')


@pytest.mark.parametrize('kind',['world','analysis','status','material'])
def test_public_nested_values_are_detached_from_source_cache_and_project(kind):
    p,s,pid,a,b=model();before=p.to_dict()
    if kind=='world':
        value=p.world_geometry(s);expected=copy.deepcopy(value);value['boundary'][0]['source']['role']='poison';value['vertex_sources'][0]['v']=123;value['vertices'][0][0]=123
        assert p.world_geometry(s)==expected
    elif kind=='analysis':
        value=actual.analysis(p,p.surfaces[s]);expected=copy.deepcopy(value);value['native']['patches'][0]['first']['segments'][0]['source']['profile_id']='poison';value['patches'][0]['id']='poison';value['area']['source_intrinsic']['coverage']['first_profile_id']='poison'
        assert actual.analysis(p,p.surfaces[s])==expected
    elif kind=='status':
        value=p.loft_status(s);expected=copy.deepcopy(value);value['source_binding']['profiles'][0]['vertices'][0]['point'][0]=123;value['representation']['position_error_bound_paper_mm']=123;value['crease_geometry'][0]['role']='poison'
        assert p.loft_status(s)==expected
    else:
        built=actual.build_loft_part(p,p.parts[pid]);original=copy.deepcopy(built);built.lineage.append('poison');built.surface_ids.append('poison');built.frame.anchor_vertex_id='poison';built.edges[0]['start'][0]=123;built.labels[0]['text']='poison';built.paths['CUT'][0]['commands'][0][1]=123
        assert actual.build_loft_part(p,p.parts[pid])==original
    assert p.to_dict()==before


@pytest.mark.parametrize('which',[0,1])
def test_actual_profile_plane_data_changes_key_without_revision_shortcut(which):
    p,s,pid,a,b=model();prior=p.world_geometry(s);old_digest=p.loft_status(s)['source_digest'];profile=p.profiles[(a,b)[which]];revision=profile.revision
    profile.plane.origin[0]+=2
    mesh=p.world_geometry(s);assert profile.revision==revision and p.loft_status(s)['source_digest']!=old_digest
    assert mesh!=prior
    for xyz,meta in zip(mesh['vertices'],mesh['vertex_sources']):
        x=2*(1-meta['v']) if which==0 else 2*meta['v'];segment=p.profiles[a].segment(meta['first_segment_id']);v0=p.profiles[a].vertex(segment.start_vertex_id).point;v1=p.profiles[a].vertex(segment.end_vertex_id).point;u=meta['first_parameter']
        np.testing.assert_allclose(xyz,[(1-u)*v0[0]+u*v1[0]+x,(1-u)*v0[1]+u*v1[1],5*meta['v']],atol=1e-12,rtol=0)
    assert p.loft_status(s)['paper_stale']
    with pytest.raises(ValidationError):p.snapshot()


def test_curve_controls_change_without_revision_changes_actual_numeric_source():
    p=AuthorProject.new(scale=1);a=p.add_profile(segments=[dict(kind='cubic',start=[0,0],end=[6,0],data={'control1':[1,0],'control2':[3,0]})],closed=False);b=p.copy_profile(a,plane={'origin':[0,0,5],'u':[1,0,0],'v':[0,1,0]});s=p.add_loft(a,b,correspondences=[dict(first_segment_id=p.profiles[a].segments[0].id,second_segment_id=p.profiles[b].segments[0].id)]);p.world_geometry(s);old=p.loft_status(s)['source_digest'];rev=p.profiles[a].revision
    # Both sources remain exact matching nonuniform collinear cubics.
    for profile in (p.profiles[a],p.profiles[b]):profile.segments[0].data['control1']=[2,0]
    mesh=p.world_geometry(s);assert p.profiles[a].revision==rev and p.loft_status(s)['source_digest']!=old
    for xyz,m in zip(mesh['vertices'],mesh['vertex_sources']):
        u=m['first_parameter'];x=6*(1-u)**2*u+9*(1-u)*u*u+6*u**3
        np.testing.assert_allclose(xyz,[x,0,5*m['v']],atol=1e-12,rtol=0)


@pytest.mark.parametrize('mutation',['position','rotation','parent','scale'])
def test_actual_pose_and_scale_keys_recompute_world_certificate(mutation,monkeypatch):
    p,s,pid,a,b=model();actual._world_mesh_json.cache_clear();calls=[];build=actual._build_world_mesh
    def count(*args):calls.append(1);return build(*args)
    monkeypatch.setattr(actual,'_build_world_mesh',count);p.world_geometry(s);revision=p.surfaces[s].revision;old=p.loft_status(s)['source_digest']
    if mutation=='position':p.surfaces[s].position_mm[:]=[3,4,5];expected=[3,4,5]
    elif mutation=='rotation':p.surfaces[s].rotation_deg[:]=[0,0,90];expected=[0,0,0]
    elif mutation=='parent':p.surfaces[s].parent_transforms.append([[1,0,0,7],[0,1,0,8],[0,0,1,9],[0,0,0,1]]);expected=[7,8,9]
    else:p.scale=.5;expected=[0,0,0]
    mesh=p.world_geometry(s);np.testing.assert_allclose(mesh['vertices'][0],expected,atol=1e-12,rtol=0);assert len(calls)==2 and p.surfaces[s].revision==revision and p.loft_status(s)['source_digest']!=old
    if mutation=='rotation':
        for xyz,m in zip(mesh['vertices'],mesh['vertex_sources']):
            seg=p.profiles[a].segment(m['first_segment_id']);p0=p.profiles[a].vertex(seg.start_vertex_id).point;p1=p.profiles[a].vertex(seg.end_vertex_id).point;u=m['first_parameter'];x,y=[(1-u)*q+u*r for q,r in zip(p0,p1)];np.testing.assert_allclose(xyz,[-y,x,5*m['v']],atol=1e-12,rtol=0)


def test_invalid_actual_pose_cannot_reuse_previous_world_success():
    p,s,pid,a,b=model();p.world_geometry(s);p.surfaces[s].parent_transforms.append([[2,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
    with pytest.raises(ValidationError):p.validate()
    with pytest.raises(ValidationError):p.world_geometry(s)


@pytest.mark.parametrize('mutation',['frame','side','name'])
def test_material_cache_keys_anchor_side_and_authored_name(mutation,monkeypatch):
    p,s,pid,a,b=model();part=p.parts[pid];actual._loft_material_json.cache_clear();calls=[];build=actual._build_loft_material_geometry
    def count(*args):calls.append(1);return build(*args)
    monkeypatch.setattr(actual,'_build_loft_material_geometry',count);first=actual.build_loft_part(p,part);actual.build_loft_part(p,part);assert len(calls)==1
    if mutation=='frame':part.frame.anchor_vertex_id=p.profiles[a].vertices[1].id
    elif mutation=='side':part.front_side='inside'
    else:part.name='Vlastni dil'
    second=actual.build_loft_part(p,part);assert len(calls)==2
    if mutation=='frame':assert first.polygons!=second.polygons
    elif mutation=='side':assert first.paths['FOLD_MOUNTAIN']==second.paths['FOLD_VALLEY'] and first.paths['FOLD_VALLEY']==second.paths['FOLD_MOUNTAIN']
    else:assert second.labels[0]['text']=='Vlastni dil'


@pytest.mark.parametrize('field',['paths','edges','polygons','labels'])
def test_every_actual_payload_is_compared_even_after_warm_validation(field):
    p,s,pid,a,b=model();assert not p.validate_layout();part=p.parts[pid]
    if field=='paths':
        for c in part.paths['CUT'][0]['commands']:
            for i in range(1,len(c),2):c[i]+=.25
    elif field=='edges':part.edges[0]['start'][0]+=.25
    elif field=='polygons':part.polygons[s][0][0][0]+=.25
    else:part.labels[0]['text']='Poison'
    assert any(i.code=='INVALID_CACHE' for i in p.validate_layout())
    with pytest.raises(ValidationError):p.snapshot()


def line(a,b,segment='s',profile='p'):
    return dict(kind='line',start=a,end=b,data={},source={'profile_id':profile,'segment_id':segment})


@pytest.mark.parametrize('seed',[3,17,151])
def test_exact_collinear_reduction_preserves_whole_monotone_locus(seed):
    rng=random.Random(seed);ts=sorted(set([0,64]+[rng.randrange(1,64) for i in range(30)]));pts=[[Q(3*t,8),Q(t,4)] for t in ts];segments=[line(a,b) for a,b in zip(pts,pts[1:])];before=copy.deepcopy(segments)
    commands=actual._commands(segments)
    assert commands==[['M',*pts[0]],['L',*pts[-1]],['Z']] and segments==before


@pytest.mark.parametrize('kind',['tiny_corner','backtracking','source_segment','source_profile','missing_source','cubic'])
def test_compaction_never_smooths_or_joins_unsupported_source_transitions(kind):
    first=line([0,0],[1,0]);second=line([1,0],[2,0])
    if kind=='tiny_corner':second['end'][1]=2**-60
    elif kind=='backtracking':first['end']=[2,0];second['start']=[2,0];second['end']=[1,0]
    elif kind=='source_segment':second['source']['segment_id']='different'
    elif kind=='source_profile':second['source']['profile_id']='different'
    elif kind=='missing_source':second['source']={}
    else:first.update(kind='cubic',data={'control1':[Q(1,3),0],'control2':[Q(2,3),0]})
    result=actual._commands([first,second]);assert len(result)==4 and result[1][0]==('C' if kind=='cubic' else 'L')


def test_real_saved_803_command_part_becomes_stale_until_explicit_recompute(tmp_path):
    raw=REAL803.read_bytes();p=load_project(REAL803);sid=next(s.id for s in p.surfaces.values() if s.kind=='ruled_loft');pid=p.part_for_surface(sid);before=p.to_dict();status=p.loft_status(sid)
    assert len(p.parts[pid].paths['CUT'][0]['commands'])==803
    assert status['paper_stale']
    with pytest.raises(ValidationError):p.snapshot()
    p.recompute();after=p.to_dict();assert len(p.parts[pid].paths['CUT'][0]['commands'])==5
    assert after['profiles']==before['profiles'] and after['placements']==before['placements'] and after['parts'][pid]['frame']==before['parts'][pid]['frame'] and after['parts'][pid]['id']==before['parts'][pid]['id']
    assert not p.validate_layout() and not p.loft_status(sid)['paper_stale'] and REAL803.read_bytes()==raw
    copied=tmp_path/'copy.apcraft';p.save(copied);assert load_project(copied).to_dict()==p.to_dict()


def test_compaction_keeps_detailed_source_provenance_and_writer_binding(tmp_path):
    p=load_project(REAL803);p.recompute();sid=next(s.id for s in p.surfaces.values() if s.kind=='ruled_loft');pid=p.part_for_surface(sid);report=actual.analysis(p,p.surfaces[sid]);native=report['native']['patches'][0]
    assert len(native['first']['segments'])>100 and len(native['second']['segments'])>100
    for side in ['first','second']:
        intervals=[item['source']['parameter_interval'] for item in native[side]['segments']]
        assert intervals[0][0]==0 and intervals[-1][1]==1 and all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
    # The separately approved 3f4 writer is not merged into this exact source.
    # Exercise its unchanged private API contract, not nonexistent full writer.
    snapshot=p.snapshot();binding=snapshot['construction_checks']['lofts'][sid]['source_binding']
    key=json.dumps({'profiles':binding['profiles'],'params':binding['surface']['params'],'scale':binding['scale']},sort_keys=True,allow_nan=False)
    bound=actual._bound_analysis(key,json.dumps(binding['surface'],sort_keys=True,allow_nan=False))
    rotation,origin=actual._local_frame(p,p.parts[pid],bound);commands=[]
    for c in bound['native_commands']:
        points=((np.asarray([c[i:i+2] for i in range(1,len(c),2)])-origin)@rotation.T).tolist() if c[0]!='Z' else []
        commands.append([c[0],*(x for pt in points for x in pt)])
    assert commands==p.parts[pid].paths['CUT'][0]['commands'] and len(commands)==5
    assert bound['feature_id']==sid and bound['area']['status']=='CERTIFIED'


def test_new_cache_contract_does_not_hide_current_equal_area_poison_after_reload():
    p,s,pid,a,b=model();before=p.to_dict();raw=copy.deepcopy(before)
    for c in raw['parts'][pid]['paths']['CUT'][0]['commands']:
        for i in range(1,len(c),2):c[i]+=.25
    loaded=AuthorProject.from_dict(raw)
    assert not loaded.loft_status(s)['paper_stale']
    assert [i.code for i in loaded.validate_layout()]==['INVALID_CACHE']
    with pytest.raises(ValidationError):loaded.snapshot()
    loaded.recompute();assert loaded.to_dict()==before


def test_shared_capability_contract_changes_digest_status_and_material_key(monkeypatch):
    p,s,pid,a,b=model();part=p.parts[pid];old_digest=part_input(p,part);calls=[];build=actual._build_loft_material_geometry
    def counted(*args):calls.append(1);return build(*args)
    monkeypatch.setattr(actual,'_build_loft_material_geometry',counted);actual._loft_material_json.cache_clear();actual.build_loft_part(p,part);assert len(calls)==1
    old=actual.LOFT_PAPER_CONTRACT;monkeypatch.setattr(actual,'LOFT_PAPER_CONTRACT',old+'_REVIEW_ONLY')
    assert part_input(p,part)!=old_digest
    status=p.loft_status(s);assert status['paper_stale'] and status['paper_contract']==old+'_REVIEW_ONLY'
    rebuilt=actual.build_loft_part(p,part);assert len(calls)==2 and rebuilt.input_digest!=old_digest
