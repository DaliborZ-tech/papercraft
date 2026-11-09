"""Independent analytic clearance oracles; expected values use no kernel helper."""
import argparse
from dataclasses import asdict,replace
import json
import math
from pathlib import Path
import sys
import time
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--sha',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.source/'src'))
from archpapercraft.authoring.clearance import ContactAllowance,FoldSweep,MaterialObstacle,MaterialProfile,check_fold_clearance
import archpapercraft.authoring.clearance as kernel
assert Path(kernel.__file__).resolve().is_relative_to(a.source.resolve())
def quad(a,b,c,d):return [[a,b,c],[a,c,d]]
def box(x,y,z):return [[a,b,c] for a in x for b in y for c in z]
def scene(static=True):
    s=FoldSweep([[[0,0,0],[10,0,0],[10,0,-5],[0,0,-5]]],[0,0,0],[10,0,0],0 if static else -90,'source','receiver',[0,1,0],[0,1,0] if static else [0,0,-1])
    m=MaterialProfile(.2 if static else .001)
    src=MaterialObstacle('source',quad([0,0,0],[10,0,0],[10,0,10],[0,0,10]),m.thickness_mm)
    rec=MaterialObstacle('receiver',quad([-10,0,-20],[20,0,-20],[20,0,0],[-10,0,0]) if static else quad([-10,-10,0],[20,-10,0],[20,10,0],[-10,10,0]),m.thickness_mm)
    permits=[ContactAllowance('source','hinge',box([-.5,10.5],[-.5,.5],[-.5,.5]),(0,0) if static else (-90,0),'explicit finite source crease')]
    if static:permits+=[ContactAllowance('receiver','final_contact',box([-.5,10.5],[-.25,.25],[-5.5,.5]),(0,0),'actual flat contact')]
    else:permits += [ContactAllowance('receiver','hinge',box([-.1,10.1],[-.1,.1],[-.1,.1]),(-90,0),'finite receiver crease'),ContactAllowance('receiver','final_contact',box([-.1,10.1],[-5.1,.1],[-.01,.01]),(-90,-45),'finite terminal glue patch')]
    return s,m,[src,rec],permits
rows=[]
def run(name,s,m,obs,permits,expected,**kw):
    start=time.perf_counter();r=check_fold_clearance(s,m,obs,expected_obstacle_ids=[o.id for o in obs],allowances=permits,**kw)
    rows.append(dict(name=name,expected=expected,passed=r.status in expected,result=asdict(r),seconds=time.perf_counter()-start));return r
s,m,obs,permits=scene()
run('static-positive-real-one-interval',s,m,obs,permits,['CLEAR'])
block=MaterialObstacle('known-blocker',quad([2,.15,-4],[8,.15,-4],[8,.15,-1],[2,.15,-1]),.2)
far=MaterialObstacle('unrelated-unknown',quad([20,40,-4],[25,40,-4],[25,40,-1],[20,40,-1]),None)
run('K01-known-overlap-0.05mm',s,m,obs+[block],permits,['COLLISION'])
run('K01-same-known-overlap-with-unrelated-unknown',s,m,obs+[block,far],permits,['COLLISION'])
run('unknown-tab-inside-known-one-mm-slab',s,replace(m,thickness_mm=None),obs+[replace(block,thickness_mm=1)],permits,['COLLISION'])
run('known-tab-contains-unknown-midplane',s,m,obs+[replace(block,triangles_world_mm=quad([2,.05,-4],[8,.05,-4],[8,.05,-1],[2,.05,-1]),thickness_mm=None)],permits,['COLLISION'])
run('unknown-free-never-CLEAR',s,replace(m,thickness_mm=None),obs,permits,['UNVERIFIED'])
short=replace(permits[-1],vertices_world_mm=box([-.5,4.9],[-.25,.25],[-5.5,.5]))
run('permission-does-not-remove-unpermitted-half',s,m,obs,[permits[0],short],['COLLISION'])
run('unknown-permission-does-not-remove-unpermitted-half',s,replace(m,thickness_mm=None),obs,[permits[0],short],['COLLISION'])
independent=MaterialObstacle('other',quad([2,0,-4],[8,0,-4],[8,0,-1],[2,0,-1]),.2)
run('third-party-cannot-be-permitted',s,m,obs+[independent],permits+[replace(permits[-1],obstacle_id='other')],['UNRESOLVED'])
# An L has a true absent corner. Full rectangle must collide there; its exact
# material patches must preserve the void instead of filling a bounding hull.
void=MaterialObstacle('in-void',quad([6,0,-4],[8,0,-4],[8,0,-3],[6,0,-3]),.2)
patches=[[[0,0,0],[10,0,0],[10,0,-2],[0,0,-2]],[[0,0,-2],[4,0,-2],[4,0,-5],[0,0,-5]]]
run('rectangle-covers-L-void',s,m,obs+[void],permits,['COLLISION'])
run('exact-concave-patches-keep-void',replace(s,patches_world_mm=patches),m,obs+[void],permits,['CLEAR'])
for shift in [1e4,1e7]:
    delta=np.array([shift,-shift,shift])
    point=lambda v:(np.asarray(v)+delta).tolist()
    sm=replace(s,patches_world_mm=[point(x) for x in s.patches_world_mm],hinge_start_mm=point(s.hinge_start_mm),hinge_end_mm=point(s.hinge_end_mm))
    om=[replace(o,triangles_world_mm=[point(x) for x in o.triangles_world_mm]) for o in obs]
    pm=[replace(t,vertices_world_mm=point(t.vertices_world_mm)) for t in permits]
    run('coordinate-conditioning:'+str(shift),sm,m,om,pm,['CLEAR'] if shift==1e4 else ['UNRESOLVED'])
s,m,obs,permits=scene(False)
phi=math.radians(-23.456789);r=3.;y,z=r*math.sin(phi),-r*math.cos(phi)
thin=MaterialObstacle('independent-thin-between',quad([2,y,z-.003],[8,y,z-.003],[8,y,z+.003],[2,y,z+.003]),.001)
run('thin-nondyadic-between-coarse-samples',s,m,obs+[thin],permits,['UNRESOLVED'],max_depth=0)
run('thin-nondyadic-refined-witness',s,m,obs+[thin],permits,['COLLISION'])
run('thin-unknown-refined-witness',s,replace(m,thickness_mm=None),obs+[replace(thin,thickness_mm=None)],permits,['COLLISION'],max_depth=12,max_intervals=4096)
run('thin-unknown-exhaustion-never-CLEAR',s,replace(m,thickness_mm=None),obs+[replace(thin,thickness_mm=None)],permits,['UNVERIFIED','UNRESOLVED'],max_depth=0,max_intervals=1)
if hasattr(kernel.ClearanceResult,'search_budget_exhausted'):
    limited=run('thin-default-limited-not-an-absence-proof',s,replace(m,thickness_mm=None),obs+[replace(thin,thickness_mm=None)],permits,['UNVERIFIED','UNRESOLVED'])
    rows.append(dict(name='default-budget-metadata',passed=limited.search_interval_limit==128 and limited.search_depth_limit==8 and limited.search_budget_exhausted and limited.certified_intervals==0 and 'NOT been proved' in limited.message and 'bounded' in limited.proof_method,result=asdict(limited)))
    tangent=MaterialObstacle('independent-hinge-tangency',quad([0,0,0],[10,0,0],[10,0,10],[0,0,10]),None)
    for degrees,budget,expected in [(-67.5,2,'COLLISION'),(-78.75,2,'UNVERIFIED'),(-78.75,3,'COLLISION')]:
        ph=math.radians(degrees);yy,zz=3*math.sin(ph),-3*math.cos(ph)
        late=MaterialObstacle('later-proper-crossing',quad([2,yy,zz-.03],[8,yy,zz-.03],[8,yy,zz+.03],[2,yy,zz+.03]),None)
        run('tangent-does-not-starve:'+str(degrees)+':'+str(budget),s,replace(m,thickness_mm=None),obs+[tangent,late],permits,[expected],max_depth=0 if degrees==-67.5 else 8,max_intervals=budget)
    b02=MaterialObstacle('own-B02',quad([2,-2,-2.5],[8,-2,-2.5],[8,-2,-1.5],[2,-2,-1.5]),None)
    rr=run('B02-unknown-exact-45deg-remains',s,replace(m,thickness_mm=None),obs+[b02],permits,['COLLISION'])
    rows.append(dict(name='B02-exact-angle-and-witness',passed=abs(rr.witness_angle_deg+45)<1e-12 and abs(rr.witness_point_mm[1]+2)<1e-10 and abs(rr.witness_point_mm[2]+2)<1e-10,result=asdict(rr)))
    for budget in [0,-1,True,1.5]:
        run('invalid-budget:'+str(budget),s,m,obs,permits,['UNRESOLVED'],max_intervals=budget)
missing=check_fold_clearance(s,m,obs,expected_obstacle_ids=['source','receiver','omitted'],allowances=permits)
rows.append(dict(name='complete-registry-required',expected=['UNRESOLVED'],passed=missing.status=='UNRESOLVED',result=asdict(missing)))
report=dict(source_sha=a.sha,kind='independent_numeric_geometry_permission_mixed_material_and_between_samples',analytic_thin_witness_mm=[5,y,z],analytic_known_overlap_mm=.05,results=rows,passed=sum(r['passed'] for r in rows),failed=sum(not r['passed'] for r in rows))
a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='results'}));print(json.dumps([dict(name=r['name'],status=r['result']['status'],passed=r['passed'],seconds=r.get('seconds')) for r in rows]))
raise SystemExit(bool(report['failed']))
