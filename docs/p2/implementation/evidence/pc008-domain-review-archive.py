"""Pinned D domain review; concurrent bulk placement is deliberately excluded."""
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4];PIN='95fa2c7c0e5a5d50f0763ae2a461a4e5e2821872'
E=ROOT/'docs/p2/implementation/evidence'
raw=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml',
    'docs/p2/implementation/evidence/pc006a-desktop-7da2403-run04/own-model.apcraft'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-segmentation-domain-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    for member in archive.getmembers():assert (target/member.name).resolve().is_relative_to(target)
    archive.extractall(target,filter='data')
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
imports=json.loads(subprocess.check_output([sys.executable,'-c','import json,hashlib;from pathlib import Path;from archpapercraft.authoring import project,segmented_surface,paper;print(json.dumps({m.__name__:{"path":m.__file__,"lf_sha256":hashlib.sha256(Path(m.__file__).read_text(encoding="utf8").encode()).hexdigest()} for m in (project,segmented_surface,paper)}))'],cwd=target,env=env,text=True))
for record in imports.values():
    path=Path(record['path']).resolve();assert path.is_relative_to(target)
    blob=subprocess.check_output(['git','show',PIN+':'+path.relative_to(target).as_posix()],cwd=ROOT)
    assert record['lf_sha256']==hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()
runs={}
for name,tests in [('original',['tests/authoring/test_segmented_surface.py','tests/authoring/test_segmented_loft.py','tests/authoring/test_interior_persistence.py','tests/authoring/test_material_profile.py']),('own',[str(E/'pc008-domain-review-own.py')])]:
    result=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc008-domain-review-{name}-95fa2c7.xml'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
(E/'pc008-domain-review-archive-95fa2c7.json').write_text(json.dumps({'source_sha':PIN,'archive_sha256':hashlib.sha256(raw).hexdigest(),'isolated_directory':str(target),'actual_imports':imports,'runs':runs},indent=2)+'\n',encoding='utf8')
print(json.dumps({k:{'exit':v['returncode'],'summary':v['stdout'].splitlines()[-1]} for k,v in runs.items()},indent=2))
