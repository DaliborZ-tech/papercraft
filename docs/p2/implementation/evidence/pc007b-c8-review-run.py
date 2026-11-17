"""Exact isolated C+LINE/schema8 review, never a native GUI driver."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
CODE='8f1ec6382d527c719133958e7eb6f78a724ef5d5'
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests/authoring'),str(ROOT/'tools/authoring')]),QT_QPA_PLATFORM='offscreen')
probe=json.loads(subprocess.check_output([sys.executable,'-c','''import json,hashlib
from pathlib import Path
from archpapercraft.authoring import project,curved_connectors,profile_subdivision
from archpapercraft.ui import author_window
import circular_desktop_steps
print(json.dumps({m.__name__:{"path":m.__file__,"sha256_lf":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (project,curved_connectors,profile_subdivision,author_window,circular_desktop_steps)}))'''],cwd=ROOT,env=env,text=True))
for row in probe.values():
 p=Path(row['path']);assert p.resolve().is_relative_to(ROOT)
 blob=subprocess.check_output(['git','show',CODE+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n');assert hashlib.sha256(blob).hexdigest()==row['sha256_lf']
mode=sys.argv[1] if len(sys.argv)>1 else 'own';suffix=sys.argv[2] if len(sys.argv)>2 else 'run01'
tests=[str(E/'pc007b-c8-review-own.py')] if mode=='own' else ['tests/authoring/test_combined_authoring_format.py','tests/authoring/test_curved_connector_sources.py','tests/authoring/test_subdivision_workspace.py']
if len(sys.argv)>3:tests=[tests[0]+'::'+sys.argv[3]]
r=subprocess.run([sys.executable,'-m','pytest',*tests,'-q',f'--junitxml={E}/pc007b-c8-review-{mode}-{suffix}.xml'],cwd=ROOT,env=env,text=True,capture_output=True)
out=dict(source_sha=CODE,actual_imports=probe,qt_platform='offscreen',own_source_sha256=hashlib.sha256((E/'pc007b-c8-review-own.py').read_bytes()).hexdigest() if mode=='own' else None,run=dict(exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
(E/f'pc007b-c8-review-{mode}-{suffix}.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(mode=mode,exit=r.returncode,summary=r.stdout.splitlines()[-1],stdout=r.stdout if r.returncode else '')))
