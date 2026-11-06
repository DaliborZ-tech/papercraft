"""Independent B-01 exact witness with side/identity/atomicity controls."""
from pathlib import Path
exec(Path(__file__).with_name('pc006b-review-oracles.py').read_text(encoding='utf8').split('p=AuthorProject.new(scale=1)')[0])

def fixture():
    p=AuthorProject.new(scale=1)
    receiver,rp=rect(p,100,100);wall1,p1=rect(p,100,10);wall2,p2=rect(p,40,10)
    j=p.place_and_connect_edges(receiver,p.profiles[rp].segments[0].id,wall1,p.profiles[p1].segments[0].id,angle_deg=90,mode='cut')
    p.set_tab(j,owner=wall1,width_mm=7,taper=1)
    a=p.place_and_attach_edge(wall2,p.profiles[p2].segments[0].id,receiver,[20,5],[60,5],angle_deg=90,glue_direction=-1,target_side='outside')
    ac=p.set_attachment_tab(a,width_mm=5,taper=1)
    layout(p,[receiver,wall1,wall2])
    return p,j,p.joints[j].connector_id,ac,receiver

def record(name,ok,detail=None):
    results.append(dict(name=name,passed=bool(ok),detail=detail))

for side,expected in [('unknown','FOLDED_SIDE_UNRESOLVED'),('outside','FOLDED_CONNECTOR_COLLISION'),('inside',None)]:
    p,j,c,ac,receiver=fixture();p.set_connector(c,receiver_side=side);p.recompute()
    issues=p.validate_layout();codes=[i.code for i in issues if i.code.startswith('FOLDED_')]
    a,b=[p.connector_geometry(cid)['tabs'][0]['footprint_uv_mm'] for cid in [c,ac]]
    overlap=Polygon(a).intersection(Polygon(b)).area
    record('analytic-200mm2:'+side,abs(overlap-200)<1e-9,overlap)
    record('side-diagnostic:'+side,codes==([] if expected is None else [expected]),codes)
    record('snapshot-block-or-allow:'+side,exportable(p)==(expected is None))
    if expected:
        issue=next(i for i in issues if i.code==expected)
        try:p.acknowledge(issue.id);blocked=False
        except ValidationError:blocked=True
        record('error-cannot-acknowledge:'+side,blocked)
    restored=AuthorProject.from_dict(p.to_dict())
    record('roundtrip-side-and-tabIDs:'+side,restored.connectors[c].receiver_side==side and restored.connectors[c].tab_ids==p.connectors[c].tab_ids)

p,j,c,ac,receiver=fixture();p.set_connector(c,receiver_side='outside');ids=list(p.connectors[c].tab_ids)
p.set_connector(c,enabled=False);p.recompute()
record('off-removes-only-conflict',not any(i.code.startswith('FOLDED_') for i in p.validate_layout()) and exportable(p))
p.set_connector(c,enabled=True);p.recompute()
record('reenable-same-UUID-restores-error',p.connectors[c].tab_ids==ids and any(i.code=='FOLDED_CONNECTOR_COLLISION' for i in p.validate_layout()))
before=copy.deepcopy(p.to_dict())
try:p.set_connector(c,receiver_side='neither');rejected=False
except ValidationError:rejected=True
record('invalid-side-atomic',rejected and p.to_dict()==before)
p.set_tab(j,owner=receiver)
record('owner-change-drops-face-intent',p.connectors[c].receiver_side=='unknown')

report=dict(source_sha=args.sha,kind='independent_numeric_exact_200mm2_negative_and_opposite_side_positive',results=results,passed=sum(r['passed'] for r in results),failed=sum(not r['passed'] for r in results))
args.output.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
if report['failed']:print(json.dumps([r for r in results if not r['passed']]))
raise SystemExit(bool(report['failed']))
