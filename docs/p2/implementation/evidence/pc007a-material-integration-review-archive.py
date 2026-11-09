"""Isolated source snapshot and fresh subprocesses; does not use live source."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN='61168e0879157baba1193785b9856f24d1d1c959'
evidence=ROOT/'docs/p2/implementation/evidence'
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-material-integration-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not (target/member.name).resolve().is_relative_to(target):raise ValueError('archive path')
    source.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=str(target/'src'),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c',
    'import json,hashlib,importlib;from pathlib import Path;names=["attachments","bend","clearance","curve_material"];r={};exec("for n in names:\\n m=importlib.import_module(\\"archpapercraft.authoring.\\"+n);r[n]={\\"path\\":m.__file__,\\"source_lf_sha256\\":hashlib.sha256(Path(m.__file__).read_text(encoding=\\"utf8\\").encode(\\"utf8\\")).hexdigest()}");print(json.dumps(r))'],cwd=target,env=env,text=True))
for name,record in probe.items():
    if not Path(record['path']).resolve().is_relative_to(target):raise ValueError('wrong source import')
    raw=subprocess.check_output(['git','show',PIN+':src/archpapercraft/authoring/'+name+'.py'],cwd=ROOT)
    if record['source_lf_sha256']!=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest():raise ValueError('source differs beyond line endings')
runs={}
tests=['tests/authoring/test_curve_contacts.py','tests/authoring/test_curve_bend.py','tests/authoring/test_clearance_lower_bound.py','tests/authoring/test_clearance.py','tests/authoring/test_bend_adapter.py']
for name,paths in [('original',tests),('own',[str(evidence/'pc007a-material-integration-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*paths,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={evidence}/pc007a-material-integration-review-{name}-61168e0.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(evidence/'pc007a-material-integration-review-archive-61168e0.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(archive).hexdigest(),'isolated_directory':str(target),'actual_import_probe':probe,'runs':runs},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
