"""Independent panel-paper review. Pinned imports; analytic oracles, not UI tests."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(sys.argv[1]).resolve()
PIN = sys.argv[2]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REVIEW, text=True).strip() == PIN
sys.path.insert(0, str(REVIEW/'src'))
import numpy as np
from archpapercraft.domain import PanelProject, PaperFrame, ValidationError, ProjectFormatError
from archpapercraft.domain.paper import PanelEngine, fold_kind

started = time.perf_counter()
results = {}


def area(polygon):
    # Independent shoelace oracle on small convex fixture coordinates.
    return abs(math.fsum(float(a[0]*b[1]-a[1]*b[0]) for a,b in zip(polygon,np.roll(polygon,-1,axis=0))))/2


def part_for(engine, key):
    sid = engine.project.surface_id(key)
    return next(part for part in engine.parts.values() if sid in part.surface_ids)


def joint_for(project, a, b):
    ids = {project.surface_id(a),project.surface_id(b)}
    return next(j for j in project.joints.values() if {j.surface_a,j.surface_b}==ids)


def no_tabs(project, engine):
    for joint in project.joints.values():
        joint.tab_owner = None
    engine.recompute()


def ready():
    project = PanelProject.new_house()
    engine = PanelEngine(project)
    no_tabs(project, engine)
    project.set_scale(.005)
    engine.recompute()
    for index,part in enumerate(engine.parts.values()):
        placement = project.placements[part.id]
        placement.page_id = project.pages[index//4].id
        placement.x_mm = 40+(index%2)*85
        placement.y_mm = 40+((index%4)//2)*110
    assert not engine.validate_layout()
    return project,engine


project=PanelProject.new_house(length_mm=12000,width_mm=8000,wall_height_mm=5000,roof_rise_mm=3000)
engine=PanelEngine(project)
no_tabs(project,engine)
all_ids=[sid for part in engine.parts.values() for sid in part.surface_ids]
assert len(all_ids)==len(set(all_ids))==8
total_area=sum(area(poly) for part in engine.parts.values() for poly in part.polygons.values())
assert abs(total_area-34400)<.01
assert sum(len(part.cut_paths) for part in engine.parts.values())==30
results['nondefault_panel_coverage']=dict(surfaces=8,area_paper_mm2=total_area,cut_paths_without_tabs=30,internal_triangulation_cuts=0)

project=PanelProject.new_house()
engine=PanelEngine(project)
initial_tabs=[(part,jid,tab) for part in engine.parts.values() for jid,tab in zip(part.tab_joints,part.tab_polygons)]
assert len(initial_tabs)==len(project.joints)==13
for part,jid,tab in initial_tabs:
    assert sum(other_jid==jid for _,other_jid,_ in initial_tabs)==1
    base=tab[-1]-tab[0]
    outside_signed=float(base[0]*(tab[1]-tab[0])[1]-base[1]*(tab[1]-tab[0])[0])
    assert outside_signed<0
    assert abs(abs(outside_signed)/np.linalg.norm(base)-5)<1e-8
    assert any(np.array_equal(path,tab) for path in part.cut_paths)
    assert not any(len(path)==2 and np.array_equal(path,tab[[0,-1]]) for path in part.cut_paths)
joint=joint_for(project,'wall-left','roof-left')
engine.set_tab(joint.id,owner=joint.surface_b,width_mm=7,taper=.5)
assert sum(jid==joint.id for part in engine.parts.values() for jid in part.tab_joints)==1
results['tabs']=dict(one_owner_per_joint=True,outward_signed_halfplane=True,default_width_mm=5,no_base_cut=True,owner_change_removes_old=True)

no_tabs(project,engine)
wall=part_for(engine,'wall-left')
engine.set_joint(joint.id,mode='fold',receiving_part_id=wall.id)
mixed=part_for(engine,'wall-left')
placement=project.placements[mixed.id]
placement.page_id=project.pages[1].id
placement.x_mm=60;placement.y_mm=60;placement.rotation_deg=30
placement.lock_position=placement.lock_rotation=True
wall_sid=project.surface_id('wall-left');roof_sid=project.surface_id('roof-left')
before=engine.part_polygons_on_page(mixed.id)[wall_sid].copy()
expected=np.array([[60,60],[60+50*math.sqrt(3),110],[40+50*math.sqrt(3),60+50+20*math.sqrt(3)],[40,60+20*math.sqrt(3)]])
assert np.max(np.abs(before-expected))<1e-8
root_frame=copy.deepcopy(mixed.frame)
old_roof=mixed.polygons[roof_sid].copy()
project.set_dimension('roof_rise_mm',3500)
with tempfile.TemporaryDirectory(prefix='paper-review-mixed-') as temp:
    path=Path(temp)/'stale.apcraft'
    project.save(path)
    reopened=PanelEngine(PanelProject.load(path))
    assert reopened.parts[mixed.id].stale
    assert np.array_equal(reopened.parts[mixed.id].polygons[roof_sid],old_roof)
    assert any(issue.code=='STALE_PART' for issue in reopened.validate_layout())
    reopened.recompute()
    new_wall=reopened.part_polygons_on_page(mixed.id)[wall_sid]
    assert np.max(np.abs(new_wall-before))<1e-8
    assert reopened.parts[mixed.id].frame==root_frame
    assert abs(reopened.parts[mixed.id].polygons[roof_sid][:,1].max()-(40+math.hypot(30,35)))<.01
    assert reopened.project.placements[mixed.id].lock_position and reopened.project.placements[mixed.id].lock_rotation
    project,engine=reopened.project,reopened
results['mixed_anchor']=dict(wall_corners_paper_mm=before.tolist(),stale_cache_saved=True,wall_max_drift_mm=float(np.max(np.abs(new_wall-before))),new_roof_slope_mm=math.hypot(30,35),locks_and_frame_preserved=True)
before_split=engine.part_polygons_on_page(mixed.id)
parent_id=mixed.id
engine.set_joint(joint.id,mode='cut')
for key in ('wall-left','roof-left'):
    child=part_for(engine,key);sid=project.surface_id(key)
    assert child.id!=parent_id and project.part_records[child.id]['lineage']==[parent_id]
    assert np.max(np.abs(engine.part_polygons_on_page(child.id)[sid]-before_split[sid]))<1e-8
results['split']=dict(new_ids=True,lineage_preserved=True,page_geometry_preserved=True)

# Independent convex/concave normals and oriented tangent. Surface identity
# strings never determine polarity, and swapping both sides reverses tangent.
a=type('N',(),{'normal':np.array([0.,0.,1.])})()
b=type('N',(),{'normal':np.array([0.,1.,0.])})()
edge=type('E',(),{'start':np.zeros(3),'end':np.array([1.,0.,0.]),'length':1.})()
reverse=type('E',(),{'start':edge.end,'end':edge.start,'length':1.})()
assert fold_kind(a,b,edge)=='valley'
assert fold_kind(b,a,reverse)=='valley'
assert fold_kind(a,b,edge,'inside')=='mountain'
convex=type('N',(),{'normal':np.array([0.,-1.,0.])})()
assert fold_kind(a,convex,edge)=='mountain'
results['fold_polarity']=dict(concave='valley',convex='mountain',side_swap_consistent=True,printed_side_flips=True)

project=PanelProject.new_house();engine=PanelEngine(project);no_tabs(project,engine)
for a_key,b_key in [('wall-left','roof-left'),('roof-left','roof-right'),('roof-right','wall-right')]:
    receiver=part_for(engine,'wall-left')
    engine.set_joint(joint_for(project,a_key,b_key).id,mode='fold',receiving_part_id=receiver.id)
strip=part_for(engine,'wall-left')
right_sid=project.surface_id('wall-right')
right_source=project.surfaces()[right_sid]
index=right_source.vertex_ids.index(project.element_id+':front-right-top')
old_point=strip.polygons[right_sid][index].copy()
assert np.max(np.abs(old_point-[0,40+2*math.hypot(30,30)]))<1e-8
project.set_dimension('roof_rise_mm',3500);engine.recompute()
new_point=engine.parts[strip.id].polygons[right_sid][index]
assert np.max(np.abs(new_point-[0,40+2*math.hypot(30,35)]))<1e-8
results['dependency_wall']=dict(reference_point_before_local_mm=old_point.tolist(),reference_point_after_local_mm=new_point.tolist(),movement_mm=float(np.linalg.norm(new_point-old_point)),expected_movement_mm=2*(math.hypot(30,35)-math.hypot(30,30)))

project,engine=ready();wall=part_for(engine,'wall-left');placement=project.placements[wall.id]
placement.page_id=project.pages[0].id;placement.x_mm=2;placement.y_mm=30
margin=next(issue for issue in engine.validate_layout() if issue.code=='PRINT_MARGIN' and wall.id in issue.part_ids)
engine.acknowledge(margin.id)
assert next(issue for issue in engine.validate_layout() if issue.id==margin.id).acknowledged
placement=project.placements[wall.id];placement.x_mm=3
assert not next(issue for issue in engine.validate_layout() if issue.id==margin.id).acknowledged
placement.x_mm=-1
overflow=next(issue for issue in engine.validate_layout() if issue.code=='PHYSICAL_OVERFLOW' and wall.id in issue.part_ids)
try:engine.acknowledge(overflow.id)
except ValidationError:pass
else:raise AssertionError('Physical overflow acknowledged')
project.acknowledgements[overflow.id]=overflow.digest
assert not next(issue for issue in engine.validate_layout() if issue.id==overflow.id).acknowledged
try:engine.snapshot()
except ValidationError:pass
else:raise AssertionError('Forged acknowledgement bypassed complete-export integrity')
placement.x_mm=50;placement.y_mm=275
footer=next(issue for issue in engine.validate_layout() if issue.code=='PRINT_GUIDE_OVERLAP' and wall.id in issue.part_ids)
assert footer.severity=='warning'
results['warnings_and_integrity']=dict(margin_ack_allowed=True,placement_change_invalidates_ack=True,physical_overflow_not_acknowledgeable=True,forged_ack_cannot_bypass_hard_error=True,footer_overlap_detected=True)

project,engine=ready()
pid=next(iter(engine.parts));part=engine.parts[pid]
source_before=project.to_dict()
assert sum(len(page['parts']) for page in engine.snapshot()['pages'])==8
removed=engine.parts.pop(pid)
try:
    missing_snapshot=engine.snapshot()
except ValidationError as exc:
    results['missing_runtime_cache_part']=dict(blocked=True,code=exc.code,authoritative_part_records=len(project.part_records))
else:
    results['missing_runtime_cache_part']=dict(blocked=False,authoritative_part_records=len(project.part_records),runtime_parts=len(engine.parts),exported_parts=sum(len(page['parts']) for page in missing_snapshot['pages']),issues=[issue.code for issue in engine.validate_layout()])

project,engine=ready()
bad=next(iter(engine.parts.values()))
sid=bad.surface_ids[0]
project.part_records[bad.id]['geometry']['polygons'][sid][1][0]+=3
tampered=PanelEngine(PanelProject.from_dict(project.to_dict()))
assert any(issue.code=='INVALID_GEOMETRY' for issue in tampered.validate_layout())
try:tampered.snapshot()
except ValidationError:pass
else:raise AssertionError('Tampered persisted geometry exported')
results['tampered_serialized_geometry']='blocked'

counter_cases=[]
for counter in (True,0,-1,'9',1.5,1):
    payload=copy.deepcopy(source_before)
    payload['paper_state']['next_part_number']=counter
    try:PanelProject.from_dict(payload)
    except ProjectFormatError:counter_cases.append(repr(counter))
    else:raise AssertionError(f'Invalid counter accepted: {counter!r}')
results['strict_counter_rejected']=counter_cases

output=dict(code_sha=PIN,seconds=round(time.perf_counter()-started,3),scope='paper engine only; no UI/export renderer approval',results=results)
(ROOT/'docs/p2/evidence'/f'paper-review-results-{PIN[:7]}.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps(output,indent=2))
