"""Independent contact-tolerance and full glued-patch registry cases."""
import argparse,copy,json,math,sys
from pathlib import Path
from shapely import Polygon
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.source/'src'))
from archpapercraft.authoring import AuthorProject,ValidationError
import archpapercraft.authoring as module
assert Path(module.__file__).resolve().is_relative_to(a.source.resolve())
rows=[]
def check(name,ok,detail=None):rows.append(dict(name=name,passed=bool(ok),detail=detail))
for scale in [1,1e6]:
    for fraction in [.9,1.1]:
        p=AuthorProject.new(scale=scale);pr=p.add_profile([[0,0],[10,0],[10,10],[0,10]]);s=p.add_surface(pr);t=p.add_surface(p.add_profile([[-10,-10],[20,-10],[20,20],[-10,20]]))
        tolerance=min(1e-6,.01/scale);gap=tolerance*fraction;p.set_transform(s,[0,0,gap]);before=copy.deepcopy(p.to_dict())
        try:
            aid=p.attach_edge_to_surface(s,p.profiles[pr].segments[0].id,t);accepted=True;data=p.attachment_geometry(aid)
        except ValidationError:accepted=False
        check('contact-threshold:'+str(scale)+':'+str(fraction),accepted==(fraction<1),dict(gap_model_mm=gap,gap_paper_mm=gap*scale))
        if accepted:check('source-never-snapped:'+str(scale),p.world_geometry(s)['vertices'][0][2]==gap and data['contact_gap_mm']==gap and data['contact_tolerance_model_mm']*scale<=.01)
        else:check('invalid-contact-atomic:'+str(scale),p.to_dict()==before)
rawpath=a.source/'docs/p2/implementation/evidence/pc006b-desktop-d83429c-run02/FAIL-partial-observed-state.json';raw=rawpath.read_bytes();p=AuthorProject.from_dict(json.loads(raw));aid=max(p.attachments.values(),key=lambda x:x.number).id;t=p.attachments[aid].target_surface_id;pr=p.profiles[p.surfaces[t].profile_id];before=copy.deepcopy(pr.points);band=p.add_glue_band(aid,width_mm=2)
area=sum(Polygon(loops[0],loops[1:]).area for loops in p.parts[band].polygons.values())
check('actual-rounding-band-independent-area',abs(area-4*math.sqrt(30**2+30**2))<1e-7,area)
check('actual-rounding-roof-unchanged',pr.points==before and rawpath.read_bytes()==raw)
path=a.source/'docs/p2/implementation/evidence/pc006b-desktop-5b1161c-run03/model-A/model-A.apcraft';raw=path.read_bytes();p=AuthorProject.from_dict(json.loads(raw));contacts=[]
for att in p.attachments.values():
    if att.source_edge_id is None:
        loops=p.attachment_geometry(att.id)['target_loops_uv'];contacts.append((att,Polygon(loops[0],loops[1:])))
areas=[x.intersection(y).area*p.scale**2 for index,(att,x) in enumerate(contacts) for other,y in contacts[index+1:] if att.target_surface_id==other.target_surface_id and att.target_side==other.target_side]
check('actual-native-registry-20mm2',max(areas)==20,areas)
check('actual-native-registry-blocks',any(i.code=='FOLDED_CONNECTOR_COLLISION' for i in p.validate_layout()))
try:p.snapshot();blocked=False
except ValidationError:blocked=True
check('actual-native-snapshot-blocked-preserves-raw',blocked and path.read_bytes()==raw)
for overlap,side in [(False,'inside'),(True,'inside'),(True,'outside')]:
    p=AuthorProject.new(scale=1);base=p.add_surface(p.add_profile([[0,0],[100,0],[100,100],[0,100]]));outer=[[10,10],[70,10],[70,70],[10,70]];hole=p.add_profile([[20,20],[60,20],[60,60],[20,60]]);ring=p.add_surface(p.add_profile(outer),holes=[hole]);p.set_glue_region(ring,base,outer)
    small=[[15,30],[25,30],[25,40],[15,40]] if overlap else [[30,30],[40,30],[40,40],[30,40]]
    s=p.add_surface(p.add_profile(small));p.set_glue_region(s,base,small,target_side=side)
    contact=p.attachment_geometry(next(att.id for att in p.attachments.values() if att.source_surface_id==ring));loops=contact['target_loops_uv'];ringpoly=Polygon(loops[0],loops[1:]);numeric=ringpoly.intersection(Polygon(small)).area
    check('independent-hole-area:'+str(overlap)+':'+side,numeric==(50 if overlap else 0),numeric)
    issues=p.validate_layout();check('independent-hole-registry:'+str(overlap)+':'+side,any(i.code=='FOLDED_CONNECTOR_COLLISION' for i in issues)==(overlap and side=='inside'))
report=dict(source_sha='255088984fc189eec62109dc1890905e53e00b73',contact_source='5b1161c3df9fc3dc90e04818e9526c0c4f1fdf50',kind='independent-contact-boundary-actual-raw-state-and-glued-hole-registry',results=rows,passed=sum(r['passed'] for r in rows),failed=sum(not r['passed'] for r in rows));a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report));raise SystemExit(bool(report['failed']))
