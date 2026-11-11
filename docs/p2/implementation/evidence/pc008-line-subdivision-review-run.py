"""Exact archive for independent pure math/live LINE/widget review."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
PIN=sys.argv[1] if len(sys.argv)>1 else '9b87c89e1507b1df56940e4c08d213532a5216ad'
PIN=subprocess.check_output(['git','rev-parse',PIN],cwd=ROOT,text=True).strip()
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='pc008-line-subdivision-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
 for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
 archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c','''import hashlib,json;from pathlib import Path
from archpapercraft.authoring import curve_subdivision,profile_subdivision,project
from archpapercraft.ui import author_subdivision
print(json.dumps({m.__name__:{"path":m.__file__,"sha256_lf":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (curve_subdivision,profile_subdivision,project,author_subdivision)}))'''],cwd=target,env=env,text=True))
for record in probe.values():
 p=Path(record['path']);assert p.resolve().is_relative_to(target)
 blob=subprocess.check_output(['git','show',PIN+':'+p.relative_to(target).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n')
 assert record['sha256_lf']==hashlib.sha256(blob).hexdigest()
suffix=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--suffix=')),PIN[:7]);runs={}
for name,tests in [('original',['tests/authoring/test_curve_subdivision.py','tests/authoring/test_profile_subdivision.py','tests/authoring/test_subdivision_workspace.py']),('own',[str(E/'pc008-line-subdivision-review-own.py')])]:
 if '--own-only' in sys.argv and name=='original':continue
 select=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--select=')),None)
 if select and name=='own':tests=[tests[0]+'::'+select]
 r=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc008-line-subdivision-review-{name}-{suffix}.xml'],cwd=target,env=env,text=True,capture_output=True)
 runs[name]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 print(json.dumps({name:dict(exit=r.returncode,summary=r.stdout.splitlines()[-1])}),flush=True)
(E/f'pc008-line-subdivision-review-{suffix}.json').write_text(json.dumps(dict(source_sha=PIN,archive_sha256=hashlib.sha256(raw).hexdigest(),isolated_directory=str(target),actual_imports=probe,own_test_sha256_at_run=hashlib.sha256((E/'pc008-line-subdivision-review-own.py').read_bytes()).hexdigest(),runs=runs),indent=2)+'\n',encoding='utf8')
