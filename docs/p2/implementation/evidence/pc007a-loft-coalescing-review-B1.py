"""Own backend replay of the actual native dense B1 file, not editor proof."""
import copy
import hashlib
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
archive=json.loads((E/'pc007a-loft-coalescing-review-archive-730cb28.json').read_text(encoding='utf8'))
sys.path.insert(0,str(Path(archive['isolated_directory'])/'src'))
from archpapercraft.authoring import AuthorProject,ValidationError,load_project,loft_surface

source=ROOT.parent/'papercraft-loft-integration/docs/p2/implementation/evidence/pc007a-loft-B1-desktop-b127fc5-run02/loft-B1/loft-B1.apcraft'
started=time.perf_counter();raw=source.read_bytes();p=load_project(source)
sid=next(sid for sid,s in p.surfaces.items() if s.kind=='ruled_loft');pid=p.part_for_surface(sid)
old=p.to_dict();old_paths=copy.deepcopy(p.parts[pid].paths)
assert p.parts[pid].stale and 'STALE' in [i.code for i in p.validate_layout()]
try:p.snapshot()
except ValidationError:pass
else:raise AssertionError('Old paper contract was not blocked')
p.recompute();state=p.to_dict();record=p.loft_status(sid);analysis=loft_surface.analysis(p,p.surfaces[sid])
assert record['status']=='EXACT' and record['paper_contract'].endswith('V3') and not record['paper_stale']
assert record['area']['status']=='CERTIFIED' and record['paper_frame_area']['status']=='CERTIFIED'
for key in ('profiles','surfaces','placements','pages','next_part_number','next_joint_number','next_attachment_number'):
    assert old[key]==state[key],key
assert old['parts'][pid]['frame']==state['parts'][pid]['frame']
assert not p.validate_layout()
snapshot=p.snapshot();assert snapshot['coverage']['expected_loft_surface_ids']==[sid]
binding=record['source_binding']
assert binding['profiles']==[state['profiles'][identity] for identity in p.surfaces[sid].source_profile_ids()]
assert binding['surface']==state['surfaces'][sid]
intrinsic={'profiles':binding['profiles'],'params':binding['surface']['params'],'scale':binding['scale']}
intrinsic_hash=hashlib.sha256(json.dumps(intrinsic,sort_keys=True,allow_nan=False).encode()).hexdigest()
assert intrinsic_hash==record['intrinsic_source_digest']
native=analysis['native'];fine_records=0
for patch in native['patches']:
    for s in [*patch['first']['segments'],*patch['second']['segments'],*patch['closed_boundary_segments']]:
        for r in [s['source'],*s['source'].get('subintervals',[])]:
            assert r['feature_id']==sid and r['patch_id']==patch['patch_id']
            fine_records+=1
    first=patch['first']['segments'];second=patch['second']['segments']
    backward=[s for s in patch['closed_boundary_segments'] if s['source'].get('profile_id')==second[0]['source']['profile_id']]
    assert backward
target=Path(tempfile.mkdtemp(prefix='papercraft-coalescing-review-B1-'))/'own-recomputed.apcraft'
p.save(target);restored=load_project(target);assert restored.to_dict()==state
assert source.read_bytes()==raw
poison=copy.deepcopy(state)
for cmd in poison['parts'][pid]['paths']['CUT'][0]['commands']:
    for i in range(1,len(cmd),2):cmd[i]+=.125
bad=AuthorProject.from_dict(poison)
assert not bad.parts[pid].stale and 'INVALID_CACHE' in [i.code for i in bad.validate_layout()]
try:bad.snapshot()
except ValidationError:pass
else:raise AssertionError('Actual B1 equal-area current-contract poison passed')
commands=p.parts[pid].paths['CUT'][0]['commands'];kinds=dict(Counter(cmd[0] for cmd in commands))
assert kinds=={'M':1,'C':64,'L':3,'Z':1},kinds
result={'source_sha':archive['source_sha'],'actual_import':loft_surface.__file__,
        'fixture_path':str(source),'fixture_sha256':hashlib.sha256(raw).hexdigest(),
        'original_commands':len(old_paths['CUT'][0]['commands']),'current_commands':len(commands),'actual_command_kinds':kinds,
        'source_profiles_surfaces_frame_layout_unchanged':True,'old_contract_stale_and_snapshot_blocked':True,
        'current_v3_equal_area_poison_rejected':True,'save_reopen_preserved':True,'source_file_unchanged':True,
        'feature_and_patch_bound_records_checked':fine_records,'coalescing':native['coalescing'],
        'source_to_coarse_position_bound_paper_mm':native['position_error_bound_paper_mm'],
        'source_to_coarse_length_bound_paper_mm':native['boundary_length_error_bound_paper_mm'],
        'native_topology':analysis['native_topology'],'area':record['area'],'seconds':time.perf_counter()-started,
        'scope':'INDEPENDENT_BACKEND_REPLAY_NOT_NATIVE_EDITOR_NOVICE_OR_PHYSICAL',
        'LX01_actual_new_editor_result':'NOT_RUN_BY_REVIEWER; required before digital closure'}
(E/'pc007a-loft-coalescing-review-B1-730cb28.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('area','native_topology','coalescing')},indent=2))
