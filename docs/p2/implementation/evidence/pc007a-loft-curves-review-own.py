"""Independent rational Bernstein/global-chain/native-length review oracles."""
import copy
from fractions import Fraction as Q
import math
import os
from pathlib import Path

import pytest
from scipy.integrate import quad

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_geometry import LoftProfile,LoftCorrespondence,flatten_loft
from archpapercraft.authoring.loft_curves import fit_native_loft_boundaries
import archpapercraft.authoring.loft_curves as actual

assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())

def dist_enclosure(a,b):
    """Rational sqrt enclosure by integer isqrt at 200 binary fraction bits."""
    square=sum((Q(x)-Q(y))**2 for x,y in zip(a,b));den=1<<200
    if not square:return Q(0),Q(0)
    k=math.isqrt(square.numerator*den*den//square.denominator)
    return Q(k,den),Q(k if k*k*square.denominator==square.numerator*den*den else k+1,den)

def rational_whole_parameter_and_global_length(report,fit):
    assert fit['status']=='CERTIFIED_REPRESENTATION_ONLY',fit.get('message')
    residual=Q(fit['position_error_bound_paper_mm'])-Q(report['representation_error_bound_paper_mm'])-Q(fit['rounding_reserve_paper_mm'])
    assert residual>=0
    totals=[Q(0),Q(0)]
    for patch in fit['patches']:
        for side_index,side in enumerate(['first','second']):
            boundary=patch[side]
            boundary_total=Q(0)
            for segment in boundary['segments']:
                start,end=map(lambda p:tuple(map(Q,p)),[segment['start'],segment['end']])
                if segment['kind']=='line':continue
                controls=[start,tuple(map(Q,segment['data']['control1'])),tuple(map(Q,segment['data']['control2'])),end]
                line=[start,tuple((2*x+y)/3 for x,y in zip(start,end)),tuple((x+2*y)/3 for x,y in zip(start,end)),end]
                # Convex-hull theorem then covers EVERY local parameter, not a grid.
                for ctrl,elevated in zip(controls,line):
                    square=sum((x-y)**2 for x,y in zip(ctrl,elevated))
                    assert Q(segment['line_interpolant_deviation_bound_paper_mm'])**2>=square
                    assert Q(boundary['line_interpolant_deviation_bound_paper_mm'])**2>=square
                    assert residual**2>=square
                extra=max(Q(0),sum((dist_enclosure(x,y)[1] for x,y in zip(controls,controls[1:])),Q(0))-dist_enclosure(start,end)[0])
                assert Q(segment['length_excess_bound_paper_mm'])>=extra
                totals[side_index]+=extra
                boundary_total+=extra
            # Global values sum unrounded rational bounds, then round once;
            # summing already outward-rounded public local fields overcounts.
            assert Q(boundary['length_excess_bound_paper_mm'])>=boundary_total
            jumps=[]
            for left,right in zip(boundary['segments'],boundary['segments'][1:]):
                def derivative(s,end):
                    h=Q(s['source']['loft_parameter_interval'][1])-Q(s['source']['loft_parameter_interval'][0])
                    if s['kind']=='line':return [(Q(y)-Q(x))/h for x,y in zip(s['start'],s['end'])]
                    if end:return [3*(Q(x)-Q(y))/h for x,y in zip(s['end'],s['data']['control2'])]
                    return [3*(Q(x)-Q(y))/h for x,y in zip(s['data']['control1'],s['start'])]
                sq=sum((x-y)**2 for x,y in zip(derivative(left,True),derivative(right,False)));jumps.append(sq)
                assert Q(boundary['binary_control_derivative_jump_bound_paper_mm_per_u'])**2>=sq
            assert boundary['exact_c1_of_binary_controls']==all(x==0 for x in jumps)
    assert Q(fit['native_boundary_length_excess_bound_paper_mm']['first'])>=totals[0]
    assert Q(fit['native_boundary_length_excess_bound_paper_mm']['second'])>=totals[1]
    assert Q(fit['boundary_length_error_bound_paper_mm'])>=Q(report['boundary_length_error_bound_paper_mm'])+max(totals)+Q(fit['rounding_reserve_paper_mm'])
    assert Q(fit['both_profile_boundaries_length_error_bound_paper_mm'])>=2*Q(report['boundary_length_error_bound_paper_mm'])+sum(totals)+2*Q(fit['rounding_reserve_paper_mm'])

def synthetic(parameters=(0,.125,.5,1),*,count=1,near_line=False):
    q=Q(1,1<<40) if near_line else Q(1,32);xscale=Q(1,1024) if near_line else Q(1,4)
    offset=Q(1<<20) if near_line else Q(0)
    patches=[]
    for i in range(count):
        first=[[float(offset+i+xscale*Q(t)),float(q*Q(t)**2)] for t in parameters]
        second=[[x,y+.5] for x,y in first]
        patches.append(dict(parameters=list(parameters),source_parameters=[[t,t] for t in parameters],first_profile_id='p-first',second_profile_id='p-second',first_segment_id='a'+str(i),second_segment_id='b'+str(i),first_parameter_interval=[0,1],second_parameter_interval=[0,1],flat_first_paper_mm=first,flat_second_paper_mm=second,join_before_kind='FOLD_CREASE'))
    h=max(Q(b)-Q(a) for a,b in zip(parameters,parameters[1:]));delta=float(q*h*h/4)
    return dict(status='EXACT',family='POSITIVE_HOMOTHETIC_CONE',patches=patches,representation_error_bound_paper_mm=delta,boundary_length_error_bound_paper_mm=.001,regularity_lower_bound_paper_mm2=1,proof_scope='DECLARED_REGULAR_PARAMETRIC_FAMILY_AND_BOUNDED_REPRESENTATION'),q,xscale,offset

def evaluate(segment,t):
    if segment['kind']=='line':return [(1-t)*x+t*y for x,y in zip(segment['start'],segment['end'])]
    return [(1-t)**3*x+3*(1-t)**2*t*y+3*(1-t)*t*t*z+t**3*w for x,y,z,w in zip(segment['start'],segment['data']['control1'],segment['data']['control2'],segment['end'])]

def length(boundary):
    total=0
    for s in boundary['segments']:
        if s['kind']=='line':total+=math.dist(s['start'],s['end']);continue
        controls=[s['start'],s['data']['control1'],s['data']['control2'],s['end']]
        def speed(t):return math.hypot(*(3*((1-t)**2*(b-a)+2*(1-t)*t*(c-b)+t*t*(d-c)) for a,b,c,d in zip(*controls)))
        value,error=quad(speed,0,1,epsabs=1e-12,epsrel=1e-12);assert error<1e-10;total+=value
    return total

@pytest.mark.parametrize('near_line',[False,True])
@pytest.mark.parametrize('parameters',[(0,.125,.5,1),(0,2**-20,.03125,.5,1)])
def test_unequal_nearline_actual_binary_proof_over_whole_parameter(near_line,parameters):
    report,q,xscale,offset=synthetic(parameters,near_line=near_line);before=copy.deepcopy(report)
    fit=fit_native_loft_boundaries(report,position_budget_mm=.1,length_budget_mm=.1,rounding_reserve_mm=0)
    rational_whole_parameter_and_global_length(report,fit)
    assert report==before and fit['patches'][0]['first']['representation']=='NATIVE_HERMITE_CUBICS'
    # Independently elevate the known analytic quadratic F to Bernstein degree3.
    # Comparing ACTUAL controls with F's controls bounds F-C on every t.
    for side,dy in [('first',Q(0)),('second',Q(1,2))]:
        for segment in fit['patches'][0][side]['segments']:
            a,b=map(Q,segment['source']['loft_parameter_interval']);h=b-a
            p0=(offset+xscale*a,q*a*a+dy);p2=(offset+xscale*b,q*b*b+dy)
            p1=(p0[0]+h*xscale/2,p0[1]+h*q*a)
            true=[p0,tuple((x+2*y)/3 for x,y in zip(p0,p1)),tuple((2*x+y)/3 for x,y in zip(p1,p2)),p2]
            native=[segment['start'],segment['data']['control1'],segment['data']['control2'],segment['end']]
            for n,t in zip(native,true):assert sum((Q(x)-y)**2 for x,y in zip(n,t))<=Q(fit['position_error_bound_paper_mm'])**2

@pytest.mark.parametrize('r,k,depth,reverse',[(7,2,11,False),(13,.5,-9,False),(7,2,0,True)])
def test_actual_source_circle_chains_have_independent_length_and_curve_bounds(r,k,depth,reverse):
    interval=(1,0) if reverse else (0,1)
    profiles=[LoftProfile((Curve((radius,0),(-radius,0),'arc',dict(center=(0,0),sweep_deg=180),name),),origin=(0,0,z),profile_id=name) for radius,z,name in [(r,0,'a'),(r*k,depth,'b')]]
    report=flatten_loft(*profiles,[LoftCorrespondence('a','b',interval,interval)])
    fit=fit_native_loft_boundaries(report)
    rational_whole_parameter_and_global_length(report,fit)
    for side,radius in [('first',r),('second',r*k)]:
        assert abs(length(fit['patches'][0][side])-math.pi*radius)<=fit['boundary_length_error_bound_paper_mm']
    assert fit['serialized_output']=='NOT_VERIFIED' and fit['physical_build']=='NOT_VERIFIED'

def test_global_length_sums_asymmetric_patches_and_rejects_local_only_budget():
    report,*_=synthetic(count=12)
    for i,p in enumerate(report['patches']):
        if i%2==0:p['flat_second_paper_mm']=[[x,0.5] for x,y in p['flat_second_paper_mm']]
        else:p['flat_first_paper_mm']=[[x,0.] for x,y in p['flat_first_paper_mm']]
    fit=fit_native_loft_boundaries(report,position_budget_mm=.1,length_budget_mm=.1)
    rational_whole_parameter_and_global_length(report,fit)
    local=max(s['length_excess_bound_paper_mm'] for p in fit['patches'] for side in ['first','second'] for s in p[side]['segments'])
    total=max(fit['native_boundary_length_excess_bound_paper_mm'].values());assert total>3*local
    budget=report['boundary_length_error_bound_paper_mm']+(local+total)/2
    refused=fit_native_loft_boundaries(report,position_budget_mm=.1,length_budget_mm=budget)
    assert refused['status']=='UNRESOLVED' and refused['boundary_length_error_bound_paper_mm']>budget

def test_reverse_source_controls_and_closed_loop_whole_geometry():
    report,*_=synthetic();p=report['patches'][0];p['second_parameter_interval']=[1,0]
    for row in p['source_parameters']:row[1]=1-row[1]
    fit=fit_native_loft_boundaries(report,position_budget_mm=.1,length_budget_mm=.1);rational_whole_parameter_and_global_length(report,fit)
    patch=fit['patches'][0];count=len(patch['first']['segments'])
    for original,reversed_s in zip(reversed(patch['second']['segments']),patch['closed_boundary_segments'][count+1:-1]):
        assert reversed_s['source']['parameter_interval']==list(reversed(original['source']['parameter_interval']))
        for t in [0,.137,.5,.911,1]:assert math.dist(evaluate(original,1-t),evaluate(reversed_s,t))<1e-15
    assert patch['closed_boundary_commands'][-1]==['Z']

@pytest.mark.parametrize('reverse',[False,True])
def test_true_cubic_source_normal_extrusion_preserves_nonlinear_same_u_with_lines(reverse):
    c=Curve((0,0),(6,0),'cubic',dict(control1=(1,0),control2=(3,0)),'a')
    other=Curve(c.start,c.end,c.kind,dict(c.data),'b')
    profiles=[LoftProfile((c,),profile_id='first'),LoftProfile((other,),origin=(0,0,7),profile_id='second')]
    interval=(1,0) if reverse else (0,1)
    report=flatten_loft(*profiles,[LoftCorrespondence('a','b',interval,interval)])
    fit=fit_native_loft_boundaries(report);rational_whole_parameter_and_global_length(report,fit)
    # Exact source arclength is 3u+3u² forward, 9u-3u² reversed.
    alpha,beta=(Q(9),Q(-3)) if reverse else (Q(3),Q(3))
    for side in ['first','second']:
        boundary=fit['patches'][0][side];assert boundary['representation']=='NATIVE_LINES'
        assert abs(length(boundary)-6)<=fit['boundary_length_error_bound_paper_mm']
        for s in boundary['segments']:
            a,b=map(Q,s['source']['loft_parameter_interval']);x0,x1=Q(s['start'][0]),Q(s['end'][0]);slope=(x1-x0)/(b-a)
            critical=(slope-alpha)/(2*beta)
            points=[a,b]+([critical] if a<critical<b else [])
            actual=max(abs(x0+(u-a)*slope-alpha*u-beta*u*u) for u in points)
            assert actual<=Q(fit['position_error_bound_paper_mm'])

def test_true_pointed_gothic_source_has_global_lengths_and_unsmoothed_corner():
    profiles=[]
    for k,z,name in [(1,0,'a'),(2,3,'b')]:
        top=math.sqrt(3)*k
        curves=(Curve((-k,0),(0,top),'arc',dict(center=(k,0),sweep_deg=-60),name+'-left'),Curve((0,top),(k,0),'arc',dict(center=(-k,0),sweep_deg=-60),name+'-right'),Curve((k,0),(-k,0),segment_id=name+'-base'))
        profiles.append(LoftProfile(curves,origin=(0,0,z),profile_id=name,closed=True))
    report=flatten_loft(*profiles,[LoftCorrespondence(x.segment_id,y.segment_id) for x,y in zip(profiles[0].curves,profiles[1].curves)])
    fit=fit_native_loft_boundaries(report);rational_whole_parameter_and_global_length(report,fit)
    for side,k in [('first',1),('second',2)]:
        actual=sum(length(p[side]) for p in fit['patches'])
        assert abs(actual-k*(4*math.pi/3+2))<=fit['boundary_length_error_bound_paper_mm']
        left,right=[fit['patches'][i][side]['segments'][-1 if i==0 else 0] for i in [0,1]]
        first=[x-y for x,y in zip(left['end'],left['data']['control2'])];second=[x-y for x,y in zip(right['data']['control1'],right['start'])]
        assert abs(first[0]*second[1]-first[1]*second[0])>1e-10
        assert fit['patches'][1]['join_before_kind']=='FOLD_CREASE'
        assert fit['patches'][2][side]['representation']=='NATIVE_LINES'

@pytest.mark.parametrize('damage',['negative_bound','nan_node','zero_interval','wrong_direction','missing_proof','zero_regularity','tight_position','tiny_parameter','fraction_node'])
def test_adversarial_source_refusal_is_pure(damage):
    report,*_=synthetic();options={}
    if damage=='negative_bound':report['boundary_length_error_bound_paper_mm']=-1
    elif damage=='nan_node':report['patches'][0]['flat_first_paper_mm'][1][0]=float('nan')
    elif damage=='zero_interval':report['patches'][0]['parameters'][1]=0
    elif damage=='wrong_direction':report['patches'][0]['source_parameters'][1][0]=.9
    elif damage=='missing_proof':report.pop('proof_scope')
    elif damage=='zero_regularity':report['regularity_lower_bound_paper_mm2']=0
    elif damage=='tight_position':options['position_budget_mm']=1e-30
    elif damage=='fraction_node':report['patches'][0]['flat_first_paper_mm'][1][0]=Q(1,3)
    else:
        report['patches'][0]['parameters']=[0,1e-320,1];report['patches'][0]['source_parameters']=[[0,0],[1e-320,1e-320],[1,1]]
        report['patches'][0]['flat_first_paper_mm']=[[0,0],[1,1],[2,0]];report['patches'][0]['flat_second_paper_mm']=[[0,1],[1,2],[2,1]]
    before=copy.deepcopy(report);fit=fit_native_loft_boundaries(report,**options)
    assert fit['status']=='UNRESOLVED'
    if damage!='nan_node':assert report==before
