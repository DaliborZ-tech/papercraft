"""Archive the exact reviewed tree and run fresh processes outside shared edits."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[4]
PIN=sys.argv[1] if len(sys.argv)>1 else '55c4443d40beb36c83d26f8ae940b987c4facf9c'
evidence=ROOT/'docs/p2/implementation/evidence'
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tests','pyproject.toml'],cwd=ROOT)
target=Path(tempfile.mkdtemp(prefix='papercraft-topology-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not (target/member.name).resolve().is_relative_to(target):
            raise ValueError('Archive path escaped isolated review tree')
    source.extractall(target,filter='data')
env=dict(os.environ)
env['PYTHONPATH']=str(target/'src')
env['QT_QPA_PLATFORM']='offscreen'
runs={}
for name,tests in [('original',['tests/authoring/test_curve_topology.py','tests/authoring/test_curves.py']),
                   ('own',[str(evidence/'pc007a-topology-review-own.py')])]:
    output=evidence/f'pc007a-topology-review-{name}-{PIN[:7]}-archive.xml'
    process=subprocess.run([sys.executable,'-m','pytest',*tests,'-q','-c',str(target/'pyproject.toml'),f'--junitxml={output}'],cwd=target,env=env,text=True,capture_output=True)
    runs[name]={'returncode':process.returncode,'stdout':process.stdout,'stderr':process.stderr}
payload={'source_sha':PIN,'archive_sha256':hashlib.sha256(archive).hexdigest(),'isolated_directory':str(target),
         'method':'git_archive_exact_src_tests_pyproject_fresh_subprocess','runs':runs}
(evidence/f'pc007a-topology-review-archive-{PIN[:7]}.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({key:{'exit':value['returncode'],'summary':value['stdout'].splitlines()[-1]} for key,value in runs.items()},indent=2))
