"""Archive-pin helper review and preserve actual imports/Git LF identity."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
PIN='52836321810f7a8a0c6a8d43b801f98ed875bbde'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','tools','pyproject.toml'],cwd=ROOT)
a=Path(tempfile.mkdtemp(prefix='pc007b-c8-svg-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as t:
 for member in t.getmembers():assert (a/member.name).resolve().is_relative_to(a)
 t.extractall(a,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(a/'src'),str(a/'tools/authoring'),str(a/'tests/authoring')]),QT_QPA_PLATFORM='offscreen',PC8_NEAR_FAIL_EVIDENCE=sys.argv[1])
probe=json.loads(subprocess.check_output([sys.executable,'-c','import circular_svg_oracle as m,json,hashlib;from pathlib import Path;print(json.dumps(dict(path=m.__file__,sha256_lf=hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest())))'],cwd=a,env=env,text=True))
assert Path(probe['path']).resolve().is_relative_to(a)
assert probe['sha256_lf']==hashlib.sha256(subprocess.check_output(['git','show',PIN+':tools/authoring/circular_svg_oracle.py'],cwd=ROOT).replace(b'\r\n',b'\n')).hexdigest()
runs={};suffix=sys.argv[2] if len(sys.argv)>2 else 'run02'
for mode,path in [('author','tests/authoring/test_circular_svg_oracle.py'),('own',str(E/'pc007b-c8-review-svg-own.py'))]:
 r=subprocess.run([sys.executable,'-m','pytest',path,'-q','-c',str(a/'pyproject.toml'),f'--junitxml={E}/pc007b-c8-review-svg-{mode}-5283632-{suffix}.xml'],cwd=a,env=env,text=True,capture_output=True)
 runs[mode]=dict(exit=r.returncode,stdout=r.stdout,stderr=r.stderr)
 print(mode,r.stdout[-2000:] if r.returncode else r.stdout.splitlines()[-1],flush=True)
(E/f'pc007b-c8-review-svg-5283632-{suffix}.json').write_text(json.dumps(dict(source_sha=PIN,archive_sha256=hashlib.sha256(raw).hexdigest(),actual_import=probe,own_tests_sha256_at_run=hashlib.sha256((E/'pc007b-c8-review-svg-own.py').read_bytes()).hexdigest(),runs=runs),indent=2)+'\n',encoding='utf8')
