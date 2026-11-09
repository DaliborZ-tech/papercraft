"""Isolated full source/test/tool archive for the actual vector-output review."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PIN=sys.argv[1] if len(sys.argv)>1 else '820ab6672d6a3f252391807b4c2c626c51a040bb'
evidence=ROOT/'docs/p2/implementation/evidence'
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','tools','pyproject.toml',
                                'docs/p2/implementation/evidence/pc006b-desktop-eb08f97-run06/model-A/model-A.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-vector-output-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not (target/member.name).resolve().is_relative_to(target): raise ValueError('archive path')
    source.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=str(target/'src'),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c',
    'import json,hashlib;from pathlib import Path;import archpapercraft.exporter.curve_output_validation as m;print(json.dumps({"module_path":m.__file__,"sha256":hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest(),"source_lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode("utf8")).hexdigest()}))'],
    cwd=target,env=env,text=True))
if not Path(probe['module_path']).resolve().is_relative_to(target): raise ValueError('wrong actual module import')
expected_source=subprocess.check_output(['git','show',PIN+':src/archpapercraft/exporter/curve_output_validation.py'],cwd=ROOT)
if probe['source_lf_sha256']!=hashlib.sha256(expected_source.replace(b'\r\n',b'\n')).hexdigest(): raise ValueError('imported module source differs from reviewed Git blob beyond line endings')
runs={}
for name,tests in [('original',['tests/authoring/test_curve_pdf_validation.py','tests/authoring/test_curve_export_guard.py','tests/authoring/test_profile_curves.py','tests/authoring/test_curve_workspace.py']),('own',[str(evidence/'pc007a-vector-output-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={evidence}/pc007a-vector-output-review-{name}-{PIN[:7]}.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(evidence/f'pc007a-vector-output-review-archive-{PIN[:7]}.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(archive).hexdigest(),'isolated_directory':str(target),'actual_import_probe':probe,'runs':runs},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
