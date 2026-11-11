"""Independent exact/analytic oracles for pinned C source-transfer component."""
import copy
import hashlib
import json
import math
import subprocess
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import numpy as np
import pytest
import archpapercraft.authoring.curved_tabs_transfer as actual
from archpapercraft.authoring.curved_tabs import Rim, Tab, Cap, CircularHole, Limits
from archpapercraft.authoring.curved_tabs_chart import certify_native_tab_chart
from archpapercraft.authoring.curved_tabs_transfer import SourceTransferBounds, ReceiverTransferBounds, TabChartBounds, certify_source_transfer, CHART_KIND, ANGULAR_KIND, RECEIVER_KIND

ROOT=Path(__file__).resolve().parents[4]
PIN='f10fa26ad86e232429c7000772d983a2ba9fc4f5'
I2=((1,0),(0,1));I3=((1,0,0),(0,1,0),(0,0,1))
assert Path(actual.__file__).resolve().is_relative_to(ROOT/'src')
assert not subprocess.check_output(['git','diff',PIN,'HEAD','--','src','tests','pyproject.toml'],cwd=ROOT).strip()

def fixture(k=Q(0),r=Q(10),count=12):
    rim=Rim(r,k,'rim-source','body-source')
    tabs=tuple(Tab(f'tab-{i}',Q(2*i+1,2*count),Q(6,25),Q(19,2),Q(3,5),'body-source','cap-source') for i in range(count))
    cap=Cap(r,'cap-source');limits=Limits(Q(1,100),Q(1,100),1,Q(1,5),Q(1,100))
    source=SourceTransferBounds((r,r),(k,k),'rim-source','body-source',('actual-profile1','actual-profile2','actual-shell'),'a'*64,'b'*64,I2,0,I3,0,0,CHART_KIND,ANGULAR_KIND,world_frame_position_error_mm=0)
    receiver=ReceiverTransferBounds('cap-source',('actual-cap-profile',),'c'*64,RECEIVER_KIND)
    return [rim,tabs,cap,limits,source,receiver]

def independent_packet(rim,tab,A=I2,tr=(0,0),rounded=False):
    r,k,b=map(Q,[rim.radius_mm,rim.radial_slope,tab.nominal_base_mm]);q=k*b/(4*r)
    x=b/(2*(1+q*q));y=-2*(r/k)*q*q/(1+q*q) if k else Q(0)
    def point(v):
        p=tuple(sum(Q(A[i][j])*Q(v[j]) for j in range(2))+Q(tr[i]) for i in range(2))
        return tuple(map(float,p)) if rounded else p
    a=point((-x,y));z=point((x,y));apex=point((tab.tip_offset_mm,tab.depth_mm));det=Q(A[0][0])*Q(A[1][1])-Q(A[0][1])*Q(A[1][0])
    radius=abs(r/k) if k else None
    if rounded and radius is not None:radius=float(radius)
    command=('A',radius,radius,0,0,int(k<0) if det>0 else int(k>=0),*z) if k else ('L',*z)
    return (('M',*a),command),apex

def chart(args,tab,commands,apex,A=I2,tr=(0,0),digest='a'*64):
    return certify_native_tab_chart(args[0],tab,commands,apex,A,tr,source_ids=('actual-shell','rim-source',tab.tab_id),source_digest=digest)

def independent_jacobian(r,k,x,y,relief,phase,rs,ks):
    # Direct differentiation of the stated material map, no production helper.
    square=math.sqrt(1-(k*x/r)**2)
    f=-k*x*x/r/(1+square) if k else 0
    fp=-k*x/(r*square);theta=math.asin(k*x/r)/k if k else x/r
    tp=1/(r*square)
    if y<relief:
        alpha=(relief-y)/(relief-f);ax=(relief-y)*fp/(relief-f)**2;ay=-1/(relief-f)
    else:alpha=ax=ay=0
    rt=np.array([math.cos(theta),math.sin(theta),0.]);tt=np.array([-math.sin(theta),math.cos(theta),0.]);r0=np.array([1.,0,0]);t0=np.array([0.,1,0])
    angle=phase*math.pi+(1-phase)*math.acos(ks);d=np.array([math.cos(angle),0,math.sin(angle)])
    dx=rs*(ax*(rt-r0)+alpha*tp*tt)+(1-alpha-x*ax)*t0+(-ax*f-alpha*fp)*d
    dy=rs*ay*(rt-r0)-x*ay*t0+(1-ay*f)*d
    return np.stack([dx,dy],axis=1)

@pytest.mark.parametrize('k',[Q(0),Q(1,3),Q(-1,3),Q(1,10**18),Q(-1,10**18)])
def test_independent_full_phase_jacobian_and_strain_crosschecks(k):
    args=fixture(k);rn=Q(args[0].radius_mm);dr=Q(1,10**5);dk=Q(1,10**6)
    args[4]=replace(args[4],radius_bounds_mm=(rn+dr,rn+dr),radial_slope_bounds=(k+dk,k+dk))
    result=certify_source_transfer(*args);row=result['tabs'][0];bound=float(row['source_jacobian_delta_operator_bound']);strain=float(row['source_differential_deformation_total_bound'])
    for x in [-.113719,-.04031,0,.071823,.110735]:
        for y in [.013471,.290137,.599371,.600137,4.12731]:
            for phase in [0,.137197,.538971,.993713,1]:
                a=independent_jacobian(float(rn),float(k),x,y,.6,phase,float(rn),float(k))
                b=independent_jacobian(float(rn),float(k),x,y,.6,phase,float(rn+dr),float(k+dk))
                assert np.linalg.norm(b-a,ord=2)<=bound+1e-12
                singular=np.linalg.svd(b,compute_uv=False)
                assert max(abs(singular-1))<=strain+1e-12
    # At x=0,y=relief/2 the source x-column is exactly (1+dr/(2R))*tangent.
    assert row['source_jacobian_delta_column_bounds'][0]>=dr/(2*rn)

@pytest.mark.parametrize('slope',[Q(1,3),Q(-1,3)])
def test_actual_binary_height_not_native_slant_all12_A_and_metric_pose(slope):
    args=fixture(slope,10 if slope<0 else 20);r=Q(args[0].radius_mm)
    h=Q(math.sqrt(800));square=100+h*h;scale=10**90
    root=math.isqrt(square.numerator*scale*scale//square.denominator);sl=(Q(root,scale),Q(root+1,scale))
    ks=tuple(sorted(10*(1 if slope>0 else -1)/s for s in sl));assert not ks[0]<=slope<=ks[1]
    with localcontext() as c:
        c.prec=100;v=Decimal(10 if slope>0 else -10)/(Decimal(square.numerator)/Decimal(square.denominator)).sqrt()
        assert Decimal(ks[0].numerator)/Decimal(ks[0].denominator)<=v<=Decimal(ks[1].numerator)/Decimal(ks[1].denominator)
    charts=[]
    for tab in args[1]:
        theta=2*math.pi*float(tab.center_turn)/3;A=((math.cos(theta),-math.sin(theta)),(math.sin(theta),math.cos(theta)))
        cmds,apex=independent_packet(args[0],tab,A,(Q(1001,8),Q(-311,4)),True);c=chart(args,tab,cmds,apex,A,(Q(1001,8),Q(-311,4)))
        assert c['status']=='CERTIFIED_NATIVE_CHART'
        charts.append(TabChartBounds(tab.tab_id,c['paper_chart_matrix'],c['paper_chart_derivative_remainder'],c['native_chart_position_error_mm'],c['native_chart_digest']))
    theta=.731337;world=((math.cos(theta),0,math.sin(theta)),(0,1,0),(-math.sin(theta),0,math.cos(theta)))
    rr=Q(int(r)*100)*Q(.01)
    args[4]=replace(args[4],radius_bounds_mm=(rr,rr),radial_slope_bounds=ks,tab_charts=tuple(charts),world_frame_matrix=world,world_frame_operator_remainder=Q(1,10**18),world_frame_position_error_mm=Q(1,10**18))
    args[5]=replace(args[5],radius_error_mm=abs(rr-r))
    before=copy.deepcopy(args);result=certify_source_transfer(*args)
    assert result['status']=='CERTIFIED_TRANSFER' and len(result['pairs'])==66
    assert result['source_differential_deformation_total_bound']<Q(1,100) and result['source_position_total_bound']<Q(1,100)
    assert min(row['source_actual_glue_area_bounds_mm2'][0] for row in result['tabs'])>=1 and args==before

@pytest.mark.parametrize('epsilon',[Q(1,1000),Q(-1,1000),Q(1,10**20)])
def test_affine_cylinder_shear_has_exact_whole_material_derivative(epsilon):
    args=fixture();tab=args[1][0];cmd,apex=independent_packet(args[0],tab)
    result=chart(args,tab,cmd,(apex[0]+epsilon,apex[1]));assert result['status']=='CERTIFIED_NATIVE_CHART'
    assert result['paper_chart_derivative_remainder']>=abs(epsilon/Q(tab.depth_mm))
    assert result['native_chart_position_error_mm']==abs(epsilon)

def test_known_source_strain_violation_at_analytic_centerline_is_not_certified():
    args=fixture(Q(1,3));args[4]=replace(args[4],radius_bounds_mm=(Q(21,2),Q(21,2)))
    result=certify_source_transfer(*args);assert result['status']=='UNRESOLVED'
    # Actual singular value at x=0,y=.3 is 1+.5/(2*10)=1.025.
    assert result['tabs'][0]['source_differential_deformation_total_bound']>=Q(1,40)
    assert any(p[0]=='SOURCE_STRAIN_BUDGET' for p in result['problems'])

@pytest.mark.parametrize('field,matrix',[('paper_chart_matrix',((Q(101,100),0),(0,1))),('world_frame_matrix',((Q(102,100),0,0),(0,1,0),(0,0,1)))])
def test_zero_position_reserve_cannot_hide_metric_change(field,matrix):
    args=fixture();args[4]=replace(args[4],**{field:matrix})
    result=certify_source_transfer(*args);assert result['status']=='UNRESOLVED'
    assert any(p[0]=='SOURCE_STRAIN_BUDGET' for p in result['problems'])

def test_exact_final_contact_area_12_tabs_and_receiver_hole_negative():
    args=fixture();result=certify_source_transfer(*args);assert result['status']=='CERTIFIED_TRANSFER'
    # Independent flat triangle at y=.6 has width .24*(9.5-.6)/9.5 and height8.9.
    area=Q(6,25)*(Q(19,2)-Q(3,5))**2/(2*Q(19,2))
    assert area>1
    for row in result['tabs']:assert row['source_actual_glue_area_bounds_mm2']==(area,area)
    tab=replace(args[1][0],center_turn=Q(1,4));args[1]=(tab,)
    args[2]=replace(args[2],holes=(CircularHole(0,Q(193,30),Q(1,10)),))
    args[5]=replace(args[5],hole_radius_errors_mm=(0,),hole_center_errors_mm=(0,))
    bad=certify_source_transfer(*args,max_cells=1000)
    assert bad['status']=='UNRESOLVED' and bad['native_status']=='INVALID'
    assert bad['tabs'][0]['source_actual_glue_area_bounds_mm2'][0]<area

def test_unknown_does_not_erase_exact_coincident_source_negative():
    args=fixture();args[1]=(args[1][0],replace(args[1][1],center_turn=args[1][0].center_turn))
    a=certify_source_transfer(*args);b=certify_source_transfer(*args,unresolved_obstacle_ids=('unrelated-wall',))
    assert a['source_negative_witnesses']==b['source_negative_witnesses'] and a['source_negative_witnesses'][0]['area_lower_mm2']>1
    assert a['native_status']==b['native_status']=='INVALID'

@pytest.mark.parametrize('change',['source','native-chart','receiver','apex','base'])
def test_changed_current_data_recomputed_not_mutated_report_or_revision_shortcut(change):
    args=fixture();tab=args[1][0];cmd,apex=independent_packet(args[0],tab);a=chart(args,tab,cmd,apex)
    a['native_chart_position_error_mm']=Q(-100);a['paper_chart_matrix']=((0,0),(0,0))
    b=chart(args,tab,cmd,apex);assert b['native_chart_position_error_mm']==0 and b['paper_chart_matrix']==I2
    if change=='source':
        changed=chart(args,tab,cmd,apex,digest='d'*64);assert changed['native_chart_digest']!=b['native_chart_digest']
    elif change=='apex':
        changed=chart(args,tab,cmd,(Q(1,100),apex[1]));assert changed['native_chart_digest']!=b['native_chart_digest']
    elif change=='base':
        altered=(cmd[0],('L',cmd[1][1]+Q(1,1000),cmd[1][2]));changed=chart(args,tab,altered,apex);assert changed['native_chart_digest']!=b['native_chart_digest']
    else:
        args[4]=replace(args[4],native_chart_digest='') if change=='native-chart' else args[4]
        args[5]=replace(args[5],source_digest='') if change=='receiver' else args[5]
        assert certify_source_transfer(*args)['status']=='UNRESOLVED'

@pytest.mark.parametrize('kwargs',[{'max_cells':0},{'max_depth':0,'max_cells':1},{'max_pairs':0}])
def test_no_partial_certification_when_budget_missing(kwargs):
    args=fixture();result=certify_source_transfer(*args,**kwargs)
    assert result['status']=='UNRESOLVED' and result['total_cells_used']<=2*kwargs.get('max_cells',10000)

@pytest.mark.parametrize('case',['collapsed','reversed','position-only','pose-only','hole-missing','missing-proof'])
def test_unsupported_or_missing_proof_does_not_become_transfer(case):
    args=fixture(Q(1,3));tab=args[1][0];cmd,apex=independent_packet(args[0],tab)
    if case in ['collapsed','reversed']:
        if case=='collapsed':apex=cmd[0][1:]
        else:cmd=(cmd[0],tuple([*cmd[1][:5],1-cmd[1][5],*cmd[1][6:]]))
        assert chart(args,tab,cmd,apex)['status']=='UNRESOLVED';return
    if case=='position-only':args[4]=replace(args[4],paper_chart_derivative_remainder=None,native_chart_position_error_mm=0)
    elif case=='pose-only':args[4]=replace(args[4],world_frame_operator_remainder=None,world_frame_position_error_mm=0)
    elif case=='hole-missing':args[2]=replace(args[2],holes=(CircularHole(0,0,1),))
    else:args[4]=None
    assert certify_source_transfer(*args)['status']=='UNRESOLVED'

def test_source_manifest():
    files=['src/archpapercraft/authoring/curved_tabs_transfer.py','src/archpapercraft/authoring/curved_tabs_chart.py','src/archpapercraft/authoring/curved_tabs.py']
    hashes={}
    for rel in files:
        raw=(ROOT/rel).read_bytes();pinned=subprocess.check_output(['git','show',PIN+':'+rel],cwd=ROOT)
        assert raw.replace(b'\r\n',b'\n')==pinned.replace(b'\r\n',b'\n')
        hashes[rel]={'actual_sha256':hashlib.sha256(raw).hexdigest(),'git_blob_sha256':hashlib.sha256(pinned).hexdigest()}
    assert not subprocess.check_output(['git','diff','d26c4c16ea259c55bdbedd0472a3faebaf5b8286',PIN,'--','src/archpapercraft/authoring/curved_tabs.py'],cwd=ROOT).strip()
    out={'source_sha':PIN,'actual_module':actual.__file__,'files':hashes,'independent_expected':'direct analytic Jacobian, exact cylinder shear/triangle, independent integer-sqrt bounds for actual binary H, no production geometry helper for expected','proof_scope':'conditional pure math only, binder/native body union/world source registry/export/UI/novice/physical NOT_PROVED'}
    (ROOT/'docs/p2/implementation/evidence/pc007b-source-transfer-review-source.json').write_text(json.dumps(out,indent=2),encoding='utf-8')


@pytest.mark.parametrize('k,reflection',[(Q(1,3),False),(Q(-1,3),False),(Q(1,3),True),(Q(-1,3),True)])
def test_actual_A_rational_parameter_whole_fan_derivative_independent_crosscheck(k,reflection):
    args=fixture(k);tab=args[1][0]
    A=((Q(3,5),Q(-4,5)),(Q(4,5),Q(3,5)))
    if reflection:A=(A[0],tuple(-v for v in A[1]))
    tr=(Q(1231,10),Q(-732,10));cmd,apex=independent_packet(args[0],tab,A,tr,True)
    apex=(Q(apex[0])+Q(1,10**7),Q(apex[1])-Q(1,10**8))
    bound=chart(args,tab,cmd,apex,A,tr);assert bound['status']=='CERTIFIED_NATIVE_CHART'
    # Independent circle-center/tangent-intersection rational conic. No use of
    # production _endpoint_arc_node or chart's homogeneous hull expectations.
    with localcontext() as ctx:
        ctx.prec=100
        def d(q):q=Q(q);return Decimal(q.numerator)/Decimal(q.denominator)
        r,b,kk=map(d,[10,Q(6,25),k]);q=kk*b/(4*r)
        x=b/(2*(1+q*q));f=-2*(r/kk)*q*q/(1+q*q);w=(1-q*q)/(1+q*q)
        reference=[[-x,f,Decimal(1)],[Decimal(0),w*f+x*x/(r/kk),w],[x,f,Decimal(1)]]
        P=list(map(d,cmd[0][1:]));T=list(map(d,cmd[1][-2:]));radius=d(cmd[1][1])
        dx,dy=(P[0]-T[0])/2,(P[1]-T[1])/2;dd=dx*dx+dy*dy
        sign=-1 if cmd[1][5]==0 else 1
        factor=sign*((radius*radius-dd)/dd).sqrt()
        center=[(P[0]+T[0])/2+factor*dy,(P[1]+T[1])/2-factor*dx]
        wa=(1-dd/(radius*radius)).sqrt();middle=[(P[i]+T[i])/2 for i in range(2)]
        actual_h=[[*P,Decimal(1)],[*(wa*center[i]+(middle[i]-center[i])/wa for i in range(2)),wa],[*T,Decimal(1)]]
        def evaluate(h,t):
            n=[(1-t)**2*h[0][i]+2*t*(1-t)*h[1][i]+t*t*h[2][i] for i in range(3)]
            p=[2*(1-t)*(h[1][i]-h[0][i])+2*t*(h[2][i]-h[1][i]) for i in range(3)]
            return [n[i]/n[2] for i in range(2)],[(p[i]*n[2]-n[i]*p[2])/(n[2]*n[2]) for i in range(2)]
        Qn=list(map(d,[0,tab.depth_mm]));Qa=list(map(d,apex));Ad=[[d(v) for v in row]for row in A]
        max_operator=0.;max_base=0.
        for t in [Decimal(0),Decimal(1)/13,Decimal(71)/223,Decimal(333)/997,Decimal(1)]:
            B,Bp=evaluate(reference,t);C,Cp=evaluate(actual_h,t)
            predicted=[sum(Ad[i][j]*B[j] for j in range(2))+d(tr[i]) for i in range(2)]
            max_base=max(max_base,float(sum((C[i]-predicted[i])**2 for i in range(2)).sqrt()))
            for lam in [Decimal(1),Decimal(19)/37,Decimal(1)/10**12]:
                J=[[B[0]-Qn[0],lam*Bp[0]],[B[1]-Qn[1],lam*Bp[1]]]
                K=[[C[0]-Qa[0],lam*Cp[0]],[C[1]-Qa[1],lam*Cp[1]]]
                det=J[0][0]*J[1][1]-J[0][1]*J[1][0]
                inv=[[J[1][1]/det,-J[0][1]/det],[-J[1][0]/det,J[0][0]/det]]
                delta=np.array([[float(sum(K[i][s]*inv[s][j] for s in range(2))-Ad[i][j]) for j in range(2)] for i in range(2)])
                max_operator=max(max_operator,np.linalg.norm(delta,ord=2))
        assert max_base<=float(bound['base_position_error_bound_mm'])*(1+1e-10)+1e-90
        assert max_operator<=float(bound['paper_chart_derivative_remainder'])*(1+1e-10)
