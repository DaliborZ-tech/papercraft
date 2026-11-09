"""Read-only pinned handoff/reference audit; no runtime or product tests."""
import hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN='1cd6dc5f42acde23cb72c443216fd68f6ca34448'
PUBLISHED='a27cf5aaf76e7057a49d4b4cb7ec85a87855c17f'
LOCAL='f214222592550a0a057bf09e99e06b0a791f6e07'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(pin,path):return git('show',pin+':'+path)
changes=git('diff','--name-only',PUBLISHED,PIN).decode().splitlines()
assert set(changes)=={'00_START_HERE.md','05_WORK_QUEUE.json','docs/p2/implementation/CONTINUE_2026-11-10.md'}
assert not git('diff',PUBLISHED,PIN,'--','src','tools','pyproject.toml','AGENTS.md','04_ACCEPTANCE_AND_VERIFICATION.md','docs/p2/v1.2')
q=json.loads(blob(PIN,'05_WORK_QUEUE.json'));c=q['current_delivery'];tickets={t['id']:t for t in q['tickets']}
assert c['status']=='PAUSED' and tickets['PC-007A']['status']=='PAUSED'
assert c['paused_on']=='2026-11-09' and c['continuation_target_date']=='2026-11-10'
assert c['implementation_authorization_unchanged'] and c['pending_local_package']['whole_P2_complete'] is False
assert c['pending_local_package']['published_on_master'] is False and c['pending_local_package']['performance_independent_review']=='NOT_RUN'
assert c['wip_source_sha']==LOCAL and c['planar_verified_slice']['published_sha']==PUBLISHED
assert c['pending_local_package']['novice_participants']==0 and c['pending_local_package']['physical_proof']=='NOT_RUN_P3'
assert q['release_readiness'].startswith('NOT_READY')
perf=c['pending_local_package']
assert perf['performance_runtime_sha']=='2e4212388caef05adef42a4301bf367e7a6cb7f0'
assert perf['performance_handoff_sha']=='d460446cd643478b8236df1e058522d63d72553c'
assert perf['performance_worktree_clean'] is True
before=json.loads(blob(perf['performance_handoff_sha'],'docs/p2/implementation/evidence/pc007a-loft-performance/before.json'))
after=json.loads(blob(perf['performance_handoff_sha'],'docs/p2/implementation/evidence/pc007a-loft-performance/after.json'))
assert before['fixture']['sha256']==after['fixture']['sha256'] and before['fixture_unchanged'] and after['fixture_unchanged']
assert after['source_sha']==perf['performance_runtime_sha'] and after['runtime']['qpa']=='offscreen'
assert round(before['operations']['qt_placement_command_and_refresh'],2)==18.48
assert round(after['operations']['qt_placement_command_and_refresh'],2)==3.24
assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT.parent/'papercraft-loft-performance')
remote=git('ls-remote','origin','refs/heads/master').decode().split()[0]
assert git('rev-parse','master').decode().strip()==git('rev-parse','origin/master').decode().strip()==remote==PUBLISHED
subprocess.check_call(['git','merge-base','--is-ancestor',PUBLISHED,LOCAL],cwd=ROOT)
worktrees=git('worktree','list','--porcelain').decode()
assert 'worktree C:/Users/dalib/projects/papercraft-loft-integration\n' in worktrees
integration_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT.parent/'papercraft-loft-integration',text=True).strip()
subprocess.check_call(['git','merge-base','--is-ancestor',LOCAL,integration_head],cwd=ROOT)
for name in ('loft-domain','loft-ui','loft-output','loft-performance','segmentation-math'):
    assert 'worktree C:/Users/dalib/projects/papercraft-'+name+'\n' in worktrees
cases={
 'B1':('pc007a-loft-B1-desktop-a9d155a-run01/results.json','FAIL','a9d155a'),
 'B2':('pc007a-loft-B2-desktop-23ce202-run02/results.json','PASS_REQUESTED_FIXTURE','23ce202'),
 'Bezier':('pc007a-loft-Bezier-desktop-23ce202-run01/results.json','PASS_REQUESTED_FIXTURE','23ce202'),
 'B2_editor_disk':('pc007a-loft-B2-inkscape-23b2446-run01/editor-results.json','PASS','23b2446'),
 'B2_editor_band':('pc007a-loft-B2-inkscape-23b2446-run02/editor-results.json','PASS','23b2446'),
 'Bezier_editor':('pc007a-loft-Bezier-inkscape-23b2446-run01/editor-results.json','FAIL','23b2446')}
observations={}
for name,(path,status,prefix) in cases.items():
    raw=blob(LOCAL,'docs/p2/implementation/evidence/'+path);r=json.loads(raw)
    assert r['status']==status and r['source_sha'].startswith(prefix)
    observations[name]={'status':r['status'],'source_sha':r['source_sha'],'elapsed_seconds':r['elapsed_seconds'],'git_blob_sha256':hashlib.sha256(raw).hexdigest()}
for source in ('a1cbf920397694f3b1d3e85a08052acdc3962a7b','6efd70a33f377298a267b4a91214e5383eb548f5','3f4ece8e54081164a1f5731518056712930ac14b','eeaf08182977d89dac0a6a989a8a1076255d343e'):
    git('cat-file','-e',source+'^{commit}')
for path in ('PC007A_LOFT_DOMAIN_REVIEW.md','PC007A_LOFT_UI_REVIEW.md','PC007A_LOFT_OUTPUT_REVIEW.md','PC007A_LOFT_WORKSPACE_REVIEW.md'):
    raw=blob(LOCAL,'docs/p2/implementation/'+path)
    assert b'APPROVED_IN_' in raw
result={'handoff_sha':PIN,'published_master_sha_verified_remote':remote,'pending_local_sha':LOCAL,'integration_head_descends_from_checkpoint':integration_head,
        'changed_paths':changes,'runtime_and_acceptance_unchanged':True,'pause_explicit_owner_request':True,
        'actual_local_evidence_records':observations,'performance_independent_review':'NOT_RUN',
        'performance_runtime_sha':perf['performance_runtime_sha'],'performance_handoff_sha':perf['performance_handoff_sha'],
        'performance_measurements':'AUTHOR_RECORDED_OFFSCREEN_ONLY; NOT_INDEPENDENT_PERFORMANCE_REVIEW',
        'whole_P2_complete':False,'novice_count':0,'physical':'NOT_RUN_P3',
        'verdict':'APPROVED_IN_DOC_ONLY_HANDOFF_PUBLICATION_SCOPE',
        'permitted_mechanical_followup':'Exact frozen performance checkpoint and its handoff path; retain review NOT_RUN and no source publication'}
out=ROOT/'docs/p2/implementation/evidence/handoff-2026-11-10-review-1cd6dc5.json'
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,indent=2))
