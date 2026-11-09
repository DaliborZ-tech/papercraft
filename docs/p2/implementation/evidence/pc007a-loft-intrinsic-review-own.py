"""Independent area/legacy/cache oracles for exact pinned a1cbf92; no UI proof."""
import copy
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import importlib.util
import json
import math
import os
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject, ProjectFormatError, ValidationError
from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring import loft_area as actual
from archpapercraft.authoring.loft_geometry import LoftProfile, LoftCorrespondence
from archpapercraft.authoring import loft_surface

assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('prior_review', HERE/'pc007a-loft-domain-review-own.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)

PI_LO = Q('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')
PI_HI = PI_LO + Q(1, 10**100)


def sqrt_bounds(value, bits=240):
    value = Q(value)
    n = math.isqrt((value.numerator << (2*bits))//value.denominator)
    return Q(n, 1<<bits), Q(n+1, 1<<bits)


def bounds(result):
    assert result['status']=='CERTIFIED', result
    lo, hi = Q(result['area_lower_exact']), Q(result['area_upper_exact'])
    assert 0<lo<=hi and hi-lo<=Q(result['absolute_budget_mm2'])
    assert Q(result['area_lower_paper_mm2'])<=lo<=hi<=Q(result['area_upper_paper_mm2'])
    assert result['proof']['scope']=='INTRINSIC_AREA_ONLY_NOT_A_FLATTENING_OR_TOPOLOGY_CERTIFICATE'
    return lo,hi


def refs(a,b,reverse=False):
    pairs=list(zip(a.curves,b.curves))
    if reverse:pairs.reverse()
    interval=(1,0) if reverse else (0,1)
    return tuple(LoftCorrespondence(x.segment_id,y.segment_id,interval,interval) for x,y in pairs)


def circle(radius,height=0,prefix='a',*,basis=((1,0,0),(0,1,0)),sweep=180,origin_x=0):
    assert abs(sweep) in (90,180,270)
    ends={90:(0,radius),-90:(0,-radius),180:(-radius,0),-180:(-radius,0),270:(0,-radius),-270:(0,radius)}
    c=Curve((radius,0),ends[sweep],'arc',{'center':(0,0),'sweep_deg':sweep},prefix+'0')
    return LoftProfile((c,),origin=(origin_x,0,height),u=basis[0],v=basis[1],profile_id=prefix)


@pytest.mark.parametrize('r0,r1,height,sweep,scale',[(3,7,12,90,1),(7,3,-12,-270,.125),(20,24,10,180,.01),(2,2,200,270,1)])
@pytest.mark.parametrize('reverse',[False,True])
def test_pi_frustum_source_area_against_integer_isqrt_rational_oracle(r0,r1,height,sweep,scale,reverse):
    a,b=circle(r0,sweep=sweep,origin_x=1e30),circle(r1,height,'b',sweep=sweep,origin_x=1e30)
    result=actual.certify_loft_intrinsic_area(a,b,refs(a,b,reverse),scale=scale,absolute_budget_mm2=1e-10)
    lo,hi=bounds(result)
    sl,su=sqrt_bounds((r1-r0)**2+height**2)
    factor=Q(r0+r1,2)*Q(abs(sweep),180)*Q(scale)**2
    assert lo<=factor*sl*PI_LO<=factor*su*PI_HI<=hi


@pytest.mark.parametrize('eps',[2**-42,-2**-42])
def test_actual_binary_nonunit_world_basis_is_not_idealized(eps):
    f=1+eps;basis=((f,0,0),(0,f,0))
    a,b=circle(11,basis=basis),circle(11,19,'b',basis=basis)
    lo,hi=bounds(actual.certify_loft_intrinsic_area(a,b,refs(a,b),scale=1,absolute_budget_mm2=1e-11))
    factor=Q(209)*Q(f)
    assert lo<=factor*PI_LO<=factor*PI_HI<=hi
    if eps>0:assert lo>209*PI_HI
    else:assert hi<209*PI_LO


def quarter_pair(two=False,height=3):
    # r=2, off-axis center c=1, k=2. Every interval is real circular material.
    aa=[Curve((3,0),(1,2),'arc',{'center':(1,0),'sweep_deg':90},'a0')]
    if two:aa.append(Curve((1,2),(-1,0),'arc',{'center':(1,0),'sweep_deg':90},'a1'))
    bb=[Curve(tuple(2*x for x in a.start),tuple(2*x for x in a.end),'arc',{'center':(2,0),'sweep_deg':90},'b'+str(i)) for i,a in enumerate(aa)]
    return LoftProfile(tuple(aa),profile_id='a'),LoftProfile(tuple(bb),origin=(0,0,height),profile_id='b')


def rational_half_angle_oracle(sign=1):
    """Independent substitution t=tan(theta/2), 0..1; no source trig/helper.

    f(t)=6 sqrt(9(1+t²)^2+[(2+sign)+(2-sign)t²]^2)/(1+t²)^2.
    P>=1, and sum(abs(coeff)*falling_factorial) bounds its derivatives.
    Derivatives of sqrt(P) use explicit scalar chain rule; q=(1+t²)^-2
    has bounds [1,4,28,264,3144]. Composite Simpson remainder M4/(180N^4).
    Decimal rounding is separately reserved far above 80-digit arithmetic error.
    """
    p0=9+(2+sign)**2;p2=18+2*(2+sign)*(2-sign);p4=9+(2-sign)**2
    d1=2*abs(p2)+4*abs(p4);d2=2*abs(p2)+12*abs(p4);d3=24*abs(p4);d4=24*abs(p4)
    g0=Q(p0+abs(p2)+abs(p4)) # sqrt(P)<=Pmax, since Pmax>1.
    g1=Q(d1,2)
    g2=Q(d2,2)+Q(d1*d1,4)
    g3=Q(d3,2)+Q(3*d1*d2,4)+Q(3*d1**3,8)
    g4=Q(d4,2)+Q(4*d1*d3+3*d2*d2,4)+Q(18*d1*d1*d2,8)+Q(15*d1**4,16)
    m4=6*(g4+4*g3*4+6*g2*28+4*g1*264+g0*3144)
    count=8192
    with localcontext() as c:
        c.prec=80
        def f(t):
            z=t*t
            return 6*(Decimal(p0)+p2*z+p4*z*z).sqrt()/(1+z)**2
        total=f(Decimal(0))+f(Decimal(1))
        for i in range(1,count):total+=(4 if i%2 else 2)*f(Decimal(i)/count)
        estimate=Q(total/(3*count))
    remainder=m4/(180*count**4)+Q(1,10**55)
    return estimate-remainder,estimate+remainder


@pytest.mark.parametrize('two',[False,True])
@pytest.mark.parametrize('reverse',[False,True])
def test_nonconstant_arcs_global_budget_against_rational_half_angle_integral(two,reverse):
    a,b=quarter_pair(two)
    result=actual.certify_loft_intrinsic_area(a,b,refs(a,b,reverse),scale=1,absolute_budget_mm2=1e-5)
    lo,hi=bounds(result)
    ol,oh=rational_half_angle_oracle()
    if two:
        ql,qh=rational_half_angle_oracle(-1);ol+=ql;oh+=qh
    assert lo<=ol<=oh<=hi
    assert len(result['coverage']['correspondences'])==(2 if two else 1)


@pytest.mark.parametrize('u',[(Q(-699,100),Q(-699,100)),(Q(0),Q(0)),(Q(699,100),Q(699,100)),(Q(1,3),Q(1,3)),(Q(1,3)-Q(1,10**30),Q(1,3)+Q(1,10**30))])
def test_trig_enclosure_against_longer_independent_rational_series(u):
    def series(x,cosine=False):
        # 160 exact rational terms, alternating tail after the decreasing range.
        value=Q(0)
        for i in range(160):
            degree=2*i+(0 if cosine else 1)
            value+=(-1 if i%2 else 1)*x**degree/math.factorial(degree)
        d=320+(0 if cosine else 1)
        error=abs(x)**d/math.factorial(d)
        return value-error,value+error
    s,c=actual._sin_cos(u)
    for endpoint in u:
        sl,sh=series(endpoint);cl,ch=series(endpoint,True)
        assert s[0]<=sl<=sh<=s[1] and c[0]<=cl<=ch<=c[1]


@pytest.mark.parametrize('height',[0,2**-30,2**-12])
def test_near_zero_height_no_unbounded_simpson_claim(height):
    a,b=quarter_pair(True,height)
    result=actual.certify_loft_intrinsic_area(a,b,refs(a,b),scale=1,max_nodes=15,max_depth=2,absolute_budget_mm2=1e-10)
    assert result['status']=='UNRESOLVED' and 'area_lower_exact' not in result
    assert result['examined_nodes']<=15


@pytest.mark.parametrize('settings',[{'max_nodes':2},{'max_depth':0},{'absolute_budget_mm2':1e-25}])
def test_nonconstant_source_exhaustion_stays_unresolved(settings):
    a,b=quarter_pair(True)
    r=actual.certify_loft_intrinsic_area(a,b,refs(a,b),scale=1,**settings)
    assert r['status']=='UNRESOLVED' and 'area_lower_exact' not in r


@pytest.mark.parametrize('reverse',[False,True])
def test_polynomial_nonuniform_source_global_area_is_exact_integer(reverse):
    # Two collinear but non-uniform cubic parameters: true lengths 6 and 9.
    a=LoftProfile((Curve((0,0),(6,0),'cubic',{'control1':(1,0),'control2':(3,0)},'a0'),Curve((6,0),(15,0),'cubic',{'control1':(7,0),'control2':(10,0)},'a1')),profile_id='a')
    b=LoftProfile(tuple(Curve(c.start,c.end,c.kind,dict(c.data),'b'+str(i)) for i,c in enumerate(a.curves)),origin=(0,0,7),profile_id='b')
    lo,hi=bounds(actual.certify_loft_intrinsic_area(a,b,refs(a,b,reverse),scale=.125,absolute_budget_mm2=1e-20))
    assert lo<=Q(105,64)<=hi


def test_polynomial_area_only_certificate_does_not_certify_nonregular_surface():
    # End derivative collapses, while integral area remains positive. Helper is
    # correctly ONLY an area certificate; source regularity belongs to solver.
    c=Curve((0,0),(1,0),'cubic',{'control1':(0,0),'control2':(0,0)},'a0')
    a=LoftProfile((c,),profile_id='a');b=LoftProfile((replace(c,segment_id='b0'),),origin=(0,0,10),profile_id='b')
    lo,hi=bounds(actual.certify_loft_intrinsic_area(a,b,refs(a,b),scale=1))
    assert lo<=10<=hi


@pytest.mark.parametrize('reverse',[False,True])
def test_true_cubic_global_two_patch_cross_product_against_scalar_quartic_oracle(reverse):
    # x=3t,y=3t² over t=0..2, split at t=1. All native controls are integers.
    aa=(Curve((0,0),(3,3),'cubic',{'control1':(1,0),'control2':(2,1)},'a0'),Curve((3,3),(6,12),'cubic',{'control1':(4,5),'control2':(5,8)},'a1'))
    bb=tuple(Curve(tuple(2*x for x in c.start),tuple(2*x for x in c.end),'cubic',{k:tuple(2*x for x in v) for k,v in c.data.items()},'b'+str(i)) for i,c in enumerate(aa))
    a=LoftProfile(aa,profile_id='a');b=LoftProfile(bb,origin=(0,0,11),profile_id='b')
    lo,hi=bounds(actual.certify_loft_intrinsic_area(a,b,refs(a,b,reverse),scale=1,absolute_budget_mm2=1e-5))
    # |C' cross (C+(0,0,11))|=3sqrt(121+484t²+9t⁴), factor 3/2.
    # Scalar sqrt chain-rule bound with P>=121 and t<=2, using m=11.
    d1,d2,d3,d4=2224,1400,432,216
    m=Q(11)
    fourth=Q(9,2)*(Q(d4)/(2*m)+Q(4*d1*d3+3*d2*d2)/(4*m**3)+Q(18*d1*d1*d2)/(8*m**5)+Q(15*d1**4)/(16*m**7))
    count=8192
    with localcontext() as c:
        c.prec=80
        def f(t):return Decimal('4.5')*(121+484*t*t+9*t**4).sqrt()
        total=f(Decimal(0))+f(Decimal(2))
        for i in range(1,count):total+=(4 if i%2 else 2)*f(Decimal(2*i)/count)
        estimate=Q(total*2/(3*count))
    remainder=Q(2,180)*Q(2,count)**4*fourth+Q(1,10**55)
    assert lo<=estimate-remainder<=estimate+remainder<=hi


@pytest.mark.parametrize('case',['area','crease'])
def test_historical_472_paper_cache_is_stale_without_changing_source_or_anchor(case):
    raw=json.loads((HERE/f'pc007a-loft-domain-review-{case}-472.json').read_text(encoding='utf8'))
    p=AuthorProject.from_dict(raw['project']);sid=next(s.id for s in p.surfaces.values() if s.kind=='ruled_loft');pid=p.part_for_surface(sid)
    profiles=copy.deepcopy(p.profiles);frame=copy.deepcopy(p.parts[pid].frame);place=copy.deepcopy(p.placements.get(pid));part_ids=set(p.parts)
    assert p.loft_status(sid)['paper_stale']
    with pytest.raises(ValidationError):p.snapshot()
    p.recompute()
    assert not p.loft_status(sid)['paper_stale'] and set(p.parts)==part_ids
    assert p.profiles==profiles and p.parts[pid].frame==frame and p.placements.get(pid)==place
    assert p.loft_status(sid)['area']['status']=='CERTIFIED'


@pytest.mark.parametrize('damage',['missing','duplicate','one_reverse','partial','bool','basis'])
def test_unbound_or_partial_numeric_certificate_is_never_certified(damage):
    a,b=quarter_pair(True);r=refs(a,b)
    if damage=='missing':r=r[:-1]
    elif damage=='duplicate':r=(r[0],r[0])
    elif damage=='one_reverse':r=(replace(r[0],second_interval=(1,0)),r[1])
    elif damage=='partial':r=(replace(r[0],first_interval=(0,.5)),r[1])
    elif damage=='bool':r=(replace(r[0],first_interval=(False,True)),r[1])
    else:b=replace(b,u=(0,1,0),v=(-1,0,0))
    result=actual.certify_loft_intrinsic_area(a,b,r,scale=1)
    assert result['status']=='UNRESOLVED' and 'area_lower_exact' not in result


@pytest.mark.parametrize('version,writer',[(1,'0.3.0-experimental'),(2,'0.3.0-pc006b-experimental'),(3,'0.3.0-pc006b-clearance-experimental')])
def test_LD03_declared_legacy_envelopes_reject_future_loft_and_arc_params(version,writer):
    p,a,b=prior.source();p.add_loft(a,b,correspondences=prior.refs(p,a,b));data=p.to_dict();data.update(schema_version=version,writer_version=writer)
    with pytest.raises(ProjectFormatError):AuthorProject.from_dict(data)
    p=AuthorProject.new(scale=1);a=p.add_profile(segments=[dict(kind='arc',start=[10,0],end=[0,10],data=dict(center=[0,0],sweep_deg=90)),dict(kind='line',start=[0,10],end=[10,0])]);p.add_surface(a);data=p.to_dict();data.update(schema_version=version,writer_version=writer)
    with pytest.raises(ProjectFormatError):AuthorProject.from_dict(data)


def test_poisoned_cache_blocks_before_old_INVALID_CACHE_code_and_recomputes_safely():
    p,a,b=prior.source();s=p.add_loft(a,b,correspondences=prior.refs(p,a,b));pid=p.part_for_surface(s);p.set_placement(pid,p.pages[0].id,30,30)
    before=p.to_dict();data=copy.deepcopy(before);data['parts'][pid]['paths']['CUT'][0]['commands'][0][1]+=1
    loaded=AuthorProject.from_dict(data)
    assert any(i.code=='LOFT_FRAME_AREA_UNRESOLVED' and i.severity=='error' for i in loaded.validate_layout())
    with pytest.raises(ValidationError):loaded.snapshot()
    loaded.recompute();assert loaded.to_dict()==before
    assert loaded.snapshot()['coverage']['expected_part_ids']==[pid]


@pytest.mark.parametrize('damage',['profile','segment','closed','second_interval'])
def test_intrinsic_source_proof_binding_guard_is_live(monkeypatch,damage):
    original=actual.certify_loft_intrinsic_area
    def wrong(*args,**kwargs):
        report=original(*args,**kwargs);assert report['status']=='CERTIFIED'
        cov=report['coverage']
        if damage=='profile':cov['second_profile_id']='wrong'
        elif damage=='segment':cov['expected_first_segment_ids'][0]='wrong'
        elif damage=='closed':cov['second_closed']=not cov['second_closed']
        else:cov['correspondences'][0]['second_parameter_interval']=[1,0]
        return report
    monkeypatch.setattr(actual,'certify_loft_intrinsic_area',wrong)
    loft_surface._analyze.cache_clear();loft_surface._bound_analysis.cache_clear()
    p,a,b=prior.source();s=p.add_loft(a,b,correspondences=prior.refs(p,a,b));assert p.loft_status(s)['status']=='UNRESOLVED'
    with pytest.raises(ValidationError):p.snapshot()


def test_LD02_bounded_refinement_cannot_silently_expand_node_cap_or_change_sources():
    p=AuthorProject.new(scale=1);a=p.add_profile(segments=[dict(kind='arc',start=[20,0],end=[-20,0],data=dict(center=[0,0],sweep_deg=180))],closed=False);b=p.copy_profile(a,plane=dict(origin=[0,0,200],u=[1,0,0],v=[0,1,0]));profiles=copy.deepcopy(p.profiles)
    s=p.add_loft(a,b,correspondences=prior.refs(p,a,b),max_segments=512)
    result=p.loft_status(s)
    assert result['status']=='UNRESOLVED' and p.profiles==profiles
    assert p.surfaces[s].params['max_segments']==512 and 1<len(result['area']['refinement_attempts'])<=5
    assert AuthorProject.from_dict(p.to_dict()).surfaces[s]==p.surfaces[s]
    before=p.to_dict()
    with pytest.raises(ValidationError):p.recompute()
    assert p.to_dict()==before
    with pytest.raises(ValidationError):p.snapshot()
