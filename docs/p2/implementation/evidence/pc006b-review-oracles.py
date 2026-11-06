"""Independent exact-pin interior contact counterexamples; no GUI or writer helpers."""
import argparse,copy,hashlib,json,math,sys,tempfile
from pathlib import Path
from shapely import Polygon
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--sha',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();sys.path.insert(0,str(args.source/'src'))
from archpapercraft.authoring import AuthorProject,ValidationError,UnsupportedOperationError
import archpapercraft.authoring as imported
assert Path(imported.__file__).resolve().is_relative_to(args.source.resolve())
results=[]
def rect(p,w,h,**kwargs):
    profile=p.add_profile([[0,0],[w,0],[w,h],[0,h]],**kwargs)
    return p.add_surface(profile),profile
def layout(p,surfaces):
    for index,sid in enumerate(surfaces):
        page=p.pages[0].id if index==0 else p.add_page()
        p.set_placement(p.part_for_surface(sid),page_id=page,x_mm=20,y_mm=20)
    p.recompute()
def exportable(p):
    issues=p.validate_layout()
    for issue in issues:
        if issue.severity=='warning':p.acknowledge(issue.id)
    try:p.snapshot();return True
    except ValidationError:return False

p=AuthorProject.new(scale=1)
receiver,rp=rect(p,100,100);wall1,p1=rect(p,100,10);wall2,p2=rect(p,40,10)
j=p.place_and_connect_edges(receiver,p.profiles[rp].segments[0].id,wall1,p.profiles[p1].segments[0].id,angle_deg=90,mode='cut')
p.set_tab(j,owner=wall1,width_mm=7,taper=1)
a=p.place_and_attach_edge(wall2,p.profiles[p2].segments[0].id,receiver,[20,5],[60,5],angle_deg=90,glue_direction=-1,target_side='outside')
c=p.set_attachment_tab(a,width_mm=5,taper=1)
layout(p,[receiver,wall1,wall2])
edge_contact=p.connector_geometry(p.joints[j].connector_id)
trace_contact=p.connector_geometry(c)
actual_overlap=Polygon(edge_contact['tabs'][0]['footprint_uv_mm']).intersection(Polygon(trace_contact['tabs'][0]['footprint_uv_mm'])).area
issues=[{'code':i.code,'severity':i.severity} for i in p.validate_layout()]
snapshot_allowed=exportable(p)
payload=args.output.with_name(args.output.stem+'-B01-project.json')
payload.write_text(json.dumps(p.to_dict(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results.append({'name':'B01_mixed_EdgePair_SurfaceTrace_collision','project_payload':str(payload),'analytic_overlap_mm2':40*5,'actual_overlap_mm2':actual_overlap,'edge_contact':edge_contact,'trace_contact':trace_contact,'issues':issues,'snapshot_allowed_after_warnings':snapshot_allowed,'expected_snapshot_blocked':True,'pass':abs(actual_overlap-200)<1e-8 and not snapshot_allowed})

p=AuthorProject.new(scale=1)
receiver,rp=rect(p,100,100);wall,wp=rect(p,40,10)
a=p.place_and_attach_edge(wall,p.profiles[wp].segments[0].id,receiver,[20,5],[60,5],angle_deg=90,glue_direction=-1,target_side='outside')
c=p.set_attachment_tab(a,width_mm=5,taper=1)
obstacle,op=rect(p,30,1,plane='XZ')
p.set_transform(obstacle,position_mm=[25,3,-2.5])
layout(p,[receiver,wall,obstacle])
geometry=p.connector_geometry(c)
snapshot_allowed=exportable(p)
payload=args.output.with_name(args.output.stem+'-B02-project.json')
payload.write_text(json.dumps(p.to_dict(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Exact witness: at an intermediate 45-degree rotation of the initially downward
# tab about x, radius sqrt(8)<5 gives y=5-2=3,z=-2. Both final/flat configurations
# miss the independent obstacle y=3,z=[-2.5,-1.5],x=[25,55].
witness=[40,3,-2]
results.append({'name':'B02_intermediate_bend_obstacle_is_not_checked','project_payload':str(payload),'analytic_witness_world_mm':witness,'tab_radius_at_witness_mm':math.sqrt(8),'tab_width_mm':5,'obstacle_bounds_world':{'x':[25,55],'y':[3,3],'z':[-2.5,-1.5]},'folded_contact_valid':geometry['valid'],'bend_sweep_status':geometry['bend_sweep_status'],'snapshot_allowed_after_warnings':snapshot_allowed,'scope':'Known digital sweep gap, not an assertion that the API falsely reports sweep PASS. Physical material is separately unknown.','pass':not snapshot_allowed})

p=AuthorProject.new(scale=.1)
target,tp=rect(p,170,140,plane={'origin':[13,7,5],'u':[.8,.6,0],'v':[0,0,1]})
wall,wp=rect(p,60,40)
a=p.place_and_attach_edge(wall,p.profiles[wp].segments[0].id,target,[20,30],[80,30],angle_deg=35,glue_direction=1,target_side='inside')
c=p.set_attachment_tab(a,width_mm=1.5,taper=1)
contact=p.connector_geometry(c)
results.append({'name':'rotated_plane_straight_tab_has_analytic_9mm2_contact','actual_nominal_mm2':contact['tabs'][0]['nominal_area_mm2'],'actual_available_mm2':contact['tabs'][0]['available_area_mm2'],'analytic_mm2':6*1.5,'pass':contact['valid'] and abs(contact['tabs'][0]['available_area_mm2']-9)<1e-8})
p.set_connector(c,count=3,gap_mm=.3,shape='triangle')
ids=list(p.connectors[c].tab_ids)
p.set_connector_tab(c,ids[1],enabled=False)
contact=p.connector_geometry(c)
results.append({'name':'authored_off_tab_identity_and_area','analytic_mm2':2*1.7*1.5/2,'actual_mm2':sum(t['available_area_mm2'] for t in contact['tabs']),'ids_preserved':ids==p.connectors[c].tab_ids,'pass':ids==p.connectors[c].tab_ids and abs(sum(t['available_area_mm2'] for t in contact['tabs'])-2.55)<1e-8})
before=copy.deepcopy(p.to_dict())
try:p.set_connector(c,gap_mm=2.1);rejected=False
except ValidationError:rejected=True
results.append({'name':'invalid_gap_rejects_atomically','pass':rejected and p.to_dict()==before})
result={'source_sha':args.sha,'source_root':str(args.source),'kind':'independent_numeric_negative_and_positive_domain_experiments_no_GUI','results':results,'pass':sum(r['pass'] for r in results),'fail':sum(not r['pass'] for r in results)}
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_sha':args.sha,'pass':result['pass'],'fail':result['fail'],'results':[{'name':r['name'],'pass':r['pass']} for r in results]}))
raise SystemExit(1 if result['fail'] else 0)
