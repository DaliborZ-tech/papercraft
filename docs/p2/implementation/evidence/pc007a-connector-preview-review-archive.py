"""Source-isolated UI delta review with actual module-path verification."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN='2944c0fc7bb899355d45fe1f16e49253c90560c4'
evidence=ROOT/'docs/p2/implementation/evidence'
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-preview-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not (target/member.name).resolve().is_relative_to(target):raise ValueError('archive path')
    source.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=str(target/'src'),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c',
    'import json,hashlib;from pathlib import Path;import archpapercraft.ui.author_connectors as m;print(json.dumps({"path":m.__file__,"source_lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode("utf8")).hexdigest()}))'],cwd=target,env=env,text=True))
blob=subprocess.check_output(['git','show',PIN+':src/archpapercraft/ui/author_connectors.py'],cwd=ROOT)
if not Path(probe['path']).resolve().is_relative_to(target) or probe['source_lf_sha256']!=hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest():raise ValueError('wrong actual preview source')
runs={}
for name,paths in [('original',['tests/authoring/test_curve_connector_preview.py','tests/authoring/test_connector_panel.py','tests/authoring/test_curve_workspace.py']),('own',[str(evidence/'pc007a-connector-preview-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*paths,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={evidence}/pc007a-connector-preview-review-{name}-2944c0f.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(evidence/'pc007a-connector-preview-review-archive-2944c0f.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(archive).hexdigest(),'isolated_directory':str(target),'actual_import_probe':probe,'runs':runs},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
