"""Pin and isolate the async-export review from all live worktree changes."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN=sys.argv[1] if len(sys.argv)>1 else 'e1948cfd11c095fd2aaf5643edd2403630ea4747'
PIN=subprocess.check_output(['git','rev-parse',PIN],cwd=ROOT,text=True).strip()
E=ROOT/'docs/p2/implementation/evidence'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','tools','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-export-job-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
    archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
imports=json.loads(subprocess.check_output([sys.executable,'-c','import json,hashlib;from pathlib import Path;from archpapercraft.ui import author_window,author_export_job;from archpapercraft.exporter import author_export;print(json.dumps({m.__name__:{"path":m.__file__,"lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (author_window,author_export_job,author_export)}))'],cwd=target,env=env,text=True))
for record in imports.values():
    path=Path(record['path']).resolve();assert path.is_relative_to(target)
    blob=subprocess.check_output(['git','show',PIN+':'+path.relative_to(target).as_posix()],cwd=ROOT)
    assert record['lf_sha256']==hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()
runs={}
for name,paths in [('original',['tests/authoring/test_export_job.py','tests/authoring/test_export.py','tests/authoring/test_workspace.py']),('own',[str(E/'pc007a-export-job-review-own.py')])]:
    if name=='original' and '--own-only' in sys.argv:continue
    result=subprocess.run([sys.executable,'-m','pytest',*paths,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc007a-export-job-review-{name}-{PIN[:7]}.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(E/f'pc007a-export-job-review-archive-{PIN[:7]}.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(raw).hexdigest(),'isolated_directory':str(target),'actual_imports':imports,'runs':runs},indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
