"""Isolated full source/test/tool archive for the actual vector-output review."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN='820ab6672d6a3f252391807b4c2c626c51a040bb'
evidence=ROOT/'docs/p2/implementation/evidence'
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','tools','pyproject.toml',
                                'docs/p2/implementation/evidence/pc006b-desktop-eb08f97-run06/model-A/model-A.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-vector-output-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not (target/member.name).resolve().is_relative_to(target): raise ValueError('archive path')
    source.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=str(target/'src'),QT_QPA_PLATFORM='offscreen')
runs={}
for name,tests in [('original',['tests/authoring/test_curve_pdf_validation.py','tests/authoring/test_curve_export_guard.py','tests/authoring/test_profile_curves.py','tests/authoring/test_curve_workspace.py']),('own',[str(evidence/'pc007a-vector-output-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={evidence}/pc007a-vector-output-review-{name}-820ab66.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(evidence/'pc007a-vector-output-review-archive-820ab66.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(archive).hexdigest(),'isolated_directory':str(target),'runs':runs},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
