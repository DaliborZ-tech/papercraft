"""Pin exact source and fixtures for independent D writer review."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
PIN=sys.argv[1] if len(sys.argv)>1 else '26873c6d0950af412ba531f01440c3506b3dd6b1'
PIN=subprocess.check_output(['git','rev-parse',PIN],cwd=ROOT,text=True).strip()
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml',
 'docs/p2/implementation/evidence/pc008-domain-95fa2c7/backend-fixture.apcraft',
 'docs/p2/implementation/evidence/pc008-curved-domain-518b91a/raw/gothic-backend.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-D-output-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
 for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
 archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c','''import hashlib,json;from pathlib import Path
from archpapercraft.exporter import segmented_output_validation,author_export
from archpapercraft.authoring import project
print(json.dumps({m.__name__:{"path":m.__file__,"lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (segmented_output_validation,author_export,project)}))'''],cwd=target,env=env,text=True))
for name,record in probe.items():
 path=Path(record['path']);assert path.resolve().is_relative_to(target)
 expected=subprocess.check_output(['git','show',PIN+':'+path.relative_to(target).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n')
 assert record['lf_sha256']==hashlib.sha256(expected).hexdigest()
suffix=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--suffix=')),PIN[:7])
manifest=dict(source_sha=PIN,archive_sha256=hashlib.sha256(raw).hexdigest(),isolated_directory=str(target),actual_imports=probe,runs={})
manifestpath=E/f'pc008-output-review-archive-{suffix}.json';manifestpath.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
for name,tests in [('original',['tests/authoring/test_segmented_export.py']),('own',[str(E/'pc008-output-review-own.py')])]:
 if '--own-only' in sys.argv and name=='original':continue
 if '--original-only' in sys.argv and name=='own':continue
 if '--original-comparator' in sys.argv and name=='original':tests=[
  'tests/authoring/test_segmented_export.py::test_numeric_actual_files_tab_area_cannot_enlarge_the_body_error_budget',
  'tests/authoring/test_segmented_export.py::test_legitimate_tab_union_keeps_the_certified_body_and_is_not_a_false_exact']
 selected=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--select=')),None)
 if selected and name=='own':tests=[tests[0]+'::'+selected]
 if '--exclude-tab' in sys.argv and name=='own':tests.extend(['-k','not tab_does_not_relax'])
 r=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc008-output-review-{name}-{suffix}.xml'],cwd=target,env=env,text=True,capture_output=True)
 manifest['runs'][name]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 manifestpath.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 print(json.dumps({name:{'exit':r.returncode,'summary':r.stdout.splitlines()[-1]}}),flush=True)
