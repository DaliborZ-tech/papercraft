"""Exact power-polynomial and constructive length lower-bound review oracles."""
import copy
from fractions import Fraction as F

import pytest

from archpapercraft.authoring import AuthorProject,ValidationError,load_project
from archpapercraft.authoring.loft_curve_compaction import coalesce_native_loft_boundaries,restrict_cubic,reverse_segment


def coefficients(points):
    result=[]
    for axis in (0,1):
        a,b,c,d=(F(p[axis]) for p in points)
        result.append((a,3*(b-a),3*(c-2*b+a),d-3*c+3*b-a))
    return result


def restricted_power(points,a,b):
    """Substitute u=a+(b-a)t in ordinary monomials, not de Casteljau."""
    a,b=F(a),F(b);h=b-a;axes=[]
    for c0,c1,c2,c3 in coefficients(points):
        q0=c0+c1*a+c2*a*a+c3*a*a*a
        q1=h*(c1+2*c2*a+3*c3*a*a)
        q2=h*h*(c2+3*c3*a);q3=h*h*h*c3
        axes.append((q0,q0+q1/3,q0+2*q1/3+q2/3,q0+q1+q2+q3))
    return tuple(tuple(axis[i] for axis in axes) for i in range(4))


def value(points,u):
    return tuple(sum(c*u**i for i,c in enumerate(axis)) for axis in coefficients(points))


def segment(points,u,v,*,sid='curve',reverse=False):
    points=[list(map(float,p)) for p in points]
    return {'kind':'cubic' if len(points)==4 else 'line','start':points[0],'end':points[-1],
            'data':{'control1':points[1],'control2':points[2]} if len(points)==4 else {},
            'source':{'profile_id':'profile','segment_id':sid,'feature_id':'feature','patch_id':'patch',
                      'parameter_interval':[float(1-u if reverse else u),float(1-v if reverse else v)],
                      'loft_parameter_interval':[float(u),float(v)],'direction':-1 if reverse else 1}}


def actual_controls(s):
    return tuple(tuple(map(F,p)) for p in ([s['start'],s['end']] if s['kind']=='line' else
                 [s['start'],s['data']['control1'],s['data']['control2'],s['end']]))


def native(chain,*,patches=1):
    result={'status':'CERTIFIED_REPRESENTATION_ONLY','patches':[],
            'position_error_bound_paper_mm':.001,'boundary_length_error_bound_paper_mm':.002,
            'both_profile_boundaries_length_error_bound_paper_mm':.004,
            'line_interpolant_deviation_bound_paper_mm':.0001,
            'native_boundary_length_excess_bound_paper_mm':{'first':.0002,'second':.0003}}
    for index in range(patches):
        patch={}
        for side,shift in (('first',0),('second',8)):
            sides=copy.deepcopy(chain)
            for s in sides:
                s['source']['patch_id']=f'patch-{index}';s['source']['profile_id']=side
                for point in [s['start'],s['end'],*s['data'].values()]:point[1]+=shift
            patch[side]={'segments':sides,'line_interpolant_deviation_bound_paper_mm':.0001,'length_excess_bound_paper_mm':.0002}
        first=patch['first']['segments'];second=patch['second']['segments']
        def ruling(a,b,name):return {'kind':'line','start':copy.deepcopy(a),'end':copy.deepcopy(b),'data':{},'source':{'kind':'EXPLICIT_MATCHED_RULING','ruling_id':name}}
        patch['closed_boundary_segments']=[ruling(first[-1]['end'],second[-1]['end'],'end'),ruling(second[0]['start'],first[0]['start'],'start')]
        patch['source_patch_boundary_policy']='NO_CROSS_PATCH_SMOOTHING'
        result['patches'].append(patch)
    return result


def known_chain(points,parameters,*,reverse=False):
    return [segment(restricted_power(points,a,b),a,b,reverse=reverse) for a,b in zip(parameters,parameters[1:])]


@pytest.mark.parametrize('a,b',[(F(1,128),F(97,128)),(F(13,64),F(31,32)),(F(0),F(1)),(F(1023,1024),F(1))])
def test_product_restriction_equals_independent_exact_substitution_everywhere(a,b):
    controls=((2,-5),(17,13),(-11,19),(29,-7))
    actual=restrict_cubic(controls,a,b);expected=restricted_power(controls,a,b)
    assert actual==expected
    for t in (F(0),F(1,17),F(9,13),F(1)):
        assert value(actual,t)==value(controls,a+(b-a)*t)


def test_unequal_intervals_recover_one_exact_binary_cubic_and_all_provenance():
    controls=((0,0),(12,24),(-6,18),(24,-3));u=[F(0),F(1,128),F(3,16),F(7,8),F(1)]
    source=native(known_chain(controls,u,reverse=True));before=copy.deepcopy(source)
    result=coalesce_native_loft_boundaries(source)
    s=result['patches'][0]['first']['segments'];assert len(s)==1
    assert actual_controls(s[0])==tuple(tuple(map(F,p)) for p in controls)
    assert F(result['coalescing']['position_bound_exact'])==0
    assert s[0]['source']['subintervals']==[x['source'] for x in source['patches'][0]['first']['segments']]
    assert s[0]['source']['direction']==-1 and s[0]['source']['parameter_interval']==[1,0]
    reversed_s=reverse_segment(s[0]);assert reversed_s['source']['direction']==1
    assert reverse_segment(reversed_s)==s[0] and source==before


def hump_chain():
    eps=F(1,2**20);points=((0,0),(eps,0),(2*eps,0),(3*eps,0));u=[F(i,64) for i in range(65)]
    result=known_chain(points,u)
    for i,s in enumerate(result):
        if i!=0:s['data']['control1'][1]=float(eps)
        if i!=63:s['data']['control2'][1]=float(eps)
    return result,eps


def test_many_actual_humps_prove_global_length_error_exceeds_max_local_error():
    chain,eps=hump_chain();source=native(chain,patches=2)
    result=coalesce_native_loft_boundaries(source,merge_length_budget_mm=.001)
    assert all(len(p['first']['segments'])==1 for p in result['patches'])
    bound=F(result['coalescing']['length_bound_exact']['first'])
    # Each curve length is at least total y variation through its midpoint.
    # 62 full humps height3eps/4,2 end humps height3eps/8, minus coarse3eps.
    rigorous_length_difference_lower=2*(2*(62*F(3,4)+2*F(3,8))-3)*eps
    assert rigorous_length_difference_lower>100*eps
    assert bound>=rigorous_length_difference_lower
    assert bound>=2*126*eps  # derivative-difference integral bound summed over2 patches
    assert bound>max(F(p['first']['coalescing']['length_bound_exact']) for p in result['patches'])
    assert rigorous_length_difference_lower>max(F(p['first']['coalescing']['length_bound_exact']) for p in result['patches'])
    assert F(result['both_profile_boundaries_length_error_bound_paper_mm'])>=F(source['both_profile_boundaries_length_error_bound_paper_mm'])+2*bound
    assert F(result['boundary_length_error_bound_paper_mm'])>=F(source['boundary_length_error_bound_paper_mm'])+bound
    assert F(result['position_error_bound_paper_mm'])>=F(source['position_error_bound_paper_mm'])+F(result['coalescing']['position_bound_exact'])


def test_recomputed_coarse_binary_derivative_jump_has_analytic_global_u_units():
    chain=[]
    for points,lo,hi,sid in [(((0,0),(1,0),(2,0),(3,0)),F(0),F(1,4),'horizontal'),
                              (((3,0),(3,F(1,2)),(3,1),(3,F(3,2))),F(1,4),F(1),'vertical')]:
        for u,v in ((F(0),F(1,2)),(F(1,2),F(1))):
            chain.append(segment(restricted_power(points,u,v),lo+(hi-lo)*u,lo+(hi-lo)*v,sid=sid))
    result=coalesce_native_loft_boundaries(native(chain))
    boundary=result['patches'][0]['first'];assert len(boundary['segments'])==2
    # Actual endpoint derivatives are exactly (12,0) and (0,2) in global u.
    bound=F(boundary['binary_control_derivative_jump_bound_paper_mm_per_u'])
    assert bound*bound>=148 and F('12.16')<bound<F('12.17')
    assert not boundary['exact_c1_of_binary_controls']


def test_actual_binary_controls_at_large_offset_remain_inside_same_u_bound():
    off=2**30;s=F(1,2**15)
    controls=((off,off),(off+12*s,off+24*s),(off-6*s,off+18*s),(off+24*s,off-3*s))
    params=[F(0),F(1,128),F(3,16),F(7,8),F(1)]
    source=native(known_chain(controls,params));result=coalesce_native_loft_boundaries(source)
    merged=result['patches'][0]['first']['segments'];assert len(merged)<=len(params)-1
    for coarse in merged:
        if 'coalescing' not in coarse:continue
        controls_c=actual_controls(coarse);a,b=map(F,coarse['source']['loft_parameter_interval'])
        radius=F(coarse['coalescing']['position_bound_exact'])
        for fine in source['patches'][0]['first']['segments']:
            u,v=map(F,fine['source']['loft_parameter_interval'])
            if u<a or v>b:continue
            restriction=restricted_power(controls_c,(u-a)/(b-a),(v-a)/(b-a))
            for x,y in zip(restriction,actual_controls(fine)):
                assert sum((a-b)**2 for a,b in zip(x,y))<=radius*radius


def test_kind_source_corner_side_and_patch_boundaries_preserve_rulings():
    controls=((0,0),(4,0),(8,0),(12,0));params=[F(0),F(1,4),F(1,2),F(3,4),F(1)]
    chain=known_chain(controls,params)
    for s in chain[2:]:s['source']['segment_id']='next-source'
    chain[-1]=segment([chain[-1]['start'],chain[-1]['end']],F(3,4),F(1),sid='tiny-corner-line')
    source=native(chain,patches=2);result=coalesce_native_loft_boundaries(source)
    for p,q in zip(source['patches'],result['patches']):
        assert [s['kind'] for s in q['first']['segments']]==['cubic','cubic','line']
        assert q['first']['segments'][0]['end']==p['first']['segments'][1]['end']
        actual_rulings=[s for s in q['closed_boundary_segments'] if s['source'].get('kind')=='EXPLICIT_MATCHED_RULING']
        assert actual_rulings==p['closed_boundary_segments']
        backward=q['closed_boundary_segments'][-2]
        assert reverse_segment(backward)==q['second']['segments'][0]


@pytest.mark.parametrize('limit',['max_candidates','max_comparisons'])
def test_exhausted_work_limit_returns_entire_original_not_partially_compacted(limit):
    chain,_=hump_chain();source=native(chain,patches=2);before=copy.deepcopy(source)
    result=coalesce_native_loft_boundaries(source,**{limit:2})
    assert result.pop('coalescing')['status']=='NOT_APPLIED_WORK_BUDGET_EXHAUSTED'
    assert result==source==before


def test_remaining_budget_never_discards_existing_source_to_fine_error():
    chain,eps=hump_chain();source=native(chain)
    result=coalesce_native_loft_boundaries(source,position_budget_mm=.001)
    assert result.pop('coalescing')['status']=='NOT_APPLIED_NO_REMAINING_ERROR_BUDGET'
    assert result==source


def test_current_v3_equal_area_poison_fails_but_old_contract_stales_preserving_source(tmp_path,monkeypatch):
    from archpapercraft.authoring import loft_surface
    p=AuthorProject.new(scale=1);a=p.add_profile([[0,0],[10,0],[10,5]],closed=False)
    b=p.copy_profile(a,plane={'origin':[0,0,7],'u':[1,0,0],'v':[0,1,0]})
    pairs=[{'first_segment_id':x.id,'second_segment_id':y.id} for x,y in zip(p.profiles[a].segments,p.profiles[b].segments)]
    sid=p.add_loft(a,b,correspondences=pairs);pid=p.part_for_surface(sid)
    p.set_placement(pid,p.pages[0].id,30,40,19,position_locked=True,rotation_locked=True)
    current=copy.deepcopy(p.to_dict())
    poison=copy.deepcopy(current)
    for cmd in poison['parts'][pid]['paths']['CUT'][0]['commands']:
        for index in range(1,len(cmd),2):cmd[index]+=.25
    bad=AuthorProject.from_dict(poison)
    assert 'INVALID_CACHE' in [i.code for i in bad.validate_layout()]
    with pytest.raises(ValidationError):bad.snapshot()
    with monkeypatch.context() as old:
        old.setattr(loft_surface,'LOFT_PAPER_CONTRACT','ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_EXACT_COLLINEAR_CUT_V2')
        p.recompute()
    path=tmp_path/'old.apcraft';p.save(path);raw=path.read_bytes();state=copy.deepcopy(p.to_dict())
    restored=load_project(path);assert restored.parts[pid].stale
    with pytest.raises(ValidationError):restored.snapshot()
    restored.recompute()
    assert restored.to_dict()['profiles']==state['profiles'] and restored.to_dict()['surfaces']==state['surfaces']
    assert restored.to_dict()['placements']==state['placements'] and restored.to_dict()['parts'][pid]['frame']==state['parts'][pid]['frame']
    assert path.read_bytes()==raw and not restored.validate_layout()
