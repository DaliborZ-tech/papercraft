"""Add the omitted exact Git fixture and replay only its previously unrun test."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
a=json.loads((E/'pc008-domain-review-archive-95fa2c7.json').read_text(encoding='utf8'))
target=Path(a['isolated_directory']);relative='docs/p2/implementation/evidence/pc006a-desktop-7da2403-run04/own-model.apcraft'
raw=subprocess.check_output(['git','show',a['source_sha']+':'+relative],cwd=ROOT)
path=target/relative;assert path.resolve().is_relative_to(target.resolve());path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(target/'src'),str(target/'tests/authoring')]),QT_QPA_PLATFORM='offscreen')
test='tests/authoring/test_interior_persistence.py::test_actual_schema_one_implicit_tab_can_be_edited_individually_in_its_copy'
r=subprocess.run([sys.executable,'-m','pytest',test,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={E}/pc008-domain-review-legacy-replay-95fa2c7.xml'],cwd=target,env=env,text=True,capture_output=True)
result={'source_sha':a['source_sha'],'isolated_directory':str(target),'fixture_path':relative,'fixture_git_blob_sha256':hashlib.sha256(raw).hexdigest(),
        'note':'Initial1FAIL was missing reviewer archive fixture, not product.92 original and19 own already passed; only missing-fixture test replayed.',
        'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
(E/'pc008-domain-review-legacy-replay-95fa2c7.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(r.stdout);assert r.returncode==0
