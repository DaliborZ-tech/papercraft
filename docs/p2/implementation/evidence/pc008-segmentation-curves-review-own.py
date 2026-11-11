"""Independent rational whole-cell and analytic source oracles; pure math only."""
from dataclasses import replace
from decimal import Decimal,localcontext
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.loft_geometry import LoftProfile,LoftCorrespondence
from archpapercraft.authoring.segmented_loft import segment_ruled_loft
from archpapercraft.authoring import segmented_loft_curves as actual

HERE=Path(__file__).parent
assert Path(actual.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())
PI=Q('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')


def roots(value):
    q=Q(value);n=math.isqrt((q.numerator<<480)//q.denominator);return Q(n,1<<240),Q(n+1,1<<240)
def norm(v):return roots(sum(x*x for x in v))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def refs(a,b,reverse=False):
    pairs=list(zip(a.curves,b.curves));pairs=pairs[::-1] if reverse else pairs;interval=(1,0) if reverse else (0,1)
    return tuple(LoftCorrespondence(x.segment_id,y.segment_id,interval,interval) for x,y in pairs)
def certified(r):
    assert r['status']=='CERTIFIED',r
    assert r['mode']=='APPROXIMATE' and r['global_embedding']=='NOT_CHECKED' and r['source_area_distortion']=='NOT_CERTIFIED_BY_THIS_COMPONENT'
    assert r['max_surface_deviation_paper_mm']<=r['requested_deviation_budget_paper_mm']
    for f in ['max_surface_deviation_paper_mm','max_surface_deviation_model_mm','max_normal_angle_bound_deg']:
        assert Q(r[f])>=Q(r[f+'_exact'])
    assert 0<Q(r['regularity_lower_paper_mm2'])<=Q(r['regularity_lower_paper_mm2_exact'])
    assert r['examined_cells']<2*max(1,r['counts']['cells'])
    json.dumps(r,allow_nan=False);return r


def parabola(other=False,reverse=False,scale=1):
    c=Curve((0,0),(6,6),'cubic',{'control1':(2,0),'control2':(4,2)},'a0')
    d=Curve((0,0),(9,6),'cubic',{'control1':(3,0),'control2':(6,1)},'b0') if other else replace(c,segment_id='b0')
    a=LoftProfile((c,),profile_id='a');b=LoftProfile((d,),profile_id='b',origin=(0,0,5))
    return a,b,certified(segment_ruled_loft(a,b,refs(a,b,reverse),scale=scale))


def test_actual_import_hashes_and_source_json_are_pinned():
    out={}
    for name in ['segmented_loft','segmented_loft_curves','loft_area','curve_area']:
        m=__import__('archpapercraft.authoring.'+name,fromlist=['x']);p=Path(m.__file__).resolve();assert p.is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve());out[name]={'module_path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    (HERE/'pc008-segmentation-curves-review-imports.json').write_text(json.dumps(out,indent=2),encoding='utf8')


@pytest.mark.parametrize('reverse',[False,True])
def test_parabola_whole_triangle_deviation_and_perimeter_have_analytic_oracle(reverse):
    a,b,r=parabola(reverse=reverse)
    for tri in r['triangles']:
        uv=[[Q(x) for x in p] for p in tri['parameter_vertices_exact']];us=[p[0] for p in uv];h=max(us)-min(us)
        # F=(6u,6u²,5v); linear interpolation error=(0,6(u-u0)(u-u1),0).
        # This is its WHOLE-triangle maximum, attained at the middle ruling.
        assert Q(tri['source_interpolation_bound_model_mm_exact'])>=Q(3,2)*h*h
        assert Q(tri['position_error_bound_paper_mm_exact'])>=Q(3,2)*h*h
        for point,actual_uv in zip(tri['world_vertices_model_mm'],uv):
            u,v=actual_uv;t=1-u if reverse else u
            assert list(map(Q,point))==[6*t,6*t*t,5*v]
    with localcontext() as c:
        c.prec=90;root=Decimal(5).sqrt();expected=6*root+3*(2+root).ln()+10;err=Decimal('1e-70')
        lo,hi=Q(expected-err),Q(expected+err)
    lengths=r['lengths'];assert Q(lengths['source_boundary_lower_paper_mm_exact'])<=lo<=hi<=Q(lengths['source_boundary_upper_paper_mm_exact'])


def bernstein(coeff,start,end):
    n=len(coeff)-1;h=end-start
    power=[sum(coeff[i]*math.comb(i,j)*start**(i-j)*h**j for i in range(j,n+1)) for j in range(n+1)]
    return [sum(power[j]*Q(math.comb(k,j),math.comb(n,j)) for j in range(k+1)) for k in range(n+1)]


def tangent_lower(angle):
    # Independent Decimal Taylor, generous rounding reserve; used only with
    # the small positive regional angles of this explicit polynomial fixture.
    with localcontext() as c:
        c.prec=90;x=Decimal(angle.numerator)/angle.denominator*Decimal(PI.numerator)/PI.denominator/180
        assert 0<x<Decimal('1.2')
        sine=cosine=Decimal(0)
        for i in range(70):
            sine+=(-1 if i%2 else 1)*x**(2*i+1)/math.factorial(2*i+1)
            cosine+=(-1 if i%2 else 1)*x**(2*i)/math.factorial(2*i)
        return Q(sine/cosine-Decimal('1e-70'))


def test_nondevelopable_two_cubics_global_normal_and_regularity_use_independent_bernstein_hull():
    a,b,r=parabola(other=True)
    # F=(6u+3uv,6u²+v(-3u²+3u³),5v). Exact determinant at u=.5 is112.5.
    assert dot((6,6,0),cross((Q(3,2),Q(-3,8),5),(3,Q(-3,4),0)))==Q(225,2)
    for tri in r['triangles']:
        uv=[[Q(x) for x in p] for p in tri['parameter_vertices_exact']];u0,u1=min(p[0] for p in uv),max(p[0] for p in uv);v0,v1=min(p[1] for p in uv),max(p[1] for p in uv)
        points=[tuple(map(Q,p)) for p in tri['world_vertices_model_mm']];k=cross(sub(points[1],points[0]),sub(points[2],points[0]));ku=norm(k)[1]
        # J exact power coefficients, restricted independently to actual cell.
        controls=[]
        for v in [v0,v1]:
            polys=[[0,60-30*v,45*v,0],[-30-15*v,0,0,0],[0,0,-54+9*v,18-18*v]]
            bc=[bernstein(p,u0,u1) for p in polys];controls += list(zip(*bc))
        minimum=min(dot(j,k) for j in controls);assert minimum>0
        assert Q(tri['regularity_lower_paper_mm2_exact'])<=minimum/ku
        numerator=max(norm(cross(j,k))[1] for j in controls)
        angle=Q(tri['normal_angle_bound_deg_exact'])
        assert numerator/minimum<=tangent_lower(angle)
        # Independent rational barycentric interior sanity check supplements
        # the WHOLE-cell hull proof; samples are not the positive certificate.
        for weights in [(Q(1,3),)*3,(Q(1,2),Q(1,4),Q(1,4))]:
            u,v=[sum(w*p[i] for w,p in zip(weights,uv)) for i in (0,1)]
            f=(6*u+3*u*v,6*u*u+v*(-3*u*u+3*u**3),5*v);delivered=[sum(w*p[i] for w,p in zip(weights,points)) for i in range(3)];diff=sub(f,delivered);bound=Q(tri['position_error_bound_paper_mm_exact'])
            assert dot(diff,diff)<=bound*bound
    (HERE/'pc008-segmentation-curves-review-polynomial-report.json').write_text(json.dumps({'source_sha':'3a0355f42a6ef5bc710ce3bd85c6280bf7cf39fe','manual_source':'C0=(6u,6u²,0), C1=(9u,3u²+3u³,5)','independent_whole_cell_jacobian_hull':'PASS for every actual triangle cell','nondevelopability_determinant_at_half_exact':'225/2','result':r},indent=2),encoding='utf8')


@pytest.mark.parametrize('orientation',[(0,1),(1,0)])
@pytest.mark.parametrize('derivative',[0,1,2])
def test_exact_restricted_cubic_bounds_include_independently_derived_extrema(orientation,derivative):
    a,b,r=parabola();source=actual._SourceCurve(a,a.curves[0],orientation);lo,hi=Q(1,5),Q(4,5);bound=source.bounds(lo,hi,derivative)
    ts=[Q(orientation[0])+(orientation[1]-orientation[0])*u for u in (lo,hi)];change=orientation[1]-orientation[0]
    points=[(6*t,6*t*t,0) if derivative==0 else (6*change,12*t*change,0) if derivative==1 else (0,12,0) for t in ts]
    for axis in range(3):assert bound[axis][0]<=min(p[axis] for p in points)<=max(p[axis] for p in points)<=bound[axis][1]


@pytest.mark.parametrize('factor',[1,1+2**-42,1-2**-42])
@pytest.mark.parametrize('reverse',[False,True])
def test_actual_circle_gram_speed_perimeter_and_entire_normal_angle(factor,reverse):
    c=Curve((4,0),(0,4),'arc',{'center':(0,0),'sweep_deg':90},'a0');a=LoftProfile((c,),profile_id='a',u=(factor,0,0),v=(0,factor,0));b=replace(a,curves=(replace(c,segment_id='b0'),),profile_id='b',origin=(0,0,6))
    r=certified(segment_ruled_loft(a,b,refs(a,b,reverse),scale=1));expected_lo=4*PI*Q(factor)+12;expected_hi=4*(PI+Q(1,10**100))*Q(factor)+12;lengths=r['lengths'];lo,hi=Q(lengths['source_boundary_lower_paper_mm_exact']),Q(lengths['source_boundary_upper_paper_mm_exact']);assert lo<=expected_lo<=expected_hi<=hi
    if factor>1:assert lo>4*(PI+Q(1,10**100))+12
    if factor<1:assert hi<4*PI+12
    for tri in r['triangles']:
        us=[Q(p[0]) for p in tri['parameter_vertices_exact']];h=max(us)-min(us)
        # Circle-extrusion triangle normals point at angular midpoint. Entire
        # source normal cone's exact endpoint angle is90*h/2 degrees.
        assert Q(tri['normal_angle_bound_deg_exact'])>=45*h
        assert Q(tri['source_interpolation_bound_model_mm_exact'])>=Q(factor)*PI**2*h*h/8


@pytest.mark.parametrize('target',['cubic_2_5','arc_2_7'])
def test_nondyadic_singularities_are_unresolved_even_with_large_position_budget(target):
    if target=='cubic_2_5':
        c=Curve((0,0),(7,0),'cubic',{'control1':(4,0),'control2':(-2,0)},'a0');a=LoftProfile((c,),profile_id='a');b=replace(a,curves=(replace(c,segment_id='b0'),),profile_id='b',origin=(0,0,5))
        # x'=3(5u-2)² has an exact zero not present at any dyadic vertex.
        assert 75*Q(2,5)**2-60*Q(2,5)+12==0
    else:
        c=Curve((4,0),(-4,0),'arc',{'center':(0,0),'sweep_deg':180},'a0');d=Curve((10,0),(-10,0),'arc',{'center':(0,0),'sweep_deg':180},'b0');a=LoftProfile((c,),profile_id='a');b=LoftProfile((d,),profile_id='b',u=(-1,0,0),v=(0,-1,0))
        assert 1-Q(7,2)*Q(2,7)==0
    r=segment_ruled_loft(a,b,refs(a,b),scale=1,max_deviation_mm=100,max_cells=256,max_depth=8)
    assert r['status']=='UNRESOLVED' and 'triangles' not in r and 'edges' not in r


def test_endpoint_gap_is_actual_vertex_reservation_not_an_exact_circle_identity():
    sweep=.01;r=.001;omega=math.radians(sweep);end=(r*math.cos(omega)+9e-8,r*math.sin(omega));c=Curve((r,0),end,'arc',{'center':(0,0),'sweep_deg':sweep},'a0');a=LoftProfile((c,),profile_id='a');b=replace(a,curves=(replace(c,segment_id='b0'),),profile_id='b',origin=(0,0,1));pair=refs(a,b,True)
    loose=certified(segment_ruled_loft(a,b,pair,scale=1,max_deviation_mm=1e-5,max_cells=32,max_depth=5));assert loose['numerical_vertex_error_bound_model_mm']>=8.999e-8
    tight=segment_ruled_loft(a,b,pair,scale=1,max_deviation_mm=1e-9,max_cells=32,max_depth=5);assert tight['status']=='UNRESOLVED' and 'triangles' not in tight


@pytest.mark.parametrize('options',[{'max_cells':1},{'max_depth':0},{'max_deviation_mm':1e-25},{'max_cells':True},{'scale':False}])
def test_explicit_caps_fail_without_partial_mesh(options):
    a,b,_=parabola(other=True);out=segment_ruled_loft(a,b,refs(a,b),**{'scale':1,**options});assert out['status']=='UNRESOLVED' and 'triangles' not in out and 'edges' not in out


def test_large_world_rounding_reserve_cannot_hide_beneath_small_budget():
    a,b,r=parabola();a=replace(a,origin=(2**60,0,0));b=replace(b,origin=(2**60,0,5));r=segment_ruled_loft(a,b,refs(a,b),scale=1,max_cells=64,max_depth=6);assert r['status']=='UNRESOLVED' and 'triangles' not in r


def test_rational_parameter_triangle_coverage_and_detached_result():
    a,b,r=parabola(other=True);before=json.dumps(r,sort_keys=True);area=Q(0)
    for t in r['triangles']:
        p,q,s=[[Q(x) for x in u] for u in t['parameter_vertices_exact']];signed=((q[0]-p[0])*(s[1]-p[1])-(q[1]-p[1])*(s[0]-p[0]))/2;assert signed>0;area+=signed
    assert area==1 and all(len(e['uses']) in (1,2) for e in r['edges'])
    r['source']['first_profile_id']='poison';r['triangles'][0]['world_vertices_model_mm'][0][0]=123
    fresh=segment_ruled_loft(a,b,refs(a,b),scale=1);assert json.dumps(fresh,sort_keys=True)==before


def test_model_and_paper_bounds_apply_scale_once_and_jacobian_scale_squared():
    a,b,base=parabola(other=True);small=certified(segment_ruled_loft(a,b,refs(a,b),scale=.125,max_deviation_mm=.25*.125))
    assert base['subdivisions']==small['subdivisions'] and base['counts']==small['counts']
    assert abs(Q(small['max_surface_deviation_paper_mm_exact'])-Q(small['max_surface_deviation_model_mm_exact'])/8)<Q(2,10**24)
    assert abs(Q(small['regularity_lower_paper_mm2_exact'])-Q(base['regularity_lower_paper_mm2_exact'])/64)<Q(2,10**24)
    assert [t['world_vertices_model_mm'] for t in base['triangles']]==[t['world_vertices_model_mm'] for t in small['triangles']]


@pytest.mark.parametrize('damage',['partial','duplicate','missing','identity'])
def test_curved_source_refs_never_get_nearest_or_incomplete_provenance(damage):
    a,b,r=parabola();reference=refs(a,b)
    if damage=='partial':reference=(replace(reference[0],first_interval=(Q(1,5),Q(4,5))),)
    elif damage=='duplicate':reference=reference*2
    elif damage=='missing':reference=(replace(reference[0],second_segment_id='missing'),)
    else:b=replace(b,profile_id=a.profile_id)
    out=segment_ruled_loft(a,b,reference,scale=1);assert out['status']=='UNRESOLVED' and 'triangles' not in out and out['examined_cells']==0
