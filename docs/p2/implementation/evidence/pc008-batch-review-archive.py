"""Exact isolated source for batch placement; live curved bridge is not tested."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
PIN=sys.argv[1] if len(sys.argv)>1 else '0210118e02dd7f65dc6161b5f86cfda2b2dbdf29'
PIN=subprocess.check_output(['git','rev-parse',PIN],cwd=ROOT,text=True).strip();E=ROOT/'docs/p2/implementation/evidence'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml',
    'docs/p2/implementation/evidence/pc006a-desktop-7da2403-run04/own-model.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-batch-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
    archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c','import hashlib,json;from pathlib import Path;from archpapercraft.authoring import project;print(json.dumps({"path":project.__file__,"lf_sha256":hashlib.sha256(Path(project.__file__).read_text(encoding="utf8").encode()).hexdigest()}))'],cwd=target,env=env,text=True))
assert Path(probe['path']).resolve().is_relative_to(target)
expected=subprocess.check_output(['git','show',PIN+':src/archpapercraft/authoring/project.py'],cwd=ROOT)
assert probe['lf_sha256']==hashlib.sha256(expected.replace(b'\r\n',b'\n')).hexdigest()
runs={}
for name,tests in [('original',['tests/authoring/test_batch_placement.py','tests/authoring/test_controller.py','tests/authoring/test_domain.py']),('own',[str(E/'pc008-batch-review-own.py')])]:
    if '--own-only' in sys.argv and name=='original':continue
    r=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc008-batch-review-{name}-{PIN[:7]}.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
(E/f'pc008-batch-review-archive-{PIN[:7]}.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(raw).hexdigest(),'isolated_directory':str(target),'actual_import':probe,'runs':runs},indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
