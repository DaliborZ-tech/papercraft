"""Independent pinned/offscreen review; never imports the concurrently edited WT."""
import hashlib, io, json, os, subprocess, sys, tarfile, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PIN = sys.argv[1] if len(sys.argv)>1 else 'ea03025cba5245acdaa83ae4a2575dd1b0e6a2e6'
PIN = subprocess.check_output(['git','rev-parse',PIN],cwd=ROOT,text=True).strip()
E = ROOT/'docs/p2/implementation/evidence'
raw = subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml',
    'docs/p2/implementation/evidence/pc006a-desktop-7da2403-run04/own-model.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-D-ui-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    for member in archive.getmembers(): assert (target/member.name).resolve().is_relative_to(target)
    archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
code='''import hashlib,json;from pathlib import Path
from archpapercraft.ui import author_segmentation,author_manual_layout,author_window,author_viewport
print(json.dumps({m.__name__:{"path":m.__file__,"lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (author_segmentation,author_manual_layout,author_window,author_viewport)}))'''
probes=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=target,env=env,text=True))
for name,probe in probes.items():
    assert Path(probe['path']).resolve().is_relative_to(target)
    relative=Path(probe['path']).relative_to(target).as_posix()
    expected=subprocess.check_output(['git','show',PIN+':'+relative],cwd=ROOT).replace(b'\r\n',b'\n')
    assert probe['lf_sha256']==hashlib.sha256(expected).hexdigest()
runs={}
suffix=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--suffix=')),PIN[:7])
select=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--select=')),None)
for name,tests in [
    ('original',['tests/authoring/test_segmentation_dialog.py','tests/authoring/test_segmentation_workspace.py',
                 'tests/authoring/test_workspace.py','tests/authoring/test_loft_workspace.py']),
    ('own',[str(E/'pc008-ui-review-own.py')])]:
    if '--own-only' in sys.argv and name=='original': continue
    if '--dialogs-only' in sys.argv and name=='original':tests=tests[:2]
    if select and name=='own':tests=[tests[0]+'::'+select]
    r=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),
        f'--junitxml={E}/pc008-ui-review-{name}-{suffix}.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
(E/f'pc008-ui-review-archive-{suffix}.json').write_text(json.dumps({
    'source_sha':PIN,'archive_sha256':hashlib.sha256(raw).hexdigest(),
    'isolated_directory':str(target),'actual_imports':probes,'runs':runs},indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
