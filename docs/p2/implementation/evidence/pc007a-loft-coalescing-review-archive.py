"""Exact-source independent coalescing review; never imports the live worktree."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4];PIN='730cb28f2e3f221e03e7df174bf194ff577d6c3c'
E=ROOT/'docs/p2/implementation/evidence'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-loft-coalescing-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
    archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
imports=json.loads(subprocess.check_output([sys.executable,'-c','import json,hashlib;from pathlib import Path;from archpapercraft.authoring import loft_surface,loft_curve_compaction;print(json.dumps({m.__name__:{"path":m.__file__,"lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (loft_surface,loft_curve_compaction)}))'],cwd=target,env=env,text=True))
for record in imports.values():
    path=Path(record['path']).resolve();assert path.is_relative_to(target)
    blob=subprocess.check_output(['git','show',PIN+':'+path.relative_to(target).as_posix()],cwd=ROOT)
    assert record['lf_sha256']==hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()
runs={}
for name,tests in [('original',['tests/authoring/test_loft_curve_compaction.py','tests/authoring/test_loft_curves.py','tests/authoring/test_loft_surface.py']),('own',[str(E/'pc007a-loft-coalescing-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc007a-loft-coalescing-review-{name}-730cb28.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(E/'pc007a-loft-coalescing-review-archive-730cb28.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(raw).hexdigest(),'isolated_directory':str(target),'actual_imports':imports,'runs':runs},indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
