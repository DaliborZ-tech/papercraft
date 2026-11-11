"""Narrow exact-commit lesson/queue/link audit; no product changes."""
import hashlib,json,posixpath,re,subprocess,sys
from pathlib import Path
ROOT=Path(sys.argv[1]);OWN=Path(__file__).resolve().parent
CODE='24e08019a711c5c7c19ca73a5ac35e5093dfb4d0';META='93f650c4a22a9d1dffd3b65c69f4b9505d5889f7'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(path):return git('show',META+':'+path)
paths=set(git('ls-tree','-r','--name-only',META).decode().splitlines())
norms=['AGENTS.md','02_CODEX_MANDATE.md','04_ACCEPTANCE_AND_VERIFICATION.md','docs/p2/v1.2/ACCEPTANCE.md']
assert not git('diff','--name-only','6796c63dc6aee0cd8331feb22df4e1c4afd0df27',META,'--',*norms).strip()
assert not git('diff','--name-only',CODE,META,'--','src','tools','tests','pyproject.toml').strip()
documents=['.agents/skills/'+n+'/SKILL.md' for n in ('papercraft-construction','papercraft-authoring-ui','papercraft-verification','papercraft-delivery')]
documents+=['docs/p2/implementation/PC008_LINE_SUBDIVISION_DELIVERY.md']
checked=[]
for relative in documents:
 for target in re.findall(r'\]\(([^)]+)\)',blob(relative).decode('utf8')):
  if target.startswith(('https:','http:','#')):continue
  path=posixpath.normpath(posixpath.join(posixpath.dirname(relative),target.split('#')[0]));assert path in paths,(relative,target)
  checked.append(dict(source=relative,target=path))
ledger=json.loads(blob('docs/p2/SKILL_IMPROVEMENTS.json'));items={e['id']:e for e in ledger['entries']}
line=items['SK-011']['line_transfer_2026_11_11'];consumer=items['SK-015']
assert line['source_sha']==CODE and line['status'].startswith('INITIAL_TRANSFER_FAILED_LS04') and line['effectiveness']=='PENDING_NEXT_USE'
assert consumer['product_correction']['source_sha']=='a770f8a8bed102bcf8538d0e57e4f5659f809949'
assert consumer['effectiveness']=='PENDING_NEXT_USE' and consumer['next_use']['status']=='NOT_RUN'
assert consumer['cause']['status']=='REPRODUCED_WITH_ORIGINAL_COMMAND_TRACEBACK'
queue=json.loads(blob('05_WORK_QUEUE.json'));tickets={t['id']:t for t in queue['tickets']}
assert all(tickets[k]['status']!='COMPLETE' for k in ('PC-008','PC-009','PC-010'))
assert queue['current_delivery']['status']=='IN_PROGRESS' and queue['release_readiness'].startswith('NOT_READY')
progress=tickets['PC-008']['live_LINE_progress_2026_11_11'];assert progress['code_sha']==CODE and 'FINAL_ARTIFACT_REVIEW_PENDING' in progress['status']
out=dict(status='PASS_METADATA_IN_SCOPE_PENDING_MECHANICAL_CLOSURE',source_sha=CODE,metadata_sha=META,runtime_unchanged=True,normative_documents_unchanged=True,
 links_checked=len(checked),links=checked,sk011_initial_transfer_failure_preserved=True,sk015_current_repair_documented=True,broader_effectiveness='PENDING_NEXT_USE',
 current_package='LINE_TECHNICAL_INCREMENT_ONLY_NOT_COMPLETE_AU13_AU14_PC008_P2',closure_notes=['Update reviewed LINE694 text to final24e','Separate expected8769.772228646 from actualSVG8769.772229 and actualPDF8769.772000000002','Mark current repair/text/artifact review approved by final report while preserving initial transfer failure and PENDING_NEXT_USE'])
(OWN/'pc008-line-subdivision-review-metadata-93f650c.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in out.items() if k!='links'},indent=2))
