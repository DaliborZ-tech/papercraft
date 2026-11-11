"""Pin own isolated checkout imports; only tests and review evidence change."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
CODE='62cb8bc3d84c5c3edf0c7faf08965ea5eef4b625';HEAD='9e1c7ed95690080a008edd101c45eeb6e006d9df'
args=[x for x in sys.argv[1:] if not x.startswith('--pin=')]
pin=next((x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--pin=')),None)
SOURCE=ROOT;archive_sha=None
if pin:
 CODE=subprocess.check_output(['git','rev-parse',pin],cwd=ROOT,text=True).strip();HEAD=CODE
 raw=subprocess.check_output(['git','archive','--format=tar',CODE,'src','tests','pyproject.toml'],cwd=ROOT)
 SOURCE=Path(tempfile.mkdtemp(prefix='pc007b-curved-ui-review-')).resolve();archive_sha=hashlib.sha256(raw).hexdigest()
 with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
  for member in archive.getmembers():assert (SOURCE/member.name).resolve().is_relative_to(SOURCE)
  archive.extractall(SOURCE,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(SOURCE/'src'),str(SOURCE/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c','''import json,hashlib
from pathlib import Path
from archpapercraft.ui import author_curved_connectors,author_window,author_paper,author_viewport
print(json.dumps({m.__name__:{"path":m.__file__,"sha256_lf":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (author_curved_connectors,author_window,author_paper,author_viewport)}))'''],cwd=SOURCE,env=env,text=True))
for row in probe.values():
 p=Path(row['path']);assert p.resolve().is_relative_to(SOURCE/'src')
 blob=subprocess.check_output(['git','show',CODE+':'+p.relative_to(SOURCE).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n')
 assert hashlib.sha256(blob).hexdigest()==row['sha256_lf']
mode=args[0] if args else 'own';suffix=args[1] if len(args)>1 else 'run01'
tests=([str(E/'pc007b-curved-ui-review-own.py')] if mode=='own' else ['tests/authoring/test_curved_authoring_ui.py','tests/authoring/test_curve_workspace.py','tests/authoring/test_loft_workspace.py','tests/authoring/test_segmentation_workspace.py'])
if len(args)>2:tests=[tests[0]+'::'+args[2]]
r=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(SOURCE/'pyproject.toml'),f'--junitxml={E}/pc007b-curved-ui-review-{mode}-{suffix}.xml'],cwd=SOURCE,env=env,text=True,capture_output=True)
out=dict(source_sha=CODE,source_handoff_sha=HEAD,archive_sha256=archive_sha,actual_imports=probe,qt_platform='offscreen',own_tests_sha256_at_run=hashlib.sha256((E/'pc007b-curved-ui-review-own.py').read_bytes()).hexdigest(),run=dict(exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
(E/f'pc007b-curved-ui-review-{mode}-{suffix}.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(mode=mode,exit=r.returncode,summary=r.stdout.splitlines()[-1],stdout=r.stdout if r.returncode else '')))
