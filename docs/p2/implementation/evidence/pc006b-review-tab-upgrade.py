"""Independent actual A-project copy and implicit-to-semantic tab ID audit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--sha',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.source/'src'))
from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject,ProjectFormatError
assert Path(sys.modules[AuthorProject.__module__].__file__).resolve().is_relative_to(a.source.resolve())
source=a.source/'docs/p2/implementation/evidence/pc006a-desktop-7da2403-run04/own-model.apcraft'
original=source.read_bytes();old=json.loads(original);c=AuthorController();c.open(source);p=c.project;cid=next(iter(p.connectors));tid=p.connectors[cid].tab_ids[0];checks=[]
def check(n,ok):checks.append(dict(name=n,passed=bool(ok)))
check('source-IDs-preserved',set(p.surfaces)==set(old['surfaces']) and set(p.profiles)==set(old['profiles']) and set(p.parts)==set(old['parts']) and p.connectors[cid].id==cid and p.connectors[cid].owner_surface_id==old['connectors'][cid]['owner_surface_id'])
check('new-tab-semantic-not-connector',len(p.connectors[cid].tab_ids)==1 and tid!=cid)
check('copypolicy-known-source',c.copy_source_path==source and c.file_path is None)
check('layout-position-and-locks',p.to_dict()['placements']==old['placements'])
c.execute('Independent off',lambda p:p.set_connector_tab(cid,tid,enabled=False))
check('off-exact-tab',c.project.connectors[cid].tab_overrides[tid]['enabled'] is False)
c.undo();check('undo-preserves-new-tab-identity',c.project.connectors[cid].tab_ids==[tid] and not c.project.connectors[cid].tab_overrides)
c.redo();check('redo-preserves-new-tab-identity',c.project.connectors[cid].tab_ids==[tid] and c.project.connectors[cid].tab_overrides[tid]['enabled'] is False)
try:c.save(source);blocked=False
except ValueError:blocked=True
check('original-write-blocked-after-undo-redo',blocked and source.read_bytes()==original)
copy_path=Path(tempfile.mkdtemp(prefix='pc006b-review-original-tab-'))/'copy.apcraft';c.save(copy_path);restored=AuthorProject.load(copy_path)
check('reopen-same-semantic-ID-and-off',restored.connectors[cid].tab_ids==[tid] and restored.connectors[cid].tab_overrides[tid]['enabled'] is False)
check('origin-bytes-unchanged',source.read_bytes()==original)
data=restored.to_dict();data['connectors'][cid]['tab_ids']=[]
try:AuthorProject.from_dict(data);blocked=False
except ProjectFormatError:blocked=True
check('strict-schema2-rejects-empty-ids',blocked)
p=AuthorProject.new(scale=1);s1=p.add_profile([[0,0],[40,0],[40,20],[0,20]]);s2=p.add_profile([[0,0],[40,0],[40,20],[0,20]],plane='XZ');s,t=p.add_surface(s1),p.add_surface(s2)
j=p.connect_edges(s,p.profiles[s1].segments[0].id,t,p.profiles[s2].segments[0].id);p.set_tab(j,owner=t,width_mm=4)
nc=p.connectors[p.joints[j].connector_id];newid=nc.tab_ids[0];p.set_connector_tab(nc.id,newid,enabled=False)
check('fresh-edgepair-tab-editable',len(nc.tab_ids)==1 and newid!=nc.id and nc.tab_overrides[newid]['enabled'] is False)
report=dict(source_sha=a.sha,actual_old_model_sha256=hashlib.sha256(original).hexdigest(),kind='independent-actual-A-schema1-copy-ID-layout-source-preservation-no-GUI',results=checks,passed=sum(x['passed'] for x in checks),failed=sum(not x['passed'] for x in checks))
a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
raise SystemExit(bool(report['failed']))
