"""Independent V4 allocation limits and actual saved B1 replay; no desktop."""
import copy
from decimal import Decimal,localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

import pytest

from archpapercraft.authoring import AuthorProject,ValidationError,load_project
from archpapercraft.authoring import loft_curve_compaction as actual,loft_surface
from archpapercraft.authoring.loft_curve_compaction import coalesce_native_loft_boundaries

HERE=Path(__file__).parent
assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())
spec=importlib.util.spec_from_file_location('previous_review',HERE/'pc007a-loft-coalescing-review-own.py');previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
SOURCE='7ee42b397e0491bff87a0f76b7c07850ef5b56c3'
REAL=Path(r'C:\Users\dalib\projects\papercraft-loft-integration\docs\p2\implementation\evidence\pc007a-loft-B1-desktop-73f3437-run01\loft-B1\loft-B1.apcraft')


def simple():
    return previous.native(previous.known_chain(((0,0),(2,3),(4,-1),(8,0)),[Q(0),Q(1,8),Q(3,4),Q(1)]),patches=3)


def test_runtime_imports_and_metadata_are_bound():
    out={}
    for name in ['loft_curve_compaction','loft_surface','project','paper']:
        mod=__import__('archpapercraft.authoring.'+name,fromlist=['x']);f=Path(mod.__file__).resolve();assert f.is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve());out[name]={'module_path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    (HERE/'pc007a-loft-coalescing-v4-review-imports.json').write_text(json.dumps(out,indent=2),encoding='utf8')


@pytest.mark.parametrize('room',[Q(1,2**30),Q(1,2**20),Q(1,2**10),Q(1,4)])
def test_default_internal_allocations_are_min_of_true_remaining_total(room):
    data=simple();data['position_error_bound_paper_mm']=float(Q(1,1024));data['boundary_length_error_bound_paper_mm']=float(Q(1,512))
    pb=float(Q(data['position_error_bound_paper_mm'])+room);lb=float(Q(data['boundary_length_error_bound_paper_mm'])+room)
    before=copy.deepcopy(data);result=coalesce_native_loft_boundaries(data,position_budget_mm=pb,length_budget_mm=lb);c=result['coalescing'];assert c['status']=='CERTIFIED_SAME_U_AND_GLOBAL_LENGTH'
    expected_p=min(Q(pb)-Q(data['position_error_bound_paper_mm']),Q(.001));expected_l=min(Q(lb)-Q(data['boundary_length_error_bound_paper_mm']),Q(.006))
    assert Q(c['effective_position_budget_paper_mm'])==expected_p and Q(c['effective_global_side_length_budget_paper_mm'])==expected_l
    assert Q(c['total_position_budget_paper_mm'])==Q(pb) and Q(c['total_global_side_length_budget_paper_mm'])==Q(lb)
    assert Q(result['position_error_bound_paper_mm'])<=Q(pb) and Q(result['boundary_length_error_bound_paper_mm'])<=Q(lb) and data==before


def test_default_reserves_do_not_bypass_global_side_length_by_patch_or_max():
    chain,eps=previous.hump_chain()
    # Keep x scale, enlarge actual y humps sixteenfold. If every patch were
    # merged into one straight C, the true total length loss would exceed .006.
    for s in chain:
        for p in [s['start'],s['end'],*s['data'].values()]:p[1]*=16
    data=previous.native(chain,patches=8);before=copy.deepcopy(data);result=coalesce_native_loft_boundaries(data);c=result['coalescing'];assert c['status']=='CERTIFIED_SAME_U_AND_GLOBAL_LENGTH'
    rigorous_loss_if_all_merged=8*(2*(62*Q(3,4)+2*Q(3,8))*16*eps-3*eps)
    assert rigorous_loss_if_all_merged>Q(.006)
    assert any(len(p['first']['segments'])>1 for p in result['patches'])
    for side in ('first','second'):
        total=sum(Q(p[side]['coalescing']['length_bound_exact']) for p in result['patches'])
        assert total==Q(c['length_bound_exact'][side]) and total<=Q(.006)
    assert Q(result['boundary_length_error_bound_paper_mm'])<=Q(.008) and data==before


@pytest.mark.parametrize('field',['position_budget_mm','length_budget_mm'])
def test_exactly_exhausted_original_total_keeps_whole_original(field):
    data=simple();before=copy.deepcopy(data);value=data['position_error_bound_paper_mm'] if field.startswith('position') else data['boundary_length_error_bound_paper_mm']
    result=coalesce_native_loft_boundaries(data,**{field:value});assert result.pop('coalescing')['status']=='NOT_APPLIED_NO_REMAINING_ERROR_BUDGET' and result==before==data


@pytest.mark.parametrize('field',['max_candidates','max_comparisons'])
def test_work_cap_cannot_publish_partial_coalescing(field):
    data=simple();before=copy.deepcopy(data);result=coalesce_native_loft_boundaries(data,**{field:1});assert result.pop('coalescing')['status']=='NOT_APPLIED_WORK_BUDGET_EXHAUSTED' and result==data==before


def test_repeat_call_does_not_spend_default_reserves_again():
    data=simple();result=coalesce_native_loft_boundaries(data);assert coalesce_native_loft_boundaries(result)==result
    with pytest.raises(ValueError):coalesce_native_loft_boundaries(result,position_budget_mm=.0001)


@pytest.mark.parametrize('version',['V2','V3'])
def test_previous_versions_load_stale_until_explicit_recompute(version,monkeypatch,tmp_path):
    p=AuthorProject.new(scale=1);a=p.add_profile([[0,0],[10,0],[10,5]],closed=False);b=p.copy_profile(a,plane={'origin':[0,0,7],'u':[1,0,0],'v':[0,1,0]});s=p.add_loft(a,b,correspondences=[dict(first_segment_id=x.id,second_segment_id=y.id) for x,y in zip(p.profiles[a].segments,p.profiles[b].segments)]);pid=p.part_for_surface(s);p.set_placement(pid,p.pages[0].id,40,50,19,position_locked=True,rotation_locked=True)
    with monkeypatch.context() as old:
        old.setattr(loft_surface,'LOFT_PAPER_CONTRACT','ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_EXACT_COLLINEAR_CUT_V2' if version=='V2' else 'ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_BOUNDED_COALESCED_CUT_V3');p.recompute()
    f=tmp_path/(version+'.apcraft');p.save(f);raw=f.read_bytes();loaded=load_project(f);before=loaded.to_dict();assert loaded.loft_status(s)['paper_stale'] and [i.code for i in loaded.validate_layout()]==['STALE']
    with pytest.raises(ValidationError):loaded.snapshot()
    loaded.recompute();after=loaded.to_dict();assert before['profiles']==after['profiles'] and before['surfaces']==after['surfaces'] and before['placements']==after['placements'] and before['parts'][pid]['frame']==after['parts'][pid]['frame'] and f.read_bytes()==raw
    assert loaded.loft_status(s)['paper_contract'].endswith('V4') and not loaded.validate_layout()


def green(commands):
    total=Q(0);current=start=None
    for c in commands:
        op=c[0];values=list(map(Q,c[1:]))
        if op=='M':current=start=tuple(values);continue
        end=start if op=='Z' else tuple(values[-2:])
        if op in ('L','Z'):total+=(current[0]*end[1]-current[1]*end[0])/2
        else:
            assert op=='C';poly=[]
            for axis in (0,1):
                a,b,d,e=current[axis],values[axis],values[2+axis],values[4+axis];poly.append((a,3*(b-a),3*(a-2*b+d),e-3*d+3*b-a))
            x,y=poly;total+=sum(Q(j,2*(i+j))*(x[i]*y[j]-y[i]*x[j]) for i in range(4) for j in range(1,4))
        current=end
    return abs(total)


def source_area_interval(scale):
    # Independent half-angle substitution for Gothic R32.5/c12.5/H10/k6/5:
    # area=440+2.2 integral_0^(2/3)65sqrt(116+272t²+181t4)/(1+t²)² dt.
    # Whole f'''' bound1e8 with sqrt(P)>10; see previous independent area review.
    n=4096
    with localcontext() as c:
        c.prec=80;end=Decimal(2)/3;step=end/n
        def f(t):return 65*(116+272*t*t+181*t**4).sqrt()/(1+t*t)**2
        total=f(Decimal(0))+f(end)
        for i in range(1,n):total+=(4 if i%2 else 2)*f(i*step)
        estimate=Q(440)+Q(11,5)*Q(total*step/3);error=Q(11,5)*Q(end)*Q(step)**4*10**8/180+Q(1,10**9)
    factor=(100*Q(scale))**2
    return (estimate-error)*factor,(estimate+error)*factor


def test_actual_saved_69_command_B1_replay_keeps_source_and_checks_direct_area(tmp_path):
    started=time.perf_counter();raw=REAL.read_bytes();p=load_project(REAL);sid=next(s.id for s in p.surfaces.values() if s.kind=='ruled_loft');pid=p.part_for_surface(sid);before=p.to_dict();assert len(p.parts[pid].paths['CUT'][0]['commands'])==69
    assert p.parts[pid].stale and p.loft_status(sid)['paper_stale']
    with pytest.raises(ValidationError):p.snapshot()
    p.recompute();after=p.to_dict();report=p.loft_status(sid);cmd=p.parts[pid].paths['CUT'][0]['commands'];assert len(cmd)==21 and sum(c[0]=='C' for c in cmd)==16
    for k in ['profiles','surfaces','placements','pages','next_part_number','next_joint_number','next_attachment_number']:assert before[k]==after[k]
    assert before['parts'][pid]['frame']==after['parts'][pid]['frame'] and before['parts'][pid]['id']==after['parts'][pid]['id'] and REAL.read_bytes()==raw
    assert report['native_topology']['status']=='VALID' and report['area']['status']==report['paper_frame_area']['status']=='CERTIFIED'
    area=green(cmd);lo,hi=source_area_interval(p.scale);assert max(abs(area-lo),abs(area-hi))<Q(1,100)
    native=loft_surface.analysis(p,p.surfaces[sid])['native'];assert native['position_error_bound_paper_mm']<.008 and native['boundary_length_error_bound_paper_mm']<.008
    assert not p.validate_layout() and p.snapshot()
    copyfile=tmp_path/'B1-copy.apcraft';p.save(copyfile);assert load_project(copyfile).to_dict()==p.to_dict()
    poisoned=copy.deepcopy(after)
    for c in poisoned['parts'][pid]['paths']['CUT'][0]['commands']:
        for i in range(1,len(c),2):c[i]+=.125
    bad=AuthorProject.from_dict(poisoned);assert not bad.parts[pid].stale and 'INVALID_CACHE' in [i.code for i in bad.validate_layout()]
    with pytest.raises(ValidationError):bad.snapshot()
    result={'source_sha':SOURCE,'module':str(Path(actual.__file__).resolve()),'fixture':str(REAL),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'old_commands':69,'new_commands':21,'source_layout_frame_identity_file_unchanged':True,'current_poison_rejected':True,'save_reopen':True,'actual_native_green_area_exact':str(area),'actual_native_green_area_mm2':float(area),'independent_source_area_interval_mm2':[float(lo),float(hi)],'source_to_native_area_error_upper_mm2':float(max(abs(area-lo),abs(area-hi))),'coalescing':native['coalescing'],'total_position_bound_mm':native['position_error_bound_paper_mm'],'total_global_side_length_bound_mm':native['boundary_length_error_bound_paper_mm'],'seconds':time.perf_counter()-started,'native_and_editor':'NOT_RUN_BY_THIS_REVIEWER'}
    (HERE/'pc007a-loft-coalescing-v4-review-actualB1.json').write_text(json.dumps(result,indent=2),encoding='utf8')
