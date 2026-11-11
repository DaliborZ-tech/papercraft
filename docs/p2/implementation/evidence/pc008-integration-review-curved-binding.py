"""Independent combined source/cache boundary checks; no GUI or new math approval."""
import copy,hashlib,json,sys
from pathlib import Path
E=Path(__file__).resolve().parent
audit=json.loads((E/'pc008-integration-review-d762-artifacts.json').read_text())
root=Path(audit['isolated_directory']);sys.path.insert(0,str(root/'src'))
from archpapercraft.authoring import AuthorProject,ValidationError
from archpapercraft.authoring import segmented_surface
assert Path(segmented_surface.__file__).resolve().is_relative_to(root)
source=root/'docs/p2/implementation/evidence/pc008-curved-domain-518b91a/raw/gothic-backend.apcraft'
state=json.loads(source.read_text(encoding='utf8'));original=copy.deepcopy(state)
p=AuthorProject.from_dict(copy.deepcopy(state));vid=next(iter(p.segmented_variants));v=p.segmented_variants[vid]
target=v.target_surface_id;params=v.parameters
assert p.segmented_variant_status(vid)['status']=='APPROXIMATE'
before=p.to_dict();preview=p.preview_segmented_variant(target,**params)
assert preview['can_confirm'] and len(preview['preview_geometry']['triangles'])==96
token=preview['preview_digest']
preview['preview_geometry']['vertices'][0][0]+=1e6
preview['certificate']['math']['status']='POISONED_CALLER_COPY'
fresh=p.preview_segmented_variant(target,**params)
assert fresh['preview_digest']==token and fresh['certificate']['math']['status']=='CERTIFIED'
assert p.to_dict()==before
q=AuthorProject.from_dict(copy.deepcopy(state));source_profile=q.profiles[q.surfaces[target].source_profile_ids()[1]]
revision=source_profile.revision;source_profile.plane.origin[2]+=2
assert source_profile.revision==revision and q.segmented_variant_status(vid)['status']=='STALE'
assert q.placements==p.placements
changed=q.preview_segmented_variant(target,**params)
assert not changed['can_confirm'] or changed['preview_digest']!=token
if changed['can_confirm']:
 assert changed['source_binding']['profiles'][1]['plane']['origin'][2]==source_profile.plane.origin[2]
 assert changed['certificate']!=fresh['certificate']
q=AuthorProject.from_dict(copy.deepcopy(state));row=q.segmented_variants[vid].triangle_bindings[0]
q.profiles[row['profile_id']].vertices[0].point[0]+=.001
assert q.segmented_variant_status(vid)['status']=='UNRESOLVED'
forged=copy.deepcopy(state);profile=next(iter(forged['profiles'].values()));profile['external_factory']={'opaque_callback':'same UUID'}
try:AuthorProject.from_dict(forged)
except ValidationError:pass
else:raise AssertionError('External source factory crossed closed persistent profile schema')
assert state==original
result=dict(source_sha=audit['source_sha'],actual_module=segmented_surface.__file__,
 source_fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),checks={
 'curved_96_real_candidate_and_caller_mutation_does_not_poison_cache':'PASS',
 'same_UUID_no_revision_actual_plane_change_invalidates_source_and_token':'PASS',
 'actual_child_profile_poison_is_UNRESOLVED':'PASS',
 'closed_profile_rejects_external_factory_field':'PASS'},
 changed_source_candidate_status=changed['status'],scope='INTEGRATED_CURVED_DOMAIN_BINDING_NOT_REPEAT_OF_CURVED_MATH_CERTIFICATION')
(E/'pc008-integration-review-curved-binding.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,indent=2))
