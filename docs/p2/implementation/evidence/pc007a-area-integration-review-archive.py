"""Exact archived source and actual import binding for V02 integration review."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN='3252544850c0d4a9c4465de8f359ec2a5350af27'
evidence=ROOT/'docs/p2/implementation/evidence'
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','tools','pyproject.toml',
    'docs/p2/implementation/evidence/pc006b-desktop-eb08f97-run06/model-A/model-A.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-area-integration-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not (target/member.name).resolve().is_relative_to(target):raise ValueError('archive path')
    source.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=str(target/'src'),QT_QPA_PLATFORM='offscreen')
probes=json.loads(subprocess.check_output([sys.executable,'-c',
    'import json,hashlib;from pathlib import Path;from archpapercraft.exporter import author_export,curve_output_validation,svg_curve_validation;from archpapercraft.authoring import curve_area;print(json.dumps({m.__name__:{"module_path":m.__file__,"source_lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode("utf8")).hexdigest()} for m in (author_export,curve_output_validation,svg_curve_validation,curve_area)}))'],cwd=target,env=env,text=True))
for name,probe in probes.items():
    path=Path(probe['module_path']).resolve()
    if not path.is_relative_to(target):raise ValueError('wrong actual module import')
    blob=subprocess.check_output(['git','show',PIN+':'+path.relative_to(target).as_posix()],cwd=ROOT)
    if probe['source_lf_sha256']!=hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest():raise ValueError('wrong imported source')
runs={}
for name,tests in [('original',['tests/authoring/test_curve_export_guard.py','tests/authoring/test_curve_pdf_validation.py','tests/authoring/test_editor_path_comparison.py','tests/authoring/test_curve_area.py']),('own',[str(evidence/'pc007a-area-integration-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={evidence}/pc007a-area-integration-review-{name}-3252544.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(evidence/'pc007a-area-integration-review-archive-3252544.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(archive).hexdigest(),'isolated_directory':str(target),'actual_import_probes':probes,'runs':runs},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
